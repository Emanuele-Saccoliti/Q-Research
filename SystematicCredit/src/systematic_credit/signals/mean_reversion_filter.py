"""Optional mean-reversion confirmation filter."""

from __future__ import annotations

import numpy as np
import pandas as pd

from systematic_credit.data.preprocess import require_columns, sort_panel


def add_mean_reversion_confirmation(df: pd.DataFrame) -> pd.DataFrame:
    """Flag active trades where the basis is starting to move toward zero."""

    require_columns(df, ["issuer", "bond_id", "date", "bond_cds_basis_bps", "rv_signal"], "signals")
    out = sort_panel(df, ["issuer", "bond_id", "date"])
    out["basis_change_bps"] = out.groupby(["issuer", "bond_id"])["bond_cds_basis_bps"].diff()
    out["mean_reversion_confirmed"] = np.where(
        out["rv_signal"] > 0,
        out["basis_change_bps"] < 0,
        np.where(out["rv_signal"] < 0, out["basis_change_bps"] > 0, False),
    )
    return sort_panel(out, ["date", "issuer", "bond_id"])
