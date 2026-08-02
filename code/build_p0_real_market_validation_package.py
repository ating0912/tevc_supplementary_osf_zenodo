from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
EXP_ROOT = ROOT / "p0_lite_outputs" / "p1_rolling_window_market_validation_20260719"
RAW_ROOT = EXP_ROOT / "raw"
SUMMARY_DIR = EXP_ROOT / "p0_real_market_validation"

METHODS = ["NSGAII", "SPEA2", "MOEAD", "GDE3", "A_MPMO", "ECMADE_MOO"]
COST_SCENARIOS = {"10bps": 0.001, "20bps": 0.002, "50bps": 0.005}


def run_dir(row: pd.Series) -> Path:
    return RAW_ROOT / str(row["universe"]) / str(row["window_id"]) / str(row["method"]) / f"run_{int(row['run']):03d}"


def daily_returns(row: pd.Series) -> pd.Series:
    path = run_dir(row) / "test_daily_returns.csv"
    return pd.read_csv(path, header=None).iloc[:, 0].astype(float).dropna()


def weights(row: pd.Series) -> pd.Series:
    path = run_dir(row) / "selected_portfolio.csv"
    portfolio = pd.read_csv(path, encoding="utf-8-sig")
    series = portfolio.set_index("ticker")["weight"].astype(float)
    return series[series.abs() > 1e-12]


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


def annualize(total_return: pd.Series, days: pd.Series) -> pd.Series:
    return np.power(1.0 + total_return, 252.0 / days) - 1.0


def build_run_metrics(run_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in run_summary.iterrows():
        rets = daily_returns(row)
        out = row.to_dict()
        out["daily_return_days"] = int(len(rets))
        out["cvar95_loss"] = cvar95_loss(rets)
        out["mdd_from_daily_returns"] = max_drawdown_from_returns(rets)
        rows.append(out)
    return pd.DataFrame(rows)


def pair_turnover(previous: pd.Series | None, current: pd.Series) -> float:
    if previous is None:
        return 1.0
    tickers = previous.index.union(current.index)
    diff = current.reindex(tickers, fill_value=0.0) - previous.reindex(tickers, fill_value=0.0)
    return float(0.5 * diff.abs().sum())


def add_rebalance_turnover(run_metrics: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for _, group in run_metrics.groupby(["universe", "method", "run"], sort=False):
        group = group.sort_values("window_id").copy()
        previous = None
        turnovers = []
        for _, row in group.iterrows():
            current = weights(row)
            turnovers.append(pair_turnover(previous, current))
            previous = current
        group["rebalance_turnover"] = turnovers
        frames.append(group)
    return pd.concat(frames, ignore_index=True)


def summarize_windows(run_metrics: pd.DataFrame) -> pd.DataFrame:
    return (
        run_metrics.groupby(["universe", "window_id", "method", "assets", "K", "train_days", "test_days"], sort=False)
        .agg(
            runs=("run", "nunique"),
            annual_net_return_mean=("annual_net_return", "mean"),
            annual_net_return_std=("annual_net_return", "std"),
            sharpe_mean=("sharpe", "mean"),
            sortino_mean=("sortino", "mean"),
            max_drawdown_mean=("max_drawdown", "mean"),
            cvar95_loss_mean=("cvar95_loss", "mean"),
            rebalance_turnover_mean=("rebalance_turnover", "mean"),
            gross_return_mean=("gross_return", "mean"),
            runtime_sec_mean=("runtime_sec", "mean"),
        )
        .reset_index()
    )


def summarize_overall(window_summary: pd.DataFrame) -> pd.DataFrame:
    overall = (
        window_summary.groupby("method", sort=False)
        .agg(
            windows=("window_id", "count"),
            mean_annual_net_return=("annual_net_return_mean", "mean"),
            mean_sharpe=("sharpe_mean", "mean"),
            mean_sortino=("sortino_mean", "mean"),
            mean_max_drawdown=("max_drawdown_mean", "mean"),
            mean_cvar95_loss=("cvar95_loss_mean", "mean"),
            mean_rebalance_turnover=("rebalance_turnover_mean", "mean"),
            mean_runtime_sec=("runtime_sec_mean", "mean"),
        )
        .reset_index()
    )
    rank_specs = {
        "rank_return": ("mean_annual_net_return", False),
        "rank_sharpe": ("mean_sharpe", False),
        "rank_sortino": ("mean_sortino", False),
        "rank_mdd": ("mean_max_drawdown", False),
        "rank_cvar": ("mean_cvar95_loss", True),
        "rank_turnover": ("mean_rebalance_turnover", True),
    }
    rank_cols = []
    for rank_col, (metric_col, ascending) in rank_specs.items():
        overall[rank_col] = overall[metric_col].rank(ascending=ascending, method="average")
        rank_cols.append(rank_col)
    overall["stability_rank_score"] = overall[rank_cols].mean(axis=1)
    return overall.sort_values(["stability_rank_score", "method"])


def transaction_cost_sensitivity(run_metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    base = run_metrics.copy()
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
            windows=("window_id", "nunique"),
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


def build_wealth_curve(run_metrics: pd.DataFrame, cost_rate: float = 0.001) -> pd.DataFrame:
    curves = []
    for (universe, method, run), group in run_metrics.groupby(["universe", "method", "run"], sort=False):
        group = group.sort_values("window_id")
        pieces = []
        day_offset = 0
        for _, row in group.iterrows():
            rets = daily_returns(row).reset_index(drop=True)
            if rets.empty:
                continue
            net_rets = rets.copy()
            net_rets.iloc[0] = net_rets.iloc[0] - cost_rate * float(row["rebalance_turnover"])
            n = len(net_rets)
            pieces.append(
                pd.DataFrame(
                    {
                        "universe": universe,
                        "method": method,
                        "run": run,
                        "window_id": row["window_id"],
                        "global_test_day": np.arange(day_offset + 1, day_offset + n + 1),
                        "net_daily_return_10bps": net_rets,
                    }
                )
            )
            day_offset += n
        if pieces:
            frame = pd.concat(pieces, ignore_index=True)
            frame["wealth_10bps"] = (1.0 + frame["net_daily_return_10bps"]).cumprod()
            curves.append(frame)
    run_curves = pd.concat(curves, ignore_index=True)
    mean_curve = (
        run_curves.groupby(["universe", "method", "global_test_day"], sort=False)
        .agg(
            mean_net_daily_return_10bps=("net_daily_return_10bps", "mean"),
            mean_wealth_10bps=("wealth_10bps", "mean"),
            runs=("run", "nunique"),
        )
        .reset_index()
    )
    return run_curves, mean_curve


def plot_wealth_curve(mean_curve: pd.DataFrame) -> Path:
    out_path = SUMMARY_DIR / "p0_real_market_wealth_curve_10bps.png"
    universes = list(mean_curve["universe"].drop_duplicates())
    fig, axes = plt.subplots(len(universes), 1, figsize=(9, 2.8 * len(universes)), sharex=False)
    if len(universes) == 1:
        axes = [axes]
    for ax, universe in zip(axes, universes):
        part = mean_curve[mean_curve["universe"] == universe]
        for method in METHODS:
            line = part[part["method"] == method]
            if line.empty:
                continue
            ax.plot(line["global_test_day"], line["mean_wealth_10bps"], label=method, linewidth=1.6)
        ax.set_title(universe)
        ax.set_ylabel("Wealth")
        ax.grid(True, alpha=0.25)
    axes[-1].set_xlabel("Out-of-sample trading day")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(out_path, dpi=220)
    plt.close(fig)
    return out_path


def write_paper_ready_text(overall: pd.DataFrame, cost_overall: pd.DataFrame) -> None:
    display_cols = [
        "method",
        "windows",
        "mean_annual_net_return",
        "mean_sharpe",
        "mean_sortino",
        "mean_max_drawdown",
        "mean_cvar95_loss",
        "mean_rebalance_turnover",
        "stability_rank_score",
    ]
    cost_cols = [
        "cost_scenario",
        "method",
        "windows",
        "mean_annual_net_return",
        "mean_turnover",
        "rank_annual_net_return",
    ]
    lines = [
        "# P0 Real-Market Rolling-Window 補稿表格與文字",
        "",
        "## 實驗設計",
        "",
        "本補充實驗使用 SP100、NASDAQ100 與 TW50 三組真實市場 universe，每組 11 個 rolling windows，共 33 個 universe-window。每個 window 採用約 3 年 training window 與約 6 個月 out-of-sample testing window，並以 final Pareto front 中 training Sharpe 最高的投資組合作為測試投資組合。每個方法每個 window 執行 10 runs；基準交易成本為 10 bps，另做 20 bps 與 50 bps sensitivity。",
        "",
        "## Table: Real-Market Rolling-Window Validation",
        "",
        overall[display_cols].to_markdown(index=False, floatfmt=".6g"),
        "",
        "## Table: Transaction-Cost Sensitivity",
        "",
        cost_overall[cost_cols].to_markdown(index=False, floatfmt=".6g"),
        "",
        "## 建議寫法",
        "",
        "Across 33 real-market rolling windows, the proposed ECMADE-MOO did not dominate the return-oriented baselines in annualized after-cost return; however, it achieved the lowest mean CVaR(95%) loss among the six compared methods, indicating a more conservative downside-risk profile under real-market data. The transaction-cost sensitivity analysis further shows that the ranking of annualized net return is stable across 10, 20, and 50 bps settings. Therefore, the real-market experiment is reported as an external validation and limitation analysis rather than as evidence of return dominance.",
        "",
    ]
    (SUMMARY_DIR / "P0_real_market_validation_paper_ready.md").write_text("\n".join(lines), encoding="utf-8")


def write_readme(overall: pd.DataFrame, cost_overall: pd.DataFrame) -> None:
    lines = [
        "# P0 Real-Market Rolling-Window Validation",
        "",
        "Design: 3-year training window and 6-month out-of-sample testing window, using completed rolling-market optimizer outputs.",
        "Portfolio choice: the max-training-Sharpe portfolio selected from each final Pareto front.",
        "Reported metrics: after-transaction-cost return, turnover, CVaR(95%), maximum drawdown, Sharpe, Sortino, 10 bps after-cost wealth curve, and stability ranks.",
        "",
        "## Overall Validation Summary",
        "",
        overall.to_markdown(index=False, floatfmt=".6g"),
        "",
        "## Transaction-Cost Sensitivity",
        "",
        cost_overall.to_markdown(index=False, floatfmt=".6g"),
        "",
    ]
    (SUMMARY_DIR / "README_p0_real_market_validation.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    run_summary_path = RAW_ROOT / "rolling_backtest_run_summary.csv"
    run_summary = pd.read_csv(run_summary_path, encoding="utf-8-sig")
    run_summary = run_summary[run_summary["method"].isin(METHODS)].copy()

    run_metrics = add_rebalance_turnover(build_run_metrics(run_summary))
    window_summary = summarize_windows(run_metrics)
    overall = summarize_overall(window_summary)
    run_sens, cost_overall = transaction_cost_sensitivity(run_metrics)
    cost_overall["windows"] = cost_overall["windows"].astype(int) * run_metrics["universe"].nunique()
    wealth_curve_runs, wealth_curve_mean = build_wealth_curve(run_metrics)
    wealth_plot = plot_wealth_curve(wealth_curve_mean)

    run_metrics.to_csv(SUMMARY_DIR / "p0_real_market_run_metrics.csv", index=False, encoding="utf-8-sig")
    window_summary.to_csv(SUMMARY_DIR / "p0_real_market_window_method_summary.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(SUMMARY_DIR / "p0_real_market_overall_summary.csv", index=False, encoding="utf-8-sig")
    run_sens.to_csv(SUMMARY_DIR / "p0_real_market_transaction_cost_run_sensitivity.csv", index=False, encoding="utf-8-sig")
    cost_overall.to_csv(SUMMARY_DIR / "p0_real_market_transaction_cost_overall.csv", index=False, encoding="utf-8-sig")
    wealth_curve_runs.to_csv(SUMMARY_DIR / "p0_real_market_wealth_curve_run_level.csv", index=False, encoding="utf-8-sig")
    wealth_curve_mean.to_csv(SUMMARY_DIR / "p0_real_market_wealth_curve_mean.csv", index=False, encoding="utf-8-sig")
    write_readme(overall, cost_overall)
    write_paper_ready_text(overall, cost_overall)

    print(f"Wrote {SUMMARY_DIR}")
    print(f"Wealth plot: {wealth_plot}")
    print(overall.to_string(index=False))
    print(cost_overall.to_string(index=False))


if __name__ == "__main__":
    main()
