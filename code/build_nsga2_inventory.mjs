import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";
import fs from "node:fs/promises";
import path from "node:path";

const root = ".";
const outRoot = path.join(root, "nsga2_outputs");
const outputPath = path.join(outRoot, "NSGAII_all_experiment_combinations_with_IGD_data_2026-06-09.xlsx");

const common = {
  N: 100,
  proC: 1,
  etaC: 20,
  etaM: 20,
  operators: "SBX + Polynomial Mutation",
  selection: "Tournament + non-dominated sorting + crowding distance",
};

const configs = [];
function addConfig(family, id, implementation, matlab, coverage, budget, mutation, population, pf, igd, seed, runs, notes = "") {
  configs.push({
    family, id, implementation, matlab, coverage,
    N: common.N, budget, proC: common.proC, etaC: common.etaC,
    mutation, etaM: common.etaM, population, pf, igd, seed,
    runs, operators: common.operators, selection: common.selection, notes,
  });
}

const mPlat = "PlatEMO OperatorGA: parameter proM=1, effective probability=1/D";
const mPaper = "Paper literal: per-variable mutation probability=1";
const raw = "Raw objective-space IGD";
const norm = "Objective-normalized IGD";
const finalPop = "Final population";
const ndPop = "Final non-dominated subset";
const fixedSeed = "rng(run), twister";

// A-H paper interpretation matrix.
[
  ["A", "PlatEMO v4.3", "R2026a", "22 problems", "maxFE=10000", mPlat, finalPop, "Analytic/native PF, 10000 points", raw, fixedSeed, 30, "PlatEMO native reference"],
  ["B", "PlatEMO v4.3 + NSGAII_PaperMutation", "R2026a", "22 problems", "maxFE=10000", mPaper, finalPop, "Analytic/native PF, 10000 points", raw, fixedSeed, 30, "Closest ZDT1 scale in early tests"],
  ["C", "PlatEMO v4.3 + NSGAII_PaperMutation", "R2026a", "22 problems", "maxFE=10000", mPaper, finalPop, "PlatEMO GetOptimum(100)", raw, fixedSeed, 30],
  ["D", "PlatEMO v4.3 + NSGAII_PaperMutation", "R2026a", "22 problems", "maxFE=10000", mPaper, finalPop, "PlatEMO GetOptimum(10000)", raw, fixedSeed, 30],
  ["E", "PlatEMO v4.3", "R2026a", "22 problems", "maxFE=N*10000=1000000", mPlat, finalPop, "Analytic/native PF, 10000 points", raw, fixedSeed, 30, "MaxIt interpreted as generations"],
  ["F", "PlatEMO v4.3 + NSGAII_PaperMutation", "R2026a", "22 problems", "maxFE=N*10000=1000000", mPaper, finalPop, "Analytic/native PF, 10000 points", raw, fixedSeed, 30],
  ["G", "PlatEMO v4.3 + NSGAII_PaperMutation", "R2026a", "22 problems", "maxFE=10000", mPaper, finalPop, "Analytic/native PF, 10000 points", norm, fixedSeed, 30],
  ["H", "pymoo NSGA2", "Python environment", "22 problems", "100 generations (=10000 evaluations)", mPaper, finalPop, "Analytic/native PF", raw, "seed=run", 30, "Cross-platform comparison"],
].forEach(r => addConfig("A-H matrix", ...r));

// Evaluation-budget x mutation matrix.
for (const fe of [3500, 10000, 30000, 50000]) {
  addConfig("Budget/mutation matrix", `PlatEMO-${fe}`, "PlatEMO v4.3", "R2026a", "22 problems", `maxFE=${fe}`, mPlat, finalPop, "Analytic/native PF, 10000 points", raw, fixedSeed, 30);
  addConfig("Budget/mutation matrix", `Paper-${fe}`, "PlatEMO v4.3 + NSGAII_PaperMutation", "R2026a", "22 problems", `maxFE=${fe}`, mPaper, finalPop, "Analytic/native PF, 10000 points", raw, fixedSeed, 30);
}

// V1-V15 matrix (V13 was later covered by the Deb C batches).
[
  ["V1", "PlatEMO v4.3", finalPop, "Analytic/native PF, 10000 points", raw, fixedSeed, mPlat],
  ["V2", "PlatEMO v4.3", ndPop, "Analytic/native PF, 10000 points", raw, fixedSeed, mPlat],
  ["V3", "PlatEMO v4.3", finalPop, "Analytic/native PF, 10000 points", norm, fixedSeed, mPlat],
  ["V4", "PlatEMO v4.3", ndPop, "Analytic/native PF, 10000 points", norm, fixedSeed, mPlat],
  ["V5", "PlatEMO v4.3", finalPop, "PlatEMO GetOptimum(100)", raw, fixedSeed, mPlat],
  ["V6", "PlatEMO v4.3", finalPop, "PlatEMO GetOptimum(10000)", raw, fixedSeed, mPlat],
  ["V7", "PlatEMO v4.3", finalPop, "Analytic/native PF, 10000 points", raw, "Default/shuffle seed", mPlat],
  ["V8", "PlatEMO v4.3 + NSGAII_PaperMutation", finalPop, "Analytic/native PF, 10000 points", raw, fixedSeed, mPaper],
  ["V9", "PlatEMO v4.3 + NSGAII_PaperMutation", ndPop, "Analytic/native PF, 10000 points", raw, fixedSeed, mPaper],
  ["V10", "PlatEMO v4.3 + NSGAII_PaperMutation", finalPop, "Analytic/native PF, 10000 points", norm, fixedSeed, mPaper],
  ["V11", "pymoo NSGA2", finalPop, "Analytic/native PF", raw, "seed=run", mPaper],
  ["V12", "pymoo NSGA2", ndPop, "Analytic/native PF", raw, "seed=run", mPaper],
].forEach(([id, impl, pop, pf, metric, seed, mut]) =>
  addConfig("V matrix", id, impl, impl.startsWith("pymoo") ? "Python environment" : "R2026a", "22 problems", impl.startsWith("pymoo") ? "100 generations (=10000 evaluations)" : "maxFE=10000", mut, pop, pf, metric, seed, 30));
addConfig("V matrix", "V14", "PlatEMO v4.3", "R2026a", "22 problems", "maxFE=N*10000=1000000", mPlat, finalPop, "Analytic/native PF, 10000 points", raw, fixedSeed, 30);
addConfig("V matrix", "V15", "PlatEMO v4.3 + NSGAII_PaperMutation", "R2026a", "22 problems", "maxFE=N*10000=1000000", mPaper, finalPop, "Analytic/native PF, 10000 points", raw, fixedSeed, 30);

// P1-P4 seeded paper matrix.
[
  ["P1", "maxFE=10000", mPlat],
  ["P2", "maxFE=1000000", mPlat],
  ["P3", "maxFE=10000", mPaper],
  ["P4", "maxFE=1000000", mPaper],
].forEach(([id, budget, mutation]) =>
  addConfig("P1-P4 seeded", id, mutation === mPlat ? "PlatEMO v4.3" : "PlatEMO v4.3 + NSGAII_PaperMutation", "R2026a", "22 problems", budget, mutation, finalPop, "PlatEMO GetOptimum(10000)", raw, fixedSeed, 30,
    id === "P1" ? "Comparison CSV had paper-value transcription errors for DTLZ1/DTLZ4; run outputs remain valid" : ""));

// Implementation/version comparison.
addConfig("Implementation versions", "v4.3-R2026a", "PlatEMO v4.3", "R2026a", "ZDT1-4,6; DTLZ1-7; UF1-10", "maxFE=10000", mPlat, finalPop, "Native PF, 10000 points", raw, fixedSeed, 30);
addConfig("Implementation versions", "v4.3-R2020b", "PlatEMO v4.3", "R2020b", "UF1-UF5", "maxFE=10000", mPlat, finalPop, "Native PF, 10000 points", raw, fixedSeed, 30);
addConfig("Implementation versions", "v2.9-R2020b", "PlatEMO v2.9.0", "R2020b", "ZDT1-4,6; DTLZ1-7; UF1-10", "maxFE=10000", mPlat, finalPop, "Native PF, 10000 points", raw, fixedSeed, 30);
addConfig("Implementation versions", "Deb-C-1.1.6", "Deb original C NSGA-II v1.1.6 + local DTLZ/UF definitions", "Native executable", "ZDT1-4,6; DTLZ1-7; UF1-10", "maxFE=10000", "C implementation polynomial mutation, nominal 1/D", finalPop, "Native/analytic PF, 10000 points", raw, "seed=run", 30);

// Focused UF and generation/seed tests.
addConfig("Focused UF", "UF-paper", "PlatEMO v4.3 + NSGAII_PaperMutation", "R2026a", "UF1-UF10", "maxFE=10000", mPaper, finalPop, "GetOptimum(10000)", raw, fixedSeed, 30);
addConfig("Focused UF", "UF1-5-sequential", "PlatEMO v4.3", "R2026a", "UF1-UF5", "maxFE=10000", mPlat, finalPop, "Native PF, 10000 points", raw, "One sequential RNG stream", 30);
addConfig("Focused UF", "UF1-5-exact100gen", "PlatEMO v4.3", "R2026a", "UF1-UF5", "100 offspring generations (=10100 evaluations incl. initialization)", mPlat, finalPop, "Native PF, 10000 points", raw, fixedSeed, 30);

// Latest algorithm diagnostics.
addConfig("Algorithm diagnostics", "Baseline-v2.9", "PlatEMO v2.9.0", "R2020b", "22 problems", "maxFE=10000", mPlat, finalPop, "Native PF, 10000 points", raw, fixedSeed, 30, "Reused official version baseline");
addConfig("Algorithm diagnostics", "Per-variable-v2.9", "PlatEMO v2.9.0 modified mutation", "R2020b", "22 problems", "maxFE=10000", mPaper, finalPop, "Native PF, 10000 points", raw, fixedSeed, 30);
addConfig("Algorithm diagnostics", "Exact100Gen-v2.9", "PlatEMO v2.9.0", "R2020b", "22 problems", "10100 evaluations", mPlat, finalPop, "Native PF, 10000 points", raw, fixedSeed, 30);

// Metric-only combinations based on saved v2.9 populations.
for (const points of [100, 1000, 10000]) {
  for (const pop of [finalPop, ndPop]) {
    addConfig("Metric-only reanalysis", `PF${points}-${pop === finalPop ? "full" : "nd"}`, "PlatEMO v2.9.0 saved populations", "R2020b", "22 problems", "No new optimization", mPlat, pop, `Native PF, ${points} points`, raw, fixedSeed, 30, "IGD recomputation only");
  }
}
addConfig("Metric-only reanalysis", "PF10000-swapped", "PlatEMO v2.9.0 saved populations", "R2020b", "22 problems", "No new optimization", mPlat, finalPop, "Native PF, 10000 points", "IGD arguments swapped diagnostic", fixedSeed, 30, "Diagnostic only; not standard IGD");

// ZDT2 budget sweeps.
for (const fe of [200, 300, 500, 800, 1000, 1500, 2000, 3000, 5000, 8000, 10000]) {
  addConfig("ZDT2 budget sweep", `Plat-${fe}`, "PlatEMO v4.3", "R2026a", "ZDT2", `maxFE=${fe}`, mPlat, finalPop, "GetOptimum(10000)", raw, fixedSeed, 10);
  addConfig("ZDT2 budget sweep", `Paper-${fe}`, "PlatEMO v4.3 + NSGAII_PaperMutation", "R2026a", "ZDT2", `maxFE=${fe}`, mPaper, finalPop, "GetOptimum(10000)", raw, fixedSeed, 10);
}
for (const fe of [3500, 4000, 4500, 5000]) {
  addConfig("ZDT2 refined sweep", `Paper-${fe}`, "PlatEMO v4.3 + NSGAII_PaperMutation", "R2026a", "ZDT2", `maxFE=${fe}`, mPaper, finalPop, "GetOptimum(10000)", raw, fixedSeed, 30);
}

// Early focused ZDT batches.
addConfig("Early focused", "ZDT1-PlatEMO", "PlatEMO v4.3", "R2026a", "ZDT1", "maxFE=10000", mPlat, finalPop, "GetOptimum(10000)", raw, "Initial/default then later fixed", 30);
addConfig("Early focused", "ZDT1-paper", "PlatEMO v4.3 + NSGAII_PaperMutation", "R2026a", "ZDT1", "maxFE=10000", mPaper, finalPop, "GetOptimum(10000)", raw, fixedSeed, 30);
addConfig("Early focused", "ZDT-series-paper", "PlatEMO v4.3 + NSGAII_PaperMutation", "R2026a", "ZDT1-4,6", "maxFE=10000", mPaper, finalPop, "GetOptimum(10000)", raw, fixedSeed, 30);
addConfig("Early focused", "pymoo-ZDT1", "pymoo NSGA2", "Python environment", "ZDT1", "100 generations", mPaper, finalPop, "Analytic PF", raw, "seed=run", 30);
addConfig("Seed validation", "A-repeat-twice", "PlatEMO v4.3", "R2026a", "ZDT1", "maxFE=10000", mPlat, finalPop, "GetOptimum(10000)", raw, fixedSeed, 2, "Same seed executed twice; outputs matched exactly");

const batches = [
  ["paper_matrix_nsga2", "A-H matrix", "8 x 22 problems x 30", 5280, "Complete", "A-H full matrix; includes long-run E/F"],
  ["all_nsga2_test_matrix", "Budget/mutation matrix", "8 x 22 problems x 30", 5280, "Complete", "maxFE 3500/10000/30000/50000 x two mutation interpretations"],
  ["version_matrix_rerun", "V matrix", "14 x 22 problems x 30", 9240, "Complete", "V1-V12, V14-V15; V13 later represented by Deb C runs"],
  ["paper_four_seeded", "P1-P4 seeded", "4 x 22 problems x 30", 2640, "Complete", "Fixed-seed four-config experiment"],
  ["all_benchmarks_nsga2_closest_params", "Selected closest batch", "22 problems x 30", 660, "Complete", "maxFE=3500, per-variable mutation"],
  ["uf_series_nsga2_paper_params", "Focused UF", "UF1-UF10 x 30", 300, "Complete", "Per-variable mutation"],
  ["platemo_v43_zdt_seeded_r2026a", "Implementation versions", "5 ZDT x 30", 150, "Complete", "PlatEMO v4.3 / R2026a"],
  ["platemo_v43_dtlz1_7_seeded_r2026a", "Implementation versions", "7 DTLZ x 30", 210, "Complete", "PlatEMO v4.3 / R2026a"],
  ["platemo_v43_uf1_5_seeded", "Implementation versions", "UF1-UF5 x 30", 150, "Complete", "PlatEMO v4.3 / R2026a"],
  ["platemo_v43_uf1_5_seeded_2020b", "Implementation versions", "UF1-UF5 x 30", 150, "Complete", "Same v4.3 code / MATLAB R2020b"],
  ["platemo_v43_uf6_10_seeded_r2026a", "Implementation versions", "UF6-UF10 x 30", 150, "Complete", "PlatEMO v4.3 / R2026a"],
  ["platemo_v290_zdt_seeded_r2020b", "Implementation versions", "5 ZDT x 30", 150, "Complete", "PlatEMO v2.9.0 / R2020b"],
  ["platemo_v290_dtlz1_7_seeded_r2020b", "Implementation versions", "7 DTLZ x 30", 210, "Complete", "PlatEMO v2.9.0 / R2020b"],
  ["platemo_v290_uf1_5_seeded_r2020b", "Implementation versions", "UF1-UF5 x 30", 150, "Complete", "PlatEMO v2.9.0 / R2020b"],
  ["platemo_v290_uf6_10_seeded_r2020b", "Implementation versions", "UF6-UF10 x 30", 150, "Complete", "PlatEMO v2.9.0 / R2020b"],
  ["deb_c_zdt_maxfe10000", "Implementation versions", "5 ZDT x 30", 150, "Complete", "Deb C v1.1.6"],
  ["deb_c_dtlz1_7_maxfe10000", "Implementation versions", "7 DTLZ x 30", 210, "Complete", "Deb C + local problem definitions"],
  ["deb_c_uf1_5_maxfe10000", "Implementation versions", "UF1-UF5 x 30", 150, "Complete", "Deb C + local problem definitions"],
  ["deb_c_uf6_10_maxfe10000", "Implementation versions", "UF6-UF10 x 30", 150, "Complete", "Deb C + local problem definitions"],
  ["v290_all22_algorithm_diagnostics", "Algorithm diagnostics", "2 new variants x 22 x 30", 1320, "Complete", "Per-variable mutation and exact 100 offspring generations"],
  ["v290_all22_diagnostics", "Metric-only reanalysis", "7 metrics x 22 x 30 saved populations", 0, "Complete", "No new algorithm runs"],
  ["platemo_v43_uf1_5_sequential_rng", "Focused UF", "UF1-UF5 x 30", 150, "Complete", "Sequential RNG test"],
  ["platemo_v43_uf1_5_exact_100gen", "Focused UF", "UF1-UF5 x 30", 150, "Complete", "Exact 100 offspring generations"],
  ["zdt1_abcd_test", "ZDT1 A-D", "4 configs x 30", 120, "Complete", "Mutation/PF-point test; B and D logically duplicate"],
  ["zdt2_abcd_test", "ZDT2 A-D", "4 configs x 30", 120, "Complete", "Mutation/PF-point test; B and D logically duplicate"],
  ["zdt2_budget_sweep", "ZDT2 budget sweep", "22 configs x 10", 220, "Complete", "11 budgets x two mutation interpretations"],
  ["zdt2_refine_budget_30runs", "ZDT2 refined sweep", "4 configs x 30", 120, "Complete", "maxFE 3500/4000/4500/5000"],
  ["platemo", "Early focused", "ZDT1 x 30", 30, "Complete", "Initial PlatEMO baseline"],
  ["pymoo", "Early focused", "ZDT1 x 30", 30, "Complete", "Initial pymoo baseline"],
  ["platemo_paper_mutation", "Early focused", "ZDT1 x 30", 30, "Complete", "Initial per-variable mutation test"],
  ["platemo_paper_mutation_zdt_series", "Early focused", "5 ZDT x 30", 150, "Complete", "Per-variable mutation ZDT series"],
  ["platemo_maxfe10000_check", "Validation", "Spot checks", 0, "Complete", "Small verification batch; not counted as full 30-run experiment"],
  ["a_seed_repro_validation", "Seed validation", "Same seed repeated twice", 2, "Complete", "Determinism validation"],
];

function parseCsv(text) {
  const rows = [];
  let row = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(field); field = ""; }
    else if (ch === "\n") { row.push(field.replace(/\r$/, "")); rows.push(row); row = []; field = ""; }
    else field += ch;
  }
  if (field.length || row.length) { row.push(field.replace(/\r$/, "")); rows.push(row); }
  const headers = rows.shift() || [];
  return rows.filter(r => r.some(v => v !== "")).map(r => Object.fromEntries(headers.map((h, i) => [h, r[i] ?? ""])));
}

async function readCsv(rel) {
  return parseCsv(await fs.readFile(path.join(outRoot, rel), "utf8"));
}

const canonicalPaperRows = await readCsv("paper_matrix_nsga2\\paper_matrix_all_A_to_H_summary.csv");
const paperMap = new Map(canonicalPaperRows.filter(r => r.config === "A").map(r => [r.problem, Number(r.paper_nsga2_igd)]));
const resultRows = [];
const num = v => v === undefined || v === null || v === "" ? null : Number(v);

async function addResultFile(rel, family, options = {}) {
  const data = await readCsv(rel);
  for (const r of data) {
    const problem = r.problem || options.problem;
    if (!problem) continue;
    const mean = num(r.mean_igd ?? r.ours_mean_igd ?? r.full_mean ?? r.mean_value ?? r.mean);
    const std = num(r.sample_std ?? r.std_sample ?? r.ours_std ?? r.full_std ?? r.std);
    if (mean === null || Number.isNaN(mean)) continue;
    const paper = paperMap.get(problem) ?? num(r.paper_nsga2_igd ?? r.paper_igd);
    const signed = paper === null ? null : mean - paper;
    const abs = signed === null ? null : Math.abs(signed);
    const relPct = paper === null || paper === 0 ? null : abs / Math.abs(paper) * 100;
    resultRows.push({
      family,
      config: options.configFrom ? options.configFrom(r) : (options.config || r.config || r.case_name || r.variant || r.case || options.defaultConfig || path.basename(path.dirname(rel))),
      description: options.descriptionFrom ? options.descriptionFrom(r) : (options.description || r.description || r.normalization || ""),
      problem,
      M: num(r.M),
      D: num(r.D),
      budget: r.maxFE || r.evaluation_budget || r.generations || options.budget || "",
      runs: num(r.runs ?? r.completed_runs) ?? options.runs ?? null,
      mean, std, paper, signed, abs, relPct,
      source: rel,
    });
  }
}

await addResultFile("paper_matrix_nsga2\\paper_matrix_all_A_to_H_summary.csv", "A-H matrix");
await addResultFile("all_nsga2_test_matrix\\all_nsga2_test_matrix_summary.csv", "Budget/mutation matrix");
await addResultFile("version_matrix_rerun\\version_matrix_all_summary.csv", "V matrix");
await addResultFile("paper_four_seeded\\all_results.csv", "P1-P4 seeded");
await addResultFile("all_benchmarks_nsga2_closest_params\\all_benchmarks_nsga2_closest_params_summary.csv", "Selected closest batch", { config: "Paper-3500" });
await addResultFile("uf_series_nsga2_paper_params\\uf_series_nsga2_paper_params_summary.csv", "Focused UF", { config: "UF-paper" });
for (const [rel, config] of [
  ["platemo_v43_zdt_seeded_r2026a\\summary.csv", "v4.3-R2026a"],
  ["platemo_v43_dtlz1_7_seeded_r2026a\\summary.csv", "v4.3-R2026a"],
  ["platemo_v43_uf1_5_seeded\\summary.csv", "v4.3-R2026a"],
  ["platemo_v43_uf1_5_seeded_2020b\\summary.csv", "v4.3-R2020b"],
  ["platemo_v43_uf6_10_seeded_r2026a\\summary.csv", "v4.3-R2026a"],
  ["platemo_v290_zdt_seeded_r2020b\\summary.csv", "v2.9-R2020b"],
  ["platemo_v290_dtlz1_7_seeded_r2020b\\summary.csv", "v2.9-R2020b"],
  ["platemo_v290_uf1_5_seeded_r2020b\\summary.csv", "v2.9-R2020b"],
  ["platemo_v290_uf6_10_seeded_r2020b\\summary.csv", "v2.9-R2020b"],
  ["deb_c_zdt_maxfe10000\\summary.csv", "Deb-C-1.1.6"],
  ["deb_c_dtlz1_7_maxfe10000\\summary.csv", "Deb-C-1.1.6"],
  ["deb_c_uf1_5_maxfe10000\\summary.csv", "Deb-C-1.1.6"],
  ["deb_c_uf6_10_maxfe10000\\summary.csv", "Deb-C-1.1.6"],
]) await addResultFile(rel, "Implementation versions", { config });
await addResultFile("v290_all22_algorithm_diagnostics\\summary.csv", "Algorithm diagnostics");
await addResultFile("v290_all22_diagnostics\\summary.csv", "Metric-only reanalysis");
await addResultFile("platemo_v43_uf1_5_exact_100gen\\summary.csv", "Focused UF", { config: "UF1-5-exact100gen", budget: "10100" });
await addResultFile("platemo_v43_uf1_5_sequential_rng\\summary.csv", "Focused UF", { config: "UF1-5-sequential", budget: "10000" });
await addResultFile("platemo_v43_uf1_5_seeded\\igd_evaluation_matrix\\summary_all.csv", "UF IGD evaluation matrix", {
  configFrom: r => [r.pf_source, `PF${r.pf_points}`, r.solution_set, r.normalization, r.metric].join("|"),
  descriptionFrom: r => `PF=${r.pf_source}; points=${r.pf_points}; set=${r.solution_set}; normalization=${r.normalization}; metric=${r.metric}`,
});
await addResultFile("zdt1_abcd_test\\abcd_summary.csv", "ZDT1 A-D", { problem: "ZDT1", budget: "10000" });
await addResultFile("zdt2_abcd_test\\abcd_summary.csv", "ZDT2 A-D", { problem: "ZDT2", budget: "10000" });
await addResultFile("zdt2_budget_sweep\\zdt2_budget_sweep_summary.csv", "ZDT2 budget sweep", { problem: "ZDT2" });
await addResultFile("zdt2_refine_budget_30runs\\zdt2_refine_budget_30runs_summary.csv", "ZDT2 refined sweep", { problem: "ZDT2" });
await addResultFile("platemo_paper_mutation_zdt_series\\zdt_igd_summary.csv", "Early focused", { config: "ZDT-series-paper", budget: "10000" });

// Deduplicate logical settings while retaining where they appeared.
const uniqueMap = new Map();
for (const c of configs) {
  const key = [
    c.implementation, c.matlab, c.N, c.budget, c.mutation, c.population,
    c.pf, c.igd, c.seed, c.proC, c.etaC, c.etaM,
  ].join("|");
  if (!uniqueMap.has(key)) {
    uniqueMap.set(key, { ...c, families: new Set([c.family]), ids: new Set([c.id]), coverages: new Set([c.coverage]), runCounts: new Set([c.runs]) });
  } else {
    const u = uniqueMap.get(key);
    u.families.add(c.family);
    u.ids.add(c.id);
    u.coverages.add(c.coverage);
    u.runCounts.add(c.runs);
  }
}
const uniqueConfigs = [...uniqueMap.values()].map((u, i) => ({
  no: i + 1,
  families: [...u.families].join("; "),
  ids: [...u.ids].join("; "),
  implementation: u.implementation,
  matlab: u.matlab,
  coverage: [...u.coverages].join("; "),
  N: u.N,
  budget: u.budget,
  proC: u.proC,
  etaC: u.etaC,
  mutation: u.mutation,
  etaM: u.etaM,
  population: u.population,
  pf: u.pf,
  igd: u.igd,
  seed: u.seed,
  runs: [...u.runCounts].join("; "),
  notes: u.notes,
}));

const workbook = await Workbook.create();
const summary = workbook.worksheets.add("Summary");
const unique = workbook.worksheets.add("Unique Configs");
const batchSheet = workbook.worksheets.add("Run Batches");
const allSheet = workbook.worksheets.add("All Test Rows");
const results = workbook.worksheets.add("IGD Results");
const rankings = workbook.worksheets.add("Result Rankings");
const legend = workbook.worksheets.add("Parameter Legend");

const colors = {
  navy: "#1F4E78", blue: "#D9EAF7", teal: "#2F7D7A", pale: "#F4F7F9",
  gold: "#D8A43B", warn: "#FFF2CC", grid: "#D6DEE5", text: "#1F2933", white: "#FFFFFF",
};

function titleBand(sheet, title, subtitle, endCol) {
  sheet.mergeCells(`A1:${endCol}1`);
  sheet.getRange("A1").values = [[title]];
  sheet.getRange("A1").format = { fill: colors.navy, font: { bold: true, color: colors.white, size: 18 }, horizontalAlignment: "left", verticalAlignment: "center" };
  sheet.getRange("A1").format.rowHeight = 32;
  sheet.mergeCells(`A2:${endCol}2`);
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange("A2").format = { fill: colors.blue, font: { color: colors.text, size: 10 }, wrapText: true, verticalAlignment: "center" };
  sheet.getRange("A2").format.rowHeight = 32;
  sheet.showGridlines = false;
}

function styleHeader(range) {
  range.format = {
    fill: colors.teal,
    font: { bold: true, color: colors.white, size: 10 },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { bottom: { style: "thin", color: colors.grid } },
  };
  range.format.rowHeight = 30;
}

function styleBody(range) {
  range.format = {
    font: { color: colors.text, size: 9 },
    verticalAlignment: "top",
    wrapText: true,
    borders: {
      bottom: { style: "hair", color: colors.grid },
      right: { style: "hair", color: colors.grid },
    },
  };
}

titleBand(summary, "NSGA-II Experiment Inventory", "整理截至 2026-06-09 已執行的參數組合、版本、批次與 IGD 診斷。相同邏輯設定已在 Unique Configs 去重；Run Batches 保留實際輸出資料夾。", "J");
summary.getRange("A4:B8").values = [
  ["KPI", "Value"],
  ["Logical unique configurations", uniqueConfigs.length],
  ["Recorded output batches", batches.length],
  ["Expected optimization runs", null],
  ["IGD result rows", resultRows.length],
];
styleHeader(summary.getRange("A4:B4"));
styleBody(summary.getRange("A5:B8"));
summary.getRange("B7").formulas = [[`=SUM('Run Batches'!D5:D${batches.length + 4})`]];
summary.getRange("B5:B8").format.numberFormat = "0";
summary.getRange("D4:J4").merge();
summary.getRange("D4").values = [["Reading guide"]];
summary.getRange("D4:J4").format = { fill: colors.gold, font: { bold: true, color: colors.white }, horizontalAlignment: "left" };
summary.getRange("D5:J9").merge();
summary.getRange("D5").values = [[
  "1. Unique Configs: deduplicated logical parameter settings.\n" +
  "2. Run Batches: actual folders and expected optimization-run counts.\n" +
  "3. All Test Rows: every named A-H, V, P, sweep and diagnostic row before deduplication.\n" +
  "4. maxFE=10000 means 100 initial solutions plus subsequent offspring until 10,000 evaluations; exact 100 offspring generations produces 10,100 evaluations.\n" +
  "5. PF point-count/full-vs-ND rows under Metric-only reanalysis reuse saved populations and do not rerun NSGA-II."
]];
summary.getRange("D5:J9").format = { fill: colors.pale, wrapText: true, verticalAlignment: "top", font: { size: 10, color: colors.text } };

const categoryCounts = {};
for (const b of batches) categoryCounts[b[1]] = (categoryCounts[b[1]] || 0) + b[3];
const catRows = Object.entries(categoryCounts).sort((a, b) => b[1] - a[1]);
summary.getRange(`A11:B${catRows.length + 11}`).values = [["Category", "Optimization runs"], ...catRows];
styleHeader(summary.getRange("A11:B11"));
styleBody(summary.getRange(`A12:B${catRows.length + 11}`));
summary.getRange(`B12:B${catRows.length + 11}`).format.numberFormat = "#,##0";
summary.getRange("A:A").format.columnWidth = 30;
summary.getRange("B:B").format.columnWidth = 18;
summary.getRange("C:C").format.columnWidth = 3;
summary.getRange("D:J").format.columnWidth = 15;
summary.freezePanes.freezeRows(2);

const uniqueHeaders = ["No.", "Families", "IDs", "Implementation/version", "MATLAB/runtime", "Coverage", "N", "Budget", "proC", "etaC", "Mutation interpretation", "etaM", "Population used", "Reference PF", "IGD", "Seed", "Runs/problem", "Notes"];
titleBand(unique, "Deduplicated Logical Configurations", "The same settings may have been rerun in several folders. Families/IDs and Coverage are aggregated so duplicate parameter settings appear once.", "R");
unique.getRange("A4:R4").values = [uniqueHeaders];
styleHeader(unique.getRange("A4:R4"));
const uniqueRows = uniqueConfigs.map(u => [u.no, u.families, u.ids, u.implementation, u.matlab, u.coverage, u.N, u.budget, u.proC, u.etaC, u.mutation, u.etaM, u.population, u.pf, u.igd, u.seed, u.runs, u.notes]);
unique.getRange(`A5:R${uniqueRows.length + 4}`).values = uniqueRows;
styleBody(unique.getRange(`A5:R${uniqueRows.length + 4}`));
unique.freezePanes.freezeRows(4);
unique.getRange("A:A").format.columnWidth = 6;
unique.getRange("B:C").format.columnWidth = 22;
unique.getRange("D:D").format.columnWidth = 34;
unique.getRange("E:E").format.columnWidth = 16;
unique.getRange("F:F").format.columnWidth = 28;
unique.getRange("G:J").format.columnWidth = 10;
unique.getRange("K:K").format.columnWidth = 34;
unique.getRange("L:L").format.columnWidth = 9;
unique.getRange("M:P").format.columnWidth = 24;
unique.getRange("Q:Q").format.columnWidth = 14;
unique.getRange("R:R").format.columnWidth = 36;
unique.tables.add(`A4:R${uniqueRows.length + 4}`, true, "UniqueConfigurations");

const batchHeaders = ["Output folder", "Category", "Coverage", "Optimization runs", "Status", "Notes", "Absolute path"];
titleBand(batchSheet, "Actual Execution Batches", "One row per output folder. Optimization runs excludes metric-only recomputation and small spot checks.", "G");
batchSheet.getRange("A4:G4").values = [batchHeaders];
styleHeader(batchSheet.getRange("A4:G4"));
const batchRows = batches.map(b => [...b, path.join(outRoot, b[0])]);
batchSheet.getRange(`A5:G${batchRows.length + 4}`).values = batchRows;
styleBody(batchSheet.getRange(`A5:G${batchRows.length + 4}`));
batchSheet.getRange(`D5:D${batchRows.length + 4}`).format.numberFormat = "#,##0";
batchSheet.freezePanes.freezeRows(4);
batchSheet.getRange("A:A").format.columnWidth = 38;
batchSheet.getRange("B:B").format.columnWidth = 24;
batchSheet.getRange("C:C").format.columnWidth = 28;
batchSheet.getRange("D:E").format.columnWidth = 16;
batchSheet.getRange("F:F").format.columnWidth = 45;
batchSheet.getRange("G:G").format.columnWidth = 65;
batchSheet.tables.add(`A4:G${batchRows.length + 4}`, true, "ExecutionBatches");

const allHeaders = ["Family", "ID", "Implementation/version", "MATLAB/runtime", "Coverage", "N", "Budget", "proC", "etaC", "Mutation interpretation", "etaM", "Population", "Reference PF", "IGD", "Seed", "Runs/problem", "Notes"];
titleBand(allSheet, "All Named Test Rows", "Complete pre-deduplication list: A-H, budget/mutation matrix, V variants, P variants, version tests, diagnostics, sweeps and early focused batches.", "Q");
allSheet.getRange("A4:Q4").values = [allHeaders];
styleHeader(allSheet.getRange("A4:Q4"));
const allRows = configs.map(c => [c.family, c.id, c.implementation, c.matlab, c.coverage, c.N, c.budget, c.proC, c.etaC, c.mutation, c.etaM, c.population, c.pf, c.igd, c.seed, c.runs, c.notes]);
allSheet.getRange(`A5:Q${allRows.length + 4}`).values = allRows;
styleBody(allSheet.getRange(`A5:Q${allRows.length + 4}`));
allSheet.freezePanes.freezeRows(4);
allSheet.getRange("A:B").format.columnWidth = 22;
allSheet.getRange("C:C").format.columnWidth = 36;
allSheet.getRange("D:D").format.columnWidth = 16;
allSheet.getRange("E:E").format.columnWidth = 28;
allSheet.getRange("F:I").format.columnWidth = 10;
allSheet.getRange("J:J").format.columnWidth = 36;
allSheet.getRange("K:K").format.columnWidth = 9;
allSheet.getRange("L:O").format.columnWidth = 25;
allSheet.getRange("P:P").format.columnWidth = 14;
allSheet.getRange("Q:Q").format.columnWidth = 42;
allSheet.tables.add(`A4:Q${allRows.length + 4}`, true, "AllNamedTests");

const resultHeaders = ["Family", "Config/version", "Description", "Problem", "M", "D", "Budget", "Runs", "Mean IGD", "Sample std", "mean(std)", "Paper NSGA-II", "Signed diff", "Absolute diff", "Relative diff (%)", "Source CSV"];
titleBand(results, "IGD Results by Configuration and Problem", "Actual numerical results collected from completed summary CSV files. Paper values use the corrected canonical paper table; differences are recalculated consistently.", "P");
results.getRange("A4:P4").values = [resultHeaders];
styleHeader(results.getRange("A4:P4"));
const resultData = resultRows.map(r => [
  r.family, r.config, r.description, r.problem, r.M, r.D, r.budget, r.runs,
  r.mean, r.std, null, r.paper, null, null, null, r.source,
]);
results.getRange(`A5:P${resultData.length + 4}`).values = resultData;
for (let row = 5; row <= resultData.length + 4; row++) {
  results.getRange(`K${row}`).formulas = [[`=IF(OR(I${row}="",J${row}=""),"",TEXT(I${row},"0.0000E+00")&" ("&TEXT(J${row},"0.0000E+00")&")")`]];
  results.getRange(`M${row}`).formulas = [[`=IF(OR(I${row}="",L${row}=""),"",I${row}-L${row})`]];
  results.getRange(`N${row}`).formulas = [[`=IF(M${row}="","",ABS(M${row}))`]];
  results.getRange(`O${row}`).formulas = [[`=IF(OR(N${row}="",L${row}=0),"",N${row}/ABS(L${row})*100)`]];
}
styleBody(results.getRange(`A5:P${resultData.length + 4}`));
results.getRange(`I5:J${resultData.length + 4}`).format.numberFormat = "0.0000E+00";
results.getRange(`L5:N${resultData.length + 4}`).format.numberFormat = "0.0000E+00";
results.getRange(`O5:O${resultData.length + 4}`).format.numberFormat = "0.00";
results.freezePanes.freezeRows(4);
results.getRange("A:C").format.columnWidth = 24;
results.getRange("D:D").format.columnWidth = 12;
results.getRange("E:H").format.columnWidth = 10;
results.getRange("I:O").format.columnWidth = 16;
results.getRange("P:P").format.columnWidth = 55;
results.tables.add(`A4:P${resultData.length + 4}`, true, "IGDResults");

const rankingMap = new Map();
for (const r of resultRows) {
  if (r.relPct === null || Number.isNaN(r.relPct)) continue;
  const key = `${r.family}|${r.config}`;
  if (!rankingMap.has(key)) rankingMap.set(key, { family: r.family, config: r.config, values: [], abs: [] });
  rankingMap.get(key).values.push(r.relPct);
  rankingMap.get(key).abs.push(r.abs);
}
const rankRows = [...rankingMap.values()].map(v => {
  const sorted = [...v.values].sort((a, b) => a - b);
  const median = sorted.length % 2 ? sorted[(sorted.length - 1) / 2] : (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2;
  return [v.family, v.config, v.values.length, v.values.reduce((a, b) => a + b, 0) / v.values.length, median, v.abs.reduce((a, b) => a + b, 0) / v.abs.length];
}).sort((a, b) => a[3] - b[3]);
titleBand(rankings, "Configuration Ranking by Paper Difference", "Ranking uses mean absolute relative difference across available problems. Metric-only diagnostics are included and clearly identified by family.", "F");
rankings.getRange("A4:F4").values = [["Family", "Config/version", "Problems", "Mean relative diff (%)", "Median relative diff (%)", "Mean absolute IGD diff"]];
styleHeader(rankings.getRange("A4:F4"));
rankings.getRange(`A5:F${rankRows.length + 4}`).values = rankRows;
styleBody(rankings.getRange(`A5:F${rankRows.length + 4}`));
rankings.getRange(`D5:E${rankRows.length + 4}`).format.numberFormat = "0.00";
rankings.getRange(`F5:F${rankRows.length + 4}`).format.numberFormat = "0.0000E+00";
rankings.freezePanes.freezeRows(4);
rankings.getRange("A:B").format.columnWidth = 30;
rankings.getRange("C:F").format.columnWidth = 22;
rankings.tables.add(`A4:F${rankRows.length + 4}`, true, "ResultRankings");

titleBand(legend, "Parameter Legend and Fixed Paper Settings", "Definitions used throughout the inventory. This sheet separates explicit paper settings from interpretation choices and later diagnostics.", "F");
legend.getRange("A4:F4").values = [["Parameter", "Meaning", "Paper-explicit value", "Actual interpretations tested", "Can explain differences?", "Notes"]];
styleHeader(legend.getRange("A4:F4"));
const legendRows = [
  ["N", "Population size", "100", "100 in all main experiments", "Low", "Fixed"],
  ["proC", "SBX crossover probability", "1", "1", "Low", "Fixed"],
  ["etaC", "SBX distribution index", "20", "20", "Low", "Fixed"],
  ["proM", "Mutation control parameter", "1", "PlatEMO effective 1/D; literal per-variable probability 1", "High", "Main interpretation split"],
  ["etaM", "Polynomial mutation distribution index", "20", "20", "Low", "Fixed"],
  ["MaxIt/maxFE", "Stopping budget", "MaxIt=10000", "10000 evaluations; N*10000 evaluations; exact 100 generations; budget sweeps", "Very high", "Terminology ambiguity"],
  ["Population for IGD", "Solutions sent to metric", "Not stated", "Final population; final non-dominated subset", "Medium", "Metric-only or output-filter difference"],
  ["Reference PF", "Points approximating true Pareto front", "Not stated", "Native/analytic PF with 100, 500, 1000, 10000 points; official CEC files", "Medium", "Affects measured IGD"],
  ["IGD scaling", "Objective transformation before distance", "Not stated", "Raw; objective-normalized; swapped diagnostic", "High", "Swapped is diagnostic only"],
  ["Seed policy", "Random stream initialization", "30 independent runs", "rng(run); seed=run; default/shuffle; sequential stream", "Medium", "Fixed seeds support reproducibility"],
  ["Implementation", "NSGA-II source/version", "NSGA-II", "PlatEMO v4.3; PlatEMO v2.9.0; Deb C v1.1.6; pymoo", "High", "Tie handling and operator details differ"],
  ["MATLAB", "Runtime version", "R2020b", "R2020b and R2026a", "Low in observed UF test", "Version was explicitly tested"],
];
legend.getRange(`A5:F${legendRows.length + 4}`).values = legendRows;
styleBody(legend.getRange(`A5:F${legendRows.length + 4}`));
legend.freezePanes.freezeRows(4);
legend.getRange("A:A").format.columnWidth = 22;
legend.getRange("B:B").format.columnWidth = 32;
legend.getRange("C:C").format.columnWidth = 24;
legend.getRange("D:D").format.columnWidth = 55;
legend.getRange("E:E").format.columnWidth = 20;
legend.getRange("F:F").format.columnWidth = 38;
legend.tables.add(`A4:F${legendRows.length + 4}`, true, "ParameterLegend");

// Highlight metric-only and warnings.
for (const sheet of [unique, allSheet, batchSheet, legend]) {
  sheet.getUsedRange().format.verticalAlignment = "top";
}
summary.getRange("A1:J20").format.font.name = "Aptos";
unique.getUsedRange().format.font.name = "Aptos";
batchSheet.getUsedRange().format.font.name = "Aptos";
allSheet.getUsedRange().format.font.name = "Aptos";
results.getUsedRange().format.font.name = "Aptos";
rankings.getUsedRange().format.font.name = "Aptos";
legend.getUsedRange().format.font.name = "Aptos";

await fs.mkdir(outRoot, { recursive: true });
const exported = await SpreadsheetFile.exportXlsx(workbook);
await exported.save(outputPath);

const check1 = await workbook.inspect({ kind: "table", range: "Summary!A1:J20", include: "values,formulas", tableMaxRows: 20, tableMaxCols: 10 });
const check2 = await workbook.inspect({ kind: "table", range: "Unique Configs!A1:R12", include: "values,formulas", tableMaxRows: 12, tableMaxCols: 18 });
const check3 = await workbook.inspect({ kind: "table", range: "IGD Results!A1:P12", include: "values,formulas", tableMaxRows: 12, tableMaxCols: 16 });
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula error scan" });
console.log(check1.ndjson);
console.log(check2.ndjson);
console.log(check3.ndjson);
console.log(errors.ndjson);

for (const [sheetName, range, file] of [
  ["Summary", "A1:J20", "inventory_summary.png"],
  ["Unique Configs", "A1:R18", "inventory_unique.png"],
  ["Run Batches", "A1:G20", "inventory_batches.png"],
  ["All Test Rows", "A1:Q18", "inventory_all_rows.png"],
  ["IGD Results", "A1:P18", "inventory_results.png"],
  ["Result Rankings", "A1:F22", "inventory_rankings.png"],
  ["Parameter Legend", "A1:F18", "inventory_legend.png"],
]) {
  const image = await workbook.render({ sheetName, range, scale: 1.2 });
  await fs.writeFile(path.join(outRoot, file), new Uint8Array(await image.arrayBuffer()));
}

console.log(JSON.stringify({ outputPath, uniqueCount: uniqueConfigs.length, batchCount: batches.length, allRows: configs.length, resultRows: resultRows.length, rankingRows: rankRows.length }, null, 2));
