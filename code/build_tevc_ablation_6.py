"""Build TEVC ablation 6: theta factor main-effect analysis.

This is an orthogonal/factor main-effect analysis over completed theta-label
tables. It does not launch MATLAB or create new raw optimization runs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs" / "tevc_ablation_6_20260717"

TRAIN_STANDARD = (
    ROOT
    / "p0_lite_outputs"
    / "theta24_70_15_15_training_label_full_20260706"
    / "knowledge_base_parameter_report"
    / "regression_score_labels.csv"
)
VALID_STANDARD = (
    ROOT
    / "p0_lite_outputs"
    / "theta24_70_15_15_validation_label_full_20260713"
    / "knowledge_base_parameter_report"
    / "regression_score_labels.csv"
)
TRAIN_C = (
    ROOT
    / "p0_lite_outputs"
    / "theta24_70_15_15_training_label_full_20260706"
    / "knowledge_base_parameter_report"
    / "experiment_c_stability_regression_labels.csv"
)
VALID_C = (
    ROOT
    / "p0_lite_outputs"
    / "theta24_70_15_15_validation_label_full_20260713"
    / "knowledge_base_parameter_report"
    / "experiment_c_stability_regression_labels.csv"
)

FACTORS = [
    ("subpops", "S"),
    ("source_operator", "operator"),
    ("source_migration", "migration"),
    ("source_elite_ratio", "elite_ratio"),
    ("stagnationThreshold", "stagnation_threshold"),
]
METRICS = ["HV", "IGD", "PF_Overlap", "PF_Drift", "Diversity", "Runtime"]
GROUP_KEYS = ["split", "instance", "K"]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def add_objective_columns(df: pd.DataFrame, objective: str) -> pd.DataFrame:
    out = df.copy()
    numeric_cols = [
        "K",
        "HV",
        "IGD",
        "PF_Overlap",
        "PF_Drift",
        "Diversity",
        "Runtime",
        "rank_HV",
        "rank_IGD",
        "rank_PF_Overlap",
        "rank_PF_Drift",
        "rank_Runtime",
        "LabelScore",
        "ThetaRank",
        "C_LabelScore",
        "C_ThetaRank",
        "subpops",
        "eliteRatio",
        "stagnationThreshold",
    ]
    for col in numeric_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if objective == "standard_label":
        out["objective_loss"] = out["LabelScore"]
        out["objective_rank"] = out["ThetaRank"]
    elif objective == "stability_label":
        out["objective_loss"] = out["C_LabelScore"]
        out["objective_rank"] = out["C_ThetaRank"]
    elif objective == "performance_only":
        out["objective_loss"] = (out["rank_HV"] + out["rank_IGD"]) / 2.0
        out["objective_rank"] = (
            out.groupby(GROUP_KEYS)["objective_loss"].rank(method="first", ascending=True).astype(int)
        )
    elif objective == "pf_stability_only":
        out["objective_loss"] = (out["rank_PF_Overlap"] + out["rank_PF_Drift"]) / 2.0
        out["objective_rank"] = (
            out.groupby(GROUP_KEYS)["objective_loss"].rank(method="first", ascending=True).astype(int)
        )
    else:
        raise ValueError(f"Unknown objective: {objective}")

    out["is_top1"] = (out["objective_rank"] == 1).astype(float)
    out["is_top3"] = (out["objective_rank"] <= 3).astype(float)
    return out


def load_objective_frames() -> dict[str, pd.DataFrame]:
    standard = pd.concat(
        [read_csv(TRAIN_STANDARD), read_csv(VALID_STANDARD)],
        ignore_index=True,
    )
    stability = pd.concat(
        [read_csv(TRAIN_C), read_csv(VALID_C)],
        ignore_index=True,
    )
    return {
        "standard_label": add_objective_columns(standard, "standard_label"),
        "stability_label": add_objective_columns(stability, "stability_label"),
        "performance_only": add_objective_columns(stability, "performance_only"),
        "pf_stability_only": add_objective_columns(stability, "pf_stability_only"),
    }


def source_slices(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "Training": frame[frame["split"].astype(str).str.lower() == "training"].copy(),
        "Validation": frame[frame["split"].astype(str).str.lower() == "validation"].copy(),
        "All": frame.copy(),
    }


def factor_balance(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for objective, frame in frames.items():
        for source_name, part in source_slices(frame).items():
            for factor_col, factor_name in FACTORS:
                counts = (
                    part[["method", factor_col]]
                    .drop_duplicates()
                    .groupby(factor_col)
                    .size()
                    .reset_index(name="theta_candidates")
                )
                for _, row in counts.iterrows():
                    rows.append(
                        {
                            "objective": objective,
                            "source": source_name,
                            "factor": factor_name,
                            "level": row[factor_col],
                            "theta_candidates": int(row["theta_candidates"]),
                            "instance_groups": int(part[GROUP_KEYS].drop_duplicates().shape[0]),
                            "rows": int(len(part[part[factor_col] == row[factor_col]])),
                        }
                    )
    return pd.DataFrame(rows)


def build_group_detail(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for objective, frame in frames.items():
        for source_name, part in source_slices(frame).items():
            if part.empty:
                continue
            for factor_col, factor_name in FACTORS:
                group_cols = GROUP_KEYS + [factor_col]
                agg = (
                    part.groupby(group_cols, dropna=False)
                    .agg(
                        theta_rows=("method", "count"),
                        objective_loss=("objective_loss", "mean"),
                        objective_rank=("objective_rank", "mean"),
                        top1_share=("is_top1", "mean"),
                        top3_share=("is_top3", "mean"),
                        HV=("HV", "mean"),
                        IGD=("IGD", "mean"),
                        PF_Overlap=("PF_Overlap", "mean"),
                        PF_Drift=("PF_Drift", "mean"),
                        Diversity=("Diversity", "mean"),
                        Runtime=("Runtime", "mean"),
                    )
                    .reset_index()
                    .rename(columns={factor_col: "level"})
                )
                agg.insert(0, "factor", factor_name)
                agg.insert(0, "source", source_name)
                agg.insert(0, "objective", objective)
                rows.append(agg)
    return pd.concat(rows, ignore_index=True)


def build_summary(detail: pd.DataFrame) -> pd.DataFrame:
    summary = (
        detail.groupby(["objective", "source", "factor", "level"], dropna=False)
        .agg(
            instance_groups=("instance", "nunique"),
            rows=("theta_rows", "sum"),
            mean_objective_loss=("objective_loss", "mean"),
            mean_objective_rank=("objective_rank", "mean"),
            mean_top1_share=("top1_share", "mean"),
            mean_top3_share=("top3_share", "mean"),
            mean_HV=("HV", "mean"),
            mean_IGD=("IGD", "mean"),
            mean_PF_Overlap=("PF_Overlap", "mean"),
            mean_PF_Drift=("PF_Drift", "mean"),
            mean_Diversity=("Diversity", "mean"),
            mean_Runtime=("Runtime", "mean"),
        )
        .reset_index()
    )

    summary["level_rank_within_factor"] = (
        summary.groupby(["objective", "source", "factor"])["mean_objective_loss"]
        .rank(method="first", ascending=True)
        .astype(int)
    )
    best_loss = summary.groupby(["objective", "source", "factor"])["mean_objective_loss"].transform("min")
    summary["delta_loss_from_best_level"] = summary["mean_objective_loss"] - best_loss
    return summary.sort_values(
        ["objective", "source", "factor", "level_rank_within_factor", "level"],
        kind="stable",
    )


def build_best_level_counts(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    keys = ["objective", "source", "factor", *GROUP_KEYS]
    for _, group in detail.groupby(keys, dropna=False):
        best_loss = group["objective_loss"].min()
        winners = group[group["objective_loss"] == best_loss].sort_values("level")
        winner = winners.iloc[0]
        rows.append(
            {
                "objective": winner["objective"],
                "source": winner["source"],
                "factor": winner["factor"],
                "split": winner["split"],
                "instance": winner["instance"],
                "K": winner["K"],
                "best_level": winner["level"],
                "best_level_loss": winner["objective_loss"],
                "ties_at_best": int(len(winners)),
            }
        )
    best_detail = pd.DataFrame(rows)
    summary = (
        best_detail.groupby(["objective", "source", "factor", "best_level"], dropna=False)
        .agg(
            best_group_count=("instance", "count"),
            mean_best_level_loss=("best_level_loss", "mean"),
            tie_groups=("ties_at_best", lambda x: int((x > 1).sum())),
        )
        .reset_index()
        .rename(columns={"best_level": "level"})
    )
    totals = summary.groupby(["objective", "source", "factor"])["best_group_count"].transform("sum")
    summary["best_group_rate"] = summary["best_group_count"] / totals
    return best_detail, summary.sort_values(
        ["objective", "source", "factor", "best_group_count", "level"],
        ascending=[True, True, True, False, True],
        kind="stable",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frames = load_objective_frames()
    balance = factor_balance(frames)
    detail = build_group_detail(frames)
    summary = build_summary(detail)
    best_detail, best_summary = build_best_level_counts(detail)

    balance.to_csv(OUT_DIR / "theta_factor_balance.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUT_DIR / "theta_factor_group_detail.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT_DIR / "theta_factor_main_effect_summary.csv", index=False, encoding="utf-8-sig")
    best_detail.to_csv(OUT_DIR / "theta_factor_best_level_by_instance.csv", index=False, encoding="utf-8-sig")
    best_summary.to_csv(OUT_DIR / "theta_factor_best_level_counts.csv", index=False, encoding="utf-8-sig")

    readme = {
        "output_dir": str(OUT_DIR),
        "inputs": {
            "training_standard": str(TRAIN_STANDARD),
            "validation_standard": str(VALID_STANDARD),
            "training_stability": str(TRAIN_C),
            "validation_stability": str(VALID_C),
        },
        "objectives": {
            "standard_label": "LabelScore / ThetaRank; lower is better",
            "stability_label": "C_LabelScore / C_ThetaRank; lower is better",
            "performance_only": "mean(rank_HV, rank_IGD); lower is better",
            "pf_stability_only": "mean(rank_PF_Overlap, rank_PF_Drift); lower is better",
        },
        "method": (
            "For each instance and factor level, theta rows are averaged first; "
            "factor summaries then average across instance groups. This is a "
            "main-effect analysis over existing theta-label data, not a strict "
            "one-factor-at-a-time causal rerun."
        ),
    }
    (OUT_DIR / "README.json").write_text(json.dumps(readme, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
