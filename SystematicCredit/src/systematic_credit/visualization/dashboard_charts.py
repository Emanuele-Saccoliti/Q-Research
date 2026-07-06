"""Prepare compact chart source tables for the Excel dashboard."""

from __future__ import annotations

import pandas as pd


def latest_basis_by_bond(signals: pd.DataFrame, n: int = 12) -> pd.DataFrame:
    latest_date = signals["date"].max()
    latest = signals[signals["date"] == latest_date].copy()
    return (
        latest.sort_values("bond_cds_basis_bps", ascending=False)
        .head(n)[["bond_id", "issuer", "bond_cds_basis_bps", "basis_zscore", "rv_signal"]]
        .reset_index(drop=True)
    )


def regime_counts(macro: pd.DataFrame) -> pd.DataFrame:
    return macro["macro_regime"].value_counts().rename_axis("macro_regime").reset_index(name="days")
