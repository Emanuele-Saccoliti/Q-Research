import numpy as np

from systematic_credit.calibration.hazard_rate_bootstrap import (
    CDSBootstrapConfig,
    bootstrap_piecewise_hazards,
)


def test_bootstrap_matches_market_spreads_and_survival_decreases():
    curve = bootstrap_piecewise_hazards(
        np.array([1, 3, 5], dtype=float),
        np.array([80, 120, 150], dtype=float),
        CDSBootstrapConfig(recovery_rate=0.40),
    )

    assert (curve["hazard_rate"] > 0).all()
    assert curve["survival_probability"].is_monotonic_decreasing
    assert (curve["model_cds_spread_bps"] - curve["market_cds_spread_bps"]).abs().max() < 1e-3
