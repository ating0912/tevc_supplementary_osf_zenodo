from __future__ import annotations

import itertools
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, rankdata, wilcoxon

from rank_knowledge_base_parameter_search import (
    centroid,
    diversity,
    hv2d,
    igd,
    nondominated,
    normalize,
    overlap,
    read_matrix,
    read_runtime,
    thin,
)


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "p0_lite_outputs" / "p1_mokp_config_comparison_20260719"
SOURCES = [
    ROOT / "p0_lite_outputs" / "p1_multi_objective_knapsack_full_independent_20260719",
    ROOT / "p0_lite_outputs" / "p1_mokp_random_config_full_20260719",
    ROOT / "p0_lite_outputs" / "p1_mokp_meta_transfer_full_20260719",
    ROOT / "p0_lite_outputs" / "p1_mokp_bayesian_config_full_20260719" / "final_test",
    ROOT / "p0_lite_outputs" / "p1_mokp_experiment_c_stability_full_20260729",
    ROOT / "p0_lite_outputs" / "p1_mokp_experiment_c_global_theta_diagnostic_20260729",
]
METHODS = [
    "NSGAII",
    "SPEA2",
    "MOEAD",
    "GDE3",
    "A_MPMO",
    "RandomConfig_ECMADE_MOO",
    "MetaTransfer_ECMADE_MOO",
    "BayesianConfig_ECMADE_MOO",
    "ExperimentC_StabilityAware_ECMADE_MOO",
    "ExperimentC_GlobalTheta034_ECMADE_MOO",
    "ExperimentC_GlobalTheta037_ECMADE_MOO",
    "ECMADE_MOO",
]
PAIR_KEYS = ["split", "instance"]
METRICS = {
    "HV": "max",
    "IGD": "min",
    "PF_Overlap": "max",
    "PF_Drift": "min",
    "Diversity": "max",
    "Runtime": "min",
}


def scalar(row: pd.Series, name: str, default=math.nan):
    return row[name] if name in row else default


def read_metadata(run_dir: Path) -> dict | None:
    meta_file = run_dir / "instance_metadata.csv"
    if not meta_file.exists():
        meta_file = run_dir / "theta_metadata.csv"
    if not meta_file.exists():
        return None
    meta = pd.read_csv(meta_file, encoding="utf-8-sig").iloc[0]
    return {
        "split": str(scalar(meta, "split", "test")),
        "instance": str(scalar(meta, "instance", "")),
        "items": int(scalar(meta, "items")),
        "objectives": int(scalar(meta, "objectives", 2)),
        "capacity_ratio": float(scalar(meta, "capacity_ratio")),
        "profit_mode": str(scalar(meta, "profit_mode", "")),
        "replicate": int(scalar(meta, "replicate", 1)),
        "seed": int(scalar(meta, "seed")),
    }


def read_feasible(run_dir: Path) -> tuple[float, float]:
    path = run_dir / "feasible_rate.csv"
    if not path.exists():
        return math.nan, math.nan
    try:
        row = pd.read_csv(path, encoding="utf-8-sig").iloc[0]
        return float(row["PF_Feasible_Rate"]), float(row["Population_Feasible_Rate"])
    except Exception:
        return math.nan, math.nan


def discover_runs() -> tuple[pd.DataFrame, dict, dict]:
    rows = []
    pfs = {}
    fronts_by_instance = {}
    for source in SOURCES:
        for pf_file in source.glob("test/*/*/run_*/pf_obj.csv"):
            run_dir = pf_file.parent
            method = run_dir.parent.name
            if method not in METHODS:
                continue
            meta = read_metadata(run_dir)
            if meta is None:
                continue
            run = int(run_dir.name.split("_")[-1])
            pf = read_matrix(pf_file)
            if len(pf) == 0:
                continue
            pf_feas, pop_feas = read_feasible(run_dir)
            rec = {
                **meta,
                "method": method,
                "run": run,
                "PF_Size": len(pf),
                "Runtime": read_runtime(run_dir / "runtime.csv"),
                "PF_Feasible_Rate": pf_feas,
                "Population_Feasible_Rate": pop_feas,
                "run_dir": str(run_dir),
            }
            key = (meta["split"], meta["instance"], method, run)
            instance_key = (meta["split"], meta["instance"])
            rows.append(rec)
            pfs[key] = pf
            fronts_by_instance.setdefault(instance_key, []).append(pf)
    run_df = pd.DataFrame(rows)
    if run_df.empty:
        raise RuntimeError("No P1 MOKP runs found for config comparison")
    return run_df, pfs, fronts_by_instance


def compute_metrics() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    run_df, pfs, fronts_by_instance = discover_runs()
    ref_info = {}
    ref_rows = []
    for instance_key, fronts in fronts_by_instance.items():
        union = np.vstack(fronts)
        ideal = union.min(axis=0)
        nadir = union.max(axis=0)
        ref = thin(nondominated(normalize(union, ideal, nadir)), max_points=200)
        ref_info[instance_key] = (ideal, nadir, ref)
        ref_rows.append(
            {
                "split": instance_key[0],
                "instance": instance_key[1],
                "ideal_obj1": ideal[0],
                "ideal_obj2": ideal[1],
                "nadir_obj1": nadir[0],
                "nadir_obj2": nadir[1],
                "reference_points": len(ref),
            }
        )

    metric_rows = []
    norm_fronts = {}
    for rec in run_df.to_dict("records"):
        key = (rec["split"], rec["instance"], rec["method"], int(rec["run"]))
        ideal, nadir, ref = ref_info[(rec["split"], rec["instance"])]
        nf = thin(nondominated(normalize(pfs[key], ideal, nadir)), max_points=200)
        norm_fronts[key] = nf
        metric_rows.append(
            {
                **rec,
                "HV": hv2d(nf),
                "IGD": igd(nf, ref),
                "PF_Overlap": overlap(nf, ref),
                "Diversity": diversity(nf),
            }
        )
    run_metrics = pd.DataFrame(metric_rows)

    inst_rows = []
    group_cols = [
        "split",
        "instance",
        "items",
        "objectives",
        "capacity_ratio",
        "profit_mode",
        "replicate",
        "seed",
        "method",
    ]
    for keys, base in run_metrics.groupby(group_cols, sort=False):
        rec = dict(zip(group_cols, keys))
        fronts = [
            norm_fronts[(rec["split"], rec["instance"], rec["method"], int(run))]
            for run in base["run"]
        ]
        centroids = np.vstack([centroid(front) for front in fronts if len(front)])
        mean_c = np.nanmean(centroids, axis=0)
        drifts = [
            float(np.sqrt(((centroid(front) - mean_c) ** 2).sum()))
            for front in fronts
            if len(front)
        ]
        inst_rows.append(
            {
                **rec,
                "runs": int(base["run"].nunique()),
                "PF_Size": float(base["PF_Size"].mean()),
                "HV": float(base["HV"].mean()),
                "IGD": float(base["IGD"].mean()),
                "PF_Overlap": float(base["PF_Overlap"].mean()),
                "PF_Drift": float(np.nanmean(drifts)),
                "Diversity": float(base["Diversity"].mean()),
                "Runtime": float(base["Runtime"].mean()),
                "PF_Feasible_Rate": float(base["PF_Feasible_Rate"].mean()),
                "Population_Feasible_Rate": float(base["Population_Feasible_Rate"].mean()),
            }
        )
    return pd.DataFrame(inst_rows), run_metrics, pd.DataFrame(ref_rows)


def add_ranks(frame: pd.DataFrame) -> pd.DataFrame:
    ranked_frames = []
    for _, base in frame.groupby(PAIR_KEYS, sort=False):
        ranked = base.copy()
        rank_cols = []
        for metric, direction in METRICS.items():
            col = f"rank_{metric}"
            ranked[col] = ranked[metric].rank(ascending=(direction == "min"), method="average")
            rank_cols.append(col)
        ranked["RankScore"] = ranked[rank_cols].mean(axis=1)
        ranked["OverallInstanceRank"] = ranked["RankScore"].rank(ascending=True, method="average")
        ranked_frames.append(ranked)
    return pd.concat(ranked_frames, ignore_index=True)


def build_overall(ranked: pd.DataFrame) -> pd.DataFrame:
    overall = (
        ranked.groupby("method")
        .agg(
            instances=("instance", "nunique"),
            runs=("runs", "sum"),
            mean_HV=("HV", "mean"),
            mean_IGD=("IGD", "mean"),
            mean_PF_Overlap=("PF_Overlap", "mean"),
            mean_PF_Drift=("PF_Drift", "mean"),
            mean_Diversity=("Diversity", "mean"),
            mean_Runtime=("Runtime", "mean"),
            mean_PF_Size=("PF_Size", "mean"),
            mean_PF_Feasible_Rate=("PF_Feasible_Rate", "mean"),
            mean_RankScore=("RankScore", "mean"),
            mean_InstanceRank=("OverallInstanceRank", "mean"),
            first_place_instances=("OverallInstanceRank", lambda s: int((s == 1).sum())),
        )
        .reset_index()
    )
    for metric, direction in METRICS.items():
        overall[f"overall_rank_{metric}"] = overall[f"mean_{metric}"].rank(
            ascending=(direction == "min"), method="average"
        )
    overall["overall_RankScore"] = overall[[f"overall_rank_{m}" for m in METRICS]].mean(axis=1)
    return overall.sort_values(["overall_RankScore", "mean_InstanceRank", "method"])


def oriented(values: pd.Series, direction: str) -> pd.Series:
    return values if direction == "max" else -values


def holm_adjust(p_values: list[float]) -> list[float]:
    n = len(p_values)
    order = sorted(range(n), key=lambda i: p_values[i])
    adjusted = [math.nan] * n
    running = 0.0
    for rank, idx in enumerate(order):
        adj = min((n - rank) * p_values[idx], 1.0)
        running = max(running, adj)
        adjusted[idx] = running
    return adjusted


def signed_rank_effect(diff: np.ndarray) -> float:
    diff = diff[np.isfinite(diff)]
    diff = diff[np.abs(diff) > 1e-12]
    if len(diff) == 0:
        return 0.0
    ranks = rankdata(np.abs(diff), method="average")
    denom = len(diff) * (len(diff) + 1) / 2.0
    return float((ranks[diff > 0].sum() - ranks[diff < 0].sum()) / denom)


def safe_wilcoxon(diff: np.ndarray) -> tuple[float, float]:
    diff = diff[np.isfinite(diff)]
    diff = diff[np.abs(diff) > 1e-12]
    if len(diff) == 0:
        return 0.0, 1.0
    try:
        stat, p_value = wilcoxon(diff, zero_method="wilcox", alternative="two-sided")
        return float(stat), float(p_value)
    except ValueError:
        return math.nan, 1.0


def build_statistics(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    friedman_rows = []
    wilcoxon_rows = []
    for metric, direction in METRICS.items():
        pivot = frame.pivot_table(index=PAIR_KEYS, columns="method", values=metric, aggfunc="mean")
        pivot = pivot[[m for m in METHODS if m in pivot.columns]].dropna(axis=0, how="any")
        if pivot.empty:
            continue
        transformed = pivot if direction == "max" else -pivot
        stat, p_value = friedmanchisquare(*[transformed[m].to_numpy() for m in pivot.columns])
        friedman_rows.append(
            {
                "metric": metric,
                "direction": direction,
                "instances": len(pivot),
                "methods": len(pivot.columns),
                "friedman_chi_square": float(stat),
                "friedman_p_value": float(p_value),
            }
        )
        raw_p = []
        temp_rows = []
        for a, b in itertools.combinations(pivot.columns, 2):
            diff = oriented(pivot[a], direction).to_numpy(dtype=float) - oriented(pivot[b], direction).to_numpy(dtype=float)
            stat_w, p_w = safe_wilcoxon(diff)
            raw_p.append(p_w)
            temp_rows.append(
                {
                    "metric": metric,
                    "direction": direction,
                    "method_a": a,
                    "method_b": b,
                    "instances": len(diff),
                    "median_oriented_difference": float(np.nanmedian(diff)),
                    "mean_oriented_difference": float(np.nanmean(diff)),
                    "wilcoxon_stat": stat_w,
                    "p_value": p_w,
                    "signed_rank_effect": signed_rank_effect(diff),
                }
            )
        for row, adj in zip(temp_rows, holm_adjust(raw_p)):
            row["holm_p_value"] = adj
            row["significant_0_05"] = adj < 0.05
            wilcoxon_rows.append(row)
    return pd.DataFrame(friedman_rows), pd.DataFrame(wilcoxon_rows)


def write_markdown(overall: pd.DataFrame, friedman: pd.DataFrame) -> None:
    lines = [
        "# P1 MOKP Configuration Comparison",
        "",
        "- Scope: six baseline algorithms plus RandomConfig, MetaTransfer, BayesianConfig, ExperimentC stability-aware ECMADE-MOO, and ExperimentC global-theta diagnostics.",
        "- Runs: 18 MOKP instances x 30 final runs per method.",
        "- Reference fronts are rebuilt from all included methods for fair ranking.",
        "",
        "## Overall Ranking",
        "",
        overall[
            [
                "method",
                "instances",
                "runs",
                "mean_HV",
                "mean_IGD",
                "mean_PF_Overlap",
                "mean_Runtime",
                "overall_RankScore",
                "mean_InstanceRank",
            ]
        ].to_markdown(index=False),
        "",
        "## Friedman Tests",
        "",
        friedman.to_markdown(index=False),
    ]
    (OUT_DIR / "README_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    instance_metrics, run_metrics, reference_info = compute_metrics()
    ranked = add_ranks(instance_metrics)
    overall = build_overall(ranked)
    friedman, wilcoxon_df = build_statistics(ranked)

    run_metrics.to_csv(OUT_DIR / "run_metrics.csv", index=False, encoding="utf-8-sig")
    reference_info.to_csv(OUT_DIR / "reference_front_info.csv", index=False, encoding="utf-8-sig")
    ranked.to_csv(OUT_DIR / "instance_method_metrics_ranked.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(OUT_DIR / "overall_method_summary.csv", index=False, encoding="utf-8-sig")
    friedman.to_csv(OUT_DIR / "friedman_tests.csv", index=False, encoding="utf-8-sig")
    wilcoxon_df.to_csv(OUT_DIR / "pairwise_wilcoxon.csv", index=False, encoding="utf-8-sig")
    write_markdown(overall, friedman)
    print(f"Wrote P1 MOKP config comparison to {OUT_DIR}")
    print(overall[["method", "instances", "runs", "mean_HV", "mean_IGD", "mean_PF_Overlap", "overall_RankScore"]])


if __name__ == "__main__":
    main()
