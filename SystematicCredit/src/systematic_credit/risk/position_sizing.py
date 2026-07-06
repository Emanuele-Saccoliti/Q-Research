"""CS01-weighted position sizing with portfolio concentration limits."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from systematic_credit.data.preprocess import require_columns, sort_panel


@dataclass(frozen=True)
class PositionSizingConfig:
    target_cs01_per_trade: float = 3_500.0
    max_gross_notional: float = 25_000_000.0
    max_net_notional: float = 9_000_000.0
    issuer_notional_limit: float = 6_000_000.0
    rating_notional_limit: float = 14_000_000.0
    min_cs01_per_1mm: float = 1.0


class CS01WeightedPositionSizer:
    """Scale target notional inversely to each instrument's CS01."""

    def __init__(self, config: PositionSizingConfig | None = None) -> None:
        self.config = config or PositionSizingConfig()

    def size(self, signals: pd.DataFrame) -> pd.DataFrame:
        require_columns(
            signals,
            ["date", "issuer", "rating", "bond_id", "rv_signal", "signal_strength"],
            "signals",
        )
        out = sort_panel(signals, ["date", "issuer", "bond_id"])
        cs01_col = (
            "matched_cds_cs01_per_1mm"
            if "matched_cds_cs01_per_1mm" in out.columns
            else "cs01_per_1mm"
        )
        require_columns(out, [cs01_col], "signals")
        safe_cs01 = out[cs01_col].abs().clip(lower=self.config.min_cs01_per_1mm)
        out["raw_target_cs01"] = (
            out["rv_signal"].astype(float)
            * out["signal_strength"].astype(float)
            * self.config.target_cs01_per_trade
        )
        out["raw_target_notional"] = out["raw_target_cs01"] / safe_cs01 * 1_000_000.0

        scaled_frames = [self._apply_limits_for_date(group) for _, group in out.groupby("date", sort=False)]
        sized = pd.concat(scaled_frames, ignore_index=True)
        sized["target_cs01"] = sized["target_notional"] / 1_000_000.0 * sized[cs01_col]
        sized["abs_target_notional"] = sized["target_notional"].abs()
        return sort_panel(sized, ["date", "issuer", "bond_id"])

    def _apply_limits_for_date(self, group: pd.DataFrame) -> pd.DataFrame:
        out = group.copy()
        out["target_notional"] = out["raw_target_notional"].astype(float)

        for limit_col, limit in [
            ("issuer", self.config.issuer_notional_limit),
            ("rating", self.config.rating_notional_limit),
        ]:
            out = self._scale_group_limit(out, limit_col, limit)

        gross = out["target_notional"].abs().sum()
        if gross > self.config.max_gross_notional > 0:
            out["target_notional"] *= self.config.max_gross_notional / gross

        net = out["target_notional"].sum()
        if abs(net) > self.config.max_net_notional > 0:
            out["target_notional"] *= self.config.max_net_notional / abs(net)

        return out

    @staticmethod
    def _scale_group_limit(df: pd.DataFrame, group_col: str, limit: float) -> pd.DataFrame:
        out = df.copy()
        if group_col not in out.columns or limit <= 0:
            return out
        for _, idx in out.groupby(group_col).groups.items():
            gross = out.loc[idx, "target_notional"].abs().sum()
            if gross > limit:
                out.loc[idx, "target_notional"] *= limit / gross
        return out
