from __future__ import annotations

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from macro_research_assistant.config import Settings
from macro_research_assistant.schemas import MacroAnalysisDraft, NewsItem

SYSTEM_PROMPT = """You are a senior macro research analyst.
Use only the supplied retrieved context. Do not invent data, dates, prices, or sources.
Transform noisy news into concise research signals for a financial markets workflow.
Emphasize policy, inflation, growth, liquidity, FX, rates, commodities, and
cross-asset implications.
If the evidence is thin or mixed, say so and lower confidence.
Return only valid JSON that follows the requested schema.
"""


USER_PROMPT = """Research query:
{query}

Retrieved context:
{news_context}

Output requirements:
- Executive summary: 4-7 sentences.
- Key themes: short bullets as strings.
- Signals: 3-6 structured signals when possible.
- Evidence must cite item titles or source names from the context.
- Confidence must be between 0 and 1.
- Risks to watch should be actionable for an analyst.

{format_instructions}
"""


class MacroLLMAnalyzer:
    """LangChain + OpenAI + Pydantic structured extraction."""

    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required for LLM analysis. Add it to .env or key.env."
            )

        self.parser = PydanticOutputParser(pydantic_object=MacroAnalysisDraft)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("human", USER_PROMPT),
            ]
        ).partial(format_instructions=self.parser.get_format_instructions())
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=settings.temperature,
            timeout=settings.request_timeout_seconds,
        )
        self.chain = self.prompt | self.llm | self.parser

    def analyze(self, query: str, news_items: list[NewsItem]) -> MacroAnalysisDraft:
        return self.chain.invoke(
            {
                "query": query,
                "news_context": "\n".join(
                    f"{index}. {item.context_line()}" for index, item in enumerate(news_items, 1)
                ),
            }
        )
