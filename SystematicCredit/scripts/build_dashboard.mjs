#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const __filename = fileURLToPath(import.meta.url);
const PROJECT_ROOT = path.resolve(path.dirname(__filename), "..");
const PAYLOAD_PATH = path.join(PROJECT_ROOT, "data", "output", "dashboard_payload.json");
const OUTPUT_DIR = path.join(PROJECT_ROOT, "outputs", "systematic_credit_toolkit");
const PREVIEW_DIR = path.join(OUTPUT_DIR, "previews");
const OUTPUT_XLSX = path.join(OUTPUT_DIR, "bond_cds_basis_dashboard.xlsx");
const WORKBOOK_ROW_LIMIT = 1200;

const SHEET_ORDER = [
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
];

const TABLE_TO_SHEET = {
  cds_curves: "CDS_Curves",
  hazard_survival: "Hazard_Survival",
  bond_cds_basis: "Bond_CDS_Basis",
  rv_signals: "RV_Signals",
  positions: "Positions",
  macro: "Macro_Regime",
  hedge_overlay: "Hedge_Overlay",
  pnl_attribution: "PnL_Attribution",
  performance: "Performance",
  stress_test: "Stress_Test",
  config: "Config",
};

const COLORS = {
  navy: "#12355B",
  blue: "#2563EB",
  teal: "#0F766E",
  green: "#15803D",
  amber: "#B45309",
  red: "#B91C1C",
  gray: "#F3F4F6",
  border: "#CBD5E1",
  text: "#111827",
};

await fs.mkdir(OUTPUT_DIR, { recursive: true });
await fs.mkdir(PREVIEW_DIR, { recursive: true });

const payload = JSON.parse(await fs.readFile(PAYLOAD_PATH, "utf8"));
const workbook = Workbook.create();
const sheets = new Map();
const renderRanges = new Map([["Dashboard", "A1:Q104"]]);

for (const sheetName of SHEET_ORDER) {
  const sheet = workbook.worksheets.add(sheetName);
  sheet.showGridLines = false;
  sheets.set(sheetName, sheet);
}

for (const [tableName, sheetName] of Object.entries(TABLE_TO_SHEET)) {
  const table = payload.tables[tableName];
  if (!table) continue;
  const range = writeDataSheet(sheets.get(sheetName), table, tableName);
  renderRanges.set(sheetName, range);
}

writeDashboard(sheets.get("Dashboard"), payload);

const dashboardInspect = await workbook.inspect({
  kind: "table",
  range: "Dashboard!A1:H20",
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 8,
});
console.log(dashboardInspect.ndjson);

const errorScan = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(errorScan.ndjson);

for (const sheetName of SHEET_ORDER) {
  const preview = await workbook.render({
    sheetName,
    range: renderRanges.get(sheetName),
    scale: 1,
    format: "png",
  });
  const previewBytes = new Uint8Array(await preview.arrayBuffer());
  await fs.writeFile(path.join(PREVIEW_DIR, `${sheetName}.png`), previewBytes);
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(OUTPUT_XLSX);
console.log(`Dashboard written to ${OUTPUT_XLSX}`);

function writeDataSheet(sheet, table, tableName) {
  const columns = table.columns;
  const records = limitWorkbookRows(table.records, tableName);
  const matrix = [columns.map(formatHeader)];
  for (const record of records) {
    matrix.push(columns.map((column) => toCellValue(record[column], column)));
  }

  const rowCount = matrix.length;
  const colCount = columns.length;
  const range = sheet.getRangeByIndexes(0, 0, rowCount, colCount);
  range.values = matrix;

  const tableRange = `A1:${colToLetter(colCount)}${rowCount}`;
  const excelTable = sheet.tables.add(tableRange, true, toTableName(tableName));
  excelTable.style = "TableStyleMedium2";
  excelTable.showFilterButton = true;

  sheet.freezePanes.freezeRows(1);
  sheet.getRangeByIndexes(0, 0, 1, colCount).format = {
    fill: COLORS.navy,
    font: { bold: true, color: "#FFFFFF" },
  };
  sheet.getRangeByIndexes(0, 0, rowCount, colCount).format.borders = {
    preset: "outside",
    style: "thin",
    color: COLORS.border,
  };

  for (let colIdx = 0; colIdx < colCount; colIdx += 1) {
    const columnName = columns[colIdx];
    const colRange = sheet.getRangeByIndexes(1, colIdx, Math.max(rowCount - 1, 1), 1);
    colRange.format.numberFormat = [[numberFormatFor(columnName)]];
    sheet.getRangeByIndexes(0, colIdx, rowCount, 1).format.columnWidth = widthFor(columnName);
  }
  return `A1:${colToLetter(Math.min(colCount, 12))}${Math.min(rowCount, 30)}`;
}

function limitWorkbookRows(records, tableName) {
  const unlimited = new Set([
    "macro",
    "hedge_overlay",
    "pnl_attribution",
    "performance",
    "stress_test",
    "config",
  ]);
  if (unlimited.has(tableName) || records.length <= WORKBOOK_ROW_LIMIT) {
    return records;
  }
  return records.slice(records.length - WORKBOOK_ROW_LIMIT);
}

function writeDashboard(sheet, payload) {
  sheet.getRange("A1:H1").merge();
  sheet.getRange("A1").values = [["Bond-CDS Basis Trading Dashboard"]];
  sheet.getRange("A1:H1").format = {
    fill: COLORS.navy,
    font: { bold: true, color: "#FFFFFF", size: 16 },
  };
  sheet.getRange("A2:H2").merge();
  sheet.getRange("A2").values = [["Synthetic issuer-level research dashboard | CDS curves, basis signals, CS01 exposure, hedging, and P&L attribution"]];
  sheet.getRange("A2:H2").format = {
    fill: "#E5E7EB",
    font: { color: COLORS.text, italic: true },
  };

  writeKpiBlock(sheet, payload);
  writeDashboardHelpers(sheet, payload);
  addDashboardCharts(sheet);
  formatDashboard(sheet);
}

function writeKpiBlock(sheet, payload) {
  const hedgeRows = payload.tables.hedge_overlay.records.length;
  const hedgeLastRow = hedgeRows + 1;
  const kpiLabels = [
    ["Metric", "Value", "Format"],
    ["Total P&L", null, "Currency"],
    ["Total Return", null, "Percent"],
    ["Sharpe Ratio", null, "Number"],
    ["Max Drawdown", null, "Percent"],
    ["Hit Rate", null, "Percent"],
    ["Ending NAV", null, "Currency"],
  ];
  sheet.getRange("A4:C10").values = kpiLabels;
  sheet.getRange("B5:B10").formulas = [
    ["='Performance'!B2"],
    ["='Performance'!C2"],
    ["='Performance'!E2"],
    ["='Performance'!F2"],
    ["='Performance'!G2"],
    ["='Performance'!H2"],
  ];
  sheet.getRange("E4:G10").values = [
    ["Latest Risk", "Value", "Unit"],
    ["Macro Regime", null, "label"],
    ["Net Strategy CS01", null, "per bp"],
    ["Gross Strategy CS01", null, "per bp"],
    ["Hedge Ratio", null, "%"],
    ["Hedge CS01", null, "per bp"],
    ["Hedge Notional", null, "currency"],
  ];
  sheet.getRange("F5:F10").formulas = [
    [`='Hedge_Overlay'!B${hedgeLastRow}`],
    [`='Hedge_Overlay'!C${hedgeLastRow}`],
    [`='Hedge_Overlay'!D${hedgeLastRow}`],
    [`='Hedge_Overlay'!E${hedgeLastRow}`],
    [`='Hedge_Overlay'!F${hedgeLastRow}`],
    [`='Hedge_Overlay'!G${hedgeLastRow}`],
  ];
}

function writeDashboardHelpers(sheet, payload) {
  const pnlRows = payload.tables.pnl_attribution.records.length;
  const pnlStart = Math.max(0, pnlRows - 60);
  const pnlCount = pnlRows - pnlStart;
  sheet.getRange("A13:B13").values = [["Date", "Cumulative P&L"]];
  const pnlFormulas = [];
  for (let i = 0; i < pnlCount; i += 1) {
    const sourceRow = 2 + pnlStart + i;
    pnlFormulas.push([
      `=TEXT('PnL_Attribution'!A${sourceRow},"yyyy-mm-dd")`,
      `='PnL_Attribution'!H${sourceRow}`,
    ]);
  }
  if (pnlFormulas.length > 0) {
    sheet.getRangeByIndexes(13, 0, pnlFormulas.length, 2).formulas = pnlFormulas;
  }

  const latestBasis = payload.tables.dashboard_summary.records.filter(
    (row) => row.summary_type === "latest_basis",
  );
  sheet.getRange("D13:G13").values = [["Bond", "Basis bps", "Z-score", "Signal"]];
  if (latestBasis.length > 0) {
    sheet.getRangeByIndexes(13, 3, latestBasis.length, 4).values = latestBasis.map((row) => [
      row.bond_id,
      row.bond_cds_basis_bps,
      row.basis_zscore,
      row.rv_signal,
    ]);
  }

  const regimeCounts = payload.tables.dashboard_summary.records.filter(
    (row) => row.summary_type === "regime_counts",
  );
  sheet.getRange("A77:B77").values = [["Regime", "Days"]];
  if (regimeCounts.length > 0) {
    sheet.getRangeByIndexes(77, 0, regimeCounts.length, 2).values = regimeCounts.map((row) => [
      row.macro_regime,
      row.days,
    ]);
  }

  sheet.getRange("D30:E35").values = [
    ["P&L Component", "Total"],
    ["Basis Convergence", null],
    ["Credit Spread", null],
    ["Hedge", null],
    ["Carry", null],
    ["Transaction Costs", null],
  ];
  const pnlLastRow = pnlRows + 1;
  sheet.getRange("E31:E35").formulas = [
    [`=SUM('PnL_Attribution'!B2:B${pnlLastRow})`],
    [`=SUM('PnL_Attribution'!C2:C${pnlLastRow})`],
    [`=SUM('PnL_Attribution'!F2:F${pnlLastRow})`],
    [`=SUM('PnL_Attribution'!D2:D${pnlLastRow})`],
    [`=-SUM('PnL_Attribution'!E2:E${pnlLastRow})`],
  ];
}

function addDashboardCharts(sheet) {
  const pnlChart = sheet.charts.add("line", sheet.getRange("A13:B73"));
  pnlChart.title = "Cumulative P&L";
  pnlChart.hasLegend = false;
  pnlChart.xAxis = { axisType: "textAxis", textStyle: { fontSize: 9 } };
  pnlChart.yAxis = { numberFormatCode: "$#,##0" };
  pnlChart.setPosition("J3", "Q18");

  const basisChart = sheet.charts.add("bar", sheet.getRange("D13:E25"));
  basisChart.title = "Latest Bond-CDS Basis (bps)";
  basisChart.hasLegend = false;
  basisChart.xAxis = { textStyle: { fontSize: 8 } };
  basisChart.yAxis = { numberFormatCode: "#,##0.0" };
  basisChart.setPosition("J20", "Q35");

  const attributionChart = sheet.charts.add("bar", sheet.getRange("D30:E35"));
  attributionChart.title = "P&L Attribution";
  attributionChart.hasLegend = false;
  attributionChart.yAxis = { numberFormatCode: "$#,##0" };
  attributionChart.setPosition("J37", "Q52");

  const regimeChart = sheet.charts.add("bar", sheet.getRange("A77:B82"));
  regimeChart.title = "Macro Regime Days";
  regimeChart.hasLegend = false;
  regimeChart.yAxis = { numberFormatCode: "#,##0" };
  regimeChart.setPosition("A88", "H104");
}

function formatDashboard(sheet) {
  sheet.getRange("A1:Q104").format.font = { name: "Aptos", color: COLORS.text };
  sheet.getRange("A4:C4").format = headerFormat();
  sheet.getRange("E4:G4").format = headerFormat();
  sheet.getRange("A13:B13").format = headerFormat();
  sheet.getRange("D13:G13").format = headerFormat();
  sheet.getRange("A77:B77").format = headerFormat();
  sheet.getRange("D30:E30").format = headerFormat();
  sheet.getRange("B5:B5").format.numberFormat = "$#,##0;[Red]($#,##0);-";
  sheet.getRange("B6:B6").format.numberFormat = "0.0%;[Red](0.0%);-";
  sheet.getRange("B7:B7").format.numberFormat = "0.00";
  sheet.getRange("B8:B9").format.numberFormat = "0.0%;[Red](0.0%);-";
  sheet.getRange("B10:B10").format.numberFormat = "$#,##0;[Red]($#,##0);-";
  sheet.getRange("A14:A73").format.numberFormat = "yyyy-mm-dd";
  sheet.getRange("F6:F7").format.numberFormat = "#,##0";
  sheet.getRange("F8:F8").format.numberFormat = "0.0%";
  sheet.getRange("F9:F9").format.numberFormat = "#,##0";
  sheet.getRange("F10:F10").format.numberFormat = "$#,##0;[Red]($#,##0);-";
  sheet.getRange("B14:B73").format.numberFormat = "$#,##0;[Red]($#,##0);-";
  sheet.getRange("E14:F25").format.numberFormat = "#,##0.0";
  sheet.getRange("E31:E35").format.numberFormat = "$#,##0;[Red]($#,##0);-";
  sheet.getRange("A1:Q104").format.borders = { preset: "outside", style: "thin", color: COLORS.border };
  sheet.getRange("A1:H1").format = {
    fill: COLORS.navy,
    font: { bold: true, color: "#FFFFFF", size: 16, name: "Aptos" },
  };
  sheet.getRange("A2:H2").format = {
    fill: "#E5E7EB",
    font: { color: COLORS.text, italic: true, name: "Aptos" },
  };
  for (let colIdx = 0; colIdx < 17; colIdx += 1) {
    sheet.getRangeByIndexes(0, colIdx, 104, 1).format.columnWidth = colIdx < 8 ? 15 : 12;
  }
}

function headerFormat() {
  return {
    fill: COLORS.navy,
    font: { bold: true, color: "#FFFFFF" },
  };
}

function formatHeader(value) {
  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function toCellValue(value, columnName) {
  if (value === undefined || value === null) return null;
  if (columnName.toLowerCase().includes("date") && typeof value === "string") {
    return new Date(`${value}T00:00:00`);
  }
  return value;
}

function numberFormatFor(columnName) {
  const col = columnName.toLowerCase();
  if (col.includes("date")) return "yyyy-mm-dd";
  if (col.includes("return") || col.includes("probability") || col.includes("hazard_rate") || col.includes("ratio") || col.includes("drawdown") || col.includes("hit_rate")) {
    return "0.0%;[Red](0.0%);-";
  }
  if (col.includes("pnl") || col.includes("notional") || col.includes("cost") || col.includes("nav")) {
    return "$#,##0;[Red]($#,##0);-";
  }
  if (col.includes("bps") || col.includes("cs01") || col.includes("spread") || col.includes("basis")) {
    return "#,##0.0;[Red](#,##0.0);-";
  }
  if (col.includes("score") || col.includes("multiplier") || col.includes("zscore")) return "0.00";
  return "General";
}

function widthFor(columnName) {
  const col = columnName.toLowerCase();
  if (col.includes("date")) return 13;
  if (col.includes("issuer") || col.includes("bond_id") || col.includes("sector") || col.includes("regime")) return 18;
  if (col.includes("reason") || col.includes("scenario") || col.includes("parameter")) return 24;
  return 14;
}

function colToLetter(colNumberOneBased) {
  let dividend = colNumberOneBased;
  let columnName = "";
  while (dividend > 0) {
    const modulo = (dividend - 1) % 26;
    columnName = String.fromCharCode(65 + modulo) + columnName;
    dividend = Math.floor((dividend - modulo) / 26);
  }
  return columnName;
}

function toTableName(name) {
  return `${name.replace(/[^A-Za-z0-9]/g, "_")}_table`;
}
