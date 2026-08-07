"""Build unified TEVC P0 statistical test tables.

The script uses completed instance-level metric tables and writes:
  - unified_friedman_tests.csv
  - unified_average_ranks.csv
  - unified_nemenyi_pairs.csv
  - unified_pairwise_wilcoxon.csv

All pairwise tests are paired by split/instance/K. Metrics are converted to a
"higher is better" convention before testing where needed, so positive effect
sizes indicate method_a outperforms method_b.
"""

from __future__ import annotations

import itertools
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, wilcoxon, friedmanchisquare


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "p0_lite_outputs" / "tevc_p0_statistical_tests_20260718"

METRICS = {
    "HV": "max",
    "IGD": "min",
    "PF_Overlap": "max",
    "PF_Drift": "min",
    "Diversity": "max",
    "Runtime": "min",
}

SCOPES = [
    (
        "Experiment_A_Synthetic",
        ROOT
        / "p0_lite_outputs"
        / "synthetic_constrained_portfolio"
        / "knowledge_base_parameter_report"
        / "instance_method_metrics.csv",
    ),
    (
        "Experiment_A_ORLibrary",
        ROOT
        / "p0_lite_outputs"
        / "orlib_constrained_portfolio"
        / "knowledge_base_parameter_report"
        / "instance_method_metrics.csv",
    ),
    (
        "Experiment_B_ConfigComparison",
        ROOT
        / "p0_lite_outputs"
        / "experiment_b_configuration_summary_20260713"
        / "combined_instance_method_metrics_ranked.csv",
    ),
    (
        "Experiment_C_StabilityComparison",
        ROOT
        / "p0_lite_outputs"
        / "experiment_c_stability_comparison_20260717"
        / "combined_instance_method_metrics_ranked.csv",
    ),
    (
        "TEVC_PDF_Direct_Ablation_All",
        ROOT
        / "p0_lite_outputs"
        / "tevc_pdf_direct_ablation_full_20260717"
        / "knowledge_base_parameter_report"
        / "instance_method_metrics.csv",
    ),
]

DIRECT_ABLATION_ROOT = ROOT / "p0_lite_outputs" / "tevc_pdf_direct_ablation_full_20260717"
PAIR_KEYS = ["split", "instance", "K"]

# Demsar/Nemenyi critical q_alpha values for alpha=0.05, infinite df.
Q_ALPHA_05 = {
    2: 1.960,
    3: 2.343,
    4: 2.569,
    5: 2.728,
    6: 2.850,
    7: 2.949,
    8: 3.031,
    9: 3.102,
    10: 3.164,
}


def read_metrics(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, encoding="utf-8-sig")
    missing = [col for col in PAIR_KEYS + ["method"] + list(METRICS) if col not in frame.columns]
    if missing:
        raise RuntimeError(f"{path} missing columns: {missing}")
    for col in METRICS:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame[PAIR_KEYS + ["method"] + list(METRICS)].copy()


def oriented(values: pd.Series, direction: str) -> pd.Series:
    return values if direction == "max" else -values


def average_ranks(pivot: pd.DataFrame, direction: str) -> pd.Series:
    rank_rows = []
    for _, row in pivot.iterrows():
        vals = row.to_numpy(dtype=float)
        if direction == "max":
            ranks = rankdata(-vals, method="average")
        else:
            ranks = rankdata(vals, method="average")
        rank_rows.append(ranks)
    ranks_df = pd.DataFrame(rank_rows, columns=pivot.columns, index=pivot.index)
    return ranks_df.mean(axis=0)


def holm_adjust(p_values: list[float]) -> list[float]:
    n = len(p_values)
    order = sorted(range(n), key=lambda i: p_values[i])
    adjusted = [math.nan] * n
    running_max = 0.0
    for rank, idx in enumerate(order):
        raw = p_values[idx]
        adj = min((n - rank) * raw, 1.0)
        running_max = max(running_max, adj)
        adjusted[idx] = running_max
    return adjusted


def signed_rank_effect(diff: np.ndarray) -> float:
    diff = diff[np.isfinite(diff)]
    nonzero = diff[np.abs(diff) > 1e-12]
    if len(nonzero) == 0:
        return 0.0
    ranks = rankdata(np.abs(nonzero), method="average")
    w_plus = float(ranks[nonzero > 0].sum())
    w_minus = float(ranks[nonzero < 0].sum())
    denom = len(nonzero) * (len(nonzero) + 1) / 2.0
    return (w_plus - w_minus) / denom


def safe_wilcoxon(diff: np.ndarray) -> tuple[float, float]:
    diff = diff[np.isfinite(diff)]
    nonzero = diff[np.abs(diff) > 1e-12]
    if len(nonzero) == 0:
        return 0.0, 1.0
    try:
        stat, p_value = wilcoxon(nonzero, zero_method="wilcox", alternative="two-sided")
        return float(stat), float(p_value)
    except ValueError:
        return math.nan, 1.0


def nemenyi_cd(method_count: int, instance_count: int) -> float:
    q_alpha = Q_ALPHA_05.get(method_count)
    if q_alpha is None:
        q_alpha = Q_ALPHA_05[max(Q_ALPHA_05)]
    return q_alpha * math.sqrt(method_count * (method_count + 1) / (6.0 * instance_count))


def add_direct_ablation_family_scopes(scopes: list[tuple[str, Path]]) -> list[tuple[str, pd.DataFrame]]:
    loaded = [(name, read_metrics(path)) for name, path in scopes]
    candidates_path = DIRECT_ABLATION_ROOT / "kb_theta_candidates.csv"
    if not candidates_path.exists():
        return loaded
    direct = read_metrics(
        DIRECT_ABLATION_ROOT / "knowledge_base_parameter_report" / "instance_method_metrics.csv"
    )
    candidates = pd.read_csv(candidates_path, encoding="utf-8-sig")[["method", "ablation_family"]]
    direct = direct.merge(candidates, on="method", how="left")
    for family, group in direct.groupby("ablation_family", sort=True):
        if pd.isna(family):
            continue
        loaded.append((f"TEVC_PDF_Direct_Ablation_{family}", group.drop(columns=["ablation_family"])))
    return loaded


def build_scope_tables(scope: str, frame: pd.DataFrame) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    friedman_rows: list[dict] = []
    rank_rows: list[dict] = []
    nemenyi_rows: list[dict] = []
    wilcoxon_rows: list[dict] = []

    for metric, direction in METRICS.items():
        pivot = frame.pivot_table(index=PAIR_KEYS, columns="method", values=metric, aggfunc="mean")
        pivot = pivot.dropna(axis=0, how="any")
        methods = list(pivot.columns)
        n_instances = int(len(pivot))
        k_methods = int(len(methods))
        if n_instances == 0 or k_methods < 2:
            continue

        transformed = pivot.copy()
        if direction == "min":
            transformed = -transformed

        if k_methods >= 3:
            stat, p_value = friedmanchisquare(*[transformed[m].to_numpy() for m in methods])
        else:
            stat, p_value = math.nan, math.nan

        avg_ranks = average_ranks(pivot, direction)
        cd = nemenyi_cd(k_methods, n_instances)
        friedman_rows.append(
            {
                "scope": scope,
                "metric": metric,
                "direction": direction,
                "instances": n_instances,
                "methods": k_methods,
                "friedman_chi_square": float(stat) if not math.isnan(stat) else math.nan,
                "friedman_p_value": float(p_value) if not math.isnan(p_value) else math.nan,
                "nemenyi_cd_alpha_0_05": cd,
            }
        )
        for method, avg_rank in avg_ranks.items():
            rank_rows.append(
                {
                    "scope": scope,
                    "metric": metric,
                    "direction": direction,
                    "method": method,
                    "average_rank": float(avg_rank),
                    "mean_metric": float(pivot[method].mean()),
                }
            )

        pair_p_values = []
        pair_indices = []
        for method_a, method_b in itertools.combinations(methods, 2):
            values_a = oriented(pivot[method_a], direction).to_numpy(dtype=float)
            values_b = oriented(pivot[method_b], direction).to_numpy(dtype=float)
            diff = values_a - values_b
            stat_w, p_w = safe_wilcoxon(diff)
            pair_indices.append(len(wilcoxon_rows))
            pair_p_values.append(p_w)
            wins = int((diff > 1e-12).sum())
            losses = int((diff < -1e-12).sum())
            ties = int((np.abs(diff) <= 1e-12).sum())
            wilcoxon_rows.append(
                {
                    "scope": scope,
                    "metric": metric,
                    "direction": direction,
                    "method_a": method_a,
                    "method_b": method_b,
                    "instances": n_instances,
                    "wins_a": wins,
                    "ties": ties,
                    "losses_a": losses,
                    "wilcoxon_statistic": stat_w,
                    "wilcoxon_p_value": p_w,
                    "holm_p_value": math.nan,
                    "rank_biserial_effect_a_minus_b": signed_rank_effect(diff),
                    "mean_oriented_diff_a_minus_b": float(np.nanmean(diff)),
                }
            )

            rank_diff = abs(float(avg_ranks[method_a] - avg_ranks[method_b]))
            better = method_a if avg_ranks[method_a] < avg_ranks[method_b] else method_b
            nemenyi_rows.append(
                {
                    "scope": scope,
                    "metric": metric,
                    "direction": direction,
                    "method_a": method_a,
                    "method_b": method_b,
                    "instances": n_instances,
                    "average_rank_a": float(avg_ranks[method_a]),
                    "average_rank_b": float(avg_ranks[method_b]),
                    "absolute_rank_difference": rank_diff,
                    "critical_difference_alpha_0_05": cd,
                    "significant_by_cd": bool(rank_diff > cd),
                    "better_average_rank_method": better,
                }
            )

        adjusted = holm_adjust(pair_p_values)
        for row_idx, adj_p in zip(pair_indices, adjusted):
            wilcoxon_rows[row_idx]["holm_p_value"] = adj_p

    return friedman_rows, rank_rows, nemenyi_rows, wilcoxon_rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scopes = add_direct_ablation_family_scopes(SCOPES)

    all_friedman: list[dict] = []
    all_ranks: list[dict] = []
    all_nemenyi: list[dict] = []
    all_wilcoxon: list[dict] = []
    for scope, frame in scopes:
        friedman, ranks, nemenyi, pairwise = build_scope_tables(scope, frame)
        all_friedman.extend(friedman)
        all_ranks.extend(ranks)
        all_nemenyi.extend(nemenyi)
        all_wilcoxon.extend(pairwise)

    pd.DataFrame(all_friedman).to_csv(
        OUT_DIR / "unified_friedman_tests.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(all_ranks).to_csv(
        OUT_DIR / "unified_average_ranks.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(all_nemenyi).to_csv(
        OUT_DIR / "unified_nemenyi_pairs.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(all_wilcoxon).to_csv(
        OUT_DIR / "unified_pairwise_wilcoxon.csv", index=False, encoding="utf-8-sig"
    )
    readme = "\n".join(
        [
            "# TEVC P0 Unified Statistical Tests",
            "",
            "All tests use paired instance-level metrics keyed by split, instance, and K.",
            "For IGD, PF_Drift, and Runtime, values are sign-flipped before pairwise testing so positive effect sizes mean method_a is better.",
            "Nemenyi critical differences use alpha=0.05 infinite-df critical values.",
            "",
            f"Scopes: {', '.join(name for name, _ in scopes)}",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")
    print(f"OUT_DIR={OUT_DIR}")
    print(f"friedman_rows={len(all_friedman)}")
    print(f"average_rank_rows={len(all_ranks)}")
    print(f"nemenyi_pair_rows={len(all_nemenyi)}")
    print(f"wilcoxon_pair_rows={len(all_wilcoxon)}")


if __name__ == "__main__":
    main()
