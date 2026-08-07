from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
P0 = ROOT / "p0_lite_outputs"
OUT_DIR = P0 / "tevc_cost_runtime_summary_20260723"

LABEL_TABLES = [
    (
        "ExperimentC training label generation",
        P0
        / "theta24_70_15_15_training_label_full_20260706"
        / "knowledge_base_parameter_report"
        / "experiment_c_stability_regression_labels.csv",
        30,
    ),
    (
        "ExperimentC validation label generation",
        P0
        / "theta24_70_15_15_validation_label_full_20260713"
        / "knowledge_base_parameter_report"
        / "experiment_c_stability_regression_labels.csv",
        30,
    ),
]


def summarize_label_table(label: str, path: Path, runs_per_label: int) -> dict:
    frame = pd.read_csv(path, encoding="utf-8-sig")
    runtime = pd.to_numeric(frame["Runtime"], errors="coerce").dropna()
    label_rows = int(len(runtime))
    estimated_runs = int(label_rows * runs_per_label)
    total = float(runtime.sum() * runs_per_label)
    return {
        "cost_component": label,
        "label_rows": label_rows,
        "runs_per_label": runs_per_label,
        "estimated_optimizer_runs": estimated_runs,
        "total_runtime_sec": total,
        "total_runtime_hours": total / 3600.0,
        "mean_runtime_sec_per_optimizer_run": float(runtime.mean()),
        "min_mean_runtime_sec": float(runtime.min()),
        "max_mean_runtime_sec": float(runtime.max()),
        "runtime_source": str(path),
    }


def read_optional_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig") if path.exists() else pd.DataFrame()


def config_cost_rows() -> pd.DataFrame:
    rows = []
    exp_b = read_optional_csv(P0 / "experiment_b_configuration_summary_20260713" / "overall_configuration_comparison.csv")
    if not exp_b.empty:
        for row in exp_b.itertuples(index=False):
            rows.append(
                {
                    "scope": "Experiment B synthetic configuration comparison",
                    "method": row.method,
                    "instances": int(row.instances),
                    "runs": "",
                    "mean_runtime_sec": float(row.mean_Runtime),
                    "overall_rank_score": float(row.overall_RankScore),
                    "first_place_instances": int(row.first_place_instances),
                }
            )
    mokp = read_optional_csv(P0 / "p1_mokp_config_comparison_20260719" / "overall_method_summary.csv")
    if not mokp.empty:
        for row in mokp.itertuples(index=False):
            rows.append(
                {
                    "scope": "P1 MOKP configuration comparison",
                    "method": row.method,
                    "instances": int(row.instances),
                    "runs": int(row.runs),
                    "mean_runtime_sec": float(row.mean_Runtime),
                    "overall_rank_score": float(row.overall_RankScore),
                    "first_place_instances": int(row.first_place_instances),
                }
            )
    rolling = read_optional_csv(
        P0 / "p1_rolling_window_market_validation_20260719" / "summary" / "method_overall_summary.csv"
    )
    if not rolling.empty:
        for row in rolling.itertuples(index=False):
            rows.append(
                {
                    "scope": "P1 rolling-market final optimization",
                    "method": row.method,
                    "instances": int(row.windows),
                    "runs": "",
                    "mean_runtime_sec": float(row.mean_runtime_sec),
                    "overall_rank_score": float(row.mean_RankScore),
                    "first_place_instances": int(row.first_place_windows),
                }
            )
    return pd.DataFrame(rows)


def selector_training_rows() -> pd.DataFrame:
    rows = []
    configs = [
        ("Experiment B meta-designed selector", P0 / "meta_designed_ecmade_moo_training"),
        ("Experiment C stability-aware selector", P0 / "experiment_c_stability_selector_training"),
    ]
    for label, root in configs:
        config_path = root / "training_config.json"
        if not config_path.exists():
            continue
        import json

        config = json.loads(config_path.read_text(encoding="utf-8"))
        rows.append(
            {
                "selector": label,
                "training_rows": config.get("rows", config.get("training_rows")),
                "validation_rows": config.get("validation_rows"),
                "instance_groups": config.get("instance_groups"),
                "theta_candidates": config.get("theta_candidates", 24),
                "target": config.get("target"),
                "runtime_note": "model-fit runtime was not separately logged",
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    label_runtime = pd.DataFrame(
        [summarize_label_table(label, path, runs_per_label) for label, path, runs_per_label in LABEL_TABLES]
    )
    config_cost = config_cost_rows()
    selector_cost = selector_training_rows()

    label_runtime.to_csv(OUT_DIR / "label_generation_runtime_summary.csv", index=False, encoding="utf-8-sig")
    config_cost.to_csv(OUT_DIR / "configuration_and_final_runtime_summary.csv", index=False, encoding="utf-8-sig")
    selector_cost.to_csv(OUT_DIR / "selector_training_data_summary.csv", index=False, encoding="utf-8-sig")

    lines = [
        "# TEVC Cost and Runtime Summary",
        "",
        "## Label Generation Runtime",
        "",
        label_runtime.to_markdown(index=False),
        "",
        "## Configuration / Final Optimization Runtime",
        "",
        config_cost.to_markdown(index=False),
        "",
        "## Selector Training Data Scale",
        "",
        selector_cost.to_markdown(index=False),
        "",
    ]
    (OUT_DIR / "README_cost_runtime.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"OUT_DIR={OUT_DIR}")
    print(label_runtime.to_string(index=False))
    print(config_cost.to_string(index=False))
    print(selector_cost.to_string(index=False))


if __name__ == "__main__":
    main()
