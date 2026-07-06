"""Strategy performance metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def max_drawdown(nav: pd.Series) -> float:
    peak = nav.cummax()
    drawdown = nav / peak - 1.0
    return float(drawdown.min())


def compute_performance_metrics(
    pnl: pd.DataFrame,
    initial_capital: float = 10_000_000.0,
    annualization_factor: int = 252,
) -> dict[str, float]:
    if pnl.empty:
        return {
            "total_pnl": 0.0,
            "total_return": 0.0,
            "annualized_volatility": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "hit_rate": 0.0,
        }

    returns = pnl["daily_return"].fillna(0.0)
    total_pnl = float(pnl["total_pnl"].sum())
    daily_vol = float(returns.std(ddof=0))
    sharpe = 0.0 if daily_vol == 0 else float(returns.mean() / daily_vol * np.sqrt(annualization_factor))
    return {
        "total_pnl": total_pnl,
        "total_return": total_pnl / initial_capital,
        "annualized_volatility": daily_vol * np.sqrt(annualization_factor),
        "sharpe_ratio": sharpe,
        "max_drawdown": max_drawdown(pnl["strategy_nav"]),
        "hit_rate": float((pnl["total_pnl"] > 0).mean()),
        "ending_nav": float(pnl["strategy_nav"].iloc[-1]),
    }
