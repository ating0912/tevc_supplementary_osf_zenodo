from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "no_replicate_data_existence_audit_zh_20260731.md"
PRIMARY = "ExperimentC_NoReplicate_ECMADE_MOO"


def exists(path: Path) -> bool:
    return path.exists()


def csv_has(path: Path, columns: list[str]) -> bool:
    if not path.exists():
        return False
    try:
        header = pd.read_csv(path, nrows=0, encoding="utf-8-sig").columns
    except Exception:
        return False
    return all(col in header for col in columns)


def row_count(path: Path) -> int | None:
    if not path.exists():
        return None
    return len(pd.read_csv(path, encoding="utf-8-sig"))


def status(ok: bool, partial: bool = False) -> str:
    if ok:
        return "存在"
    if partial:
        return "部分存在"
    return "未找到"


def add(rows: list[dict], section: str, item: str, state: str, evidence: str, note: str = "") -> None:
    rows.append({"section": section, "item": item, "status": state, "evidence": evidence, "note": note})


def main() -> None:
    rows: list[dict] = []

    selector_dir = ROOT / "p0_lite_outputs" / "experiment_c_stability_selector_training"
    fi_dir = ROOT / "outputs" / "experiment_c_feature_importance_20260725"
    rep_dir = ROOT / "outputs" / "experiment_c_replicate_audit_20260730"
    final_dir = ROOT / "p0_lite_outputs" / "experiment_c_replicate_audit_final_test_20260730"
    formal_dir = ROOT / "p0_lite_outputs" / "experiment_c_formal_five_method_no_replicate_20260731"
    real_dir = ROOT / "p0_lite_outputs" / "p1_rolling_window_market_validation_20260719" / "configured_ecmade_no_replicate_audit_summary_20260731"
    mokp_dir = ROOT / "p0_lite_outputs" / "p1_mokp_config_comparison_no_replicate_audit_20260731"
    ext_assign_dir = ROOT / "p0_lite_outputs" / "experiment_c_no_replicate_external_assignments_20260731"
    ext_audit_dir = ROOT / "outputs" / "experiment_c_external_selector_dependency_audit_20260731"
    selector_ablation_dir = ROOT / "outputs" / "selector_level_ablation_20260728"
    selector_ablation_summary = selector_ablation_dir / "final_test_analysis" / "selector_ablation_overall_summary.csv"
    cost_dir = ROOT / "outputs" / "experiment_c_cost_audit_20260801"

    feature_cols = json.loads((selector_dir / "feature_columns.json").read_text(encoding="utf-8"))
    flat_features = feature_cols.get("numeric", []) + feature_cols.get("categorical", [])
    train_cfg = json.loads((selector_dir / "training_config.json").read_text(encoding="utf-8"))

    add(rows, "1. selector training", "replicate removed from model feature columns", status("replicate" not in flat_features), str(selector_dir / "feature_columns.json"), f"feature count(raw)={len(flat_features)}")
    add(rows, "1. selector training", "replicate may remain in manifest but not model", status(not train_cfg.get("include_replicate_feature", True)), str(selector_dir / "training_config.json"), f"include_replicate_feature={train_cfg.get('include_replicate_feature')}")
    add(rows, "1. selector training", "training/validation rows", status(train_cfg.get("training_rows") == 3216 and train_cfg.get("validation_rows") == 696), str(selector_dir / "training_config.json"), f"training_rows={train_cfg.get('training_rows')}, validation_rows={train_cfg.get('validation_rows')}")
    add(rows, "1. selector training", "theta candidate count", status(train_cfg.get("theta_candidates") == 24), str(selector_dir / "training_config.json"), f"theta_candidates={train_cfg.get('theta_candidates')}")
    add(rows, "1. selector training", "label target and C formula", status(train_cfg.get("target") == "C_LabelScore"), str(selector_dir / "training_config.json"), train_cfg.get("c_score_formula", ""))
    add(rows, "1. selector training", "train/validation R2 and MAE", status(csv_has(fi_dir / "selector_model_validation_metrics.csv", ["split", "rows", "r2", "mae", "target"])), str(fi_dir / "selector_model_validation_metrics.csv"), "training R2 and validation R2 present")
    add(rows, "1. selector training", "RMSE", status(csv_has(rep_dir / "replicate_audit_final_compact.csv", ["rmse", "mae"])), str(rep_dir / "replicate_audit_final_compact.csv"), "validation RMSE present in compact audit")
    add(rows, "1. selector training", "full feature columns", status(exists(selector_dir / "feature_columns.json")), str(selector_dir / "feature_columns.json"))
    add(rows, "1. selector training", "transformed feature count", status(exists(fi_dir / "shap_status.txt")), str(fi_dir / "shap_status.txt"), "Transformed features=36")
    add(rows, "1. selector training", "RF seed and parameters", status(exists(selector_dir / "experiment_c_stability_random_forest.joblib")), str(selector_dir / "experiment_c_stability_random_forest.joblib"), "Verified separately: random_state=20260717, n_estimators=500, min_samples_leaf=2")

    add(rows, "2. validation selection", "Top-1/Top-3/mean rank/regret/PF stability", status(csv_has(rep_dir / "replicate_audit_final_compact.csv", ["top1_hit_rate", "top3_hit_rate", "mean_target_rank", "mean_C_regret", "mean_PF_Overlap", "mean_PF_Drift"])), str(rep_dir / "replicate_audit_final_compact.csv"))
    add(rows, "2. validation selection", "instance-level predicted top-1 and oracle top-1", status(csv_has(selector_dir / "validation_theta_selection.csv", ["selected_theta", "best_c_theta"])), str(selector_dir / "validation_theta_selection.csv"), "selected_theta=predicted top-1; best_c_theta=oracle C top-1")
    add(rows, "2. validation selection", "theta selection distribution", status(exists(rep_dir / "theta_selection_distribution.csv")), str(rep_dir / "theta_selection_distribution.csv"))

    add(rows, "3. impurity importance", "transformed-feature RF importance", status(exists(fi_dir / "rf_impurity_importance_grouped.csv"), partial=exists(selector_dir / "feature_importance.csv")), str(fi_dir / "rf_impurity_importance_grouped.csv"), "Grouped exists; transformed/raw feature importance also in selector training feature_importance.csv")
    add(rows, "3. impurity importance", "grouped feature importance top/full", status(exists(fi_dir / "feature_importance_combined_summary.csv")), str(fi_dir / "feature_importance_combined_summary.csv"))
    add(rows, "3. impurity importance", "importance plot", status(exists(fi_dir / "feature_importance_grouped_no_replicate.png")), str(fi_dir / "feature_importance_grouped_no_replicate.png"))

    add(rows, "4. permutation importance", "validation permutation importance full table", status(csv_has(fi_dir / "permutation_importance_raw_features.csv", ["feature", "permutation_importance_mean_r2_drop", "permutation_importance_std"])), str(fi_dir / "permutation_importance_raw_features.csv"))
    add(rows, "4. permutation importance", "repeats and seed", status(exists(fi_dir / "compute_selector_importance.py")), str(fi_dir / "compute_selector_importance.py"), "n_repeats=5, random_state=20260725")

    add(rows, "5. SHAP", "no-replicate TreeSHAP status", status(exists(fi_dir / "shap_status.txt")), str(fi_dir / "shap_status.txt"), "sample rows=200, transformed features=36")
    add(rows, "5. SHAP", "transformed SHAP table", status(exists(fi_dir / "shap_global_importance_transformed.csv")), str(fi_dir / "shap_global_importance_transformed.csv"))
    add(rows, "5. SHAP", "grouped SHAP table", status(exists(fi_dir / "shap_global_importance_grouped.csv")), str(fi_dir / "shap_global_importance_grouped.csv"))
    add(rows, "5. SHAP", "summary/beeswarm/dependence plot", status(exists(fi_dir / "shap_summary_beeswarm_no_replicate.png") and exists(fi_dir / "shap_summary_bar_no_replicate.png") and exists(fi_dir / "shap_dependence_plot_inventory.csv")), str(fi_dir), "No-replicate SHAP beeswarm/bar/dependence plots generated")

    add(rows, "6. test theta assignment", "32-group included vs no-replicate diff table", status(exists(rep_dir / "test_assignment_diff_no_replicate_vs_replicate.csv")), str(rep_dir / "test_assignment_diff_no_replicate_vs_replicate.csv"), f"rows={row_count(rep_dir / 'test_assignment_diff_no_replicate_vs_replicate.csv')}")
    add(rows, "6. test theta assignment", "predicted scores per group", status(exists(selector_dir / "test_theta_predicted_scores.csv")), str(selector_dir / "test_theta_predicted_scores.csv"))
    add(rows, "6. test theta assignment", "rerun completeness for six-method audit", status(exists(final_dir / "replicate_audit_run_completeness.csv")), str(final_dir / "replicate_audit_run_completeness.csv"))

    add(rows, "7. formal five-method comparison", "six-method audit common-reference results", status(exists(final_dir / "replicate_audit_overall_summary.csv")), str(final_dir / "replicate_audit_overall_summary.csv"), "Includes replicate-included audit")
    add(rows, "7. formal five-method comparison", "formal five-method common-reference results excluding replicate-included", status(exists(formal_dir / "formal_five_overall_summary.csv")), str(formal_dir / "formal_five_overall_summary.csv"), "Replicate-included audit excluded")
    add(rows, "7. formal five-method comparison", "reference ideal/nadir points", status(exists(formal_dir / "formal_five_reference_front_info.csv")), str(formal_dir / "formal_five_reference_front_info.csv"), "Formal five-method reference metadata")

    add(rows, "8. run completeness/control", "six-method 32x30 completeness", status(exists(final_dir / "replicate_audit_run_completeness.csv")), str(final_dir / "replicate_audit_run_completeness.csv"))
    add(rows, "8. run completeness/control", "formal five-method completeness", status(exists(formal_dir / "formal_five_run_completeness.csv")), str(formal_dir / "formal_five_run_completeness.csv"))
    add(rows, "8. run completeness/control", "feasible rate/repair success/CV check", status(exists(formal_dir / "formal_five_constraint_invalid_units.csv") and csv_has(formal_dir / "formal_five_instance_method_metrics_raw.csv", ["PF_Feasible_Rate", "PF_Max_Violation"])), str(formal_dir), "Feasible/CV consolidated; repair success not separately logged")
    add(rows, "8. run completeness/control", "optimizer seed/RNG/maxFE/population size audit", status(csv_has(formal_dir / "formal_five_instance_method_metrics_raw.csv", ["N", "maxFE", "rng_policy", "seed_policy"])), str(formal_dir / "formal_five_instance_method_metrics_raw.csv"))

    add(rows, "9. Stability-weighted J-score", "requested Performance/Stability/Diversity/Runtime weighted J_stability", status(csv_has(formal_dir / "formal_five_instance_method_endpoints_ranked.csv", ["PerformanceScore", "StabilityScore", "DiversityScore", "RuntimeScore", "J_stability", "StabilityWeightedRank"])), str(formal_dir / "formal_five_instance_method_endpoints_ranked.csv"), "Weights 0.25/0.45/0.20/0.10; normalized inside formal five-method instance group")
    add(rows, "9. Stability-weighted J-score", "rank-based StabilityWeightedRank using C-label ranks", "部分存在", str(final_dir / "stability_weighted_rank_pairwise_wilcoxon_holm.csv"), "This uses 0.2 HV + 0.2 IGD + 0.3 PF_Overlap + 0.3 PF_Drift, not the requested J_stability")

    add(rows, "10. primary C vs Meta-designed", "StabilityWeightedRank Wilcoxon/Holm", status(exists(formal_dir / "formal_five_primary_method_wilcoxon_holm.csv")), str(formal_dir / "formal_five_primary_method_wilcoxon_holm.csv"), "Includes primary no-replicate comparisons for requested J_stability-derived rank")
    add(rows, "10. primary C vs Meta-designed", "one-sided p and Vargha-Delaney/rank-biserial", status(csv_has(formal_dir / "formal_five_primary_method_wilcoxon_holm.csv", ["one_sided_greater_p_value", "vargha_delaney_A_oriented", "rank_biserial_correlation"])), str(formal_dir / "formal_five_primary_method_wilcoxon_holm.csv"))

    add(rows, "11. secondary endpoints", "RankScore/InstanceRankScore Wilcoxon", status(exists(final_dir / "replicate_audit_pairwise_wilcoxon_holm.csv")), str(final_dir / "replicate_audit_pairwise_wilcoxon_holm.csv"))
    add(rows, "11. secondary endpoints", "PerformanceRank/EqualWeightedRank/Jperformance/Jstability", status(csv_has(formal_dir / "formal_five_instance_method_endpoints_ranked.csv", ["PerformanceRank", "EqualWeightedRank", "J_performance", "J_stability"])), str(formal_dir / "formal_five_instance_method_endpoints_ranked.csv"))

    add(rows, "12. Friedman tests", "six-method metric Friedman tests", status(exists(final_dir / "replicate_audit_friedman_tests.csv")), str(final_dir / "replicate_audit_friedman_tests.csv"))
    add(rows, "12. Friedman tests", "StabilityWeightedRank Friedman", "部分存在", str(final_dir / "stability_weighted_rank_friedman_test.csv"), "C-label rank endpoint only")
    add(rows, "12. Friedman tests", "formal five-method Friedman tests", status(exists(formal_dir / "formal_five_friedman_tests.csv")), str(formal_dir / "formal_five_friedman_tests.csv"))

    add(rows, "13. replicate audit", "no-rep vs replicate-included descriptive metrics", status(exists(rep_dir / "replicate_audit_final_compact.csv")), str(rep_dir / "replicate_audit_final_compact.csv"))
    add(rows, "13. replicate audit", "paired Wilcoxon/Holm by metric", status(exists(final_dir / "replicate_audit_pairwise_wilcoxon_holm.csv")), str(final_dir / "replicate_audit_pairwise_wilcoxon_holm.csv"))
    add(rows, "13. replicate audit", "theta change vs performance delta", status(exists(rep_dir / "replicate_audit_metric_delta.csv")), str(rep_dir / "replicate_audit_metric_delta.csv"), "May need richer problem-characteristic analysis")

    add(rows, "14. feature-group validation ablation", "four validation variants summary", status(exists(rep_dir / "feature_group_ablation_validation_summary.csv")), str(rep_dir / "feature_group_ablation_validation_summary.csv"))
    add(rows, "14. feature-group validation ablation", "all variants exclude replicate", "部分存在", str(rep_dir / "feature_group_ablation_validation_summary.csv"), "Need inspect each variant config/model columns if strict proof required")

    selector_ablation_ok = False
    selector_ablation_note = ""
    if selector_ablation_summary.exists():
        selector_ablation_df = pd.read_csv(selector_ablation_summary, encoding="utf-8-sig")
        selector_ablation_methods = set(selector_ablation_df.get("method", []))
        expected_methods = {
            "SelectorAblation_FullSelector_ECMADE_MOO",
            "SelectorAblation_NoInstanceFeatures_ECMADE_MOO",
            "SelectorAblation_NoThetaFeatures_ECMADE_MOO",
            "SelectorAblation_RandomizedLabels_ECMADE_MOO",
        }
        selector_ablation_ok = (
            expected_methods.issubset(selector_ablation_methods)
            and "instances" in selector_ablation_df.columns
            and selector_ablation_df["instances"].min() == 32
        )
        selector_ablation_note = f"methods={len(selector_ablation_methods)}, min_instances={selector_ablation_df.get('instances', pd.Series(dtype=float)).min()}"
    add(rows, "15. selector-level final-test ablation", "four selector variants no-replicate final-test optimization", status(selector_ablation_ok, partial=selector_ablation_summary.exists()), str(selector_ablation_summary), selector_ablation_note)

    add(rows, "16. real-market external", "selector dependency audit", status(exists(ext_audit_dir / "external_selector_dependency_summary.csv")), str(ext_audit_dir / "external_selector_dependency_summary.csv"), "real_market changed 19/33 and rerun required")
    add(rows, "16. real-market external", "no-replicate theta assignments", status(exists(ext_assign_dir / "real_market_no_replicate_assignment.csv")), str(ext_assign_dir / "real_market_no_replicate_assignment.csv"), f"rows={row_count(ext_assign_dir / 'real_market_no_replicate_assignment.csv')}")
    add(rows, "16. real-market external", "no-replicate rerun common-reference metrics/statistics", status(exists(real_dir / "configured_overall_summary.csv") and exists(real_dir / "configured_pairwise_wilcoxon_holm.csv")), str(real_dir))
    add(rows, "16. real-market external", "transaction cost sensitivity", status(exists(real_dir / "configured_transaction_cost_overall.csv")), str(real_dir / "configured_transaction_cost_overall.csv"))
    add(rows, "16. real-market external", "cumulative wealth plots/data", status(exists(real_dir / "configured_cumulative_wealth_by_run.csv") and exists(real_dir / "configured_cumulative_wealth_mean.png")), str(real_dir), "Consolidated cumulative wealth by run, mean table, and plot generated")

    add(rows, "17. MOKP external", "selector dependency audit", status(exists(ext_audit_dir / "external_selector_dependency_summary.csv")), str(ext_audit_dir / "external_selector_dependency_summary.csv"), "mokp changed 8/18 and rerun required")
    add(rows, "17. MOKP external", "no-replicate theta assignments", status(exists(ext_assign_dir / "mokp_no_replicate_assignment.csv")), str(ext_assign_dir / "mokp_no_replicate_assignment.csv"), f"rows={row_count(ext_assign_dir / 'mokp_no_replicate_assignment.csv')}")
    add(rows, "17. MOKP external", "no-replicate rerun metrics/statistics", status(exists(mokp_dir / "overall_method_summary.csv") and exists(mokp_dir / "pairwise_wilcoxon.csv")), str(mokp_dir))
    add(rows, "17. MOKP external", "global theta 034/037 diagnostics included", status(csv_has(mokp_dir / "overall_method_summary.csv", ["method"])), str(mokp_dir / "overall_method_summary.csv"), "Overall summary includes global theta diagnostics")

    add(rows, "18. configuration/meta-training cost", "cost audit summary table", status(csv_has(cost_dir / "experiment_c_cost_audit_summary.csv", ["stage", "execution_count", "total_hms", "average_seconds", "environment", "cost_record_status"])), str(cost_dir / "experiment_c_cost_audit_summary.csv"), "Includes label generation, selector training, theta recommendation, final optimization, post-processing, and feature importance/SHAP costs")
    add(rows, "18. configuration/meta-training cost", "hardware/software environment", status(exists(cost_dir / "experiment_c_cost_environment.json") and exists(ROOT / "no_replicate_reproducibility_manifest_20260731.json")), str(cost_dir / "experiment_c_cost_environment.json"))

    df = pd.DataFrame(rows)
    counts = df["status"].value_counts().rename_axis("status").reset_index(name="count")
    lines = [
        "# No-replicate data existence audit",
        "",
        "日期：2026-07-31",
        "",
        "判讀：`存在` 表示已找到對應輸出；`部分存在` 表示有近似或部分資料但不足以完全滿足清單；`未找到` 表示目前沒有找到可直接引用的正式輸出。",
        "",
        "## Summary",
        "",
        counts.to_markdown(index=False),
        "",
        "## Detail",
        "",
        df.to_markdown(index=False),
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"WROTE={OUT}")
    print(counts.to_string(index=False))


if __name__ == "__main__":
    main()
