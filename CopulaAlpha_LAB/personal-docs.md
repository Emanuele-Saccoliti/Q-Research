# CopulaAlpha LAB

CopulaAlpha LAB is a quantitative research project for testing whether rolling copula models can generate stable relative-value signals across related liquid ETFs.

The project builds a complete alpha research workflow:

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

- removing broad benchmark ETFs that are too efficient or too overlapping;
- blocking clearly duplicated ETF pairs within selected overlap groups;
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
- expected-edge filter estimated only on the training set;
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

The main configuration lives in the `MVPConfig` dataclass inside the notebook. Important parameters include:

```text
rolling_window
max_candidate_pairs
top_n_pairs
entry_quantile
exit_quantile
max_holding_days
max_daily_turnover
cost_bps
```

## Outputs

The project writes research artifacts under:

```text
results/mixture_only/
```

Main files:

```text
backtest.csv
daily_positions.csv
pair_signals.csv
pair_expected_edges.csv
daily_ic.csv
performance_summary.csv
performance_by_period.csv
simple_v2_grid_small.csv
```

Diagnostic plots:

```text
results/mixture_only/plots/equity_curve.png
results/mixture_only/plots/drawdown.png
results/mixture_only/plots/turnover.png
```

## Results

Main full-period results:

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

Performance by period:

| Period | Annualized Return | Volatility | Sharpe | Max Drawdown |
|---|---:|---:|---:|---:|
| Train | 0.21% | 0.77% | 0.28 | -1.89% |
| Validation | 2.36% | 1.65% | 1.42 | -0.87% |
| Test | 0.24% | 0.89% | 0.28 | -1.46% |

The validation period is the strongest, while the test period remains positive but much weaker. This matters: the result should be read as a research signal with some predictive content, not as a finished strategy.

## Interpretation

The project shows that rolling copula features can produce a measurable relative-value signal across selected ETF pairs. The positive IC and low market beta suggest that the signal is not simply a directional equity market bet.

However, the edge is modest after costs, and the test-period Sharpe is materially lower than the validation-period Sharpe. The next research step is not to add more model complexity immediately, but to improve robustness:

- compare against a z-score pairs baseline;
- test sector-neutral pair selection;
- estimate ETF-specific costs;
- add beta-neutral position sizing;
- test volatility-targeted sizing;
- expand walk-forward validation;
- check whether the edge survives a larger universe.

## Repository Layout

```text
CopulaAlpha_LAB/
├── CIAO.md
├── README.md
├── requirements.txt
├── data/
│   └── processed/
├── notebooks/
│   └── v3_english.ipynb
└── results/
    └── mixture_only/
```

## Disclaimer

This project is for quantitative research and educational purposes only. It is not investment advice and should not be treated as a live trading system without additional validation, execution modeling, risk management, and operational controls.
