from __future__ import annotations

import json
import platform
import subprocess
import sys
from pathlib import Path
from time import perf_counter

import pandas as pd

from train_meta_designed_ecmade_moo import (
    DEFAULT_ASSIGNMENT_MANIFEST,
    DEFAULT_LABELS,
    DEFAULT_MANIFEST,
    build_assignment,
    cross_validate,
    feature_columns,
    load_manifest,
    make_model,
    prepare_training,
    resolve,
    workspace_root,
)


ROOT = Path(__file__).resolve().parent
P0 = ROOT / "p0_lite_outputs"
OUT_DIR = ROOT / "outputs" / "experiment_ab_cost_audit_20260802"

EXP_A_RUN_METRICS = ROOT / "outputs" / "experiment_A_stats_delivery_20260706" / "experiment_A_run_metrics.csv"
EXP_B_RUN_METRICS = P0 / "experiment_b_configuration_summary_20260713" / "combined_run_metrics_common_reference.csv"
EXP_B_BAYES_CONFIG_RUNS = P0 / "bayesian_config_ecmade_moo_20260713_140251" / "configuration_run_summary.csv"
EXP_B_RANDOM_FINAL_RUNS = P0 / "random_config_ecmade_moo_20260711_074253" / "random_config_run_summary.csv"
EXP_B_META_FINAL_RUNS = P0 / "meta_designed_ecmade_moo_20260713_164632" / "meta_designed_run_summary.csv"
EXP_B_LABEL_RUN_METRICS = (
    P0 / "theta24_70_15_15_training_label_full_20260706" / "knowledge_base_parameter_report" / "run_metrics.csv"
)
EXP_B_THETA_TABLE = P0 / "meta_designed_ecmade_moo_training" / "theta_candidate_table.csv"


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
    print(f"{label}: {elapsed:.3f}s", flush=True)
    return value, elapsed


def runtime_column(df: pd.DataFrame) -> str:
    for col in ["Runtime", "runtime_sec", "mean_runtime_sec"]:
        if col in df.columns:
            return col
    raise RuntimeError(f"No runtime column found in {df.columns.tolist()}")


def stage_row(
    experiment: str,
    stage: str,
    execution_count: str,
    total_seconds: float,
    average_seconds: float,
    average_unit: str,
    environment: str,
    source: str,
    status: str,
    notes: str = "",
    groups: int | str = "",
    runs: int | str = "",
) -> dict:
    return {
        "experiment": experiment,
        "stage": stage,
        "execution_count": execution_count,
        "total_seconds": float(total_seconds),
        "total_hms": seconds_to_hms(total_seconds),
        "total_minutes": float(total_seconds) / 60.0,
        "average_seconds": float(average_seconds),
        "average_unit": average_unit,
        "groups": groups,
        "runs": runs,
        "environment": environment,
        "measurement_source": source,
        "cost_record_status": status,
        "notes": notes,
    }


def optimizer_summary(
    experiment: str,
    stage: str,
    path: Path,
    execution_count: str,
    environment: str,
    notes: str = "",
) -> tuple[dict, pd.DataFrame]:
    df = pd.read_csv(path, encoding="utf-8-sig")
    rt_col = runtime_column(df)
    runtime = pd.to_numeric(df[rt_col], errors="coerce").dropna()
    groups = df[["instance", "K"]].drop_duplicates().shape[0] if {"instance", "K"}.issubset(df.columns) else ""
    runs = len(runtime)
    total = float(runtime.sum())
    row = stage_row(
        experiment,
        stage,
        execution_count,
        total,
        total / runs if runs else float("nan"),
        "per optimizer run",
        environment,
        str(path),
        "historical Runtime column available",
        notes,
        groups=groups,
        runs=runs,
    )
    if "method" in df.columns:
        by_method = (
            df.assign(_runtime=pd.to_numeric(df[rt_col], errors="coerce"))
            .groupby("method", as_index=False)
            .agg(
                runs=("_runtime", "count"),
                total_seconds=("_runtime", "sum"),
                mean_seconds=("_runtime", "mean"),
                groups=("instance", lambda s: df.loc[s.index, ["instance", "K"]].drop_duplicates().shape[0])
                if {"instance", "K"}.issubset(df.columns)
                else ("_runtime", "count"),
            )
        )
        by_method["experiment"] = experiment
        by_method["stage"] = stage
        by_method["total_hms"] = by_method["total_seconds"].map(seconds_to_hms)
    else:
        by_method = pd.DataFrame()
    return row, by_method


def distinct_count(path: Path, columns: list[str]) -> int:
    df = pd.read_csv(path, encoding="utf-8-sig")
    if not set(columns).issubset(df.columns):
        return 0
    return int(df[columns].drop_duplicates().shape[0])


def measure_b_meta_selector() -> tuple[list[dict], dict]:
    root = workspace_root()
    seed = 20260713
    folds = 5

    def load_inputs():
        labels = pd.read_csv(resolve(DEFAULT_LABELS, root), encoding="utf-8-sig")
        manifest = load_manifest(resolve(DEFAULT_MANIFEST, root))
        assignment_manifest = load_manifest(resolve(DEFAULT_ASSIGNMENT_MANIFEST, root))
        theta = pd.read_csv(EXP_B_THETA_TABLE, encoding="utf-8-sig")
        return labels, manifest, assignment_manifest, theta

    (labels, manifest, assignment_manifest, theta), load_seconds = timed("Experiment B load selector inputs", load_inputs)

    def preprocess():
        train = prepare_training(labels, manifest)
        numeric, categorical = feature_columns(train)
        return train, numeric, categorical

    (train, numeric, categorical), preprocess_seconds = timed("Experiment B feature preprocessing", preprocess)

    def train_selector():
        cv_predictions, cv_summary = cross_validate(train, numeric, categorical, folds, seed)
        final_model = make_model(numeric, categorical, seed)
        final_model.fit(train[numeric + categorical], train["target"])
        return final_model, cv_predictions, cv_summary

    (model, cv_predictions, cv_summary), train_seconds = timed("Experiment B 5-fold CV + final RF fit", train_selector)

    def recommend():
        return build_assignment(model, assignment_manifest, theta, numeric, categorical, ["test"])

    (assignment, test_scores), recommend_seconds = timed("Experiment B theta recommendation", recommend)

    rows = [
        stage_row(
            "Experiment B",
            "Meta-selector feature preprocessing",
            f"{len(train)} training rows",
            preprocess_seconds,
            preprocess_seconds / len(train),
            "per label row",
            "Python / pandas + scikit-learn preprocessing",
            "remeasured on 2026-08-02 by build_experiment_ab_cost_audit.py",
            "no historical wall-clock log; remeasured",
            f"Input loading measured separately: {load_seconds:.3f}s.",
            groups=int(train[["instance", "K"]].drop_duplicates().shape[0]),
        ),
        stage_row(
            "Experiment B",
            "Meta-selector training",
            "5-fold GroupKFold CV + 1 final RandomForestRegressor fit",
            train_seconds,
            train_seconds / (folds + 1),
            "per RF fit equivalent",
            "Python / scikit-learn RandomForestRegressor(n_estimators=500, min_samples_leaf=2, n_jobs=-1)",
            "remeasured on 2026-08-02 by build_experiment_ab_cost_audit.py",
            "no historical wall-clock log; remeasured",
            f"CV prediction rows={len(cv_predictions)}; CV folds={len(cv_summary)}.",
            groups=int(train[["instance", "K"]].drop_duplicates().shape[0]),
        ),
        stage_row(
            "Experiment B",
            "Meta-selector theta recommendation",
            f"{len(assignment)} test groups x {len(theta)} theta candidates",
            recommend_seconds,
            recommend_seconds / len(assignment),
            "per test group",
            "Python / trained Random Forest selector",
            "remeasured on 2026-08-02 by build_experiment_ab_cost_audit.py",
            "no historical wall-clock log; remeasured",
            f"Prediction rows={len(test_scores)}.",
            groups=len(assignment),
        ),
    ]
    metadata = {
        "training_rows": int(len(train)),
        "instance_groups": int(train[["instance", "K"]].drop_duplicates().shape[0]),
        "theta_candidates": int(len(theta)),
        "test_assignment_rows": int(len(assignment)),
        "raw_feature_count": int(len(numeric) + len(categorical)),
        "input_loading_seconds": load_seconds,
    }
    return rows, metadata


def measure_postprocessing(experiment: str, stage: str, command: list[str], notes: str, timeout_seconds: int = 300) -> dict:
    start = perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
            timeout=timeout_seconds,
        )
        elapsed = perf_counter() - start
        status = "no historical wall-clock log; remeasured"
        note_suffix = f" stdout_tail={completed.stdout[-250:].strip()}"
    except subprocess.TimeoutExpired as exc:
        elapsed = perf_counter() - start
        status = f"no historical wall-clock log; rerun exceeded {timeout_seconds}s timeout"
        note_suffix = f" timeout_after={elapsed:.3f}s stdout_tail={(exc.stdout or '')[-250:]}"
    return stage_row(
        experiment,
        stage,
        "1 script execution",
        elapsed,
        elapsed,
        "per script execution",
        "Python / pandas + scipy/report generation scripts",
        "remeasured on 2026-08-02 by build_experiment_ab_cost_audit.py",
        status,
        notes + note_suffix,
    )


def timeout_lower_bound_stage(
    experiment: str,
    stage: str,
    timeout_seconds: float,
    notes: str,
) -> dict:
    return stage_row(
        experiment,
        stage,
        "1 script execution attempted",
        timeout_seconds,
        timeout_seconds,
        "lower-bound timeout",
        "Python / pandas + scipy common-reference script",
        "attempted on 2026-08-02 by build_experiment_ab_cost_audit.py",
        f"no historical wall-clock log; rerun exceeded {int(timeout_seconds)}s timeout",
        notes,
    )


def environment_metadata(extra: dict) -> dict:
    return {
        "created": "2026-08-02",
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
        "extra": extra,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    method_frames: list[pd.DataFrame] = []

    row, by_method = optimizer_summary(
        "Experiment A",
        "Final algorithm comparison optimization",
        EXP_A_RUN_METRICS,
        "formal groups x algorithms x independent runs",
        "MATLAB / PlatEMO algorithms",
        "Historical algorithm Runtime sum from Experiment A delivery table.",
    )
    row["execution_count"] = f"{row['groups']} groups x {by_method['method'].nunique()} algorithms x {int(by_method['runs'].median()) // int(row['groups'])} runs"
    rows.append(row)
    method_frames.append(by_method)

    # Experiment B meta-designed selector uses the same theta24 label table later reused by Experiment C.
    row, by_method = optimizer_summary(
        "Experiment B",
        "Meta-training label generation",
        EXP_B_LABEL_RUN_METRICS,
        "134 groups x 24 theta x 30 runs",
        "MATLAB / PlatEMO + ECMADE-MOO",
        "Historical algorithm Runtime sum for label generation used by the meta-designed selector.",
    )
    rows.append(row)
    method_frames.append(by_method)

    selector_rows, selector_metadata = measure_b_meta_selector()
    rows.extend(selector_rows)

    row, by_method = optimizer_summary(
        "Experiment B",
        "Bayesian configuration search",
        EXP_B_BAYES_CONFIG_RUNS,
        "configuration validation groups x theta evaluations x runs",
        "MATLAB / PlatEMO + ECMADE-MOO",
        "Historical Runtime sum for Bayesian configuration evaluation runs.",
    )
    bayes_theta = distinct_count(EXP_B_BAYES_CONFIG_RUNS, ["theta_id"])
    bayes_runs_per_theta_group = int(row["runs"]) // (int(row["groups"]) * bayes_theta)
    row["execution_count"] = f"{row['groups']} configuration validation groups x {bayes_theta} theta evaluations x {bayes_runs_per_theta_group} runs"
    rows.append(row)
    method_frames.append(by_method)

    row, by_method = optimizer_summary(
        "Experiment B",
        "Final configuration comparison optimization",
        EXP_B_RUN_METRICS,
        "test groups x configuration methods x independent runs",
        "MATLAB / PlatEMO + ECMADE-MOO",
        "Historical Runtime sum from common-reference Experiment B final comparison.",
    )
    row["execution_count"] = f"{row['groups']} test groups x {by_method['method'].nunique()} configuration methods x {int(by_method['runs'].median()) // int(row['groups'])} runs"
    rows.append(row)
    method_frames.append(by_method)

    # These are separated to make clear that random/meta final rows are already included in the combined final comparison.
    for label, path in [
        ("Random-config selected final runs", EXP_B_RANDOM_FINAL_RUNS),
        ("Meta-designed selected final runs", EXP_B_META_FINAL_RUNS),
    ]:
        if path.exists():
            row, by_method = optimizer_summary(
                "Experiment B",
                label,
                path,
                "32 test groups x 30 runs",
                "MATLAB / PlatEMO + ECMADE-MOO",
                "Diagnostic subset of the final comparison; do not add to the combined final comparison total.",
            )
            row["cost_record_status"] = "historical Runtime column available; diagnostic subset"
            rows.append(row)
            method_frames.append(by_method)

    rows.append(
        timeout_lower_bound_stage(
            "Experiment B",
            "Post-processing and common-reference computation",
            1201.281,
            "Full rerun of summarize_experiment_b_configurations.py exceeded the 20-minute shell timeout in this session; existing output tables are present, but exact original wall-clock was not logged.",
        )
    )

    # Experiment A report/statistics generation is measured using the existing report script; optimizer Runtime remains the source for compute cost.
    rows.append(
        timeout_lower_bound_stage(
            "Experiment A",
            "Report/statistical post-processing",
            300.102,
            "Rerun of build_synthetic_experiment_a_report.py exceeded the 5-minute timeout in this session; existing statistical/report tables are present, but exact original wall-clock was not logged.",
        )
    )

    summary = pd.DataFrame(rows)
    summary.to_csv(OUT_DIR / "experiment_ab_cost_audit_summary.csv", index=False, encoding="utf-8-sig")

    method_detail = pd.concat([frame for frame in method_frames if not frame.empty], ignore_index=True)
    method_detail.to_csv(OUT_DIR / "experiment_ab_cost_by_method.csv", index=False, encoding="utf-8-sig")

    env = environment_metadata({"experiment_b_meta_selector": selector_metadata})
    (OUT_DIR / "experiment_ab_cost_environment.json").write_text(
        json.dumps(env, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    lines = [
        "# Experiment A/B cost audit",
        "",
        "Optimizer rows use historical per-run Runtime sums. Python training/post-processing rows were remeasured on 2026-08-02.",
        "",
        summary[
            [
                "experiment",
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
        "## By-method optimizer detail",
        "",
        method_detail[["experiment", "stage", "method", "groups", "runs", "total_hms", "mean_seconds"]].to_markdown(index=False),
        "",
        "## Notes",
        "",
        "- Experiment A optimizer cost is recoverable from the formal run table; original MATLAB batch wall-clock was not separately logged.",
        "- Experiment B meta-training label generation uses the theta24 training-label runtime table. This cost is shared with later selector experiments if the same labels are reused.",
        "- Random-config and meta-designed selected final runs are listed as diagnostic subsets because they are already included in the combined final configuration comparison.",
    ]
    (OUT_DIR / "experiment_ab_cost_audit_summary.md").write_text("\n".join(lines), encoding="utf-8")

    zh = [
        "# Experiment A/B 成本稽核報告",
        "",
        "日期：2026-08-02",
        "",
        "說明：Optimizer 類成本使用既有 run table 中每個 run 的 `Runtime` 欄位加總，因此是可回溯的演算法執行時間，不等於原始 MATLAB batch 的外部 wall-clock。Python 類 meta-training、recommendation 與 post-processing 若沒有歷史 wall-clock，則以本次同機器重新量測或 timeout lower bound 標註。",
        "",
        "## 成本總表",
        "",
        summary[
            [
                "experiment",
                "stage",
                "execution_count",
                "total_hms",
                "total_minutes",
                "average_seconds",
                "average_unit",
                "environment",
                "cost_record_status",
            ]
        ].rename(
            columns={
                "experiment": "實驗",
                "stage": "階段",
                "execution_count": "執行次數",
                "total_hms": "總時間",
                "total_minutes": "總分鐘",
                "average_seconds": "平均秒數",
                "average_unit": "平均單位",
                "environment": "執行環境",
                "cost_record_status": "紀錄狀態",
            }
        ).to_markdown(index=False),
        "",
        "## By-method optimizer detail",
        "",
        method_detail[["experiment", "stage", "method", "groups", "runs", "total_hms", "mean_seconds"]]
        .rename(
            columns={
                "experiment": "實驗",
                "stage": "階段",
                "method": "方法",
                "groups": "groups",
                "runs": "runs",
                "total_hms": "總時間",
                "mean_seconds": "平均秒數/run",
            }
        )
        .to_markdown(index=False),
        "",
        "## 重點解讀",
        "",
        "- Experiment A 正式演算法比較：212 groups × 6 algorithms × 30 runs，歷史 Runtime 加總 57:06:53.85。",
        "- Experiment B meta-training label generation：134 groups × 24 theta × 30 runs，歷史 Runtime 加總 109:32:25.55。若此 label table 同時供 Experiment C 使用，論文中應說明這是共享離線成本，避免重複計入。",
        "- Experiment B meta-selector training：5-fold GroupKFold CV + 1 final RandomForest fit，本次重新量測 00:00:20.06。",
        "- Experiment B theta recommendation：32 test groups × 24 theta candidates，本次重新量測 00:00:12.59，平均每個 test group 0.393 秒。",
        "- Experiment B Bayesian configuration search：8 configuration validation groups × 12 theta evaluations × 3 runs，歷史 Runtime 加總 00:04:26.94。",
        "- Experiment B final configuration comparison：32 test groups × 4 configuration methods × 30 runs，歷史 Runtime 加總 03:33:40.19。",
        "- B 的 full common-reference post-processing 重新執行超過 20 分鐘 timeout，因此目前只能給出 >= 00:20:01.28 的 lower bound；A 的 report/stat post-processing 重新執行超過 5 分鐘 timeout，因此目前只能給出 >= 00:05:00.10 的 lower bound。",
        "",
        "## 未完整取得的歷史成本",
        "",
        "- 原始 MATLAB batch 的外部 wall-clock 沒有完整紀錄；目前使用 per-run Runtime 加總作為 optimizer 成本。",
        "- A/B 原始 post-processing wall-clock 沒有歷史 log；本次重跑 B common-reference 與 A report/stat scripts 均超時，因此表中標示 lower-bound timeout。",
        "- Random-config selected final runs 與 Meta-designed selected final runs 是 B final comparison 的子集合，報告中可作診斷使用，但計總成本時不要再與 combined final comparison 重複相加。",
    ]
    (OUT_DIR / "Experiment_AB_cost_report_zh_20260802.md").write_text("\n".join(zh), encoding="utf-8")

    print(f"WROTE={OUT_DIR}")
    print(summary[["experiment", "stage", "execution_count", "total_hms", "average_seconds", "average_unit"]].to_string(index=False))


if __name__ == "__main__":
    main()
