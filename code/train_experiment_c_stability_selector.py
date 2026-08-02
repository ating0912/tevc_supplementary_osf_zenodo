"""Train and validate the Experiment C stability-aware theta selector."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import joblib
import pandas as pd

from train_meta_designed_ecmade_moo import (
    INSTANCE_CATEGORICAL,
    INSTANCE_NUMERIC,
    JOIN_KEYS,
    THETA_CATEGORICAL,
    THETA_NUMERIC,
    feature_importance,
    load_manifest,
    make_model,
)


DEFAULT_TRAIN_LABELS = Path(
    "p0_lite_outputs/theta24_70_15_15_training_label_full_20260706/"
    "knowledge_base_parameter_report/experiment_c_stability_regression_labels.csv"
)
DEFAULT_VALIDATION_LABELS = Path(
    "p0_lite_outputs/theta24_70_15_15_validation_label_full_20260713/"
    "knowledge_base_parameter_report/experiment_c_stability_regression_labels.csv"
)
DEFAULT_MANIFEST_701515 = Path("data/synthetic_constrained_portfolio/manifest_70_15_15.csv")
DEFAULT_ASSIGNMENT_MANIFEST = Path("data/synthetic_constrained_portfolio/manifest.csv")
DEFAULT_OUTPUT = Path("p0_lite_outputs/experiment_c_stability_selector_training")

THETA_ASSIGNMENT_COLUMNS = [
    "method",
    "source_theta_id",
    "source_operator",
    "source_migration",
    "source_elite_ratio",
    "source_archive_strategy",
    "source_constraint_handling",
    "subpops",
    "operatorMode",
    "exchangeMode",
    "eliteRatio",
    "stagnationThreshold",
    "theta",
    "archiveLimitFactor",
    "consensusArchive",
    "archiveConsWeight",
    "bestGuide",
    "minSubpopSize",
]


def workspace_root() -> Path:
    return Path(__file__).resolve().parent


def resolve(path: Path, root: Path) -> Path:
    return path if path.is_absolute() else root / path


def prepare_labels(labels: pd.DataFrame, manifest: pd.DataFrame) -> pd.DataFrame:
    merged = labels.merge(manifest, on=JOIN_KEYS, how="left", suffixes=("", "_manifest"))
    missing = merged["assets"].isna().sum()
    if missing:
        raise RuntimeError(f"{missing} C label rows did not match manifest by {JOIN_KEYS}")
    merged["target"] = pd.to_numeric(merged["C_LabelScore"], errors="coerce")
    return merged


def feature_columns(df: pd.DataFrame, *, include_replicate: bool = False) -> tuple[list[str], list[str]]:
    instance_numeric = [col for col in INSTANCE_NUMERIC if include_replicate or col != "replicate"]
    numeric = [c for c in instance_numeric + THETA_NUMERIC if c in df.columns]
    categorical = [c for c in INSTANCE_CATEGORICAL + THETA_CATEGORICAL if c in df.columns]
    return numeric, categorical


def theta_candidates_from_labels(labels: pd.DataFrame) -> pd.DataFrame:
    cols = [col for col in THETA_ASSIGNMENT_COLUMNS if col in labels.columns]
    theta = labels[cols].drop_duplicates("method").sort_values("method").reset_index(drop=True)
    if theta.empty:
        raise RuntimeError("No theta candidates found in C labels.")
    return theta


def predict_rows(model, frame: pd.DataFrame, numeric: list[str], categorical: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for col in numeric:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["predicted_C_LabelScore"] = model.predict(out[numeric + categorical])
    out["predicted_C_ThetaRank"] = (
        out.groupby(JOIN_KEYS)["predicted_C_LabelScore"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    return out


def select_by_prediction(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in predictions.groupby(JOIN_KEYS, sort=False):
        instance, k_value = keys
        ranked = group.copy()
        ranked["target_rank_desc"] = ranked["C_LabelScore"].rank(method="min", ascending=False)
        selected = ranked.sort_values(["predicted_C_LabelScore", "method"], ascending=[False, True]).iloc[0]
        best = group.sort_values("C_LabelScore", ascending=False).iloc[0]
        standard = group.sort_values("ThetaRank", ascending=True).iloc[0]
        rows.append(
            {
                "instance": instance,
                "K": int(k_value),
                "selected_theta": selected["method"],
                "best_c_theta": best["method"],
                "standard_label_top1_theta": standard["method"],
                "selected_C_LabelScore": float(selected["C_LabelScore"]),
                "best_C_LabelScore": float(best["C_LabelScore"]),
                "standard_C_LabelScore": float(standard["C_LabelScore"]),
                "C_regret": float(best["C_LabelScore"] - selected["C_LabelScore"]),
                "selected_C_ThetaRank": int(selected["target_rank_desc"]),
                "selected_C_ThetaRank_raw": int(selected["C_ThetaRank"]),
                "hit_top1": float(selected["target_rank_desc"] == 1),
                "hit_top3": float(selected["target_rank_desc"] <= 3),
                "selected_PF_Overlap": float(selected["PF_Overlap"]),
                "best_PF_Overlap": float(best["PF_Overlap"]),
                "standard_PF_Overlap": float(standard["PF_Overlap"]),
                "selected_PF_Drift": float(selected["PF_Drift"]),
                "best_PF_Drift": float(best["PF_Drift"]),
                "standard_PF_Drift": float(standard["PF_Drift"]),
                "selected_HV": float(selected["HV"]),
                "best_HV": float(best["HV"]),
                "standard_HV": float(standard["HV"]),
                "selected_IGD": float(selected["IGD"]),
                "best_IGD": float(best["IGD"]),
                "standard_IGD": float(standard["IGD"]),
            }
        )
    return pd.DataFrame(rows)


def summarize_validation(selection: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "selector": "ExperimentC_StabilityAware",
            "groups": int(len(selection)),
            "top1_hit_rate": float(selection["hit_top1"].mean()),
            "top3_hit_rate": float(selection["hit_top3"].mean()),
            "mean_C_ThetaRank": float(selection["selected_C_ThetaRank"].mean()),
            "mean_C_regret": float(selection["C_regret"].mean()),
            "mean_C_LabelScore": float(selection["selected_C_LabelScore"].mean()),
            "mean_PF_Overlap": float(selection["selected_PF_Overlap"].mean()),
            "mean_PF_Drift": float(selection["selected_PF_Drift"].mean()),
            "mean_HV": float(selection["selected_HV"].mean()),
            "mean_IGD": float(selection["selected_IGD"].mean()),
        },
        {
            "selector": "C_Oracle",
            "groups": int(len(selection)),
            "top1_hit_rate": 1.0,
            "top3_hit_rate": 1.0,
            "mean_C_ThetaRank": 1.0,
            "mean_C_regret": 0.0,
            "mean_C_LabelScore": float(selection["best_C_LabelScore"].mean()),
            "mean_PF_Overlap": float(selection["best_PF_Overlap"].mean()),
            "mean_PF_Drift": float(selection["best_PF_Drift"].mean()),
            "mean_HV": float(selection["best_HV"].mean()),
            "mean_IGD": float(selection["best_IGD"].mean()),
        },
        {
            "selector": "Standard_Label_Top1",
            "groups": int(len(selection)),
            "top1_hit_rate": float((selection["standard_label_top1_theta"] == selection["best_c_theta"]).mean()),
            "top3_hit_rate": float("nan"),
            "mean_C_ThetaRank": float("nan"),
            "mean_C_regret": float((selection["best_C_LabelScore"] - selection["standard_C_LabelScore"]).mean()),
            "mean_C_LabelScore": float(selection["standard_C_LabelScore"].mean()),
            "mean_PF_Overlap": float(selection["standard_PF_Overlap"].mean()),
            "mean_PF_Drift": float(selection["standard_PF_Drift"].mean()),
            "mean_HV": float(selection["standard_HV"].mean()),
            "mean_IGD": float(selection["standard_IGD"].mean()),
        },
        {
            "selector": "All_Theta_Mean",
            "groups": int(predictions[JOIN_KEYS].drop_duplicates().shape[0]),
            "top1_hit_rate": float("nan"),
            "top3_hit_rate": float("nan"),
            "mean_C_ThetaRank": float(predictions["C_ThetaRank"].mean()),
            "mean_C_regret": float("nan"),
            "mean_C_LabelScore": float(predictions["C_LabelScore"].mean()),
            "mean_PF_Overlap": float(predictions["PF_Overlap"].mean()),
            "mean_PF_Drift": float(predictions["PF_Drift"].mean()),
            "mean_HV": float(predictions["HV"].mean()),
            "mean_IGD": float(predictions["IGD"].mean()),
        },
    ]
    return pd.DataFrame(rows)


def build_assignment(
    model,
    manifest: pd.DataFrame,
    theta: pd.DataFrame,
    numeric: list[str],
    categorical: list[str],
    splits: Iterable[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    test = manifest[manifest["split"].isin(list(splits))].copy()
    if test.empty:
        raise RuntimeError(f"No manifest rows found for splits={list(splits)}")
    rows = []
    all_scores = []
    for _, instance in test.iterrows():
        tiled = pd.concat([instance.to_frame().T] * len(theta), ignore_index=True)
        tiled = pd.concat([tiled.reset_index(drop=True), theta.reset_index(drop=True)], axis=1)
        for col in numeric:
            tiled[col] = pd.to_numeric(tiled[col], errors="coerce")
        tiled["predicted_C_LabelScore"] = model.predict(tiled[numeric + categorical])
        tiled["predicted_C_ThetaRank"] = (
            tiled["predicted_C_LabelScore"].rank(method="first", ascending=False).astype(int)
        )
        all_scores.append(tiled.copy())
        best = tiled.sort_values("predicted_C_LabelScore", ascending=False).iloc[0]
        rows.append(
            {
                "split": best["split"],
                "instance": best["instance"],
                "assets": int(best["assets"]),
                "K": int(best["K"]),
                "k_ratio": float(best["k_ratio"]),
                "theta_index": int(theta.index[theta["method"] == best["method"]][0]) + 1,
                "theta_id": best["method"],
                "predicted_score": float(best["predicted_C_LabelScore"]),
                "predicted_C_LabelScore": float(best["predicted_C_LabelScore"]),
                "S": int(best["subpops"]),
                "operator": best["source_operator"],
                "migration": best["source_migration"],
                "elite_ratio": float(best["eliteRatio"]),
                "stagnation_threshold": int(best["stagnationThreshold"]),
                "path": best["path"],
            }
        )
    return pd.DataFrame(rows), pd.concat(all_scores, ignore_index=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-labels", type=Path, default=DEFAULT_TRAIN_LABELS)
    parser.add_argument("--validation-labels", type=Path, default=DEFAULT_VALIDATION_LABELS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_701515)
    parser.add_argument("--assignment-manifest", type=Path, default=DEFAULT_ASSIGNMENT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=20260717)
    parser.add_argument("--assignment-splits", default="test")
    parser.add_argument(
        "--include-replicate",
        action="store_true",
        help="Audit mode: include the synthetic replicate/generation index as an instance feature.",
    )
    return parser.parse_args()


def main() -> None:
    root = workspace_root()
    args = parse_args()
    train_labels_path = resolve(args.train_labels, root)
    validation_labels_path = resolve(args.validation_labels, root)
    manifest_path = resolve(args.manifest, root)
    assignment_manifest_path = resolve(args.assignment_manifest, root)
    output_dir = resolve(args.output_dir, root)
    output_dir.mkdir(parents=True, exist_ok=True)

    train_labels = pd.read_csv(train_labels_path)
    validation_labels = pd.read_csv(validation_labels_path)
    manifest = load_manifest(manifest_path)
    assignment_manifest = load_manifest(assignment_manifest_path)

    theta = theta_candidates_from_labels(train_labels)
    train = prepare_labels(train_labels, manifest)
    validation = prepare_labels(validation_labels, manifest)
    numeric, categorical = feature_columns(train, include_replicate=args.include_replicate)

    model = make_model(numeric, categorical, args.seed)
    model.fit(train[numeric + categorical], train["target"])

    validation_predictions = predict_rows(model, validation, numeric, categorical)
    validation_selection = select_by_prediction(validation_predictions)
    validation_summary = summarize_validation(validation_selection, validation_predictions)

    assignment_splits = [part.strip() for part in args.assignment_splits.split(",") if part.strip()]
    assignment, test_scores = build_assignment(
        model, assignment_manifest, theta, numeric, categorical, assignment_splits
    )

    joblib.dump(model, output_dir / "experiment_c_stability_random_forest.joblib")
    train.to_csv(output_dir / "training_table.csv", index=False, encoding="utf-8-sig")
    validation_predictions.to_csv(
        output_dir / "validation_predictions.csv", index=False, encoding="utf-8-sig"
    )
    validation_selection.to_csv(
        output_dir / "validation_theta_selection.csv", index=False, encoding="utf-8-sig"
    )
    validation_summary.to_csv(
        output_dir / "validation_selector_summary.csv", index=False, encoding="utf-8-sig"
    )
    feature_importance(model, numeric, categorical).to_csv(
        output_dir / "feature_importance.csv", index=False, encoding="utf-8-sig"
    )
    theta.to_csv(output_dir / "theta_candidate_table.csv", index=False, encoding="utf-8-sig")
    assignment.to_csv(
        output_dir / "experiment_c_stability_theta_assignment.csv",
        index=False,
        encoding="utf-8-sig",
    )
    test_scores.to_csv(
        output_dir / "test_theta_predicted_scores.csv", index=False, encoding="utf-8-sig"
    )
    with (output_dir / "feature_columns.json").open("w", encoding="utf-8") as f:
        json.dump({"numeric": numeric, "categorical": categorical}, f, indent=2)
    with (output_dir / "training_config.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "train_labels": str(train_labels_path),
                "validation_labels": str(validation_labels_path),
                "manifest": str(manifest_path),
                "assignment_manifest": str(assignment_manifest_path),
                "target": "C_LabelScore",
                "selection_rule": "maximize predicted_C_LabelScore",
                "include_replicate_feature": bool(args.include_replicate),
                "c_score_formula": "-0.2*rank_HV - 0.2*rank_IGD - 0.3*rank_PF_Overlap - 0.3*rank_PF_Drift",
                "assignment_splits": assignment_splits,
                "training_rows": int(len(train)),
                "validation_rows": int(len(validation)),
                "theta_candidates": int(len(theta)),
            },
            f,
            indent=2,
        )

    print(f"OUTPUT={output_dir}")
    print(validation_summary.to_string(index=False))
    print(f"assignment_rows={len(assignment)}")
    print("assignment theta counts:")
    print(assignment["theta_id"].value_counts().to_string())


if __name__ == "__main__":
    main()
