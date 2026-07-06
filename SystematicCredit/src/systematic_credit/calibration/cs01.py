"""Credit spread DV01/CS01 utilities."""

from __future__ import annotations

import numpy as np

from systematic_credit.calibration.hazard_rate_bootstrap import (
    discount_factor,
    payment_grid,
    survival_at,
)


def risky_annuity(
    maturities: np.ndarray,
    hazard_rates: np.ndarray,
    maturity: float,
    discount_rate: float = 0.035,
    premium_frequency: int = 4,
) -> float:
    """Present value of one basis point per unit notional paid until default/maturity."""

    times = payment_grid(maturity, premium_frequency)
    previous_times = np.r_[0.0, times[:-1]]
    annuity = 0.0
    for prev_t, t in zip(previous_times, times, strict=True):
        dt = float(t - prev_t)
        annuity += discount_factor(float(t), discount_rate) * survival_at(
            float(t), np.asarray(maturities), np.asarray(hazard_rates)
        ) * dt
    return float(annuity)


def cs01_per_notional(
    maturities: np.ndarray,
    hazard_rates: np.ndarray,
    maturity: float,
    notional: float = 1_000_000.0,
    discount_rate: float = 0.035,
    premium_frequency: int = 4,
) -> float:
    """Currency P&L sensitivity to a 1 bp spread move for the given notional."""

    return float(
        notional
        * 0.0001
        * risky_annuity(
            maturities=maturities,
            hazard_rates=hazard_rates,
            maturity=maturity,
            discount_rate=discount_rate,
            premium_frequency=premium_frequency,
        )
    )


def spread_duration(
    maturities: np.ndarray,
    hazard_rates: np.ndarray,
    maturity: float,
    discount_rate: float = 0.035,
    premium_frequency: int = 4,
) -> float:
    """Approximate risky spread duration in years."""

    return risky_annuity(maturities, hazard_rates, maturity, discount_rate, premium_frequency)
