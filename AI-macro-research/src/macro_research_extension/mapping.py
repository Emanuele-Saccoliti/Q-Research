from __future__ import annotations

import numpy as np

from macro_research_extension.schemas import AssetImplication, MacroRegime

ASSET_AXIS_WEIGHTS: dict[str, dict[str, float]] = {
    "Global equities": {
        "growth": 0.45,
        "inflation": -0.15,
        "policy": -0.25,
        "liquidity": 0.25,
        "risk_sentiment": 0.45,
    },
    "Long-duration government bonds (price)": {
        "growth": -0.20,
        "inflation": -0.50,
        "policy": -0.55,
        "liquidity": 0.20,
        "risk_sentiment": -0.20,
    },
    "US dollar": {
        "growth": 0.05,
        "inflation": 0.10,
        "policy": 0.50,
        "liquidity": -0.20,
        "risk_sentiment": -0.25,
    },
    "Broad commodities": {
        "growth": 0.35,
        "inflation": 0.45,
        "policy": -0.15,
        "liquidity": 0.15,
        "risk_sentiment": 0.05,
    },
    "Credit": {
        "growth": 0.40,
        "inflation": -0.10,
        "policy": -0.35,
        "liquidity": 0.30,
        "risk_sentiment": 0.50,
    },
}


class CrossAssetMapper:
    """Transparent research mapping from a macro state vector to asset implications."""

    def map(self, regime: MacroRegime) -> list[AssetImplication]:
        implications: list[AssetImplication] = []
        for asset, weights in ASSET_AXIS_WEIGHTS.items():
            contributions = {
                axis: getattr(regime.state, axis) * weight for axis, weight in weights.items()
            }
            denominator = sum(abs(weight) for weight in weights.values()) or 1.0
            score = float(np.clip(sum(contributions.values()) / denominator, -1.0, 1.0))
            direction = "positive" if score > 0.12 else "negative" if score < -0.12 else "mixed"
            drivers = [
                f"{axis.replace('_', ' ')}: {value:+.2f}"
                for axis, value in sorted(
                    contributions.items(), key=lambda item: abs(item[1]), reverse=True
                )[:3]
                if abs(value) >= 0.02
            ]
            confidence = float(np.clip(regime.confidence * (0.5 + abs(score)), 0.0, 1.0))
            implications.append(
                AssetImplication(
                    asset_class=asset,
                    direction=direction,
                    score=score,
                    confidence=confidence,
                    drivers=drivers,
                )
            )

        return implications

