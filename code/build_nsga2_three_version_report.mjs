import fs from "node:fs/promises";
import path from "node:path";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const root = "C:/Users/yiting/Documents/Playground/nsga2_outputs";
const outputPath = path.join(root, "NSGAII_three_versions_vs_paper_by_dataset.xlsx");

function parseCsv(text) {
  const rows = [];
  let row = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') {
      if (quoted && text[i + 1] === '"') {
        field += '"';
        i++;
      } else {
        quoted = !quoted;
      }
    } else if (c === "," && !quoted) {
      row.push(field);
      field = "";
    } else if ((c === "\n" || c === "\r") && !quoted) {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field);
      if (row.some((v) => v !== "")) rows.push(row);
      row = [];
      field = "";
    } else {
      field += c;
    }
  }
  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }
  const headers = rows.shift().map((h) => h.replace(/^\uFEFF/, ""));
  return rows.map((values) =>
    Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]))
  );
}

async function readCsv(name) {
  return parseCsv(await fs.readFile(path.join(root, name), "utf8"));
}

const num = (value) => Number(value);
const fmt = (mean, std) =>
  `${num(mean).toExponential(5).replace("e", "E")} (${num(std).toExponential(5).replace("e", "E")})`;

function normalizeWide(rows, dataset) {
  return rows.map((r) => ({
    dataset,
    problem: r.problem,
    M: r.M ? num(r.M) : r.problem.match(/^UF([8-9]|10)$/) ? 3 : 2,
    D: r.D ? num(r.D) : 30,
    paper: num(r.paper_igd),
    v43Mean: num(r.v43_mean),
    v43Std: num(r.v43_std),
    v43Rel: num(r.v43_relative_diff_percent),
    v290Mean: num(r.v290_mean),
    v290Std: num(r.v290_std),
    v290Rel: num(r.v290_relative_diff_percent),
    debMean: num(r.deb_c_mean),
    debStd: num(r.deb_c_std),
    debRel: num(r.deb_c_relative_diff_percent),
    closest: r.closest_version,
  }));
}

function normalizeZdt(rows) {
  const grouped = new Map();
  for (const r of rows) {
    if (!grouped.has(r.problem)) {
      grouped.set(r.problem, {
        dataset: "ZDT",
        problem: r.problem,
        M: num(r.M),
        D: num(r.D),
        paper: num(r.paper_igd),
      });
    }
    const x = grouped.get(r.problem);
    const version = r.version;
    if (version.includes("v4.3")) {
      x.v43Mean = num(r.mean_igd);
      x.v43Std = num(r.sample_std);
      x.v43Rel = num(r.relative_diff_percent);
    } else if (version.includes("v2.9")) {
      x.v290Mean = num(r.mean_igd);
      x.v290Std = num(r.sample_std);
      x.v290Rel = num(r.relative_diff_percent);
    } else {
      x.debMean = num(r.mean_igd);
      x.debStd = num(r.sample_std);
      x.debRel = num(r.relative_diff_percent);
    }
  }
  return [...grouped.values()].map((x) => {
    const choices = [
      ["PlatEMO v4.3", x.v43Rel],
      ["PlatEMO v2.9", x.v290Rel],
      ["Deb C", x.debRel],
    ].sort((a, b) => a[1] - b[1]);
    x.closest = choices[0][0];
    return x;
  });
}

const dtlz = normalizeWide(await readCsv("dtlz1_7_three_version_comparison.csv"), "DTLZ");
const uf = normalizeWide(await readCsv("uf1_10_three_version_comparison.csv"), "UF");
const zdt = normalizeZdt(await readCsv("zdt_three_version_comparison.csv"));
const datasets = [
  { name: "ZDT", rows: zdt },
  { name: "DTLZ", rows: dtlz },
  { name: "UF", rows: uf },
];

const workbook = Workbook.create();
const summary = workbook.worksheets.add("總覽");
const detailSheets = new Map(
  datasets.map((dataset) => [dataset.name, workbook.worksheets.add(dataset.name)])
);

const navy = "#17324D";
const teal = "#087E8B";
const green = "#2F855A";
const amber = "#D97706";
const lightBlue = "#E8F1F8";
const lightGreen = "#E9F6EF";
const lightAmber = "#FFF4E5";
const grid = "#CBD5E1";

summary.getRange("A1:H1").merge();
summary.getRange("A1").values = [["NSGA-II 三版本與論文 IGD 比較"]];
summary.getRange("A1:H1").format = {
  fill: navy,
  font: { bold: true, color: "#FFFFFF", size: 18 },
  horizontalAlignment: "center",
  verticalAlignment: "center",
};
summary.getRange("A1:H1").format.rowHeight = 34;
summary.getRange("A2:H2").merge();
summary.getRange("A2").values = [[
  "條件：N=100、maxFE=10000、30 runs；數值為 mean(std)，相對差越小代表越接近論文。"
]];
summary.getRange("A2:H2").format = {
  fill: lightBlue,
  font: { color: navy, italic: true },
  horizontalAlignment: "left",
};

summary.getRange("A4:H4").values = [[
  "資料集", "題數", "v4.3 平均相對差", "v2.9 平均相對差",
  "Deb C 平均相對差", "v4.3 最接近題數", "v2.9 最接近題數", "Deb C 最接近題數"
]];
summary.getRange("A4:H4").format = {
  fill: teal,
  font: { bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  wrapText: true,
};

for (let i = 0; i < datasets.length; i++) {
  const row = i + 5;
  const dataset = datasets[i];
  const last = dataset.rows.length + 4;
  summary.getRange(`A${row}:B${row}`).values = [[dataset.name, dataset.rows.length]];
  summary.getRange(`C${row}:H${row}`).formulas = [[
    `=AVERAGE('${dataset.name}'!G5:G${last})`,
    `=AVERAGE('${dataset.name}'!J5:J${last})`,
    `=AVERAGE('${dataset.name}'!M5:M${last})`,
    `=COUNTIF('${dataset.name}'!O5:O${last},"PlatEMO v4.3")`,
    `=COUNTIF('${dataset.name}'!O5:O${last},"PlatEMO v2.9")`,
    `=COUNTIF('${dataset.name}'!O5:O${last},"Deb C")+COUNTIF('${dataset.name}'!O5:O${last},"Deb original C")`,
  ]];
}
summary.getRange("A5:H7").format.borders = {
  top: { style: "thin", color: grid },
  bottom: { style: "thin", color: grid },
  left: { style: "thin", color: grid },
  right: { style: "thin", color: grid },
};
summary.getRange("C5:E7").format.numberFormat = "0.00%";
summary.getRange("A9:D9").values = [["版本", "22 題平均相對差", "總最接近題數", "整體判讀"]];
summary.getRange("A9:D9").format = {
  fill: navy,
  font: { bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
};
summary.getRange("A10:A12").values = [["PlatEMO v4.3"], ["PlatEMO v2.9"], ["Deb C"]];
summary.getRange("B10:B12").formulas = [
  ["=SUMPRODUCT(C5:C7,B5:B7)/SUM(B5:B7)"],
  ["=SUMPRODUCT(D5:D7,B5:B7)/SUM(B5:B7)"],
  ["=SUMPRODUCT(E5:E7,B5:B7)/SUM(B5:B7)"],
];
summary.getRange("C10:C12").formulas = [
  ["=SUM(F5:F7)"],
  ["=SUM(G5:G7)"],
  ["=SUM(H5:H7)"],
];
summary.getRange("D10:D12").values = [
  ["PlatEMO 現行版"],
  ["論文時期 MATLAB/PlatEMO 對照"],
  ["原作者 C 實作"],
];
summary.getRange("B10:B12").format.numberFormat = "0.00%";
summary.getRange("A10:D12").format.borders = {
  top: { style: "thin", color: grid },
  bottom: { style: "thin", color: grid },
  left: { style: "thin", color: grid },
  right: { style: "thin", color: grid },
};

const chart = summary.charts.add("bar", {
  chartType: "bar",
  title: "各資料集平均相對差",
  hasLegend: true,
});
const chartSeries = [
  ["PlatEMO v4.3", "C", "#D97706"],
  ["PlatEMO v2.9", "D", "#2F855A"],
  ["Deb C", "E", "#0891B2"],
];
for (const [label, column, color] of chartSeries) {
  const series = chart.series.add(label);
  series.categoryFormula = "'總覽'!$A$5:$A$7";
  series.formula = `'總覽'!$${column}$5:$${column}$7`;
  series.fill = color;
}
chart.title = "各資料集平均相對差";
chart.hasLegend = true;
chart.xAxis = { axisType: "textAxis" };
chart.yAxis = { numberFormatCode: "0%" };
chart.setPosition("J3", "Q17");

summary.getRange("A14:H18").values = [
  ["解讀說明", "", "", "", "", "", "", ""],
  ["相對差", "ABS(實驗平均 IGD - 論文 IGD) / 論文 IGD", "", "", "", "", "", ""],
  ["最接近版本", "每題三版本中相對差最小者，不代表該版本的原始 IGD 最低。", "", "", "", "", "", ""],
  ["論文值", "取自 A-MPMO 論文表格中的 NSGA-II 欄。", "", "", "", "", "", ""],
  ["ZDT5", "論文未列 ZDT5，因此本比較維持 22 題，不納入 ZDT5。", "", "", "", "", "", ""],
];
summary.getRange("A14:H14").merge();
for (let row = 15; row <= 18; row++) summary.getRange(`B${row}:H${row}`).merge();
summary.getRange("A14:H14").format = { fill: amber, font: { bold: true, color: "#FFFFFF" } };
summary.getRange("A15:A18").format.font = { bold: true, color: navy };
summary.getRange("A14:H18").format.wrapText = true;
summary.getRange("A15:H18").format.rowHeight = 24;

summary.getRange("A:A").format.columnWidth = 18;
summary.getRange("B:B").format.columnWidth = 18;
summary.getRange("C:E").format.columnWidth = 19;
summary.getRange("F:H").format.columnWidth = 18;
summary.getRange("D:D").format.columnWidth = 28;
summary.freezePanes.freezeRows(4);

function addDatasetSheet(name, rows) {
  const sheet = detailSheets.get(name);
  sheet.getRange("A1:O1").merge();
  sheet.getRange("A1").values = [[`${name}：三版本與論文 IGD 比較`]];
  sheet.getRange("A1:O1").format = {
    fill: navy,
    font: { bold: true, color: "#FFFFFF", size: 16 },
    horizontalAlignment: "center",
  };
  sheet.getRange("A2:O2").merge();
  sheet.getRange("A2").values = [[
    "每題 30 runs；mean(std) 使用科學記號。Abs diff 與 Relative diff 均以 mean 對論文 IGD 計算。"
  ]];
  sheet.getRange("A2:O2").format = { fill: lightBlue, font: { italic: true, color: navy } };
  sheet.getRange("A4:O4").values = [[
    "Problem", "M", "D", "Paper IGD",
    "v4.3 mean(std)", "v4.3 Abs diff", "v4.3 Relative diff",
    "v2.9 mean(std)", "v2.9 Abs diff", "v2.9 Relative diff",
    "Deb C mean(std)", "Deb C Abs diff", "Deb C Relative diff",
    "Min relative diff", "Closest version"
  ]];
  sheet.getRange("A4:O4").format = {
    fill: teal,
    font: { bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
  };
  const values = rows.map((r) => [
    r.problem, r.M, r.D, r.paper,
    fmt(r.v43Mean, r.v43Std), Math.abs(r.v43Mean - r.paper), r.v43Rel / 100,
    fmt(r.v290Mean, r.v290Std), Math.abs(r.v290Mean - r.paper), r.v290Rel / 100,
    fmt(r.debMean, r.debStd), Math.abs(r.debMean - r.paper), r.debRel / 100,
    Math.min(r.v43Rel, r.v290Rel, r.debRel) / 100, r.closest
  ]);
  const last = values.length + 4;
  sheet.getRange(`A5:O${last}`).values = values;
  sheet.getRange(`D5:D${last}`).format.numberFormat = "0.00000E+00";
  sheet.getRange(`F5:F${last}`).format.numberFormat = "0.00000E+00";
  sheet.getRange(`I5:I${last}`).format.numberFormat = "0.00000E+00";
  sheet.getRange(`L5:L${last}`).format.numberFormat = "0.00000E+00";
  sheet.getRange(`G5:G${last}`).format.numberFormat = "0.00%";
  sheet.getRange(`J5:J${last}`).format.numberFormat = "0.00%";
  sheet.getRange(`M5:N${last}`).format.numberFormat = "0.00%";
  sheet.getRange(`A5:O${last}`).format.borders = {
    top: { style: "thin", color: grid },
    bottom: { style: "thin", color: grid },
    left: { style: "thin", color: grid },
    right: { style: "thin", color: grid },
  };
  sheet.getRange(`N5:N${last}`).conditionalFormats.add("colorScale", {
    criteria: [
      { type: "lowestValue", color: "#B7E4C7" },
      { type: "percentile", value: 50, color: "#FFF3BF" },
      { type: "highestValue", color: "#FFCCD5" },
    ],
  });
  sheet.getRange(`O5:O${last}`).format = { fill: lightGreen, font: { bold: true, color: green } };
  sheet.getRange("A:A").format.columnWidth = 12;
  sheet.getRange("B:C").format.columnWidth = 7;
  sheet.getRange("D:D").format.columnWidth = 14;
  sheet.getRange("E:E").format.columnWidth = 25;
  sheet.getRange("F:G").format.columnWidth = 18;
  sheet.getRange("H:H").format.columnWidth = 25;
  sheet.getRange("I:J").format.columnWidth = 18;
  sheet.getRange("K:K").format.columnWidth = 25;
  sheet.getRange("L:N").format.columnWidth = 18;
  sheet.getRange("O:O").format.columnWidth = 20;
  sheet.freezePanes.freezeRows(4);
  sheet.getRange(`A4:O${last}`).format.verticalAlignment = "center";
}

for (const dataset of datasets) addDatasetSheet(dataset.name, dataset.rows);

const inspect = await workbook.inspect({
  kind: "table",
  range: "總覽!A1:H18",
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 8,
});
console.log(inspect.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

for (const sheetName of ["總覽", "ZDT", "DTLZ", "UF"]) {
  const preview = await workbook.render({
    sheetName,
    autoCrop: "all",
    scale: 1,
    format: "png",
  });
  await fs.writeFile(path.join(root, `_preview_${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
