from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class NewsItem(BaseModel):
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


EventType = Literal[
    "economic_data_release",
    "central_bank_decision",
    "central_bank_communication",
    "fiscal_policy",
    "geopolitical_event",
    "commodity_supply_event",
    "market_stress",
    "research_outlook",
    "other",
]


class ExtractedEvent(BaseModel):
    """Fields produced by the LLM; source metadata is attached deterministically later."""

    item_id: int = Field(ge=0)
    summary: str = Field(min_length=10)
    event_type: EventType = "other"
    entities: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    key_facts: list[str] = Field(default_factory=list)
    actual: float | None = None
    consensus: float | None = None
    previous: float | None = None
    unit: str | None = None
    llm_confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class EventBatch(BaseModel):
    events: list[ExtractedEvent]


class NormalizedEvent(ExtractedEvent):
    title: str
    source: str
    url: str | None = None
    published_at: datetime | None = None

    def analysis_text(self) -> str:
        facts = "; ".join(self.key_facts)
        entities = ", ".join([*self.regions, *self.entities])
        return " | ".join(
            part
            for part in [self.event_type.replace("_", " "), self.summary, facts, entities]
            if part
        )


class MacroAxisVector(BaseModel):
    """Signed macro impulses. Each field is constrained to [-1, 1]."""

    growth: float = Field(default=0.0, ge=-1.0, le=1.0)
    inflation: float = Field(default=0.0, ge=-1.0, le=1.0)
    policy: float = Field(default=0.0, ge=-1.0, le=1.0)
    liquidity: float = Field(default=0.0, ge=-1.0, le=1.0)
    risk_sentiment: float = Field(default=0.0, ge=-1.0, le=1.0)


class ThemeMetrics(BaseModel):
    attention: float = Field(ge=0.0, le=1.0)
    momentum_zscore: float
    breadth: float = Field(ge=0.0, le=1.0)
    novelty: float = Field(ge=0.0, le=1.0)
    persistence: float = Field(ge=0.0, le=1.0)
    source_count: int = Field(ge=0)
    article_count: int = Field(ge=1)


class DynamicTheme(BaseModel):
    theme_id: str
    label: str
    event_ids: list[int]
    representative_summaries: list[str]
    metrics: ThemeMetrics
    macro_vector: MacroAxisVector
    mapping_confidence: float = Field(ge=0.0, le=1.0)


class MacroRegime(BaseModel):
    name: Literal[
        "goldilocks",
        "reflation",
        "stagflation_pressure",
        "recession_disinflation",
        "policy_tightening",
        "policy_easing",
        "risk_off",
        "mixed_transition",
    ]
    state: MacroAxisVector
    confidence: float = Field(ge=0.0, le=1.0)
    dominant_themes: list[str] = Field(default_factory=list)


class AssetImplication(BaseModel):
    asset_class: str
    direction: Literal["positive", "negative", "mixed"]
    score: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    drivers: list[str] = Field(default_factory=list)


class NarrativeDraft(BaseModel):
    executive_summary: str
    key_findings: list[str] = Field(default_factory=list)
    risks_to_watch: list[str] = Field(default_factory=list)


class DynamicResearchReport(NarrativeDraft):
    query: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    regime: MacroRegime
    themes: list[DynamicTheme] = Field(default_factory=list)
    asset_implications: list[AssetImplication] = Field(default_factory=list)
    events: list[NormalizedEvent] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)

