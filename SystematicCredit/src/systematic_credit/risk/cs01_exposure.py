"""CS01 exposure aggregation."""

from __future__ import annotations

import pandas as pd


def aggregate_cs01_exposure(
    positions: pd.DataFrame,
    group_cols: list[str] | None = None,
    cs01_col: str = "target_cs01",
) -> pd.DataFrame:
    group_cols = group_cols or ["date"]
    out = (
        positions.groupby(group_cols, as_index=False)[cs01_col]
        .agg(net_cs01="sum", gross_cs01=lambda s: s.abs().sum())
        .reset_index(drop=True)
    )
    return out
