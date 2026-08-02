import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = "C:\\Users\\yiting\\Documents\\Playground";
const outDir = path.join(root, "p0_lite_outputs", "experiment_b_configuration_summary_20260713");

const sheets = [
  ["overall_configuration_comparison.csv", "Overall"],
  ["statistical_tests_meta_vs_baselines.csv", "Stats"],
  ["friedman_tests_all_methods.csv", "Friedman"],
  ["meta_vs_baseline_metric_deltas.csv", "Deltas"],
  ["combined_instance_method_metrics_ranked.csv", "InstanceRanks"],
  ["pairwise_win_tie_loss_by_metric.csv", "WinTieLoss"],
  ["theta_usage_by_method.csv", "ThetaUsage"],
];

async function csvToSheet(workbook, csvFile, sheetName, first = false) {
  const csvPath = path.join(outDir, csvFile);
  const csvText = await fs.readFile(csvPath, "utf8");
  if (first) {
    return Workbook.fromCSV(csvText, { sheetName });
  }
  await workbook.fromCSV(csvText, { sheetName });
  return workbook;
}

function columnName(n) {
  let s = "";
  while (n > 0) {
    const m = (n - 1) % 26;
    s = String.fromCharCode(65 + m) + s;
    n = Math.floor((n - m) / 26);
  }
  return s;
}

async function formatSheet(workbook, sheetName, numericFormat = "0.000000") {
  const sheet = workbook.worksheets.getItem(sheetName);
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  const used = sheet.getUsedRange(true);
  const values = used.values;
  const rows = values.length;
  const cols = values[0]?.length ?? 0;
  if (!rows || !cols) return;

  const lastCol = columnName(cols);
  sheet.getRange(`A1:${lastCol}1`).format = {
    fill: "#1F4E79",
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
  };
  sheet.getRange(`A1:${lastCol}${rows}`).format.borders = {
    preset: "inside",
    style: "thin",
    color: "#D9E2F3",
  };
  sheet.getRange(`A1:${lastCol}${rows}`).format.autofitColumns();
  sheet.getRange(`A1:${lastCol}${rows}`).format.autofitRows();

  if (cols >= 2 && rows >= 2) {
    sheet.getRangeByIndexes(1, 1, rows - 1, cols - 1).format.numberFormat = numericFormat;
  }
}

let workbook = await csvToSheet(null, sheets[0][0], sheets[0][1], true);
for (const [csvFile, sheetName] of sheets.slice(1)) {
  workbook = await csvToSheet(workbook, csvFile, sheetName, false);
}

await formatSheet(workbook, "Overall");
await formatSheet(workbook, "Stats");
await formatSheet(workbook, "Friedman");
await formatSheet(workbook, "Deltas");
await formatSheet(workbook, "InstanceRanks");
await formatSheet(workbook, "WinTieLoss", "0");
await formatSheet(workbook, "ThetaUsage", "0");

const overall = workbook.worksheets.getItem("Overall");
overall.getRange("A1:T1").format.fill = "#17365D";
overall.getRange("A2:T4").format.borders = {
  preset: "inside",
  style: "thin",
  color: "#B8CCE4",
};

const inspect = await workbook.inspect({
  kind: "table",
  sheetId: "Overall",
  range: "A1:T5",
  include: "values",
  tableMaxRows: 5,
  tableMaxCols: 20,
});
console.log(inspect.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "formula error scan",
});
console.log(errors.ndjson);

const preview = await workbook.render({
  sheetName: "Overall",
  range: "A1:J5",
  scale: 1,
  format: "png",
});
await fs.writeFile(path.join(outDir, "overall_preview.png"), new Uint8Array(await preview.arrayBuffer()));

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(path.join(outDir, "Experiment_B_configuration_summary.xlsx"));
console.log(`XLSX=${path.join(outDir, "Experiment_B_configuration_summary.xlsx")}`);
