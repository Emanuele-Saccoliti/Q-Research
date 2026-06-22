from __future__ import annotations

import math

import numpy as np

from macro_research_extension.clustering import ThemeCandidate
from macro_research_extension.embeddings import Embedder, cosine, normalize_rows
from macro_research_extension.schemas import DynamicTheme, MacroAxisVector, MacroRegime

AXIS_PROTOTYPES: dict[str, tuple[str, str]] = {
    "growth": (
        "economic expansion stronger demand rising employment improving PMI accelerating output",
        "economic contraction weak demand falling employment deteriorating PMI recession slowdown",
    ),
    "inflation": (
        "inflation accelerating prices above expectations sticky services wages commodity shock",
        "disinflation falling prices inflation below expectations easing wage pressure deflation",
    ),
    "policy": (
        "hawkish monetary policy rate hikes higher for longer quantitative tightening",
        "dovish monetary policy rate cuts easing accommodation quantitative easing",
    ),
    "liquidity": (
        "liquidity expansion balance sheet growth credit expansion abundant funding",
        "liquidity contraction balance sheet reduction funding stress credit tightening",
    ),
    "risk_sentiment": (
        "risk on improving sentiment tighter credit spreads equity rally lower volatility",
        "risk off geopolitical stress wider credit spreads equity selloff higher volatility",
    ),
}


class PrototypeMacroMapper:
    """Maps cluster centroids to signed macro axes using semantic anchor prototypes."""

    def __init__(self, embedder: Embedder):
        self.prototype_vectors: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for axis, (positive, negative) in AXIS_PROTOTYPES.items():
            vectors = normalize_rows(embedder.encode([positive, negative]))
            self.prototype_vectors[axis] = (vectors[0], vectors[1])

    def map(self, candidate: ThemeCandidate) -> tuple[MacroAxisVector, float]:
        scores: dict[str, float] = {}
        evidence_strengths: list[float] = []

        for axis, (positive, negative) in self.prototype_vectors.items():
            positive_similarity = max(cosine(candidate.centroid, positive), 0.0)
            negative_similarity = max(cosine(candidate.centroid, negative), 0.0)
            evidence = positive_similarity + negative_similarity
            relative_direction = (
                (positive_similarity - negative_similarity) / evidence if evidence else 0.0
            )
            evidence_strength = min(evidence / 0.30, 1.0)
            scores[axis] = float(np.clip(relative_direction * evidence_strength, -1.0, 1.0))
            evidence_strengths.append(evidence_strength)

        confidence = float(
            np.clip(candidate.coherence * np.mean(evidence_strengths), 0.0, 1.0)
        )
        return MacroAxisVector(**scores), confidence


class RegimeInferer:
    def __init__(self, classification_threshold: float = 0.15):
        self.classification_threshold = classification_threshold

    def infer(self, themes: list[DynamicTheme]) -> MacroRegime:
        if not themes:
            return MacroRegime(
                name="mixed_transition",
                state=MacroAxisVector(),
                confidence=0.0,
            )

        weighted_themes: list[tuple[DynamicTheme, float]] = []
        for theme in themes:
            momentum_modifier = 1.0 + 0.15 * math.tanh(theme.metrics.momentum_zscore)
            weight = (
                theme.metrics.attention
                * (0.5 + 0.5 * theme.metrics.breadth)
                * (0.5 + 0.5 * theme.mapping_confidence)
                * momentum_modifier
            )
            weighted_themes.append((theme, weight))

        total_weight = sum(weight for _, weight in weighted_themes) or 1.0
        state_values = {
            axis: float(
                np.clip(
                    sum(
                        getattr(theme.macro_vector, axis) * weight
                        for theme, weight in weighted_themes
                    )
                    / total_weight,
                    -1.0,
                    1.0,
                )
            )
            for axis in MacroAxisVector.model_fields
        }
        state = MacroAxisVector(**state_values)
        confidence = float(
            np.clip(
                sum(theme.mapping_confidence * weight for theme, weight in weighted_themes)
                / total_weight,
                0.0,
                1.0,
            )
        )
        dominant = [
            theme.label
            for theme, _ in sorted(weighted_themes, key=lambda item: item[1], reverse=True)[:3]
        ]
        return MacroRegime(
            name=self._classify(state),
            state=state,
            confidence=confidence,
            dominant_themes=dominant,
        )

    def _classify(self, state: MacroAxisVector) -> str:
        threshold = self.classification_threshold
        if state.growth >= threshold and state.inflation <= -threshold:
            return "goldilocks"
        if state.growth >= threshold and state.inflation >= threshold:
            return "reflation"
        if state.growth <= -threshold and state.inflation >= threshold:
            return "stagflation_pressure"
        if state.growth <= -threshold and state.inflation <= -threshold:
            return "recession_disinflation"
        if state.policy >= 0.25:
            return "policy_tightening"
        if state.policy <= -0.25:
            return "policy_easing"
        if state.risk_sentiment <= -0.25:
            return "risk_off"
        return "mixed_transition"

