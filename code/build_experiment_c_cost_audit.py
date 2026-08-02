from __future__ import annotations

import json
import platform
import subprocess
import sys
from pathlib import Path
from time import perf_counter

import pandas as pd

from train_experiment_c_stability_selector import (
    DEFAULT_ASSIGNMENT_MANIFEST,
    DEFAULT_MANIFEST_701515,
    DEFAULT_TRAIN_LABELS,
    DEFAULT_VALIDATION_LABELS,
    build_assignment,
    feature_columns,
    prepare_labels,
    resolve,
    theta_candidates_from_labels,
    workspace_root,
)
from train_meta_designed_ecmade_moo import load_manifest, make_model


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs" / "experiment_c_cost_audit_20260801"
TRAIN_RUN_METRICS = (
    ROOT
    / "p0_lite_outputs"
    / "theta24_70_15_15_training_label_full_20260706"
    / "knowledge_base_parameter_report"
    / "run_metrics.csv"
)
VALIDATION_RUN_METRICS = (
    ROOT
    / "p0_lite_outputs"
    / "theta24_70_15_15_validation_label_full_20260713"
    / "knowledge_base_parameter_report"
    / "run_metrics.csv"
)
FINAL_FIVE_RUN_METRICS = (
    ROOT
    / "p0_lite_outputs"
    / "experiment_c_formal_five_method_no_replicate_20260731"
    / "formal_five_run_metrics.csv"
)
PRIMARY_METHOD = "ExperimentC_NoReplicate_ECMADE_MOO"


def seconds_to_hms(seconds: float) -> str:
    seconds = float(seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:05.2f}"


def timed(label: str, func):
    start = perf_counter()
    value = func()
    elapsed = perf_counter() - start
    print(f"{label}: {elapsed:.3f}s")
    return value, elapsed


def read_run_metrics(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def optimizer_stage(
    stage: str,
    df: pd.DataFrame,
    execution_count: str,
    environment: str,
    source: str,
    notes: str,
) -> dict:
    groups = df[["instance", "K"]].drop_duplicates().shape[0]
    total_runs = len(df)
    total_seconds = float(df["Runtime"].sum())
    return {
        "stage": stage,
        "execution_count": execution_count,
        "total_seconds": total_seconds,
        "total_hms": seconds_to_hms(total_seconds),
        "average_seconds": total_seconds / total_runs if total_runs else float("nan"),
        "average_unit": "per optimizer run",
        "groups": groups,
        "runs": total_runs,
        "environment": environment,
        "measurement_source": source,
        "cost_record_status": "historical Runtime column available",
        "notes": notes,
    }


def measure_selector_pipeline() -> tuple[list[dict], dict]:
    root = workspace_root()
    seed = 20260717

    def load_inputs():
        train_labels = pd.read_csv(resolve(DEFAULT_TRAIN_LABELS, root), encoding="utf-8-sig")
        validation_labels = pd.read_csv(resolve(DEFAULT_VALIDATION_LABELS, root), encoding="utf-8-sig")
        manifest = load_manifest(resolve(DEFAULT_MANIFEST_701515, root))
        assignment_manifest = load_manifest(resolve(DEFAULT_ASSIGNMENT_MANIFEST, root))
        return train_labels, validation_labels, manifest, assignment_manifest

    (train_labels, validation_labels, manifest, assignment_manifest), load_seconds = timed(
        "load selector inputs", load_inputs
    )

    def preprocess():
        theta = theta_candidates_from_labels(train_labels)
        train = prepare_labels(train_labels, manifest)
        validation = prepare_labels(validation_labels, manifest)
        numeric, categorical = feature_columns(train, include_replicate=False)
        return theta, train, validation, numeric, categorical

    (theta, train, validation, numeric, categorical), preprocess_seconds = timed(
        "feature preprocessing", preprocess
    )

    def fit_model():
        model = make_model(numeric, categorical, seed)
        model.fit(train[numeric + categorical], train["target"])
        return model

    model, train_seconds = timed("random forest training", fit_model)

    def recommend():
        return build_assignment(model, assignment_manifest, theta, numeric, categorical, ["test"])

    (assignment, test_scores), recommend_seconds = timed("theta recommendation", recommend)

    stages = [
        {
            "stage": "Feature preprocessing",
            "execution_count": f"{len(train)} training rows + {len(validation)} validation rows",
            "total_seconds": preprocess_seconds,
            "total_hms": seconds_to_hms(preprocess_seconds),
            "average_seconds": preprocess_seconds / (len(train) + len(validation)),
            "average_unit": "per label row",
            "groups": train[["instance", "K"]].drop_duplicates().shape[0]
            + validation[["instance", "K"]].drop_duplicates().shape[0],
            "runs": "",
            "environment": "Python / pandas + scikit-learn preprocessing",
            "measurement_source": "remeasured on 2026-08-01 by build_experiment_c_cost_audit.py",
            "cost_record_status": "no historical wall-clock log; remeasured",
            "notes": f"Input loading measured separately: {load_seconds:.3f}s.",
        },
        {
            "stage": "Selector training",
            "execution_count": "1 RandomForestRegressor fit",
            "total_seconds": train_seconds,
            "total_hms": seconds_to_hms(train_seconds),
            "average_seconds": train_seconds,
            "average_unit": "per selector fit",
            "groups": train[["instance", "K"]].drop_duplicates().shape[0],
            "runs": "",
            "environment": "Python / scikit-learn RandomForestRegressor(n_estimators=500, min_samples_leaf=2, n_jobs=-1)",
            "measurement_source": "remeasured on 2026-08-01 by build_experiment_c_cost_audit.py",
            "cost_record_status": "no historical wall-clock log; remeasured",
            "notes": "No-replicate feature mapping; replicate excluded from model features.",
        },
        {
            "stage": "Theta recommendation",
            "execution_count": f"{len(assignment)} test groups x {len(theta)} theta candidates",
            "total_seconds": recommend_seconds,
            "total_hms": seconds_to_hms(recommend_seconds),
            "average_seconds": recommend_seconds / len(assignment),
            "average_unit": "per test group",
            "groups": len(assignment),
            "runs": "",
            "environment": "Python / trained Random Forest selector",
            "measurement_source": "remeasured on 2026-08-01 by build_experiment_c_cost_audit.py",
            "cost_record_status": "no historical wall-clock log; remeasured",
            "notes": f"Prediction rows={len(test_scores)}.",
        },
    ]
    metadata = {
        "selector_training_rows": int(len(train)),
        "selector_validation_rows": int(len(validation)),
        "theta_candidates": int(len(theta)),
        "test_assignment_rows": int(len(assignment)),
        "raw_feature_count": int(len(numeric) + len(categorical)),
        "numeric_features": numeric,
        "categorical_features": categorical,
        "input_loading_seconds": load_seconds,
    }
    return stages, metadata


def measure_subprocess_stage(stage: str, command: list[str], execution_count: str, environment: str, notes: str) -> dict:
    start = perf_counter()
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True)
    elapsed = perf_counter() - start
    return {
        "stage": stage,
        "execution_count": execution_count,
        "total_seconds": elapsed,
        "total_hms": seconds_to_hms(elapsed),
        "average_seconds": elapsed,
        "average_unit": "per script execution",
        "groups": "",
        "runs": "",
        "environment": environment,
        "measurement_source": "remeasured on 2026-08-01 by build_experiment_c_cost_audit.py",
        "cost_record_status": "no historical wall-clock log; remeasured",
        "notes": notes + f" stdout_tail={completed.stdout[-300:].strip()}",
    }


def environment_metadata() -> dict:
    return {
        "created": "2026-08-01",
        "workspace": str(ROOT),
        "os": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": __import__("os").cpu_count(),
        },
        "python": {
            "executable": sys.executable,
            "version": sys.version,
        },
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    train_metrics = read_run_metrics(TRAIN_RUN_METRICS)
    rows.append(
        optimizer_stage(
            "Label generation",
            train_metrics,
            "134 groups x 24 theta x 30 runs",
            "MATLAB / PlatEMO + ECMADE-MOO",
            str(TRAIN_RUN_METRICS),
            "Historical algorithm Runtime sum for training-label generation.",
        )
    )

    validation_metrics = read_run_metrics(VALIDATION_RUN_METRICS)
    rows.append(
        optimizer_stage(
            "Validation label generation",
            validation_metrics,
            "29 groups x 24 theta x 30 runs",
            "MATLAB / PlatEMO + ECMADE-MOO",
            str(VALIDATION_RUN_METRICS),
            "Auxiliary validation-label cost used for selector validation, separated from the minimum requested training-label row.",
        )
    )

    selector_rows, selector_metadata = measure_selector_pipeline()
    rows.extend(selector_rows)

    final_metrics = read_run_metrics(FINAL_FIVE_RUN_METRICS)
    primary_final = final_metrics[final_metrics["method"].eq(PRIMARY_METHOD)].copy()
    rows.append(
        optimizer_stage(
            "Final optimization",
            primary_final,
            "32 test groups x 30 runs",
            "MATLAB / PlatEMO + ECMADE-MOO",
            str(FINAL_FIVE_RUN_METRICS),
            "Historical algorithm Runtime sum for the formal no-replicate selector final optimization only.",
        )
    )

    rows.append(
        measure_subprocess_stage(
            "Post-processing and common-reference computation",
            [sys.executable, "summarize_experiment_c_formal_five_method.py"],
            "32 test groups; five-method common reference",
            "Python / pandas + scipy",
            "Recomputed formal five-method common-reference front, endpoints, Friedman, and Wilcoxon tables.",
        )
    )

    rows.append(
        measure_subprocess_stage(
            "Feature importance and SHAP computation",
            [sys.executable, "outputs/experiment_c_feature_importance_20260725/compute_selector_importance.py"],
            "1 fitted selector; validation set permutation + TreeSHAP sample",
            "Python / scikit-learn + shap",
            "Recomputed validation metrics, permutation importance, grouped RF impurity, and TreeSHAP tables.",
        )
    )

    df = pd.DataFrame(rows)
    df["total_minutes"] = df["total_seconds"].astype(float) / 60.0
    df["total_hours"] = df["total_seconds"].astype(float) / 3600.0
    df.to_csv(OUT_DIR / "experiment_c_cost_audit_summary.csv", index=False, encoding="utf-8-sig")

    env = environment_metadata()
    env["selector_metadata"] = selector_metadata
    env["runtime_source_note"] = (
        "Optimizer costs are sums of recorded per-run Runtime values, not independently logged script wall-clock times."
    )
    (OUT_DIR / "experiment_c_cost_environment.json").write_text(
        json.dumps(env, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    md = [
        "# Experiment C cost audit",
        "",
        "Optimizer rows use historical per-run Runtime sums. Python rows were remeasured on 2026-08-01.",
        "",
        df[
            [
                "stage",
                "execution_count",
                "total_hms",
                "total_minutes",
                "average_seconds",
                "average_unit",
                "environment",
                "cost_record_status",
            ]
        ].to_markdown(index=False),
        "",
        "## Notes",
        "",
        "- Label-generation wall-clock logs for the original MATLAB batch were not found; the table reports the sum of recorded optimizer Runtime values.",
        "- Python preprocessing, selector training, theta recommendation, post-processing, and feature-importance wall times were remeasured on the same workspace and machine.",
    ]
    (OUT_DIR / "experiment_c_cost_audit_summary.md").write_text("\n".join(md), encoding="utf-8")
    print(f"WROTE={OUT_DIR}")
    print(df[["stage", "execution_count", "total_hms", "average_seconds", "average_unit"]].to_string(index=False))


if __name__ == "__main__":
    main()
