import pandas as pd

from systematic_credit.basis.basis_calculator import BasisCalculator


def test_basis_calculator_adds_basis_and_zscore():
    dates = pd.bdate_range("2025-01-01", periods=20)
    matched = pd.DataFrame(
        {
            "date": dates,
            "issuer": ["XYZ"] * len(dates),
            "bond_id": ["XYZ_01"] * len(dates),
            "bond_spread_bps": [150 + i for i in range(len(dates))],
            "matched_cds_spread_bps": [130] * len(dates),
        }
    )
    basis = BasisCalculator(rolling_window=5, min_periods=3).calculate(matched)

    assert basis["bond_cds_basis_bps"].iloc[0] == 20
    assert "basis_zscore" in basis.columns
    assert basis["basis_zscore"].notna().all()
