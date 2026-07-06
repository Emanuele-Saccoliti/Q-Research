"""Combine multiple signal columns into a final trading signal."""

from __future__ import annotations

import numpy as np
import pandas as pd


def combine_signals(
    df: pd.DataFrame,
    signal_cols: list[str],
    weights: list[float] | None = None,
    output_col: str = "combined_signal",
) -> pd.DataFrame:
    """Weighted average of numeric signal columns clipped to [-1, 1]."""

    if weights is None:
        weights = [1.0] * len(signal_cols)
    if len(weights) != len(signal_cols):
        raise ValueError("weights must match signal_cols")

    out = df.copy()
    weighted = sum(out[col].fillna(0.0) * weight for col, weight in zip(signal_cols, weights, strict=True))
    total_weight = sum(abs(weight) for weight in weights) or 1.0
    out[output_col] = np.clip(weighted / total_weight, -1.0, 1.0)
    return out
