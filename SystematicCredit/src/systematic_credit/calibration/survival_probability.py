"""Survival probability helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from systematic_credit.calibration.hazard_rate_bootstrap import survival_at


def survival_curve(
    maturities: np.ndarray,
    hazard_rates: np.ndarray,
    evaluation_times: np.ndarray | None = None,
) -> pd.DataFrame:
    """Evaluate survival and cumulative default probabilities along a curve."""

    maturities = np.asarray(maturities, dtype=float)
    hazard_rates = np.asarray(hazard_rates, dtype=float)
    times = np.asarray(evaluation_times if evaluation_times is not None else maturities, dtype=float)

    survival = np.array([survival_at(float(t), maturities, hazard_rates) for t in times])
    return pd.DataFrame(
        {
            "maturity_years": times,
            "survival_probability": survival,
            "cumulative_default_probability": 1.0 - survival,
        }
    )


def forward_default_probability(
    start_year: float,
    end_year: float,
    maturities: np.ndarray,
    hazard_rates: np.ndarray,
) -> float:
    """Probability of default between two future times, conditional on today."""

    if end_year < start_year:
        raise ValueError("end_year must be greater than or equal to start_year")
    start_survival = survival_at(start_year, maturities, hazard_rates)
    end_survival = survival_at(end_year, maturities, hazard_rates)
    return float(max(0.0, start_survival - end_survival))
