from __future__ import annotations

import itertools
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, rankdata, wilcoxon


ROOT = Path(__file__).resolve().parent
PRIMARY = "ExperimentC_NoReplicate_ECMADE_MOO"
WEIGHTS = {
    "rank_HV": 0.2,
    "rank_IGD": 0.2,
    "rank_PF_Overlap": 0.3,
    "rank_PF_Drift": 0.3,
}


DATASETS = [
    {
        "name": "synthetic_final_test",
        "ranked_path": ROOT
        / "p0_lite_outputs"
        / "experiment_c_replicate_audit_final_test_20260730"
        / "replicate_audit_instance_method_ranked.csv",
        "out_dir": ROOT / "p0_lite_outputs" / "experiment_c_replicate_audit_final_test_20260730",
        "pair_keys": ["split", "instance", "K"],
        "recompute_metric_ranks": False,
    },
    {
        "name": "real_market",
        "ranked_path": ROOT
        / "p0_lite_outputs"
        / "p1_rolling_window_market_validation_20260719"
        / "configured_ecmade_no_replicate_audit_summary_20260731"
        / "configured_window_method_ranked.csv",
        "out_dir": ROOT
        / "p0_lite_outputs"
        / "p1_rolling_window_market_validation_20260719"
        / "configured_ecmade_no_replicate_audit_summary_20260731",
        "pair_keys": ["universe", "window_id"],
        "recompute_metric_ranks": True,
        "metric_columns": {
            "HV": "HV_mean",
            "IGD": "IGD_mean",
            "PF_Overlap": "PF_Overlap_mean",
            "PF_Drift": "PF_Drift_mean",
        },
    },
    {
        "name": "mokp",
        "ranked_path": ROOT
        / "p0_lite_outputs"
        / "p1_mokp_config_comparison_no_replicate_audit_20260731"
        / "instance_method_metrics_ranked.csv",
        "out_dir": ROOT / "p0_lite_outputs" / "p1_mokp_config_comparison_no_replicate_audit_20260731",
        "pair_keys": ["split", "instance"],
        "recompute_metric_ranks": False,
    },
]


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


def recompute_metric_ranks(frame: pd.DataFrame, pair_keys: list[str], metric_columns: dict[str, str]) -> pd.DataFrame:
    frames = []
    for _, group in frame.groupby(pair_keys, sort=False):
        out = group.copy()
        out["rank_HV"] = out[metric_columns["HV"]].rank(ascending=False, method="average")
        out["rank_IGD"] = out[metric_columns["IGD"]].rank(ascending=True, method="average")
        out["rank_PF_Overlap"] = out[metric_columns["PF_Overlap"]].rank(ascending=False, method="average")
        out["rank_PF_Drift"] = out[metric_columns["PF_Drift"]].rank(ascending=True, method="average")
        frames.append(out)
    return pd.concat(frames, ignore_index=True)


def add_stability_weighted_rank(frame: pd.DataFrame, spec: dict) -> pd.DataFrame:
    out = frame.copy()
    if spec.get("recompute_metric_ranks", False):
        out = recompute_metric_ranks(out, spec["pair_keys"], spec["metric_columns"])
    missing = [col for col in WEIGHTS if col not in out.columns]
    if missing:
        raise RuntimeError(f"{spec['name']} missing rank columns: {missing}")
    out["StabilityWeightedRank"] = sum(out[col] * weight for col, weight in WEIGHTS.items())
    out["StabilityWeightedInstanceRank"] = out.groupby(spec["pair_keys"])["StabilityWeightedRank"].rank(
        ascending=True, method="average"
    )
    return out


def build_overall(ranked: pd.DataFrame, spec: dict) -> pd.DataFrame:
    return (
        ranked.groupby("method")
        .agg(
            paired_units=(spec["pair_keys"][0], "count"),
            mean_StabilityWeightedRank=("StabilityWeightedRank", "mean"),
            median_StabilityWeightedRank=("StabilityWeightedRank", "median"),
            mean_StabilityWeightedInstanceRank=("StabilityWeightedInstanceRank", "mean"),
            first_place_units=("StabilityWeightedInstanceRank", lambda s: int((s == 1).sum())),
        )
        .reset_index()
        .sort_values(["mean_StabilityWeightedRank", "mean_StabilityWeightedInstanceRank", "method"])
    )


def build_statistics(ranked: pd.DataFrame, spec: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    pair_keys = spec["pair_keys"]
    methods = sorted(ranked["method"].unique())
    pivot = ranked.pivot_table(index=pair_keys, columns="method", values="StabilityWeightedRank", aggfunc="mean")
    pivot = pivot[[m for m in methods if m in pivot.columns]].dropna(axis=0, how="any")
    oriented = -pivot
    if oriented.shape[1] >= 3 and oriented.shape[0] >= 2:
        stat, p_value = friedmanchisquare(*[oriented[m].to_numpy(dtype=float) for m in oriented.columns])
    else:
        stat, p_value = math.nan, math.nan
    friedman = pd.DataFrame(
        [
            {
                "dataset": spec["name"],
                "endpoint": "StabilityWeightedRank",
                "direction": "min",
                "paired_units": len(oriented),
                "methods": len(oriented.columns),
                "friedman_chi_square": float(stat) if np.isfinite(stat) else math.nan,
                "friedman_p_value": float(p_value) if np.isfinite(p_value) else math.nan,
            }
        ]
    )
    rows = []
    raw_p = []
    for a, b in itertools.combinations(oriented.columns, 2):
        diff = oriented[a].to_numpy(dtype=float) - oriented[b].to_numpy(dtype=float)
        stat_w, p_w = safe_wilcoxon(diff)
        raw_p.append(p_w)
        rows.append(
            {
                "dataset": spec["name"],
                "endpoint": "StabilityWeightedRank",
                "direction": "min",
                "method_a": a,
                "method_b": b,
                "paired_units": len(diff),
                "median_oriented_difference": float(np.nanmedian(diff)),
                "mean_oriented_difference": float(np.nanmean(diff)),
                "wins_a": int((diff > 1e-12).sum()),
                "ties": int((np.abs(diff) <= 1e-12).sum()),
                "wins_b": int((diff < -1e-12).sum()),
                "wilcoxon_stat": stat_w,
                "p_value": p_w,
                "signed_rank_effect": signed_rank_effect(diff),
            }
        )
    for row, adjusted in zip(rows, holm_adjust(raw_p)):
        row["holm_p_value"] = adjusted
        row["significant_0_05"] = bool(adjusted < 0.05)
    return friedman, pd.DataFrame(rows)


def main() -> None:
    for spec in DATASETS:
        ranked = pd.read_csv(spec["ranked_path"], encoding="utf-8-sig")
        ranked = add_stability_weighted_rank(ranked, spec)
        overall = build_overall(ranked, spec)
        friedman, wilcoxon_df = build_statistics(ranked, spec)
        out_dir = spec["out_dir"]
        ranked.to_csv(out_dir / "stability_weighted_rank_instance_method_ranked.csv", index=False, encoding="utf-8-sig")
        overall.to_csv(out_dir / "stability_weighted_rank_overall_summary.csv", index=False, encoding="utf-8-sig")
        friedman.to_csv(out_dir / "stability_weighted_rank_friedman_test.csv", index=False, encoding="utf-8-sig")
        wilcoxon_df.to_csv(out_dir / "stability_weighted_rank_pairwise_wilcoxon_holm.csv", index=False, encoding="utf-8-sig")
        print(f"DATASET={spec['name']} OUT_DIR={out_dir}")
        print(overall.to_string(index=False))
        focus = wilcoxon_df[wilcoxon_df["method_a"].eq(PRIMARY) | wilcoxon_df["method_b"].eq(PRIMARY)]
        print(focus.to_string(index=False))


if __name__ == "__main__":
    main()
