"""Build TEVC ablation tables for feature groups and label objectives.

Outputs:
  outputs/tevc_ablation_4_5_20260717/

The script only reuses completed theta-label tables. It does not launch
MATLAB or create new raw optimization runs.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs" / "tevc_ablation_4_5_20260717"

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
MANIFEST = ROOT / "data" / "synthetic_constrained_portfolio" / "manifest_70_15_15.csv"

INSTANCE_NUMERIC = ["assets", "days", "k_ratio", "K", "replicate"]
INSTANCE_CATEGORICAL = ["split", "corr_structure", "return_distribution", "risk_structure"]
THETA_NUMERIC = [
    "subpops",
    "eliteRatio",
    "stagnationThreshold",
    "theta",
    "archiveLimitFactor",
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
METRIC_COLS = ["HV", "IGD", "PF_Overlap", "PF_Drift", "Diversity", "Runtime"]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def available(cols: list[str], frame: pd.DataFrame) -> list[str]:
    return [c for c in cols if c in frame.columns]


def prepare(labels_path: Path, objective: str) -> pd.DataFrame:
    labels = read_csv(labels_path)
    manifest = read_csv(MANIFEST)
    frame = labels.merge(manifest, on=JOIN_KEYS, how="left", suffixes=("", "_manifest"))
    missing = int(frame["assets"].isna().sum())
    if missing:
        raise RuntimeError(f"{missing} rows from {labels_path} did not match manifest by {JOIN_KEYS}")

    for col in available(INSTANCE_NUMERIC + THETA_NUMERIC + METRIC_COLS, frame):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")

    if objective == "standard_label":
        frame["actual_score"] = -pd.to_numeric(frame["LabelScore"], errors="coerce")
        frame["actual_rank"] = pd.to_numeric(frame["ThetaRank"], errors="coerce")
    elif objective == "stability_label":
        # C_LabelScore is a rank loss: lower is better in the source label files.
        # Use a maximized score internally so selectors share one convention.
        frame["actual_score"] = -pd.to_numeric(frame["C_LabelScore"], errors="coerce")
        frame["actual_rank"] = pd.to_numeric(frame["C_ThetaRank"], errors="coerce")
    elif objective == "performance_only":
        frame["actual_score"] = (
            -pd.to_numeric(frame["rank_HV"], errors="coerce")
            - pd.to_numeric(frame["rank_IGD"], errors="coerce")
        ) / 2.0
        frame["actual_rank"] = (
            frame.groupby(JOIN_KEYS)["actual_score"].rank(method="first", ascending=False).astype(int)
        )
    elif objective == "pf_stability_only":
        frame["actual_score"] = (
            -pd.to_numeric(frame["rank_PF_Overlap"], errors="coerce")
            - pd.to_numeric(frame["rank_PF_Drift"], errors="coerce")
        ) / 2.0
        frame["actual_rank"] = (
            frame.groupby(JOIN_KEYS)["actual_score"].rank(method="first", ascending=False).astype(int)
        )
    else:
        raise ValueError(f"Unknown objective: {objective}")
    return frame


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
    model = RandomForestRegressor(
        n_estimators=500,
        min_samples_leaf=2,
        random_state=seed,
        n_jobs=-1,
    )
    return Pipeline([("preprocess", preprocess), ("model", model)])


def feature_sets(frame: pd.DataFrame) -> dict[str, tuple[list[str], list[str]]]:
    instance_numeric = available(INSTANCE_NUMERIC, frame)
    instance_categorical = available(INSTANCE_CATEGORICAL, frame)
    theta_numeric = available(THETA_NUMERIC, frame)
    theta_categorical = available(THETA_CATEGORICAL, frame)
    return {
        "all_features": (instance_numeric + theta_numeric, instance_categorical + theta_categorical),
        "instance_only_no_theta": (instance_numeric, instance_categorical),
        "theta_only_no_instance": (theta_numeric, theta_categorical),
        "numeric_only": (instance_numeric + theta_numeric, []),
        "categorical_only": ([], instance_categorical + theta_categorical),
        "no_problem_categorical": (instance_numeric + theta_numeric, theta_categorical),
        "no_theta_categorical": (instance_numeric + theta_numeric, instance_categorical),
    }


def select_from_predictions(predictions: pd.DataFrame, selector: str, objective: str) -> pd.DataFrame:
    rows = []
    for (instance, k_value), group in predictions.groupby(JOIN_KEYS, sort=False):
        selected = group.sort_values(["predicted_score", "method"], ascending=[False, True]).iloc[0]
        best = group.sort_values(["actual_score", "method"], ascending=[False, True]).iloc[0]
        all_mean = group[METRIC_COLS].mean(numeric_only=True)
        row = {
            "objective": objective,
            "selector": selector,
            "instance": instance,
            "K": int(k_value),
            "selected_theta": selected["method"],
            "oracle_theta": best["method"],
            "selected_actual_score": float(selected["actual_score"]),
            "oracle_actual_score": float(best["actual_score"]),
            "regret": float(best["actual_score"] - selected["actual_score"]),
            "selected_actual_rank": int(selected["actual_rank"]),
            "hit_top1": float(selected["method"] == best["method"]),
            "hit_top3": float(selected["actual_rank"] <= 3),
        }
        for col in METRIC_COLS:
            row[f"selected_{col}"] = float(selected[col])
            row[f"oracle_{col}"] = float(best[col])
            row[f"all_theta_mean_{col}"] = float(all_mean[col])
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_selection(selection: pd.DataFrame) -> dict[str, float | str | int]:
    row: dict[str, float | str | int] = {
        "objective": selection["objective"].iloc[0],
        "selector": selection["selector"].iloc[0],
        "groups": int(len(selection)),
        "top1_hit_rate": float(selection["hit_top1"].mean()),
        "top3_hit_rate": float(selection["hit_top3"].mean()),
        "mean_selected_rank": float(selection["selected_actual_rank"].mean()),
        "mean_regret": float(selection["regret"].mean()),
        "mean_selected_score": float(selection["selected_actual_score"].mean()),
        "mean_oracle_score": float(selection["oracle_actual_score"].mean()),
    }
    for col in METRIC_COLS:
        row[f"mean_selected_{col}"] = float(selection[f"selected_{col}"].mean())
        row[f"mean_oracle_{col}"] = float(selection[f"oracle_{col}"].mean())
        row[f"mean_all_theta_{col}"] = float(selection[f"all_theta_mean_{col}"].mean())
    return row


def build_feature_group_ablation() -> None:
    rows = []
    selections = []
    for objective, train_path, valid_path in [
        ("standard_label", TRAIN_STANDARD, VALID_STANDARD),
        ("stability_label", TRAIN_C, VALID_C),
    ]:
        train = prepare(train_path, objective)
        valid = prepare(valid_path, objective)
        for index, (name, (numeric, categorical)) in enumerate(feature_sets(train).items(), start=1):
            model = make_model(numeric, categorical, seed=20260717 + index)
            model.fit(train[numeric + categorical], train["actual_score"])
            pred = valid.copy()
            pred["predicted_score"] = model.predict(valid[numeric + categorical])
            pred["predicted_rank"] = (
                pred.groupby(JOIN_KEYS)["predicted_score"].rank(method="first", ascending=False).astype(int)
            )
            rmse = float(mean_squared_error(pred["actual_score"], pred["predicted_score"]) ** 0.5)
            mae = float(mean_absolute_error(pred["actual_score"], pred["predicted_score"]))
            selection = select_from_predictions(pred, name, objective)
            summary = summarize_selection(selection)
            summary.update(
                {
                    "numeric_features": ";".join(numeric),
                    "categorical_features": ";".join(categorical),
                    "n_numeric": len(numeric),
                    "n_categorical": len(categorical),
                    "validation_rows": int(len(pred)),
                    "rmse": rmse,
                    "mae": mae,
                }
            )
            rows.append(summary)
            selections.append(selection)
            pred.to_csv(
                OUT_DIR / f"feature_group_{objective}_{name}_validation_predictions.csv",
                index=False,
                encoding="utf-8-sig",
            )
            joblib.dump(model, OUT_DIR / f"feature_group_{objective}_{name}.joblib")

    pd.DataFrame(rows).to_csv(OUT_DIR / "feature_group_ablation_summary.csv", index=False, encoding="utf-8-sig")
    pd.concat(selections, ignore_index=True).to_csv(
        OUT_DIR / "feature_group_ablation_selection_detail.csv", index=False, encoding="utf-8-sig"
    )


def selector_from_objective(frame: pd.DataFrame, selector: str, objective: str) -> pd.DataFrame:
    pred = frame.copy()
    pred["predicted_score"] = pred["actual_score"]
    if selector == "all_theta_mean":
        rows = []
        for (instance, k_value), group in pred.groupby(JOIN_KEYS, sort=False):
            best = group.sort_values(["actual_score", "method"], ascending=[False, True]).iloc[0]
            all_mean = group[METRIC_COLS].mean(numeric_only=True)
            row = {
                "objective": objective,
                "selector": selector,
                "instance": instance,
                "K": int(k_value),
                "selected_theta": "all_theta_mean",
                "oracle_theta": best["method"],
                "selected_actual_score": float(group["actual_score"].mean()),
                "oracle_actual_score": float(best["actual_score"]),
                "regret": np.nan,
                "selected_actual_rank": float(group["actual_rank"].mean()),
                "hit_top1": np.nan,
                "hit_top3": np.nan,
            }
            for col in METRIC_COLS:
                row[f"selected_{col}"] = float(all_mean[col])
                row[f"oracle_{col}"] = float(best[col])
                row[f"all_theta_mean_{col}"] = float(all_mean[col])
            rows.append(row)
        return pd.DataFrame(rows)
    return select_from_predictions(pred, selector, objective)


def build_label_objective_ablation() -> None:
    valid_standard = prepare(VALID_STANDARD, "standard_label")
    valid_c = prepare(VALID_C, "stability_label")
    valid_perf = prepare(VALID_C, "performance_only")
    valid_pf = prepare(VALID_C, "pf_stability_only")

    selections = [
        selector_from_objective(valid_standard, "standard_label_top1", "standard_label"),
        selector_from_objective(valid_c, "stability_label_top1", "stability_label"),
        selector_from_objective(valid_perf, "performance_only_top1", "performance_only"),
        selector_from_objective(valid_pf, "pf_stability_only_top1", "pf_stability_only"),
        selector_from_objective(valid_c, "all_theta_mean", "all_theta_mean"),
    ]

    summary_rows = [summarize_selection(s) for s in selections]
    pd.DataFrame(summary_rows).to_csv(
        OUT_DIR / "label_objective_ablation_summary.csv", index=False, encoding="utf-8-sig"
    )
    pd.concat(selections, ignore_index=True).to_csv(
        OUT_DIR / "label_objective_ablation_selection_detail.csv", index=False, encoding="utf-8-sig"
    )
    build_label_objective_cross_evaluation(valid_c)


def select_with_rule_for_c_evaluation(frame: pd.DataFrame, selector: str) -> pd.DataFrame:
    rows = []
    for (instance, k_value), group in frame.groupby(JOIN_KEYS, sort=False):
        c_oracle = group.sort_values(["C_LabelScore", "method"], ascending=[True, True]).iloc[0]
        if selector == "standard_label_top1":
            selected = group.sort_values(["LabelScore", "method"], ascending=[True, True]).iloc[0]
            selected_theta = selected["method"]
        elif selector == "stability_label_top1":
            selected = c_oracle
            selected_theta = selected["method"]
        elif selector == "performance_only_top1":
            tmp = group.copy()
            tmp["selector_loss"] = (
                pd.to_numeric(tmp["rank_HV"], errors="coerce")
                + pd.to_numeric(tmp["rank_IGD"], errors="coerce")
            ) / 2.0
            selected = tmp.sort_values(["selector_loss", "method"], ascending=[True, True]).iloc[0]
            selected_theta = selected["method"]
        elif selector == "pf_stability_only_top1":
            tmp = group.copy()
            tmp["selector_loss"] = (
                pd.to_numeric(tmp["rank_PF_Overlap"], errors="coerce")
                + pd.to_numeric(tmp["rank_PF_Drift"], errors="coerce")
            ) / 2.0
            selected = tmp.sort_values(["selector_loss", "method"], ascending=[True, True]).iloc[0]
            selected_theta = selected["method"]
        elif selector == "all_theta_mean":
            selected = None
            selected_theta = "all_theta_mean"
        else:
            raise ValueError(f"Unknown selector: {selector}")

        all_mean = group[METRIC_COLS].mean(numeric_only=True)
        if selected is None:
            selected_c_loss = float(group["C_LabelScore"].mean())
            selected_c_rank = float(group["C_ThetaRank"].mean())
            selected_metrics = {col: float(all_mean[col]) for col in METRIC_COLS}
            hit_top1 = np.nan
            hit_top3 = np.nan
        else:
            selected_c_loss = float(selected["C_LabelScore"])
            selected_c_rank = float(selected["C_ThetaRank"])
            selected_metrics = {col: float(selected[col]) for col in METRIC_COLS}
            hit_top1 = float(selected["method"] == c_oracle["method"])
            hit_top3 = float(float(selected["C_ThetaRank"]) <= 3)

        row = {
            "evaluated_on": "stability_label",
            "selector": selector,
            "instance": instance,
            "K": int(k_value),
            "selected_theta": selected_theta,
            "c_oracle_theta": c_oracle["method"],
            "selected_C_LabelScore_loss": selected_c_loss,
            "c_oracle_C_LabelScore_loss": float(c_oracle["C_LabelScore"]),
            "C_regret_loss": selected_c_loss - float(c_oracle["C_LabelScore"]),
            "selected_C_ThetaRank": selected_c_rank,
            "hit_c_top1": hit_top1,
            "hit_c_top3": hit_top3,
        }
        for col in METRIC_COLS:
            row[f"selected_{col}"] = selected_metrics[col]
            row[f"c_oracle_{col}"] = float(c_oracle[col])
            row[f"all_theta_mean_{col}"] = float(all_mean[col])
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_c_cross(selection: pd.DataFrame) -> dict[str, float | str | int]:
    row: dict[str, float | str | int] = {
        "evaluated_on": "stability_label",
        "selector": selection["selector"].iloc[0],
        "groups": int(len(selection)),
        "c_top1_hit_rate": float(selection["hit_c_top1"].mean()),
        "c_top3_hit_rate": float(selection["hit_c_top3"].mean()),
        "mean_C_ThetaRank": float(selection["selected_C_ThetaRank"].mean()),
        "mean_C_LabelScore_loss": float(selection["selected_C_LabelScore_loss"].mean()),
        "mean_C_regret_loss": float(selection["C_regret_loss"].mean()),
    }
    for col in METRIC_COLS:
        row[f"mean_selected_{col}"] = float(selection[f"selected_{col}"].mean())
        row[f"mean_c_oracle_{col}"] = float(selection[f"c_oracle_{col}"].mean())
        row[f"mean_all_theta_{col}"] = float(selection[f"all_theta_mean_{col}"].mean())
    return row


def build_label_objective_cross_evaluation(valid_c: pd.DataFrame) -> None:
    raw_c = read_csv(VALID_C)
    for col in available(METRIC_COLS, raw_c):
        raw_c[col] = pd.to_numeric(raw_c[col], errors="coerce")
    selectors = [
        "standard_label_top1",
        "stability_label_top1",
        "performance_only_top1",
        "pf_stability_only_top1",
        "all_theta_mean",
    ]
    selections = [select_with_rule_for_c_evaluation(raw_c, selector) for selector in selectors]
    pd.DataFrame([summarize_c_cross(s) for s in selections]).to_csv(
        OUT_DIR / "label_objective_cross_evaluation_on_C_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.concat(selections, ignore_index=True).to_csv(
        OUT_DIR / "label_objective_cross_evaluation_on_C_detail.csv",
        index=False,
        encoding="utf-8-sig",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    build_feature_group_ablation()
    build_label_objective_ablation()
    manifest = {
        "output_dir": str(OUT_DIR),
        "created_from": {
            "train_standard": str(TRAIN_STANDARD),
            "valid_standard": str(VALID_STANDARD),
            "train_stability": str(TRAIN_C),
            "valid_stability": str(VALID_C),
            "manifest": str(MANIFEST),
        },
        "note": (
            "Feature-group ablation retrains RF selectors; label-objective ablation "
            "reuses completed validation label tables only. Cross-evaluation files "
            "compare different selector objectives under the same stability-aware C label."
        ),
    }
    (OUT_DIR / "README.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
