from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from macro_research_assistant.config import Settings
from macro_research_assistant.llm import MacroLLMAnalyzer
from macro_research_assistant.reporting import save_report
from macro_research_assistant.retrievers import MacroNewsRetriever
from macro_research_assistant.schemas import MacroResearchReport


class MacroResearchWorkflow:
    """End-to-end retrieval, LLM analysis, structured extraction, and report writing."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.retriever = MacroNewsRetriever(max_articles=settings.max_articles)
        self.analyzer = MacroLLMAnalyzer(settings=settings)

    def run(
        self,
        query: str,
        *,
        feed_urls: list[str] | None = None,
        max_articles: int | None = None,
    ) -> MacroResearchReport:
        if max_articles and max_articles != self.retriever.max_articles:
            self.retriever = MacroNewsRetriever(max_articles=max_articles)

        retrieval = self.retriever.retrieve(query, feed_urls=feed_urls)
        analysis = self.analyzer.analyze(query, retrieval.items)

        sources = sorted(
            {
                item.url or item.source
                for item in retrieval.items
                if item.url or item.source
            }
        )

        return MacroResearchReport(
            query=query,
            generated_at=datetime.now(UTC),
            news_items=retrieval.items,
            sources=sources,
            tools_used=[
                *retrieval.tools_used,
                "ChatOpenAI",
                "PydanticOutputParser",
                "LangChain ChatPromptTemplate",
            ],
            **analysis.model_dump(),
        )

    def run_and_save(
        self,
        query: str,
        *,
        feed_urls: list[str] | None = None,
        max_articles: int | None = None,
        output_dir: Path | None = None,
        output_format: str = "both",
    ) -> tuple[MacroResearchReport, list[Path]]:
        report = self.run(query, feed_urls=feed_urls, max_articles=max_articles)
        paths = save_report(
            report,
            output_dir=output_dir or self.settings.output_dir,
            output_format=output_format,
        )
        return report, paths
