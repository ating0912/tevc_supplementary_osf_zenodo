from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
SUMMARY_DIR = (
    ROOT
    / "p0_lite_outputs"
    / "p1_rolling_window_market_validation_20260719"
    / "configured_ecmade_comparison_summary"
)
OUT_DIR = ROOT / "outputs" / "real_market_config_protocol_section_20260730"

DISPLAY = {
    "HandCrafted_ECMADE_MOO": "Hand-crafted ECMADE-MOO",
    "BayesianConfig_ECMADE_MOO": "Bayesian ECMADE-MOO",
    "MetaDesigned_ECMADE_MOO": "Meta-designed ECMADE-MOO",
    "ExperimentC_StabilityAware_ECMADE_MOO": "Stability-aware ECMADE-MOO",
}


def pct(x: float) -> str:
    return f"{100 * x:.2f}%"


def num(x: float, digits: int = 4) -> str:
    return f"{x:.{digits}f}"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    overall = pd.read_csv(SUMMARY_DIR / "configured_overall_summary.csv", encoding="utf-8-sig")
    friedman = pd.read_csv(SUMMARY_DIR / "configured_friedman_tests.csv", encoding="utf-8-sig")
    pairwise = pd.read_csv(SUMMARY_DIR / "configured_pairwise_wilcoxon_holm.csv", encoding="utf-8-sig")

    cols = [
        "method",
        "mean_annual_net_return",
        "mean_sharpe",
        "mean_sortino",
        "mean_cvar95_loss",
        "mean_max_drawdown",
        "mean_rebalance_turnover",
        "mean_HV",
        "mean_IGD",
        "mean_PF_Overlap",
        "mean_PF_Drift",
        "mean_Diversity",
        "mean_WindowRank",
        "overall_RankScore",
    ]
    table = overall[cols].copy()
    table.insert(0, "Protocol", table["method"].map(DISPLAY))
    table = table.drop(columns=["method"]).rename(
        columns={
            "mean_annual_net_return": "Annualized net return",
            "mean_sharpe": "Sharpe ratio",
            "mean_sortino": "Sortino ratio",
            "mean_cvar95_loss": "CVaR 95% loss",
            "mean_max_drawdown": "MDD",
            "mean_rebalance_turnover": "Turnover",
            "mean_HV": "HV",
            "mean_IGD": "IGD",
            "mean_PF_Overlap": "PF Overlap",
            "mean_PF_Drift": "PF Drift",
            "mean_Diversity": "Diversity",
            "mean_WindowRank": "CrossWindowOverallRank",
            "overall_RankScore": "OverallRankScore",
        }
    )
    table.to_csv(OUT_DIR / "table_5_6_4_real_market_config_protocols.csv", index=False, encoding="utf-8-sig")

    rank_f = friedman[friedman["metric"].eq("RankScore")].iloc[0]
    cvar_f = friedman[friedman["metric"].eq("cvar95_loss_mean")].iloc[0]
    drift_f = friedman[friedman["metric"].eq("PF_Drift_mean")].iloc[0]
    rank_pair = pairwise[pairwise["metric"].eq("RankScore")].copy()
    rank_pair_table = rank_pair[
        [
            "baseline",
            "wins",
            "ties",
            "losses",
            "median_signed_improvement",
            "raw_p_value",
            "holm_p_value",
            "significant_after_holm",
        ]
    ].copy()
    rank_pair_table.insert(0, "Primary protocol", "Stability-aware ECMADE-MOO")
    rank_pair_table["Baseline protocol"] = rank_pair_table["baseline"].map(DISPLAY)
    rank_pair_table = rank_pair_table.drop(columns=["baseline"]).rename(
        columns={
            "wins": "Wins",
            "ties": "Ties",
            "losses": "Losses",
            "median_signed_improvement": "Median RankScore improvement",
            "raw_p_value": "Raw p-value",
            "holm_p_value": "Holm-adjusted p-value",
            "significant_after_holm": "Significant after Holm",
        }
    )
    rank_pair_table = rank_pair_table[
        [
            "Primary protocol",
            "Baseline protocol",
            "Wins",
            "Ties",
            "Losses",
            "Median RankScore improvement",
            "Raw p-value",
            "Holm-adjusted p-value",
            "Significant after Holm",
        ]
    ]

    best_by_rank = overall.sort_values(["mean_WindowRank", "method"]).iloc[0]
    bayes = overall[overall["method"].eq("BayesianConfig_ECMADE_MOO")].iloc[0]
    meta = overall[overall["method"].eq("MetaDesigned_ECMADE_MOO")].iloc[0]
    stable = overall[overall["method"].eq("ExperimentC_StabilityAware_ECMADE_MOO")].iloc[0]
    hand = overall[overall["method"].eq("HandCrafted_ECMADE_MOO")].iloc[0]

    md = f"""### 5.6.4 四種 Configuration Protocols 的真實市場比較

本節進一步比較四種 ECMADE-MOO configuration protocols 在 real-market rolling-window validation 中的 out-of-sample 表現，包括 Hand-crafted ECMADE-MOO、Bayesian ECMADE-MOO、Meta-designed ECMADE-MOO 與 Stability-aware ECMADE-MOO。此比較使用與真實市場驗證相同的 33 個 universe-window、10 bps 交易成本設定，以及相同的 final Pareto front 後處理流程。為避免與六種演算法比較混合，本節僅在四種 ECMADE-MOO configuration protocols 之間建立 common reference front、計算 Pareto-front stability 指標與跨視窗排名。

表 5.6.4 彙整四種 protocols 的主要 out-of-sample 指標。CrossWindowOverallRank 定義為每個 universe-window 內多指標 RankScore 排名後，再跨 33 個 windows 取平均，數值越低代表跨市場視窗的整體排名越好。

| Protocol | Annualized net return | Sharpe | Sortino | CVaR 95% loss | MDD | Turnover | HV | IGD | PF Overlap | PF Drift | Diversity | CrossWindowOverallRank |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Hand-crafted ECMADE-MOO | {pct(hand['mean_annual_net_return'])} | {num(hand['mean_sharpe'])} | {num(hand['mean_sortino'])} | {pct(hand['mean_cvar95_loss'])} | {pct(hand['mean_max_drawdown'])} | {num(hand['mean_rebalance_turnover'])} | {num(hand['mean_HV'])} | {num(hand['mean_IGD'])} | {num(hand['mean_PF_Overlap'])} | {num(hand['mean_PF_Drift'])} | {num(hand['mean_Diversity'])} | {num(hand['mean_WindowRank'])} |
| Bayesian ECMADE-MOO | {pct(bayes['mean_annual_net_return'])} | {num(bayes['mean_sharpe'])} | {num(bayes['mean_sortino'])} | {pct(bayes['mean_cvar95_loss'])} | {pct(bayes['mean_max_drawdown'])} | {num(bayes['mean_rebalance_turnover'])} | {num(bayes['mean_HV'])} | {num(bayes['mean_IGD'])} | {num(bayes['mean_PF_Overlap'])} | {num(bayes['mean_PF_Drift'])} | {num(bayes['mean_Diversity'])} | {num(bayes['mean_WindowRank'])} |
| Meta-designed ECMADE-MOO | {pct(meta['mean_annual_net_return'])} | {num(meta['mean_sharpe'])} | {num(meta['mean_sortino'])} | {pct(meta['mean_cvar95_loss'])} | {pct(meta['mean_max_drawdown'])} | {num(meta['mean_rebalance_turnover'])} | {num(meta['mean_HV'])} | {num(meta['mean_IGD'])} | {num(meta['mean_PF_Overlap'])} | {num(meta['mean_PF_Drift'])} | {num(meta['mean_Diversity'])} | {num(meta['mean_WindowRank'])} |
| Stability-aware ECMADE-MOO | {pct(stable['mean_annual_net_return'])} | {num(stable['mean_sharpe'])} | {num(stable['mean_sortino'])} | {pct(stable['mean_cvar95_loss'])} | {pct(stable['mean_max_drawdown'])} | {num(stable['mean_rebalance_turnover'])} | {num(stable['mean_HV'])} | {num(stable['mean_IGD'])} | {num(stable['mean_PF_Overlap'])} | {num(stable['mean_PF_Drift'])} | {num(stable['mean_Diversity'])} | {num(stable['mean_WindowRank'])} |

整體而言，四種 protocols 在跨視窗 RankScore 上存在顯著差異（Friedman chi-square = {rank_f['friedman_chi_square']:.4f}, p = {rank_f['p_value']:.3g}）。然而，這組 real-market validation 並未顯示 Meta-designed 或 Stability-aware protocols 能完整維持其在 synthetic Experiment B/C 中的相對優勢。以 CrossWindowOverallRank 觀察，Hand-crafted ECMADE-MOO 表現最佳（{best_by_rank['mean_WindowRank']:.4f}），Bayesian ECMADE-MOO 次之（{bayes['mean_WindowRank']:.4f}），Stability-aware ECMADE-MOO 排名第三（{stable['mean_WindowRank']:.4f}），Meta-designed ECMADE-MOO 排名第四（{meta['mean_WindowRank']:.4f}）。

表 5.6.5 進一步列出 Stability-aware ECMADE-MOO 相對其他三種 protocols 的 paired Wilcoxon signed-rank tests。此檢定以 33 個 universe-window 為 paired units，並以 Holm correction 校正多重比較。所有 Holm-adjusted p-values 皆未低於 0.05，因此不能宣稱 Stability-aware ECMADE-MOO 在 real-market RankScore 上顯著優於其他 protocols。

| Primary protocol | Baseline protocol | Wins | Ties | Losses | Median RankScore improvement | Raw p-value | Holm-adjusted p-value | Significant after Holm |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Stability-aware ECMADE-MOO | Bayesian ECMADE-MOO | 16 | 1 | 16 | 0.0000 | 0.6283 | 1.0000 | No |
| Stability-aware ECMADE-MOO | Hand-crafted ECMADE-MOO | 2 | 0 | 31 | -0.2727 | 1.0000 | 1.0000 | No |
| Stability-aware ECMADE-MOO | Meta-designed ECMADE-MOO | 19 | 2 | 12 | 0.1818 | 0.1709 | 0.5126 | No |

從單一財務指標來看，Bayesian ECMADE-MOO 取得最高 annualized net return（{pct(bayes['mean_annual_net_return'])}），而 Hand-crafted ECMADE-MOO 取得最高 Sharpe ratio（{num(hand['mean_sharpe'])}）、最高 Sortino ratio（{num(hand['mean_sortino'])}）、最低 CVaR 95% loss（{pct(hand['mean_cvar95_loss'])}）、較佳 MDD（{pct(hand['mean_max_drawdown'])}）與最低 turnover（{num(hand['mean_rebalance_turnover'])}）。在 Pareto-front 指標方面，Bayesian ECMADE-MOO 具有最高 HV（{num(bayes['mean_HV'])}）、最高 PF Overlap（{num(bayes['mean_PF_Overlap'])}）與最低 PF Drift（{num(bayes['mean_PF_Drift'])}）；Meta-designed ECMADE-MOO 則在 IGD（{num(meta['mean_IGD'])}）與 Diversity（{num(meta['mean_Diversity'])}）上最佳。

Stability-aware ECMADE-MOO 在 real-market setting 中相較 Meta-designed ECMADE-MOO 具有較高 annualized net return、Sharpe ratio、Sortino ratio、較低 turnover 與較低 PF Drift，顯示 stability-aware label 對部分 out-of-sample stability 與交易行為仍有幫助。不過，Stability-aware ECMADE-MOO 相對 Hand-crafted、Bayesian 與 Meta-designed 的 RankScore paired Wilcoxon tests 在 Holm correction 後皆未達顯著；因此，本研究不宣稱 Stability-aware protocol 在真實市場中顯著支配所有 baselines。

這個結果表示，Meta-designed 與 Stability-aware protocols 在 synthetic constrained portfolio instances 上的優勢，並不會自動完全轉移到 real-market rolling-window setting。真實市場資料包含 regime shifts、survivorship bias 風險、交易成本與股票池組成變動等因素，因此本節應被定位為 external validation / robustness check。其主要結論是：automated configuration protocols 在真實市場中仍能產生可比較的 Pareto-front quality 與 stability 行為，但若要在 real-market setting 中穩定優於 hand-crafted 或 Bayesian protocol，仍需要進一步使用 market-specific training labels、rolling-window selector calibration 或更嚴格的 transaction-cost-aware label design。
"""

    (OUT_DIR / "section_5_6_4_real_market_configuration_protocols.md").write_text(md, encoding="utf-8")
    rank_pair.to_csv(OUT_DIR / "rankscore_pairwise_for_section_5_6_4.csv", index=False, encoding="utf-8-sig")
    rank_pair_table.to_csv(OUT_DIR / "table_5_6_5_rankscore_pairwise_wilcoxon_holm.csv", index=False, encoding="utf-8-sig")
    print(f"OUT_DIR={OUT_DIR}")
    print(table.to_string(index=False))
    print(rank_pair[["primary", "baseline", "wins", "ties", "losses", "holm_p_value", "significant_after_holm"]].to_string(index=False))


if __name__ == "__main__":
    main()
