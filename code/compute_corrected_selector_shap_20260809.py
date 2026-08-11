from __future__ import annotations

from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, r2_score


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "outputs" / "tevc_submission_missing_items_v3_20260808"
OUT = ROOT / "outputs" / "corrected_selector_shap_20260809"

MODEL_PATH = SRC / "corrected_experiment_c_selector_random_forest.joblib"
TRAIN_PATH = SRC / "corrected_selector_training_predictions.csv"
VALID_PATH = SRC / "corrected_selector_validation_predictions.csv"
TARGET_COL = "official_C_LabelScore_utility"
PRED_COL = "predicted_corrected_C_LabelScore_utility"
SAMPLE_SEED = 20260808
PERMUTATION_SEED = 20260808
SHAP_SAMPLE_SIZE = 200


def infer_base_feature(transformed_feature: str, raw_features: list[str]) -> str:
    if "__" in transformed_feature:
        transformed_feature = transformed_feature.split("__", 1)[1]
    if transformed_feature in raw_features:
        return transformed_feature
    for raw in sorted(raw_features, key=len, reverse=True):
        if transformed_feature.startswith(raw + "_"):
            return raw
    return transformed_feature


def write_log(lines: list[str]) -> None:
    (OUT / "formal_shap_execution_log.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    model = joblib.load(MODEL_PATH)
    train = pd.read_csv(TRAIN_PATH, encoding="utf-8-sig")
    validation = pd.read_csv(VALID_PATH, encoding="utf-8-sig")

    preprocess = model.named_steps["preprocess"]
    forest = model.named_steps["model"]
    raw_features = list(preprocess.feature_names_in_)

    metrics = []
    for split_name, frame in [("training", train), ("validation", validation)]:
        y = pd.to_numeric(frame[TARGET_COL], errors="coerce")
        pred = model.predict(frame[raw_features])
        metrics.append(
            {
                "split": split_name,
                "rows": int(len(frame)),
                "groups": int(frame[["instance", "K"]].drop_duplicates().shape[0]),
                "r2": float(r2_score(y, pred)),
                "mae": float(mean_absolute_error(y, pred)),
                "rmse": float(np.sqrt(np.mean((y - pred) ** 2))),
                "target": TARGET_COL,
                "prediction_column": PRED_COL,
                "model": str(MODEL_PATH.relative_to(ROOT)),
            }
        )
    pd.DataFrame(metrics).to_csv(OUT / "corrected_selector_model_regression_metrics.csv", index=False, encoding="utf-8-sig")

    X_val = validation[raw_features]
    y_val = pd.to_numeric(validation[TARGET_COL], errors="coerce")
    perm = permutation_importance(
        model,
        X_val,
        y_val,
        scoring="r2",
        n_repeats=10,
        random_state=PERMUTATION_SEED,
        n_jobs=1,
    )
    permutation = (
        pd.DataFrame(
            {
                "feature": raw_features,
                "permutation_importance_mean_r2_drop": perm.importances_mean,
                "permutation_importance_std": perm.importances_std,
                "n_repeats": 10,
                "random_state": PERMUTATION_SEED,
            }
        )
        .sort_values("permutation_importance_mean_r2_drop", ascending=False)
        .reset_index(drop=True)
    )
    permutation.to_csv(OUT / "corrected_grouped_permutation_importance.csv", index=False, encoding="utf-8-sig")

    transformed_features = list(preprocess.get_feature_names_out())
    impurity = pd.DataFrame(
        {
            "feature": transformed_features,
            "impurity_importance": forest.feature_importances_,
        }
    )
    impurity["base_feature"] = impurity["feature"].map(lambda f: infer_base_feature(f, raw_features))
    impurity.to_csv(OUT / "corrected_impurity_importance_transformed.csv", index=False, encoding="utf-8-sig")
    (
        impurity.groupby("base_feature", as_index=False)
        .agg(impurity_importance_sum=("impurity_importance", "sum"), transformed_terms=("feature", "count"))
        .sort_values("impurity_importance_sum", ascending=False)
        .reset_index(drop=True)
        .to_csv(OUT / "corrected_grouped_impurity_importance.csv", index=False, encoding="utf-8-sig")
    )

    sample_size = min(SHAP_SAMPLE_SIZE, len(validation))
    sample = validation.sample(n=sample_size, random_state=SAMPLE_SEED).sort_index()
    sample[["instance", "K", "method", TARGET_COL, PRED_COL]].to_csv(
        OUT / "corrected_shap_sample_manifest.csv",
        index=True,
        index_label="source_row",
        encoding="utf-8-sig",
    )

    log_lines = [
        "Corrected selector SHAP execution log",
        f"run_timestamp_local={datetime.now().isoformat(timespec='seconds')}",
        f"status=started",
        f"model={MODEL_PATH.relative_to(ROOT)}",
        f"training_predictions={TRAIN_PATH.relative_to(ROOT)}",
        f"validation_predictions={VALID_PATH.relative_to(ROOT)}",
        f"target={TARGET_COL}",
        f"prediction_column={PRED_COL}",
        f"validation_population_rows={len(validation)}",
        f"validation_groups={validation[['instance', 'K']].drop_duplicates().shape[0]}",
        f"shap_sample_rows={sample_size}",
        f"shap_sampling_seed={SAMPLE_SEED}",
        f"permutation_seed={PERMUTATION_SEED}",
        f"raw_features={len(raw_features)}",
        f"transformed_features={len(transformed_features)}",
        "raw_feature_names=" + "|".join(raw_features),
    ]

    try:
        import shap  # type: ignore

        transformed = preprocess.transform(sample[raw_features])
        explainer = shap.TreeExplainer(forest)
        shap_values = explainer.shap_values(transformed)
        if isinstance(shap_values, list):
            shap_values = shap_values[0]
        shap_values = np.asarray(shap_values)

        shap_global = pd.DataFrame(
            {
                "feature": transformed_features,
                "mean_abs_shap": np.mean(np.abs(shap_values), axis=0),
                "mean_shap": np.mean(shap_values, axis=0),
            }
        ).sort_values("mean_abs_shap", ascending=False)
        shap_global["base_feature"] = shap_global["feature"].map(lambda f: infer_base_feature(f, raw_features))
        shap_global.to_csv(OUT / "corrected_shap_importance_transformed.csv", index=False, encoding="utf-8-sig")

        grouped = (
            shap_global.groupby("base_feature", as_index=False)
            .agg(
                mean_abs_shap_sum=("mean_abs_shap", "sum"),
                mean_shap_sum=("mean_shap", "sum"),
                transformed_terms=("feature", "count"),
            )
            .sort_values("mean_abs_shap_sum", ascending=False)
            .reset_index(drop=True)
        )
        grouped.to_csv(OUT / "corrected_grouped_shap_importance.csv", index=False, encoding="utf-8-sig")
        status = (
            "SHAP completed successfully.\n"
            "adopted_result=corrected_selector_shap_20260809\n"
            f"Validation population rows: {len(validation)}\n"
            f"Validation groups: {validation[['instance', 'K']].drop_duplicates().shape[0]}\n"
            f"SHAP sample rows: {sample_size}\n"
            f"Sampling seed: {SAMPLE_SEED}\n"
            f"Transformed features: {len(transformed_features)}\n"
            f"Target: {TARGET_COL}\n"
            f"Model: {MODEL_PATH.relative_to(ROOT)}\n"
        )
        (OUT / "shap_status.txt").write_text(status, encoding="utf-8")
        log_lines.append("status=completed")
    except Exception as exc:
        (OUT / "shap_status.txt").write_text(
            "SHAP failed.\n" f"Error: {type(exc).__name__}: {exc}\n",
            encoding="utf-8",
        )
        log_lines.append("status=failed")
        log_lines.append(f"error={type(exc).__name__}: {exc}")
        write_log(log_lines)
        raise

    write_log(log_lines)
    print(f"OUT_DIR={OUT}")
    print(status)


if __name__ == "__main__":
    main()
