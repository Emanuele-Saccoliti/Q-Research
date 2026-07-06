"""Rule-based macro regime classifier."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from systematic_credit.data.preprocess import ensure_datetime, require_columns, sort_panel


@dataclass(frozen=True)
class MacroRegimeConfig:
    credit_widening_threshold_bps: float = 1.2
    risk_off_credit_threshold_bps: float = 2.2
    risk_off_equity_return: float = -0.004
    risk_on_credit_threshold_bps: float = -1.0
    risk_on_equity_return: float = 0.002
    volatility_quantile: float = 0.80
    liquidity_quantile: float = 0.85


class MacroRegimeClassifier:
    """Classify daily macro regimes from transparent proxy rules."""

    def __init__(self, config: MacroRegimeConfig | None = None) -> None:
        self.config = config or MacroRegimeConfig()

    def classify(self, macro: pd.DataFrame) -> pd.DataFrame:
        require_columns(
            macro,
            ["date", "credit_index_proxy", "equity_proxy", "volatility_proxy", "liquidity_proxy"],
            "macro",
        )
        out = sort_panel(ensure_datetime(macro), ["date"])
        out["credit_index_change_bps"] = out["credit_index_proxy"].diff().fillna(0.0)
        out["equity_return"] = out["equity_proxy"].pct_change().fillna(0.0)
        out["rates_change_bps"] = (
            out["rates_proxy"].diff().fillna(0.0) * 100.0 if "rates_proxy" in out.columns else 0.0
        )
        out["volatility_change"] = out["volatility_proxy"].diff().fillna(0.0)

        vol_cutoff = float(out["volatility_proxy"].quantile(self.config.volatility_quantile))
        liq_cutoff = float(out["liquidity_proxy"].quantile(self.config.liquidity_quantile))
        regimes: list[str] = []
        for row in out.itertuples(index=False):
            if row.liquidity_proxy >= liq_cutoff and row.volatility_proxy >= vol_cutoff:
                regimes.append("liquidity_stress")
            elif (
                row.credit_index_change_bps >= self.config.risk_off_credit_threshold_bps
                and row.equity_return <= self.config.risk_off_equity_return
            ):
                regimes.append("risk_off")
            elif row.credit_index_change_bps >= self.config.credit_widening_threshold_bps:
                regimes.append("spread_widening")
            elif (
                row.credit_index_change_bps <= self.config.risk_on_credit_threshold_bps
                and row.equity_return >= self.config.risk_on_equity_return
            ):
                regimes.append("risk_on")
            else:
                regimes.append("neutral")
        out["macro_regime"] = regimes
        out["risk_reduction_multiplier"] = np.select(
            [
                out["macro_regime"].eq("liquidity_stress"),
                out["macro_regime"].eq("risk_off"),
                out["macro_regime"].eq("spread_widening"),
                out["macro_regime"].eq("risk_on"),
            ],
            [0.40, 0.55, 0.75, 1.10],
            default=1.0,
        )
        return out
