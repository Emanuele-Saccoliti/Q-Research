#!/usr/bin/env python3
"""Run the end-to-end bond-CDS basis demo pipeline."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from systematic_credit.pipeline import run_demo_pipeline


def main() -> None:
    result = run_demo_pipeline(PROJECT_ROOT)
    metrics = result["metrics"]
    print("Pipeline complete")
    print(f"Dashboard payload: {result['payload_path']}")
    print(f"Total P&L: {metrics['total_pnl']:,.0f}")
    print(f"Sharpe ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"Max drawdown: {metrics['max_drawdown']:.2%}")


if __name__ == "__main__":
    main()
