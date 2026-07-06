"""Rolling z-score utilities for bond-CDS basis."""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_rolling_zscore(
    df: pd.DataFrame,
    value_col: str,
    group_cols: list[str],
    window: int = 40,
    min_periods: int = 15,
    mean_col: str | None = None,
    vol_col: str | None = None,
    z_col: str | None = None,
) -> pd.DataFrame:
    """Append rolling mean, volatility, and z-score columns."""

    out = df.copy()
    mean_col = mean_col or f"{value_col}_rolling_mean"
    vol_col = vol_col or f"{value_col}_rolling_vol"
    z_col = z_col or f"{value_col}_zscore"

    rolling = out.groupby(group_cols, group_keys=False)[value_col].rolling(
        window=window, min_periods=min_periods
    )
    out[mean_col] = rolling.mean().reset_index(level=group_cols, drop=True)
    out[vol_col] = rolling.std(ddof=0).reset_index(level=group_cols, drop=True)
    denominator = out[vol_col].replace(0.0, np.nan)
    out[z_col] = ((out[value_col] - out[mean_col]) / denominator).replace([np.inf, -np.inf], np.nan)
    out[z_col] = out[z_col].fillna(0.0)
    return out
