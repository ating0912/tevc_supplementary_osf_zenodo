from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, wilcoxon

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
BASE_DIR = ROOT / "outputs" / "selector_level_ablation_20260728"
RAW_ROOT = BASE_DIR / "raw_final_test"
OUT_DIR = BASE_DIR / "final_test_analysis"
PRIMARY = "SelectorAblation_FullSelector_ECMADE_MOO"
METHODS = [
    "SelectorAblation_FullSelector_ECMADE_MOO",
    "SelectorAblation_NoInstanceFeatures_ECMADE_MOO",
    "SelectorAblation_NoThetaFeatures_ECMADE_MOO",
    "SelectorAblation_RandomizedLabels_ECMADE_MOO",
]
METRIC_SPECS = [
    ("HV", "max"),
    ("IGD", "min"),
    ("PF_Overlap", "max"),
    ("PF_Drift", "min"),
    ("Diversity", "max"),
    ("Runtime", "min"),
]
ALPHA = 0.05


def discover_runs(raw_root: Path) -> tuple[pd.DataFrame, dict, dict]:
    rows = []
    pfs = {}
    fronts_by_instance = {}
    for pf_file in raw_root.glob("*/*/*/K_*/*/run_*/pf_obj.csv"):
        run_dir = pf_file.parent
        method = run_dir.parent.name
        if method not in METHODS:
            continue
        k_dir = run_dir.parent.parent.name
        instance = run_dir.parent.parent.parent.name
        split = run_dir.parent.parent.parent.parent.name
        variant = run_dir.parent.parent.parent.parent.parent.name
        run = int(run_dir.name.split("_")[-1])
        try:
            k_value = int(k_dir.split("_")[-1])
        except ValueError:
            k_value = np.nan
        pf = read_matrix(pf_file)
        if len(pf) == 0:
            continue
        meta_path = run_dir / "theta_metadata.csv"
        meta = pd.read_csv(meta_path, encoding="utf-8-sig").iloc[0] if meta_path.exists() else pd.Series(dtype=object)
        runtime = read_runtime(run_dir / "runtime.csv")
        key = (split, instance, int(k_value), method, run)
        group_key = (split, instance, int(k_value))
        pfs[key] = pf
        fronts_by_instance.setdefault(group_key, []).append(pf)
        rows.append(
            {
                "variant": variant,
                "split": split,
                "instance": instance,
                "K": int(k_value),
                "method": method,
                "run": run,
                "theta_id": str(meta.get("theta_id", "")),
                "S": float(meta.get("S", np.nan)),
                "operator": str(meta.get("operator", "")),
                "migration": str(meta.get("migration", "")),
                "elite_ratio": float(meta.get("elite_ratio", np.nan)),
                "stagnation_threshold": float(meta.get("stagnation_threshold", np.nan)),
                "Runtime": runtime,
                "PF_Size": len(pf),
                "run_dir": str(run_dir),
            }
        )
    run_df = pd.DataFrame(rows)
    if run_df.empty:
        raise RuntimeError(f"No selector-level ablation runs found under {raw_root}")
    return run_df, pfs, fronts_by_instance


def add_pf_metrics(run_df: pd.DataFrame, pfs: dict, fronts_by_instance: dict) -> pd.DataFrame:
    ref_info = {}
    for group_key, fronts in fronts_by_instance.items():
        union = np.vstack(fronts)
        ideal = union.min(axis=0)
        nadir = union.max(axis=0)
        ref = thin(nondominated(normalize(union, ideal, nadir)))
        ref_info[group_key] = (ideal, nadir, ref)

    norm_fronts = {}
    rows = []
    for rec in run_df.to_dict("records"):
        key = (rec["split"], rec["instance"], int(rec["K"]), rec["method"], int(rec["run"]))
        ideal, nadir, ref = ref_info[(rec["split"], rec["instance"], int(rec["K"]))]
        nf = thin(nondominated(normalize(pfs[key], ideal, nadir)))
        norm_fronts[key] = nf
        rows.append(
            {
                **rec,
                "HV": hv2d(nf),
                "IGD": igd(nf, ref),
                "PF_Overlap": overlap(nf, ref),
                "Diversity": diversity(nf),
            }
        )
    metrics = pd.DataFrame(rows)

    drift_rows = []
    for keys, base in metrics.groupby(["split", "instance", "K", "method"], sort=False):
        split, instance, k_value, method = keys
        fronts = [norm_fronts[(split, instance, int(k_value), method, int(run))] for run in base["run"]]
        centroids = np.vstack([centroid(front) for front in fronts if len(front)])
        mean_c = np.nanmean(centroids, axis=0)
        drifts = [float(np.sqrt(((centroid(front) - mean_c) ** 2).sum())) for front in fronts if len(front)]
        drift_rows.append(
            {
                "split": split,
                "instance": instance,
                "K": int(k_value),
                "method": method,
                "PF_Drift": float(np.nanmean(drifts)),
            }
        )
    return metrics.merge(pd.DataFrame(drift_rows), on=["split", "instance", "K", "method"], how="left")


def summarize_instances(run_metrics: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["split", "instance", "K", "method"]
    agg_cols = ["HV", "IGD", "PF_Overlap", "PF_Drift", "Diversity", "Runtime", "PF_Size"]
    summary = run_metrics.groupby(group_cols, sort=False)[agg_cols].agg(["mean", "std"]).reset_index()
    summary.columns = ["_".join(col).rstrip("_") for col in summary.columns.to_flat_index()]
    summary["runs"] = run_metrics.groupby(group_cols, sort=False)["run"].nunique().to_numpy()
    return summary


def add_ranks(instance_summary: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for _, group in instance_summary.groupby(["split", "instance", "K"], sort=False):
        frame = group.copy()
        rank_cols = []
        for metric, direction in METRIC_SPECS:
            source = f"{metric}_mean"
            rank_col = f"rank_{metric}"
            frame[rank_col] = frame[source].rank(ascending=(direction == "min"), method="average")
            rank_cols.append(rank_col)
        frame["RankScore"] = frame[rank_cols].mean(axis=1)
        frame["InstanceRank"] = frame["RankScore"].rank(ascending=True, method="average")
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def overall_summary(ranked: pd.DataFrame) -> pd.DataFrame:
    overall = (
        ranked.groupby("method", sort=False)
        .agg(
            instances=("instance", "count"),
            mean_HV=("HV_mean", "mean"),
            mean_IGD=("IGD_mean", "mean"),
            mean_PF_Overlap=("PF_Overlap_mean", "mean"),
            mean_PF_Drift=("PF_Drift_mean", "mean"),
            mean_Diversity=("Diversity_mean", "mean"),
            mean_Runtime=("Runtime_mean", "mean"),
            mean_RankScore=("RankScore", "mean"),
            mean_InstanceRank=("InstanceRank", "mean"),
            first_place_instances=("InstanceRank", lambda s: int((s == 1).sum())),
        )
        .reset_index()
    )
    for metric, direction in METRIC_SPECS:
        col = f"mean_{metric}"
        overall[f"overall_rank_{metric}"] = overall[col].rank(ascending=(direction == "min"), method="average")
    rank_cols = [c for c in overall.columns if c.startswith("overall_rank_")]
    overall["overall_RankScore"] = overall[rank_cols].mean(axis=1)
    return overall.sort_values(["overall_RankScore", "mean_RankScore", "method"])


def holm_adjust(p_values: list[float]) -> list[float]:
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    adjusted = [np.nan] * len(p_values)
    running = 0.0
    m = len(p_values)
    for rank, idx in enumerate(order):
        value = min(1.0, (m - rank) * p_values[idx])
        running = max(running, value)
        adjusted[idx] = running
    return adjusted


def signed(series: pd.Series, direction: str) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values if direction == "max" else -values


def safe_wilcoxon(diff: np.ndarray) -> tuple[float, float]:
    diff = diff[np.isfinite(diff)]
    diff = diff[np.abs(diff) > 1e-12]
    if diff.size == 0:
        return 0.0, 1.0
    stat, p_value = wilcoxon(diff, zero_method="wilcox", alternative="greater")
    return float(stat), float(p_value)


def build_statistics(ranked: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = ranked.copy()
    data["paired_unit"] = data["split"].astype(str) + "::" + data["instance"].astype(str) + "::K" + data["K"].astype(str)
    metric_map = {"RankScore": "min", **{f"{metric}_mean": direction for metric, direction in METRIC_SPECS}}
    friedman_rows = []
    wilcoxon_rows = []
    for metric, direction in metric_map.items():
        wide_raw = data.pivot(index="paired_unit", columns="method", values=metric)
        cols = [m for m in METHODS if m in wide_raw.columns]
        wide = wide_raw[cols].apply(lambda col: signed(col, direction), axis=0).dropna(axis=0, how="any")
        if wide.shape[0] >= 2 and wide.shape[1] >= 3:
            stat, p_value = friedmanchisquare(*[wide[col].to_numpy(dtype=float) for col in wide.columns])
        else:
            stat, p_value = np.nan, np.nan
        friedman_rows.append(
            {
                "metric": metric,
                "direction": direction,
                "paired_unit": "split-instance-K",
                "n_paired_units": int(wide.shape[0]),
                "friedman_chi_square": float(stat) if np.isfinite(stat) else np.nan,
                "p_value": float(p_value) if np.isfinite(p_value) else np.nan,
                "alpha": ALPHA,
                "significant": bool(np.isfinite(p_value) and p_value < ALPHA),
            }
        )
        if PRIMARY not in wide.columns:
            continue
        rows = []
        x = wide[PRIMARY].to_numpy(dtype=float)
        for baseline in wide.columns:
            if baseline == PRIMARY:
                continue
            y = wide[baseline].to_numpy(dtype=float)
            diff = x - y
            stat_w, p_w = safe_wilcoxon(diff)
            rows.append(
                {
                    "metric": metric,
                    "direction": direction,
                    "paired_unit": "split-instance-K",
                    "n_paired_units": int(wide.shape[0]),
                    "primary": PRIMARY,
                    "baseline": baseline,
                    "alternative": "primary better than baseline",
                    "median_signed_improvement": float(np.nanmedian(diff)),
                    "wins": int((diff > 1e-12).sum()),
                    "ties": int((np.abs(diff) <= 1e-12).sum()),
                    "losses": int((diff < -1e-12).sum()),
                    "wilcoxon_stat": stat_w,
                    "raw_p_value": p_w,
                    "alpha": ALPHA,
                }
            )
        for row, p_adj in zip(rows, holm_adjust([row["raw_p_value"] for row in rows])):
            row["holm_p_value"] = p_adj
            row["significant_after_holm"] = bool(p_adj < ALPHA)
            wilcoxon_rows.append(row)
    return pd.DataFrame(friedman_rows), pd.DataFrame(wilcoxon_rows)


def write_readme(overall: pd.DataFrame, friedman: pd.DataFrame, pairwise: pd.DataFrame) -> None:
    rank_friedman = friedman[friedman["metric"].eq("RankScore")].iloc[0]
    best = overall.iloc[0]
    primary = overall[overall["method"].eq(PRIMARY)].iloc[0]
    lines = [
        "# Selector-Level Ablation Final-Test Analysis",
        "",
        "- Variants: Full selector, no instance features, no theta features, randomized labels.",
        "- Final-test budget: 32 synthetic test instances x 10 independent runs per variant.",
        "- Paired unit: split-instance-K.",
        "- RankScore is an average-rank aggregate over HV, IGD, PF_Overlap, PF_Drift, Diversity, and Runtime; lower is better.",
        "",
        f"- Best descriptive overall_RankScore: {best['method']} ({best['overall_RankScore']:.6g}).",
        f"- Full selector overall_RankScore: {primary['overall_RankScore']:.6g}; mean_RankScore: {primary['mean_RankScore']:.6g}.",
        f"- RankScore Friedman test: chi-square={rank_friedman['friedman_chi_square']:.6g}, p={rank_friedman['p_value']:.6g}.",
        "",
        "## RankScore Pairwise Tests",
        "",
        pairwise[pairwise["metric"].eq("RankScore")].to_csv(index=False),
    ]
    (OUT_DIR / "README_selector_level_ablation.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_df, pfs, fronts_by_instance = discover_runs(RAW_ROOT)
    run_metrics = add_pf_metrics(run_df, pfs, fronts_by_instance)
    instance_summary = summarize_instances(run_metrics)
    ranked = add_ranks(instance_summary)
    overall = overall_summary(ranked)
    friedman, pairwise = build_statistics(ranked)
    completeness = (
        run_metrics.assign(instance_key=run_metrics["split"] + "::" + run_metrics["instance"] + "::K" + run_metrics["K"].astype(str))
        .groupby("method", sort=False)
        .agg(instances=("instance_key", "nunique"), runs=("run", "count"))
        .reset_index()
    )

    run_metrics.to_csv(OUT_DIR / "selector_ablation_run_metrics.csv", index=False, encoding="utf-8-sig")
    instance_summary.to_csv(OUT_DIR / "selector_ablation_instance_method_summary.csv", index=False, encoding="utf-8-sig")
    ranked.to_csv(OUT_DIR / "selector_ablation_instance_method_ranked.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(OUT_DIR / "selector_ablation_overall_summary.csv", index=False, encoding="utf-8-sig")
    friedman.to_csv(OUT_DIR / "selector_ablation_friedman_tests.csv", index=False, encoding="utf-8-sig")
    pairwise.to_csv(OUT_DIR / "selector_ablation_pairwise_wilcoxon_holm.csv", index=False, encoding="utf-8-sig")
    completeness.to_csv(OUT_DIR / "selector_ablation_run_completeness.csv", index=False, encoding="utf-8-sig")
    write_readme(overall, friedman, pairwise)
    print(f"OUT_DIR={OUT_DIR}")
    print(completeness.to_string(index=False))
    print(overall.to_string(index=False))
    print(pairwise[pairwise["metric"].eq("RankScore")].to_string(index=False))


if __name__ == "__main__":
    main()
