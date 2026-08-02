from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

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
BASE_DIR = ROOT / "p0_lite_outputs" / "p1_rolling_window_market_validation_20260719"
RAW_ROOT = BASE_DIR / "raw_configured_ecmade"
ASSIGNMENT_PATH = BASE_DIR / "config_protocol_assignments" / "real_market_ecmade_configuration_assignment.csv"
OUT_DIR = BASE_DIR / "configured_ecmade_comparison_summary"

METHODS = [
    "HandCrafted_ECMADE_MOO",
    "BayesianConfig_ECMADE_MOO",
    "MetaDesigned_ECMADE_MOO",
    "ExperimentC_StabilityAware_ECMADE_MOO",
]
COST_SCENARIOS = {"10bps": 0.001, "20bps": 0.002, "50bps": 0.005}
METRIC_SPECS = [
    ("annual_net_return", "max"),
    ("sharpe", "max"),
    ("sortino", "max"),
    ("max_drawdown", "max"),
    ("annual_volatility", "min"),
    ("cvar95_loss", "min"),
    ("rebalance_turnover", "min"),
    ("average_pf_holdings", "min"),
    ("PF_Overlap", "max"),
    ("PF_Drift", "min"),
    ("Runtime", "min"),
]


def run_dir(row: pd.Series, raw_root: Path) -> Path:
    return raw_root / str(row["universe"]) / str(row["window_id"]) / str(row["method"]) / f"run_{int(row['run']):03d}"


def daily_returns(path: Path) -> pd.Series:
    if not path.exists():
        return pd.Series(dtype=float)
    return pd.read_csv(path, header=None).iloc[:, 0].astype(float).dropna()


def cvar95_loss(returns: pd.Series) -> float:
    if returns.empty:
        return np.nan
    threshold = returns.quantile(0.05)
    tail = returns[returns <= threshold]
    return float(-tail.mean()) if not tail.empty else float(-returns.min())


def max_drawdown_from_returns(returns: pd.Series) -> float:
    if returns.empty:
        return np.nan
    wealth = (1.0 + returns).cumprod()
    return float((wealth / wealth.cummax() - 1.0).min())


def read_selected_weights(path: Path) -> pd.Series:
    if not path.exists():
        return pd.Series(dtype=float)
    portfolio = pd.read_csv(path, encoding="utf-8-sig")
    weights = portfolio.set_index("ticker")["weight"].astype(float)
    return weights[weights.abs() > 1e-12]


def pair_turnover(previous: pd.Series | None, current: pd.Series) -> float:
    if previous is None:
        return 1.0
    tickers = previous.index.union(current.index)
    diff = current.reindex(tickers, fill_value=0.0) - previous.reindex(tickers, fill_value=0.0)
    return float(0.5 * diff.abs().sum())


def annualize(total_return: pd.Series, days: pd.Series) -> pd.Series:
    return np.power(1.0 + total_return, 252.0 / days) - 1.0


def pf_holdings(path: Path) -> tuple[float, float]:
    try:
        pf_dec = np.loadtxt(path, delimiter=",")
    except Exception:
        return np.nan, np.nan
    if pf_dec.ndim == 1:
        pf_dec = pf_dec.reshape(1, -1)
    if pf_dec.size == 0:
        return np.nan, np.nan
    counts = (pf_dec > 1e-8).sum(axis=1)
    return float(np.nanmean(counts)), float(np.nanmedian(counts))


def discover_runs(raw_root: Path) -> tuple[pd.DataFrame, dict, dict]:
    rows = []
    pfs = {}
    fronts_by_window = {}
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
        returns = daily_returns(run_path / "test_daily_returns.csv")
        selected = read_selected_weights(run_path / "selected_portfolio.csv")
        avg_hold, med_hold = pf_holdings(run_path / "pf_dec.csv")
        pf = read_matrix(pf_file)
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
            "Runtime": read_runtime(run_path / "runtime.csv"),
            "cvar95_loss": cvar95_loss(returns),
            "mdd_from_daily_returns": max_drawdown_from_returns(returns),
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
        raise RuntimeError(f"No configured ECMADE runs found under {raw_root}")
    return add_rebalance_turnover(run_df), pfs, fronts_by_window


def add_rebalance_turnover(run_df: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for _, group in run_df.groupby(["universe", "method", "run"], sort=False):
        group = group.sort_values("window_id").copy()
        previous = None
        turnovers = []
        for _, row in group.iterrows():
            current = read_selected_weights(Path(row["run_dir"]) / "selected_portfolio.csv")
            turnovers.append(pair_turnover(previous, current))
            previous = current
        group["initial_turnover"] = group["turnover"]
        group["rebalance_turnover"] = turnovers
        frames.append(group)
    return pd.concat(frames, ignore_index=True)


def add_pf_metrics(run_df: pd.DataFrame, pfs: dict, fronts_by_window: dict) -> pd.DataFrame:
    ref_info = {}
    for window_key, fronts in fronts_by_window.items():
        union = np.vstack(fronts)
        ideal = union.min(axis=0)
        nadir = union.max(axis=0)
        ref = thin(nondominated(normalize(union, ideal, nadir)))
        ref_info[window_key] = (ideal, nadir, ref)

    metric_rows = []
    norm_fronts = {}
    for rec in run_df.to_dict("records"):
        key = (rec["universe"], rec["window_id"], rec["method"], int(rec["run"]))
        ideal, nadir, ref = ref_info[(rec["universe"], rec["window_id"])]
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

    drift_rows = []
    for keys, base in run_metrics.groupby(["universe", "window_id", "method"], sort=False):
        universe, window_id, method = keys
        fronts = [norm_fronts[(universe, window_id, method, int(run))] for run in base["run"]]
        centroids = np.vstack([centroid(front) for front in fronts if len(front)])
        mean_c = np.nanmean(centroids, axis=0)
        drifts = [float(np.sqrt(((centroid(front) - mean_c) ** 2).sum())) for front in fronts if len(front)]
        drift_rows.append(
            {
                "universe": universe,
                "window_id": window_id,
                "method": method,
                "PF_Drift": float(np.nanmean(drifts)),
            }
        )
    return run_metrics.merge(pd.DataFrame(drift_rows), on=["universe", "window_id", "method"], how="left")


def summarize_windows(run_metrics: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["universe", "window_id", "method", "assets", "K", "train_days", "test_days"]
    agg_cols = [
        "annual_net_return",
        "annual_volatility",
        "sharpe",
        "sortino",
        "max_drawdown",
        "cvar95_loss",
        "rebalance_turnover",
        "selected_holdings",
        "average_pf_holdings",
        "PF_Size",
        "HV",
        "IGD",
        "PF_Overlap",
        "PF_Drift",
        "Diversity",
        "Runtime",
    ]
    out = run_metrics.groupby(group_cols, sort=False)[agg_cols].agg(["mean", "std"]).reset_index()
    out.columns = ["_".join(col).rstrip("_") for col in out.columns.to_flat_index()]
    out["runs"] = run_metrics.groupby(group_cols, sort=False)["run"].nunique().to_numpy()
    return out


def add_ranks(window_summary: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for _, group in window_summary.groupby(["universe", "window_id"], sort=False):
        frame = group.copy()
        rank_cols = []
        for metric, direction in METRIC_SPECS:
            source = f"{metric}_mean"
            if source not in frame.columns:
                continue
            rank_col = f"rank_{metric}"
            frame[rank_col] = frame[source].rank(ascending=(direction == "min"), method="average")
            rank_cols.append(rank_col)
        frame["RankScore"] = frame[rank_cols].mean(axis=1)
        frame["WindowRank"] = frame["RankScore"].rank(ascending=True, method="average")
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def overall_summary(ranked: pd.DataFrame) -> pd.DataFrame:
    overall = (
        ranked.groupby("method", sort=False)
        .agg(
            windows=("window_id", "count"),
            mean_annual_net_return=("annual_net_return_mean", "mean"),
            mean_annual_volatility=("annual_volatility_mean", "mean"),
            mean_sharpe=("sharpe_mean", "mean"),
            mean_sortino=("sortino_mean", "mean"),
            mean_max_drawdown=("max_drawdown_mean", "mean"),
            mean_cvar95_loss=("cvar95_loss_mean", "mean"),
            mean_rebalance_turnover=("rebalance_turnover_mean", "mean"),
            mean_selected_holdings=("selected_holdings_mean", "mean"),
            mean_average_pf_holdings=("average_pf_holdings_mean", "mean"),
            mean_PF_Size=("PF_Size_mean", "mean"),
            mean_HV=("HV_mean", "mean"),
            mean_IGD=("IGD_mean", "mean"),
            mean_PF_Overlap=("PF_Overlap_mean", "mean"),
            mean_PF_Drift=("PF_Drift_mean", "mean"),
            mean_Diversity=("Diversity_mean", "mean"),
            mean_Runtime=("Runtime_mean", "mean"),
            mean_RankScore=("RankScore", "mean"),
            mean_WindowRank=("WindowRank", "mean"),
            first_place_windows=("WindowRank", lambda s: int((s == 1).sum())),
        )
        .reset_index()
    )
    for metric, direction in METRIC_SPECS:
        col = f"mean_{metric}"
        if col in overall.columns:
            overall[f"overall_rank_{metric}"] = overall[col].rank(ascending=(direction == "min"), method="average")
    rank_cols = [c for c in overall.columns if c.startswith("overall_rank_")]
    overall["overall_RankScore"] = overall[rank_cols].mean(axis=1)
    return overall.sort_values(["overall_RankScore", "mean_RankScore", "method"])


def transaction_cost_sensitivity(run_metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    base = run_metrics.copy()
    base["universe_window"] = base["universe"].astype(str) + "::" + base["window_id"].astype(str)
    for label, cost_rate in COST_SCENARIOS.items():
        frame = base.copy()
        frame["cost_scenario"] = label
        frame["cost_rate"] = cost_rate
        frame["scenario_transaction_cost"] = frame["rebalance_turnover"] * cost_rate
        frame["scenario_net_return"] = frame["gross_return"] - frame["scenario_transaction_cost"]
        frame["scenario_annual_net_return"] = annualize(frame["scenario_net_return"], frame["test_days"])
        rows.append(frame)
    run_sens = pd.concat(rows, ignore_index=True)
    overall = (
        run_sens.groupby(["cost_scenario", "cost_rate", "method"], sort=False)
        .agg(
            universe_windows=("universe_window", "nunique"),
            mean_annual_net_return=("scenario_annual_net_return", "mean"),
            mean_net_return=("scenario_net_return", "mean"),
            mean_turnover=("rebalance_turnover", "mean"),
            mean_cvar95_loss=("cvar95_loss", "mean"),
            mean_max_drawdown=("max_drawdown", "mean"),
            mean_sharpe=("sharpe", "mean"),
            mean_sortino=("sortino", "mean"),
        )
        .reset_index()
    )
    overall["rank_annual_net_return"] = overall.groupby("cost_scenario")["mean_annual_net_return"].rank(
        ascending=False, method="average"
    )
    return run_sens, overall.sort_values(["cost_rate", "rank_annual_net_return", "method"])


def write_readme(overall: pd.DataFrame, cost: pd.DataFrame, completeness: pd.DataFrame, out_dir: Path) -> None:
    lines = [
        "# Real-Market Configured ECMADE-MOO Comparison",
        "",
        "Compared protocols: Hand-crafted, Bayesian, Meta-designed, and Experiment C Stability-aware ECMADE-MOO.",
        "PF metrics use the same common-reference-front post-processing as Experiments B/C, grouped by universe and rolling window.",
        "",
        "## Completeness",
        "",
        completeness.to_csv(index=False),
        "",
        "## Overall Summary",
        "",
        overall.to_csv(index=False),
        "",
        "## Transaction Cost Sensitivity",
        "",
        cost.to_csv(index=False),
    ]
    (out_dir / "README_configured_real_market.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, default=RAW_ROOT)
    parser.add_argument("--assignment", type=Path, default=ASSIGNMENT_PATH)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    run_df, pfs, fronts_by_window = discover_runs(args.raw_root)
    run_metrics = add_pf_metrics(run_df, pfs, fronts_by_window)
    window_summary = summarize_windows(run_metrics)
    ranked = add_ranks(window_summary)
    overall = overall_summary(ranked)
    run_sens, cost_overall = transaction_cost_sensitivity(run_metrics)
    completeness = (
        run_metrics.assign(universe_window=run_metrics["universe"].astype(str) + "::" + run_metrics["window_id"].astype(str))
        .groupby("method")
        .agg(universe_windows=("universe_window", "nunique"), runs=("run", "count"))
        .reset_index()
    )
    assignments = pd.read_csv(args.assignment, encoding="utf-8-sig")
    theta_usage = assignments.groupby(["method", "theta_id"]).size().reset_index(name="windows")

    run_metrics.to_csv(out_dir / "configured_run_metrics_with_pf_stability.csv", index=False, encoding="utf-8-sig")
    window_summary.to_csv(out_dir / "configured_window_method_summary.csv", index=False, encoding="utf-8-sig")
    ranked.to_csv(out_dir / "configured_window_method_ranked.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(out_dir / "configured_overall_summary.csv", index=False, encoding="utf-8-sig")
    run_sens.to_csv(out_dir / "configured_transaction_cost_run_sensitivity.csv", index=False, encoding="utf-8-sig")
    cost_overall.to_csv(out_dir / "configured_transaction_cost_overall.csv", index=False, encoding="utf-8-sig")
    completeness.to_csv(out_dir / "configured_run_completeness.csv", index=False, encoding="utf-8-sig")
    theta_usage.to_csv(out_dir / "configured_theta_usage_by_method.csv", index=False, encoding="utf-8-sig")
    write_readme(overall, cost_overall, completeness, out_dir)
    print(f"OUT_DIR={out_dir}")
    print(completeness.to_string(index=False))
    print(overall.to_string(index=False))


if __name__ == "__main__":
    main()
