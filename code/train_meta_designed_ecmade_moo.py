"""Train the Meta-designed ECMADE-MOO meta-learner.

The model learns:

    instance meta-features + theta encoding -> predicted theta quality

Training labels come from the completed theta24 label-generation report.
The output is a model plus a theta assignment table for unseen test
instances. The assignment table is the input for the next MATLAB runner.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


DEFAULT_LABELS = Path(
    "p0_lite_outputs/theta24_70_15_15_training_label_full_20260706/"
    "knowledge_base_parameter_report/regression_score_labels.csv"
)
DEFAULT_MANIFEST = Path("data/synthetic_constrained_portfolio/manifest_70_15_15.csv")
DEFAULT_ASSIGNMENT_MANIFEST = Path("data/synthetic_constrained_portfolio/manifest.csv")
DEFAULT_THETA = Path(
    r"C:\Users\yiting\Desktop\NCHU\lab\TEVC\excel"
    r"\TEVC_P0_L24_Orthogonal_Theta_Configurations.xlsx"
)
DEFAULT_OUTPUT = Path("p0_lite_outputs/meta_designed_ecmade_moo_training")

INSTANCE_NUMERIC = ["assets", "days", "k_ratio", "K", "replicate"]
INSTANCE_CATEGORICAL = [
    "split",
    "corr_structure",
    "return_distribution",
    "risk_structure",
]
THETA_NUMERIC = [
    "subpops",
    "eliteRatio",
    "stagnationThreshold",
    "theta",
    "archiveLimitFactor",
    "S_level",
    "operator_level",
    "migration_level",
    "elite_level",
    "tau_level",
]
THETA_CATEGORICAL = [
    "source_operator",
    "source_migration",
    "source_archive_strategy",
    "source_constraint_handling",
    "operatorMode",
    "exchangeMode",
    "bestGuide",
]
JOIN_KEYS = ["instance", "K"]


def workspace_root() -> Path:
    return Path(__file__).resolve().parent


def resolve(path: Path, root: Path) -> Path:
    return path if path.is_absolute() else root / path


def theta_excel_default(root: Path) -> Path:
    candidates = [
        DEFAULT_THETA,
        Path(
            r"C:\Users\yiting\Desktop\NCHU\lab\TEVC\data"
            r"\TEVC_P0_L24_Orthogonal_Theta_Configurations.xlsx"
        ),
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def normalize_theta_id(value: object, row_index: int) -> str:
    text = str(value)
    digits = "".join(ch for ch in text if ch.isdigit())
    number = int(digits) if digits else row_index
    return f"theta_{number:02d}"


def load_theta_table(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="L24_Theta_Config", header=3).iloc[:24].copy()
    df = df[df["theta_id"].notna()].copy()
    df["method"] = [normalize_theta_id(v, i + 1) for i, v in enumerate(df["theta_id"])]
    df["source_theta_id"] = df["method"]
    rename = {
        "S": "subpops",
        "operator": "source_operator",
        "migration": "source_migration",
        "elite_ratio": "source_elite_ratio",
        "stagnation_threshold": "stagnationThreshold",
    }
    df = df.rename(columns=rename)
    df["eliteRatio"] = df["source_elite_ratio"].map(parse_percent)
    df["theta"] = 1 / 13
    df["archiveLimitFactor"] = 5
    df["operatorMode"] = df["source_operator"].map(
        {"DE/rand": "rand2", "DE/best": "best2", "mixed": "mixed"}
    )
    df["exchangeMode"] = df["source_migration"].map(
        {"none": "none", "fixed": "paper", "adaptive": "stable"}
    )
    df["bestGuide"] = "rank"
    df["source_archive_strategy"] = df["archive_strategy"]
    df["source_constraint_handling"] = df["constraint_handling"]
    keep = [
        "method",
        "source_theta_id",
        "S_level",
        "operator_level",
        "migration_level",
        "elite_level",
        "tau_level",
        *THETA_NUMERIC[:5],
        *THETA_CATEGORICAL,
        "source_elite_ratio",
    ]
    return df[keep].copy()


def parse_percent(value: object) -> float:
    text = str(value).strip()
    has_percent = text.endswith("%")
    text = text.replace("%", "")
    number = float(text)
    return number / 100.0 if has_percent or number > 1 else number


def load_manifest(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in INSTANCE_NUMERIC:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def prepare_training(labels: pd.DataFrame, manifest: pd.DataFrame) -> pd.DataFrame:
    merged = labels.merge(manifest, on=JOIN_KEYS, how="left", suffixes=("", "_manifest"))
    missing = merged["assets"].isna().sum()
    if missing:
        raise RuntimeError(f"{missing} label rows did not match manifest by {JOIN_KEYS}")
    merged["target"] = -pd.to_numeric(merged["LabelScore"], errors="coerce")
    return merged


def feature_columns(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    numeric = [c for c in INSTANCE_NUMERIC + THETA_NUMERIC if c in df.columns]
    categorical = [c for c in INSTANCE_CATEGORICAL + THETA_CATEGORICAL if c in df.columns]
    return numeric, categorical


def make_model(numeric: list[str], categorical: list[str], seed: int) -> Pipeline:
    try:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse=False)
    preprocess = ColumnTransformer(
        transformers=[
            ("num", "passthrough", numeric),
            ("cat", encoder, categorical),
        ],
        remainder="drop",
    )
    rf = RandomForestRegressor(
        n_estimators=500,
        min_samples_leaf=2,
        random_state=seed,
        n_jobs=-1,
    )
    return Pipeline([("preprocess", preprocess), ("model", rf)])


def score_selected_theta(frame: pd.DataFrame) -> dict[str, float]:
    selected = frame.loc[frame["predicted_score"].idxmax()]
    best = frame.loc[frame["LabelScore"].idxmin()]
    return {
        "selected_label_score": float(selected["LabelScore"]),
        "best_label_score": float(best["LabelScore"]),
        "regret": float(selected["LabelScore"] - best["LabelScore"]),
        "selected_theta_rank": float(selected["ThetaRank"]),
        "hit_top1": float(selected["ThetaRank"] == 1),
        "selected_method": str(selected["method"]),
        "best_method": str(best["method"]),
    }


def cross_validate(
    train: pd.DataFrame,
    numeric: list[str],
    categorical: list[str],
    folds: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    groups = train["instance"].astype(str) + "|K" + train["K"].astype(str)
    n_groups = groups.nunique()
    n_splits = min(folds, n_groups)
    gkf = GroupKFold(n_splits=n_splits)
    pred_frames = []
    fold_rows = []
    X = train[numeric + categorical]
    y = train["target"]
    for fold, (tr_idx, va_idx) in enumerate(gkf.split(X, y, groups), start=1):
        model = make_model(numeric, categorical, seed + fold)
        tr = train.iloc[tr_idx].copy()
        va = train.iloc[va_idx].copy()
        model.fit(tr[numeric + categorical], tr["target"])
        va["predicted_score"] = model.predict(va[numeric + categorical])
        pred_frames.append(va)
        rmse = mean_squared_error(va["target"], va["predicted_score"]) ** 0.5
        mae = mean_absolute_error(va["target"], va["predicted_score"])
        grouped = va.groupby(JOIN_KEYS, sort=False)
        selected = pd.DataFrame([score_selected_theta(g) for _, g in grouped])
        fold_rows.append(
            {
                "fold": fold,
                "validation_rows": len(va),
                "validation_instance_groups": grouped.ngroups,
                "rmse": rmse,
                "mae": mae,
                "top1_hit_rate": selected["hit_top1"].mean(),
                "mean_selected_theta_rank": selected["selected_theta_rank"].mean(),
                "mean_regret": selected["regret"].mean(),
            }
        )
    return pd.concat(pred_frames, ignore_index=True), pd.DataFrame(fold_rows)


def feature_importance(model: Pipeline, numeric: list[str], categorical: list[str]) -> pd.DataFrame:
    prep = model.named_steps["preprocess"]
    rf = model.named_steps["model"]
    names: list[str] = []
    names.extend(numeric)
    if categorical:
        encoder = prep.named_transformers_["cat"]
        names.extend(encoder.get_feature_names_out(categorical).tolist())
    importance = rf.feature_importances_
    return pd.DataFrame({"feature": names, "importance": importance}).sort_values(
        "importance", ascending=False
    )


def build_assignment(
    model: Pipeline,
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
        tiled["predicted_score"] = model.predict(tiled[numeric + categorical])
        tiled["predicted_rank"] = (
            tiled["predicted_score"].rank(method="first", ascending=False).astype(int)
        )
        all_scores.append(tiled.copy())
        best = tiled.sort_values("predicted_score", ascending=False).iloc[0]
        rows.append(
            {
                "split": best["split"],
                "instance": best["instance"],
                "assets": int(best["assets"]),
                "K": int(best["K"]),
                "k_ratio": float(best["k_ratio"]),
                "theta_index": int(theta.index[theta["method"] == best["method"]][0]) + 1,
                "theta_id": best["method"],
                "predicted_score": float(best["predicted_score"]),
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
    root = workspace_root()
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--assignment-manifest", type=Path, default=DEFAULT_ASSIGNMENT_MANIFEST)
    parser.add_argument("--theta", type=Path, default=theta_excel_default(root))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=20260713)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--assignment-splits", default="test")
    return parser.parse_args()


def main() -> None:
    root = workspace_root()
    args = parse_args()
    labels_path = resolve(args.labels, root)
    manifest_path = resolve(args.manifest, root)
    assignment_manifest_path = resolve(args.assignment_manifest, root)
    theta_path = resolve(args.theta, root)
    output_dir = resolve(args.output_dir, root)
    output_dir.mkdir(parents=True, exist_ok=True)

    labels = pd.read_csv(labels_path)
    manifest = load_manifest(manifest_path)
    assignment_manifest = load_manifest(assignment_manifest_path)
    theta = load_theta_table(theta_path)
    train = prepare_training(labels, manifest)
    numeric, categorical = feature_columns(train)

    cv_predictions, cv_summary = cross_validate(train, numeric, categorical, args.folds, args.seed)
    final_model = make_model(numeric, categorical, args.seed)
    final_model.fit(train[numeric + categorical], train["target"])

    assignment_splits = [part.strip() for part in args.assignment_splits.split(",") if part.strip()]
    assignment, test_scores = build_assignment(
        final_model, assignment_manifest, theta, numeric, categorical, assignment_splits
    )

    joblib.dump(final_model, output_dir / "meta_learner_random_forest.joblib")
    labels.head(0).to_csv(output_dir / "label_schema.csv", index=False)
    train.to_csv(output_dir / "training_table.csv", index=False, encoding="utf-8-sig")
    cv_predictions.to_csv(output_dir / "cv_predictions.csv", index=False, encoding="utf-8-sig")
    cv_summary.to_csv(output_dir / "cv_summary.csv", index=False, encoding="utf-8-sig")
    feature_importance(final_model, numeric, categorical).to_csv(
        output_dir / "feature_importance.csv", index=False, encoding="utf-8-sig"
    )
    theta.to_csv(output_dir / "theta_candidate_table.csv", index=False, encoding="utf-8-sig")
    assignment.to_csv(output_dir / "meta_designed_theta_assignment.csv", index=False, encoding="utf-8-sig")
    test_scores.to_csv(output_dir / "test_theta_predicted_scores.csv", index=False, encoding="utf-8-sig")
    with (output_dir / "feature_columns.json").open("w", encoding="utf-8") as f:
        json.dump({"numeric": numeric, "categorical": categorical}, f, indent=2)
    with (output_dir / "training_config.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "labels": str(labels_path),
                "manifest": str(manifest_path),
                "assignment_manifest": str(assignment_manifest_path),
                "theta": str(theta_path),
                "target": "-LabelScore",
                "group_cv": "GroupKFold by instance|K",
                "assignment_splits": assignment_splits,
                "rows": int(len(train)),
                "instance_groups": int((train["instance"].astype(str) + "|K" + train["K"].astype(str)).nunique()),
            },
            f,
            indent=2,
        )

    print(f"OUTPUT={output_dir}")
    print(cv_summary.to_string(index=False))
    print(f"assignment_rows={len(assignment)}")
    print("assignment theta counts:")
    print(assignment["theta_id"].value_counts().to_string())


if __name__ == "__main__":
    main()
