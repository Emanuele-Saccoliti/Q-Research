from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from pydantic import BaseModel, Field

from macro_research_extension.clustering import ThemeCandidate
from macro_research_extension.embeddings import cosine
from macro_research_extension.schemas import ThemeMetrics


class ThemeSnapshot(BaseModel):
    theme_id: str
    label: str
    observed_at: datetime
    centroid: list[float]
    attention: float = Field(ge=0.0, le=1.0)
    source_count: int = Field(ge=0)


class ThemeHistoryData(BaseModel):
    version: int = 1
    snapshots: list[ThemeSnapshot] = Field(default_factory=list)


class ThemeHistoryStore:
    def __init__(
        self,
        path: Path,
        *,
        lookback_days: int,
        match_similarity: float,
        persistence_target_runs: int,
        breadth_target_sources: int,
    ):
        self.path = path
        self.lookback_days = lookback_days
        self.match_similarity = match_similarity
        self.persistence_target_runs = persistence_target_runs
        self.breadth_target_sources = breadth_target_sources
        self.data = self._load()

    def _load(self) -> ThemeHistoryData:
        if not self.path.exists():
            return ThemeHistoryData()
        try:
            return ThemeHistoryData.model_validate_json(self.path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            raise RuntimeError(f"Unable to read theme history at {self.path}: {exc}") from exc

    def resolve(
        self,
        candidate: ThemeCandidate,
        *,
        total_events: int,
        observed_at: datetime,
    ) -> tuple[str, ThemeMetrics]:
        recent = self._recent_snapshots(observed_at)
        compatible = [
            snapshot for snapshot in recent if len(snapshot.centroid) == len(candidate.centroid)
        ]
        similarities = [
            cosine(candidate.centroid, np.asarray(snapshot.centroid, dtype=np.float64))
            for snapshot in compatible
        ]
        best_index = int(np.argmax(similarities)) if similarities else None
        best_similarity = similarities[best_index] if best_index is not None else 0.0

        if best_index is not None and best_similarity >= self.match_similarity:
            theme_id = compatible[best_index].theme_id
        else:
            digest = hashlib.sha1(
                f"{candidate.label}|{observed_at.isoformat()}".encode()
            ).hexdigest()[:10]
            theme_id = f"theme-{digest}"

        matched = [snapshot for snapshot in recent if snapshot.theme_id == theme_id]
        attention = len(candidate.event_indices) / max(total_events, 1)
        historical_attention = [snapshot.attention for snapshot in matched]
        momentum = self._momentum(attention, historical_attention)
        breadth = self._breadth(candidate.sources)
        novelty = float(np.clip(1.0 - best_similarity, 0.0, 1.0)) if compatible else 1.0
        active_dates = {snapshot.observed_at.date() for snapshot in matched}
        active_dates.add(observed_at.date())
        persistence = min(len(active_dates) / self.persistence_target_runs, 1.0)

        return theme_id, ThemeMetrics(
            attention=attention,
            momentum_zscore=momentum,
            breadth=breadth,
            novelty=novelty,
            persistence=persistence,
            source_count=len(set(candidate.sources)),
            article_count=len(candidate.event_indices),
        )

    def append(
        self,
        candidate: ThemeCandidate,
        theme_id: str,
        metrics: ThemeMetrics,
        observed_at: datetime,
    ) -> None:
        self.data.snapshots.append(
            ThemeSnapshot(
                theme_id=theme_id,
                label=candidate.label,
                observed_at=observed_at,
                centroid=candidate.centroid.tolist(),
                attention=metrics.attention,
                source_count=metrics.source_count,
            )
        )

    def save(self, observed_at: datetime | None = None) -> None:
        now = observed_at or datetime.now(UTC)
        cutoff = now - timedelta(days=self.lookback_days * 2)
        self.data.snapshots = [
            snapshot for snapshot in self.data.snapshots if snapshot.observed_at >= cutoff
        ]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(
            json.dumps(self.data.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def _recent_snapshots(self, observed_at: datetime) -> list[ThemeSnapshot]:
        cutoff = observed_at - timedelta(days=self.lookback_days)
        return [snapshot for snapshot in self.data.snapshots if snapshot.observed_at >= cutoff]

    @staticmethod
    def _momentum(current: float, history: list[float]) -> float:
        if len(history) < 2:
            return 0.0
        mean = statistics.fmean(history)
        deviation = statistics.pstdev(history)
        if deviation < 1e-8:
            return 0.0 if abs(current - mean) < 1e-8 else math.copysign(3.0, current - mean)
        return float(np.clip((current - mean) / deviation, -5.0, 5.0))

    def _breadth(self, sources: list[str]) -> float:
        counts = Counter(sources)
        if not counts:
            return 0.0
        coverage = min(len(counts) / self.breadth_target_sources, 1.0)
        if len(counts) == 1:
            diversity = 1.0
        else:
            total = sum(counts.values())
            entropy = -sum((count / total) * math.log(count / total) for count in counts.values())
            diversity = entropy / math.log(len(counts))
        return float(np.clip(coverage * diversity, 0.0, 1.0))

