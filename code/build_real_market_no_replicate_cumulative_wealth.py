from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent
SUMMARY_DIR = (
    ROOT
    / "p0_lite_outputs"
    / "p1_rolling_window_market_validation_20260719"
    / "configured_ecmade_no_replicate_audit_summary_20260731"
)
RANKED_PATH = SUMMARY_DIR / "configured_run_metrics_with_pf_stability.csv"
OUT_RUN = SUMMARY_DIR / "configured_cumulative_wealth_by_run.csv"
OUT_MEAN = SUMMARY_DIR / "configured_cumulative_wealth_mean.csv"
OUT_PLOT = SUMMARY_DIR / "configured_cumulative_wealth_mean.png"


def read_returns(path: Path) -> pd.Series:
    if not path.exists():
        return pd.Series(dtype=float)
    return pd.read_csv(path, header=None).iloc[:, 0].astype(float).dropna().reset_index(drop=True)


def main() -> None:
    run_metrics = pd.read_csv(RANKED_PATH, encoding="utf-8-sig")
    rows = []
    for (universe, method, run), group in run_metrics.groupby(["universe", "method", "run"], sort=False):
        group = group.sort_values("window_id")
        wealth = 1.0
        day_index = 0
        for _, rec in group.iterrows():
            returns = read_returns(Path(rec["run_dir"]) / "test_daily_returns.csv")
            for ret in returns:
                wealth *= 1.0 + float(ret)
                day_index += 1
                rows.append(
                    {
                        "universe": universe,
                        "method": method,
                        "run": int(run),
                        "day_index": day_index,
                        "wealth": wealth,
                        "window_id": rec["window_id"],
                    }
                )
    run_wealth = pd.DataFrame(rows)
    if run_wealth.empty:
        raise RuntimeError("No cumulative wealth rows generated.")
    mean_wealth = (
        run_wealth.groupby(["universe", "method", "day_index"], as_index=False)
        .agg(mean_wealth=("wealth", "mean"), median_wealth=("wealth", "median"), runs=("run", "nunique"))
    )
    run_wealth.to_csv(OUT_RUN, index=False, encoding="utf-8-sig")
    mean_wealth.to_csv(OUT_MEAN, index=False, encoding="utf-8-sig")

    methods = sorted(mean_wealth["method"].unique())
    universes = sorted(mean_wealth["universe"].unique())
    fig, axes = plt.subplots(len(universes), 1, figsize=(11, 4 * len(universes)), sharex=False)
    if len(universes) == 1:
        axes = [axes]
    for ax, universe in zip(axes, universes):
        sub = mean_wealth[mean_wealth["universe"].eq(universe)]
        for method in methods:
            m = sub[sub["method"].eq(method)]
            if m.empty:
                continue
            ax.plot(m["day_index"], m["mean_wealth"], label=method, linewidth=1.8)
        ax.set_title(universe)
        ax.set_xlabel("Out-of-sample day index")
        ax.set_ylabel("Mean cumulative wealth")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT_PLOT, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"WROTE={SUMMARY_DIR}")


if __name__ == "__main__":
    main()
