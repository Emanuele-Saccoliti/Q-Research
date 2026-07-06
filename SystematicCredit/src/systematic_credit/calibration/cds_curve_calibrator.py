"""CDS curve calibration across issuer-date panels."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from systematic_credit.calibration.cs01 import cs01_per_notional
from systematic_credit.calibration.hazard_rate_bootstrap import (
    CDSBootstrapConfig,
    bootstrap_piecewise_hazards,
    par_spread_bps,
)
from systematic_credit.data.preprocess import ensure_datetime, require_columns, sort_panel


@dataclass(frozen=True)
class CDSCurveCalibrationConfig:
    recovery_rate_default: float = 0.40
    discount_rate: float = 0.035
    premium_frequency: int = 4
    notional_for_cs01: float = 1_000_000.0


class CDSCurveCalibrator:
    """Calibrate issuer-date CDS curves into hazards and survival probabilities."""

    def __init__(self, config: CDSCurveCalibrationConfig | None = None) -> None:
        self.config = config or CDSCurveCalibrationConfig()

    def calibrate(self, cds_quotes: pd.DataFrame) -> pd.DataFrame:
        require_columns(
            cds_quotes,
            ["date", "issuer", "cds_tenor_years", "market_cds_spread_bps"],
            "cds_quotes",
        )
        quotes = sort_panel(ensure_datetime(cds_quotes), ["date", "issuer", "cds_tenor_years"])

        curves: list[pd.DataFrame] = []
        for (date, issuer), group in quotes.groupby(["date", "issuer"], sort=False):
            recovery_rate = float(
                group["recovery_rate"].dropna().iloc[0]
                if "recovery_rate" in group.columns and group["recovery_rate"].notna().any()
                else self.config.recovery_rate_default
            )
            bootstrap_cfg = CDSBootstrapConfig(
                recovery_rate=recovery_rate,
                discount_rate=self.config.discount_rate,
                premium_frequency=self.config.premium_frequency,
            )
            curve = bootstrap_piecewise_hazards(
                group["cds_tenor_years"].to_numpy(dtype=float),
                group["market_cds_spread_bps"].to_numpy(dtype=float),
                bootstrap_cfg,
            )
            curve.insert(0, "issuer", issuer)
            curve.insert(0, "date", date)
            curve["recovery_rate"] = recovery_rate

            for passthrough in ["rating", "sector", "cds_liquidity_score", "cds_bid_ask_bps"]:
                if passthrough in group.columns:
                    mapping = group.set_index("cds_tenor_years")[passthrough].to_dict()
                    curve[passthrough] = curve["maturity_years"].map(mapping)

            curve["cs01_per_1mm"] = [
                cs01_per_notional(
                    curve["maturity_years"].to_numpy(dtype=float),
                    curve["hazard_rate"].to_numpy(dtype=float),
                    maturity=float(maturity),
                    notional=self.config.notional_for_cs01,
                    discount_rate=self.config.discount_rate,
                    premium_frequency=self.config.premium_frequency,
                )
                for maturity in curve["maturity_years"]
            ]
            curves.append(curve)

        return pd.concat(curves, ignore_index=True) if curves else pd.DataFrame()

    def maturity_matched_spread(self, curve: pd.DataFrame, maturity_years: float) -> float:
        """Model-implied CDS spread at a non-standard maturity."""

        require_columns(curve, ["maturity_years", "hazard_rate"], "curve")
        sorted_curve = curve.sort_values("maturity_years")
        recovery_rate = float(
            sorted_curve["recovery_rate"].dropna().iloc[0]
            if "recovery_rate" in sorted_curve.columns and sorted_curve["recovery_rate"].notna().any()
            else self.config.recovery_rate_default
        )
        return par_spread_bps(
            sorted_curve["maturity_years"].to_numpy(dtype=float),
            sorted_curve["hazard_rate"].to_numpy(dtype=float),
            maturity=float(maturity_years),
            recovery_rate=recovery_rate,
            discount_rate=self.config.discount_rate,
            premium_frequency=self.config.premium_frequency,
        )

    def cs01_for_maturity(self, curve: pd.DataFrame, maturity_years: float) -> float:
        sorted_curve = curve.sort_values("maturity_years")
        return cs01_per_notional(
            sorted_curve["maturity_years"].to_numpy(dtype=float),
            sorted_curve["hazard_rate"].to_numpy(dtype=float),
            maturity=float(maturity_years),
            notional=self.config.notional_for_cs01,
            discount_rate=self.config.discount_rate,
            premium_frequency=self.config.premium_frequency,
        )

    @staticmethod
    def curve_error_summary(curves: pd.DataFrame) -> pd.DataFrame:
        require_columns(curves, ["market_cds_spread_bps", "model_cds_spread_bps"], "curves")
        out = curves.copy()
        out["calibration_error_bps"] = out["model_cds_spread_bps"] - out["market_cds_spread_bps"]
        return (
            out.groupby("issuer", as_index=False)["calibration_error_bps"]
            .agg(["mean", "max", "min"])
            .reset_index()
        )
