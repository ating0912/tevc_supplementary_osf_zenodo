from __future__ import annotations

import itertools
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, wilcoxon


ROOT = Path(__file__).resolve().parent
RAW_ROOT = Path(
    os.environ.get(
        "P1_ROLLING_ANALYSIS_RAW",
        ROOT / "p0_lite_outputs" / "p1_rolling_window_market_validation_20260719" / "raw",
    )
)
OUT_DIR = Path(
    os.environ.get(
        "P1_ROLLING_ANALYSIS_OUT",
        ROOT / "p0_lite_outputs" / "p1_rolling_window_market_validation_20260719" / "summary",
    )
)
METHODS = ["NSGAII", "SPEA2", "MOEAD", "GDE3", "A_MPMO", "ECMADE_MOO"]
METRICS = {
    "annual_net_return": "max",
    "sharpe": "max",
    "sortino": "max",
    "max_drawdown": "max",
    "annual_volatility": "min",
    "rebalance_turnover": "min",
    "runtime_sec": "min",
}


def discover_run_summaries(root: Path) -> pd.DataFrame:
    summary_file = root / "rolling_backtest_run_summary.csv"
    if summary_file.exists():
        run_df = pd.read_csv(summary_file, encoding="utf-8-sig")
        if "selected_portfolio_path" not in run_df.columns:
            run_df["selected_portfolio_path"] = [
                str(root / str(row.universe) / str(row.window_id) / str(row.method) / f"run_{int(row.run):03d}" / "selected_portfolio.csv")
                for row in run_df.itertuples(index=False)
            ]
        if "rebalance_turnover" not in run_df.columns:
            run_df = add_rebalance_turnover(run_df)
        return run_df
    rows = []
    for bt_file in root.glob("*/*/*/run_*/backtest_metrics.csv"):
        run_dir = bt_file.parent
        meta_file = run_dir / "window_metadata.csv"
        runtime_file = run_dir / "runtime.csv"
        portfolio_file = run_dir / "selected_portfolio.csv"
        if not meta_file.exists() or not runtime_file.exists():
            continue
        meta = pd.read_csv(meta_file, encoding="utf-8-sig").iloc[0]
        bt = pd.read_csv(bt_file, encoding="utf-8-sig").iloc[0]
        runtime = pd.read_csv(runtime_file, encoding="utf-8-sig").iloc[0]["runtime_sec"]
        rows.append(
            {
                "method": str(meta["method"]),
                "universe": str(meta["universe"]),
                "window_id": str(meta["window_id"]),
                "run": int(run_dir.name.split("_")[-1]),
                "assets": int(meta["assets"]),
                "K": int(meta["K"]),
                "train_days": int(meta["train_days"]),
                "test_days": int(meta["test_days"]),
                **{col: bt[col] for col in bt.index},
                "runtime_sec": runtime,
                "selected_portfolio_path": str(portfolio_file),
            }
        )
    if not rows:
        raise RuntimeError(f"No rolling market backtest runs found under {root}")
    return add_rebalance_turnover(pd.DataFrame(rows))


def read_weights(path: str) -> pd.Series:
    portfolio = pd.read_csv(path, encoding="utf-8-sig")
    weights = portfolio.set_index("ticker")["weight"].astype(float)
    return weights[weights.abs() > 1e-12]


def pair_turnover(previous: pd.Series | None, current: pd.Series) -> float:
    if previous is None:
        return 1.0
    tickers = previous.index.union(current.index)
    diff = current.reindex(tickers, fill_value=0.0) - previous.reindex(tickers, fill_value=0.0)
    return float(0.5 * diff.abs().sum())


def add_rebalance_turnover(run_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, group in run_df.groupby(["universe", "method", "run"], sort=False):
        group = group.sort_values("window_id").copy()
        previous = None
        turnovers = []
        for _, row in group.iterrows():
            current = read_weights(row["selected_portfolio_path"])
            turnovers.append(pair_turnover(previous, current))
            previous = current
        group["initial_turnover"] = group["turnover"]
        group["rebalance_turnover"] = turnovers
        rows.append(group)
    return pd.concat(rows, ignore_index=True)


def instance_method_summary(run_df: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["universe", "window_id", "method", "assets", "K", "train_days", "test_days"]
    agg_cols = list(METRICS.keys()) + ["gross_return", "net_return", "annual_return", "transaction_cost", "initial_turnover"]
    summary = run_df.groupby(group_cols, sort=False)[agg_cols].agg(["mean", "std"]).reset_index()
    summary.columns = ["_".join(col).rstrip("_") for col in summary.columns.to_flat_index()]
    return summary


def add_ranks(summary: pd.DataFrame) -> pd.DataFrame:
    ranked_frames = []
    for _, group in summary.groupby(["universe", "window_id"], sort=False):
        frame = group.copy()
        rank_cols = []
        for metric, direction in METRICS.items():
            source = f"{metric}_mean"
            rank_col = f"rank_{metric}"
            frame[rank_col] = frame[source].rank(ascending=(direction == "min"), method="average")
            rank_cols.append(rank_col)
        frame["RankScore"] = frame[rank_cols].mean(axis=1)
        frame["WindowRank"] = frame["RankScore"].rank(ascending=True, method="average")
        ranked_frames.append(frame)
    return pd.concat(ranked_frames, ignore_index=True)


def overall_summary(ranked: pd.DataFrame) -> pd.DataFrame:
    overall = (
        ranked.groupby("method")
        .agg(
            windows=("window_id", "count"),
            mean_annual_net_return=("annual_net_return_mean", "mean"),
            mean_sharpe=("sharpe_mean", "mean"),
            mean_sortino=("sortino_mean", "mean"),
            mean_max_drawdown=("max_drawdown_mean", "mean"),
            mean_annual_volatility=("annual_volatility_mean", "mean"),
            mean_rebalance_turnover=("rebalance_turnover_mean", "mean"),
            mean_runtime_sec=("runtime_sec_mean", "mean"),
            mean_RankScore=("RankScore", "mean"),
            mean_WindowRank=("WindowRank", "mean"),
            first_place_windows=("WindowRank", lambda s: int((s == 1).sum())),
        )
        .reset_index()
    )
    return overall.sort_values(["mean_RankScore", "mean_WindowRank", "method"])


def oriented(values: pd.Series, direction: str) -> pd.Series:
    return values if direction == "max" else -values


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


def statistics(ranked: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    friedman_rows = []
    pair_rows = []
    for metric, direction in METRICS.items():
        col = f"{metric}_mean"
        pivot = ranked.pivot_table(index=["universe", "window_id"], columns="method", values=col, aggfunc="mean")
        present = [m for m in METHODS if m in pivot.columns]
        pivot = pivot[present].dropna(axis=0, how="any")
        if len(present) >= 3 and not pivot.empty:
            transformed = pivot if direction == "max" else -pivot
            stat, p_value = friedmanchisquare(*[transformed[m].to_numpy() for m in present])
            friedman_rows.append(
                {
                    "metric": metric,
                    "direction": direction,
                    "windows": len(pivot),
                    "methods": len(present),
                    "friedman_chi_square": float(stat),
                    "friedman_p_value": float(p_value),
                }
            )
        for a, b in itertools.combinations(present, 2):
            diff = oriented(pivot[a], direction).to_numpy(dtype=float) - oriented(pivot[b], direction).to_numpy(dtype=float)
            stat_w, p_w = safe_wilcoxon(diff)
            pair_rows.append(
                {
                    "metric": metric,
                    "direction": direction,
                    "method_a": a,
                    "method_b": b,
                    "windows": len(diff),
                    "mean_oriented_difference": float(np.nanmean(diff)),
                    "median_oriented_difference": float(np.nanmedian(diff)),
                    "wilcoxon_stat": stat_w,
                    "p_value": p_w,
                }
            )
    return pd.DataFrame(friedman_rows), pd.DataFrame(pair_rows)


def write_readme(overall: pd.DataFrame, friedman: pd.DataFrame) -> None:
    lines = [
        "# P1 Rolling-Window Market Validation",
        "",
        "- Train/test design: 3-year training window, 6-month test window.",
        "- Portfolio selection: max train Sharpe portfolio from the final Pareto front.",
        "- Out-of-sample metrics: annual net return, Sharpe, Sortino, max drawdown, volatility, turnover, runtime.",
        "",
        "## Overall Ranking",
        "",
        overall.to_markdown(index=False),
        "",
        "## Friedman Tests",
        "",
        friedman.to_markdown(index=False) if not friedman.empty else "(Not enough complete methods/windows.)",
    ]
    (OUT_DIR / "README_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_df = discover_run_summaries(RAW_ROOT)
    summary = instance_method_summary(run_df)
    ranked = add_ranks(summary)
    overall = overall_summary(ranked)
    friedman, pairwise = statistics(ranked)

    run_df.to_csv(OUT_DIR / "rolling_run_metrics.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT_DIR / "window_method_summary.csv", index=False, encoding="utf-8-sig")
    ranked.to_csv(OUT_DIR / "window_method_ranked.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(OUT_DIR / "method_overall_summary.csv", index=False, encoding="utf-8-sig")
    friedman.to_csv(OUT_DIR / "friedman_tests.csv", index=False, encoding="utf-8-sig")
    pairwise.to_csv(OUT_DIR / "pairwise_wilcoxon.csv", index=False, encoding="utf-8-sig")
    write_readme(overall, friedman)
    print(f"Wrote rolling market summary to {OUT_DIR}")
    print(overall.to_string(index=False))


if __name__ == "__main__":
    main()
