"""Export dashboard source tables without binding the engine to an Excel library."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd


def export_dashboard_tables(
    tables: Mapping[str, pd.DataFrame],
    output_dir: str | Path,
    payload_name: str = "dashboard_payload.json",
) -> Path:
    """Write CSV tables and a JSON payload consumed by the dashboard builder."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {"tables": {}}
    for table_name, df in tables.items():
        clean = _json_ready_frame(df)
        csv_path = output_path / f"{table_name}.csv"
        clean.to_csv(csv_path, index=False)
        payload["tables"][table_name] = {
            "columns": list(clean.columns),
            "records": clean.to_dict(orient="records"),
            "csv": csv_path.name,
        }

    payload_path = output_path / payload_name
    payload_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload_path


def _json_ready_frame(df: pd.DataFrame) -> pd.DataFrame:
    clean = df.copy()
    for col in clean.columns:
        if pd.api.types.is_datetime64_any_dtype(clean[col]):
            clean[col] = clean[col].dt.strftime("%Y-%m-%d")
    clean = clean.replace([float("inf"), float("-inf")], pd.NA)
    return clean.astype(object).where(pd.notnull(clean), None)
