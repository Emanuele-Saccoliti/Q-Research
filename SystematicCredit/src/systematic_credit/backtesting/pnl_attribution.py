"""Daily P&L attribution for bond-CDS basis strategy."""

from __future__ import annotations

import pandas as pd


def compute_pnl_attribution(
    positions: pd.DataFrame,
    hedge_history: pd.DataFrame | None = None,
    initial_capital: float = 10_000_000.0,
) -> pd.DataFrame:
    pos = positions.sort_values(["bond_id", "date"]).copy()
    for col in [
        "target_cs01",
        "bond_cds_basis_bps",
        "matched_cds_spread_bps",
        "bond_spread_bps",
        "target_notional",
    ]:
        pos[f"prev_{col}"] = pos.groupby("bond_id")[col].shift(1)

    pos["basis_delta_bps"] = pos["bond_cds_basis_bps"] - pos["prev_bond_cds_basis_bps"]
    pos["cds_delta_bps"] = pos["matched_cds_spread_bps"] - pos["prev_matched_cds_spread_bps"]
    pos["bond_spread_delta_bps"] = pos["bond_spread_bps"] - pos["prev_bond_spread_bps"]

    prev_cs01 = pos["prev_target_cs01"].fillna(0.0)
    pos["basis_convergence_pnl"] = -prev_cs01 * pos["basis_delta_bps"].fillna(0.0)
    pos["credit_spread_pnl"] = -prev_cs01 * pos["cds_delta_bps"].fillna(0.0)
    pos["carry_pnl"] = (
        pos["prev_target_notional"].fillna(0.0)
        * pos["matched_cds_spread_bps"].fillna(0.0)
        / 10_000.0
        / 252.0
    )

    daily = (
        pos.groupby("date", as_index=False)[
            ["basis_convergence_pnl", "credit_spread_pnl", "carry_pnl", "transaction_costs"]
        ]
        .sum()
        .sort_values("date")
    )

    if hedge_history is not None and not hedge_history.empty:
        hedge = hedge_history.sort_values("date").copy()
        hedge["prev_hedge_cs01"] = hedge["hedge_cs01"].shift(1).fillna(0.0)
        hedge["credit_index_change_bps"] = hedge["credit_index_proxy"].diff().fillna(0.0)
        hedge["hedge_pnl"] = -hedge["prev_hedge_cs01"] * hedge["credit_index_change_bps"]
        daily = daily.merge(hedge[["date", "hedge_pnl"]], on="date", how="left")
    else:
        daily["hedge_pnl"] = 0.0

    daily["hedge_pnl"] = daily["hedge_pnl"].fillna(0.0)
    daily["total_pnl"] = (
        daily["basis_convergence_pnl"]
        + daily["credit_spread_pnl"]
        + daily["hedge_pnl"]
        + daily["carry_pnl"]
        - daily["transaction_costs"]
    )
    daily["cumulative_total_pnl"] = daily["total_pnl"].cumsum()
    daily["strategy_nav"] = initial_capital + daily["cumulative_total_pnl"]
    daily["daily_return"] = daily["total_pnl"] / initial_capital
    return daily
