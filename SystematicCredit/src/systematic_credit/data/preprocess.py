"""Preprocessing helpers for date alignment and data quality checks."""

from __future__ import annotations

import pandas as pd


def ensure_datetime(df: pd.DataFrame, column: str = "date") -> pd.DataFrame:
    out = df.copy()
    if column in out.columns:
        out[column] = pd.to_datetime(out[column])
    return out


def sort_panel(df: pd.DataFrame, keys: list[str] | None = None) -> pd.DataFrame:
    keys = keys or [col for col in ["date", "issuer", "bond_id", "cds_tenor_years"] if col in df.columns]
    return df.sort_values(keys).reset_index(drop=True)


def require_columns(df: pd.DataFrame, columns: list[str], frame_name: str = "dataframe") -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"{frame_name} is missing required columns: {missing}")


def winsorize_series(series: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
    """Clip a numeric series to robust quantiles."""

    lo, hi = series.quantile([lower, upper])
    return series.clip(lo, hi)
