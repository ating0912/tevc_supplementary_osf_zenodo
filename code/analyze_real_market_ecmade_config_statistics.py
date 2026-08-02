from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, wilcoxon


ROOT = Path(__file__).resolve().parent
SUMMARY_DIR = (
    ROOT
    / "p0_lite_outputs"
    / "p1_rolling_window_market_validation_20260719"
    / "configured_ecmade_comparison_summary"
)
RANKED_PATH = SUMMARY_DIR / "configured_window_method_ranked.csv"

ALPHA = 0.05
PRIMARY_METHOD = "ExperimentC_StabilityAware_ECMADE_MOO"
METRIC_DIRECTIONS = {
    "RankScore": "min",
    "annual_net_return_mean": "max",
    "sharpe_mean": "max",
    "sortino_mean": "max",
    "max_drawdown_mean": "max",
    "annual_volatility_mean": "min",
    "cvar95_loss_mean": "min",
    "rebalance_turnover_mean": "min",
    "average_pf_holdings_mean": "min",
    "PF_Overlap_mean": "max",
    "PF_Drift_mean": "min",
    "Runtime_mean": "min",
}


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


def signed_values(values: pd.Series, direction: str) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric if direction == "max" else -numeric


def safe_friedman(wide: pd.DataFrame) -> tuple[float, float]:
    clean = wide.dropna(axis=0, how="any")
    if clean.shape[0] < 2 or clean.shape[1] < 3:
        return np.nan, np.nan
    arrays = [clean[col].to_numpy(dtype=float) for col in clean.columns]
    if all(np.nanstd(arr) == 0 for arr in arrays):
        return np.nan, np.nan
    stat, p_value = friedmanchisquare(*arrays)
    return float(stat), float(p_value)


def safe_wilcoxon(diff: np.ndarray) -> tuple[float, float]:
    diff = diff[np.isfinite(diff)]
    diff = diff[np.abs(diff) > 1e-12]
    if diff.size == 0:
        return 0.0, 1.0
    stat, p_value = wilcoxon(diff, zero_method="wilcox", alternative="greater")
    return float(stat), float(p_value)


def build_statistics(ranked: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ranked = ranked.copy()
    ranked["paired_unit"] = ranked["universe"].astype(str) + "::" + ranked["window_id"].astype(str)
    methods = sorted(ranked["method"].unique())
    friedman_rows = []
    wilcoxon_rows = []

    for metric, direction in METRIC_DIRECTIONS.items():
        if metric not in ranked.columns:
            continue
        frame = ranked[["paired_unit", "method", metric]].dropna()
        wide_raw = frame.pivot(index="paired_unit", columns="method", values=metric)
        wide = wide_raw.apply(lambda col: signed_values(col, direction), axis=0)
        wide = wide[[m for m in methods if m in wide.columns]].dropna(axis=0, how="any")
        stat_f, p_f = safe_friedman(wide)
        friedman_rows.append(
            {
                "metric": metric,
                "direction": direction,
                "paired_unit": "universe_window",
                "n_paired_units": int(wide.shape[0]),
                "methods": "|".join(wide.columns),
                "friedman_chi_square": stat_f,
                "p_value": p_f,
                "alpha": ALPHA,
                "significant": bool(np.isfinite(p_f) and p_f < ALPHA),
            }
        )

        if PRIMARY_METHOD not in wide.columns:
            continue
        p_rows = []
        x = wide[PRIMARY_METHOD].to_numpy(dtype=float)
        for baseline in wide.columns:
            if baseline == PRIMARY_METHOD:
                continue
            y = wide[baseline].to_numpy(dtype=float)
            diff = x - y
            stat_w, p_w = safe_wilcoxon(diff)
            p_rows.append(
                {
                    "metric": metric,
                    "direction": direction,
                    "paired_unit": "universe_window",
                    "n_paired_units": int(wide.shape[0]),
                    "primary": PRIMARY_METHOD,
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
        adjusted = holm_adjust([row["raw_p_value"] for row in p_rows])
        for row, p_adj in zip(p_rows, adjusted):
            row["holm_p_value"] = p_adj
            row["significant_after_holm"] = bool(p_adj < ALPHA)
            wilcoxon_rows.append(row)

    return pd.DataFrame(friedman_rows), pd.DataFrame(wilcoxon_rows)


def main() -> None:
    ranked = pd.read_csv(RANKED_PATH, encoding="utf-8-sig")
    friedman, wilcoxon_df = build_statistics(ranked)
    friedman.to_csv(SUMMARY_DIR / "configured_friedman_tests.csv", index=False, encoding="utf-8-sig")
    wilcoxon_df.to_csv(SUMMARY_DIR / "configured_pairwise_wilcoxon_holm.csv", index=False, encoding="utf-8-sig")
    print(f"OUT_DIR={SUMMARY_DIR}")
    print(friedman.to_string(index=False))
    print(wilcoxon_df[wilcoxon_df["metric"].eq("RankScore")].to_string(index=False))


if __name__ == "__main__":
    main()
