from pathlib import Path

from macro_research_extension.config import Settings
from macro_research_extension.embeddings import HashingEmbedder
from macro_research_extension.retrievers import RetrievalBundle
from macro_research_extension.schemas import NarrativeDraft, NewsItem, NormalizedEvent
from macro_research_extension.workflow import DynamicMacroResearchWorkflow


class FakeRetriever:
    max_articles = 4

    def retrieve(self, query: str, feed_urls=None):
        del query, feed_urls
        return RetrievalBundle(
            items=[
                NewsItem(title="CPI rises", source="source-a", snippet="Inflation rose."),
                NewsItem(title="Prices sticky", source="source-b", snippet="Core prices rose."),
                NewsItem(title="PMI weakens", source="source-c", snippet="Growth weakened."),
                NewsItem(title="Demand slows", source="source-d", snippet="Demand contracted."),
            ],
            tools_used=["fake-retriever"],
        )


class FakeNormalizer:
    def normalize(self, items):
        return [
            NormalizedEvent(
                item_id=index,
                title=item.title,
                source=item.source,
                summary=item.snippet,
                event_type="economic_data_release",
                llm_confidence=0.9,
            )
            for index, item in enumerate(items)
        ]


class FakeNarrator:
    def narrate(self, query, regime, themes, assets):
        del query, regime, themes, assets
        return NarrativeDraft(
            executive_summary="A test macro narrative.",
            key_findings=["Themes were discovered."],
            risks_to_watch=["Synthetic input."],
        )


def test_workflow_runs_without_web_or_llm(tmp_path):
    settings = Settings(
        max_articles=4,
        theme_history_path=Path(tmp_path / "history.json"),
        output_dir=Path(tmp_path / "reports"),
    )
    workflow = DynamicMacroResearchWorkflow(
        settings,
        retriever=FakeRetriever(),
        normalizer=FakeNormalizer(),
        narrator=FakeNarrator(),
        embedder=HashingEmbedder(dimensions=128),
    )

    report = workflow.run("test query", use_history=False)

    assert len(report.events) == 4
    assert report.themes
    assert report.asset_implications
    assert "AgglomerativeClustering" in report.tools_used

