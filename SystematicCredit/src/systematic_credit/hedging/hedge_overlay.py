"""Macro hedge overlay for CS01 exposure."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from systematic_credit.data.preprocess import ensure_datetime, require_columns, sort_panel


@dataclass(frozen=True)
class HedgeOverlayConfig:
    credit_index_cs01_per_1mm: float = 450.0
    hedge_ratios: dict[str, float] = field(
        default_factory=lambda: {
            "risk_on": 0.0,
            "neutral": 0.0,
            "spread_widening": 0.35,
            "risk_off": 0.65,
            "liquidity_stress": 0.85,
        }
    )
    exposure_multipliers: dict[str, float] = field(
        default_factory=lambda: {
            "risk_on": 1.10,
            "neutral": 1.00,
            "spread_widening": 0.75,
            "risk_off": 0.55,
            "liquidity_stress": 0.40,
        }
    )


class MacroHedgeOverlay:
    """Reduce exposure and create a portfolio-level credit-index hedge."""

    def __init__(self, config: HedgeOverlayConfig | None = None) -> None:
        self.config = config or HedgeOverlayConfig()

    def apply(
        self,
        positions: pd.DataFrame,
        macro_regime: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        require_columns(positions, ["date", "bond_id", "target_notional", "target_cs01"], "positions")
        require_columns(macro_regime, ["date", "macro_regime", "credit_index_proxy"], "macro_regime")

        pos = sort_panel(ensure_datetime(positions), ["date", "issuer", "bond_id"])
        macro = sort_panel(ensure_datetime(macro_regime), ["date"])
        macro_cols = [
            "macro_regime",
            "credit_index_proxy",
            "risk_reduction_multiplier",
            "credit_index_change_bps",
            "equity_return",
            "volatility_proxy",
        ]
        pos = pos.drop(columns=[col for col in macro_cols if col in pos.columns], errors="ignore")
        pos = pos.merge(
            macro[["date", *macro_cols]],
            on="date",
            how="left",
        )
        pos["macro_regime"] = pos["macro_regime"].fillna("neutral")
        pos["exposure_multiplier"] = pos["macro_regime"].map(
            self.config.exposure_multipliers
        ).fillna(1.0)
        pos["pre_hedge_notional"] = pos["target_notional"]
        pos["pre_hedge_cs01"] = pos["target_cs01"]
        pos["target_notional"] = pos["target_notional"] * pos["exposure_multiplier"]
        pos["target_cs01"] = pos["target_cs01"] * pos["exposure_multiplier"]

        hedge_rows: list[dict[str, float | str | pd.Timestamp]] = []
        for date, group in pos.groupby("date", sort=False):
            regime = str(group["macro_regime"].iloc[0])
            hedge_ratio = float(self.config.hedge_ratios.get(regime, 0.0))
            net_cs01 = float(group["target_cs01"].sum())
            hedge_cs01 = -net_cs01 * hedge_ratio
            hedge_notional = hedge_cs01 / self.config.credit_index_cs01_per_1mm * 1_000_000.0
            hedge_rows.append(
                {
                    "date": date,
                    "macro_regime": regime,
                    "net_strategy_cs01": net_cs01,
                    "gross_strategy_cs01": float(group["target_cs01"].abs().sum()),
                    "hedge_ratio": hedge_ratio,
                    "hedge_cs01": hedge_cs01,
                    "hedge_notional": hedge_notional,
                    "credit_index_proxy": float(group["credit_index_proxy"].iloc[0]),
                }
            )

        hedge_history = pd.DataFrame(hedge_rows)
        return sort_panel(pos, ["date", "issuer", "bond_id"]), sort_panel(hedge_history, ["date"])
