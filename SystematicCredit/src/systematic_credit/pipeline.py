"""End-to-end demo pipeline for the bond-CDS basis toolkit."""

from __future__ import annotations

from pathlib import Path
import ast
from typing import Any

import pandas as pd

from systematic_credit.backtesting.backtest_engine import BacktestEngine
from systematic_credit.backtesting.transaction_costs import TransactionCostConfig, TransactionCostModel
from systematic_credit.basis.basis_calculator import BasisCalculator
from systematic_credit.basis.maturity_matcher import MaturityMatcher
from systematic_credit.calibration.cds_curve_calibrator import (
    CDSCurveCalibrationConfig,
    CDSCurveCalibrator,
)
from systematic_credit.data.excel_export import export_dashboard_tables
from systematic_credit.data.synthetic_credit_data import DataGenerationConfig, SyntheticCreditDataGenerator
from systematic_credit.hedging.hedge_effectiveness import hedge_effectiveness_summary
from systematic_credit.hedging.hedge_overlay import HedgeOverlayConfig, MacroHedgeOverlay
from systematic_credit.hedging.macro_regime import MacroRegimeClassifier
from systematic_credit.risk.position_sizing import CS01WeightedPositionSizer, PositionSizingConfig
from systematic_credit.risk.stress_testing import run_spread_stress
from systematic_credit.signals.basis_rv_signal import BasisRVSignal, BasisRVSignalConfig
from systematic_credit.signals.mean_reversion_filter import add_mean_reversion_confirmation
from systematic_credit.visualization.dashboard_charts import latest_basis_by_bond, regime_counts


def run_demo_pipeline(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root)
    config_dir = root / "config"
    curve_cfg = _load_yaml(config_dir / "curve_config.yaml")
    strategy_cfg = _load_yaml(config_dir / "strategy_config.yaml")
    backtest_cfg = _load_yaml(config_dir / "backtest_config.yaml")

    generator = SyntheticCreditDataGenerator(
        DataGenerationConfig(
            cds_tenors_years=tuple(curve_cfg.get("cds_tenors_years", [1, 3, 5, 7, 10]))
        )
    )
    generated = generator.generate_all()
    macro = generated["macro"]
    cds_quotes = generated["cds_quotes"]
    bonds = generated["bonds"]

    calibrator = CDSCurveCalibrator(
        CDSCurveCalibrationConfig(
            recovery_rate_default=float(curve_cfg.get("recovery_rate_default", 0.40)),
            discount_rate=float(curve_cfg.get("discount_rate", 0.035)),
            premium_frequency=int(curve_cfg.get("premium_frequency", 4)),
            notional_for_cs01=float(curve_cfg.get("notional_for_cs01", 1_000_000)),
        )
    )
    cds_curves = calibrator.calibrate(cds_quotes)

    matched = MaturityMatcher(calibrator).match(bonds, cds_curves)
    basis = BasisCalculator(
        rolling_window=int(strategy_cfg.get("rolling_zscore_window", 40)),
        min_periods=int(strategy_cfg.get("rolling_zscore_min_periods", 15)),
    ).calculate(matched)

    signals = BasisRVSignal(
        BasisRVSignalConfig(
            entry_zscore=float(strategy_cfg.get("entry_zscore", 1.25)),
            exit_zscore=float(strategy_cfg.get("exit_zscore", 0.25)),
            max_transaction_cost_bps=float(strategy_cfg.get("max_transaction_cost_bps", 35.0)),
        )
    ).generate(basis)
    signals = add_mean_reversion_confirmation(signals)

    classified_macro = MacroRegimeClassifier().classify(macro)
    engine = BacktestEngine(
        position_sizer=CS01WeightedPositionSizer(
            PositionSizingConfig(
                target_cs01_per_trade=float(strategy_cfg.get("target_cs01_per_trade", 3_500)),
                max_gross_notional=float(strategy_cfg.get("max_gross_notional", 25_000_000)),
                max_net_notional=float(strategy_cfg.get("max_net_notional", 9_000_000)),
                issuer_notional_limit=float(strategy_cfg.get("issuer_notional_limit", 6_000_000)),
                rating_notional_limit=float(strategy_cfg.get("rating_notional_limit", 14_000_000)),
            )
        ),
        hedge_overlay=MacroHedgeOverlay(HedgeOverlayConfig()),
        transaction_cost_model=TransactionCostModel(
            TransactionCostConfig(
                base_half_spread_fraction=float(backtest_cfg.get("base_half_spread_fraction", 0.5)),
                regime_cost_multipliers=backtest_cfg.get("regime_cost_multipliers", {}),
            )
        ),
        initial_capital=float(backtest_cfg.get("initial_capital", 10_000_000)),
        annualization_factor=int(backtest_cfg.get("annualization_factor", 252)),
    )
    result = engine.run(signals, classified_macro)
    stress = run_spread_stress(result.positions, backtest_cfg.get("stress_scenarios_bps", {}))
    hedge_effectiveness = hedge_effectiveness_summary(result.pnl)

    performance = pd.DataFrame([result.metrics])
    performance.insert(0, "metric_set", "base_case")
    config_table = pd.DataFrame(
        [
            {"section": "curve", "parameter": key, "value": str(value)}
            for key, value in curve_cfg.items()
        ]
        + [
            {"section": "strategy", "parameter": key, "value": str(value)}
            for key, value in strategy_cfg.items()
        ]
        + [
            {"section": "backtest", "parameter": key, "value": str(value)}
            for key, value in backtest_cfg.items()
        ]
    )

    dashboard_summary = pd.concat(
        [
            latest_basis_by_bond(signals).assign(summary_type="latest_basis"),
            regime_counts(classified_macro).assign(summary_type="regime_counts"),
        ],
        ignore_index=True,
        sort=False,
    )

    tables = {
        "macro": classified_macro,
        "cds_quotes": cds_quotes,
        "cds_curves": cds_curves,
        "hazard_survival": cds_curves[
            [
                "date",
                "issuer",
                "maturity_years",
                "hazard_rate",
                "survival_probability",
                "cumulative_default_probability",
                "market_cds_spread_bps",
                "model_cds_spread_bps",
                "cs01_per_1mm",
            ]
        ],
        "bond_cds_basis": basis,
        "rv_signals": signals,
        "positions": result.positions,
        "hedge_overlay": result.hedge_history,
        "pnl_attribution": result.pnl,
        "performance": performance,
        "hedge_effectiveness": hedge_effectiveness,
        "stress_test": stress,
        "config": config_table,
        "dashboard_summary": dashboard_summary,
    }

    payload_path = export_dashboard_tables(tables, root / "data" / "output")
    return {
        "tables": tables,
        "payload_path": payload_path,
        "metrics": result.metrics,
    }


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except ModuleNotFoundError:
        return _load_simple_yaml(text)


def _load_simple_yaml(text: str) -> dict[str, Any]:
    """Small fallback parser for this project's flat/nested config files."""

    parsed: dict[str, Any] = {}
    current_parent: str | None = None
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        key, _, value = raw_line.strip().partition(":")
        if not key:
            continue
        if indent == 0:
            if value.strip() == "":
                parsed[key] = {}
                current_parent = key
            else:
                parsed[key] = _parse_scalar(value.strip())
                current_parent = None
        elif current_parent is not None:
            parsed.setdefault(current_parent, {})[key] = _parse_scalar(value.strip())
    return parsed


def _parse_scalar(value: str) -> Any:
    if value == "":
        return ""
    if value.startswith("[") and value.endswith("]"):
        return ast.literal_eval(value)
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    return value.strip("'\"")
