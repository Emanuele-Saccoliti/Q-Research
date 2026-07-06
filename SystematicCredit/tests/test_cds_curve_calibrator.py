import pandas as pd

from systematic_credit.calibration.cds_curve_calibrator import CDSCurveCalibrator


def test_calibrator_outputs_curve_and_maturity_matched_spread():
    quotes = pd.DataFrame(
        {
            "date": ["2025-01-02"] * 3,
            "issuer": ["XYZ"] * 3,
            "cds_tenor_years": [1, 3, 5],
            "market_cds_spread_bps": [90, 130, 160],
            "recovery_rate": [0.4, 0.4, 0.4],
            "rating": ["BBB"] * 3,
            "sector": ["Industrials"] * 3,
        }
    )
    calibrator = CDSCurveCalibrator()
    curve = calibrator.calibrate(quotes)

    assert len(curve) == 3
    assert {"hazard_rate", "survival_probability", "cs01_per_1mm"}.issubset(curve.columns)
    assert 130 < calibrator.maturity_matched_spread(curve, 4.0) < 180
