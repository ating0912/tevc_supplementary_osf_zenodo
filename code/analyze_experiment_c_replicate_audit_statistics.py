from __future__ import annotations

import itertools
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, rankdata, wilcoxon


ROOT = Path(__file__).resolve().parent
SUMMARY_DIR = ROOT / "p0_lite_outputs" / "experiment_c_replicate_audit_final_test_20260730"
RANKED_PATH = SUMMARY_DIR / "replicate_audit_instance_method_ranked.csv"
PAIR_KEYS = ["split", "instance"]
METRICS = {
    "RankScore": "min",
    "HV": "max",
    "IGD": "min",
    "PF_Overlap": "max",
    "PF_Drift": "min",
    "Diversity": "max",
    "Runtime": "min",
}


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


def oriented(values: pd.Series, direction: str) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric if direction == "max" else -numeric


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
    methods = sorted(frame["method"].unique())
    friedman_rows = []
    wilcoxon_rows = []
    for metric, direction in METRICS.items():
        if metric not in frame.columns:
            continue
        pivot = frame.pivot_table(index=PAIR_KEYS, columns="method", values=metric, aggfunc="mean")
        pivot = pivot[[m for m in methods if m in pivot.columns]].dropna(axis=0, how="any")
        if pivot.empty:
            continue
        transformed = pivot.apply(lambda col: oriented(col, direction), axis=0)
        if transformed.shape[1] >= 3 and transformed.shape[0] >= 2:
            stat, p_value = friedmanchisquare(*[transformed[m].to_numpy() for m in transformed.columns])
        else:
            stat, p_value = math.nan, math.nan
        friedman_rows.append(
            {
                "metric": metric,
                "direction": direction,
                "instances": len(transformed),
                "methods": len(transformed.columns),
                "friedman_chi_square": float(stat) if np.isfinite(stat) else math.nan,
                "friedman_p_value": float(p_value) if np.isfinite(p_value) else math.nan,
            }
        )
        raw_p = []
        temp_rows = []
        for a, b in itertools.combinations(transformed.columns, 2):
            diff = transformed[a].to_numpy(dtype=float) - transformed[b].to_numpy(dtype=float)
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
                    "wins_a": int((diff > 1e-12).sum()),
                    "ties": int((np.abs(diff) <= 1e-12).sum()),
                    "wins_b": int((diff < -1e-12).sum()),
                    "wilcoxon_stat": stat_w,
                    "p_value": p_w,
                    "signed_rank_effect": signed_rank_effect(diff),
                }
            )
        for row, adj in zip(temp_rows, holm_adjust(raw_p)):
            row["holm_p_value"] = adj
            row["significant_0_05"] = bool(adj < 0.05)
            wilcoxon_rows.append(row)
    return pd.DataFrame(friedman_rows), pd.DataFrame(wilcoxon_rows)


def main() -> None:
    ranked = pd.read_csv(RANKED_PATH, encoding="utf-8-sig")
    friedman, wilcoxon_df = build_statistics(ranked)
    friedman.to_csv(SUMMARY_DIR / "replicate_audit_friedman_tests.csv", index=False, encoding="utf-8-sig")
    wilcoxon_df.to_csv(SUMMARY_DIR / "replicate_audit_pairwise_wilcoxon_holm.csv", index=False, encoding="utf-8-sig")
    print(f"OUT_DIR={SUMMARY_DIR}")
    print(friedman.to_string(index=False))
    print(
        wilcoxon_df[
            wilcoxon_df["metric"].eq("RankScore")
            & wilcoxon_df["method_a"].str.contains("NoReplicate|ReplicateIncluded", regex=True)
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
