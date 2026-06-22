from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from macro_research_extension.clustering import DynamicThemeClusterer, ThemeCandidate
from macro_research_extension.config import Settings
from macro_research_extension.embeddings import Embedder, build_embedder
from macro_research_extension.history import ThemeHistoryData, ThemeHistoryStore
from macro_research_extension.llm import LLMEventNormalizer, LLMReportNarrator
from macro_research_extension.mapping import CrossAssetMapper
from macro_research_extension.regimes import PrototypeMacroMapper, RegimeInferer
from macro_research_extension.reporting import save_report
from macro_research_extension.retrievers import MacroNewsRetriever
from macro_research_extension.schemas import DynamicResearchReport, DynamicTheme


class DynamicMacroResearchWorkflow:
    """Retrieval -> LLM normalization -> NLP/ML themes -> regime -> research report."""

    def __init__(
        self,
        settings: Settings,
        *,
        retriever: Any | None = None,
        normalizer: Any | None = None,
        narrator: Any | None = None,
        embedder: Embedder | None = None,
    ):
        self.settings = settings
        self.retriever = retriever or MacroNewsRetriever(settings.max_articles)
        self.normalizer = normalizer or LLMEventNormalizer(settings)
        self.narrator = narrator or LLMReportNarrator(settings)
        self.embedder = embedder or build_embedder(
            settings.embedding_provider,
            settings.embedding_model,
            settings.embedding_dimensions,
        )
        self.clusterer = DynamicThemeClusterer(settings.cluster_distance_threshold)
        self.axis_mapper = PrototypeMacroMapper(self.embedder)
        self.regime_inferer = RegimeInferer()
        self.asset_mapper = CrossAssetMapper()

    def run(
        self,
        query: str,
        *,
        feed_urls: list[str] | None = None,
        max_articles: int | None = None,
        use_history: bool = True,
    ) -> DynamicResearchReport:
        if max_articles and max_articles != self.retriever.max_articles:
            self.retriever = MacroNewsRetriever(max_articles)

        observed_at = datetime.now(UTC)
        retrieval = self.retriever.retrieve(query, feed_urls=feed_urls)
        if not retrieval.items:
            raise RuntimeError("No news items were retrieved for the query.")

        events = self.normalizer.normalize(retrieval.items)
        embeddings = self.embedder.encode([event.analysis_text() for event in events])
        candidates = self.clusterer.cluster(events, embeddings)
        history = self._history_store(use_history)

        themes: list[DynamicTheme] = []
        resolved: list[tuple[ThemeCandidate, str, Any]] = []
        for candidate in candidates:
            theme_id, metrics = history.resolve(
                candidate,
                total_events=len(events),
                observed_at=observed_at,
            )
            macro_vector, mapping_confidence = self.axis_mapper.map(candidate)
            themes.append(
                DynamicTheme(
                    theme_id=theme_id,
                    label=candidate.label,
                    event_ids=candidate.event_ids,
                    representative_summaries=candidate.representative_summaries,
                    metrics=metrics,
                    macro_vector=macro_vector,
                    mapping_confidence=mapping_confidence,
                )
            )
            resolved.append((candidate, theme_id, metrics))

        regime = self.regime_inferer.infer(themes)
        asset_implications = self.asset_mapper.map(regime)
        narrative = self.narrator.narrate(query, regime, themes, asset_implications)
        sources = sorted(
            {event.url or event.source for event in events if event.url or event.source}
        )

        report = DynamicResearchReport(
            query=query,
            generated_at=observed_at,
            regime=regime,
            themes=themes,
            asset_implications=asset_implications,
            events=events,
            sources=sources,
            tools_used=[
                *retrieval.tools_used,
                "ChatOpenAI",
                "PydanticOutputParser",
                self.embedder.name,
                "AgglomerativeClustering",
                "PrototypeMacroMapper",
                "CrossAssetMapper",
            ],
            **narrative.model_dump(),
        )

        if use_history:
            for candidate, theme_id, metrics in resolved:
                history.append(candidate, theme_id, metrics, observed_at)
            history.save(observed_at)

        return report

    def run_and_save(
        self,
        query: str,
        *,
        feed_urls: list[str] | None = None,
        max_articles: int | None = None,
        use_history: bool = True,
        output_dir: Path | None = None,
        output_format: str = "both",
    ) -> tuple[DynamicResearchReport, list[Path]]:
        report = self.run(
            query,
            feed_urls=feed_urls,
            max_articles=max_articles,
            use_history=use_history,
        )
        paths = save_report(
            report,
            output_dir=output_dir or self.settings.output_dir,
            output_format=output_format,
        )
        return report, paths

    def _history_store(self, use_history: bool) -> ThemeHistoryStore:
        store = ThemeHistoryStore(
            self.settings.theme_history_path,
            lookback_days=self.settings.theme_lookback_days,
            match_similarity=self.settings.theme_match_similarity,
            persistence_target_runs=self.settings.persistence_target_runs,
            breadth_target_sources=self.settings.breadth_target_sources,
        )
        if not use_history:
            store.data = ThemeHistoryData()
        return store
