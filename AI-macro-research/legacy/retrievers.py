from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from macro_research_assistant.schemas import NewsItem


class RetrievalBundle(BaseModel):
    items: list[NewsItem] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)


def deduplicate_news(items: Iterable[NewsItem], limit: int) -> list[NewsItem]:
    """Deduplicate by URL first, then by normalized title."""

    seen: set[str] = set()
    deduped: list[NewsItem] = []

    for item in items:
        key = item.url or item.title.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= limit:
            break

    return deduped


def source_from_url(url: str | None) -> str:
    if not url:
        return "web"
    netloc = urlparse(url).netloc.lower()
    return netloc.removeprefix("www.") or "web"


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


class DuckDuckGoNewsRetriever:
    """Financial/macro web retrieval using LangChain community DuckDuckGo utilities."""

    def __init__(self, max_results: int = 10):
        self.max_results = max_results

    def search(self, query: str) -> RetrievalBundle:
        try:
            from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
        except ImportError as exc:
            raise RuntimeError(
                "langchain-community is required for DuckDuckGo retrieval. "
                "Install the project with `pip install -e .`."
            ) from exc

        wrapper = DuckDuckGoSearchAPIWrapper()
        raw_results = wrapper.results(query, max_results=self.max_results)

        items = [
            NewsItem(
                title=result.get("title") or result.get("snippet") or "Untitled result",
                url=result.get("link"),
                source=source_from_url(result.get("link")),
                snippet=result.get("snippet", ""),
            )
            for result in raw_results
        ]
        return RetrievalBundle(items=items, tools_used=["DuckDuckGoSearchAPIWrapper"])


class RSSFeedRetriever:
    """Optional RSS ingestion for central banks, data providers, or market news feeds."""

    def __init__(self, max_entries_per_feed: int = 5):
        self.max_entries_per_feed = max_entries_per_feed

    def fetch(self, feed_urls: Iterable[str]) -> RetrievalBundle:
        try:
            import feedparser
        except ImportError as exc:
            raise RuntimeError(
                "feedparser is required for RSS retrieval. "
                "Install the project with `pip install -e .`."
            ) from exc

        items: list[NewsItem] = []
        for feed_url in feed_urls:
            parsed = feedparser.parse(feed_url)
            feed_title = parsed.feed.get("title") or source_from_url(feed_url)

            for entry in parsed.entries[: self.max_entries_per_feed]:
                url = entry.get("link")
                published = _parse_datetime(entry.get("published") or entry.get("updated"))
                items.append(
                    NewsItem(
                        title=entry.get("title", "Untitled RSS entry"),
                        url=url,
                        source=feed_title,
                        published_at=published,
                        snippet=entry.get("summary", ""),
                    )
                )

        return RetrievalBundle(items=items, tools_used=["feedparser"])


class MacroNewsRetriever:
    """Coordinates web and optional RSS retrieval for the research workflow."""

    def __init__(self, max_articles: int):
        self.max_articles = max_articles
        self.search_retriever = DuckDuckGoNewsRetriever(max_results=max_articles)
        self.rss_retriever = RSSFeedRetriever(max_entries_per_feed=max(1, max_articles // 2))

    def retrieve(self, query: str, feed_urls: Iterable[str] | None = None) -> RetrievalBundle:
        search_query = (
            f"{query} macro economy markets central bank inflation rates FX commodities latest news"
        )
        search_bundle = self.search_retriever.search(search_query)

        bundles = [search_bundle]
        if feed_urls:
            bundles.append(self.rss_retriever.fetch(feed_urls))

        items = deduplicate_news(
            (item for bundle in bundles for item in bundle.items),
            limit=self.max_articles,
        )
        tools_used = sorted({tool for bundle in bundles for tool in bundle.tools_used})

        return RetrievalBundle(items=items, tools_used=tools_used)
