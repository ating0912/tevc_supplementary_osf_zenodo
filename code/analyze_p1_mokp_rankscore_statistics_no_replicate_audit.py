from __future__ import annotations

import itertools
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, rankdata, wilcoxon


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "p0_lite_outputs" / "p1_mokp_config_comparison_no_replicate_audit_20260731"
RANKED_PATH = OUT_DIR / "instance_method_metrics_ranked.csv"
PAIR_KEYS = ["split", "instance"]


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


def main() -> None:
    ranked = pd.read_csv(RANKED_PATH, encoding="utf-8-sig")
    methods = sorted(ranked["method"].unique())
    pivot = ranked.pivot_table(index=PAIR_KEYS, columns="method", values="RankScore", aggfunc="mean")
    pivot = pivot[[m for m in methods if m in pivot.columns]].dropna(axis=0, how="any")
    transformed = -pivot
    stat, p_value = friedmanchisquare(*[transformed[m].to_numpy(dtype=float) for m in transformed.columns])
    friedman = pd.DataFrame(
        [
            {
                "metric": "RankScore",
                "direction": "min",
                "instances": len(transformed),
                "methods": len(transformed.columns),
                "friedman_chi_square": float(stat),
                "friedman_p_value": float(p_value),
            }
        ]
    )
    raw_p = []
    rows = []
    for a, b in itertools.combinations(transformed.columns, 2):
        diff = transformed[a].to_numpy(dtype=float) - transformed[b].to_numpy(dtype=float)
        stat_w, p_w = safe_wilcoxon(diff)
        raw_p.append(p_w)
        rows.append(
            {
                "metric": "RankScore",
                "direction": "min",
                "method_a": a,
                "method_b": b,
                "instances": len(diff),
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
    for row, adj in zip(rows, holm_adjust(raw_p)):
        row["holm_p_value"] = adj
        row["significant_0_05"] = bool(adj < 0.05)
    wilcoxon_df = pd.DataFrame(rows)
    friedman.to_csv(OUT_DIR / "rankscore_friedman_test.csv", index=False, encoding="utf-8-sig")
    wilcoxon_df.to_csv(OUT_DIR / "rankscore_pairwise_wilcoxon_holm.csv", index=False, encoding="utf-8-sig")
    print(f"OUT_DIR={OUT_DIR}")
    print(friedman.to_string(index=False))
    print(
        wilcoxon_df[
            wilcoxon_df["method_a"].eq("ExperimentC_NoReplicate_ECMADE_MOO")
            | wilcoxon_df["method_b"].eq("ExperimentC_NoReplicate_ECMADE_MOO")
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
