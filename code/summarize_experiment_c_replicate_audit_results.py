"""Build compact summary tables for the Experiment C replicate audit."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
AUDIT_DIR = ROOT / "outputs" / "experiment_c_replicate_audit_20260730"
OLD_COMPARISON = ROOT / "p0_lite_outputs" / "experiment_c_stability_comparison_20260717"
NEW_COMPARISON = ROOT / "p0_lite_outputs" / "experiment_c_stability_comparison_no_replicate_20260730"
COMMON_AUDIT_COMPARISON = ROOT / "p0_lite_outputs" / "experiment_c_replicate_audit_final_test_20260730"
METHOD = "ExperimentC_StabilityAware_ECMADE_MOO"
NO_REP_METHOD = "ExperimentC_NoReplicate_ECMADE_MOO"
WITH_REP_METHOD = "ExperimentC_ReplicateIncludedAudit_ECMADE_MOO"


def fmt(value: float, digits: int = 4) -> str:
    return f"{float(value):.{digits}f}"


def read_overall(path: Path, method: str) -> pd.Series:
    overall_path = path / "overall_configuration_comparison.csv"
    if not overall_path.exists():
        overall_path = path / "replicate_audit_overall_summary.csv"
    overall = pd.read_csv(overall_path, encoding="utf-8-sig")
    rows = overall[overall["method"].eq(method)]
    if rows.empty:
        raise RuntimeError(f"{method} missing from {path}")
    return rows.iloc[0]


def main() -> None:
    audit = pd.read_csv(AUDIT_DIR / "replicate_audit_validation_test_summary.csv", encoding="utf-8-sig")
    old = read_overall(OLD_COMPARISON, METHOD)
    new = read_overall(NEW_COMPARISON, METHOD)
    common_no_rep = read_overall(COMMON_AUDIT_COMPARISON, NO_REP_METHOD)
    common_with_rep = read_overall(COMMON_AUDIT_COMPARISON, WITH_REP_METHOD)

    test_metrics = {
        "full_selector_no_replicate": common_no_rep,
        "replicate_included_audit": common_with_rep,
    }
    rows = []
    for row in audit.to_dict("records"):
        metric = test_metrics[row["variant"]]
        rows.append(
            {
                **row,
                "test_overall_RankScore": float(metric["overall_RankScore"]),
                "test_mean_RankScore": float(metric["mean_RankScore"]),
                "test_mean_PF_Overlap": float(metric["mean_PF_Overlap"]),
                "test_mean_PF_Drift": float(metric["mean_PF_Drift"]),
                "test_mean_HV": float(metric["mean_HV"]),
                "test_mean_IGD": float(metric["mean_IGD"]),
                "test_first_place_instances": int(metric["first_place_instances"]),
            }
        )
    final = pd.DataFrame(rows)
    final.to_csv(AUDIT_DIR / "replicate_audit_final_summary.csv", index=False, encoding="utf-8-sig")

    selected_cols = [
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
    ]
    final[selected_cols].to_csv(AUDIT_DIR / "replicate_audit_final_compact.csv", index=False, encoding="utf-8-sig")

    no_rep = final[final["variant"].eq("full_selector_no_replicate")].iloc[0]
    with_rep = final[final["variant"].eq("replicate_included_audit")].iloc[0]

    delta_rows = []
    for col in selected_cols[1:]:
        delta_rows.append(
            {
                "metric": col,
                "full_selector_no_replicate": no_rep[col],
                "replicate_included_audit": with_rep[col],
                "delta_no_replicate_minus_replicate": no_rep[col] - with_rep[col],
            }
        )
    pd.DataFrame(delta_rows).to_csv(AUDIT_DIR / "replicate_audit_metric_delta.csv", index=False, encoding="utf-8-sig")

    no_rep_importance = pd.read_csv(
        AUDIT_DIR / "full_selector_no_replicate" / "feature_importance_grouped.csv",
        encoding="utf-8-sig",
    ).head(8)
    with_rep_importance = pd.read_csv(
        AUDIT_DIR / "replicate_included_audit" / "feature_importance_grouped.csv",
        encoding="utf-8-sig",
    ).head(8)

    lines = [
        "# Experiment C Replicate Feature Audit",
        "",
        "## Main comparison",
        "",
        final[selected_cols].to_markdown(index=False),
        "",
        "## Interpretation",
        "",
        (
            "- Removing replicate changed 9/32 test theta assignments, so the no-replicate selector was "
            "evaluated with updated 30-run final-test results for those changed instances."
        ),
        (
            f"- Validation: no-replicate top1={fmt(no_rep['top1_hit_rate'])}, "
            f"top3={fmt(no_rep['top3_hit_rate'])}, mean target rank={fmt(no_rep['mean_target_rank'])}, "
            f"RMSE={fmt(no_rep['rmse'])}, MAE={fmt(no_rep['mae'])}."
        ),
        (
            f"- Replicate-included audit: top1={fmt(with_rep['top1_hit_rate'])}, "
            f"top3={fmt(with_rep['top3_hit_rate'])}, mean target rank={fmt(with_rep['mean_target_rank'])}, "
            f"RMSE={fmt(with_rep['rmse'])}, MAE={fmt(with_rep['mae'])}."
        ),
        (
            f"- Final test: no-replicate overall_RankScore={fmt(no_rep['test_overall_RankScore'])}, "
            f"mean_RankScore={fmt(no_rep['test_mean_RankScore'])}, "
            f"PF_Overlap={fmt(no_rep['test_mean_PF_Overlap'])}, PF_Drift={fmt(no_rep['test_mean_PF_Drift'])}."
        ),
        (
            f"- Final test replicate-included overall_RankScore={fmt(with_rep['test_overall_RankScore'])}, "
            f"mean_RankScore={fmt(with_rep['test_mean_RankScore'])}, "
            f"PF_Overlap={fmt(with_rep['test_mean_PF_Overlap'])}, PF_Drift={fmt(with_rep['test_mean_PF_Drift'])}."
        ),
        "",
        "## Top grouped feature importance",
        "",
        "No-replicate:",
        "",
        no_rep_importance.to_markdown(index=False),
        "",
        "Replicate-included:",
        "",
        with_rep_importance.to_markdown(index=False),
        "",
        "## Output paths",
        "",
        f"- Audit outputs: {AUDIT_DIR}",
        f"- Common-reference replicate audit final-test comparison: {COMMON_AUDIT_COMPARISON}",
        f"- No-replicate final-test comparison: {NEW_COMPARISON}",
        f"- Replicate-included original final-test comparison: {OLD_COMPARISON}",
        f"- No-replicate final-test raw runs: {ROOT / 'p0_lite_outputs' / 'experiment_c_stability_ecmade_moo_no_replicate_20260730'}",
    ]
    (AUDIT_DIR / "README_replicate_audit.md").write_text("\n".join(lines), encoding="utf-8")

    print(final[selected_cols].to_string(index=False))


if __name__ == "__main__":
    main()
