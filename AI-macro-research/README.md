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
Theme attention, momentum, breadth, novelty, and persistence
        ↓
Multi-label mapping to growth, inflation, policy, liquidity, and risk sentiment
        ↓
Macro-regime inference and cross-asset research report
```

## What Is Dynamic

- The number of themes is not fixed in advance. Agglomerative clustering discovers groups from the current event set.
- Theme IDs are matched to historical cluster centroids, allowing narratives to be followed across runs.
- Attention measures the current share of deduplicated events assigned to a theme.
- Momentum compares current attention with the theme's historical distribution.
- Breadth measures coverage and diversity across independent sources.
- Novelty measures semantic distance from historical theme centroids.
- Persistence measures how frequently a matched theme remains active across recent runs.

## Macro Mapping

Each theme is mapped to a continuous macro vector:

```text
Growth:         contraction -1 ←→ +1 expansion
Inflation:      disinflation -1 ←→ +1 inflation
Policy:         easing -1 ←→ +1 tightening
Liquidity:      contraction -1 ←→ +1 expansion
Risk sentiment: risk-off -1 ←→ +1 risk-on
```

The default implementation uses semantic anchor prototypes. It is intentionally replaceable with a supervised multi-label classifier once a reviewed training set is available.

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
│   ├── retrievers.py               # DuckDuckGo and RSS retrieval
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

## Limitations

- Prototype-based macro mapping is a semantic baseline, not a trained alpha model.
- Cross-asset coefficients encode transparent research priors and require historical validation.
- Search snippets may omit context or publication timestamps.
- Reliable regime research should combine narrative features with structured macro and market data.

## Disclaimer

This project is intended for research and educational purposes only. It does not constitute investment advice, financial advice, trading advice, or a recommendation to buy, sell, or hold any asset. Model outputs should not be used for live trading or investment decisions without independent verification and professional judgment.

