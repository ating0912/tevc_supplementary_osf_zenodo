from __future__ import annotations

import sys
from pathlib import Path


SKILL_DIR = Path(
    r"C:\Users\yiting\.codex\plugins\cache\openai-primary-runtime\documents\26.715.12143\skills\documents"
)
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from comments_add import add_comments  # noqa: E402


INPUT_DOCX = Path(
    r"C:\Users\yiting\Desktop\NCHU\lab\TEVC\陳羿婷_TEVC第二SI_中文投稿母稿_紅字待補_20260723.docx"
)
OUTPUT_DOCX = Path(
    r"C:\Users\yiting\Documents\Playground\陳羿婷_TEVC第二SI_中文投稿母稿_紅字待補_20260723_數據標註.docx"
)


COMMENTS = [
    (
        "【尚待加強｜real-market validation】",
        "P1 已補數據，放在此處與 4.1：Table S8 real-market rolling-window validation、Table S9 CVaR(95%)、Table S10 10/20/50 bps transaction-cost sensitivity。重點寫法：ECMADE_MOO 在 CVaR95 loss 排第 1，但 annual after-cost return 不是最佳，不能寫全面勝出。",
    ),
    (
        "【尚待加強｜數學式】",
        "這裡不是數據缺口，需補方法公式：objective functions、risk definition、return estimation、weight bounds、repair operator、feasible-first / constraint violation handling。可放在 Method，不要用 P0/P1 結果表替代。",
    ),
    (
        "【尚待加強｜演算法細節】",
        "這裡不是數據缺口，需補 pseudo-code 與流程：Algorithm 1 ECMADE-MOO、Algorithm 2 theta selection、Algorithm 3 stability-aware label generation。可引用 P0 的 theta table 與 label protocol，但主要要補演算法描述。",
    ),
    (
        "【尚待加強｜theta 表】",
        "P0 已補數據，放 Table S1：24/L24 theta configuration table。輸出檔：p0_lite_outputs/theta_configuration_paper_table_20260723/theta_configuration_table_for_paper.csv。文字重點：selector 實際選 S、operator、migration、elite ratio、stagnation threshold。",
    ),
    (
        "【尚待加強｜feature importance】",
        "P0 已補數據，放 Table S4/S5：feature importance 與 Experiment C selector validation。輸出檔：p0_lite_outputs/experiment_c_stability_selector_training/feature_importance.csv、validation_selector_summary.csv。注意 top1/top3 hit rate = 0，文字要寫 stability-aware trade-off，不可寫精準重建 Oracle。",
    ),
    (
        "【尚待加強｜label protocol】",
        "P0 已補可寫資料：selector training rows = 3216、validation rows = 696、theta candidates = 24；Experiment C training label generation 約 96,480 optimizer runs，validation 約 20,880 runs。放在 label protocol / reproducibility / cost 小節。",
    ),
    (
        "【尚待加強｜統一命名】",
        "P0 已補文字與表格，放 Table S3：統一用 RankScore / C_LabelScore / C_ThetaRank。C_LabelScore = -0.2 rank_HV - 0.2 rank_IGD - 0.3 rank_PF_Overlap - 0.3 rank_PF_Drift；rank 在同一 instance-K group 內計算，ties 用 average rank。",
    ),
    (
        "4.1 Real-market validation 補強設計",
        "本節放 P1 real-market validation 三張表：Table S8 rolling-window performance、Table S9 CVaR95 downside risk、Table S10 transaction-cost sensitivity。請在段落中明確寫：此為 robustness / limitation evidence，不是 ECMADE_MOO 全面報酬勝出證據。",
    ),
    (
        "【尚待加強｜real-market validation 執行】",
        "P1 已補數據：33 rolling windows；annual net return、Sharpe、Sortino、MDD、turnover、runtime 已在 summary/method_overall_summary.csv；CVaR95 與 10/20/50 bps sensitivity 已在 cvar_sensitivity/。可直接填此段。",
    ),
    (
        "【尚待加強｜一致性】",
        "需補 A/B/C 公平設定文字，不是新數據表。建議在 Method 補：paired by split-instance-K、common reference front、normalization scope、seed/runs/maxFE/N、constraint handling。統計檔已支援 paired instance-level tests。",
    ),
    (
        "【尚待加強｜統計檢定】",
        "P0 已補數據，放 Table S2：Experiment C Friedman tests；pairwise Wilcoxon + Holm 在 p0_lite_outputs/tevc_p0_statistical_tests_20260718/unified_pairwise_wilcoxon.csv。文字寫 primary endpoint / Holm-corrected paired evidence。",
    ),
    (
        "【尚待加強｜非金融泛化】",
        "P1 已補數據，放 Table S7：MOKP non-financial constrained/combinatorial test bed。18 instances，每方法 540 runs；ECMADE_MOO overall RankScore = 2.000，first-place instances = 13/18。",
    ),
    (
        "【尚待加強｜結論語氣】",
        "依已補數據修正結論：P0 可寫 selector 具可解釋特徵與 stability-aware trade-off；P1 可寫 MOKP 泛化成立、real-market CVaR95 較穩；不可寫 selector 精準重建 Oracle，也不可寫 real-market return 全面勝出。",
    ),
    (
        "【尚待加強｜可重現性 package】",
        "需整理 supplementary package，不是單一新數據。建議列入：code、README、environment.yml、MATLAB/PlatEMO version、CPU/GPU/OS、run logs、tables、figures、raw PF csv。P0/P1 新輸出路徑可引用 Playground 下 p0_lite_outputs。",
    ),
    (
        "補完整 theta configuration table 與 theta encoding",
        "P0 已補，對應 Table S1。請把 p0_lite_outputs/theta_configuration_paper_table_20260723/theta_configuration_table_for_paper.csv 轉成 SI 表格；正文簡述 theta encoding 的 5 個因子。",
    ),
    (
        "補 Experiment C 的 Holm correction 或 primary endpoint paired test",
        "P0 已補，對應 Table S2 與 unified_pairwise_wilcoxon.csv。放在 Experiment C 統計檢定段落。",
    ),
    (
        "補 meta-feature 清單與 feature importance",
        "P0 已補，對應 Table S4/S5。請放 feature importance 前 10 名與 selector validation summary。",
    ),
    (
        "統一 OverallRankScore / RankScore / J-score 名稱與公式",
        "P0 已補，對應 Table S3。建議正文統一使用 RankScore 與 C_LabelScore，避免再混用 OverallRankScore/J-score。",
    ),
    (
        "補非金融 constrained test bed",
        "P1 已補，對應 Table S7 MOKP。可寫：18 non-financial MOKP instances，每方法 540 runs，ECMADE_MOO overall RankScore 第 1。",
    ),
    (
        "補 configuration cost 與 meta-training cost",
        "P1/P0 已補，對應 Table S6 cost/runtime。請分開 offline label-generation cost 與 online final optimization runtime。",
    ),
    (
        "補論文圖表與視覺化",
        "目前已補表格數據，但仍需決定圖：建議至少放 theta selection distribution、MOKP method ranking、real-market wealth/return-risk summary、CVaR95 或 cost sensitivity bar chart。",
    ),
    (
        "補 2024–2026 最新文獻",
        "這裡不是數據缺口，需補文獻與 Reference QC。主題：automated EA design、MetaBBO、RL/operator selection、constrained MOEA。",
    ),
    (
        "【Reference QC 待辦】",
        "這裡不是實驗數據缺口。需逐筆補 DOI、卷期頁碼、IEEE TEVC style；[7]、[9]、[10]、[38]、[39] 若已有正式出版版要替換；[42] 確認卷期、頁碼與 DOI。",
    ),
]


def main() -> None:
    add_comments(
        str(INPUT_DOCX),
        str(OUTPUT_DOCX),
        COMMENTS,
        author="Codex data mapping",
        ignore_case=False,
        require_all=True,
    )
    print(OUTPUT_DOCX)


if __name__ == "__main__":
    main()
