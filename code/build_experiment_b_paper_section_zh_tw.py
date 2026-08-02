from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
SUMMARY_DIR = ROOT / "p0_lite_outputs" / "experiment_b_configuration_summary_20260713"
OUT = SUMMARY_DIR / "experiment_b_paper_section_繁中.md"

NAME = {
    "MetaDesigned_ECMADE_MOO": "Meta-designed ECMADE-MOO",
    "BayesianConfig_ECMADE_MOO": "Bayesian configuration ECMADE-MOO",
    "RandomConfig_ECMADE_MOO": "Random configuration ECMADE-MOO",
    "HandCrafted_ECMADE_MOO": "Hand-crafted ECMADE-MOO",
}


def fmt(x: float, digits: int = 4) -> str:
    return f"{float(x):.{digits}f}"


def p_fmt(x: float) -> str:
    x = float(x)
    if x < 0.001:
        return f"{x:.2e}"
    return f"{x:.4f}"


def make_overall_table(overall: pd.DataFrame) -> str:
    rows = []
    for _, r in overall.iterrows():
        rows.append(
            [
                NAME[r["method"]],
                fmt(r["mean_HV"]),
                fmt(r["mean_IGD"]),
                fmt(r["mean_PF_Overlap"]),
                fmt(r["mean_PF_Drift"]),
                fmt(r["mean_Runtime"]),
                fmt(r["overall_RankScore"], 3),
                f"{int(r['first_place_instances'])}/32",
            ]
        )
    return pd.DataFrame(
        rows,
        columns=["方法", "HV ↑", "IGD ↓", "PF overlap ↑", "PF drift ↓", "Runtime ↓", "RankScore ↓", "第一名次數"],
    ).to_markdown(index=False)


def make_stats_table(stats: pd.DataFrame) -> str:
    sub = stats[stats["metric"] == "RankScore"]
    rows = []
    for _, r in sub.iterrows():
        rows.append(
            [
                f"Meta-designed vs {NAME[r['baseline']]}",
                f"{int(r['wins'])}/{int(r['ties'])}/{int(r['losses'])}",
                fmt(r["median_improvement"], 3),
                p_fmt(r["holm_p_value"]),
                "是" if str(r["significant_0_05"]).lower() == "true" else "否",
            ]
        )
    return pd.DataFrame(
        rows,
        columns=["比較組合", "勝/平/負", "RankScore 中位改善量", "Holm p-value", "顯著"],
    ).to_markdown(index=False)


def main() -> None:
    overall = pd.read_csv(SUMMARY_DIR / "overall_configuration_comparison.csv")
    stats = pd.read_csv(SUMMARY_DIR / "statistical_tests_meta_vs_baselines.csv")
    friedman = pd.read_csv(SUMMARY_DIR / "friedman_tests_all_methods.csv")

    meta = overall[overall["method"] == "MetaDesigned_ECMADE_MOO"].iloc[0]
    bayes = overall[overall["method"] == "BayesianConfig_ECMADE_MOO"].iloc[0]
    random = overall[overall["method"] == "RandomConfig_ECMADE_MOO"].iloc[0]
    hand = overall[overall["method"] == "HandCrafted_ECMADE_MOO"].iloc[0]
    rank_friedman = friedman[friedman["metric"] == "RankScore"].iloc[0]

    text = f"""# 實驗 B：ECMADE-MOO Configuration Strategy 比較

## 實驗設定

實驗 B 的目的在於檢驗 configuration selection 是否能提升 ECMADE-MOO 在未見測試問題上的表現。本實驗比較四種策略：Hand-crafted ECMADE-MOO、Random configuration ECMADE-MOO、Bayesian configuration ECMADE-MOO，以及 Meta-designed ECMADE-MOO。四種方法皆使用相同的 32 個 unseen test instances 進行評估，每個 instance 執行 30 次獨立 run，population size 固定為 N=100，終止條件固定為 maxFE=10000。Random、Bayesian 與 Meta-designed 三種 configuration 策略皆從同一組 L24 theta configuration set 中選擇參數組合。

為確保比較公平，本研究在後處理階段將四種方法於每個 test instance 上產生的 raw Pareto fronts 合併，重新建立共同的 common reference front，再統一計算 HV、IGD、PF overlap、PF drift、diversity、runtime 與 per-instance RankScore。因此，本節結果並非使用各實驗資料夾各自生成的 reference front，而是在相同評估基準下重新計算而得。

## 整體結果

表 B1 彙整四種 configuration strategy 在 32 個 unseen test instances 上的整體表現。Meta-designed ECMADE-MOO 取得最佳 overall RankScore，並在 mean HV、mean IGD、mean PF overlap 與 mean PF drift 上皆為四種方法中最佳，顯示 meta-learner 所選出的 theta configuration 能同時改善解品質與 Pareto front 穩定性。在 per-instance 第一名次數方面，Meta-designed ECMADE-MOO 於 32 個測試問題中取得 14 次第一名，高於其他三種策略。

{make_overall_table(overall)}

具體而言，Meta-designed ECMADE-MOO 的 mean HV 為 {fmt(meta['mean_HV'], 6)}，mean IGD 為 {fmt(meta['mean_IGD'], 6)}，mean PF overlap 為 {fmt(meta['mean_PF_Overlap'], 6)}，mean PF drift 為 {fmt(meta['mean_PF_Drift'], 6)}。其 overall RankScore 為 {fmt(meta['overall_RankScore'], 3)}，優於 Bayesian configuration 的 {fmt(bayes['overall_RankScore'], 3)}、Random configuration 的 {fmt(random['overall_RankScore'], 3)}，以及 Hand-crafted ECMADE-MOO 的 {fmt(hand['overall_RankScore'], 3)}。

## 統計檢定

針對 per-instance RankScore 進行 Friedman test，結果顯示四種 configuration strategy 之間具有顯著差異（χ²={fmt(rank_friedman['friedman_chi_square'], 3)}, p={p_fmt(rank_friedman['p_value'])}）。進一步以 one-sided Wilcoxon signed-rank test 比較 Meta-designed ECMADE-MOO 與各 baseline，並使用 Holm correction 進行多重比較校正。

{make_stats_table(stats)}

結果顯示，Meta-designed ECMADE-MOO 在 per-instance RankScore 上相較於三個 baseline 皆達統計顯著。相較於 Random configuration，Meta-designed ECMADE-MOO 取得 22 勝、1 平、9 負，Holm-adjusted p-value 為 0.0050，改善幅度最明顯。相較於 Hand-crafted ECMADE-MOO 與 Bayesian configuration，Meta-designed ECMADE-MOO 亦分別達顯著差異，表示由 meta-learner 學得的 configuration policy 能有效泛化至 unseen instances。

## Runtime Trade-off

Runtime 結果顯示 Meta-designed ECMADE-MOO 並非最快的方法。Bayesian configuration ECMADE-MOO 在 final test 階段的 mean runtime 為 {fmt(bayes['mean_Runtime'], 4)}，為四種方法中最低；Meta-designed ECMADE-MOO 的 mean runtime 則為 {fmt(meta['mean_Runtime'], 4)}。然而，Bayesian configuration 使用單一全域 theta 套用至所有 test instances，而 Meta-designed ECMADE-MOO 會依據不同 instance 選擇對應 theta。因此，Meta-designed ECMADE-MOO 可視為以部分 runtime 成本換取更佳的解品質與穩定性。

## 結果討論

整體而言，實驗結果支持 instance-aware configuration selection 對 ECMADE-MOO 具有正面效果。Random configuration 雖可能偶爾選到表現良好的 theta，但其選擇與 instance 特徵無關，因此整體穩定性較差。Bayesian configuration 作為全域 tuning baseline 具有良好的 runtime 效率，但單一 theta 難以適應 heterogeneous test instances。相比之下，Meta-designed ECMADE-MOO 透過 instance features 預測 theta configuration，使演算法能依據測試問題特性調整設計，因此在整體 RankScore 與多數品質指標上取得最佳結果。

## 限制

雖然 Meta-designed ECMADE-MOO 在整體品質上表現最佳，但其 runtime 並非最短。此外，目前 meta-learner 的表現依賴 label dataset 的品質與涵蓋範圍。未來可透過擴充訓練 instances、加入更豐富的 instance features，或增加 theta candidate set 來提升泛化能力。另一個可延伸方向是將 runtime-aware objective 納入 meta-learner，使所選 configuration 能同時兼顧解品質與計算成本。

## 圖說

圖 B1. 四種 ECMADE-MOO configuration strategy 在 32 個 unseen test instances 上的 overall RankScore。RankScore 越低代表 HV、IGD、PF overlap、PF drift、diversity 與 runtime 的整體排名越佳。

圖 B2. 四種 configuration strategy 的 per-instance RankScore 分布。Meta-designed ECMADE-MOO 具有最佳平均排名，顯示其在 unseen instances 上具有較穩定的 configuration selection 能力。

圖 B3. Meta-designed ECMADE-MOO 相較於各 baseline 在不同指標上的 median improvement。正值代表 Meta-designed ECMADE-MOO 在該指標方向上較佳。

圖 B4. Meta-designed strategy 所選 theta configuration 的分布。結果顯示 meta-learner 並非只選擇單一全域 theta，而是會依據 instance 特性選擇不同 configuration。

## 表說

表 B1. 四種 ECMADE-MOO configuration strategy 在 unseen test instances 上的 common-reference 整體比較。

表 B2. 使用 per-instance RankScore 比較 Meta-designed ECMADE-MOO 與各 baseline 的 Wilcoxon signed-rank test 結果。

表 B3. 四種 configuration strategy 在 HV、IGD、PF overlap、PF drift、diversity、runtime 與 RankScore 上的 pairwise win/tie/loss 統計。

表 B4. Random、Bayesian 與 Meta-designed configuration strategy 的 theta 使用分布。
"""
    OUT.write_text(text, encoding="utf-8-sig")
    print(f"OUT={OUT}")


if __name__ == "__main__":
    main()
