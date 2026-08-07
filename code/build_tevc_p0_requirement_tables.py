"""Build TEVC P0 requirement-aligned post-processing tables.

This script fills reporting gaps that are not raw optimization runs:
constraint/feasibility aggregates, archive/diversity aggregates, runtime cost
summaries, and an explicit EAF-band-width-style stability table.
"""

from __future__ import annotations

import math
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from rank_knowledge_base_parameter_search import nondominated, normalize, read_matrix


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "p0_lite_outputs" / "tevc_p0_requirement_tables_20260717"

ROOTS = {
    "Experiment_A_Synthetic": ROOT / "p0_lite_outputs" / "synthetic_constrained_portfolio",
    "Experiment_A_ORLibrary": ROOT / "p0_lite_outputs" / "orlib_constrained_portfolio",
    "Experiment_B_Random": ROOT / "p0_lite_outputs" / "random_config_ecmade_moo_20260711_074253",
    "Experiment_B_Bayesian": ROOT / "p0_lite_outputs" / "bayesian_config_ecmade_moo_20260713_140251",
    "Experiment_B_MetaDesigned": ROOT / "p0_lite_outputs" / "meta_designed_ecmade_moo_20260713_164632",
    "Experiment_C_StabilityAware": ROOT / "p0_lite_outputs" / "experiment_c_stability_ecmade_moo_20260717",
    "TEVC_PDF_Direct_Ablation": ROOT / "p0_lite_outputs" / "tevc_pdf_direct_ablation_full_20260717",
}


def parse_run_dir(run_dir: Path, root: Path) -> dict | None:
    try:
        rel = run_dir.relative_to(root).parts
    except ValueError:
        return None
    if not run_dir.name.startswith("run_"):
        return None
    try:
        run = int(run_dir.name.split("_")[-1])
    except ValueError:
        return None
    if len(rel) >= 5 and rel[-3].startswith("K_"):
        return {
            "split": rel[-5],
            "instance": rel[-4],
            "K": int(rel[-3].split("_")[-1]),
            "method": rel[-2],
            "run": run,
            "run_dir": run_dir,
        }
    if len(rel) >= 6 and rel[-4].startswith("K_"):
        return {
            "split": rel[-6],
            "instance": rel[-5],
            "K": int(rel[-4].split("_")[-1]),
            "method": rel[-3],
            "run": run,
            "run_dir": run_dir,
        }
    return None


def discover_runs(root: Path, experiment: str) -> pd.DataFrame:
    rows = []
    for pf_file in root.glob("**/pf_obj.csv"):
        rec = parse_run_dir(pf_file.parent, root)
        if rec is None:
            continue
        rows.append({**rec, "experiment": experiment, "pf_file": pf_file})
    return pd.DataFrame(rows)


def read_one_row(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return pd.read_csv(path).iloc[0].to_dict()
    except Exception:
        return {}


def build_run_side_metrics(run_index: pd.DataFrame) -> pd.DataFrame:
    def build_row(rec: dict) -> dict:
        run_dir = Path(rec["run_dir"])
        row = {
            "experiment": rec["experiment"],
            "split": rec["split"],
            "instance": rec["instance"],
            "K": rec["K"],
            "method": rec["method"],
            "run": rec["run"],
        }
        row.update(read_one_row(run_dir / "runtime.csv"))
        row.update(read_one_row(run_dir / "feasible_rate.csv"))
        row.update(read_one_row(run_dir / "constraint_metrics.csv"))
        row.update(read_one_row(run_dir / "archive_metrics.csv"))
        return row

    rows = []
    with ThreadPoolExecutor(max_workers=16) as executor:
        for row in executor.map(build_row, run_index.to_dict("records")):
            rows.append(row)
    return pd.DataFrame(rows)


def build_side_metric_aggregates(side: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    numeric = [
        c
        for c in side.columns
        if c
        not in {
            "experiment",
            "split",
            "instance",
            "K",
            "method",
            "run",
            "run_dir",
        }
        and pd.api.types.is_numeric_dtype(side[c])
    ]
    instance = (
        side.groupby(["experiment", "split", "instance", "K", "method"], dropna=False)[numeric]
        .mean()
        .reset_index()
    )
    overall = (
        instance.groupby(["experiment", "method"], dropna=False)[numeric]
        .agg(["mean", "std"])
    )
    overall.columns = ["_".join(col).strip("_") for col in overall.columns.to_flat_index()]
    overall = overall.reset_index()
    return instance, overall


def attainment_curve(points: np.ndarray, x_grid: np.ndarray) -> np.ndarray:
    if len(points) == 0:
        return np.full_like(x_grid, np.nan, dtype=float)
    pts = points[np.argsort(points[:, 0])]
    curve = []
    for x in x_grid:
        eligible = pts[pts[:, 0] <= x]
        curve.append(np.min(eligible[:, 1]) if len(eligible) else np.nan)
    s = pd.Series(curve).ffill().bfill()
    return s.to_numpy(dtype=float)


def build_eaf_band_width(run_index: pd.DataFrame, grid_size: int = 101) -> pd.DataFrame:
    rows = []
    x_grid = np.linspace(0.0, 1.0, grid_size)
    for keys, group in run_index.groupby(["experiment", "split", "instance", "K", "method"]):
        experiment, split, instance, k_value, method = keys
        fronts = [read_matrix(Path(p)) for p in group["pf_file"]]
        fronts = [front for front in fronts if len(front)]
        if not fronts:
            continue
        union = np.vstack(fronts)
        ideal = union.min(axis=0)
        nadir = union.max(axis=0)
        curves = []
        for front in fronts:
            nf = nondominated(normalize(front, ideal, nadir))
            curves.append(attainment_curve(nf, x_grid))
        arr = np.vstack(curves)
        q75 = np.nanpercentile(arr, 75, axis=0)
        q25 = np.nanpercentile(arr, 25, axis=0)
        q90 = np.nanpercentile(arr, 90, axis=0)
        q10 = np.nanpercentile(arr, 10, axis=0)
        rows.append(
            {
                "experiment": experiment,
                "split": split,
                "instance": instance,
                "K": int(k_value),
                "method": method,
                "runs": int(group["run"].nunique()),
                "EAF_Band_Width_IQR": float(np.nanmean(q75 - q25)),
                "EAF_Band_Width_80pct": float(np.nanmean(q90 - q10)),
            }
        )
    instance = pd.DataFrame(rows)
    overall = (
        instance.groupby(["experiment", "method"], dropna=False)
        .agg(
            instances=("instance", "nunique"),
            mean_EAF_Band_Width_IQR=("EAF_Band_Width_IQR", "mean"),
            std_EAF_Band_Width_IQR=("EAF_Band_Width_IQR", "std"),
            mean_EAF_Band_Width_80pct=("EAF_Band_Width_80pct", "mean"),
            std_EAF_Band_Width_80pct=("EAF_Band_Width_80pct", "std"),
            min_runs=("runs", "min"),
            max_runs=("runs", "max"),
        )
        .reset_index()
    )
    return instance, overall


def build_completion_audit(run_index: pd.DataFrame) -> pd.DataFrame:
    counts = (
        run_index.groupby(["experiment", "split", "instance", "K", "method"])["run"]
        .nunique()
        .rename("completed_runs")
        .reset_index()
    )
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--splits", default="test", help="Comma-separated splits for metric tables; use all for every split.")
    parser.add_argument("--skip-eaf", action="store_true")
    parser.add_argument("--reuse-index", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index_path = OUT_DIR / "tevc_p0_run_index.csv"
    if args.reuse_index and index_path.exists():
        run_index = pd.read_csv(index_path)
    else:
        frames = []
        for experiment, root in ROOTS.items():
            if root.exists():
                frame = discover_runs(root, experiment)
                if not frame.empty:
                    frames.append(frame)
        if not frames:
            raise RuntimeError("No runs discovered.")
        run_index = pd.concat(frames, ignore_index=True)
        run_index.to_csv(index_path, index=False, encoding="utf-8-sig")

    completion = build_completion_audit(run_index)
    completion.to_csv(OUT_DIR / "tevc_p0_completion_audit.csv", index=False, encoding="utf-8-sig")

    if args.splits.lower() == "all":
        metric_index = run_index.copy()
    else:
        wanted = {part.strip() for part in args.splits.split(",") if part.strip()}
        metric_index = run_index[run_index["split"].isin(wanted)].copy()
    metric_index.to_csv(OUT_DIR / "tevc_p0_metric_scope_run_index.csv", index=False, encoding="utf-8-sig")

    side = build_run_side_metrics(metric_index)
    side.to_csv(OUT_DIR / "tevc_p0_run_side_metrics.csv", index=False, encoding="utf-8-sig")
    instance_side, overall_side = build_side_metric_aggregates(side)
    instance_side.to_csv(OUT_DIR / "tevc_p0_instance_constraint_archive_runtime.csv", index=False, encoding="utf-8-sig")
    overall_side.to_csv(OUT_DIR / "tevc_p0_overall_constraint_archive_runtime.csv", index=False, encoding="utf-8-sig")

    if not args.skip_eaf:
        eaf_instance, eaf_overall = build_eaf_band_width(metric_index)
        eaf_instance.to_csv(OUT_DIR / "tevc_p0_instance_eaf_band_width.csv", index=False, encoding="utf-8-sig")
        eaf_overall.to_csv(OUT_DIR / "tevc_p0_overall_eaf_band_width.csv", index=False, encoding="utf-8-sig")

    status = (
        completion.groupby(["experiment", "method"])
        .agg(groups=("completed_runs", "size"), min_runs=("completed_runs", "min"), max_runs=("completed_runs", "max"))
        .reset_index()
    )
    status.to_csv(OUT_DIR / "tevc_p0_completion_summary.csv", index=False, encoding="utf-8-sig")
    print(f"OUT_DIR={OUT_DIR}")
    print(status.to_string(index=False))


if __name__ == "__main__":
    main()
