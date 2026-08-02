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
OUT_ROOT = ROOT / "p0_lite_outputs"
OUT_DIR = OUT_ROOT / "experiment_c_formal_five_method_no_replicate_20260731"
PRIMARY = "ExperimentC_NoReplicate_ECMADE_MOO"
METHODS = {
    "HandCrafted_ECMADE_MOO": OUT_ROOT / "synthetic_constrained_portfolio",
    "RandomConfig_ECMADE_MOO": OUT_ROOT / "random_config_ecmade_moo_20260711_074253",
    "BayesianConfig_ECMADE_MOO": OUT_ROOT / "bayesian_config_ecmade_moo_20260713_140251" / "final_test",
    "MetaDesigned_ECMADE_MOO": OUT_ROOT / "meta_designed_ecmade_moo_20260713_164632",
    "ExperimentC_NoReplicate_ECMADE_MOO": OUT_ROOT / "experiment_c_stability_ecmade_moo_no_replicate_20260730",
}
ACTUAL_DIR = {
    "HandCrafted_ECMADE_MOO": "ECMADE_MOO",
    "ExperimentC_NoReplicate_ECMADE_MOO": "ExperimentC_StabilityAware_ECMADE_MOO",
}
METRIC_SPECS = [
    ("HV", "max"),
    ("IGD", "min"),
    ("PF_Overlap", "max"),
    ("PF_Drift", "min"),
    ("Diversity", "max"),
    ("Runtime", "min"),
]
ENDPOINT_DIRECTIONS = {
    "PerformanceScore": "max",
    "StabilityScore": "max",
    "DiversityScore": "max",
    "RuntimeScore": "max",
    "J_stability": "max",
    "J_performance": "max",
    "EqualWeightedScore": "max",
    "StabilityWeightedRank": "min",
    "PerformanceRank": "min",
    "EqualWeightedRank": "min",
    "RankBasedCompositeRank": "min",
    "InstanceRankScore": "min",
}
ALPHA = 0.05


def iter_pf_files(method: str, folder: Path):
    actual = ACTUAL_DIR.get(method, method)
    yield from folder.glob(f"test/*/K_*/{actual}/run_*/pf_obj.csv")


def parse_run(pf_file: Path, method: str) -> dict:
    run_dir = pf_file.parent
    return {
        "split": run_dir.parent.parent.parent.parent.name,
        "instance": run_dir.parent.parent.parent.name,
        "K": int(run_dir.parent.parent.name.split("_")[-1]),
        "method": method,
        "run": int(run_dir.name.split("_")[-1]),
        "run_dir": run_dir,
    }


def read_optional_csv(run_dir: Path, name: str) -> pd.Series:
    path = run_dir / name
    if not path.exists():
        return pd.Series(dtype=object)
    try:
        return pd.read_csv(path, encoding="utf-8-sig").iloc[0]
    except Exception:
        return pd.Series(dtype=object)


def discover_runs() -> tuple[pd.DataFrame, dict, dict]:
    rows = []
    pfs = {}
    fronts_by_instance = {}
    for method, folder in METHODS.items():
        for pf_file in iter_pf_files(method, folder):
            rec = parse_run(pf_file, method)
            pf = read_matrix(pf_file)
            if len(pf) == 0:
                continue
            run_dir = rec["run_dir"]
            feasible = read_optional_csv(run_dir, "feasible_rate.csv")
            constraints = read_optional_csv(run_dir, "constraint_metrics.csv")
            theta = read_optional_csv(run_dir, "theta_metadata.csv")
            key = (rec["split"], rec["instance"], rec["K"], method, rec["run"])
            group_key = (rec["split"], rec["instance"], rec["K"])
            pfs[key] = pf
            fronts_by_instance.setdefault(group_key, []).append(pf)
            rows.append(
                {
                    **{k: v for k, v in rec.items() if k != "run_dir"},
                    "PF_Size": len(pf),
                    "Runtime": read_runtime(run_dir / "runtime.csv"),
                    "PF_Feasible_Rate": feasible.get("PF_Feasible_Rate", np.nan),
                    "Population_Feasible_Rate": feasible.get("Population_Feasible_Rate", np.nan),
                    "PF_Mean_Violation": constraints.get("PF_Mean_Violation", np.nan),
                    "PF_Max_Violation": constraints.get("PF_Max_Violation", np.nan),
                    "Population_Mean_Violation": constraints.get("Population_Mean_Violation", np.nan),
                    "Population_Max_Violation": constraints.get("Population_Max_Violation", np.nan),
                    "theta_id": theta.get("theta_id", ""),
                    "N": theta.get("N", np.nan),
                    "maxFE": theta.get("maxFE", np.nan),
                    "rng_policy": "rng(run,'mcg16807')",
                    "seed_policy": "run index",
                    "run_dir": str(run_dir),
                }
            )
    run_df = pd.DataFrame(rows)
    if run_df.empty:
        raise RuntimeError("No formal five-method final-test runs found.")
    return run_df, pfs, fronts_by_instance


def compute_common_reference_metrics() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    run_df, pfs, fronts_by_instance = discover_runs()
    ref_rows = []
    ref_info = {}
    for instance_key, fronts in fronts_by_instance.items():
        union = np.vstack(fronts)
        ideal = union.min(axis=0)
        nadir = union.max(axis=0)
        ref = thin(nondominated(normalize(union, ideal, nadir)))
        ref_info[instance_key] = (ideal, nadir, ref)
        ref_rows.append(
            {
                "split": instance_key[0],
                "instance": instance_key[1],
                "K": instance_key[2],
                "ideal_obj1": ideal[0],
                "ideal_obj2": ideal[1],
                "nadir_obj1": nadir[0],
                "nadir_obj2": nadir[1],
                "reference_points": len(ref),
                "methods_in_reference": len(METHODS),
            }
        )

    metric_rows = []
    norm_fronts = {}
    for rec in run_df.to_dict("records"):
        key = (rec["split"], rec["instance"], int(rec["K"]), rec["method"], int(rec["run"]))
        instance_key = (rec["split"], rec["instance"], int(rec["K"]))
        ideal, nadir, ref = ref_info[instance_key]
        nf = thin(nondominated(normalize(pfs[key], ideal, nadir)))
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
    agg_cols = [
        "HV",
        "IGD",
        "PF_Overlap",
        "Diversity",
        "Runtime",
        "PF_Size",
        "PF_Feasible_Rate",
        "Population_Feasible_Rate",
        "PF_Mean_Violation",
        "PF_Max_Violation",
        "Population_Mean_Violation",
        "Population_Max_Violation",
    ]
    for keys, base in run_metrics.groupby(["split", "instance", "K", "method"], sort=False):
        split, instance, k_value, method = keys
        fronts = [
            norm_fronts[(split, instance, int(k_value), method, int(run))]
            for run in base["run"]
        ]
        centroids = np.vstack([centroid(front) for front in fronts if len(front)])
        mean_c = np.nanmean(centroids, axis=0)
        drifts = [
            float(np.sqrt(((centroid(front) - mean_c) ** 2).sum()))
            for front in fronts
            if len(front)
        ]
        rec = {
            "split": split,
            "instance": instance,
            "K": int(k_value),
            "method": method,
            "runs": int(base["run"].nunique()),
            "theta_ids": "|".join(sorted(str(x) for x in base["theta_id"].dropna().unique() if str(x))),
            "N": pd.to_numeric(base["N"], errors="coerce").dropna().unique()[0] if pd.to_numeric(base["N"], errors="coerce").notna().any() else np.nan,
            "maxFE": pd.to_numeric(base["maxFE"], errors="coerce").dropna().unique()[0] if pd.to_numeric(base["maxFE"], errors="coerce").notna().any() else np.nan,
            "rng_policy": base["rng_policy"].iloc[0],
            "seed_policy": base["seed_policy"].iloc[0],
            "PF_Drift": float(np.nanmean(drifts)),
        }
        for col in agg_cols:
            rec[col] = float(pd.to_numeric(base[col], errors="coerce").mean())
        inst_rows.append(rec)
    return pd.DataFrame(inst_rows), run_metrics, pd.DataFrame(ref_rows)


def add_metric_ranks(frame: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for _, group in frame.groupby(["split", "instance", "K"], sort=False):
        ranked = group.copy()
        rank_cols = []
        for metric, direction in METRIC_SPECS:
            col = f"rank_{metric}"
            ranked[col] = ranked[metric].rank(ascending=(direction == "min"), method="average")
            rank_cols.append(col)
        ranked["InstanceRankScore"] = ranked[rank_cols].mean(axis=1)
        ranked["RankBasedCompositeRank"] = ranked["InstanceRankScore"].rank(ascending=True, method="average")
        frames.append(ranked)
    return pd.concat(frames, ignore_index=True)


def normalize_series(values: pd.Series, direction: str) -> pd.Series:
    x = pd.to_numeric(values, errors="coerce").astype(float)
    if direction == "min":
        x = -x
    lo = x.min()
    hi = x.max()
    if not np.isfinite(lo) or not np.isfinite(hi) or abs(hi - lo) < 1e-12:
        return pd.Series(1.0, index=values.index)
    return (x - lo) / (hi - lo)


def add_endpoint_scores(ranked: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for _, group in ranked.groupby(["split", "instance", "K"], sort=False):
        out = group.copy()
        out["HV_score"] = normalize_series(out["HV"], "max")
        out["IGD_score"] = normalize_series(out["IGD"], "min")
        out["PF_Overlap_score"] = normalize_series(out["PF_Overlap"], "max")
        out["PF_Drift_score"] = normalize_series(out["PF_Drift"], "min")
        out["DiversityScore"] = normalize_series(out["Diversity"], "max")
        out["RuntimeScore"] = normalize_series(out["Runtime"], "min")
        out["PerformanceScore"] = 0.5 * out["HV_score"] + 0.5 * out["IGD_score"]
        out["StabilityScore"] = 0.5 * out["PF_Overlap_score"] + 0.5 * out["PF_Drift_score"]
        out["J_stability"] = (
            0.25 * out["PerformanceScore"]
            + 0.45 * out["StabilityScore"]
            + 0.20 * out["DiversityScore"]
            + 0.10 * out["RuntimeScore"]
        )
        out["J_performance"] = (
            0.45 * out["PerformanceScore"]
            + 0.25 * out["StabilityScore"]
            + 0.20 * out["DiversityScore"]
            + 0.10 * out["RuntimeScore"]
        )
        out["EqualWeightedScore"] = (
            out["PerformanceScore"] + out["StabilityScore"] + out["DiversityScore"] + out["RuntimeScore"]
        ) / 4.0
        out["PerformanceRank"] = out["PerformanceScore"].rank(ascending=False, method="average")
        out["StabilityWeightedRank"] = out["J_stability"].rank(ascending=False, method="average")
        out["EqualWeightedRank"] = out["EqualWeightedScore"].rank(ascending=False, method="average")
        frames.append(out)
    return pd.concat(frames, ignore_index=True)


def build_overall(ranked: pd.DataFrame) -> pd.DataFrame:
    overall = (
        ranked.groupby("method")
        .agg(
            instances=("instance", "nunique"),
            paired_units=("instance", "count"),
            runs=("runs", "sum"),
            mean_HV=("HV", "mean"),
            mean_IGD=("IGD", "mean"),
            mean_PF_Overlap=("PF_Overlap", "mean"),
            mean_PF_Drift=("PF_Drift", "mean"),
            mean_Diversity=("Diversity", "mean"),
            mean_Runtime=("Runtime", "mean"),
            mean_PerformanceScore=("PerformanceScore", "mean"),
            mean_StabilityScore=("StabilityScore", "mean"),
            mean_DiversityScore=("DiversityScore", "mean"),
            mean_RuntimeScore=("RuntimeScore", "mean"),
            mean_J_stability=("J_stability", "mean"),
            mean_J_performance=("J_performance", "mean"),
            mean_EqualWeightedScore=("EqualWeightedScore", "mean"),
            mean_StabilityWeightedRank=("StabilityWeightedRank", "mean"),
            mean_PerformanceRank=("PerformanceRank", "mean"),
            mean_EqualWeightedRank=("EqualWeightedRank", "mean"),
            mean_InstanceRankScore=("InstanceRankScore", "mean"),
            mean_RankBasedCompositeRank=("RankBasedCompositeRank", "mean"),
            stability_first_place=("StabilityWeightedRank", lambda s: int((s == 1).sum())),
            performance_first_place=("PerformanceRank", lambda s: int((s == 1).sum())),
            rankscore_first_place=("RankBasedCompositeRank", lambda s: int((s == 1).sum())),
            mean_PF_Feasible_Rate=("PF_Feasible_Rate", "mean"),
            mean_Population_Feasible_Rate=("Population_Feasible_Rate", "mean"),
            max_PF_Max_Violation=("PF_Max_Violation", "max"),
            max_Population_Max_Violation=("Population_Max_Violation", "max"),
        )
        .reset_index()
    )
    return overall.sort_values(["mean_StabilityWeightedRank", "mean_J_stability", "method"], ascending=[True, False, True])


def holm_adjust(p_values: list[float]) -> list[float]:
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    adjusted = [math.nan] * len(p_values)
    running = 0.0
    n = len(p_values)
    for rank, idx in enumerate(order):
        adj = min((n - rank) * p_values[idx], 1.0)
        running = max(running, adj)
        adjusted[idx] = running
    return adjusted


def rank_biserial(diff: np.ndarray) -> float:
    diff = diff[np.isfinite(diff)]
    diff = diff[np.abs(diff) > 1e-12]
    if len(diff) == 0:
        return 0.0
    ranks = rankdata(np.abs(diff), method="average")
    denom = len(diff) * (len(diff) + 1) / 2.0
    return float((ranks[diff > 0].sum() - ranks[diff < 0].sum()) / denom)


def vargha_delaney_a(x: np.ndarray, y: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    y = y[np.isfinite(y)]
    if len(x) == 0 or len(y) == 0:
        return math.nan
    wins = 0.0
    for value in x:
        wins += np.sum(value > y) + 0.5 * np.sum(np.abs(value - y) <= 1e-12)
    return float(wins / (len(x) * len(y)))


def safe_wilcoxon(diff: np.ndarray, alternative: str) -> tuple[float, float]:
    diff = diff[np.isfinite(diff)]
    diff = diff[np.abs(diff) > 1e-12]
    if len(diff) == 0:
        return 0.0, 1.0
    try:
        stat, p_value = wilcoxon(diff, zero_method="wilcox", alternative=alternative)
        return float(stat), float(p_value)
    except ValueError:
        return math.nan, 1.0


def build_statistics(ranked: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data = ranked.copy()
    data["paired_unit"] = data["split"].astype(str) + "::" + data["instance"].astype(str) + "::K" + data["K"].astype(str)
    endpoints = {**{m: d for m, d in METRIC_SPECS}, **ENDPOINT_DIRECTIONS}
    friedman_rows = []
    wilcoxon_rows = []
    primary_rows = []
    for endpoint, direction in endpoints.items():
        if endpoint not in data.columns:
            continue
        wide_raw = data.pivot(index="paired_unit", columns="method", values=endpoint)
        columns = [m for m in METHODS if m in wide_raw.columns]
        wide = wide_raw[columns].dropna(axis=0, how="any")
        if wide.empty:
            continue
        oriented = wide if direction == "max" else -wide
        if oriented.shape[1] >= 3 and oriented.shape[0] >= 2:
            stat, p_value = friedmanchisquare(*[oriented[c].to_numpy(dtype=float) for c in oriented.columns])
        else:
            stat, p_value = math.nan, math.nan
        avg_ranks = wide.rank(axis=1, ascending=(direction == "min"), method="average").mean(axis=0)
        friedman_rows.append(
            {
                "endpoint": endpoint,
                "direction": direction,
                "paired_units": int(len(wide)),
                "methods": int(len(wide.columns)),
                "friedman_chi_square": float(stat) if np.isfinite(stat) else math.nan,
                "degrees_of_freedom": int(len(wide.columns) - 1),
                "p_value": float(p_value) if np.isfinite(p_value) else math.nan,
                "average_method_ranks": "; ".join(f"{m}={avg_ranks[m]:.4f}" for m in wide.columns),
            }
        )
        raw_p = []
        temp_rows = []
        for a, b in itertools.combinations(wide.columns, 2):
            diff = oriented[a].to_numpy(dtype=float) - oriented[b].to_numpy(dtype=float)
            stat_w, p_two = safe_wilcoxon(diff, "two-sided")
            _, p_greater = safe_wilcoxon(diff, "greater")
            raw_p.append(p_two)
            temp_rows.append(
                {
                    "endpoint": endpoint,
                    "direction": direction,
                    "method_a": a,
                    "method_b": b,
                    "paired_units": int(len(diff)),
                    "median_oriented_difference": float(np.nanmedian(diff)),
                    "mean_oriented_difference": float(np.nanmean(diff)),
                    "wins_a": int((diff > 1e-12).sum()),
                    "ties": int((np.abs(diff) <= 1e-12).sum()),
                    "wins_b": int((diff < -1e-12).sum()),
                    "wilcoxon_stat": stat_w,
                    "two_sided_p_value": p_two,
                    "one_sided_greater_p_value": p_greater,
                    "rank_biserial_correlation": rank_biserial(diff),
                    "vargha_delaney_A_oriented": vargha_delaney_a(oriented[a].to_numpy(dtype=float), oriented[b].to_numpy(dtype=float)),
                }
            )
        for row, adjusted in zip(temp_rows, holm_adjust(raw_p)):
            row["holm_two_sided_p_value"] = adjusted
            row["significant_0_05"] = bool(adjusted < ALPHA)
            wilcoxon_rows.append(row)
            if row["method_a"] == PRIMARY or row["method_b"] == PRIMARY:
                primary_rows.append(row.copy())
    return pd.DataFrame(friedman_rows), pd.DataFrame(wilcoxon_rows), pd.DataFrame(primary_rows)


def write_readme(overall: pd.DataFrame, friedman: pd.DataFrame, primary: pd.DataFrame) -> None:
    lines = [
        "# Experiment C Formal Five-Method No-Replicate Comparison",
        "",
        "Scope: Hand-crafted, RandomConfig, BayesianConfig, Meta-designed, and ExperimentC NoReplicate Stability-aware.",
        "Replicate-included audit is intentionally excluded from the common empirical reference front.",
        "",
        "Primary endpoint: StabilityWeightedRank derived from J_stability.",
        "J_stability = 0.25*PerformanceScore + 0.45*StabilityScore + 0.20*DiversityScore + 0.10*RuntimeScore.",
        "Scores are min-max normalized inside each test instance and five-method comparison group.",
        "",
        "## Overall",
        "",
        overall.to_markdown(index=False),
        "",
        "## Friedman",
        "",
        friedman.to_markdown(index=False),
        "",
        "## Primary-Method Wilcoxon",
        "",
        primary.to_markdown(index=False),
    ]
    (OUT_DIR / "README_formal_five_method_no_replicate.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    instance_metrics, run_metrics, reference_info = compute_common_reference_metrics()
    ranked = add_endpoint_scores(add_metric_ranks(instance_metrics))
    overall = build_overall(ranked)
    friedman, wilcoxon_df, primary_wilcoxon = build_statistics(ranked)
    completeness = (
        run_metrics.groupby(["method", "split", "instance", "K"], as_index=False)
        .agg(runs=("run", "nunique"))
        .groupby("method", as_index=False)
        .agg(paired_units=("instance", "count"), min_runs=("runs", "min"), max_runs=("runs", "max"), total_runs=("runs", "sum"))
    )
    invalid = instance_metrics[
        (pd.to_numeric(instance_metrics["PF_Feasible_Rate"], errors="coerce") < 1.0)
        | (pd.to_numeric(instance_metrics["PF_Max_Violation"], errors="coerce") > 1e-8)
    ].copy()

    run_metrics.to_csv(OUT_DIR / "formal_five_run_metrics.csv", index=False, encoding="utf-8-sig")
    instance_metrics.to_csv(OUT_DIR / "formal_five_instance_method_metrics_raw.csv", index=False, encoding="utf-8-sig")
    reference_info.to_csv(OUT_DIR / "formal_five_reference_front_info.csv", index=False, encoding="utf-8-sig")
    ranked.to_csv(OUT_DIR / "formal_five_instance_method_endpoints_ranked.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(OUT_DIR / "formal_five_overall_summary.csv", index=False, encoding="utf-8-sig")
    completeness.to_csv(OUT_DIR / "formal_five_run_completeness.csv", index=False, encoding="utf-8-sig")
    invalid.to_csv(OUT_DIR / "formal_five_constraint_invalid_units.csv", index=False, encoding="utf-8-sig")
    friedman.to_csv(OUT_DIR / "formal_five_friedman_tests.csv", index=False, encoding="utf-8-sig")
    wilcoxon_df.to_csv(OUT_DIR / "formal_five_pairwise_wilcoxon_holm.csv", index=False, encoding="utf-8-sig")
    primary_wilcoxon.to_csv(OUT_DIR / "formal_five_primary_method_wilcoxon_holm.csv", index=False, encoding="utf-8-sig")
    write_readme(overall, friedman, primary_wilcoxon)
    print(f"OUT_DIR={OUT_DIR}")
    print(completeness.to_string(index=False))
    print(overall[["method", "mean_J_stability", "mean_StabilityWeightedRank", "stability_first_place", "mean_InstanceRankScore"]].to_string(index=False))


if __name__ == "__main__":
    main()
