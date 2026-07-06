"""Load market or generated data from local files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_csv(path: str | Path, parse_dates: tuple[str, ...] = ("date",)) -> pd.DataFrame:
    """Load a CSV file and parse common date columns when present."""

    path = Path(path)
    header = pd.read_csv(path, nrows=0)
    date_cols = [col for col in parse_dates if col in header.columns]
    return pd.read_csv(path, parse_dates=date_cols)


def load_output_bundle(output_dir: str | Path) -> dict[str, pd.DataFrame]:
    """Load every CSV in an output directory into a dictionary keyed by stem."""

    output_path = Path(output_dir)
    return {csv_path.stem: load_csv(csv_path) for csv_path in sorted(output_path.glob("*.csv"))}
