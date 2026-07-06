import pandas as pd

from systematic_credit.backtesting.performance_metrics import compute_performance_metrics


def test_performance_metrics_compute_core_outputs():
    pnl = pd.DataFrame(
        {
            "total_pnl": [100.0, -50.0, 150.0],
            "strategy_nav": [10_000_100.0, 10_000_050.0, 10_000_200.0],
            "daily_return": [0.00001, -0.000005, 0.000015],
        }
    )
    metrics = compute_performance_metrics(pnl, initial_capital=10_000_000)

    assert metrics["total_pnl"] == 200.0
    assert metrics["ending_nav"] == 10_000_200.0
    assert metrics["hit_rate"] == 2 / 3
