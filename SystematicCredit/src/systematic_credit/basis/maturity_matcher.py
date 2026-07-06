"""Match corporate bond maturities to calibrated CDS-implied spreads."""

from __future__ import annotations

import numpy as np
import pandas as pd

from systematic_credit.calibration.cds_curve_calibrator import CDSCurveCalibrator
from systematic_credit.data.preprocess import ensure_datetime, require_columns, sort_panel


class MaturityMatcher:
    """Estimate maturity-matched CDS spreads for bond rows."""

    def __init__(self, calibrator: CDSCurveCalibrator | None = None) -> None:
        self.calibrator = calibrator or CDSCurveCalibrator()

    def match(self, bonds: pd.DataFrame, curves: pd.DataFrame) -> pd.DataFrame:
        require_columns(bonds, ["date", "issuer", "bond_id", "bond_maturity_years"], "bonds")
        require_columns(curves, ["date", "issuer", "maturity_years", "hazard_rate"], "curves")

        bonds = sort_panel(ensure_datetime(bonds), ["date", "issuer", "bond_id"])
        curves = sort_panel(ensure_datetime(curves), ["date", "issuer", "maturity_years"])
        curve_map = {
            key: group.reset_index(drop=True)
            for key, group in curves.groupby(["date", "issuer"], sort=False)
        }

        matched_rows: list[dict[str, object]] = []
        for _, bond in bonds.iterrows():
            key = (bond["date"], bond["issuer"])
            curve = curve_map.get(key)
            row = bond.to_dict()
            if curve is None or curve.empty:
                row.update(
                    {
                        "matched_cds_spread_bps": np.nan,
                        "maturity_gap_years": np.nan,
                        "is_extrapolated": True,
                        "matched_cds_cs01_per_1mm": np.nan,
                    }
                )
            else:
                tenors = curve["maturity_years"].to_numpy(dtype=float)
                maturity = float(bond["bond_maturity_years"])
                row.update(
                    {
                        "matched_cds_spread_bps": self.calibrator.maturity_matched_spread(
                            curve, maturity
                        ),
                        "maturity_gap_years": float(np.min(np.abs(tenors - maturity))),
                        "is_extrapolated": bool(maturity < np.min(tenors) or maturity > np.max(tenors)),
                        "matched_cds_cs01_per_1mm": self.calibrator.cs01_for_maturity(curve, maturity),
                    }
                )

                for col in ["cds_liquidity_score", "cds_bid_ask_bps"]:
                    if col in curve.columns:
                        row[col] = float(np.interp(maturity, tenors, curve[col].to_numpy(dtype=float)))
            matched_rows.append(row)

        return pd.DataFrame(matched_rows)
