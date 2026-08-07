from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
RAW_ROOT = ROOT / "p0_lite_outputs" / "p1_rolling_window_market_validation_20260719" / "raw"
OUT_DIR = ROOT / "p0_lite_outputs" / "p1_rolling_window_market_validation_20260719" / "cvar_sensitivity"

COST_SCENARIOS = {
    "10bps": 0.001,
    "20bps": 0.002,
    "50bps": 0.005,
}


def annualize(total_return: pd.Series, days: pd.Series) -> pd.Series:
    return np.power(1.0 + total_return, 252.0 / days) - 1.0


def run_dir(row: pd.Series) -> Path:
    return RAW_ROOT / str(row["universe"]) / str(row["window_id"]) / str(row["method"]) / f"run_{int(row['run']):03d}"


def cvar95_return(path: Path) -> tuple[float, float, int]:
    returns = pd.read_csv(path, header=None).iloc[:, 0].astype(float).dropna()
    if returns.empty:
        return np.nan, np.nan, 0
    threshold = returns.quantile(0.05)
    tail = returns[returns <= threshold]
    cvar_return = float(tail.mean()) if not tail.empty else float(returns.min())
    return cvar_return, -cvar_return, int(len(returns))


def add_cvar(run_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in run_summary.iterrows():
        path = run_dir(row) / "test_daily_returns.csv"
        cvar_ret, cvar_loss, n_days = cvar95_return(path)
        rows.append(
            {
                **row.to_dict(),
                "test_daily_return_days": n_days,
                "cvar95_return": cvar_ret,
                "cvar95_loss": cvar_loss,
            }
        )
    return pd.DataFrame(rows)


def summarize_cvar(run_cvar: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    window = (
        run_cvar.groupby(["universe", "window_id", "method", "assets", "K", "train_days", "test_days"], sort=False)
        .agg(
            annual_net_return_mean=("annual_net_return", "mean"),
            sharpe_mean=("sharpe", "mean"),
            sortino_mean=("sortino", "mean"),
            max_drawdown_mean=("max_drawdown", "mean"),
            turnover_mean=("turnover", "mean"),
            transaction_cost_mean=("transaction_cost", "mean"),
            cvar95_return_mean=("cvar95_return", "mean"),
            cvar95_loss_mean=("cvar95_loss", "mean"),
            runtime_sec_mean=("runtime_sec", "mean"),
            runs=("run", "nunique"),
        )
        .reset_index()
    )
    overall = (
        window.groupby("method", sort=False)
        .agg(
            windows=("window_id", "count"),
            mean_annual_net_return=("annual_net_return_mean", "mean"),
            mean_sharpe=("sharpe_mean", "mean"),
            mean_sortino=("sortino_mean", "mean"),
            mean_max_drawdown=("max_drawdown_mean", "mean"),
            mean_turnover=("turnover_mean", "mean"),
            mean_cvar95_return=("cvar95_return_mean", "mean"),
            mean_cvar95_loss=("cvar95_loss_mean", "mean"),
            mean_runtime_sec=("runtime_sec_mean", "mean"),
        )
        .reset_index()
    )
    overall["rank_cvar95_loss"] = overall["mean_cvar95_loss"].rank(ascending=True, method="average")
    return window, overall.sort_values(["rank_cvar95_loss", "method"])


def build_cost_sensitivity(run_summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    base = run_summary.copy()
    base["turnover"] = pd.to_numeric(base["turnover"], errors="coerce").fillna(1.0)
    base["gross_return"] = pd.to_numeric(base["gross_return"], errors="coerce")
    base["test_days"] = pd.to_numeric(base["test_days"], errors="coerce")
    for label, cost_rate in COST_SCENARIOS.items():
        frame = base.copy()
        frame["cost_scenario"] = label
        frame["cost_rate"] = cost_rate
        frame["scenario_transaction_cost"] = frame["turnover"] * cost_rate
        frame["scenario_net_return"] = frame["gross_return"] - frame["scenario_transaction_cost"]
        frame["scenario_annual_net_return"] = annualize(frame["scenario_net_return"], frame["test_days"])
        rows.append(frame)
    run_sensitivity = pd.concat(rows, ignore_index=True)

    window = (
        run_sensitivity.groupby(
            ["cost_scenario", "cost_rate", "universe", "window_id", "method", "assets", "K", "train_days", "test_days"],
            sort=False,
        )
        .agg(
            scenario_net_return_mean=("scenario_net_return", "mean"),
            scenario_annual_net_return_mean=("scenario_annual_net_return", "mean"),
            turnover_mean=("turnover", "mean"),
            gross_return_mean=("gross_return", "mean"),
            runs=("run", "nunique"),
        )
        .reset_index()
    )
    overall = (
        window.groupby(["cost_scenario", "cost_rate", "method"], sort=False)
        .agg(
            windows=("window_id", "count"),
            mean_scenario_net_return=("scenario_net_return_mean", "mean"),
            mean_scenario_annual_net_return=("scenario_annual_net_return_mean", "mean"),
            mean_turnover=("turnover_mean", "mean"),
        )
        .reset_index()
    )
    overall["rank_annual_net_return"] = overall.groupby("cost_scenario")[
        "mean_scenario_annual_net_return"
    ].rank(ascending=False, method="average")
    return run_sensitivity, window, overall.sort_values(["cost_rate", "rank_annual_net_return", "method"])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = RAW_ROOT / "rolling_backtest_run_summary.csv"
    run_summary = pd.read_csv(summary_path, encoding="utf-8-sig")

    run_cvar = add_cvar(run_summary)
    cvar_window, cvar_overall = summarize_cvar(run_cvar)
    run_cvar.to_csv(OUT_DIR / "rolling_run_metrics_with_cvar.csv", index=False, encoding="utf-8-sig")
    cvar_window.to_csv(OUT_DIR / "window_method_cvar_summary.csv", index=False, encoding="utf-8-sig")
    cvar_overall.to_csv(OUT_DIR / "method_cvar_overall_summary.csv", index=False, encoding="utf-8-sig")

    run_sens, window_sens, overall_sens = build_cost_sensitivity(run_summary)
    run_sens.to_csv(OUT_DIR / "rolling_run_transaction_cost_sensitivity.csv", index=False, encoding="utf-8-sig")
    window_sens.to_csv(OUT_DIR / "window_transaction_cost_sensitivity.csv", index=False, encoding="utf-8-sig")
    overall_sens.to_csv(OUT_DIR / "method_transaction_cost_sensitivity.csv", index=False, encoding="utf-8-sig")

    lines = [
        "# Rolling Market CVaR and Transaction-Cost Sensitivity",
        "",
        "CVaR(95%) is computed as the mean of the worst 5% daily out-of-sample returns.",
        "Transaction-cost sensitivity is post-processed from gross return and turnover; it does not rerun the optimizer.",
        "",
        "## Method CVaR Overall",
        "",
        cvar_overall.to_markdown(index=False),
        "",
        "## Transaction-Cost Sensitivity",
        "",
        overall_sens.to_markdown(index=False),
        "",
    ]
    (OUT_DIR / "README_cvar_sensitivity.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"OUT_DIR={OUT_DIR}")
    print(cvar_overall.to_string(index=False))
    print(overall_sens.to_string(index=False))


if __name__ == "__main__":
    main()
