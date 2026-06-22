from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from macro_research_extension.embeddings import FloatMatrix, cosine, normalize_rows
from macro_research_extension.schemas import NormalizedEvent


@dataclass(slots=True)
class ThemeCandidate:
    local_id: int
    label: str
    event_indices: list[int]
    event_ids: list[int]
    centroid: NDArray[np.float64]
    representative_summaries: list[str]
    sources: list[str]
    coherence: float


class DynamicThemeClusterer:
    """Discovers themes without requiring a fixed number of clusters."""

    def __init__(self, distance_threshold: float = 0.55):
        self.distance_threshold = distance_threshold

    def cluster(
        self,
        events: list[NormalizedEvent],
        embeddings: FloatMatrix,
    ) -> list[ThemeCandidate]:
        if len(events) != len(embeddings):
            raise ValueError("Events and embeddings must have the same length.")
        if not events:
            return []

        normalized = normalize_rows(embeddings)
        labels = self._cluster_labels(normalized)
        groups: dict[int, list[int]] = defaultdict(list)
        for index, label in enumerate(labels):
            groups[int(label)].append(index)

        candidates: list[ThemeCandidate] = []
        for local_id, indices in enumerate(groups.values()):
            centroid = normalize_rows(np.mean(normalized[indices], axis=0, keepdims=True))[0]
            ranked = sorted(
                indices,
                key=lambda index: cosine(normalized[index], centroid),
                reverse=True,
            )
            coherence = float(
                np.clip(
                    np.mean([cosine(normalized[index], centroid) for index in indices]),
                    0.0,
                    1.0,
                )
            )
            candidates.append(
                ThemeCandidate(
                    local_id=local_id,
                    label=self._theme_label([events[index].summary for index in indices]),
                    event_indices=indices,
                    event_ids=[events[index].item_id for index in indices],
                    centroid=centroid,
                    representative_summaries=[events[index].summary for index in ranked[:3]],
                    sources=[events[index].source for index in indices],
                    coherence=coherence,
                )
            )

        return sorted(candidates, key=lambda item: len(item.event_indices), reverse=True)

    def _cluster_labels(self, embeddings: FloatMatrix) -> NDArray[np.int64]:
        if len(embeddings) == 1:
            return np.array([0], dtype=np.int64)

        from sklearn.cluster import AgglomerativeClustering

        model = AgglomerativeClustering(
            n_clusters=None,
            metric="cosine",
            linkage="average",
            distance_threshold=self.distance_threshold,
        )
        return np.asarray(model.fit_predict(embeddings), dtype=np.int64)

    @staticmethod
    def _theme_label(summaries: list[str]) -> str:
        from sklearn.feature_extraction.text import TfidfVectorizer

        try:
            vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                max_features=96,
            )
            matrix = vectorizer.fit_transform(summaries)
        except ValueError:
            return "Unclassified macro theme"

        terms = vectorizer.get_feature_names_out()
        scores = np.asarray(matrix.sum(axis=0)).ravel()
        ordered = [terms[index] for index in np.argsort(scores)[::-1]]
        selected: list[str] = []
        for term in ordered:
            if any(term in chosen or chosen in term for chosen in selected):
                continue
            selected.append(term)
            if len(selected) == 3:
                break
        return " / ".join(selected).title() or "Unclassified macro theme"

