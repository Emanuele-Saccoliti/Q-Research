from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import BaseModel, Field

from macro_research_extension.schemas import NewsItem


class RetrievalBundle(BaseModel):
    items: list[NewsItem] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)


def source_from_url(url: str | None) -> str:
    if not url:
        return "web"
    return urlparse(url).netloc.lower().removeprefix("www.") or "web"


def canonical_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    tracking_prefixes = ("utm_", "ref", "source", "campaign")
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query)
        if not key.lower().startswith(tracking_prefixes)
    ]
    return urlunparse(
        (parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), "", urlencode(query), "")
    )


def _title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def deduplicate_news(items: Iterable[NewsItem], limit: int) -> list[NewsItem]:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    deduped: list[NewsItem] = []

    for item in items:
        url_key = canonical_url(item.url)
        title_key = _title_key(item.title)
        if (url_key and url_key in seen_urls) or title_key in seen_titles:
            continue
        if url_key:
            seen_urls.add(url_key)
        seen_titles.add(title_key)
        deduped.append(item.model_copy(update={"url": url_key or item.url}))
        if len(deduped) >= limit:
            break

    return deduped


def build_search_queries(query: str) -> list[str]:
    return [
        f"{query} latest macroeconomic financial market news",
        f"{query} central bank economic data inflation growth rates FX",
        f"{query} cross asset implications equities bonds currencies commodities credit",
    ]


class DuckDuckGoNewsRetriever:
    def __init__(self, max_results: int):
        self.max_results = max_results

    def search(self, query: str) -> RetrievalBundle:
        try:
            from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
        except ImportError as exc:
            raise RuntimeError(
                "Install the project dependencies to use DuckDuckGo retrieval."
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


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


def _strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()


class RSSFeedRetriever:
    def __init__(self, max_entries_per_feed: int):
        self.max_entries_per_feed = max_entries_per_feed

    def fetch(self, feed_urls: Iterable[str]) -> RetrievalBundle:
        try:
            import feedparser
        except ImportError as exc:
            raise RuntimeError("Install feedparser to use RSS retrieval.") from exc

        items: list[NewsItem] = []
        for feed_url in feed_urls:
            parsed = feedparser.parse(feed_url)
            source = parsed.feed.get("title") or source_from_url(feed_url)
            for entry in parsed.entries[: self.max_entries_per_feed]:
                items.append(
                    NewsItem(
                        title=entry.get("title", "Untitled RSS entry"),
                        url=entry.get("link"),
                        source=source,
                        published_at=_parse_datetime(
                            entry.get("published") or entry.get("updated")
                        ),
                        snippet=_strip_html(entry.get("summary", "")),
                    )
                )

        return RetrievalBundle(items=items, tools_used=["feedparser"])


class MacroNewsRetriever:
    def __init__(self, max_articles: int):
        self.max_articles = max_articles
        per_query = max(3, (max_articles + 2) // 3)
        self.search_retriever = DuckDuckGoNewsRetriever(max_results=per_query)
        self.rss_retriever = RSSFeedRetriever(max_entries_per_feed=max(3, max_articles // 3))

    def retrieve(self, query: str, feed_urls: Iterable[str] | None = None) -> RetrievalBundle:
        bundles = [self.search_retriever.search(item) for item in build_search_queries(query)]
        if feed_urls:
            bundles.append(self.rss_retriever.fetch(feed_urls))

        items = deduplicate_news(
            (item for bundle in bundles for item in bundle.items),
            limit=self.max_articles,
        )
        tools_used = sorted({tool for bundle in bundles for tool in bundle.tools_used})
        return RetrievalBundle(items=items, tools_used=tools_used)

