"""Transaction-cost-aware strategy backtest engine."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from systematic_credit.backtesting.performance_metrics import compute_performance_metrics
from systematic_credit.backtesting.pnl_attribution import compute_pnl_attribution
from systematic_credit.backtesting.transaction_costs import TransactionCostModel
from systematic_credit.hedging.hedge_overlay import MacroHedgeOverlay
from systematic_credit.risk.position_sizing import CS01WeightedPositionSizer


@dataclass
class BacktestResult:
    positions: pd.DataFrame
    hedge_history: pd.DataFrame
    pnl: pd.DataFrame
    metrics: dict[str, float]


class BacktestEngine:
    """Run sizing, hedging, costs, P&L attribution, and metrics."""

    def __init__(
        self,
        position_sizer: CS01WeightedPositionSizer | None = None,
        hedge_overlay: MacroHedgeOverlay | None = None,
        transaction_cost_model: TransactionCostModel | None = None,
        initial_capital: float = 10_000_000.0,
        annualization_factor: int = 252,
        rebalance_threshold: float = 0.25,
    ) -> None:
        self.position_sizer = position_sizer or CS01WeightedPositionSizer()
        self.hedge_overlay = hedge_overlay or MacroHedgeOverlay()
        self.transaction_cost_model = transaction_cost_model or TransactionCostModel()
        self.initial_capital = initial_capital
        self.annualization_factor = annualization_factor
        self.rebalance_threshold = rebalance_threshold

    def run(self, signals: pd.DataFrame, macro_regime: pd.DataFrame) -> BacktestResult:
        raw_positions = self.position_sizer.size(signals)
        positions, hedge_history = self.hedge_overlay.apply(raw_positions, macro_regime)
        positions = positions.sort_values(["bond_id", "date"]).copy()
        positions = self._apply_rebalance_threshold(positions)
        positions["turnover_notional"] = (
            positions.groupby("bond_id")["target_notional"].diff().fillna(positions["target_notional"]).abs()
        )
        positions = self.transaction_cost_model.apply(positions)
        pnl = compute_pnl_attribution(positions, hedge_history, self.initial_capital)
        metrics = compute_performance_metrics(pnl, self.initial_capital, self.annualization_factor)
        return BacktestResult(positions=positions, hedge_history=hedge_history, pnl=pnl, metrics=metrics)

    def _apply_rebalance_threshold(self, positions: pd.DataFrame) -> pd.DataFrame:
        out = positions.copy()
        out["desired_target_notional"] = out["target_notional"]
        out["desired_target_cs01"] = out["target_cs01"]
        cs01_col = (
            "matched_cds_cs01_per_1mm"
            if "matched_cds_cs01_per_1mm" in out.columns
            else "cs01_per_1mm"
        )

        final_frames: list[pd.DataFrame] = []
        for _, group in out.groupby("bond_id", sort=False):
            held_notional = 0.0
            notionals: list[float] = []
            for desired in group["desired_target_notional"].astype(float):
                if desired == 0.0:
                    held_notional = 0.0
                elif held_notional == 0.0:
                    held_notional = desired
                elif desired * held_notional < 0.0:
                    held_notional = desired
                else:
                    relative_change = abs(desired - held_notional) / max(abs(held_notional), 1.0)
                    if relative_change >= self.rebalance_threshold:
                        held_notional = desired
                notionals.append(held_notional)
            part = group.copy()
            part["target_notional"] = notionals
            if cs01_col in part.columns:
                part["target_cs01"] = part["target_notional"] / 1_000_000.0 * part[cs01_col]
            final_frames.append(part)

        return pd.concat(final_frames, ignore_index=True).sort_values(["bond_id", "date"])
