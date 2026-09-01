# Bond-CDS Basis Trading & Credit Curve Toolkit

The project calibrates CDS-implied credit curves, bootstraps hazard rates and survival probabilities, compares corporate bond spreads with maturity-matched CDS spreads, generates bond-CDS basis signals, sizes trades by CS01, applies a macro hedge overlay, runs a transaction-cost-aware backtest, and exports the results to an Excel workbook.


The main idea is:

```text
Corporate bond spread - maturity-matched CDS-implied spread = bond-CDS basis
```

If the bond spread is wide versus the CDS-implied spread, the bond may be cheap relative to CDS. If the bond spread is tight versus the CDS-implied spread, the bond may be rich relative to CDS.

The toolkit turns this idea into an end-to-end workflow:

```text
Synthetic issuer-level CDS and bond market data
-> CDS curve calibration
-> hazard-rate bootstrap
-> survival probability term structure
-> maturity-matched CDS-implied spread
-> bond-CDS basis
-> rolling basis z-score
-> relative-value signal
-> CS01-weighted position sizing
-> macro regime classification
-> hedge overlay
-> transaction-cost-aware backtest
-> P&L attribution
-> Excel dashboard export
```

## 1. Important Clarification: Python Engine vs Excel Dashboard

This is not currently a Streamlit-style interactive web app.

The current workflow is:

1. Python generates the research outputs.
2. The Excel builder creates a formatted dashboard workbook from those outputs.
3. Excel is opened as a desk-style snapshot dashboard.

Excel refresh alone does not rerun Python and does not rebuild the dashboard from scratch. If the code, config, assumptions, or generated data change, rerun the Python pipeline and then rebuild the Excel workbook.

Normal workflow:

```bash
cd "/Users/emanuelesaccoliti/VS Code/Projects/Q-Research/SystematicCredit"
source .venv/bin/activate
python scripts/run_pipeline.py
python scripts/build_dashboard.py
open "outputs/systematic_credit_toolkit/bond_cds_basis_dashboard.xlsx"
```

## 2. Repository Structure

```text
SystematicCredit/
|
|-- README.md
|-- requirements.txt
|-- pyproject.toml
|
|-- config/
|   |-- curve_config.yaml
|   |-- strategy_config.yaml
|   |-- backtest_config.yaml
|   `-- dashboard_config.yaml
|
|-- data/
|   |-- raw/
|   |-- processed/
|   |-- synthetic/
|   `-- output/
|
|-- excel/
|   `-- vba_macros/
|       `-- refresh_dashboard.bas
|
|-- outputs/
|   `-- systematic_credit_toolkit/
|       `-- bond_cds_basis_dashboard.xlsx
|
|-- reports/
|   |-- figures/
|   `-- final_project_summary.md
|
|-- scripts/
|   |-- run_pipeline.py
|   `-- build_dashboard.py
|
|-- src/
|   `-- systematic_credit/
|       |-- data/
|       |-- calibration/
|       |-- basis/
|       |-- signals/
|       |-- risk/
|       |-- hedging/
|       |-- backtesting/
|       `-- visualization/
|
`-- tests/
```

## 3. Setup From Scratch

If `.venv` already exists, you can skip the virtual-environment creation and just activate it.

```bash
cd "/Users/emanuelesaccoliti/VS Code/Projects/Q-Research/SystematicCredit"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Verify the package and tests:

```bash
.venv/bin/python -m pytest -q
```

Expected result:

```text
11 passed
```

## 4. Running The Python Pipeline

From the project root:

```bash
cd "/Users/emanuelesaccoliti/VS Code/Projects/Q-Research/SystematicCredit"
source .venv/bin/activate
python scripts/run_pipeline.py
```

The script runs the full workflow:

1. Generate synthetic issuer-level macro, CDS, and bond data.
2. Calibrate CDS curves by issuer and date.
3. Bootstrap hazard rates and survival probabilities.
4. Estimate maturity-matched CDS spreads for each bond.
5. Compute bond-CDS basis and rolling z-scores.
6. Generate basis relative-value signals.
7. Size positions using CS01.
8. Classify macro regimes.
9. Apply hedge overlay.
10. Run transaction-cost-aware backtest.
11. Export CSV and JSON tables to `data/output/`.

Typical terminal output:

```text
Pipeline complete
Dashboard payload: .../data/output/dashboard_payload.json
Total P&L: ...
Sharpe ratio: ...
Max drawdown: ...
```

## 5. Rebuilding The Excel Dashboard

After running the Python pipeline, build the Excel workbook:

```bash
python scripts/build_dashboard.py
```

The dashboard is written to:

```text
outputs/systematic_credit_toolkit/bond_cds_basis_dashboard.xlsx
```

Open it with:

```bash
open "outputs/systematic_credit_toolkit/bond_cds_basis_dashboard.xlsx"
```

## 6. Full End-To-End Command Sequence

Use this when you want to regenerate everything:

```bash
cd "/Users/emanuelesaccoliti/VS Code/Projects/Q-Research/SystematicCredit"
source .venv/bin/activate
python scripts/run_pipeline.py
python scripts/build_dashboard.py
open "outputs/systematic_credit_toolkit/bond_cds_basis_dashboard.xlsx"
```

## 7. Main Outputs

The Python pipeline writes these files to `data/output/`:

```text
macro.csv
cds_quotes.csv
cds_curves.csv
hazard_survival.csv
bond_cds_basis.csv
rv_signals.csv
positions.csv
hedge_overlay.csv
pnl_attribution.csv
performance.csv
hedge_effectiveness.csv
stress_test.csv
config.csv
dashboard_summary.csv
dashboard_payload.json
```

The Excel dashboard is:

```text
outputs/systematic_credit_toolkit/bond_cds_basis_dashboard.xlsx
```

The workbook contains these sheets:

```text
Dashboard
CDS_Curves
Hazard_Survival
Bond_CDS_Basis
RV_Signals
Positions
Macro_Regime
Hedge_Overlay
PnL_Attribution
Performance
Stress_Test
Config
```

Large research tables are available in full as CSV files in `data/output/`. The Excel workbook may use a trimmed latest-row view for large sheets to keep the workbook responsive.

## 8. Financial Methodology

### 8.1 CDS Curve Calibration

The calibration module takes market CDS spreads by issuer, date, and tenor.

Example tenor set:

```text
1Y, 3Y, 5Y, 7Y, 10Y
```

For each issuer-date curve, the model bootstraps piecewise-constant hazard rates. The calibrated curve outputs:

```text
maturity_years
market_cds_spread_bps
hazard_rate
survival_probability
cumulative_default_probability
model_cds_spread_bps
cs01_per_1mm
```

Key assumptions:

- piecewise-constant hazard rates;
- issuer-level recovery rate;
- flat discount rate;
- quarterly premium payments;
- par-spread calibration by equating premium leg and protection leg.

### 8.2 Survival Probabilities

Survival probability is computed from the cumulative hazard:

```text
S(t) = exp(-integral hazard_rate dt)
```

Higher CDS spreads imply higher default intensity and therefore lower survival probability.

### 8.3 Maturity-Matched CDS Spread

Corporate bonds often do not mature exactly on standard CDS tenors. The maturity matcher estimates a CDS-implied spread for each bond maturity using the calibrated CDS curve.

Example:

```text
5Y CDS = 150 bps
7Y CDS = 170 bps
Bond maturity = 6Y
Matched CDS spread ~= curve-implied 6Y spread
```

### 8.4 Bond-CDS Basis

The basis is:

```text
bond_cds_basis_bps = bond_spread_bps - matched_cds_spread_bps
```

Interpretation:

```text
Positive basis:
bond spread > CDS-implied spread
cash bond may be cheap versus CDS

Negative basis:
bond spread < CDS-implied spread
cash bond may be rich versus CDS
```

### 8.5 Rolling Z-Score Signal

The strategy standardizes basis using a rolling z-score:

```text
basis_zscore = (basis - rolling_mean_basis) / rolling_basis_volatility
```

Signal logic:

```text
High positive z-score:
long cash credit exposure / bond cheap versus CDS

High negative z-score:
reduce cash credit exposure or hedge / bond rich versus CDS

Z-score close to zero:
exit or reduce mean-reversion trade
```

The signal layer also applies a transaction-cost filter to avoid low-edge trades when estimated bid-ask costs are too high.

### 8.6 CS01-Weighted Position Sizing

CS01 measures the P&L sensitivity to a one-basis-point move in credit spreads.

The position sizer scales notional inversely to CS01:

```text
higher CS01 -> smaller notional
lower CS01 -> larger notional
```

The sizer also applies:

- gross notional cap;
- net notional cap;
- issuer concentration limit;
- rating concentration limit.

### 8.7 Macro Regime Classifier

Macro regimes are classified using transparent rules based on:

- credit index spread changes;
- equity proxy returns;
- volatility proxy;
- liquidity proxy;
- rates proxy.

Regimes:

```text
risk_on
neutral
spread_widening
risk_off
liquidity_stress
```

### 8.8 Hedge Overlay

During risk-off, spread-widening, or liquidity-stress regimes, the hedge overlay reduces strategy exposure and adds a credit-index hedge based on portfolio CS01.

The hedge output includes:

```text
net_strategy_cs01
gross_strategy_cs01
hedge_ratio
hedge_cs01
hedge_notional
```

### 8.9 Transaction Costs

Transaction costs are estimated from:

- bond bid-ask spread;
- CDS bid-ask spread;
- turnover;
- liquidity score;
- macro regime cost multiplier.

Costs are higher in stressed regimes and for less liquid bonds.

### 8.10 P&L Attribution

The backtest decomposes daily P&L into:

```text
basis_convergence_pnl
credit_spread_pnl
hedge_pnl
carry_pnl
transaction_costs
total_pnl
```

Performance metrics include:

```text
total_pnl
total_return
annualized_volatility
sharpe_ratio
max_drawdown
hit_rate
ending_nav
```

## 9. Configuration Files

### `config/curve_config.yaml`

Controls curve assumptions:

```text
recovery_rate_default
discount_rate
premium_frequency
cds_tenors_years
notional_for_cs01
```

### `config/strategy_config.yaml`

Controls signal and sizing rules:

```text
rolling_zscore_window
rolling_zscore_min_periods
entry_zscore
exit_zscore
max_transaction_cost_bps
target_cs01_per_trade
max_gross_notional
max_net_notional
issuer_notional_limit
rating_notional_limit
```

### `config/backtest_config.yaml`

Controls capital, annualization, costs, and stress scenarios:

```text
initial_capital
annualization_factor
base_half_spread_fraction
regime_cost_multipliers
stress_scenarios_bps
```

### `config/dashboard_config.yaml`

Controls dashboard naming and output configuration.

## 10. Module Map

### Data

```text
src/systematic_credit/data/synthetic_credit_data.py
```

Generates synthetic issuer-level market data:

- CDS quotes;
- bond spreads;
- bond metadata;
- liquidity assumptions;
- bid-ask assumptions;
- macro factors and regimes.

### Calibration

```text
src/systematic_credit/calibration/
```

Core files:

```text
hazard_rate_bootstrap.py
survival_probability.py
cds_curve_calibrator.py
cs01.py
```

### Basis

```text
src/systematic_credit/basis/
```

Core files:

```text
maturity_matcher.py
basis_calculator.py
basis_zscore.py
```

### Signals

```text
src/systematic_credit/signals/
```

Core files:

```text
basis_rv_signal.py
mean_reversion_filter.py
signal_combiner.py
```

### Risk

```text
src/systematic_credit/risk/
```

Core files:

```text
position_sizing.py
cs01_exposure.py
stress_testing.py
```

### Hedging

```text
src/systematic_credit/hedging/
```

Core files:

```text
macro_regime.py
hedge_overlay.py
hedge_effectiveness.py
```

### Backtesting

```text
src/systematic_credit/backtesting/
```

Core files:

```text
backtest_engine.py
transaction_costs.py
pnl_attribution.py
performance_metrics.py
```

### Pipeline

```text
src/systematic_credit/pipeline.py
scripts/run_pipeline.py
```

These connect all modules into one reproducible workflow.

### Excel Dashboard Builder

```text
scripts/build_dashboard.py
```

Builds the Excel workbook using the generated dashboard payload.

## 11. Tests

Run all tests:

```bash
cd "/Users/emanuelesaccoliti/VS Code/Projects/Q-Research/SystematicCredit"
source .venv/bin/activate
.venv/bin/python -m pytest -q
```

Test coverage includes:

- hazard-rate bootstrap;
- survival probabilities;
- CS01;
- CDS curve calibrator;
- maturity matcher;
- basis calculator;
- basis RV signal;
- position sizing;
- hedge overlay;
- transaction costs;
- performance metrics.

## 12. Excel Notes


Excel is useful for:

- desk-style presentation;
- quick inspection of curves and signals;
- showing P&L attribution;
- sharing a polished workbook.

Excel refresh behavior:

- `Refresh All` can refresh workbook objects and formulas.
- It does not rerun `scripts/run_pipeline.py`.
- It does not rebuild the workbook from updated CSV files.
- To update the dashboard after changing assumptions, rerun Python and rebuild Excel.

The included VBA macro is:

```text
excel/vba_macros/refresh_dashboard.bas
```

It is a lightweight refresh/calculation helper, not a full Python launcher.


## 13. Troubleshooting

### `ModuleNotFoundError: No module named pandas`

Activate the virtual environment or install dependencies:

```bash
cd "/Users/emanuelesaccoliti/VS Code/Projects/Q-Research/SystematicCredit"
source .venv/bin/activate
pip install -r requirements.txt
```

### `ModuleNotFoundError: No module named xlsxwriter`

Install the project dependencies in the active Python environment:

```bash
pip install -r requirements.txt
```

### Excel dashboard did not change after editing config

Run both steps again:

```bash
python scripts/run_pipeline.py
python scripts/build_dashboard.py
```

## 14. Limitations

This is a research and interview project, not a production trading system.

Current limitations:

- data is synthetic by default;
- CDS curves use simplified assumptions;
- transaction costs are modelled, not sourced from executable quotes;
- hedge proxies are simplified;
- Excel is a generated snapshot, not a live trading terminal.



## 15. Quick Command Reference

Run tests:

```bash
cd "/Users/emanuelesaccoliti/VS Code/Projects/Q-Research/SystematicCredit"
source .venv/bin/activate
.venv/bin/python -m pytest -q
```

Run Python pipeline:

```bash
python scripts/run_pipeline.py
```

Build Excel dashboard:

```bash
python scripts/build_dashboard.py
```

Open Excel dashboard:

```bash
open "outputs/systematic_credit_toolkit/bond_cds_basis_dashboard.xlsx"
```

Full rebuild:

```bash
python scripts/run_pipeline.py && python scripts/build_dashboard.py && open "outputs/systematic_credit_toolkit/bond_cds_basis_dashboard.xlsx"
```
