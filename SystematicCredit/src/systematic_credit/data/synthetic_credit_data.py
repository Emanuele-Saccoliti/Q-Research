"""Synthetic issuer-level CDS, bond, and macro data generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_ISSUERS: tuple[dict[str, Any], ...] = (
    {
        "issuer": "ALPHA_CHEM",
        "rating": "BBB",
        "sector": "Materials",
        "base_spread_bps": 165.0,
        "recovery_rate": 0.40,
    },
    {
        "issuer": "BETA_TEL",
        "rating": "BBB-",
        "sector": "Telecom",
        "base_spread_bps": 190.0,
        "recovery_rate": 0.38,
    },
    {
        "issuer": "CROWN_AUTO",
        "rating": "BB+",
        "sector": "Autos",
        "base_spread_bps": 245.0,
        "recovery_rate": 0.35,
    },
    {
        "issuer": "DELTA_PHARMA",
        "rating": "A-",
        "sector": "Healthcare",
        "base_spread_bps": 92.0,
        "recovery_rate": 0.42,
    },
    {
        "issuer": "ECHO_BANK",
        "rating": "A",
        "sector": "Financials",
        "base_spread_bps": 82.0,
        "recovery_rate": 0.40,
    },
    {
        "issuer": "FALCON_RETAIL",
        "rating": "BB",
        "sector": "Consumer",
        "base_spread_bps": 285.0,
        "recovery_rate": 0.33,
    },
)


@dataclass(frozen=True)
class DataGenerationConfig:
    """Configuration for reproducible synthetic market data."""

    start_date: str = "2024-01-02"
    end_date: str = "2025-12-31"
    seed: int = 42
    cds_tenors_years: tuple[int, ...] = (1, 3, 5, 7, 10)
    bonds_per_issuer: int = 2
    issuers: tuple[dict[str, Any], ...] = field(default_factory=lambda: DEFAULT_ISSUERS)


class SyntheticCreditDataGenerator:
    """Generate realistic-enough synthetic data for the full basis workflow."""

    def __init__(self, config: DataGenerationConfig | None = None) -> None:
        self.config = config or DataGenerationConfig()
        self.rng = np.random.default_rng(self.config.seed)

    def generate_all(self) -> dict[str, pd.DataFrame]:
        """Return macro, CDS quote, bond spread, and bond universe tables."""

        macro = self.generate_macro_factors()
        cds_quotes = self.generate_cds_quotes(macro)
        bond_universe = self.generate_bond_universe()
        bonds = self.generate_bond_spreads(macro, cds_quotes, bond_universe)
        return {
            "macro": macro,
            "cds_quotes": cds_quotes,
            "bond_universe": bond_universe,
            "bonds": bonds,
        }

    def generate_macro_factors(self) -> pd.DataFrame:
        dates = pd.bdate_range(self.config.start_date, self.config.end_date)
        n = len(dates)

        risk_factor = np.zeros(n)
        for i in range(1, n):
            shock = self.rng.normal(0.0, 0.18)
            jump = self.rng.normal(0.65, 0.25) if self.rng.random() < 0.018 else 0.0
            risk_factor[i] = 0.94 * risk_factor[i - 1] + shock + jump

        credit_index_proxy = 100.0 + 22.0 * risk_factor + np.cumsum(
            self.rng.normal(0.03, 0.45, n)
        )
        rates_proxy = 3.35 + np.cumsum(self.rng.normal(0.0, 0.018, n)) - 0.045 * risk_factor
        equity_proxy = 100.0 + np.cumsum(self.rng.normal(0.04, 0.75, n)) - 2.8 * risk_factor
        volatility_proxy = np.clip(18.0 + 7.0 * risk_factor + self.rng.normal(0.0, 1.8, n), 9, None)
        liquidity_proxy = np.clip(0.45 + 0.16 * risk_factor + self.rng.normal(0.0, 0.05, n), 0.05, 0.98)

        regimes = self._classify_generated_regimes(
            credit_index_proxy, equity_proxy, volatility_proxy, liquidity_proxy
        )

        return pd.DataFrame(
            {
                "date": dates,
                "rates_proxy": rates_proxy,
                "credit_index_proxy": credit_index_proxy,
                "equity_proxy": equity_proxy,
                "volatility_proxy": volatility_proxy,
                "liquidity_proxy": liquidity_proxy,
                "generated_regime": regimes,
            }
        )

    def generate_cds_quotes(self, macro: pd.DataFrame) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        tenor_array = np.asarray(self.config.cds_tenors_years, dtype=float)
        tenor_slope = np.log1p(tenor_array) / np.log1p(10.0)

        for issuer_cfg in self.config.issuers:
            issuer_noise = self._ar_noise(len(macro), persistence=0.90, sigma=4.5)
            curve_slope_shift = self.rng.normal(0.0, 4.0)
            liquidity_score = float(np.clip(self.rng.normal(0.78, 0.08), 0.45, 0.96))

            for date_idx, macro_row in macro.reset_index(drop=True).iterrows():
                risk_pressure = macro_row["credit_index_proxy"] - 100.0
                regime_addon = {
                    "risk_on": -7.0,
                    "neutral": 0.0,
                    "spread_widening": 10.0,
                    "risk_off": 22.0,
                    "liquidity_stress": 35.0,
                }.get(macro_row["generated_regime"], 0.0)

                for tenor, slope_weight in zip(tenor_array, tenor_slope, strict=True):
                    base = issuer_cfg["base_spread_bps"]
                    spread = (
                        base
                        + 0.82 * risk_pressure
                        + regime_addon
                        + 34.0 * slope_weight
                        + curve_slope_shift * tenor / 5.0
                        + issuer_noise[date_idx]
                        + self.rng.normal(0.0, 2.4)
                    )
                    spread = float(max(18.0, spread))
                    cds_bid_ask_bps = float(
                        max(1.5, 0.025 * spread + 4.0 * (1.0 - liquidity_score))
                    )
                    rows.append(
                        {
                            "date": macro_row["date"],
                            "issuer": issuer_cfg["issuer"],
                            "rating": issuer_cfg["rating"],
                            "sector": issuer_cfg["sector"],
                            "cds_tenor_years": float(tenor),
                            "market_cds_spread_bps": spread,
                            "recovery_rate": issuer_cfg["recovery_rate"],
                            "cds_liquidity_score": liquidity_score,
                            "cds_bid_ask_bps": cds_bid_ask_bps,
                        }
                    )

        return pd.DataFrame(rows)

    def generate_bond_universe(self) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        maturity_grid = np.array([2.25, 3.75, 5.5, 6.5, 8.25, 9.75])

        for issuer_cfg in self.config.issuers:
            for bond_idx in range(self.config.bonds_per_issuer):
                maturity = float(
                    maturity_grid[(bond_idx + self.rng.integers(0, len(maturity_grid))) % len(maturity_grid)]
                    + self.rng.normal(0.0, 0.18)
                )
                maturity = float(np.clip(maturity, 1.5, 10.5))
                liquidity_score = float(np.clip(self.rng.normal(0.70, 0.13), 0.30, 0.95))
                rows.append(
                    {
                        "issuer": issuer_cfg["issuer"],
                        "rating": issuer_cfg["rating"],
                        "sector": issuer_cfg["sector"],
                        "bond_id": f"{issuer_cfg['issuer']}_{bond_idx + 1:02d}",
                        "bond_maturity_years": maturity,
                        "coupon_pct": float(np.clip(self.rng.normal(4.7, 0.9), 2.0, 8.5)),
                        "bond_liquidity_score": liquidity_score,
                        "recovery_rate": issuer_cfg["recovery_rate"],
                    }
                )

        return pd.DataFrame(rows)

    def generate_bond_spreads(
        self,
        macro: pd.DataFrame,
        cds_quotes: pd.DataFrame,
        bond_universe: pd.DataFrame,
    ) -> pd.DataFrame:
        cds_pivot = (
            cds_quotes.pivot_table(
                index=["date", "issuer"],
                columns="cds_tenor_years",
                values="market_cds_spread_bps",
            )
            .sort_index()
            .reset_index()
        )
        tenor_cols = np.asarray(self.config.cds_tenors_years, dtype=float)
        rows: list[dict[str, Any]] = []

        for _, bond in bond_universe.iterrows():
            basis_noise = self._ar_noise(len(macro), persistence=0.93, sigma=5.0)
            structural_basis = self.rng.normal(4.0, 14.0) + 18.0 * (1.0 - bond["bond_liquidity_score"])
            issuer_cds = cds_pivot[cds_pivot["issuer"] == bond["issuer"]].reset_index(drop=True)

            for date_idx, macro_row in macro.reset_index(drop=True).iterrows():
                cds_row = issuer_cds.iloc[date_idx]
                cds_curve = cds_row[tenor_cols].to_numpy(dtype=float)
                matched_cds = float(np.interp(bond["bond_maturity_years"], tenor_cols, cds_curve))
                risk_stress = max(0.0, macro_row["credit_index_proxy"] - 100.0)
                liquidity_wedge = (1.0 - bond["bond_liquidity_score"]) * (12.0 + 0.16 * risk_stress)
                basis_bps = structural_basis + liquidity_wedge + basis_noise[date_idx]
                bond_spread = float(max(25.0, matched_cds + basis_bps + self.rng.normal(0.0, 2.8)))
                bond_bid_ask_bps = float(
                    max(
                        4.0,
                        0.035 * bond_spread
                        + 14.0 * (1.0 - bond["bond_liquidity_score"])
                        + 4.0 * (macro_row["generated_regime"] in {"risk_off", "liquidity_stress"}),
                    )
                )

                rows.append(
                    {
                        "date": macro_row["date"],
                        "issuer": bond["issuer"],
                        "rating": bond["rating"],
                        "sector": bond["sector"],
                        "bond_id": bond["bond_id"],
                        "bond_maturity_years": float(bond["bond_maturity_years"]),
                        "coupon_pct": float(bond["coupon_pct"]),
                        "bond_spread_bps": bond_spread,
                        "recovery_rate": float(bond["recovery_rate"]),
                        "bond_liquidity_score": float(bond["bond_liquidity_score"]),
                        "bond_bid_ask_bps": bond_bid_ask_bps,
                        "rates_proxy": float(macro_row["rates_proxy"]),
                        "credit_index_proxy": float(macro_row["credit_index_proxy"]),
                        "equity_proxy": float(macro_row["equity_proxy"]),
                        "volatility_proxy": float(macro_row["volatility_proxy"]),
                        "liquidity_proxy": float(macro_row["liquidity_proxy"]),
                        "generated_regime": macro_row["generated_regime"],
                    }
                )

        return pd.DataFrame(rows)

    def _ar_noise(self, n: int, persistence: float, sigma: float) -> np.ndarray:
        noise = np.zeros(n)
        for i in range(1, n):
            noise[i] = persistence * noise[i - 1] + self.rng.normal(0.0, sigma)
        return noise

    @staticmethod
    def _classify_generated_regimes(
        credit_index_proxy: np.ndarray,
        equity_proxy: np.ndarray,
        volatility_proxy: np.ndarray,
        liquidity_proxy: np.ndarray,
    ) -> list[str]:
        credit_change = np.r_[0.0, np.diff(credit_index_proxy)]
        equity_return = np.r_[0.0, np.diff(equity_proxy) / np.maximum(equity_proxy[:-1], 1e-9)]
        vol_q80 = float(np.quantile(volatility_proxy, 0.80))
        liq_q85 = float(np.quantile(liquidity_proxy, 0.85))

        regimes: list[str] = []
        for dc, er, vol, liq in zip(
            credit_change, equity_return, volatility_proxy, liquidity_proxy, strict=True
        ):
            if liq > liq_q85 and vol > vol_q80:
                regimes.append("liquidity_stress")
            elif dc > 2.2 and er < -0.004:
                regimes.append("risk_off")
            elif dc > 1.2:
                regimes.append("spread_widening")
            elif dc < -1.0 and er > 0.002:
                regimes.append("risk_on")
            else:
                regimes.append("neutral")
        return regimes
