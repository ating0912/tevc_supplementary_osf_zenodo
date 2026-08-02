from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from compute_tevc_adaptive_exchange_significance import holm_adjust, wilcoxon_exact_paired


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs" / "tevc_subpopulation_significance_20260722"
C_DETAIL = ROOT / "outputs" / "tevc_ablation_6_20260717" / "theta_factor_group_detail.csv"
VALID_EAF = ROOT / "outputs" / "tevc_ablation_eaf_width_20260722" / "validation_theta_instance_eaf_width.csv"
VALID_LABELS = (
    ROOT
    / "p0_lite_outputs"
    / "theta24_70_15_15_validation_label_full_20260713"
    / "knowledge_base_parameter_report"
    / "experiment_c_stability_regression_labels.csv"
)
DIRECT = (
    ROOT
    / "p0_lite_outputs"
    / "tevc_pdf_direct_ablation_full_20260717"
    / "pdf_direct_ablation_summary"
    / "pdf_direct_ablation_instance_ranked.csv"
)
DIRECT_EAF = (
    ROOT
    / "p0_lite_outputs"
    / "tevc_p0_requirement_tables_20260717"
    / "tevc_p0_instance_eaf_band_width.csv"
)


def paired_comparison_rows(
    frame: pd.DataFrame,
    metrics: list[tuple[str, str]],
    context: str,
    reference: str,
    comparators: list[str],
) -> pd.DataFrame:
    rows = []
    for comparator in comparators:
        part = frame[frame["level"].astype(str).isin([reference, comparator])].copy()
        for metric, direction in metrics:
            pivot = part.pivot_table(index=["instance", "K"], columns="level", values=metric, aggfunc="mean")
            pivot = pivot.dropna(subset=[reference, comparator])
            ref = pivot[reference].astype(float).to_numpy()
            other = pivot[comparator].astype(float).to_numpy()
            diff = ref - other
            if direction == "min":
                ref_better = diff < -1e-12
                other_better = diff > 1e-12
            else:
                ref_better = diff > 1e-12
                other_better = diff < -1e-12
            _, p_value = wilcoxon_exact_paired(ref, other)
            rows.append(
                {
                    "context": context,
                    "comparison": f"{reference} vs {comparator}",
                    "reference_level": reference,
                    "comparator_level": comparator,
                    "metric": metric,
                    "direction": direction,
                    "n_pairs": int(len(pivot)),
                    "reference_mean": float(np.nanmean(ref)),
                    "comparator_mean": float(np.nanmean(other)),
                    "median_reference_minus_comparator": float(np.nanmedian(diff)),
                    "reference_better": int(ref_better.sum()),
                    "ties": int((np.abs(diff) <= 1e-12).sum()),
                    "comparator_better": int(other_better.sum()),
                    "wilcoxon_p_two_sided": float(p_value),
                }
            )
    out = pd.DataFrame(rows)
    out["holm_p"] = holm_adjust(out["wilcoxon_p_two_sided"].tolist())
    out["significant_0_05_holm"] = out["holm_p"] < 0.05
    return out


def validation_frame() -> pd.DataFrame:
    detail = pd.read_csv(C_DETAIL, encoding="utf-8-sig")
    detail = detail[
        detail["objective"].eq("stability_label")
        & detail["source"].eq("Validation")
        & detail["factor"].eq("S")
    ].copy()
    detail["level"] = detail["level"].astype(str)

    labels = pd.read_csv(VALID_LABELS, encoding="utf-8-sig")
    labels = labels[labels["split"].astype(str).str.lower().eq("validation")].copy()
    labels["level"] = labels["subpops"].astype(int).astype(str)
    eaf = pd.read_csv(VALID_EAF, encoding="utf-8-sig")
    merged = labels.merge(
        eaf[["split", "instance", "K", "method", "EAF_Band_Width_IQR", "EAF_Band_Width_80pct"]],
        on=["split", "instance", "K", "method"],
        how="left",
    )
    eaf_detail = (
        merged.groupby(["split", "instance", "K", "level"], dropna=False)
        .agg(
            EAF_Band_Width_IQR=("EAF_Band_Width_IQR", "mean"),
            EAF_Band_Width_80pct=("EAF_Band_Width_80pct", "mean"),
        )
        .reset_index()
    )
    detail = detail.merge(
        eaf_detail[["instance", "K", "level", "EAF_Band_Width_IQR", "EAF_Band_Width_80pct"]],
        on=["instance", "K", "level"],
        how="left",
    )
    return detail


def direct_frame() -> pd.DataFrame:
    direct = pd.read_csv(DIRECT, encoding="utf-8-sig")
    direct = direct[direct["ablation_family"].eq("subpopulation_number")].copy()
    direct = direct.rename(columns={"ablation_level": "level"})
    eaf = pd.read_csv(DIRECT_EAF, encoding="utf-8-sig")
    eaf = eaf[eaf["experiment"].eq("TEVC_PDF_Direct_Ablation")].copy()
    direct = direct.merge(
        eaf[["instance", "K", "method", "EAF_Band_Width_IQR", "EAF_Band_Width_80pct"]],
        on=["instance", "K", "method"],
        how="left",
    )
    return direct


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    c_metrics = [
        ("objective_loss", "min"),
        ("objective_rank", "min"),
        ("top3_share", "max"),
        ("PF_Overlap", "max"),
        ("PF_Drift", "min"),
        ("EAF_Band_Width_IQR", "min"),
        ("Runtime", "min"),
    ]
    direct_metrics = [
        ("RankScore", "min"),
        ("FamilyInstanceRank", "min"),
        ("HV", "max"),
        ("IGD", "min"),
        ("PF_Overlap", "max"),
        ("PF_Drift", "min"),
        ("EAF_Band_Width_IQR", "min"),
        ("Runtime", "min"),
    ]
    c_stats = paired_comparison_rows(
        validation_frame(),
        c_metrics,
        "Validation C-label S main effect",
        reference="3",
        comparators=["2", "5"],
    )
    direct_stats = paired_comparison_rows(
        direct_frame(),
        direct_metrics,
        "Direct test S ablation",
        reference="S=3",
        comparators=["S=2", "S=5"],
    )
    c_stats.to_csv(OUT_DIR / "subpopulation_s3_vs_s2_s5_c_label_wilcoxon.csv", index=False, encoding="utf-8-sig")
    direct_stats.to_csv(OUT_DIR / "subpopulation_s3_vs_s2_s5_direct_wilcoxon.csv", index=False, encoding="utf-8-sig")
    all_stats = pd.concat([c_stats, direct_stats], ignore_index=True)
    all_stats.to_csv(OUT_DIR / "subpopulation_s3_vs_s2_s5_wilcoxon_all.csv", index=False, encoding="utf-8-sig")
    print(all_stats.to_string(index=False))


if __name__ == "__main__":
    main()
