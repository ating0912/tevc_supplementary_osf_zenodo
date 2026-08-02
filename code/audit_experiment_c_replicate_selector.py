"""Retrain Experiment C selector with and without the replicate feature.

The audit intentionally retrains both models from labels/manifests instead of
editing feature-importance rows after the fact.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from train_experiment_c_stability_selector import (
    DEFAULT_ASSIGNMENT_MANIFEST,
    DEFAULT_MANIFEST_701515,
    DEFAULT_TRAIN_LABELS,
    DEFAULT_VALIDATION_LABELS,
    INSTANCE_CATEGORICAL,
    INSTANCE_NUMERIC,
    JOIN_KEYS,
    THETA_CATEGORICAL,
    THETA_NUMERIC,
    build_assignment,
    feature_importance,
    load_manifest,
    make_model,
    prepare_labels,
    predict_rows,
    select_by_prediction,
    summarize_validation,
    theta_candidates_from_labels,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = Path("outputs/experiment_c_replicate_audit_20260730")
OLD_SELECTOR_DIR = Path("p0_lite_outputs/experiment_c_stability_selector_training")
OLD_TEST_COMPARISON = Path(
    "p0_lite_outputs/experiment_c_stability_comparison_20260717/overall_configuration_comparison.csv"
)
EXPERIMENT_C_METHOD = "ExperimentC_StabilityAware_ECMADE_MOO"

VARIANTS = {
    "full_selector_no_replicate": {
        "label": "Full Selector (replicate removed)",
        "include_replicate": False,
        "drop_instance": False,
        "drop_theta": False,
        "shuffle_labels": False,
        "official_candidate": True,
    },
    "replicate_included_audit": {
        "label": "Replicate-included audit",
        "include_replicate": True,
        "drop_instance": False,
        "drop_theta": False,
        "shuffle_labels": False,
        "official_candidate": False,
    },
}

ABLATION_VARIANTS = {
    "full_selector_no_replicate": {
        "label": "Full Selector (replicate removed)",
        "include_replicate": False,
        "drop_instance": False,
        "drop_theta": False,
        "shuffle_labels": False,
    },
    "no_instance_features": {
        "label": "No instance features",
        "include_replicate": False,
        "drop_instance": True,
        "drop_theta": False,
        "shuffle_labels": False,
    },
    "no_theta_features": {
        "label": "No theta features",
        "include_replicate": False,
        "drop_instance": False,
        "drop_theta": True,
        "shuffle_labels": False,
    },
    "randomized_labels": {
        "label": "Randomized labels",
        "include_replicate": False,
        "drop_instance": False,
        "drop_theta": False,
        "shuffle_labels": True,
    },
}


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def feature_columns(
    frame: pd.DataFrame,
    *,
    include_replicate: bool,
    drop_instance: bool = False,
    drop_theta: bool = False,
) -> tuple[list[str], list[str]]:
    instance_numeric = list(INSTANCE_NUMERIC)
    if not include_replicate:
        instance_numeric = [col for col in instance_numeric if col != "replicate"]

    numeric: list[str] = []
    categorical: list[str] = []
    if not drop_instance:
        numeric.extend([col for col in instance_numeric if col in frame.columns])
        categorical.extend([col for col in INSTANCE_CATEGORICAL if col in frame.columns])
    if not drop_theta:
        numeric.extend([col for col in THETA_NUMERIC if col in frame.columns])
        categorical.extend([col for col in THETA_CATEGORICAL if col in frame.columns])
    return numeric, categorical


def infer_base_feature(transformed_feature: str, raw_features: list[str]) -> str:
    if "__" in transformed_feature:
        transformed_feature = transformed_feature.split("__", 1)[1]
    if transformed_feature in raw_features:
        return transformed_feature
    for raw in sorted(raw_features, key=len, reverse=True):
        if transformed_feature.startswith(raw + "_"):
            return raw
    return transformed_feature


def train_variant(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    assignment_manifest: pd.DataFrame,
    theta: pd.DataFrame,
    spec: dict,
    seed: int,
) -> dict:
    numeric, categorical = feature_columns(
        train,
        include_replicate=bool(spec["include_replicate"]),
        drop_instance=bool(spec["drop_instance"]),
        drop_theta=bool(spec["drop_theta"]),
    )
    if not numeric and not categorical:
        raise RuntimeError(f"{spec['label']} has no features.")

    target = train["target"].to_numpy(dtype=float)
    train_frame = train.copy()
    if spec.get("shuffle_labels"):
        rng = np.random.default_rng(seed)
        train_frame["target"] = rng.permutation(target)

    model = make_model(numeric, categorical, seed)
    model.fit(train_frame[numeric + categorical], train_frame["target"])

    validation_predictions = predict_rows(model, validation, numeric, categorical)
    validation_selection = select_by_prediction(validation_predictions)
    validation_summary = summarize_validation(validation_selection, validation_predictions)

    y_true = validation_predictions["target"].to_numpy(dtype=float)
    y_pred = validation_predictions["predicted_C_LabelScore"].to_numpy(dtype=float)
    row_metrics = {
        "rmse": float(mean_squared_error(y_true, y_pred) ** 0.5),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }

    assignment, test_scores = build_assignment(
        model,
        assignment_manifest,
        theta,
        numeric,
        categorical,
        ["test"],
    )
    return {
        "model": model,
        "numeric": numeric,
        "categorical": categorical,
        "validation_predictions": validation_predictions,
        "validation_selection": validation_selection,
        "validation_summary": validation_summary,
        "assignment": assignment,
        "test_scores": test_scores,
        "row_metrics": row_metrics,
    }


def selector_summary_row(variant_key: str, spec: dict, result: dict) -> dict:
    summary = result["validation_summary"]
    selector = summary[summary["selector"].eq("ExperimentC_StabilityAware")].iloc[0]
    corrected = corrected_selection_metrics(result["validation_predictions"])
    row = {
        "variant": variant_key,
        "label": spec["label"],
        "include_replicate": bool(spec["include_replicate"]),
        "drop_instance": bool(spec["drop_instance"]),
        "drop_theta": bool(spec["drop_theta"]),
        "shuffle_labels": bool(spec["shuffle_labels"]),
        "validation_groups": int(selector["groups"]),
        "top1_hit_rate": corrected["top1_hit_rate"],
        "top3_hit_rate": corrected["top3_hit_rate"],
        "mean_target_rank": corrected["mean_target_rank"],
        "mean_C_regret": corrected["mean_C_regret"],
        "mean_C_LabelScore": corrected["mean_C_LabelScore"],
        "mean_PF_Overlap": corrected["mean_PF_Overlap"],
        "mean_PF_Drift": corrected["mean_PF_Drift"],
        "mean_HV": corrected["mean_HV"],
        "mean_IGD": corrected["mean_IGD"],
        "legacy_top1_hit_rate_from_C_ThetaRank_le1": float(selector["top1_hit_rate"]),
        "legacy_top3_hit_rate_from_C_ThetaRank_le3": float(selector["top3_hit_rate"]),
        "legacy_mean_C_ThetaRank_raw": float(selector["mean_C_ThetaRank"]),
        **result["row_metrics"],
        "numeric_features": ";".join(result["numeric"]),
        "categorical_features": ";".join(result["categorical"]),
    }
    return row


def corrected_selection_metrics(predictions: pd.DataFrame) -> dict[str, float]:
    rows = []
    for _, group in predictions.groupby(JOIN_KEYS, sort=False):
        frame = group.copy()
        frame["target_rank_desc"] = frame["C_LabelScore"].rank(method="min", ascending=False)
        selected = frame.sort_values(["predicted_C_LabelScore", "method"], ascending=[False, True]).iloc[0]
        best_score = float(frame["C_LabelScore"].max())
        rows.append(
            {
                "target_rank": float(selected["target_rank_desc"]),
                "hit_top1": float(selected["target_rank_desc"] == 1),
                "hit_top3": float(selected["target_rank_desc"] <= 3),
                "regret": best_score - float(selected["C_LabelScore"]),
                "C_LabelScore": float(selected["C_LabelScore"]),
                "PF_Overlap": float(selected["PF_Overlap"]),
                "PF_Drift": float(selected["PF_Drift"]),
                "HV": float(selected["HV"]),
                "IGD": float(selected["IGD"]),
            }
        )
    selected = pd.DataFrame(rows)
    return {
        "top1_hit_rate": float(selected["hit_top1"].mean()),
        "top3_hit_rate": float(selected["hit_top3"].mean()),
        "mean_target_rank": float(selected["target_rank"].mean()),
        "mean_C_regret": float(selected["regret"].mean()),
        "mean_C_LabelScore": float(selected["C_LabelScore"].mean()),
        "mean_PF_Overlap": float(selected["PF_Overlap"].mean()),
        "mean_PF_Drift": float(selected["PF_Drift"].mean()),
        "mean_HV": float(selected["HV"].mean()),
        "mean_IGD": float(selected["IGD"].mean()),
    }


def write_importance_outputs(
    result: dict,
    out_dir: Path,
    variant_key: str,
    seed: int,
) -> pd.DataFrame:
    model = result["model"]
    numeric = result["numeric"]
    categorical = result["categorical"]
    raw_features = numeric + categorical
    validation = result["validation_predictions"]
    variant_dir = out_dir / variant_key
    variant_dir.mkdir(parents=True, exist_ok=True)

    transformed = feature_importance(model, numeric, categorical)
    transformed["base_feature"] = transformed["feature"].map(lambda f: infer_base_feature(f, raw_features))
    transformed.to_csv(variant_dir / "feature_importance_transformed.csv", index=False, encoding="utf-8-sig")

    grouped = (
        transformed.groupby("base_feature", as_index=False)
        .agg(
            impurity_importance_sum=("importance", "sum"),
            transformed_terms=("feature", "count"),
        )
        .sort_values("impurity_importance_sum", ascending=False)
        .reset_index(drop=True)
    )

    perm = permutation_importance(
        model,
        validation[raw_features],
        validation["target"],
        scoring="r2",
        n_repeats=5,
        random_state=seed,
        n_jobs=1,
    )
    permutation = pd.DataFrame(
        {
            "base_feature": raw_features,
            "permutation_importance_mean_r2_drop": perm.importances_mean,
            "permutation_importance_std": perm.importances_std,
        }
    )
    combined = (
        permutation.merge(grouped, on="base_feature", how="left")
        .sort_values("permutation_importance_mean_r2_drop", ascending=False)
        .reset_index(drop=True)
    )
    combined.to_csv(variant_dir / "feature_importance_grouped.csv", index=False, encoding="utf-8-sig")
    plot_importance(combined, variant_dir / "feature_importance_grouped.png", str(variant_key))
    return combined


def plot_importance(frame: pd.DataFrame, path: Path, title: str) -> None:
    top = frame.head(16).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8.8, 5.6))
    ax.barh(top["base_feature"], top["permutation_importance_mean_r2_drop"], color="#2f6fbb")
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_xlabel("Permutation importance (R2 drop)")
    ax.set_title(title)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def theta_distribution(frame: pd.DataFrame, variant_key: str, source: str, theta_col: str) -> pd.DataFrame:
    counts = frame[theta_col].value_counts().sort_index()
    total = int(counts.sum())
    return pd.DataFrame(
        {
            "variant": variant_key,
            "source": source,
            "theta_id": counts.index.astype(str),
            "count": counts.to_numpy(dtype=int),
            "share": counts.to_numpy(dtype=float) / total if total else np.nan,
        }
    )


def assignment_diff(left: pd.DataFrame, right: pd.DataFrame, left_name: str, right_name: str) -> pd.DataFrame:
    cols = JOIN_KEYS + ["theta_id", "predicted_score"]
    merged = left[cols].merge(right[cols], on=JOIN_KEYS, suffixes=(f"_{left_name}", f"_{right_name}"))
    merged["theta_changed"] = merged[f"theta_id_{left_name}"] != merged[f"theta_id_{right_name}"]
    return merged.sort_values(JOIN_KEYS).reset_index(drop=True)


def validation_selection_diff(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    cols = JOIN_KEYS + ["selected_theta", "selected_C_LabelScore", "selected_C_ThetaRank", "C_regret"]
    merged = left[cols].merge(right[cols], on=JOIN_KEYS, suffixes=("_no_replicate", "_replicate_included"))
    merged["theta_changed"] = merged["selected_theta_no_replicate"] != merged["selected_theta_replicate_included"]
    return merged.sort_values(JOIN_KEYS).reset_index(drop=True)


def test_metrics_for_variant(assignment: pd.DataFrame, old_assignment: pd.DataFrame, old_overall: pd.DataFrame) -> dict:
    diff = assignment_diff(assignment, old_assignment, "new", "old")
    changed = int(diff["theta_changed"].sum())
    row = {
        "test_assignment_groups": int(len(diff)),
        "test_assignment_changed_groups_vs_previous_official": changed,
        "test_metrics_source": "unavailable_new_final_test_required" if changed else "previous_official_final_test_reused",
        "test_overall_RankScore": np.nan,
        "test_mean_RankScore": np.nan,
        "test_mean_PF_Overlap": np.nan,
        "test_mean_PF_Drift": np.nan,
    }
    if changed == 0 and not old_overall.empty:
        c_row = old_overall[old_overall["method"].eq(EXPERIMENT_C_METHOD)]
        if not c_row.empty:
            rec = c_row.iloc[0]
            row.update(
                {
                    "test_overall_RankScore": float(rec["overall_RankScore"]),
                    "test_mean_RankScore": float(rec["mean_RankScore"]),
                    "test_mean_PF_Overlap": float(rec["mean_PF_Overlap"]),
                    "test_mean_PF_Drift": float(rec["mean_PF_Drift"]),
                }
            )
    return row


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-labels", type=Path, default=DEFAULT_TRAIN_LABELS)
    parser.add_argument("--validation-labels", type=Path, default=DEFAULT_VALIDATION_LABELS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_701515)
    parser.add_argument("--assignment-manifest", type=Path, default=DEFAULT_ASSIGNMENT_MANIFEST)
    parser.add_argument("--old-selector-dir", type=Path, default=OLD_SELECTOR_DIR)
    parser.add_argument("--old-test-comparison", type=Path, default=OLD_TEST_COMPARISON)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=20260717)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = resolve(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train_labels = read_csv(resolve(args.train_labels))
    validation_labels = read_csv(resolve(args.validation_labels))
    manifest = load_manifest(resolve(args.manifest))
    assignment_manifest = load_manifest(resolve(args.assignment_manifest))
    theta = theta_candidates_from_labels(train_labels)
    train = prepare_labels(train_labels, manifest)
    validation = prepare_labels(validation_labels, manifest)

    old_selector_dir = resolve(args.old_selector_dir)
    old_assignment = read_csv(old_selector_dir / "experiment_c_stability_theta_assignment.csv")
    old_overall_path = resolve(args.old_test_comparison)
    old_overall = read_csv(old_overall_path) if old_overall_path.exists() else pd.DataFrame()

    results: dict[str, dict] = {}
    all_summaries = []
    all_test_rows = []
    all_theta_dist = []
    all_importance_rows = []

    for variant_key, spec in VARIANTS.items():
        result = train_variant(train, validation, assignment_manifest, theta, spec, args.seed)
        results[variant_key] = result
        variant_dir = out_dir / variant_key
        variant_dir.mkdir(parents=True, exist_ok=True)

        joblib.dump(result["model"], variant_dir / "experiment_c_stability_random_forest.joblib")
        result["validation_predictions"].to_csv(variant_dir / "validation_predictions.csv", index=False, encoding="utf-8-sig")
        result["validation_selection"].to_csv(variant_dir / "validation_theta_selection.csv", index=False, encoding="utf-8-sig")
        result["validation_summary"].to_csv(variant_dir / "validation_selector_summary.csv", index=False, encoding="utf-8-sig")
        result["assignment"].to_csv(variant_dir / "experiment_c_stability_theta_assignment.csv", index=False, encoding="utf-8-sig")
        result["test_scores"].to_csv(variant_dir / "test_theta_predicted_scores.csv", index=False, encoding="utf-8-sig")
        with (variant_dir / "feature_columns.json").open("w", encoding="utf-8") as fh:
            json.dump({"numeric": result["numeric"], "categorical": result["categorical"]}, fh, indent=2)

        importance = write_importance_outputs(result, out_dir, variant_key, args.seed + 100)
        importance["variant"] = variant_key
        all_importance_rows.append(importance)

        summary_row = selector_summary_row(variant_key, spec, result)
        test_row = test_metrics_for_variant(result["assignment"], old_assignment, old_overall)
        all_test_rows.append({"variant": variant_key, **test_row})
        all_summaries.append({**summary_row, **{k: v for k, v in test_row.items() if k.startswith("test_")}})
        all_theta_dist.append(theta_distribution(result["validation_selection"], variant_key, "validation_selection", "selected_theta"))
        all_theta_dist.append(theta_distribution(result["assignment"], variant_key, "test_assignment", "theta_id"))

    comparison = pd.DataFrame(all_summaries)
    comparison.to_csv(out_dir / "replicate_audit_validation_test_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(all_test_rows).to_csv(out_dir / "replicate_audit_test_metric_availability.csv", index=False, encoding="utf-8-sig")
    pd.concat(all_theta_dist, ignore_index=True).to_csv(out_dir / "theta_selection_distribution.csv", index=False, encoding="utf-8-sig")
    pd.concat(all_importance_rows, ignore_index=True).to_csv(out_dir / "feature_importance_all_variants.csv", index=False, encoding="utf-8-sig")

    assignment_diff(
        results["full_selector_no_replicate"]["assignment"],
        results["replicate_included_audit"]["assignment"],
        "no_replicate",
        "replicate_included",
    ).to_csv(out_dir / "test_assignment_diff_no_replicate_vs_replicate.csv", index=False, encoding="utf-8-sig")
    validation_selection_diff(
        results["full_selector_no_replicate"]["validation_selection"],
        results["replicate_included_audit"]["validation_selection"],
    ).to_csv(out_dir / "validation_selection_diff_no_replicate_vs_replicate.csv", index=False, encoding="utf-8-sig")

    ablation_rows = []
    for variant_key, spec in ABLATION_VARIANTS.items():
        result = train_variant(train, validation, assignment_manifest, theta, spec, args.seed)
        ablation_rows.append(selector_summary_row(variant_key, spec, result))
    pd.DataFrame(ablation_rows).to_csv(out_dir / "feature_group_ablation_validation_summary.csv", index=False, encoding="utf-8-sig")

    protocol = {
        "purpose": "Experiment C replicate feature audit and no-replicate retraining",
        "seed": args.seed,
        "train_labels": str(resolve(args.train_labels)),
        "validation_labels": str(resolve(args.validation_labels)),
        "manifest": str(resolve(args.manifest)),
        "assignment_manifest": str(resolve(args.assignment_manifest)),
        "old_selector_dir": str(old_selector_dir),
        "old_test_comparison": str(old_overall_path),
        "variants": VARIANTS,
        "feature_group_ablation_variants": ABLATION_VARIANTS,
        "test_metric_rule": "Reuse previous Experiment C final-test metrics only when the new test theta assignment is identical to the previous official assignment.",
    }
    with (out_dir / "replicate_audit_protocol.json").open("w", encoding="utf-8") as fh:
        json.dump(protocol, fh, indent=2)

    print(f"OUT_DIR={out_dir}")
    print(comparison[[
        "variant",
        "top1_hit_rate",
        "top3_hit_rate",
        "mean_target_rank",
        "mean_C_regret",
        "rmse",
        "mae",
        "test_assignment_changed_groups_vs_previous_official",
        "test_overall_RankScore",
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
