from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
FORMAL_DIR = ROOT / "p0_lite_outputs" / "experiment_c_formal_five_method_no_replicate_20260731"
SIX_METHOD_DIR = ROOT / "p0_lite_outputs" / "experiment_c_replicate_audit_final_test_20260730"
OUT_DIR = ROOT / "outputs" / "experiment_c_table_5_7_holdout_20260802"

METHOD_LABELS = {
    "ExperimentC_NoReplicate_ECMADE_MOO": "Experiment C No-replicate",
    "MetaDesigned_ECMADE_MOO": "Meta-designed",
    "BayesianConfig_ECMADE_MOO": "BayesianConfig",
    "RandomConfig_ECMADE_MOO": "RandomConfig",
    "HandCrafted_ECMADE_MOO": "Hand-crafted",
    "ExperimentC_ReplicateIncludedAudit_ECMADE_MOO": "Replicate-included audit",
}

METRIC_DIRECTIONS = {
    "mean_HV": False,
    "mean_IGD": True,
    "mean_PF_Overlap": False,
    "mean_PF_Drift": True,
    "mean_Diversity": False,
    "mean_Runtime": True,
}


def fmt4(value) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.4f}"


def add_overall_rankscore(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rank_cols = []
    for metric, ascending in METRIC_DIRECTIONS.items():
        rank_col = f"rank_{metric.removeprefix('mean_')}"
        out[rank_col] = out[metric].rank(method="min", ascending=ascending)
        rank_cols.append(rank_col)
    out["overall_RankScore_five_method"] = out[rank_cols].mean(axis=1)
    return out


def build_formal_table() -> pd.DataFrame:
    formal = pd.read_csv(FORMAL_DIR / "formal_five_overall_summary.csv", encoding="utf-8-sig")
    formal = add_overall_rankscore(formal)
    table = formal[
        [
            "method",
            "mean_HV",
            "mean_IGD",
            "mean_PF_Overlap",
            "mean_PF_Drift",
            "mean_Diversity",
            "mean_Runtime",
            "mean_InstanceRankScore",
            "overall_RankScore_five_method",
        ]
    ].copy()
    table["方法"] = table["method"].map(METHOD_LABELS)
    table = table.rename(
        columns={
            "mean_HV": "HV ↑",
            "mean_IGD": "IGD ↓",
            "mean_PF_Overlap": "PF Overlap ↑",
            "mean_PF_Drift": "PF Drift ↓",
            "mean_Diversity": "Diversity ↑",
            "mean_Runtime": "Runtime ↓",
            "mean_InstanceRankScore": "Mean RankScore ↓",
            "overall_RankScore_five_method": "Overall RankScore ↓",
        }
    )
    table = table[
        [
            "方法",
            "HV ↑",
            "IGD ↓",
            "PF Overlap ↑",
            "PF Drift ↓",
            "Diversity ↑",
            "Runtime ↓",
            "Mean RankScore ↓",
            "Overall RankScore ↓",
        ]
    ]
    return table.sort_values(["Overall RankScore ↓", "Mean RankScore ↓", "方法"]).reset_index(drop=True)


def build_audit_reference() -> pd.DataFrame:
    six = pd.read_csv(SIX_METHOD_DIR / "replicate_audit_overall_summary.csv", encoding="utf-8-sig")
    audit = six[six["method"].eq("ExperimentC_ReplicateIncludedAudit_ECMADE_MOO")].copy()
    table = audit[
        [
            "method",
            "mean_HV",
            "mean_IGD",
            "mean_PF_Overlap",
            "mean_PF_Drift",
            "mean_Diversity",
            "mean_Runtime",
            "mean_RankScore",
            "overall_RankScore",
        ]
    ].copy()
    table["方法"] = table["method"].map(METHOD_LABELS)
    table = table.rename(
        columns={
            "mean_HV": "HV ↑",
            "mean_IGD": "IGD ↓",
            "mean_PF_Overlap": "PF Overlap ↑",
            "mean_PF_Drift": "PF Drift ↓",
            "mean_Diversity": "Diversity ↑",
            "mean_Runtime": "Runtime ↓",
            "mean_RankScore": "Mean RankScore ↓ (six-method audit)",
            "overall_RankScore": "Overall RankScore ↓ (six-method audit)",
        }
    )
    return table[
        [
            "方法",
            "HV ↑",
            "IGD ↓",
            "PF Overlap ↑",
            "PF Drift ↓",
            "Diversity ↑",
            "Runtime ↓",
            "Mean RankScore ↓ (six-method audit)",
            "Overall RankScore ↓ (six-method audit)",
        ]
    ]


def markdown_table(df: pd.DataFrame) -> str:
    view = df.copy()
    for col in view.columns:
        if col != "方法":
            view[col] = view[col].map(fmt4)
    return view.to_markdown(index=False)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    formal = build_formal_table()
    audit = build_audit_reference()

    formal.to_csv(OUT_DIR / "table_5_7_experiment_c_holdout_formal_five_methods.csv", index=False, encoding="utf-8-sig")
    audit.to_csv(OUT_DIR / "table_5_7_experiment_c_holdout_replicate_audit_reference.csv", index=False, encoding="utf-8-sig")

    lines = [
        "# Table 5/7 Experiment C hold-out Test corrected tables",
        "",
        "## Formal five-protocol comparison",
        "",
        "Replicate-included audit is excluded from both the empirical common reference front and the RankScore calculation.",
        "",
        markdown_table(formal),
        "",
        "## Replicate-included audit reference",
        "",
        "This row is retained only as an audit reference. Its RankScores are the six-method audit values and must not be mixed with the formal five-protocol RankScores.",
        "",
        markdown_table(audit),
        "",
    ]
    (OUT_DIR / "table_5_7_experiment_c_holdout_corrected.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"WROTE={OUT_DIR}")
    print(markdown_table(formal))
    print()
    print(markdown_table(audit))


if __name__ == "__main__":
    main()
