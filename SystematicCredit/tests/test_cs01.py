import numpy as np

from systematic_credit.calibration.cs01 import cs01_per_notional


def test_cs01_is_positive_and_increases_with_maturity():
    maturities = np.array([1, 3, 5], dtype=float)
    hazards = np.array([0.015, 0.02, 0.025], dtype=float)

    one_year = cs01_per_notional(maturities, hazards, 1)
    five_year = cs01_per_notional(maturities, hazards, 5)

    assert one_year > 0
    assert five_year > one_year
