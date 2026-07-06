import pandas as pd

from systematic_credit.signals.basis_rv_signal import BasisRVSignal, BasisRVSignalConfig


def test_basis_signal_enters_holds_exits_and_respects_cost_filter():
    df = pd.DataFrame(
        {
            "date": pd.bdate_range("2025-01-01", periods=5),
            "issuer": ["XYZ"] * 5,
            "bond_id": ["XYZ_01"] * 5,
            "basis_zscore": [0.0, 1.5, 1.0, 0.1, 1.6],
            "bond_cds_basis_bps": [5, 30, 20, 2, 35],
            "bond_bid_ask_bps": [5, 5, 5, 5, 50],
            "cds_bid_ask_bps": [2, 2, 2, 2, 20],
        }
    )
    signals = BasisRVSignal(
        BasisRVSignalConfig(entry_zscore=1.25, exit_zscore=0.25, max_transaction_cost_bps=20)
    ).generate(df)

    assert signals["rv_signal"].tolist() == [0, 1, 1, 0, 0]
    assert signals["signal_reason"].iloc[-1] == "cost_filter"
