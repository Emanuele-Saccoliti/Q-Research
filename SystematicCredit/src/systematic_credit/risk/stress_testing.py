"""Simple credit spread stress testing."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


def run_spread_stress(
    positions: pd.DataFrame,
    shock_scenarios_bps: Mapping[str, float],
    cs01_col: str = "target_cs01",
) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    latest_date = positions["date"].max() if "date" in positions.columns and not positions.empty else None
    latest = positions[positions["date"] == latest_date] if latest_date is not None else positions
    net_cs01 = float(latest[cs01_col].sum()) if cs01_col in latest.columns else 0.0
    gross_cs01 = float(latest[cs01_col].abs().sum()) if cs01_col in latest.columns else 0.0

    for name, shock_bps in shock_scenarios_bps.items():
        rows.append(
            {
                "scenario": name,
                "spread_shock_bps": float(shock_bps),
                "net_cs01": net_cs01,
                "gross_cs01": gross_cs01,
                "estimated_pnl": -net_cs01 * float(shock_bps),
            }
        )
    return pd.DataFrame(rows)
