from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, rankdata, wilcoxon

import analyze_real_market_ecmade_config_comparison as base


ROOT = Path(__file__).resolve().parent
BASE_DIR = ROOT / "p0_lite_outputs" / "p1_rolling_window_market_validation_20260719"
OUT_DIR = BASE_DIR / "configured_ecmade_no_replicate_audit_summary_20260731"
RAW_ROOTS = [
    BASE_DIR / "raw_configured_ecmade",
    BASE_DIR / "raw_configured_ecmade_no_replicate_20260731",
]
ASSIGNMENT_PATHS = [
    BASE_DIR / "config_protocol_assignments" / "real_market_ecmade_configuration_assignment.csv",
    ROOT
    / "p0_lite_outputs"
    / "experiment_c_no_replicate_external_assignments_20260731"
    / "real_market_no_replicate_assignment.csv",
]
METHODS = [
    "HandCrafted_ECMADE_MOO",
    "BayesianConfig_ECMADE_MOO",
    "MetaDesigned_ECMADE_MOO",
    "ExperimentC_StabilityAware_ECMADE_MOO",
    "ExperimentC_NoReplicate_ECMADE_MOO",
]
PRIMARY_METHOD = "ExperimentC_NoReplicate_ECMADE_MOO"
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


def discover_runs_multi() -> tuple[pd.DataFrame, dict, dict]:
    rows = []
    pfs = {}
    fronts_by_window = {}
    for raw_root in RAW_ROOTS:
        for pf_file in raw_root.glob("*/*/*/run_*/pf_obj.csv"):
            run_path = pf_file.parent
            method = run_path.parent.name
            window_id = run_path.parent.parent.name
            universe = run_path.parent.parent.parent.name
            if method not in METHODS:
                continue
            run = int(run_path.name.split("_")[-1])
            meta = pd.read_csv(run_path / "window_metadata.csv", encoding="utf-8-sig").iloc[0]
            bt = pd.read_csv(run_path / "backtest_metrics.csv", encoding="utf-8-sig").iloc[0]
            returns = base.daily_returns(run_path / "test_daily_returns.csv")
            selected = base.read_selected_weights(run_path / "selected_portfolio.csv")
            avg_hold, med_hold = base.pf_holdings(run_path / "pf_dec.csv")
            pf = base.read_matrix(pf_file)
            if len(pf) == 0:
                continue
            rec = {
                "universe": universe,
                "window_id": window_id,
                "method": method,
                "run": run,
                "assets": int(meta["assets"]),
                "K": int(meta["K"]),
                "train_days": int(meta["train_days"]),
                "test_days": int(meta["test_days"]),
                "gross_return": float(bt["gross_return"]),
                "net_return": float(bt["net_return"]),
                "annual_return": float(bt["annual_return"]),
                "annual_net_return": float(bt["annual_net_return"]),
                "annual_volatility": float(bt["annual_volatility"]),
                "sharpe": float(bt["sharpe"]),
                "sortino": float(bt["sortino"]),
                "max_drawdown": float(bt["max_drawdown"]),
                "turnover": float(bt["turnover"]),
                "transaction_cost": float(bt["transaction_cost"]),
                "Runtime": base.read_runtime(run_path / "runtime.csv"),
                "cvar95_loss": base.cvar95_loss(returns),
                "mdd_from_daily_returns": base.max_drawdown_from_returns(returns),
                "selected_holdings": int(len(selected)),
                "average_pf_holdings": avg_hold,
                "median_pf_holdings": med_hold,
                "PF_Size": len(pf),
                "run_dir": str(run_path),
            }
            key = (universe, window_id, method, run)
            window_key = (universe, window_id)
            pfs[key] = pf
            fronts_by_window.setdefault(window_key, []).append(pf)
            rows.append(rec)
    run_df = pd.DataFrame(rows)
    if run_df.empty:
        raise RuntimeError("No configured ECMADE real-market runs found for no-replicate audit")
    return base.add_rebalance_turnover(run_df), pfs, fronts_by_window


def holm_adjust(p_values: list[float]) -> list[float]:
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    adjusted = [math.nan] * len(p_values)
    running = 0.0
    m = len(p_values)
    for rank, idx in enumerate(order):
        value = min(1.0, (m - rank) * p_values[idx])
        running = max(running, value)
        adjusted[idx] = running
    return adjusted


def orient(values: pd.Series, direction: str) -> pd.Series:
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


def build_statistics(ranked: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = ranked.copy()
    frame["paired_unit"] = frame["universe"].astype(str) + "::" + frame["window_id"].astype(str)
    friedman_rows = []
    wilcoxon_rows = []
    for metric, direction in METRIC_DIRECTIONS.items():
        if metric not in frame.columns:
            continue
        wide_raw = frame.pivot(index="paired_unit", columns="method", values=metric)
        columns = [m for m in METHODS if m in wide_raw.columns]
        wide = wide_raw[columns].dropna(axis=0, how="any")
        if wide.empty:
            continue
        oriented = wide.apply(lambda col: orient(col, direction), axis=0)
        if oriented.shape[1] >= 3 and oriented.shape[0] >= 2:
            stat, p_value = friedmanchisquare(*[oriented[c].to_numpy(dtype=float) for c in oriented.columns])
        else:
            stat, p_value = math.nan, math.nan
        friedman_rows.append(
            {
                "metric": metric,
                "direction": direction,
                "paired_unit": "universe_window",
                "n_paired_units": int(oriented.shape[0]),
                "methods": "|".join(oriented.columns),
                "friedman_chi_square": float(stat) if np.isfinite(stat) else math.nan,
                "p_value": float(p_value) if np.isfinite(p_value) else math.nan,
            }
        )
        if PRIMARY_METHOD not in oriented.columns:
            continue
        primary = oriented[PRIMARY_METHOD].to_numpy(dtype=float)
        temp_rows = []
        raw_p = []
        for baseline in oriented.columns:
            if baseline == PRIMARY_METHOD:
                continue
            diff = primary - oriented[baseline].to_numpy(dtype=float)
            stat_w, p_w = safe_wilcoxon(diff)
            raw_p.append(p_w)
            temp_rows.append(
                {
                    "metric": metric,
                    "direction": direction,
                    "primary": PRIMARY_METHOD,
                    "baseline": baseline,
                    "paired_unit": "universe_window",
                    "n_paired_units": int(len(diff)),
                    "median_signed_improvement": float(np.nanmedian(diff)),
                    "mean_signed_improvement": float(np.nanmean(diff)),
                    "wins": int((diff > 1e-12).sum()),
                    "ties": int((np.abs(diff) <= 1e-12).sum()),
                    "losses": int((diff < -1e-12).sum()),
                    "signed_rank_effect": signed_rank_effect(diff),
                    "wilcoxon_stat": stat_w,
                    "p_value": p_w,
                }
            )
        for row, adjusted in zip(temp_rows, holm_adjust(raw_p)):
            row["holm_p_value"] = adjusted
            row["significant_0_05"] = bool(adjusted < 0.05)
            wilcoxon_rows.append(row)
    return pd.DataFrame(friedman_rows), pd.DataFrame(wilcoxon_rows)


def theta_usage() -> pd.DataFrame:
    frames = []
    for path in ASSIGNMENT_PATHS:
        if path.exists():
            frames.append(pd.read_csv(path, encoding="utf-8-sig"))
    if not frames:
        return pd.DataFrame()
    assignments = pd.concat(frames, ignore_index=True)
    return assignments.groupby(["method", "theta_id"]).size().reset_index(name="windows")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base.METHODS = METHODS
    run_df, pfs, fronts_by_window = discover_runs_multi()
    run_metrics = base.add_pf_metrics(run_df, pfs, fronts_by_window)
    window_summary = base.summarize_windows(run_metrics)
    ranked = base.add_ranks(window_summary)
    overall = base.overall_summary(ranked)
    run_sens, cost_overall = base.transaction_cost_sensitivity(run_metrics)
    completeness = (
        run_metrics.assign(universe_window=run_metrics["universe"].astype(str) + "::" + run_metrics["window_id"].astype(str))
        .groupby("method")
        .agg(universe_windows=("universe_window", "nunique"), runs=("run", "count"))
        .reset_index()
    )
    friedman, wilcoxon_df = build_statistics(ranked)
    usage = theta_usage()

    run_metrics.to_csv(OUT_DIR / "configured_run_metrics_with_pf_stability.csv", index=False, encoding="utf-8-sig")
    window_summary.to_csv(OUT_DIR / "configured_window_method_summary.csv", index=False, encoding="utf-8-sig")
    ranked.to_csv(OUT_DIR / "configured_window_method_ranked.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(OUT_DIR / "configured_overall_summary.csv", index=False, encoding="utf-8-sig")
    run_sens.to_csv(OUT_DIR / "configured_transaction_cost_run_sensitivity.csv", index=False, encoding="utf-8-sig")
    cost_overall.to_csv(OUT_DIR / "configured_transaction_cost_overall.csv", index=False, encoding="utf-8-sig")
    completeness.to_csv(OUT_DIR / "configured_run_completeness.csv", index=False, encoding="utf-8-sig")
    usage.to_csv(OUT_DIR / "configured_theta_usage_by_method.csv", index=False, encoding="utf-8-sig")
    friedman.to_csv(OUT_DIR / "configured_friedman_tests.csv", index=False, encoding="utf-8-sig")
    wilcoxon_df.to_csv(OUT_DIR / "configured_pairwise_wilcoxon_holm.csv", index=False, encoding="utf-8-sig")

    print(f"OUT_DIR={OUT_DIR}")
    print(completeness.to_string(index=False))
    print(overall[["method", "windows", "mean_RankScore", "overall_RankScore", "first_place_windows"]].to_string(index=False))


if __name__ == "__main__":
    main()
