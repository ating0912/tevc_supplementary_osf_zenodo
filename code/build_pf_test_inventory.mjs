import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";
import fs from "node:fs/promises";
import path from "node:path";

const root = ".";
const base = path.join(root, "nsga2_outputs");
const t18 = path.join(base, "v290_pf_sources_t1_t8");
const pf10 = path.join(base, "v290_pf10_native_metric");
const output = path.join(base, "v290_PF_T1_T10_complete_summary_2026-06-09.xlsx");

function parseCsv(text) {
  const rows = []; let row = [], field = "", quoted = false;
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
  const headers = rows.shift();
  return rows.filter(r => r.some(v => v !== "")).map(r => Object.fromEntries(headers.map((h, i) => [h, r[i] ?? ""])));
}
const read = async file => parseCsv(await fs.readFile(file, "utf8"));
const n = v => v === "" || v == null ? null : Number(v);

const s18 = await read(path.join(t18, "summary.csv"));
const s10 = await read(path.join(pf10, "summary.csv"));
const r18 = await read(path.join(t18, "per_run_igd.csv"));
const r10 = await read(path.join(pf10, "per_run_igd.csv"));
const pointRows = await read(path.join(t18, "pf_point_counts.csv"));

const definitions = [
  ["T1", "T1_v290_PF", "v2.9 problem.PF(10000)", "22", "Completed", "Full final population", "Native v2.9 problem PF"],
  ["T2", "T2_v43_GetOptimum", "v4.3 GetOptimum(10000)", "22", "Completed", "Full final population", "Numerically identical to T1"],
  ["T3", "T3_experiment_file", "Reference files used by completed experiments", "22", "Completed", "Full final population", "ZDT/DTLZ saved v4.3 PF; UF CEC2009 files"],
  ["T4", "T4_CEC2009_official", "CEC2009 official PF files", "UF1-UF10", "Completed", "Full final population", "Only applicable to UF"],
  ["T5", "T5_analytic_10000", "Independent analytic PF, nominal 10,000 points", "ZDT+DTLZ (12)", "Completed", "Full final population", "No independent analytic UF implementation"],
  ["T6", "T6_analytic_100000", "High-density analytic PF, nominal 100,000 points", "ZDT+DTLZ (12)", "Completed", "Full final population", "Tests point-density effect"],
  ["T7", "T7_merged_reference", "T1-T5 union, duplicate removal and ND filtering", "22", "Completed", "Full final population", "Merged reference diagnostic"],
  ["T8", "T8_empirical_union", "v4.3 + v2.9 + Deb C final populations, ND filtered", "22", "Completed", "Full final population", "Diagnostic and optimistically biased; includes evaluated v2.9 data"],
  ["T9", "", "Paper-era original PF files", "0", "Not run", "", "Files have not been obtained; no numerical result"],
  ["PF10a", "PF10a_native_full", "v2.9 native IGD.m with problem.PF", "22", "Completed", "Full final population", "Confirms T1 using native metric code"],
  ["PF10b", "PF10b_GLOBAL_Metric_ND", "v2.9 GLOBAL.Metric behavior", "22", "Completed", "Feasible non-dominated subset", "Native PF + ND filtering + native IGD.m"],
];
const nameMap = new Map(definitions.map(d => [d[1], d[0]]));

const results = [
  ...s18.map(r => ({ code: nameMap.get(r.source), source: r.source, ...r, mean_nd_size: "" })),
  ...s10.map(r => ({ code: nameMap.get(r.variant), source: r.variant, ...r })),
];
const perRun = [
  ...r18.map(r => ({ code: nameMap.get(r.source), source: r.source, ...r, full_size: "", nd_size: "" })),
  ...r10.map(r => ({ code: nameMap.get(r.variant), source: r.variant, ...r })),
];

const rankings = [];
for (const d of definitions.filter(x => x[4] === "Completed")) {
  const rows = results.filter(r => r.code === d[0]);
  const vals = rows.map(r => n(r.relative_diff_percent)).filter(Number.isFinite).sort((a,b)=>a-b);
  const median = vals.length % 2 ? vals[(vals.length-1)/2] : (vals[vals.length/2-1]+vals[vals.length/2])/2;
  rankings.push([d[0], d[1], rows.length, vals.reduce((a,b)=>a+b,0)/vals.length, median, d[3], d[5], d[6]]);
}
const fullRanking = rankings.filter(r => r[2] === 22).sort((a,b)=>a[3]-b[3]);

const datasetRows = [];
for (const d of definitions.filter(x => x[4] === "Completed")) {
  for (const dataset of ["DTLZ","ZDT","UF"]) {
    const rows = results.filter(r => r.code === d[0] && r.problem.startsWith(dataset));
    if (!rows.length) continue;
    const vals = rows.map(r=>n(r.relative_diff_percent)).sort((a,b)=>a-b);
    const med = vals.length%2 ? vals[(vals.length-1)/2] : (vals[vals.length/2-1]+vals[vals.length/2])/2;
    datasetRows.push([d[0], dataset, rows.length, vals.reduce((a,b)=>a+b,0)/vals.length, med]);
  }
}

const wb = await Workbook.create();
const overview = wb.worksheets.add("Overview");
const defs = wb.worksheets.add("Test Definitions");
const rank = wb.worksheets.add("Fair Rankings");
const detail = wb.worksheets.add("Problem Results");
const points = wb.worksheets.add("PF Point Counts");
const runs = wb.worksheets.add("Per Run IGD");

const c = { navy:"#204F78", teal:"#338784", blue:"#D9EAF7", pale:"#F4F7F9", gold:"#D9A63A", white:"#FFFFFF", grid:"#D7E0E7", text:"#24313B", warn:"#FFF2CC" };
function title(sheet, text, sub, end) {
  sheet.mergeCells(`A1:${end}1`); sheet.getRange("A1").values=[[text]];
  sheet.getRange("A1").format={fill:c.navy,font:{bold:true,color:c.white,size:18},verticalAlignment:"center"}; sheet.getRange("A1").format.rowHeight=32;
  sheet.mergeCells(`A2:${end}2`); sheet.getRange("A2").values=[[sub]];
  sheet.getRange("A2").format={fill:c.blue,font:{color:c.text,size:10},wrapText:true,verticalAlignment:"center"}; sheet.getRange("A2").format.rowHeight=30;
  sheet.showGridlines=false;
}
function header(range){range.format={fill:c.teal,font:{bold:true,color:c.white,size:10},horizontalAlignment:"center",verticalAlignment:"center",wrapText:true,borders:{bottom:{style:"thin",color:c.grid}}};range.format.rowHeight=28;}
function body(range){range.format={font:{color:c.text,size:9},verticalAlignment:"top",wrapText:true,borders:{bottom:{style:"hair",color:c.grid},right:{style:"hair",color:c.grid}}};}

title(overview,"PlatEMO v2.9 PF / IGD Test Summary","T1-T8 and PF10 are completed using the same saved v2.9 populations. T9 remains unavailable because the paper-era original PF files have not been obtained.","Q");
overview.getRange("A4:B9").values=[
  ["KPI","Value"],["Completed definitions",10],["Unavailable definitions",1],
  ["Problem-level result rows",results.length],["Per-run IGD rows",perRun.length],
  ["Optimization reruns",0],
]; header(overview.getRange("A4:B4")); body(overview.getRange("A5:B9"));
overview.getRange("D4:H4").merge(); overview.getRange("D4").values=[["Conclusion"]];
overview.getRange("D4:H4").format={fill:c.gold,font:{bold:true,color:c.white}};
overview.getRange("D5:H9").merge(); overview.getRange("D5").values=[[
  "PF10b is the closest full-coverage definition, but improves the mean relative difference only from 58.652% to 58.609% (0.043 percentage points). " +
  "T1 and T2 are effectively identical. Increasing analytic PF density from 10,000 to 100,000 points has negligible impact. " +
  "T7 does not improve the overall result. T8 is diagnostic only because its empirical PF contains the evaluated v2.9 populations. " +
  "Therefore PF source, PF density, and final-vs-ND metric input are not the main causes of the discrepancy from the paper."
]]; overview.getRange("D5:H9").format={fill:c.pale,wrapText:true,verticalAlignment:"top",font:{size:10,color:c.text}};
overview.getRange("A12:H12").values=[["Code","Internal name","Problems","Mean relative diff (%)","Median relative diff (%)","Coverage","Population","Notes"]]; header(overview.getRange("A12:H12"));
overview.getRange(`A13:H${12+fullRanking.length}`).values=fullRanking; body(overview.getRange(`A13:H${12+fullRanking.length}`));
overview.getRange(`D13:E${12+fullRanking.length}`).format.numberFormat="0.000";
overview.getRange("J12:K12").values=[["Full coverage code","Mean relative diff (%)"],...fullRanking.map(r=>[r[0],r[3]])];
const chart=overview.charts.add("bar",overview.getRange(`J12:K${12+fullRanking.length}`));
chart.title="Full 22-Problem Mean Relative Difference";
chart.hasLegend=false; chart.xAxis={axisType:"textAxis"}; chart.yAxis={numberFormatCode:"0.0"};
chart.setPosition("J4","Q20");
overview.getRange("A:A").format.columnWidth=12; overview.getRange("B:B").format.columnWidth=28; overview.getRange("C:C").format.columnWidth=12;
overview.getRange("D:E").format.columnWidth=20; overview.getRange("F:H").format.columnWidth=28; overview.getRange("I:I").format.columnWidth=3;
overview.getRange("J:Q").format.columnWidth=15; overview.freezePanes.freezeRows(2);

title(defs,"PF Test Definitions","Scope and interpretation of every proposed test. T9 is retained explicitly to show that it has not been executed.","G");
defs.getRange("A4:G4").values=[["Code","Internal name","PF / metric definition","Applicable problems","Status","Metric population","Notes"]]; header(defs.getRange("A4:G4"));
defs.getRange(`A5:G${4+definitions.length}`).values=definitions; body(defs.getRange(`A5:G${4+definitions.length}`));
defs.getRange("A:B").format.columnWidth=24; defs.getRange("C:C").format.columnWidth=48; defs.getRange("D:F").format.columnWidth=22; defs.getRange("G:G").format.columnWidth=55;
defs.tables.add(`A4:G${4+definitions.length}`,true,"PFDefinitions"); defs.freezePanes.freezeRows(4);

title(rank,"Comparable Rankings","The first table compares only definitions covering all 22 problems. The second table compares each source within the same dataset family.","E");
rank.getRange("A4:E4").values=[["Code","Problems","Mean relative diff (%)","Median relative diff (%)","Interpretation"]]; header(rank.getRange("A4:E4"));
rank.getRange(`A5:E${4+fullRanking.length}`).values=fullRanking.map(r=>[r[0],r[2],r[3],r[4],r[7]]); body(rank.getRange(`A5:E${4+fullRanking.length}`));
rank.getRange(`C5:D${4+fullRanking.length}`).format.numberFormat="0.000";
const start=7+fullRanking.length;
rank.getRange(`A${start}:E${start}`).values=[["Code","Dataset","Problems","Mean relative diff (%)","Median relative diff (%)"]]; header(rank.getRange(`A${start}:E${start}`));
rank.getRange(`A${start+1}:E${start+datasetRows.length}`).values=datasetRows; body(rank.getRange(`A${start+1}:E${start+datasetRows.length}`));
rank.getRange(`D${start+1}:E${start+datasetRows.length}`).format.numberFormat="0.000";
rank.getRange("A:B").format.columnWidth=25; rank.getRange("C:E").format.columnWidth=24; rank.freezePanes.freezeRows(4);

title(detail,"Problem-Level IGD Results","Every completed PF/metric definition with mean, sample standard deviation, paper value, and recalculated differences.","P");
const dh=["Code","Source","Problem","Dataset","M","D","Runs","PF points","Mean ND size","Mean IGD","Sample std","mean(std)","Paper IGD","Signed diff","Absolute diff","Relative diff (%)"];
detail.getRange("A4:P4").values=[dh]; header(detail.getRange("A4:P4"));
const dr=results.map(r=>[r.code,r.source,r.problem,r.problem.replace(/[0-9]/g,""),n(r.M),n(r.D),n(r.runs),n(r.pf_points),n(r.mean_nd_size),n(r.mean_igd),n(r.sample_std),r.mean_std,n(r.paper_igd),n(r.signed_diff),n(r.abs_diff),n(r.relative_diff_percent)]);
detail.getRange(`A5:P${4+dr.length}`).values=dr; body(detail.getRange(`A5:P${4+dr.length}`));
detail.getRange(`J5:O${4+dr.length}`).format.numberFormat="0.0000E+00"; detail.getRange(`P5:P${4+dr.length}`).format.numberFormat="0.000";
detail.getRange("A:B").format.columnWidth=27; detail.getRange("C:D").format.columnWidth=12; detail.getRange("E:I").format.columnWidth=12; detail.getRange("J:P").format.columnWidth=17;
detail.tables.add(`A4:P${4+dr.length}`,true,"PFProblemResults"); detail.freezePanes.freezeRows(4);

title(points,"Reference PF Point Counts","Actual point counts can differ from the requested count because UniformPoint and non-dominated filtering return the nearest feasible design.","K");
const ph=["Problem","M","D","T1","T2","T3","T4","T5","T6","T7","T8"];
points.getRange("A4:K4").values=[ph]; header(points.getRange("A4:K4"));
const pr=pointRows.map(r=>[r.problem,n(r.M),n(r.D),n(r.T1_points),n(r.T2_points),n(r.T3_points),n(r.T4_points),n(r.T5_points),n(r.T6_points),n(r.T7_points),n(r.T8_points)]);
points.getRange(`A5:K${4+pr.length}`).values=pr; body(points.getRange(`A5:K${4+pr.length}`));
points.getRange("A:A").format.columnWidth=16; points.getRange("B:K").format.columnWidth=12; points.tables.add(`A4:K${4+pr.length}`,true,"PFPointCounts"); points.freezePanes.freezeRows(4);

title(runs,"Per-Run IGD Data","All 5,640 metric observations. T1-T8 and PF10 use the same saved v2.9 final populations; no optimization was rerun.","L");
const rh=["Code","Source","Problem","Dataset","M","D","Run","PF points","Full size","ND size","IGD","Source group"];
runs.getRange("A4:L4").values=[rh]; header(runs.getRange("A4:L4"));
const rr=perRun.map(r=>[r.code,r.source,r.problem,r.problem.replace(/[0-9]/g,""),n(r.M),n(r.D),n(r.run),n(r.pf_points),n(r.full_size),n(r.nd_size),n(r.igd),r.source.startsWith("PF10")?"PF10":"T1-T8"]);
runs.getRange(`A5:L${4+rr.length}`).values=rr; body(runs.getRange(`A5:L${4+rr.length}`)); runs.getRange(`K5:K${4+rr.length}`).format.numberFormat="0.0000E+00";
runs.getRange("A:B").format.columnWidth=28; runs.getRange("C:D").format.columnWidth=12; runs.getRange("E:J").format.columnWidth=11; runs.getRange("K:L").format.columnWidth=17;
runs.tables.add(`A4:L${4+rr.length}`,true,"PFPerRunIGD"); runs.freezePanes.freezeRows(4);

for (const sh of [overview,defs,rank,detail,points,runs]) sh.getUsedRange().format.font.name="Aptos";

await fs.mkdir(base,{recursive:true});
const xlsx=await SpreadsheetFile.exportXlsx(wb); await xlsx.save(output);
const checks=[
  await wb.inspect({kind:"table",range:"Overview!A1:H20",include:"values,formulas",tableMaxRows:20,tableMaxCols:8}),
  await wb.inspect({kind:"table",range:"Problem Results!A1:P10",include:"values,formulas",tableMaxRows:10,tableMaxCols:16}),
  await wb.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",options:{useRegex:true,maxResults:100},summary:"formula errors"}),
];
for(const x of checks) console.log(x.ndjson);
for(const [sheetName,range,file] of [
  ["Overview","A1:Q20","pf_summary_overview.png"],
  ["Test Definitions","A1:G16","pf_summary_definitions.png"],
  ["Fair Rankings",`A1:E${Math.min(start+datasetRows.length,35)}`,"pf_summary_rankings.png"],
  ["Problem Results","A1:P18","pf_summary_problem_results.png"],
  ["PF Point Counts","A1:K18","pf_summary_points.png"],
  ["Per Run IGD","A1:L18","pf_summary_runs.png"],
]){
  const img=await wb.render({sheetName,range,scale:1.2});
  await fs.writeFile(path.join(base,file),new Uint8Array(await img.arrayBuffer()));
}
console.log(JSON.stringify({output,definitions:definitions.length,results:results.length,perRun:perRun.length,fullRanking:fullRanking.length},null,2));
