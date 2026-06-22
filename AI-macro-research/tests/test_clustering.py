import numpy as np

from macro_research_extension.clustering import DynamicThemeClusterer
from macro_research_extension.schemas import NormalizedEvent


def _event(item_id: int, summary: str, source: str = "source") -> NormalizedEvent:
    return NormalizedEvent(
        item_id=item_id,
        title=summary,
        summary=summary,
        source=source,
        llm_confidence=0.9,
    )


def test_clusterer_discovers_two_separated_themes():
    events = [
        _event(0, "Inflation remains sticky after a strong CPI release."),
        _event(1, "Core prices exceeded expectations and delayed rate cuts."),
        _event(2, "Manufacturing demand contracted and employment weakened."),
        _event(3, "PMI data signalled a broad growth slowdown."),
    ]
    embeddings = np.asarray(
        [
            [1.0, 0.0],
            [0.95, 0.05],
            [0.0, 1.0],
            [0.05, 0.95],
        ],
        dtype=np.float64,
    )

    themes = DynamicThemeClusterer(distance_threshold=0.30).cluster(events, embeddings)

    assert len(themes) == 2
    assert sorted(len(theme.event_indices) for theme in themes) == [2, 2]
    assert all(theme.coherence > 0.95 for theme in themes)

