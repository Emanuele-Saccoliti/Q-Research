"""Hedge effectiveness analytics."""

from __future__ import annotations

import pandas as pd


def hedge_effectiveness_summary(pnl: pd.DataFrame) -> pd.DataFrame:
    """Compare hedged and unhedged daily P&L volatility."""

    if pnl.empty:
        return pd.DataFrame()
    unhedged = pnl["basis_convergence_pnl"] + pnl["credit_spread_pnl"] + pnl["carry_pnl"] - pnl["transaction_costs"]
    hedged = pnl["total_pnl"]
    unhedged_vol = float(unhedged.std(ddof=0))
    hedged_vol = float(hedged.std(ddof=0))
    return pd.DataFrame(
        [
            {
                "unhedged_daily_vol": unhedged_vol,
                "hedged_daily_vol": hedged_vol,
                "vol_reduction_pct": 0.0
                if unhedged_vol == 0
                else (unhedged_vol - hedged_vol) / unhedged_vol,
                "hedge_pnl_correlation": float(pnl["hedge_pnl"].corr(unhedged))
                if len(pnl) > 1
                else 0.0,
            }
        ]
    )
