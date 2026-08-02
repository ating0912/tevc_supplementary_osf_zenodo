from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "Experiment_C_no_replicate_selector_audit_report_zh_20260731.md"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def fmt(x, digits: int = 4) -> str:
    if pd.isna(x):
        return ""
    if isinstance(x, (int,)) or (isinstance(x, float) and float(x).is_integer() and abs(x) >= 10):
        return str(int(x))
    return f"{float(x):.{digits}f}"


def md_table(df: pd.DataFrame, columns: list[str], rename: dict[str, str] | None = None, digits: int = 4) -> str:
    rename = rename or {}
    view = df[columns].copy()
    for col in view.columns:
        if pd.api.types.is_numeric_dtype(view[col]):
            view[col] = view[col].map(lambda x: fmt(x, digits))
    view = view.rename(columns=rename)
    return view.to_markdown(index=False)


def rankscore_wilcoxon(path: Path, method: str) -> pd.DataFrame:
    df = read_csv(path)
    df = df[df["metric"].eq("RankScore")].copy()
    if "primary" in df.columns:
        return df[df["primary"].eq(method)]
    mask = df["method_a"].eq(method) | df["method_b"].eq(method)
    return df[mask]


def primary_wilcoxon(path: Path, method: str) -> pd.DataFrame:
    df = read_csv(path)
    if "primary" in df.columns:
        return df[df["primary"].eq(method)]
    return df[df["method_a"].eq(method) | df["method_b"].eq(method)]


def main() -> None:
    rep_dir = ROOT / "outputs" / "experiment_c_replicate_audit_20260730"
    fi_dir = ROOT / "outputs" / "experiment_c_feature_importance_20260725"
    main_dir = ROOT / "p0_lite_outputs" / "experiment_c_replicate_audit_final_test_20260730"
    formal_dir = ROOT / "p0_lite_outputs" / "experiment_c_formal_five_method_no_replicate_20260731"
    real_dir = ROOT / "p0_lite_outputs" / "p1_rolling_window_market_validation_20260719" / "configured_ecmade_no_replicate_audit_summary_20260731"
    mokp_dir = ROOT / "p0_lite_outputs" / "p1_mokp_config_comparison_no_replicate_audit_20260731"
    ext_dir = ROOT / "outputs" / "experiment_c_external_selector_dependency_audit_20260731"
    selector_ablation_dir = ROOT / "outputs" / "selector_level_ablation_20260728" / "final_test_analysis"
    cost_dir = ROOT / "outputs" / "experiment_c_cost_audit_20260801"
    table57_dir = ROOT / "outputs" / "experiment_c_table_5_7_holdout_20260802"

    compact = read_csv(rep_dir / "replicate_audit_final_compact.csv")
    ablation = read_csv(rep_dir / "feature_group_ablation_validation_summary.csv")
    theta_dist = read_csv(rep_dir / "theta_selection_distribution.csv")
    importance = read_csv(fi_dir / "feature_importance_combined_summary.csv")
    shap = read_csv(fi_dir / "shap_global_importance_grouped.csv")
    selector_metrics = read_csv(fi_dir / "selector_model_validation_metrics.csv")
    selector_ablation_overall = read_csv(selector_ablation_dir / "selector_ablation_overall_summary.csv")
    selector_ablation_completeness = read_csv(selector_ablation_dir / "selector_ablation_run_completeness.csv")
    selector_ablation_friedman = read_csv(selector_ablation_dir / "selector_ablation_friedman_tests.csv")
    selector_ablation_wil = read_csv(selector_ablation_dir / "selector_ablation_pairwise_wilcoxon_holm.csv")
    cost_summary = read_csv(cost_dir / "experiment_c_cost_audit_summary.csv")
    cost_env = json.loads((ROOT / "no_replicate_reproducibility_manifest_20260731.json").read_text(encoding="utf-8"))
    table57_formal = read_csv(table57_dir / "table_5_7_experiment_c_holdout_formal_five_methods.csv")
    table57_audit = read_csv(table57_dir / "table_5_7_experiment_c_holdout_replicate_audit_reference.csv")
    formal_friedman = read_csv(formal_dir / "formal_five_friedman_tests.csv")
    formal_primary_wil = read_csv(formal_dir / "formal_five_primary_method_wilcoxon_holm.csv")
    main_overall = read_csv(main_dir / "replicate_audit_overall_summary.csv")
    main_friedman = read_csv(main_dir / "replicate_audit_friedman_tests.csv")
    main_wil = rankscore_wilcoxon(main_dir / "replicate_audit_pairwise_wilcoxon_holm.csv", "ExperimentC_NoReplicate_ECMADE_MOO")
    main_swr_overall = read_csv(main_dir / "stability_weighted_rank_overall_summary.csv")
    main_swr_friedman = read_csv(main_dir / "stability_weighted_rank_friedman_test.csv")
    main_swr_wil = primary_wilcoxon(main_dir / "stability_weighted_rank_pairwise_wilcoxon_holm.csv", "ExperimentC_NoReplicate_ECMADE_MOO")
    external = read_csv(ext_dir / "external_selector_dependency_summary.csv")
    real_overall = read_csv(real_dir / "configured_overall_summary.csv")
    real_wil = rankscore_wilcoxon(real_dir / "configured_pairwise_wilcoxon_holm.csv", "ExperimentC_NoReplicate_ECMADE_MOO")
    real_swr_overall = read_csv(real_dir / "stability_weighted_rank_overall_summary.csv")
    real_swr_friedman = read_csv(real_dir / "stability_weighted_rank_friedman_test.csv")
    real_swr_wil = primary_wilcoxon(real_dir / "stability_weighted_rank_pairwise_wilcoxon_holm.csv", "ExperimentC_NoReplicate_ECMADE_MOO")
    real_usage = read_csv(real_dir / "configured_theta_usage_by_method.csv")
    mokp_overall = read_csv(mokp_dir / "overall_method_summary.csv")
    mokp_rank_friedman = read_csv(mokp_dir / "rankscore_friedman_test.csv")
    mokp_wil_all = read_csv(mokp_dir / "rankscore_pairwise_wilcoxon_holm.csv")
    mokp_swr_overall = read_csv(mokp_dir / "stability_weighted_rank_overall_summary.csv")
    mokp_swr_friedman = read_csv(mokp_dir / "stability_weighted_rank_friedman_test.csv")
    mokp_swr_wil = primary_wilcoxon(mokp_dir / "stability_weighted_rank_pairwise_wilcoxon_holm.csv", "ExperimentC_NoReplicate_ECMADE_MOO")
    mokp_wil = mokp_wil_all[
        mokp_wil_all["metric"].eq("RankScore")
        & (
            mokp_wil_all["method_a"].eq("ExperimentC_NoReplicate_ECMADE_MOO")
            | mokp_wil_all["method_b"].eq("ExperimentC_NoReplicate_ECMADE_MOO")
        )
    ].copy()
    mokp_usage = read_csv(ROOT / "p0_lite_outputs" / "experiment_c_no_replicate_external_assignments_20260731" / "mokp_no_replicate_assignment.csv")
    mokp_usage = mokp_usage.groupby(["theta_id"]).size().reset_index(name="instances")

    lines = [
        "# Experiment C no-replicate selector audit 中文數據報告",
        "",
        "日期：2026-07-31",
        "",
        "## 1. 結論摘要",
        "",
        "- Full Selector 已重新訓練為正式 no-replicate 版本；replicate-included 僅保留為 audit 對照。",
        "- Validation 上 no-replicate 與 replicate-included 表現接近：Top-1 相同，Top-3 小幅下降，RMSE/MAE 近似。",
        "- Final synthetic test 的正式主表已改為五方法 common-reference 與五方法 RankScore；replicate-included 僅保留為 audit reference，不納入正式排名。",
        "- 外部驗證不是只需改文字：real-market 33 組中 19 組 theta 會改，MOKP 18 組中 8 組 theta 會改，因此兩者已用 no-replicate selector 重新產生 assignments 並重跑。",
        "",
        "## 2. Selector validation 與 final test 對照",
        "",
        md_table(
            compact,
            [
                "variant",
                "top1_hit_rate",
                "top3_hit_rate",
                "mean_target_rank",
                "mean_C_regret",
                "rmse",
                "mae",
                "mean_PF_Overlap",
                "mean_PF_Drift",
                "test_overall_RankScore",
                "test_mean_RankScore",
                "test_mean_PF_Overlap",
                "test_mean_PF_Drift",
                "test_first_place_instances",
            ],
            {
                "variant": "版本",
                "top1_hit_rate": "Top-1",
                "top3_hit_rate": "Top-3",
                "mean_target_rank": "Mean rank",
                "mean_C_regret": "Regret",
                "rmse": "RMSE",
                "mae": "MAE",
                "mean_PF_Overlap": "Val PF Overlap",
                "mean_PF_Drift": "Val PF Drift",
                "test_overall_RankScore": "Test Overall J-score",
                "test_mean_RankScore": "Test mean J-score",
                "test_mean_PF_Overlap": "Test PF Overlap",
                "test_mean_PF_Drift": "Test PF Drift",
                "test_first_place_instances": "Test #1 instances",
            },
        ),
        "",
        "註：J-score 即 rank-based RankScore，越低越好。",
        "",
        "## 3. Selector model validation metrics",
        "",
        md_table(selector_metrics, ["split", "rows", "r2", "mae", "target"], {"split": "資料切分", "rows": "列數", "r2": "R2", "mae": "MAE", "target": "目標"}),
        "",
        "## 4. Feature importance：Permutation 與 Random Forest impurity",
        "",
        md_table(
            importance.head(10),
            ["feature", "permutation_importance_mean_r2_drop", "permutation_importance_std", "impurity_importance_sum", "transformed_terms"],
            {
                "feature": "特徵",
                "permutation_importance_mean_r2_drop": "Permutation R2 drop",
                "permutation_importance_std": "Permutation std",
                "impurity_importance_sum": "RF impurity importance",
                "transformed_terms": "轉換後項數",
            },
        ),
        "",
        "## 5. SHAP global importance",
        "",
        md_table(
            shap.head(10),
            ["base_feature", "mean_abs_shap_sum", "mean_shap_sum", "transformed_terms"],
            {
                "base_feature": "特徵",
                "mean_abs_shap_sum": "mean |SHAP|",
                "mean_shap_sum": "mean SHAP",
                "transformed_terms": "轉換後項數",
            },
        ),
        "",
        "SHAP 狀態：TreeExplainer 成功完成；validation rows=696，sample rows=200，transformed features=36。",
        "",
        "## 6. Feature-group ablation validation",
        "",
        md_table(
            ablation,
            ["variant", "top1_hit_rate", "top3_hit_rate", "mean_target_rank", "mean_C_regret", "rmse", "mae", "r2"],
            {
                "variant": "版本",
                "top1_hit_rate": "Top-1",
                "top3_hit_rate": "Top-3",
                "mean_target_rank": "Mean rank",
                "mean_C_regret": "Regret",
                "rmse": "RMSE",
                "mae": "MAE",
                "r2": "R2",
            },
        ),
        "",
        "## 7. Selector-level final-test ablation",
        "",
        "本段為補跑後的正式 selector-level final-test ablation；四個 variant 均在同一組 32 個 test instance 上重跑 30 次，不再只是 validation 層級比較。",
        "",
        md_table(
            selector_ablation_completeness,
            ["method", "instances", "runs"],
            {
                "method": "方法",
                "instances": "instances",
                "runs": "runs",
            },
        ),
        "",
        md_table(
            selector_ablation_overall,
            ["method", "instances", "mean_HV", "mean_IGD", "mean_PF_Overlap", "mean_PF_Drift", "mean_Diversity", "mean_Runtime", "mean_RankScore", "overall_RankScore", "first_place_instances"],
            {
                "method": "方法",
                "instances": "instances",
                "mean_HV": "HV",
                "mean_IGD": "IGD",
                "mean_PF_Overlap": "PF Overlap",
                "mean_PF_Drift": "PF Drift",
                "mean_Diversity": "Diversity",
                "mean_Runtime": "Runtime",
                "mean_RankScore": "Mean RankScore",
                "overall_RankScore": "Overall RankScore",
                "first_place_instances": "#1 instances",
            },
        ),
        "",
        "Selector-level ablation Friedman tests：",
        "",
        md_table(
            selector_ablation_friedman,
            ["metric", "n_paired_units", "friedman_chi_square", "p_value", "significant"],
            {
                "metric": "metric",
                "n_paired_units": "paired n",
                "friedman_chi_square": "chi-square",
                "p_value": "p",
                "significant": "sig.",
            },
        ),
        "",
        "以 FullSelector 為 primary 的 RankScore Wilcoxon-Holm：",
        "",
        md_table(
            selector_ablation_wil[selector_ablation_wil["metric"].eq("RankScore")],
            ["primary", "baseline", "n_paired_units", "median_signed_improvement", "wins", "ties", "losses", "raw_p_value", "holm_p_value", "significant_after_holm"],
            {
                "primary": "primary",
                "baseline": "baseline",
                "n_paired_units": "paired n",
                "median_signed_improvement": "median signed improvement",
                "wins": "wins",
                "ties": "ties",
                "losses": "losses",
                "raw_p_value": "p",
                "holm_p_value": "Holm p",
                "significant_after_holm": "sig.",
            },
        ),
        "",
        "解讀：此 selector-level ablation 是重新訓練並重新跑 optimizer 的結果，不是從表格刪除欄位。FullSelector 對三個 ablation baseline 的 RankScore 差異在 Holm correction 後皆未達 0.05 顯著；但 RandomizedLabels 與 NoThetaFeatures 在 overall RankScore 上可接近或優於 FullSelector，表示 final-test 層級的 selector 貢獻需謹慎解讀，正式主結論仍以 no-replicate selector 與外部驗證重跑為準。",
        "",
        "## 8. Final synthetic hold-out Test：正式五方法表",
        "",
        md_table(
            table57_formal,
            ["方法", "HV ↑", "IGD ↓", "PF Overlap ↑", "PF Drift ↓", "Diversity ↑", "Runtime ↓", "Mean RankScore ↓", "Overall RankScore ↓"],
            {"方法": "方法"},
        ),
        "",
        "註：本表正式排除 replicate-included audit；`Mean RankScore` 為五方法 instance-level rank 平均，`Overall RankScore` 為五方法整體均值指標排名平均。因此此表不可與六方法 audit RankScore 混用。",
        "",
        "### Replicate-included audit reference",
        "",
        md_table(
            table57_audit,
            ["方法", "HV ↑", "IGD ↓", "PF Overlap ↑", "PF Drift ↓", "Diversity ↑", "Runtime ↓", "Mean RankScore ↓ (six-method audit)", "Overall RankScore ↓ (six-method audit)"],
            {"方法": "方法"},
        ),
        "",
        "Replicate-included audit 僅用於檢查 generation index artifact；其 RankScore 是六方法 audit reference，不納入正式五方法 protocol 排名。",
        "",
        "Formal five-method Friedman tests：",
        "",
        md_table(
            formal_friedman[formal_friedman["endpoint"].isin(["InstanceRankScore", "RankBasedCompositeRank", "StabilityWeightedRank", "J_stability"])],
            ["endpoint", "paired_units", "methods", "friedman_chi_square", "p_value"],
            {"endpoint": "endpoint", "paired_units": "paired n", "methods": "methods", "friedman_chi_square": "chi-square", "p_value": "p"},
        ),
        "",
        "Formal five-method primary Wilcoxon-Holm：",
        "",
        md_table(
            formal_primary_wil[formal_primary_wil["endpoint"].isin(["InstanceRankScore", "StabilityWeightedRank", "J_stability"])],
            ["endpoint", "method_a", "method_b", "paired_units", "median_oriented_difference", "wins_a", "ties", "wins_b", "two_sided_p_value", "holm_two_sided_p_value", "significant_0_05"],
            {
                "endpoint": "endpoint",
                "method_a": "method A",
                "method_b": "method B",
                "paired_units": "paired n",
                "median_oriented_difference": "median signed diff",
                "wins_a": "A wins",
                "ties": "ties",
                "wins_b": "B wins",
                "two_sided_p_value": "p",
                "holm_two_sided_p_value": "Holm p",
                "significant_0_05": "sig.",
            },
        ),
        "",
        "### Six-method audit C-label StabilityWeightedRank endpoint",
        "",
        "定義：`StabilityWeightedRank = 0.2*rank_HV + 0.2*rank_IGD + 0.3*rank_PF_Overlap + 0.3*rank_PF_Drift`，越低越好；Wilcoxon 使用 paired instance，比較方向以 oriented difference 表示，正值代表 method A 優於 method B。",
        "",
        md_table(
            main_swr_overall,
            ["method", "paired_units", "mean_StabilityWeightedRank", "median_StabilityWeightedRank", "mean_StabilityWeightedInstanceRank", "first_place_units"],
            {
                "method": "方法",
                "paired_units": "paired units",
                "mean_StabilityWeightedRank": "Mean SWR",
                "median_StabilityWeightedRank": "Median SWR",
                "mean_StabilityWeightedInstanceRank": "Mean SW instance rank",
                "first_place_units": "#1 units",
            },
        ),
        "",
        "StabilityWeightedRank Friedman test：",
        "",
        md_table(main_swr_friedman, ["endpoint", "paired_units", "methods", "friedman_chi_square", "friedman_p_value"], {"endpoint": "endpoint", "paired_units": "paired n", "methods": "methods", "friedman_chi_square": "chi-square", "friedman_p_value": "p"}),
        "",
        "No-replicate StabilityWeightedRank Wilcoxon-Holm：",
        "",
        md_table(
            main_swr_wil,
            ["method_a", "method_b", "paired_units", "median_oriented_difference", "mean_oriented_difference", "wins_a", "ties", "wins_b", "p_value", "holm_p_value", "significant_0_05"],
            {
                "method_a": "method A",
                "method_b": "method B",
                "paired_units": "paired n",
                "median_oriented_difference": "median signed diff",
                "mean_oriented_difference": "mean signed diff",
                "wins_a": "A wins",
                "ties": "ties",
                "wins_b": "B wins",
                "p_value": "p",
                "holm_p_value": "Holm p",
                "significant_0_05": "sig.",
            },
        ),
        "",
        "## 9. Theta selection distribution",
        "",
        md_table(
            theta_dist[theta_dist["source"].isin(["test_assignment"])],
            ["variant", "theta_id", "count", "share"],
            {"variant": "版本", "theta_id": "theta", "count": "count", "share": "share"},
        ),
        "",
        "## 10. 外部驗證重跑判定",
        "",
        md_table(
            external,
            ["domain", "groups", "changed_no_replicate_vs_replicate_included", "changed_no_replicate_vs_old_used", "requires_external_rerun"],
            {
                "domain": "外部驗證",
                "groups": "groups",
                "changed_no_replicate_vs_replicate_included": "no-rep vs replicate-included 改變數",
                "changed_no_replicate_vs_old_used": "no-rep vs old-used 改變數",
                "requires_external_rerun": "需重跑",
            },
        ),
        "",
        "稽核結論：4.7/5.6 real-market 舊 protocol 將 window index 映成 replicate；4.8/5.7 MOKP 舊 transfer 將 replicate 固定為 1。兩者若載入舊 selector 都會使用 replicate，因此已改用 no-replicate selector 重新產生 theta assignments 並重跑。",
        "",
        "## 11. Real-market no-replicate rerun",
        "",
        md_table(
            real_overall,
            ["method", "windows", "mean_annual_net_return", "mean_sharpe", "mean_PF_Overlap", "mean_PF_Drift", "mean_Runtime", "mean_RankScore", "overall_RankScore", "first_place_windows"],
            {
                "method": "方法",
                "windows": "windows",
                "mean_annual_net_return": "annual net return",
                "mean_sharpe": "Sharpe",
                "mean_PF_Overlap": "PF Overlap",
                "mean_PF_Drift": "PF Drift",
                "mean_Runtime": "Runtime",
                "mean_RankScore": "Mean J-score",
                "overall_RankScore": "Overall J-score",
                "first_place_windows": "#1 windows",
            },
        ),
        "",
        "No-replicate RankScore Wilcoxon-Holm：",
        "",
        md_table(
            real_wil,
            ["baseline", "n_paired_units", "median_signed_improvement", "wins", "ties", "losses", "p_value", "holm_p_value", "significant_0_05"],
            {
                "baseline": "baseline",
                "n_paired_units": "paired n",
                "median_signed_improvement": "median signed improvement",
                "wins": "wins",
                "ties": "ties",
                "losses": "losses",
                "p_value": "p",
                "holm_p_value": "Holm p",
                "significant_0_05": "sig.",
            },
        ),
        "",
        "Real-market theta usage：",
        "",
        md_table(
            real_usage[real_usage["method"].isin(["ExperimentC_NoReplicate_ECMADE_MOO", "ExperimentC_StabilityAware_ECMADE_MOO"])],
            ["method", "theta_id", "windows"],
            {"method": "方法", "theta_id": "theta", "windows": "windows"},
        ),
        "",
        "Real-market StabilityWeightedRank endpoint：",
        "",
        md_table(
            real_swr_overall,
            ["method", "paired_units", "mean_StabilityWeightedRank", "median_StabilityWeightedRank", "mean_StabilityWeightedInstanceRank", "first_place_units"],
            {
                "method": "方法",
                "paired_units": "paired units",
                "mean_StabilityWeightedRank": "Mean SWR",
                "median_StabilityWeightedRank": "Median SWR",
                "mean_StabilityWeightedInstanceRank": "Mean SW window rank",
                "first_place_units": "#1 windows",
            },
        ),
        "",
        "Real-market StabilityWeightedRank Friedman test：",
        "",
        md_table(real_swr_friedman, ["endpoint", "paired_units", "methods", "friedman_chi_square", "friedman_p_value"], {"endpoint": "endpoint", "paired_units": "paired n", "methods": "methods", "friedman_chi_square": "chi-square", "friedman_p_value": "p"}),
        "",
        "No-replicate StabilityWeightedRank Wilcoxon-Holm：",
        "",
        md_table(
            real_swr_wil,
            ["method_a", "method_b", "paired_units", "median_oriented_difference", "mean_oriented_difference", "wins_a", "ties", "wins_b", "p_value", "holm_p_value", "significant_0_05"],
            {
                "method_a": "method A",
                "method_b": "method B",
                "paired_units": "paired n",
                "median_oriented_difference": "median signed diff",
                "mean_oriented_difference": "mean signed diff",
                "wins_a": "A wins",
                "ties": "ties",
                "wins_b": "B wins",
                "p_value": "p",
                "holm_p_value": "Holm p",
                "significant_0_05": "sig.",
            },
        ),
        "",
        "## 12. MOKP no-replicate rerun",
        "",
        md_table(
            mokp_overall,
            ["method", "instances", "runs", "mean_HV", "mean_IGD", "mean_PF_Overlap", "mean_PF_Drift", "mean_Runtime", "mean_RankScore", "overall_RankScore", "first_place_instances"],
            {
                "method": "方法",
                "instances": "instances",
                "runs": "runs",
                "mean_HV": "HV",
                "mean_IGD": "IGD",
                "mean_PF_Overlap": "PF Overlap",
                "mean_PF_Drift": "PF Drift",
                "mean_Runtime": "Runtime",
                "mean_RankScore": "Mean J-score",
                "overall_RankScore": "Overall J-score",
                "first_place_instances": "#1 instances",
            },
        ),
        "",
        "No-replicate RankScore Wilcoxon-Holm：",
        "",
        "RankScore Friedman test：",
        "",
        md_table(mokp_rank_friedman, ["metric", "instances", "methods", "friedman_chi_square", "friedman_p_value"], {"metric": "metric", "instances": "instances", "methods": "methods", "friedman_chi_square": "chi-square", "friedman_p_value": "p"}),
        "",
        md_table(
            mokp_wil,
            ["method_a", "method_b", "instances", "median_oriented_difference", "mean_oriented_difference", "wins_a", "ties", "wins_b", "signed_rank_effect", "p_value", "holm_p_value", "significant_0_05"],
            {
                "method_a": "method A",
                "method_b": "method B",
                "instances": "paired n",
                "median_oriented_difference": "median signed diff",
                "mean_oriented_difference": "mean signed diff",
                "wins_a": "A wins",
                "ties": "ties",
                "wins_b": "B wins",
                "signed_rank_effect": "signed-rank effect",
                "p_value": "p",
                "holm_p_value": "Holm p",
                "significant_0_05": "sig.",
            },
        ),
        "",
        "MOKP no-replicate theta usage：",
        "",
        md_table(mokp_usage, ["theta_id", "instances"], {"theta_id": "theta", "instances": "instances"}),
        "",
        "MOKP StabilityWeightedRank endpoint：",
        "",
        md_table(
            mokp_swr_overall,
            ["method", "paired_units", "mean_StabilityWeightedRank", "median_StabilityWeightedRank", "mean_StabilityWeightedInstanceRank", "first_place_units"],
            {
                "method": "方法",
                "paired_units": "paired units",
                "mean_StabilityWeightedRank": "Mean SWR",
                "median_StabilityWeightedRank": "Median SWR",
                "mean_StabilityWeightedInstanceRank": "Mean SW instance rank",
                "first_place_units": "#1 instances",
            },
        ),
        "",
        "MOKP StabilityWeightedRank Friedman test：",
        "",
        md_table(mokp_swr_friedman, ["endpoint", "paired_units", "methods", "friedman_chi_square", "friedman_p_value"], {"endpoint": "endpoint", "paired_units": "paired n", "methods": "methods", "friedman_chi_square": "chi-square", "friedman_p_value": "p"}),
        "",
        "No-replicate StabilityWeightedRank Wilcoxon-Holm：",
        "",
        md_table(
            mokp_swr_wil,
            ["method_a", "method_b", "paired_units", "median_oriented_difference", "mean_oriented_difference", "wins_a", "ties", "wins_b", "p_value", "holm_p_value", "significant_0_05"],
            {
                "method_a": "method A",
                "method_b": "method B",
                "paired_units": "paired n",
                "median_oriented_difference": "median signed diff",
                "mean_oriented_difference": "mean signed diff",
                "wins_a": "A wins",
                "ties": "ties",
                "wins_b": "B wins",
                "p_value": "p",
                "holm_p_value": "Holm p",
                "significant_0_05": "sig.",
            },
        ),
        "",
        "## 13. Configuration cost 與 meta-training cost",
        "",
        "下表補齊第 6.4 節原本只以限制說明帶過的離線成本。Optimizer 類成本使用歷史 `Runtime` 欄位加總，因此代表各 run 內部記錄的演算法執行時間總和，不等同於原始 MATLAB batch 的外部 wall-clock。Python 類成本原本沒有歷史 wall-clock log，已於 2026-08-01 在同一 workspace 重新量測。",
        "",
        md_table(
            cost_summary,
            ["stage", "execution_count", "total_hms", "total_minutes", "average_seconds", "average_unit", "environment", "cost_record_status"],
            {
                "stage": "階段",
                "execution_count": "執行次數",
                "total_hms": "總時間",
                "total_minutes": "總分鐘",
                "average_seconds": "平均秒數",
                "average_unit": "平均單位",
                "environment": "執行環境",
                "cost_record_status": "紀錄狀態",
            },
        ),
        "",
        "重點數字：Training label generation 為 134 groups × 24 theta × 30 runs，歷史 Runtime 加總 109:32:25.55；正式 no-replicate final optimization 為 32 test groups × 30 runs，歷史 Runtime 加總 00:54:20.71；theta recommendation 重新量測為 13.23 秒，平均每個 test group 0.413 秒；post-processing 與 common-reference 計算重新量測為 00:07:39.46。",
        "",
        "硬體與軟體環境：Windows 11，CPU 顯示為 Intel64 Family 6 Model 186 Stepping 2，邏輯核心數 20；Python executable 為 `C:\\Users\\yiting\\miniconda3\\python.exe`，Python 3.13.12，pandas 2.3.3，scikit-learn 1.8.0，scipy 1.16.3，shap 0.52.0。MATLAB/PlatEMO 使用本 workspace 內 `PlatEMO_v2.9.0\\PlatEMO` 與 `PlatEMO_v4.3`；manifest 中 MATLAB version command 未成功回傳，因此版本號仍標為 unavailable。",
        "",
        "仍未找到完整歷史紀錄的項目：原始 MATLAB label-generation batch 的外部 wall-clock、feature preprocessing / selector training / theta recommendation / post-processing 的原始執行 wall-clock。這些 Python 項目已用同一資料與同一機器重新量測補足；MATLAB optimizer 項目則使用每個 run 的歷史 Runtime 欄位作為可回溯成本。",
        "",
        "## 14. 輸出檔案",
        "",
        f"- Feature importance 圖：`{fi_dir / 'feature_importance_grouped_no_replicate.png'}`",
        f"- 主測試 Wilcoxon：`{main_dir / 'replicate_audit_pairwise_wilcoxon_holm.csv'}`",
        f"- Selector-level ablation：`{selector_ablation_dir / 'selector_ablation_overall_summary.csv'}`",
        f"- Configuration/meta-training cost：`{cost_dir / 'experiment_c_cost_audit_summary.csv'}`",
        f"- 主測試 StabilityWeightedRank Wilcoxon：`{main_dir / 'stability_weighted_rank_pairwise_wilcoxon_holm.csv'}`",
        f"- real-market no-replicate summary：`{real_dir}`",
        f"- real-market StabilityWeightedRank Wilcoxon：`{real_dir / 'stability_weighted_rank_pairwise_wilcoxon_holm.csv'}`",
        f"- MOKP no-replicate summary：`{mokp_dir}`",
        f"- MOKP StabilityWeightedRank Wilcoxon：`{mokp_dir / 'stability_weighted_rank_pairwise_wilcoxon_holm.csv'}`",
    ]

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"WROTE={REPORT}")


if __name__ == "__main__":
    main()
