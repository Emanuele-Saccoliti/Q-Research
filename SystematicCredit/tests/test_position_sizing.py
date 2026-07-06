import pandas as pd

from systematic_credit.risk.position_sizing import CS01WeightedPositionSizer, PositionSizingConfig


def test_position_sizer_scales_inverse_to_cs01_and_caps_gross():
    signals = pd.DataFrame(
        {
            "date": ["2025-01-02", "2025-01-02"],
            "issuer": ["A", "B"],
            "rating": ["BBB", "BBB"],
            "bond_id": ["A_01", "B_01"],
            "rv_signal": [1, 1],
            "signal_strength": [1.0, 1.0],
            "matched_cds_cs01_per_1mm": [100.0, 500.0],
        }
    )
    sized = CS01WeightedPositionSizer(
        PositionSizingConfig(target_cs01_per_trade=1_000, max_gross_notional=12_000_000)
    ).size(signals)

    assert sized.loc[sized["bond_id"] == "A_01", "target_notional"].iloc[0] > sized.loc[
        sized["bond_id"] == "B_01", "target_notional"
    ].iloc[0]
    assert sized["target_notional"].abs().sum() <= 12_000_000
