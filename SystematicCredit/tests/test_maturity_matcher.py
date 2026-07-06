import pandas as pd

from systematic_credit.basis.maturity_matcher import MaturityMatcher
from systematic_credit.calibration.cds_curve_calibrator import CDSCurveCalibrator


def test_maturity_matcher_interpolates_non_standard_bond_maturity():
    quotes = pd.DataFrame(
        {
            "date": ["2025-01-02"] * 3,
            "issuer": ["XYZ"] * 3,
            "cds_tenor_years": [1, 3, 5],
            "market_cds_spread_bps": [90, 130, 160],
            "recovery_rate": [0.4, 0.4, 0.4],
        }
    )
    bonds = pd.DataFrame(
        {
            "date": ["2025-01-02"],
            "issuer": ["XYZ"],
            "rating": ["BBB"],
            "bond_id": ["XYZ_01"],
            "bond_maturity_years": [4.0],
            "bond_spread_bps": [175.0],
        }
    )
    calibrator = CDSCurveCalibrator()
    curves = calibrator.calibrate(quotes)
    matched = MaturityMatcher(calibrator).match(bonds, curves)

    assert matched["matched_cds_spread_bps"].iloc[0] > 0
    assert not bool(matched["is_extrapolated"].iloc[0])
    assert matched["maturity_gap_years"].iloc[0] == 1.0
