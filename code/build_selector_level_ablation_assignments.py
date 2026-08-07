from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs" / "selector_level_ablation_20260728"
TRAIN_LABELS = (
    ROOT
    / "p0_lite_outputs"
    / "theta24_70_15_15_training_label_full_20260706"
    / "knowledge_base_parameter_report"
    / "experiment_c_stability_regression_labels.csv"
)
MANIFEST = ROOT / "data" / "synthetic_constrained_portfolio" / "manifest_70_15_15.csv"
ASSIGNMENT_MANIFEST = ROOT / "data" / "synthetic_constrained_portfolio" / "manifest.csv"
THETA_TABLE = ROOT / "p0_lite_outputs" / "experiment_c_stability_selector_training" / "theta_candidate_table.csv"

INSTANCE_NUMERIC = ["assets", "days", "k_ratio", "K"]
INSTANCE_CATEGORICAL = ["split", "corr_structure", "return_distribution", "risk_structure"]
THETA_NUMERIC = ["subpops", "eliteRatio", "stagnationThreshold", "theta", "archiveLimitFactor"]
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

VARIANTS = {
    "FullSelector": {
        "method": "SelectorAblation_FullSelector_ECMADE_MOO",
        "drop_instance": False,
        "drop_theta": False,
        "shuffle_labels": False,
    },
    "NoInstanceFeatures": {
        "method": "SelectorAblation_NoInstanceFeatures_ECMADE_MOO",
        "drop_instance": True,
        "drop_theta": False,
        "shuffle_labels": False,
    },
    "NoThetaFeatures": {
        "method": "SelectorAblation_NoThetaFeatures_ECMADE_MOO",
        "drop_instance": False,
        "drop_theta": True,
        "shuffle_labels": False,
    },
    "RandomizedLabels": {
        "method": "SelectorAblation_RandomizedLabels_ECMADE_MOO",
        "drop_instance": False,
        "drop_theta": False,
        "shuffle_labels": True,
    },
}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


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


def feature_columns(frame: pd.DataFrame, drop_instance: bool, drop_theta: bool) -> tuple[list[str], list[str]]:
    numeric: list[str] = []
    categorical: list[str] = []
    if not drop_instance:
        numeric += [c for c in INSTANCE_NUMERIC if c in frame.columns]
        categorical += [c for c in INSTANCE_CATEGORICAL if c in frame.columns]
    if not drop_theta:
        numeric += [c for c in THETA_NUMERIC if c in frame.columns]
        categorical += [c for c in THETA_CATEGORICAL if c in frame.columns]
    return numeric, categorical


def prepare_training(seed: int, shuffle_labels: bool) -> pd.DataFrame:
    labels = read_csv(TRAIN_LABELS)
    manifest = read_csv(MANIFEST)
    train = labels.merge(manifest, on=JOIN_KEYS, how="left", suffixes=("", "_manifest"))
    if train["assets"].isna().any():
        missing = int(train["assets"].isna().sum())
        raise RuntimeError(f"{missing} training label rows did not match manifest by {JOIN_KEYS}")
    for col in INSTANCE_NUMERIC + THETA_NUMERIC:
        if col in train.columns:
            train[col] = pd.to_numeric(train[col], errors="coerce")
    target = pd.to_numeric(train["C_LabelScore"], errors="coerce").to_numpy(dtype=float)
    if shuffle_labels:
        rng = np.random.default_rng(seed)
        target = rng.permutation(target)
    train["target"] = target
    return train


def build_test_grid(theta: pd.DataFrame) -> pd.DataFrame:
    manifest = read_csv(ASSIGNMENT_MANIFEST)
    test = manifest[manifest["split"].eq("test")].copy().reset_index(drop=True)
    rows = []
    for _, inst in test.iterrows():
        tiled = pd.concat([inst.to_frame().T] * len(theta), ignore_index=True)
        grid = pd.concat([tiled.reset_index(drop=True), theta.reset_index(drop=True)], axis=1)
        rows.append(grid)
    out = pd.concat(rows, ignore_index=True)
    for col in INSTANCE_NUMERIC + THETA_NUMERIC:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def assignment_from_predictions(pred: pd.DataFrame, variant_key: str, method: str, theta_index_map: dict[str, int]) -> pd.DataFrame:
    rows = []
    for _, group in pred.groupby(JOIN_KEYS, sort=False):
        best = group.sort_values(["predicted_C_LabelScore", "method"], ascending=[False, True]).iloc[0]
        theta_id = str(best["method"])
        rows.append(
            {
                "split": best["split"],
                "instance": best["instance"],
                "assets": int(best["assets"]),
                "K": int(best["K"]),
                "k_ratio": float(best["k_ratio"]),
                "theta_index": int(theta_index_map[theta_id]),
                "theta_id": theta_id,
                "predicted_score": float(best["predicted_C_LabelScore"]),
                "predicted_C_LabelScore": float(best["predicted_C_LabelScore"]),
                "S": int(best["subpops"]),
                "operator": best["source_operator"],
                "migration": best["source_migration"],
                "elite_ratio": float(best["eliteRatio"]),
                "stagnation_threshold": int(best["stagnationThreshold"]),
                "path": best["path"],
                "selector_ablation_variant": variant_key,
                "method_name": method,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    theta = read_csv(THETA_TABLE).sort_values("method").reset_index(drop=True)
    theta_index_map = {str(row["method"]): idx + 1 for idx, row in theta.iterrows()}
    test_grid = build_test_grid(theta)

    manifest_rows = []
    for offset, (variant_key, spec) in enumerate(VARIANTS.items(), start=1):
        seed = 20260728 + offset
        train = prepare_training(seed, bool(spec["shuffle_labels"]))
        numeric, categorical = feature_columns(train, bool(spec["drop_instance"]), bool(spec["drop_theta"]))
        if not numeric and not categorical:
            raise RuntimeError(f"{variant_key} has no features.")
        model = make_model(numeric, categorical, seed)
        model.fit(train[numeric + categorical], train["target"])
        joblib.dump(model, OUT_DIR / f"{variant_key}.joblib")

        pred = test_grid.copy()
        pred["predicted_C_LabelScore"] = model.predict(pred[numeric + categorical])
        pred["predicted_C_ThetaRank"] = (
            pred.groupby(JOIN_KEYS)["predicted_C_LabelScore"].rank(method="first", ascending=False).astype(int)
        )
        assignment = assignment_from_predictions(pred, variant_key, str(spec["method"]), theta_index_map)
        assignment_path = OUT_DIR / f"{variant_key}_theta_assignment.csv"
        prediction_path = OUT_DIR / f"{variant_key}_test_theta_predicted_scores.csv"
        assignment.to_csv(assignment_path, index=False, encoding="utf-8-sig")
        pred.to_csv(prediction_path, index=False, encoding="utf-8-sig")
        manifest_rows.append(
            {
                "variant": variant_key,
                "method": spec["method"],
                "assignment_path": str(assignment_path),
                "prediction_path": str(prediction_path),
                "drop_instance_features": bool(spec["drop_instance"]),
                "drop_theta_features": bool(spec["drop_theta"]),
                "shuffle_labels": bool(spec["shuffle_labels"]),
                "seed": seed,
                "target": "C_LabelScore",
                "selection_rule": "maximize predicted_C_LabelScore",
                "test_instances": int(assignment[["instance", "K"]].drop_duplicates().shape[0]),
                "numeric_features": ";".join(numeric),
                "categorical_features": ";".join(categorical),
            }
        )

    pd.DataFrame(manifest_rows).to_csv(OUT_DIR / "selector_level_ablation_assignment_manifest.csv", index=False, encoding="utf-8-sig")
    theta.to_csv(OUT_DIR / "theta_candidate_table_used.csv", index=False, encoding="utf-8-sig")
    with (OUT_DIR / "selector_level_ablation_protocol.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "purpose": "formal selector-level final-test ablation for Experiment C",
                "variants": VARIANTS,
                "runs_per_instance_planned": 10,
                "N": 100,
                "maxFE": 10000,
                "test_instances": 32,
                "expected_optimizer_runs": 4 * 32 * 10,
                "target": "C_LabelScore",
            },
            f,
            indent=2,
        )
    print(f"OUT_DIR={OUT_DIR}")
    print(pd.DataFrame(manifest_rows)[["variant", "method", "test_instances", "numeric_features", "categorical_features"]].to_string(index=False))


if __name__ == "__main__":
    main()
