from datetime import UTC, datetime, timedelta

import numpy as np

from macro_research_extension.clustering import ThemeCandidate
from macro_research_extension.history import ThemeHistoryStore


def _candidate(centroid: list[float]) -> ThemeCandidate:
    return ThemeCandidate(
        local_id=0,
        label="Sticky Inflation",
        event_indices=[0, 1],
        event_ids=[0, 1],
        centroid=np.asarray(centroid, dtype=np.float64),
        representative_summaries=["Inflation remains sticky."],
        sources=["source-a", "source-b"],
        coherence=0.9,
    )


def test_history_matches_theme_and_updates_dynamic_metrics(tmp_path):
    path = tmp_path / "history.json"
    first_time = datetime(2026, 6, 20, tzinfo=UTC)
    store = ThemeHistoryStore(
        path,
        lookback_days=90,
        match_similarity=0.70,
        persistence_target_runs=5,
        breadth_target_sources=5,
    )
    first = _candidate([1.0, 0.0])
    theme_id, metrics = store.resolve(first, total_events=4, observed_at=first_time)

    assert metrics.attention == 0.5
    assert metrics.novelty == 1.0
    assert metrics.breadth == 0.4
    assert metrics.persistence == 0.2

    store.append(first, theme_id, metrics, first_time)
    store.save(first_time)

    second_time = first_time + timedelta(days=1)
    reloaded = ThemeHistoryStore(
        path,
        lookback_days=90,
        match_similarity=0.70,
        persistence_target_runs=5,
        breadth_target_sources=5,
    )
    second_id, second_metrics = reloaded.resolve(
        _candidate([0.99, 0.01]),
        total_events=4,
        observed_at=second_time,
    )

    assert second_id == theme_id
    assert second_metrics.novelty < 0.01
    assert second_metrics.persistence == 0.4

