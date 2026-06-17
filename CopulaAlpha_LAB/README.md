# Copula-Based Relative-Value Alpha Engine

## Overview

This project develops a Python-based quantitative research pipeline for generating **relative-value alpha signals** from the dependence structure of liquid financial assets.

The core idea is to identify when one asset appears statistically **rich** or **cheap** relative to another asset, using rolling copula models estimated from market data.

The project is designed to demonstrate practical quant research skills relevant to roles such as **Quantitative Research Intern**, especially in alpha research environments where the goal is to transform data into predictive signals and evaluate them rigorously.

---

## Project Objective

The objective is to build and backtest a full alpha research workflow:

```text
market data → pair selection → copula dependence estimation → mispricing signal → portfolio construction → backtest → validation
```

The strategy estimates rolling dependence between related assets and converts deviations from the expected dependence structure into market-neutral long/short signals.

Example:

```text
Asset A appears rich relative to Asset B → short A, long B
Asset A appears cheap relative to Asset B → long A, short B
```

The final output is not just a trading strategy, but a **research framework** for testing whether copula-based dependence features have predictive power.

---

## Why This Project Is Relevant for Quant Research

This project demonstrates:

- Python scripting for financial research.
- Data ingestion, cleaning and feature engineering.
- Statistical signal construction.
- Cross-sectional alpha mining.
- Rolling-window model estimation.
- Backtesting with no look-ahead bias.
- Transaction-cost-aware performance analysis.
- Out-of-sample validation.
- Robustness testing across parameters and model classes.

The project is particularly aligned with alpha research because it focuses on:

```text
signal quality
predictive power
IC / rank IC
turnover-adjusted returns
walk-forward validation
robustness
```

---

## Core Research Question

The main research question is:

> Can rolling copula dependence models extract stable relative-value signals from related financial assets?

A secondary research question is:

> Do richer dependence models, such as Student-t, Clayton or mixture copulas, improve out-of-sample alpha quality compared with a simple Gaussian copula baseline?

The goal is not to assume that more complex models are better.  
The goal is to test whether additional dependence structure creates real predictive value.

---

## Universe

The MVP version uses a liquid ETF universe.

Suggested universe:

```python
ETF_UNIVERSE = [
    "SPY", "QQQ", "IWM", "DIA",
    "EFA", "EEM", "VGK", "EWJ",
    "TLT", "IEF", "SHY", "LQD", "HYG",
    "GLD", "SLV", "USO", "DBA",
    "XLK", "XLF", "XLE", "XLY", "XLI",
    "XLP", "XLU", "XLV", "XLB", "XLRE",
    "SMH", "IBB", "KRE", "XRT", "ITA",
    "VNQ", "IYR", "DBC", "UUP", "FXE",
    "FXY", "FXB", "EWT", "EWG", "EWU",
]
```

Future extensions can use:

```text
300+ liquid US equities
sector-level peer groups
industry-neutral pairs
global equity universes
cross-asset ETF universes
```

---

## Methodology

### 1. Data

The project uses adjusted close prices and computes daily log returns:

```python
returns = np.log(prices / prices.shift(1))
```

The data pipeline should:

- download prices;
- clean missing observations;
- remove assets with insufficient history;
- save processed prices and returns;
- ensure all downstream calculations use only information available at the time.

---

### 2. Pair Selection

Instead of estimating copulas on all possible pairs, the pipeline first selects economically or statistically related pairs.

Possible pair selection rules:

```text
top correlated pairs
same-sector pairs
same-industry pairs
ETF thematic peers
cointegrated pairs
high Kendall tau pairs
```

MVP rule:

```text
For each asset, select the top K most correlated peers based on historical returns.
```

This reduces noise and makes the pair universe more realistic.

---

### 3. Copula-Based Dependence Modeling

A copula separates marginal distributions from the dependence structure.

For each asset pair, returns are transformed into empirical percentiles:

```python
u_i = rank(return_i) / (window + 1)
u_j = rank(return_j) / (window + 1)
```

This maps returns into pseudo-observations in `(0, 1)`.

The copula is then used to estimate how unusual one asset's move is conditional on the other asset's move.

---

## Copula Families

The project is structured in levels.

---

### Level 1: Gaussian Copula Baseline

The Gaussian copula is the first baseline model.

For a bivariate Gaussian copula:

```text
C(u, v; rho) = Phi_rho(Phi^{-1}(u), Phi^{-1}(v))
```

where:

- `Phi^{-1}` is the inverse standard normal CDF;
- `Phi_rho` is the bivariate normal CDF;
- `rho` is the dependence parameter.

The Gaussian copula is useful because it is:

```text
simple
fast
stable
interpretable
harder to overfit
good as a baseline
```

However, it does not capture true tail dependence.

---

### Level 2: Student-t Copula

The Student-t copula extends the Gaussian copula by allowing heavier tails.

It can capture symmetric tail dependence:

```text
assets move together more strongly during extreme events
```

This is useful for:

```text
equity indices
credit ETFs
high-volatility regimes
crisis periods
crypto-like assets
```

The t-copula has two main parameters:

```text
rho: dependence / correlation parameter
nu: degrees of freedom
```

Lower `nu` means heavier tails.

---

### Level 3: Clayton Copula

The Clayton copula is an Archimedean copula that captures **lower-tail dependence**.

It is useful when assets become more dependent during downside moves:

```text
assets crash together more than they rise together
```

This is especially relevant for:

```text
equities
credit
bank stocks
risk-off assets
high yield
```

Clayton can be useful when downside co-movement is the main dependence feature.

---

### Level 4: Mixture Copula

A mixture copula combines multiple copulas:

```text
C_mix(u, v) = w_1 C_1(u, v) + w_2 C_2(u, v) + ... + w_K C_K(u, v)
```

with:

```text
w_k >= 0
sum_k w_k = 1
```

For this project, the preferred mixture is:

```text
C_mix = w_Gaussian C_Gaussian + w_t C_t + w_Clayton C_Clayton
```

Interpretation:

| Component | Role |
|---|---|
| Gaussian copula | normal co-movement |
| Student-t copula | symmetric tail dependence |
| Clayton copula | downside crash dependence |

The mixture copula can be interpreted as a simple regime-aware dependence model:

```text
normal market dependence
extreme co-movement dependence
downside crash dependence
```

The mixture model should only be used after simpler baselines are implemented and validated.

---

## Elliptical vs Archimedean Copulas

This project compares two broad copula classes.

| Class | Examples | Main Use |
|---|---|---|
| Elliptical | Gaussian, Student-t | correlation-style dependence and symmetric tail dependence |
| Archimedean | Clayton, Gumbel, Frank | flexible asymmetric tail dependence |

### Elliptical Copulas

Elliptical copulas come from multivariate elliptical distributions.

They are natural when dependence is mostly symmetric and correlation-like.

Examples:

```text
Gaussian copula
Student-t copula
```

### Archimedean Copulas

Archimedean copulas are built through a generator function.

They are useful when the dependence structure is asymmetric.

Examples:

```text
Clayton: lower-tail dependence
Gumbel: upper-tail dependence
Frank: symmetric dependence without tail dependence
```

For this project, the main Archimedean copula of interest is Clayton, because downside dependence is often more relevant in financial markets.

---

## Copula Selection

Copula selection should not be based on theoretical elegance.

It should be based on:

```text
statistical fit
out-of-sample predictive power
robustness
interpretability
turnover-adjusted performance
```

The model selection process should compare:

```text
Gaussian copula
Student-t copula
Clayton copula
Gaussian + Student-t + Clayton mixture copula
```

Evaluation metrics:

```text
conditional log-likelihood
AIC / BIC
information coefficient
rank information coefficient
out-of-sample Sharpe
transaction-cost-adjusted Sharpe
max drawdown
turnover
stability across periods
```

Final selection rule:

> Choose the simplest copula model that produces stable out-of-sample predictive value.

This means the mixture copula should only be preferred if it improves out-of-sample signal quality after costs and robustness checks.

---

## Mispricing Signal

For a Gaussian copula, the conditional distribution is:

```text
z_i = Phi^{-1}(u_i)
z_j = Phi^{-1}(u_j)
z_i | z_j ~ N(rho z_j, 1 - rho^2)
```

The conditional probability is:

```text
conditional_prob = Phi((z_i - rho z_j) / sqrt(1 - rho^2))
```

The mispricing score is:

```text
mispricing_score = conditional_prob - 0.5
```

Interpretation:

```text
mispricing_score > 0 → asset i is rich relative to asset j
mispricing_score < 0 → asset i is cheap relative to asset j
```

Trading rule:

```text
if mispricing_score > threshold:
    short asset_i
    long asset_j

if mispricing_score < -threshold:
    long asset_i
    short asset_j
```

For mixture copulas, the conditional probability can be estimated as a weighted combination of the conditional probabilities from the component copulas:

```text
conditional_prob_mix =
    w_Gaussian * conditional_prob_Gaussian
  + w_t        * conditional_prob_t
  + w_Clayton  * conditional_prob_Clayton
```

Then:

```text
mispricing_score_mix = conditional_prob_mix - 0.5
```

---

## Portfolio Construction

The portfolio is constructed from pair-level signals.

Each day:

```text
1. Compute all available pair signals.
2. Rank pairs by absolute mispricing score.
3. Select the top N strongest signals.
4. Build dollar-neutral pair trades.
5. Aggregate all pair trades into asset-level positions.
6. Normalize gross exposure to 1.
7. Shift positions by one day before computing PnL.
```

Dollar-neutral pair rule:

```text
long leg weight + short leg weight = 0
```

Portfolio-level constraint:

```text
gross exposure = 1
net exposure ≈ 0
```

---

## Backtesting Rules

The backtest must be realistic and avoid look-ahead bias.

Correct PnL calculation:

```python
positions_for_pnl = positions.shift(1)
daily_pnl = (positions_for_pnl * returns).sum(axis=1)
```

Transaction costs:

```python
turnover = positions.diff().abs().sum(axis=1)
cost = turnover * cost_bps / 10000
net_return = gross_return - cost
```

The backtest reports both gross and net performance.

---

## Validation Design

The project uses a train / validation / test split:

```text
Train / research period: 2015-01-01 to 2020-12-31
Validation period:      2021-01-01 to 2022-12-31
Test period:            2023-01-01 to latest available date
```

Rules:

```text
use train and validation for development
use validation for model and parameter selection
use test only for final reporting
do not optimize on the test set
```

---

## Performance Metrics

The project computes:

```text
annualized return
annualized volatility
Sharpe ratio
Sortino ratio
Calmar ratio
max drawdown
hit rate
average daily turnover
average transaction cost
gross exposure
net exposure
market beta
information coefficient
rank information coefficient
IC t-stat
```

Example output format:

```text
Annualized Return: X.X%
Annualized Volatility: X.X%
Sharpe Ratio: X.XX
Max Drawdown: -X.X%
Hit Rate: XX.X%
Average Daily Turnover: XX.X%
Average IC: 0.0XX
IC t-stat: X.XX
Market Beta: 0.0X
```

No performance numbers should be claimed unless generated by the actual backtest.

---

## Robustness Testing

The strategy should be evaluated across parameter grids.

Example grid:

```text
window = [126, 252, 504]
threshold = [0.60, 0.70, 0.80, 0.90]
top_n_pairs = [10, 25, 50]
cost_bps = [0, 5, 10]
copula_model = ["gaussian", "t", "clayton", "mixture"]
```

The robustness table should include:

```text
window
threshold
top_n_pairs
cost_bps
copula_model
annual_return
annual_volatility
sharpe
max_drawdown
hit_rate
turnover
IC
rank_IC
market_beta
```

The key question is not whether one configuration looks great.

The key question is whether performance is stable across reasonable parameter choices.

---

## Repository Structure

```text
copula-relative-value-alpha/
│
├── data/
│   ├── raw/
│   ├── processed/
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_pair_selection.ipynb
│   ├── 03_copula_signal_research.ipynb
│   ├── 04_backtest_analysis.ipynb
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── data_loader.py
│   ├── features.py
│   ├── pair_selection.py
│   ├── copulas.py
│   ├── signals.py
│   ├── portfolio.py
│   ├── backtester.py
│   ├── metrics.py
│   ├── plots.py
│   └── utils.py
│
├── scripts/
│   ├── run_data_pipeline.py
│   ├── run_pair_selection.py
│   ├── run_backtest.py
│   ├── run_robustness.py
│   └── run_report.py
│
├── tests/
│   ├── test_features.py
│   ├── test_copulas.py
│   ├── test_backtester.py
│   └── test_metrics.py
│
├── results/
│   ├── performance_summary.csv
│   ├── performance_by_period.csv
│   ├── robustness_table.csv
│   ├── equity_curve.csv
│   ├── daily_positions.csv
│   ├── pair_signals.csv
│   └── plots/
│
├── README.md
├── requirements.txt
├── Makefile
└── .gitignore
```

---

## Installation

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Running the Pipeline

Download and process data:

```bash
python scripts/run_data_pipeline.py
```

Select candidate pairs:

```bash
python scripts/run_pair_selection.py
```

Run a baseline Gaussian copula backtest:

```bash
python scripts/run_backtest.py \
    --copula gaussian \
    --window 252 \
    --threshold 0.75 \
    --top-n-pairs 25 \
    --cost-bps 5 \
    --max-pairs 200
```

Run a t-copula backtest:

```bash
python scripts/run_backtest.py \
    --copula t \
    --window 252 \
    --threshold 0.75 \
    --top-n-pairs 25 \
    --cost-bps 5 \
    --max-pairs 200
```

Run a mixture copula backtest:

```bash
python scripts/run_backtest.py \
    --copula mixture \
    --window 252 \
    --threshold 0.75 \
    --top-n-pairs 25 \
    --cost-bps 5 \
    --max-pairs 200
```

Run robustness tests:

```bash
python scripts/run_robustness.py --max-pairs 200
```

---

## Makefile Commands

Target command sequence:

```bash
make setup
make data
make pairs
make backtest
make robustness
make report
```

---

## Expected Outputs

The pipeline should generate:

```text
data/processed/prices.csv
data/processed/returns.csv
data/processed/candidate_pairs.csv
results/pair_signals.csv
results/daily_positions.csv
results/backtest.csv
results/performance_summary.csv
results/performance_by_period.csv
results/robustness_table.csv
results/plots/equity_curve.png
results/plots/drawdown.png
results/plots/turnover.png
```

---

## Example Research Interpretation

After running the full experiment, the analysis should answer:

```text
Does the copula signal have positive IC?
Does the signal remain predictive out-of-sample?
Does the strategy survive transaction costs?
Does the t-copula improve performance during high-volatility regimes?
Does Clayton improve downside relative-value detection?
Does the mixture copula improve robustness or just overfit?
Is performance stable across windows, thresholds and cost assumptions?
```

---

## Limitations

This project has several limitations:

```text
daily data may miss intraday mean-reversion dynamics
ETF universe is small compared with institutional universes
transaction costs are simplified
borrow costs and shorting constraints are ignored
corporate actions are handled indirectly through adjusted prices
copula parameters may be unstable for short windows
mixture copulas may overfit if not carefully validated
```

These limitations should be discussed explicitly in the final report.

---

## Future Extensions

Potential extensions:

```text
1. Expand from ETFs to 300+ liquid equities.
2. Add sector-neutral and industry-neutral pair selection.
3. Implement Student-t copula with rolling degrees-of-freedom estimation.
4. Implement Clayton, Gumbel and Frank copulas.
5. Implement Gaussian + t + Clayton mixture copula.
6. Estimate mixture weights using rolling likelihood.
7. Add IC decay analysis across 1-day, 5-day and 10-day horizons.
8. Add beta-neutral position sizing.
9. Add volatility targeting.
10. Add risk model constraints.
11. Add ML model using copula features to predict pair convergence.
12. Add regime-dependent copula weights.
13. Add slippage and borrow-cost models.
```

---

## CV Bullet Templates

Use only after real metrics are generated.

### Conservative Version

```text
Built a Python copula-based relative-value research pipeline to estimate rolling dependence across liquid ETF pairs and generate market-neutral rich/cheap signals. Implemented pair selection, Gaussian copula mispricing scores, transaction-cost-aware backtesting, turnover analysis and out-of-sample validation.
```

### Strong Version With Numbers

```text
Built and backtested a Python copula-based relative-value alpha engine across {N_ASSETS} liquid assets and {N_PAIRS} candidate pairs, estimating rolling dependence and conditional mispricing signals to identify rich/cheap opportunities. Achieved {SHARPE} out-of-sample Sharpe, {HIT_RATE}% hit rate, {MAX_DD}% max drawdown and {IC} average IC after {COST_BPS} bps transaction costs.
```

### Advanced Mixture Copula Version

```text
Developed a regime-aware mixture-copula alpha research framework, combining Gaussian, Student-t and Clayton copulas to mine relative-value signals from changing dependence structures across {N_PAIRS} liquid asset pairs. Evaluated predictive power using IC, rank IC, walk-forward backtests and transaction-cost-adjusted Sharpe analysis.
```

---

## Definition of Done

The project is complete when:

```text
1. The full pipeline runs from the command line.
2. Data is downloaded and cleaned.
3. Candidate pairs are selected.
4. Copula signals are generated.
5. Positions are built with no look-ahead bias.
6. Backtest includes transaction costs.
7. Metrics are saved.
8. Train / validation / test performance is reported.
9. Robustness grid is saved.
10. Gaussian, t, Clayton and mixture variants are compared.
11. README is professional and recruiter-friendly.
12. CV bullet can be filled with real generated numbers.
```

---

## Key Research Principle

The central principle of the project is:

> Do not assume that a more complex copula is better. Test whether it improves out-of-sample predictive power after costs.

This is the mindset of a real alpha research project.
