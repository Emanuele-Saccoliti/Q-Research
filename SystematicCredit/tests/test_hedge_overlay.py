import pandas as pd

from systematic_credit.hedging.hedge_overlay import MacroHedgeOverlay


def test_hedge_overlay_reduces_risk_off_exposure_and_offsets_cs01():
    positions = pd.DataFrame(
        {
            "date": ["2025-01-02"],
            "issuer": ["XYZ"],
            "bond_id": ["XYZ_01"],
            "target_notional": [5_000_000.0],
            "target_cs01": [2_500.0],
        }
    )
    macro = pd.DataFrame(
        {
            "date": ["2025-01-02"],
            "macro_regime": ["risk_off"],
            "credit_index_proxy": [110.0],
            "risk_reduction_multiplier": [0.55],
            "credit_index_change_bps": [5.0],
            "equity_return": [-0.01],
            "volatility_proxy": [30.0],
        }
    )

    adjusted, hedge = MacroHedgeOverlay().apply(positions, macro)

    assert adjusted["target_notional"].iloc[0] < positions["target_notional"].iloc[0]
    assert hedge["hedge_cs01"].iloc[0] < 0
