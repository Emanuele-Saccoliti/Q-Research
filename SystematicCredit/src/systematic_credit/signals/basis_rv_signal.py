"""Bond-CDS basis relative-value signals."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from systematic_credit.data.preprocess import require_columns, sort_panel


@dataclass(frozen=True)
class BasisRVSignalConfig:
    entry_zscore: float = 1.25
    exit_zscore: float = 0.25
    max_transaction_cost_bps: float = 35.0
    max_signal_strength: float = 2.0


class BasisRVSignal:
    """Generate stateful long/short credit signals from basis z-scores."""

    def __init__(self, config: BasisRVSignalConfig | None = None) -> None:
        self.config = config or BasisRVSignalConfig()

    def generate(self, basis: pd.DataFrame) -> pd.DataFrame:
        require_columns(
            basis,
            ["date", "issuer", "bond_id", "basis_zscore", "bond_cds_basis_bps"],
            "basis",
        )
        out = sort_panel(basis, ["issuer", "bond_id", "date"])
        if "bond_bid_ask_bps" in out.columns and "cds_bid_ask_bps" in out.columns:
            out["roundtrip_cost_bps"] = out["bond_bid_ask_bps"].fillna(0.0) + out[
                "cds_bid_ask_bps"
            ].fillna(0.0)
        elif "bond_bid_ask_bps" in out.columns:
            out["roundtrip_cost_bps"] = out["bond_bid_ask_bps"].fillna(0.0)
        else:
            out["roundtrip_cost_bps"] = 0.0

        frames: list[pd.DataFrame] = []
        for _, group in out.groupby(["issuer", "bond_id"], sort=False):
            active_signal = 0
            signals: list[int] = []
            reasons: list[str] = []
            for row in group.itertuples(index=False):
                z = float(row.basis_zscore)
                cost = float(row.roundtrip_cost_bps)
                cost_ok = cost <= self.config.max_transaction_cost_bps
                if not cost_ok:
                    active_signal = 0
                    reason = "cost_filter"
                elif active_signal == 0 and z >= self.config.entry_zscore:
                    active_signal = 1
                    reason = "long_cash_vs_cds"
                elif active_signal == 0 and z <= -self.config.entry_zscore:
                    active_signal = -1
                    reason = "rich_cash_reduce_or_hedge"
                elif active_signal != 0 and abs(z) <= self.config.exit_zscore:
                    active_signal = 0
                    reason = "mean_reversion_exit"
                elif active_signal != 0:
                    reason = "hold"
                else:
                    reason = "no_trade"
                signals.append(active_signal)
                reasons.append(reason)

            part = group.copy()
            part["rv_signal"] = signals
            part["signal_reason"] = reasons
            part["signal_strength"] = np.where(
                part["rv_signal"] == 0,
                0.0,
                np.minimum(
                    self.config.max_signal_strength,
                    np.maximum(0.0, np.abs(part["basis_zscore"]) / self.config.entry_zscore),
                ),
            )
            part["expected_edge_bps"] = np.maximum(
                0.0, np.abs(part["bond_cds_basis_bps"]) - part["roundtrip_cost_bps"]
            )
            frames.append(part)

        return sort_panel(pd.concat(frames, ignore_index=True), ["date", "issuer", "bond_id"])
