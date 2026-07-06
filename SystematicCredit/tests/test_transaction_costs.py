import pandas as pd

from systematic_credit.backtesting.transaction_costs import TransactionCostModel


def test_transaction_costs_increase_in_stress_regime():
    positions = pd.DataFrame(
        {
            "bond_id": ["A", "A"],
            "target_notional": [1_000_000.0, 2_000_000.0],
            "turnover_notional": [1_000_000.0, 1_000_000.0],
            "bond_bid_ask_bps": [10.0, 10.0],
            "cds_bid_ask_bps": [4.0, 4.0],
            "bond_liquidity_score": [0.8, 0.8],
            "macro_regime": ["neutral", "risk_off"],
        }
    )
    costed = TransactionCostModel().apply(positions)

    assert costed["transaction_costs"].iloc[0] > 0
    assert costed["transaction_costs"].iloc[1] > costed["transaction_costs"].iloc[0]
