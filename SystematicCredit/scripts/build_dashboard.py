#!/usr/bin/env python3
"""Build the Systematic Credit Excel dashboard from the pipeline payload."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import xlsxwriter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_PATH = PROJECT_ROOT / "data" / "output" / "dashboard_payload.json"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "systematic_credit_toolkit"
OUTPUT_XLSX = OUTPUT_DIR / "bond_cds_basis_dashboard.xlsx"
WORKBOOK_ROW_LIMIT = 1_200

SHEET_ORDER = [
    "Dashboard",
    "CDS_Curves",
    "Hazard_Survival",
    "Bond_CDS_Basis",
    "RV_Signals",
    "Positions",
    "Macro_Regime",
    "Hedge_Overlay",
    "PnL_Attribution",
    "Performance",
    "Stress_Test",
    "Config",
]

TABLE_TO_SHEET = {
    "cds_curves": "CDS_Curves",
    "hazard_survival": "Hazard_Survival",
    "bond_cds_basis": "Bond_CDS_Basis",
    "rv_signals": "RV_Signals",
    "positions": "Positions",
    "macro": "Macro_Regime",
    "hedge_overlay": "Hedge_Overlay",
    "pnl_attribution": "PnL_Attribution",
    "performance": "Performance",
    "stress_test": "Stress_Test",
    "config": "Config",
}

COLORS = {
    "navy": "#12355B",
    "green": "#15803D",
    "gray": "#E5E7EB",
    "border": "#CBD5E1",
    "text": "#111827",
    "white": "#FFFFFF",
}


def main() -> None:
    if not PAYLOAD_PATH.exists():
        raise FileNotFoundError(
            f"Dashboard payload not found: {PAYLOAD_PATH}. "
            "Run scripts/run_pipeline.py first."
        )

    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    workbook = xlsxwriter.Workbook(OUTPUT_XLSX)
    workbook.set_properties(
        {
            "title": "Bond-CDS Basis Trading Dashboard",
            "subject": "Systematic credit relative-value research",
            "author": "Q-Research",
        }
    )
    formats = build_formats(workbook)
    sheets = {name: workbook.add_worksheet(name) for name in SHEET_ORDER}
    for sheet in sheets.values():
        sheet.hide_gridlines(2)

    for table_name, sheet_name in TABLE_TO_SHEET.items():
        table = payload["tables"].get(table_name)
        if table:
            write_data_sheet(
                workbook,
                sheets[sheet_name],
                table_name,
                table,
                formats,
            )

    write_dashboard(workbook, sheets["Dashboard"], payload, formats)
    workbook.close()
    print(f"Dashboard written to {OUTPUT_XLSX}")


def build_formats(workbook: xlsxwriter.Workbook) -> dict[str, Any]:
    base = {"font_name": "Aptos", "font_color": COLORS["text"]}
    return {
        "title": workbook.add_format(
            {
                **base,
                "bold": True,
                "font_size": 16,
                "font_color": COLORS["white"],
                "bg_color": COLORS["navy"],
                "align": "left",
                "valign": "vcenter",
            }
        ),
        "subtitle": workbook.add_format(
            {
                **base,
                "italic": True,
                "bg_color": COLORS["gray"],
                "valign": "vcenter",
            }
        ),
        "header": workbook.add_format(
            {
                **base,
                "bold": True,
                "font_color": COLORS["white"],
                "bg_color": COLORS["navy"],
                "border": 1,
                "border_color": COLORS["border"],
            }
        ),
        "text": workbook.add_format({**base, "border": 1, "border_color": COLORS["border"]}),
        "currency": workbook.add_format(
            {
                **base,
                "num_format": "$#,##0;[Red]($#,##0);-",
                "border": 1,
                "border_color": COLORS["border"],
            }
        ),
        "percent": workbook.add_format(
            {
                **base,
                "num_format": "0.0%;[Red](0.0%);-",
                "border": 1,
                "border_color": COLORS["border"],
            }
        ),
        "number": workbook.add_format(
            {
                **base,
                "num_format": "0.00",
                "border": 1,
                "border_color": COLORS["border"],
            }
        ),
        "integer": workbook.add_format(
            {
                **base,
                "num_format": "#,##0",
                "border": 1,
                "border_color": COLORS["border"],
            }
        ),
        "bps": workbook.add_format(
            {
                **base,
                "num_format": "#,##0.0;[Red](#,##0.0);-",
                "border": 1,
                "border_color": COLORS["border"],
            }
        ),
        "date": workbook.add_format(
            {
                **base,
                "num_format": "yyyy-mm-dd",
                "border": 1,
                "border_color": COLORS["border"],
            }
        ),
    }


def write_data_sheet(
    workbook: xlsxwriter.Workbook,
    sheet: xlsxwriter.worksheet.Worksheet,
    table_name: str,
    table: dict[str, Any],
    formats: dict[str, Any],
) -> None:
    columns = table["columns"]
    records = limit_workbook_rows(table["records"], table_name)

    for col_idx, column_name in enumerate(columns):
        sheet.write(0, col_idx, format_header(column_name), formats["header"])
        column_format = workbook.add_format(
            {
                "font_name": "Aptos",
                "font_color": COLORS["text"],
                "num_format": number_format_for(column_name),
                "border": 1,
                "border_color": COLORS["border"],
            }
        )
        sheet.set_column(col_idx, col_idx, width_for(column_name), column_format)

    for row_idx, record in enumerate(records, start=1):
        for col_idx, column_name in enumerate(columns):
            write_cell(sheet, row_idx, col_idx, record.get(column_name), column_name)

    last_row = max(len(records), 1)
    last_col = len(columns) - 1
    sheet.add_table(
        0,
        0,
        last_row,
        last_col,
        {
            "name": to_table_name(table_name),
            "style": "Table Style Medium 2",
            "columns": [{"header": format_header(column)} for column in columns],
        },
    )
    sheet.freeze_panes(1, 0)


def write_cell(
    sheet: xlsxwriter.worksheet.Worksheet,
    row: int,
    col: int,
    value: Any,
    column_name: str,
) -> None:
    if value is None:
        sheet.write_blank(row, col, None)
    elif "date" in column_name.lower() and isinstance(value, str):
        try:
            sheet.write_datetime(row, col, datetime.fromisoformat(value))
        except ValueError:
            sheet.write(row, col, value)
    else:
        sheet.write(row, col, value)


def limit_workbook_rows(records: list[dict[str, Any]], table_name: str) -> list[dict[str, Any]]:
    unlimited = {
        "macro",
        "hedge_overlay",
        "pnl_attribution",
        "performance",
        "stress_test",
        "config",
    }
    if table_name in unlimited or len(records) <= WORKBOOK_ROW_LIMIT:
        return records
    return records[-WORKBOOK_ROW_LIMIT:]


def write_dashboard(
    workbook: xlsxwriter.Workbook,
    sheet: xlsxwriter.worksheet.Worksheet,
    payload: dict[str, Any],
    formats: dict[str, Any],
) -> None:
    sheet.set_row(0, 24)
    sheet.merge_range("A1:H1", "Bond-CDS Basis Trading Dashboard", formats["title"])
    sheet.merge_range(
        "A2:H2",
        "Synthetic issuer-level research dashboard | CDS curves, basis signals, "
        "CS01 exposure, hedging, and P&L attribution",
        formats["subtitle"],
    )
    sheet.set_column("A:H", 15)
    sheet.set_column("I:Q", 12)

    write_kpis(sheet, payload, formats)
    helper_ranges = write_dashboard_helpers(sheet, payload, formats)
    add_dashboard_charts(workbook, sheet, helper_ranges)


def write_kpis(
    sheet: xlsxwriter.worksheet.Worksheet,
    payload: dict[str, Any],
    formats: dict[str, Any],
) -> None:
    performance = payload["tables"]["performance"]["records"][0]
    hedge_records = payload["tables"]["hedge_overlay"]["records"]
    latest_hedge = hedge_records[-1] if hedge_records else {}

    sheet.write_row("A4", ["Metric", "Value", "Format"], formats["header"])
    kpis = [
        ("Total P&L", performance.get("total_pnl"), "Currency", formats["currency"]),
        ("Total Return", performance.get("total_return"), "Percent", formats["percent"]),
        ("Sharpe Ratio", performance.get("sharpe_ratio"), "Number", formats["number"]),
        ("Max Drawdown", performance.get("max_drawdown"), "Percent", formats["percent"]),
        ("Hit Rate", performance.get("hit_rate"), "Percent", formats["percent"]),
        ("Ending NAV", performance.get("ending_nav"), "Currency", formats["currency"]),
    ]
    for row, (label, value, unit, value_format) in enumerate(kpis, start=4):
        sheet.write(row, 0, label, formats["text"])
        sheet.write(row, 1, value, value_format)
        sheet.write(row, 2, unit, formats["text"])

    sheet.write_row("E4", ["Latest Risk", "Value", "Unit"], formats["header"])
    risk_rows = [
        ("Macro Regime", latest_hedge.get("macro_regime"), "label", formats["text"]),
        ("Net Strategy CS01", latest_hedge.get("net_strategy_cs01"), "per bp", formats["integer"]),
        ("Gross Strategy CS01", latest_hedge.get("gross_strategy_cs01"), "per bp", formats["integer"]),
        ("Hedge Ratio", latest_hedge.get("hedge_ratio"), "%", formats["percent"]),
        ("Hedge CS01", latest_hedge.get("hedge_cs01"), "per bp", formats["integer"]),
        ("Hedge Notional", latest_hedge.get("hedge_notional"), "currency", formats["currency"]),
    ]
    for row, (label, value, unit, value_format) in enumerate(risk_rows, start=4):
        sheet.write(row, 4, label, formats["text"])
        sheet.write(row, 5, value, value_format)
        sheet.write(row, 6, unit, formats["text"])


def write_dashboard_helpers(
    sheet: xlsxwriter.worksheet.Worksheet,
    payload: dict[str, Any],
    formats: dict[str, Any],
) -> dict[str, tuple[int, int]]:
    pnl_records = payload["tables"]["pnl_attribution"]["records"][-60:]
    sheet.write_row("A13", ["Date", "Cumulative P&L"], formats["header"])
    for row, record in enumerate(pnl_records, start=13):
        date_value = record.get("date")
        try:
            date_value = datetime.fromisoformat(date_value) if isinstance(date_value, str) else date_value
        except ValueError:
            pass
        sheet.write(row, 0, date_value, formats["date"])
        sheet.write(row, 1, record.get("cumulative_total_pnl"), formats["currency"])

    summary = payload["tables"]["dashboard_summary"]["records"]
    latest_basis = [row for row in summary if row.get("summary_type") == "latest_basis"]
    sheet.write_row("D13", ["Bond", "Basis bps", "Z-score", "Signal"], formats["header"])
    for row, record in enumerate(latest_basis, start=13):
        sheet.write(row, 3, record.get("bond_id"), formats["text"])
        sheet.write(row, 4, record.get("bond_cds_basis_bps"), formats["bps"])
        sheet.write(row, 5, record.get("basis_zscore"), formats["number"])
        sheet.write(row, 6, record.get("rv_signal"), formats["text"])

    regime_counts = [row for row in summary if row.get("summary_type") == "regime_counts"]
    sheet.write_row("A77", ["Regime", "Days"], formats["header"])
    for row, record in enumerate(regime_counts, start=77):
        sheet.write(row, 0, record.get("macro_regime"), formats["text"])
        sheet.write(row, 1, record.get("days"), formats["integer"])

    attribution = [
        ("Basis Convergence", "basis_convergence_pnl", 1),
        ("Credit Spread", "credit_spread_pnl", 2),
        ("Hedge", "hedge_pnl", 5),
        ("Carry", "carry_pnl", 3),
        ("Transaction Costs", "transaction_costs", 4),
    ]
    sheet.write_row("D30", ["P&L Component", "Total"], formats["header"])
    all_pnl_records = payload["tables"]["pnl_attribution"]["records"]
    for row, (label, key, _) in enumerate(attribution, start=30):
        value = sum(float(record.get(key) or 0.0) for record in all_pnl_records)
        if key == "transaction_costs":
            value = -value
        sheet.write(row, 3, label, formats["text"])
        sheet.write(row, 4, value, formats["currency"])

    return {
        "pnl": (13, len(pnl_records)),
        "basis": (13, len(latest_basis)),
        "attribution": (30, len(attribution)),
        "regime": (77, len(regime_counts)),
    }


def add_dashboard_charts(
    workbook: xlsxwriter.Workbook,
    sheet: xlsxwriter.worksheet.Worksheet,
    ranges: dict[str, tuple[int, int]],
) -> None:
    pnl_start, pnl_count = ranges["pnl"]
    if pnl_count:
        chart = workbook.add_chart({"type": "line"})
        chart.add_series(
            {
                "name": "Cumulative P&L",
                "categories": ["Dashboard", pnl_start, 0, pnl_start + pnl_count - 1, 0],
                "values": ["Dashboard", pnl_start, 1, pnl_start + pnl_count - 1, 1],
                "line": {"color": COLORS["navy"], "width": 2.25},
            }
        )
        chart.set_title({"name": "Cumulative P&L"})
        chart.set_legend({"none": True})
        chart.set_y_axis({"num_format": "$#,##0"})
        sheet.insert_chart("J3", chart, {"x_scale": 1.0, "y_scale": 1.0})

    add_column_chart(workbook, sheet, "J20", "Latest Bond-CDS Basis (bps)", ranges["basis"], 3, 4, "#,##0.0")
    add_column_chart(workbook, sheet, "J37", "P&L Attribution", ranges["attribution"], 3, 4, "$#,##0")
    add_column_chart(workbook, sheet, "A88", "Macro Regime Days", ranges["regime"], 0, 1, "#,##0")


def add_column_chart(
    workbook: xlsxwriter.Workbook,
    sheet: xlsxwriter.worksheet.Worksheet,
    position: str,
    title: str,
    row_range: tuple[int, int],
    category_col: int,
    value_col: int,
    number_format: str,
) -> None:
    start, count = row_range
    if not count:
        return
    chart = workbook.add_chart({"type": "column"})
    chart.add_series(
        {
            "name": title,
            "categories": ["Dashboard", start, category_col, start + count - 1, category_col],
            "values": ["Dashboard", start, value_col, start + count - 1, value_col],
            "fill": {"color": COLORS["navy"]},
            "border": {"color": COLORS["navy"]},
        }
    )
    chart.set_title({"name": title})
    chart.set_legend({"none": True})
    chart.set_y_axis({"num_format": number_format})
    sheet.insert_chart(position, chart, {"x_scale": 1.0, "y_scale": 1.0})


def format_header(value: str) -> str:
    return str(value).replace("_", " ").title()


def number_format_for(column_name: str) -> str:
    column = column_name.lower()
    if "date" in column:
        return "yyyy-mm-dd"
    if any(token in column for token in ("return", "probability", "hazard_rate", "ratio", "drawdown", "hit_rate")):
        return "0.0%;[Red](0.0%);-"
    if any(token in column for token in ("pnl", "notional", "cost", "nav")):
        return "$#,##0;[Red]($#,##0);-"
    if any(token in column for token in ("bps", "cs01", "spread", "basis")):
        return "#,##0.0;[Red](#,##0.0);-"
    if any(token in column for token in ("score", "multiplier", "zscore")):
        return "0.00"
    return "General"


def width_for(column_name: str) -> int:
    column = column_name.lower()
    if "date" in column:
        return 13
    if any(token in column for token in ("issuer", "bond_id", "sector", "regime")):
        return 18
    if any(token in column for token in ("reason", "scenario", "parameter")):
        return 24
    return 14


def to_table_name(name: str) -> str:
    return f"{re.sub(r'[^A-Za-z0-9]', '_', name)}_table"


if __name__ == "__main__":
    main()
