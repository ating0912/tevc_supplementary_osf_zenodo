from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from rank_knowledge_base_parameter_search import nondominated, normalize, read_matrix


ROOT = Path(__file__).resolve().parent
VALID_ROOT = ROOT / "p0_lite_outputs" / "theta24_70_15_15_validation_label_full_20260713"
VALID_LABELS = VALID_ROOT / "knowledge_base_parameter_report" / "experiment_c_stability_regression_labels.csv"
SEL_DETAIL = ROOT / "outputs" / "tevc_ablation_4_5_20260717" / "label_objective_cross_evaluation_on_C_detail.csv"
OUT_45 = ROOT / "outputs" / "tevc_ablation_4_5_20260717" / "label_objective_cross_evaluation_eaf_summary.csv"
OUT_45_DETAIL = ROOT / "outputs" / "tevc_ablation_4_5_20260717" / "label_objective_cross_evaluation_eaf_detail.csv"
OUT_6 = ROOT / "outputs" / "tevc_ablation_6_20260717" / "theta_factor_main_effect_eaf_summary.csv"
OUT_6_DETAIL = ROOT / "outputs" / "tevc_ablation_6_20260717" / "theta_factor_group_eaf_detail.csv"
OUT_EAF_INSTANCE = ROOT / "outputs" / "tevc_ablation_eaf_width_20260722" / "validation_theta_instance_eaf_width.csv"


def attainment_curve(points: np.ndarray, x_grid: np.ndarray) -> np.ndarray:
    if len(points) == 0:
        return np.full_like(x_grid, np.nan, dtype=float)
    pts = points[np.argsort(points[:, 0])]
    curve = []
    for x_value in x_grid:
        eligible = pts[pts[:, 0] <= x_value]
        curve.append(np.min(eligible[:, 1]) if len(eligible) else np.nan)
    return pd.Series(curve).ffill().bfill().to_numpy(dtype=float)


def k_dir_name(k_value: int) -> list[str]:
    return [f"K_{k_value:02d}", f"K_{k_value}"]


def pf_files(split: str, instance: str, k_value: int, method: str) -> list[Path]:
    base = VALID_ROOT / split / instance
    for name in k_dir_name(int(k_value)):
        candidate = base / name / method
        if candidate.exists():
            return sorted(candidate.glob("run_*/pf_obj.csv"))
    return []


def compute_one(rec: dict, grid_size: int = 101) -> dict:
    files = pf_files(str(rec["split"]), str(rec["instance"]), int(rec["K"]), str(rec["method"]))
    fronts = [read_matrix(path) for path in files]
    fronts = [front for front in fronts if len(front)]
    row = {
        "split": rec["split"],
        "instance": rec["instance"],
        "K": int(rec["K"]),
        "method": rec["method"],
        "runs": len(fronts),
        "EAF_Band_Width_IQR": np.nan,
        "EAF_Band_Width_80pct": np.nan,
    }
    if not fronts:
        return row
    union = np.vstack(fronts)
    ideal = union.min(axis=0)
    nadir = union.max(axis=0)
    x_grid = np.linspace(0.0, 1.0, grid_size)
    curves = []
    for front in fronts:
        normalized = nondominated(normalize(front, ideal, nadir))
        curves.append(attainment_curve(normalized, x_grid))
    arr = np.vstack(curves)
    row["EAF_Band_Width_IQR"] = float(np.nanmean(np.nanpercentile(arr, 75, axis=0) - np.nanpercentile(arr, 25, axis=0)))
    row["EAF_Band_Width_80pct"] = float(np.nanmean(np.nanpercentile(arr, 90, axis=0) - np.nanpercentile(arr, 10, axis=0)))
    return row


def compute_validation_theta_eaf(labels: pd.DataFrame) -> pd.DataFrame:
    keys = ["split", "instance", "K", "method"]
    unique = labels[keys].drop_duplicates().sort_values(keys).reset_index(drop=True)
    rows = []
    with ThreadPoolExecutor(max_workers=16) as executor:
        for row in executor.map(compute_one, unique.to_dict("records")):
            rows.append(row)
    eaf = pd.DataFrame(rows)
    OUT_EAF_INSTANCE.parent.mkdir(parents=True, exist_ok=True)
    eaf.to_csv(OUT_EAF_INSTANCE, index=False, encoding="utf-8-sig")
    return eaf


def build_selector_eaf(selection: pd.DataFrame, eaf: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    eaf_keys = ["instance", "K", "method"]
    eaf_map = eaf[eaf["split"].astype(str).str.lower().eq("validation")][
        eaf_keys + ["runs", "EAF_Band_Width_IQR", "EAF_Band_Width_80pct"]
    ].rename(columns={"method": "selected_theta"})
    group_mean = (
        eaf[eaf["split"].astype(str).str.lower().eq("validation")]
        .groupby(["instance", "K"], dropna=False)
        .agg(
            selected_runs=("runs", "min"),
            selected_EAF_Band_Width_IQR=("EAF_Band_Width_IQR", "mean"),
            selected_EAF_Band_Width_80pct=("EAF_Band_Width_80pct", "mean"),
        )
        .reset_index()
    )
    detail = selection.merge(eaf_map, on=["instance", "K", "selected_theta"], how="left")
    detail = detail.rename(
        columns={
            "runs": "selected_runs",
            "EAF_Band_Width_IQR": "selected_EAF_Band_Width_IQR",
            "EAF_Band_Width_80pct": "selected_EAF_Band_Width_80pct",
        }
    )
    all_mask = detail["selected_theta"].eq("all_theta_mean")
    detail.loc[all_mask, ["selected_runs", "selected_EAF_Band_Width_IQR", "selected_EAF_Band_Width_80pct"]] = (
        detail.loc[all_mask, ["instance", "K"]]
        .merge(group_mean, on=["instance", "K"], how="left")[
            ["selected_runs", "selected_EAF_Band_Width_IQR", "selected_EAF_Band_Width_80pct"]
        ]
        .to_numpy()
    )
    summary = (
        detail.groupby("selector", dropna=False)
        .agg(
            groups=("instance", "count"),
            mean_selected_EAF_Band_Width_IQR=("selected_EAF_Band_Width_IQR", "mean"),
            mean_selected_EAF_Band_Width_80pct=("selected_EAF_Band_Width_80pct", "mean"),
            min_runs=("selected_runs", "min"),
            max_runs=("selected_runs", "max"),
        )
        .reset_index()
    )
    return detail, summary


def build_migration_eaf(labels: pd.DataFrame, eaf: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    merged = labels.merge(
        eaf[["split", "instance", "K", "method", "runs", "EAF_Band_Width_IQR", "EAF_Band_Width_80pct"]],
        on=["split", "instance", "K", "method"],
        how="left",
    )
    detail = (
        merged[merged["split"].astype(str).str.lower().eq("validation")]
        .groupby(["split", "instance", "K", "source_migration"], dropna=False)
        .agg(
            theta_rows=("method", "count"),
            min_runs=("runs", "min"),
            EAF_Band_Width_IQR=("EAF_Band_Width_IQR", "mean"),
            EAF_Band_Width_80pct=("EAF_Band_Width_80pct", "mean"),
        )
        .reset_index()
        .rename(columns={"source_migration": "level"})
    )
    summary = (
        detail.groupby("level", dropna=False)
        .agg(
            instance_groups=("instance", "nunique"),
            rows=("theta_rows", "sum"),
            mean_EAF_Band_Width_IQR=("EAF_Band_Width_IQR", "mean"),
            mean_EAF_Band_Width_80pct=("EAF_Band_Width_80pct", "mean"),
            min_runs=("min_runs", "min"),
        )
        .reset_index()
    )
    summary.insert(0, "factor", "migration")
    summary.insert(0, "source", "Validation")
    summary.insert(0, "objective", "stability_label")
    return detail, summary


def main() -> None:
    labels = pd.read_csv(VALID_LABELS, encoding="utf-8-sig")
    eaf = compute_validation_theta_eaf(labels)
    selection = pd.read_csv(SEL_DETAIL, encoding="utf-8-sig")
    selector_detail, selector_summary = build_selector_eaf(selection, eaf)
    migration_detail, migration_summary = build_migration_eaf(labels, eaf)
    OUT_45.parent.mkdir(parents=True, exist_ok=True)
    OUT_6.parent.mkdir(parents=True, exist_ok=True)
    selector_detail.to_csv(OUT_45_DETAIL, index=False, encoding="utf-8-sig")
    selector_summary.to_csv(OUT_45, index=False, encoding="utf-8-sig")
    migration_detail.to_csv(OUT_6_DETAIL, index=False, encoding="utf-8-sig")
    migration_summary.to_csv(OUT_6, index=False, encoding="utf-8-sig")
    print(f"validation theta EAF rows: {len(eaf)}")
    print(selector_summary.to_string(index=False))
    print(migration_summary.to_string(index=False))


if __name__ == "__main__":
    main()
