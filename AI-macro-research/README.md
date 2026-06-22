# Dynamic Macro Research Extension

An extended version of the original AI Macro Research Assistant. It combines LLM-based news normalization with NLP/ML theme discovery, dynamic narrative metrics, macro-regime inference, and transparent cross-asset research mapping.

The original copied implementation is preserved in `legacy/`.

## Pipeline

```text
Web search and RSS feeds
        ↓
LLM event normalization and summarization
        ↓
Text embeddings
        ↓
Dynamic clustering of related events
        ↓        
Multi-label mapping (growth, inflation, policy, liquidity, and risk sentiment)
        ↓
Macro-regime inference and cross-asset research report
```


## Project Structure

```text
.
├── legacy/                         # preserved original package files
├── src/macro_research_extension/
│   ├── clustering.py               # dynamic event clustering
│   ├── embeddings.py               # hashing or transformer embeddings
│   ├── history.py                  # theme matching and temporal metrics
│   ├── llm.py                      # event normalization and report narration
│   ├── mapping.py                  # transparent cross-asset mapping
│   ├── regimes.py                  # macro-axis and regime inference
│   ├── reporting.py                # Markdown and JSON reports
│   ├── retrievers.py               # online search and RSS retrieval
│   ├── schemas.py                  # Pydantic contracts
│   └── workflow.py                 # end-to-end orchestration
├── tests/
└── pyproject.toml
```

## Setup

```bash
cd "/Users/emanuelesaccoliti/VS Code/_Archive/AI_Macro_ResearchAssistant/src/macro_research_assistant extension"
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Add `OPENAI_API_KEY` to `.env`.

The lightweight default uses `HashingVectorizer` embeddings. For transformer embeddings:

```bash
pip install -e ".[dev,transformers]"
```

Then set:

```text
EMBEDDING_PROVIDER=sentence-transformer
```

## Usage

```bash
python -m macro_research_extension \
  "US inflation, Fed policy and cross-asset implications" \
  --max-articles 30
```

Add RSS sources:

```bash
python -m macro_research_extension \
  "global monetary policy divergence" \
  --feed-url "https://www.federalreserve.gov/feeds/press_all.xml"
```

Theme history is stored in `data/theme_history.json`. To run without reading or updating it:

```bash
python -m macro_research_extension "China growth and commodities" --no-history
```

## Outputs

- Normalized events with entities, regions, key facts, and LLM confidence.
- Dynamic themes with interpretable narrative metrics.
- Continuous macro state vector and inferred regime.
- Conditional cross-asset implications for equities, government bonds, USD, commodities, and credit.
- Markdown and machine-readable JSON reports.

## Validation

```bash
python -m compileall src tests
ruff check .
pytest
```


## Disclaimer

This project is intended for research and educational purposes only. It does not constitute investment advice, financial advice, trading advice, or a recommendation to buy, sell, or hold any asset. Model outputs should not be used for live trading or investment decisions without independent verification and professional judgment.

