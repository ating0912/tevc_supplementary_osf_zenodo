import fs from "node:fs";
import path from "node:path";

const root = path.resolve("nsga2_outputs");
const canonical = readCsv(path.resolve("paper_nsga2_table3.csv"));
const paper = new Map(canonical.map(row => [row.problem, Number(row.paper_mean)]));

let updatedFiles = 0;
for (const file of walk(root)) {
  if (!file.toLowerCase().endsWith(".csv")) continue;
  const base = path.basename(file).toLowerCase();
  if (!base.includes("summary") && !base.includes("comparison")) continue;
  const rows = readCsv(file);
  if (!rows.length || !("problem" in rows[0]) || !("paper_igd" in rows[0])) continue;

  let changed = false;
  for (const row of rows) {
    if (!paper.has(row.problem)) continue;
    const expected = paper.get(row.problem);
    if (Number(row.paper_igd) !== expected) {
      row.paper_igd = String(expected);
      changed = true;
    }
    changed = recalculateRow(row, expected) || changed;
  }
  if (changed) {
    writeCsv(file, rows);
    updatedFiles++;
  }
}

rebuildSimpleRanking(
  "v290_deb_bounded_diagnostic",
  ["variant"],
  "ranking.csv",
);
rebuildBestByProblem("v290_deb_bounded_diagnostic", "best_by_problem.csv");
rebuildSimpleRanking(
  "v290_tournament_diagnostic",
  ["variant"],
  "ranking.csv",
);
rebuildBestByProblem("v290_tournament_diagnostic", "best_by_problem.csv");
rebuildSimpleRanking(
  "v290_sampling_point_diagnostic",
  ["variant"],
  "ranking.csv",
);
rebuildSimpleRanking(
  "v290_diagnostic_8_metric",
  ["variant"],
  "ranking.csv",
);
rebuildSimpleRanking(
  "v290_diagnostics_5_7",
  ["family", "variant"],
  "ranking.csv",
);
rebuildPaperFourRanking();
rebuildSeedBlockRanking();

console.log(`Updated ${updatedFiles} CSV files.`);

function recalculateRow(row, expected) {
  let changed = false;
  if (isFiniteNumber(row.mean_igd)) {
    const mean = Number(row.mean_igd);
    changed = setNumber(row, "signed_diff", mean - expected) || changed;
    changed = setNumber(row, "abs_diff", Math.abs(mean - expected)) || changed;
    changed = setNumber(
      row,
      "relative_diff_percent",
      Math.abs(mean - expected) / expected * 100,
    ) || changed;
  }
  if (isFiniteNumber(row.baseline_10000_mean)) {
    const baseline = Number(row.baseline_10000_mean);
    changed = setNumber(
      row,
      "baseline_relative_diff_percent",
      Math.abs(baseline - expected) / expected * 100,
    ) || changed;
  }
  if (isFiniteNumber(row.maxit10000_mean)) {
    const longMean = Number(row.maxit10000_mean);
    changed = setNumber(
      row,
      "maxit10000_relative_diff_percent",
      Math.abs(longMean - expected) / expected * 100,
    ) || changed;
    if (isFiniteNumber(row.baseline_relative_diff_percent)) {
      changed = setNumber(
        row,
        "relative_diff_change_points",
        Number(row.maxit10000_relative_diff_percent) -
          Number(row.baseline_relative_diff_percent),
      ) || changed;
    }
  }
  return changed;
}

function rebuildSimpleRanking(directory, keys, outputName) {
  const dir = path.join(root, directory);
  const summaryFile = path.join(dir, "summary.csv");
  if (!fs.existsSync(summaryFile)) return;
  const rows = readCsv(summaryFile);
  const groups = new Map();
  for (const row of rows) {
    if (!isFiniteNumber(row.relative_diff_percent)) continue;
    const key = keys.map(name => row[name]).join("\u0000");
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(Number(row.relative_diff_percent));
  }
  const ranking = [...groups.entries()].map(([key, values]) => {
    const parts = key.split("\u0000");
    const row = {};
    keys.forEach((name, index) => row[name] = parts[index]);
    row.GroupCount = String(values.length);
    row.mean_relative_diff_percent = String(mean(values));
    row.median_relative_diff_percent = String(median(values));
    return row;
  }).sort((a, b) =>
    Number(a.mean_relative_diff_percent) -
    Number(b.mean_relative_diff_percent)
  );
  writeCsv(path.join(dir, outputName), ranking);
}

function rebuildBestByProblem(directory, outputName) {
  const dir = path.join(root, directory);
  const rows = readCsv(path.join(dir, "summary.csv"));
  const problems = new Map();
  for (const row of rows) {
    if (!problems.has(row.problem)) problems.set(row.problem, []);
    problems.get(row.problem).push(row);
  }
  const best = [...problems.entries()].map(([problem, candidates]) => {
    candidates.sort((a, b) =>
      Number(a.relative_diff_percent) - Number(b.relative_diff_percent)
    );
    const row = candidates[0];
    return {
      problem,
      closest_variant: row.variant,
      mean_igd: row.mean_igd,
      sample_std: row.sample_std,
      paper_igd: row.paper_igd,
      relative_diff_percent: row.relative_diff_percent,
    };
  });
  writeCsv(path.join(dir, outputName), best);
}

function rebuildPaperFourRanking() {
  const dir = path.join(root, "paper_four_seeded");
  if (!fs.existsSync(dir)) return;
  const configs = ["P1", "P2", "P3", "P4"];
  const summaries = new Map();
  for (const config of configs) {
    const file = path.join(dir, config, "summary.csv");
    if (fs.existsSync(file)) summaries.set(config, readCsv(file));
  }
  const problems = [...new Set(
    [...summaries.values()].flat().map(row => row.problem),
  )];
  const wins = Object.fromEntries(configs.map(config => [config, 0]));
  const rankSums = Object.fromEntries(configs.map(config => [config, 0]));
  const output = [];
  for (const config of configs) {
    const rows = summaries.get(config) ?? [];
    output.push({
      config,
      wins: "0",
      average_rank: "",
      mean_abs_diff: String(mean(rows.map(row => Number(row.abs_diff)))),
      mean_relative_diff_percent: String(mean(rows.map(row =>
        Number(row.abs_diff) / Number(row.paper_nsga2_igd) * 100
      ))),
      median_relative_diff_percent: String(median(rows.map(row =>
        Number(row.abs_diff) / Number(row.paper_nsga2_igd) * 100
      ))),
    });
  }
  for (const problem of problems) {
    const candidates = configs.map(config => {
      const row = (summaries.get(config) ?? []).find(item => item.problem === problem);
      return { config, diff: Number(row?.abs_diff ?? Infinity) };
    }).sort((a, b) => a.diff - b.diff);
    if (candidates[0]) wins[candidates[0].config]++;
    candidates.forEach((candidate, index) => rankSums[candidate.config] += index + 1);
  }
  for (const row of output) {
    row.wins = String(wins[row.config]);
    row.average_rank = String(rankSums[row.config] / problems.length);
  }
  output.sort((a, b) => Number(a.average_rank) - Number(b.average_rank));
  writeCsv(path.join(dir, "overall_ranking.csv"), output);
}

function rebuildSeedBlockRanking() {
  const dir = path.join(root, "v290_seed_sensitivity_all22_rerun2");
  const file = path.join(dir, "summary.csv");
  if (!fs.existsSync(file)) return;
  const rows = readCsv(file);
  const key = "seed_block";
  if (!rows.length || !(key in rows[0])) return;
  const groups = new Map();
  for (const row of rows) {
    if (!groups.has(row[key])) groups.set(row[key], []);
    groups.get(row[key]).push(Number(row.relative_diff_percent));
  }
  const ranking = [...groups.entries()].map(([seedBlock, values]) => ({
    seed_block: seedBlock,
    GroupCount: String(values.length),
    mean_relative_diff_percent: String(mean(values)),
    median_relative_diff_percent: String(median(values)),
  })).sort((a, b) =>
    Number(a.mean_relative_diff_percent) -
    Number(b.mean_relative_diff_percent)
  );
  writeCsv(path.join(dir, "seed_block_paper_closeness_ranking.csv"), ranking);
}

function setNumber(row, key, value) {
  if (!(key in row)) return false;
  const next = String(value);
  if (row[key] === next) return false;
  row[key] = next;
  return true;
}

function isFiniteNumber(value) {
  return value !== undefined && value !== "" && Number.isFinite(Number(value));
}

function mean(values) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2
    ? sorted[middle]
    : (sorted[middle - 1] + sorted[middle]) / 2;
}

function* walk(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) yield* walk(full);
    else yield full;
  }
}

function readCsv(file) {
  if (!fs.existsSync(file)) return [];
  const records = parseCsv(fs.readFileSync(file, "utf8"));
  if (records.length < 2) return [];
  const headers = records[0];
  return records.slice(1)
    .filter(record => record.some(value => value !== ""))
    .map(record => Object.fromEntries(
      headers.map((header, index) => [header, record[index] ?? ""]),
    ));
}

function writeCsv(file, rows) {
  if (!rows.length) return;
  const headers = Object.keys(rows[0]);
  const lines = [
    headers.map(escapeCsv).join(","),
    ...rows.map(row => headers.map(header => escapeCsv(row[header] ?? "")).join(",")),
  ];
  fs.writeFileSync(file, `${lines.join("\n")}\n`);
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') {
        field += '"';
        i++;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }
  if (field || row.length) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }
  return rows;
}

function escapeCsv(value) {
  const text = String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}
