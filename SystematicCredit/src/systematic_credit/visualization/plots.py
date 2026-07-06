"""Matplotlib helpers for notebooks and research reports."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd


def plot_cumulative_pnl(pnl: pd.DataFrame, ax: plt.Axes | None = None) -> plt.Axes:
    ax = ax or plt.subplots(figsize=(9, 4))[1]
    ax.plot(pd.to_datetime(pnl["date"]), pnl["cumulative_total_pnl"], color="#2563EB", linewidth=1.8)
    ax.set_title("Cumulative Strategy P&L")
    ax.set_ylabel("P&L")
    ax.grid(alpha=0.25)
    return ax


def plot_basis_history(
    basis: pd.DataFrame,
    bond_id: str,
    ax: plt.Axes | None = None,
) -> plt.Axes:
    ax = ax or plt.subplots(figsize=(9, 4))[1]
    subset = basis[basis["bond_id"] == bond_id].sort_values("date")
    ax.plot(pd.to_datetime(subset["date"]), subset["bond_cds_basis_bps"], color="#0F766E")
    ax.axhline(0, color="#111827", linewidth=0.8)
    ax.set_title(f"Bond-CDS Basis: {bond_id}")
    ax.set_ylabel("Basis (bps)")
    ax.grid(alpha=0.25)
    return ax
