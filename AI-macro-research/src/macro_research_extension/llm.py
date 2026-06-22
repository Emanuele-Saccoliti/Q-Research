from __future__ import annotations

import json

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from macro_research_extension.config import Settings
from macro_research_extension.schemas import (
    AssetImplication,
    DynamicTheme,
    EventBatch,
    ExtractedEvent,
    MacroRegime,
    NarrativeDraft,
    NewsItem,
    NormalizedEvent,
)

EVENT_SYSTEM_PROMPT = """You normalize macro-financial news for an NLP pipeline.
Use only the supplied items. Preserve numeric facts and distinguish actual, consensus, and previous.
Do not infer market prices, entities, or facts that are absent. Return one event for every item_id.
Return only valid JSON matching the requested schema.
"""


EVENT_USER_PROMPT = """Normalize these retrieved items:
{items}

Requirements:
- summary: one or two factual sentences, not investment advice;
- event_type: choose the closest allowed category;
- entities and regions: explicit mentions only;
- key_facts: concise evidence retained from the source text;
- llm_confidence: confidence that the source text supports the extraction.

{format_instructions}
"""


REPORT_SYSTEM_PROMPT = """You are a macro research editor.
Explain the supplied NLP/ML outputs without adding facts or pretending they are trading signals.
Use conditional language for asset implications. Return only valid JSON matching the schema.
"""


REPORT_USER_PROMPT = """Research query: {query}

Inferred regime:
{regime}

Dynamic themes:
{themes}

Cross-asset implications:
{assets}

Write a concise executive summary, 3-6 key findings, and 2-5 risks or limitations.
{format_instructions}
"""


def _chat_model(settings: Settings) -> ChatOpenAI:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required. Add it to .env or key.env.")
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=settings.temperature,
        timeout=settings.request_timeout_seconds,
    )


class LLMEventNormalizer:
    def __init__(self, settings: Settings):
        self.parser = PydanticOutputParser(pydantic_object=EventBatch)
        self.prompt = ChatPromptTemplate.from_messages(
            [("system", EVENT_SYSTEM_PROMPT), ("human", EVENT_USER_PROMPT)]
        ).partial(format_instructions=self.parser.get_format_instructions())
        self.chain = self.prompt | _chat_model(settings) | self.parser

    def normalize(self, items: list[NewsItem]) -> list[NormalizedEvent]:
        if not items:
            return []

        context = "\n".join(
            f"ITEM {index}: {item.context_line()[:1800]}" for index, item in enumerate(items)
        )
        batch = self.chain.invoke({"items": context})
        extracted_by_id = {
            event.item_id: event for event in batch.events if 0 <= event.item_id < len(items)
        }

        normalized: list[NormalizedEvent] = []
        for item_id, item in enumerate(items):
            extracted = extracted_by_id.get(item_id) or ExtractedEvent(
                item_id=item_id,
                summary=item.snippet or item.title,
                event_type="other",
                key_facts=[item.title],
                llm_confidence=0.2,
            )
            payload = extracted.model_dump()
            payload.update(
                title=item.title,
                source=item.source,
                url=item.url,
                published_at=item.published_at,
            )
            normalized.append(NormalizedEvent(**payload))

        return normalized


class LLMReportNarrator:
    def __init__(self, settings: Settings):
        self.parser = PydanticOutputParser(pydantic_object=NarrativeDraft)
        self.prompt = ChatPromptTemplate.from_messages(
            [("system", REPORT_SYSTEM_PROMPT), ("human", REPORT_USER_PROMPT)]
        ).partial(format_instructions=self.parser.get_format_instructions())
        self.chain = self.prompt | _chat_model(settings) | self.parser

    def narrate(
        self,
        query: str,
        regime: MacroRegime,
        themes: list[DynamicTheme],
        assets: list[AssetImplication],
    ) -> NarrativeDraft:
        return self.chain.invoke(
            {
                "query": query,
                "regime": json.dumps(regime.model_dump(mode="json"), indent=2),
                "themes": json.dumps(
                    [theme.model_dump(mode="json") for theme in themes], indent=2
                ),
                "assets": json.dumps(
                    [asset.model_dump(mode="json") for asset in assets], indent=2
                ),
            }
        )

