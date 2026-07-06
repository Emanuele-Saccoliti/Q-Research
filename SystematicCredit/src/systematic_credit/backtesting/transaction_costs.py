"""Transaction-cost model for bond-CDS basis trading."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class TransactionCostConfig:
    base_half_spread_fraction: float = 0.5
    regime_cost_multipliers: dict[str, float] = field(
        default_factory=lambda: {
            "risk_on": 0.85,
            "neutral": 1.0,
            "spread_widening": 1.35,
            "risk_off": 1.75,
            "liquidity_stress": 2.25,
        }
    )


class TransactionCostModel:
    """Estimate costs from turnover, bid-ask spreads, liquidity, and regime."""

    def __init__(self, config: TransactionCostConfig | None = None) -> None:
        self.config = config or TransactionCostConfig()

    def apply(self, positions: pd.DataFrame) -> pd.DataFrame:
        out = positions.copy()
        if "turnover_notional" not in out.columns:
            out["turnover_notional"] = (
                out.groupby("bond_id")["target_notional"].diff().fillna(out["target_notional"]).abs()
            )
        bond_bid_ask = out["bond_bid_ask_bps"].fillna(0.0) if "bond_bid_ask_bps" in out.columns else 0.0
        cds_bid_ask = out["cds_bid_ask_bps"].fillna(0.0) if "cds_bid_ask_bps" in out.columns else 0.0
        liquidity_score = (
            out["bond_liquidity_score"].fillna(0.7).clip(0.05, 1.0)
            if "bond_liquidity_score" in out.columns
            else 0.7
        )
        regime_mult = out.get("macro_regime", pd.Series("neutral", index=out.index)).map(
            self.config.regime_cost_multipliers
        )
        regime_mult = regime_mult.fillna(1.0)
        blended_half_spread_bps = self.config.base_half_spread_fraction * (bond_bid_ask + cds_bid_ask)
        illiquidity_multiplier = 1.0 + 0.75 * (1.0 - liquidity_score)
        out["transaction_costs"] = (
            out["turnover_notional"].abs()
            * blended_half_spread_bps
            / 10_000.0
            * illiquidity_multiplier
            * regime_mult
        )
        return out
