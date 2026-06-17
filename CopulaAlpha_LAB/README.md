# CopulaAlpha LAB
This GitHub Repo builds a complete alpha research workflow:

```text
market data -> pair selection -> rolling copula signals -> position sizing -> backtest -> validation
```

The core idea is to identify when one ETF appears statistically rich or cheap relative to another ETF. If asset A looks rich relative to asset B, the strategy shorts A and goes long B. If asset A looks cheap relative to B, the strategy goes long A and shorts B.

This is not meant to be a production trading system. It is a research framework for testing signal quality, robustness, transaction costs, turnover, and out-of-sample behavior.


## Project Summary
The current version focuses on a mixture copula model built from three components:

- Gaussian copula for stable linear dependence.
- Student-t copula for symmetric tail dependence.
- Clayton copula for lower-tail dependence.

The pipeline processes daily adjusted close data from 2015 to 2026 across 42 ETFs, computes log returns, selects candidate ETF pairs, generates rolling copula mispricing signals, constructs market-neutral long/short positions, and evaluates performance after transaction costs.


## Methodology
### 1. Data
The project uses adjusted close prices and converts them into daily log returns:

```python
returns = np.log(prices / prices.shift(1))
```

The processed datasets are saved in:

```text
data/processed/prices.csv
data/processed/returns.csv
```

### 2. Pair Selection
The project does not estimate copulas on every possible ETF pair. Instead, it first selects a cleaner universe of related pairs using only the training period.

The pair selection process includes:
- removing duplicated ETF pairs within selected overlap groups;
- requiring high return correlation;
- estimating a residual return spread;
- requiring the residual spread to be sufficiently volatile and mean-reverting.

The final selected pairs are saved in:

```text
data/processed/candidate_pairs.csv
```

### 3. Rolling Copula Signal
For each selected pair, the notebook estimates a rolling mixture copula using only past data. Returns are transformed into empirical ranks, then each copula component estimates conditional probabilities for each asset relative to the other.

The tradable score is a bidirectional mispricing index:

```text
positive score -> asset i rich, asset j cheap -> short i, long j
negative score -> asset i cheap, asset j rich -> long i, short j
```

Signals are saved in:

```text
results/mixture_only/pair_signals.csv
```

### 4. Position Sizing
The trading layer uses equal-slot position sizing.

Each active pair receives the same gross exposure slot:

```text
w_pair = 1 / N_max
```

The strategy is built to be dollar-neutral at the pair level, with one long leg and one short leg. The current version does not use beta-neutral or volatility-targeted sizing; those are natural extensions.

### 5. Risk Controls
The backtest includes several basic risk and realism controls:

- pair-specific entry and exit thresholds;
- maximum holding period;
- maximum daily turnover constraint;
- one-day signal shift to avoid look-ahead bias;
- transaction costs in basis points;
- gross and net exposure monitoring;
- drawdown and turnover diagnostics;
- train, validation, and test period evaluation.


## How To Use
Create and activate a Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Open the main notebook:

```text
notebooks/v3_english.ipynb
```

Run the notebook from top to bottom. The notebook will either use the cached processed data or download fresh market data with `yfinance` if configured to refresh.

The main configuration lives in the `MVPConfig` dataclass inside the notebook.

## Results

| Metric | Value |
|---|---:|
| Gross annualized return | 1.06% |
| Gross annualized volatility | 1.03% |
| Gross Sharpe ratio | 1.03 |
| Gross max drawdown | -1.36% |
| Net annualized return | 0.62% |
| Net annualized volatility | 1.03% |
| Net Sharpe ratio | 0.61 |
| Net max drawdown | -1.89% |
| Average daily turnover | 6.88% |
| Average gross exposure | 3.44% |
| Average net exposure | 0.00% |
| Market beta to SPY | 0.003 |
| Average IC | 0.038 |
| Average rank IC | 0.039 |


## Interpretation
The project shows that rolling copula features can produce a measurable relative-value signal across selected ETF pairs. The positive IC and low market beta suggest that the signal is not simply a directional equity market bet.


## Disclaimer
This project is for quantitative research and educational purposes only. It is not investment advice and should not be treated as a live trading system without additional validation, execution modeling, risk management, and operational controls.

