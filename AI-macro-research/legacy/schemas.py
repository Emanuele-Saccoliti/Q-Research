from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    """Normalized item retrieved from web search or RSS."""

    title: str = Field(min_length=1)
    url: str | None = None
    source: str = "unknown"
    published_at: datetime | None = None
    snippet: str = ""

    def context_line(self) -> str:
        published = self.published_at.date().isoformat() if self.published_at else "date unknown"
        url = f" ({self.url})" if self.url else ""
        snippet = f" - {self.snippet}" if self.snippet else ""
        return f"[{self.source} | {published}] {self.title}{url}{snippet}"


class MacroSignal(BaseModel):
    """Structured signal extracted from retrieved macro evidence."""

    theme: str = Field(description="Concise macro theme, e.g. Fed repricing or China demand.")
    direction: Literal[
        "risk_on",
        "risk_off",
        "hawkish",
        "dovish",
        "inflationary",
        "disinflationary",
        "growth_positive",
        "growth_negative",
        "mixed",
        "neutral",
    ]
    time_horizon: Literal["intraday", "1w", "1m", "3m+", "unclear"] = "unclear"
    affected_assets: list[str] = Field(
        default_factory=list,
        description="Asset classes, regions, sectors, FX pairs, rates, or commodities affected.",
    )
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    research_note: str = Field(description="Why this signal matters for macro research.")


class MacroAnalysisDraft(BaseModel):
    """LLM-generated structured analysis before workflow metadata is attached."""

    executive_summary: str
    key_themes: list[str] = Field(default_factory=list)
    signals: list[MacroSignal] = Field(default_factory=list)
    market_implications: list[str] = Field(default_factory=list)
    risks_to_watch: list[str] = Field(default_factory=list)


class MacroResearchReport(MacroAnalysisDraft):
    """Final persisted report."""

    query: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    news_items: list[NewsItem] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)

    @property
    def source_count(self) -> int:
        return len(self.sources)
