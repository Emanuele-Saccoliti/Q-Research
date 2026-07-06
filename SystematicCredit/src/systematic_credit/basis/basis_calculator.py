"""Bond-CDS basis calculation."""

from __future__ import annotations

import pandas as pd

from systematic_credit.basis.basis_zscore import add_rolling_zscore
from systematic_credit.data.preprocess import require_columns, sort_panel


class BasisCalculator:
    """Compute basis, rolling basis mean/volatility, and z-score."""

    def __init__(self, rolling_window: int = 40, min_periods: int = 15) -> None:
        self.rolling_window = rolling_window
        self.min_periods = min_periods

    def calculate(self, matched_bonds: pd.DataFrame) -> pd.DataFrame:
        require_columns(
            matched_bonds,
            ["date", "issuer", "bond_id", "bond_spread_bps", "matched_cds_spread_bps"],
            "matched_bonds",
        )
        out = sort_panel(matched_bonds, ["issuer", "bond_id", "date"])
        out["bond_cds_basis_bps"] = out["bond_spread_bps"] - out["matched_cds_spread_bps"]
        out = add_rolling_zscore(
            out,
            value_col="bond_cds_basis_bps",
            group_cols=["issuer", "bond_id"],
            window=self.rolling_window,
            min_periods=self.min_periods,
            mean_col="rolling_basis_mean_bps",
            vol_col="rolling_basis_vol_bps",
            z_col="basis_zscore",
        )
        return sort_panel(out, ["date", "issuer", "bond_id"])
