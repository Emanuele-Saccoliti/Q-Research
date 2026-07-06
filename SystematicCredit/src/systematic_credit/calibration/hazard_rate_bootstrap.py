"""Piecewise-constant CDS hazard-rate bootstrap."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CDSBootstrapConfig:
    """Assumptions for a transparent CDS curve bootstrap."""

    recovery_rate: float = 0.40
    discount_rate: float = 0.035
    premium_frequency: int = 4
    max_hazard_rate: float = 5.0
    tolerance_bps: float = 1e-4
    max_iterations: int = 55


def discount_factor(t: float, discount_rate: float) -> float:
    return float(np.exp(-discount_rate * t))


def survival_at(t: float, maturities: np.ndarray, hazard_rates: np.ndarray) -> float:
    """Survival probability at time t for piecewise-constant hazard rates."""

    if len(hazard_rates) == 0:
        return 1.0

    t = float(max(t, 0.0))
    maturities = np.asarray(maturities, dtype=float)
    hazard_rates = np.asarray(hazard_rates, dtype=float)

    log_survival = 0.0
    previous = 0.0
    for maturity, hazard in zip(maturities, hazard_rates, strict=False):
        interval_end = min(t, float(maturity))
        if interval_end > previous:
            log_survival -= float(hazard) * (interval_end - previous)
        previous = float(maturity)
        if t <= maturity:
            break
    if t > maturities[len(hazard_rates) - 1]:
        log_survival -= float(hazard_rates[-1]) * (t - maturities[len(hazard_rates) - 1])

    return float(np.exp(log_survival))


def payment_grid(maturity: float, premium_frequency: int) -> np.ndarray:
    step = 1.0 / premium_frequency
    times = np.arange(step, maturity + 1e-10, step)
    if len(times) == 0 or abs(times[-1] - maturity) > 1e-8:
        times = np.r_[times, maturity]
    return np.round(times, 10)


def par_spread_bps(
    maturities: np.ndarray,
    hazard_rates: np.ndarray,
    maturity: float,
    recovery_rate: float = 0.40,
    discount_rate: float = 0.035,
    premium_frequency: int = 4,
) -> float:
    """Compute the model par spread in bps for a maturity."""

    if maturity <= 0:
        raise ValueError("maturity must be positive")
    maturities = np.asarray(maturities, dtype=float)
    hazard_rates = np.asarray(hazard_rates, dtype=float)
    if len(maturities) != len(hazard_rates):
        raise ValueError("maturities and hazard_rates must have the same length")
    if len(maturities) == 0:
        return 0.0

    times = payment_grid(maturity, premium_frequency)
    previous_times = np.r_[0.0, times[:-1]]

    premium_leg = 0.0
    protection_leg = 0.0
    for prev_t, t in zip(previous_times, times, strict=True):
        dt = float(t - prev_t)
        surv_prev = survival_at(float(prev_t), maturities, hazard_rates)
        surv_t = survival_at(float(t), maturities, hazard_rates)
        discount = discount_factor(float(t), discount_rate)
        premium_leg += discount * surv_t * dt
        protection_leg += discount * (surv_prev - surv_t)

    if premium_leg <= 0:
        return 0.0
    return float((1.0 - recovery_rate) * protection_leg / premium_leg * 10_000.0)


def bootstrap_piecewise_hazards(
    tenors_years: np.ndarray,
    market_spreads_bps: np.ndarray,
    config: CDSBootstrapConfig | None = None,
) -> pd.DataFrame:
    """Bootstrap one hazard-rate interval per quoted CDS tenor."""

    cfg = config or CDSBootstrapConfig()
    tenors = np.asarray(tenors_years, dtype=float)
    spreads = np.asarray(market_spreads_bps, dtype=float)
    if len(tenors) != len(spreads):
        raise ValueError("tenors_years and market_spreads_bps must have the same length")
    if np.any(tenors <= 0):
        raise ValueError("all tenors must be positive")
    if np.any(spreads <= 0):
        raise ValueError("all market spreads must be positive")

    order = np.argsort(tenors)
    tenors = tenors[order]
    spreads = spreads[order]

    hazards: list[float] = []
    rows: list[dict[str, float]] = []
    for tenor, target_spread in zip(tenors, spreads, strict=True):
        low = 1e-8
        high = cfg.max_hazard_rate

        for _ in range(cfg.max_iterations):
            mid = 0.5 * (low + high)
            trial_hazards = np.asarray([*hazards, mid], dtype=float)
            trial_tenors = tenors[: len(trial_hazards)]
            model_spread = par_spread_bps(
                trial_tenors,
                trial_hazards,
                float(tenor),
                recovery_rate=cfg.recovery_rate,
                discount_rate=cfg.discount_rate,
                premium_frequency=cfg.premium_frequency,
            )
            if model_spread < target_spread:
                low = mid
            else:
                high = mid
            if abs(model_spread - target_spread) <= cfg.tolerance_bps:
                break

        hazard = 0.5 * (low + high)
        hazards.append(float(hazard))
        survival = survival_at(float(tenor), tenors[: len(hazards)], np.asarray(hazards))
        model_spread = par_spread_bps(
            tenors[: len(hazards)],
            np.asarray(hazards),
            float(tenor),
            recovery_rate=cfg.recovery_rate,
            discount_rate=cfg.discount_rate,
            premium_frequency=cfg.premium_frequency,
        )
        rows.append(
            {
                "maturity_years": float(tenor),
                "market_cds_spread_bps": float(target_spread),
                "hazard_rate": float(hazard),
                "survival_probability": float(survival),
                "cumulative_default_probability": float(1.0 - survival),
                "model_cds_spread_bps": float(model_spread),
            }
        )

    return pd.DataFrame(rows)
