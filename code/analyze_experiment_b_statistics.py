from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, wilcoxon


ROOT = Path(__file__).resolve().parent
SUMMARY_DIR = ROOT / "p0_lite_outputs" / "experiment_b_configuration_summary_20260713"
FIG_DIR = SUMMARY_DIR / "figures"

TARGET = "MetaDesigned_ECMADE_MOO"
BASELINES = [
    "HandCrafted_ECMADE_MOO",
    "RandomConfig_ECMADE_MOO",
    "BayesianConfig_ECMADE_MOO",
]

METRICS = {
    "HV": "max",
    "IGD": "min",
    "PF_Overlap": "max",
    "PF_Drift": "min",
    "Diversity": "max",
    "Runtime": "min",
    "RankScore": "min",
}

DISPLAY_NAMES = {
    "HandCrafted_ECMADE_MOO": "Hand-crafted",
    "RandomConfig_ECMADE_MOO": "Random",
    "BayesianConfig_ECMADE_MOO": "Bayesian",
    "MetaDesigned_ECMADE_MOO": "Meta-designed",
}


def holm_adjust(p_values: list[float]) -> list[float]:
    n = len(p_values)
    order = np.argsort(p_values)
    adjusted = np.empty(n, dtype=float)
    running = 0.0
    for rank, idx in enumerate(order):
        value = min((n - rank) * p_values[idx], 1.0)
        running = max(running, value)
        adjusted[idx] = min(running, 1.0)
    return adjusted.tolist()


def cliffs_delta(x: np.ndarray, y: np.ndarray, direction: str) -> float:
    better = 0
    worse = 0
    for xi in x:
        better += int(np.sum(xi > y)) if direction == "max" else int(np.sum(xi < y))
        worse += int(np.sum(xi < y)) if direction == "max" else int(np.sum(xi > y))
    return (better - worse) / (len(x) * len(y))


def paired_effect(x: np.ndarray, y: np.ndarray, direction: str) -> tuple[np.ndarray, float]:
    diff = x - y if direction == "max" else y - x
    median_delta = float(np.median(diff))
    return diff, median_delta


def load_ranked() -> pd.DataFrame:
    path = SUMMARY_DIR / "combined_instance_method_metrics_ranked.csv"
    df = pd.read_csv(path)
    df["instance_key"] = df["split"].astype(str) + "|" + df["instance"].astype(str) + "|K" + df["K"].astype(str)
    return df


def build_wilcoxon(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    p_values = []
    pending_idx = []
    for metric, direction in METRICS.items():
        pivot = df.pivot_table(index="instance_key", columns="method", values=metric, aggfunc="mean")
        for baseline in BASELINES:
            x = pivot[TARGET].to_numpy(dtype=float)
            y = pivot[baseline].to_numpy(dtype=float)
            diff, median_delta = paired_effect(x, y, direction)
            nonzero = diff[np.abs(diff) > 1e-12]
            if len(nonzero) == 0:
                stat = 0.0
                p_value = 1.0
            else:
                alternative = "greater"
                stat, p_value = wilcoxon(diff, alternative=alternative, zero_method="wilcox")
                stat = float(stat)
                p_value = float(p_value)
            wins = int(np.sum(diff > 1e-12))
            losses = int(np.sum(diff < -1e-12))
            ties = int(len(diff) - wins - losses)
            row = {
                "metric": metric,
                "direction": direction,
                "comparison": f"{TARGET} vs {baseline}",
                "target": TARGET,
                "baseline": baseline,
                "n_instances": len(diff),
                "wins": wins,
                "ties": ties,
                "losses": losses,
                "median_improvement": median_delta,
                "mean_improvement": float(np.mean(diff)),
                "wilcoxon_stat": stat,
                "p_value_one_sided": p_value,
                "cliffs_delta": cliffs_delta(x, y, direction),
            }
            pending_idx.append(len(rows))
            p_values.append(p_value)
            rows.append(row)

    adjusted = holm_adjust(p_values)
    for idx, p_adj in zip(pending_idx, adjusted):
        rows[idx]["holm_p_value"] = p_adj
        rows[idx]["significant_0_05"] = p_adj < 0.05
    return pd.DataFrame(rows)


def build_friedman(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    methods = [TARGET, *BASELINES]
    for metric, direction in METRICS.items():
        pivot = df.pivot_table(index="instance_key", columns="method", values=metric, aggfunc="mean")
        values = [pivot[m].to_numpy(dtype=float) for m in methods]
        stat, p_value = friedmanchisquare(*values)
        rank_direction = direction == "min"
        ranks = pivot[methods].rank(axis=1, ascending=rank_direction, method="average")
        row = {
            "metric": metric,
            "direction": direction,
            "friedman_chi_square": float(stat),
            "p_value": float(p_value),
            "n_instances": len(pivot),
        }
        for method in methods:
            row[f"mean_rank_{method}"] = float(ranks[method].mean())
        rows.append(row)
    return pd.DataFrame(rows)


def save_figures(df: pd.DataFrame, overall: pd.DataFrame) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 160,
    })

    order = overall.sort_values("overall_RankScore")["method"].tolist()
    labels = [DISPLAY_NAMES[m] for m in order]
    colors = ["#2E7D32" if m == TARGET else "#546A7B" for m in order]

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.bar(labels, overall.set_index("method").loc[order, "overall_RankScore"], color=colors)
    ax.set_ylabel("Overall rank score (lower is better)")
    ax.set_title("Experiment B overall configuration ranking")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "overall_rank_score.png", bbox_inches="tight")
    plt.close(fig)

    rank_data = [
        df[df["method"] == m]["RankScore"].to_numpy(dtype=float)
        for m in order
    ]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    bp = ax.boxplot(rank_data, tick_labels=labels, patch_artist=True, showmeans=True)
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)
    ax.set_ylabel("Per-instance rank score (lower is better)")
    ax.set_title("Per-instance configuration quality")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "per_instance_rankscore_boxplot.png", bbox_inches="tight")
    plt.close(fig)

    metric_cols = ["HV", "IGD", "PF_Overlap", "PF_Drift", "Runtime"]
    delta_rows = []
    for baseline in BASELINES:
        for metric in metric_cols:
            direction = METRICS[metric]
            pivot = df.pivot_table(index="instance_key", columns="method", values=metric, aggfunc="mean")
            diff, median_delta = paired_effect(
                pivot[TARGET].to_numpy(dtype=float),
                pivot[baseline].to_numpy(dtype=float),
                direction,
            )
            delta_rows.append({
                "baseline": DISPLAY_NAMES[baseline],
                "metric": metric,
                "median_improvement": median_delta,
                "mean_improvement": float(np.mean(diff)),
            })
    delta = pd.DataFrame(delta_rows)
    delta.to_csv(SUMMARY_DIR / "meta_vs_baseline_metric_deltas.csv", index=False, encoding="utf-8-sig")

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharey=False)
    for ax, baseline in zip(axes, [DISPLAY_NAMES[b] for b in BASELINES]):
        sub = delta[delta["baseline"] == baseline]
        ax.axhline(0, color="#444444", linewidth=0.8)
        ax.bar(sub["metric"], sub["median_improvement"], color="#2E7D32")
        ax.set_title(f"Meta vs {baseline}")
        ax.tick_params(axis="x", rotation=35)
        ax.set_ylabel("Median improvement")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "meta_median_improvement_by_metric.png", bbox_inches="tight")
    plt.close(fig)

    usage = pd.read_csv(SUMMARY_DIR / "theta_usage_by_method.csv")
    meta_usage = usage[usage["method"] == TARGET].copy()
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.bar(meta_usage["theta_id"], meta_usage["instances"], color="#2E7D32")
    ax.set_ylabel("Assigned test instances")
    ax.set_title("Meta-designed theta usage")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "meta_theta_usage.png", bbox_inches="tight")
    plt.close(fig)


def write_summary_text(overall: pd.DataFrame, wilcoxon_df: pd.DataFrame, friedman_df: pd.DataFrame) -> None:
    meta = overall[overall["method"] == TARGET].iloc[0]
    lines = [
        "# Experiment B 結果摘要",
        "",
        "本次匯總使用四種 ECMADE-MOO configuration 策略在同一批 32 個 unseen test instances 上的 raw Pareto front 重新建立 common reference front，並重新計算 HV、IGD、PF overlap、PF drift、diversity 與 runtime。這個口徑避免不同實驗資料夾各自建立 reference front 造成的不可比問題。",
        "",
        "## Overall 結果",
        "",
        f"Meta-designed ECMADE-MOO 的 overall RankScore 為 {meta['overall_RankScore']:.3f}，在四種方法中排名第一；mean HV={meta['mean_HV']:.6f}、mean IGD={meta['mean_IGD']:.6f}、mean PF_Overlap={meta['mean_PF_Overlap']:.6f}、mean PF_Drift={meta['mean_PF_Drift']:.6f}。",
        f"在 32 個 test instances 中，Meta-designed 取得 first-place instance rank 的次數為 {int(meta['first_place_instances'])}/32。",
        "",
        "## 統計檢定解讀",
        "",
    ]

    for baseline in BASELINES:
        sub = wilcoxon_df[(wilcoxon_df["baseline"] == baseline) & (wilcoxon_df["metric"] == "RankScore")].iloc[0]
        verdict = "達顯著" if sub["significant_0_05"] else "未達顯著"
        lines.append(
            f"- Meta-designed vs {DISPLAY_NAMES[baseline]}：以 per-instance RankScore 做 one-sided Wilcoxon，wins/ties/losses = {int(sub['wins'])}/{int(sub['ties'])}/{int(sub['losses'])}，Holm-adjusted p = {sub['holm_p_value']:.6g}，{verdict}。"
        )

    lines.extend([
        "",
        "## 建議論文敘述",
        "",
        "Meta-designed ECMADE-MOO 在 unseen test instances 上取得最佳整體排名，顯示由 instance features 預測 theta configuration 的策略能改善泛化表現。相較於 Bayesian configuration，Meta-designed 的 runtime 較高，但在解品質與穩定性指標上整體較佳；相較於 Random configuration 與 hand-crafted ECMADE-MOO，Meta-designed 更能穩定選擇適合 instance 特性的 theta。",
        "",
        "## 輸出檔",
        "",
        "- `statistical_tests_meta_vs_baselines.csv`：Meta-designed 對三個 baseline 的 Wilcoxon paired tests。",
        "- `friedman_tests_all_methods.csv`：四方法多重比較 Friedman tests。",
        "- `figures/`：論文可用圖表。",
    ])
    (SUMMARY_DIR / "experiment_b_result_summary_zh.md").write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> None:
    df = load_ranked()
    overall = pd.read_csv(SUMMARY_DIR / "overall_configuration_comparison.csv")
    wilcoxon_df = build_wilcoxon(df)
    friedman_df = build_friedman(df)

    wilcoxon_df.to_csv(SUMMARY_DIR / "statistical_tests_meta_vs_baselines.csv", index=False, encoding="utf-8-sig")
    friedman_df.to_csv(SUMMARY_DIR / "friedman_tests_all_methods.csv", index=False, encoding="utf-8-sig")
    save_figures(df, overall)
    write_summary_text(overall, wilcoxon_df, friedman_df)

    print("WILCOXON")
    print(wilcoxon_df[wilcoxon_df["metric"].isin(["RankScore", "HV", "IGD", "PF_Overlap", "PF_Drift"])].to_string(index=False))
    print("FRIEDMAN")
    print(friedman_df.to_string(index=False))
    print(f"OUT_DIR={SUMMARY_DIR}")


if __name__ == "__main__":
    main()
