import numpy as np

from systematic_credit.calibration.survival_probability import (
    forward_default_probability,
    survival_curve,
)


def test_survival_curve_and_forward_default_probability():
    maturities = np.array([1, 3, 5], dtype=float)
    hazards = np.array([0.01, 0.02, 0.03], dtype=float)

    curve = survival_curve(maturities, hazards)

    assert curve["survival_probability"].iloc[0] < 1.0
    assert curve["survival_probability"].is_monotonic_decreasing
    assert forward_default_probability(1, 3, maturities, hazards) > 0
