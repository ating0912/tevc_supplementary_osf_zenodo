import math
import os
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(r".")
MANIFEST = ROOT / "data" / "synthetic_constrained_portfolio" / "manifest.csv"
METHODS = [
    "ECMADE_TUNE_DEFAULT",
    "ECMADE_TUNE_CONSERVATIVE",
    "ECMADE_TUNE_REFERENCE",
    "ECMADE_TUNE_CONSENSUS",
]


def latest_tuning_root():
    candidates = sorted((ROOT / "p0_lite_outputs").glob("ecmade_moo_tuning_*"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError("No p0_lite_outputs/ecmade_moo_tuning_* directory found.")
    return candidates[-1]


def read_matrix(path):
    try:
        arr = np.loadtxt(path, delimiter=",")
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        return arr[:, :2]
    except Exception:
        return np.empty((0, 2))


def read_runtime(path):
    try:
        row = pd.read_csv(path).iloc[0]
        return float(row["runtime_sec"])
    except Exception:
        return math.nan


def nondominated(points):
    points = np.asarray(points, dtype=float)
    if points.size == 0:
        return points.reshape(0, 2)
    order = np.lexsort((points[:, 1], points[:, 0]))
    pts = points[order]
    keep = []
    best_y = math.inf
    for p in pts:
        if p[1] < best_y - 1e-12:
            keep.append(p)
            best_y = p[1]
    return np.asarray(keep)


def normalize(points, ideal, nadir):
    span = np.maximum(nadir - ideal, 1e-12)
    return np.clip((points - ideal) / span, 0, 1)


def thin(points, max_points=120):
    points = np.asarray(points, dtype=float)
    if len(points) <= max_points:
        return points
    pts = points[np.argsort(points[:, 0])]
    idx = np.linspace(0, len(pts) - 1, max_points).round().astype(int)
    return pts[idx]


def hv2d(points, ref=(1.1, 1.1)):
    pts = nondominated(points)
    if len(pts) == 0:
        return 0.0
    pts = pts[np.argsort(pts[:, 0])]
    hv = 0.0
    prev_y = ref[1]
    for x, y in pts:
        if x < ref[0] and y < prev_y:
            hv += max(ref[0] - x, 0) * max(prev_y - y, 0)
            prev_y = y
    return hv


def igd(pf, ref):
    if len(pf) == 0 or len(ref) == 0:
        return math.nan
    return float(np.mean([np.sqrt(((pf - p) ** 2).sum(axis=1)).min() for p in ref]))


def overlap(pf, ref, tol=0.02):
    if len(pf) == 0 or len(ref) == 0:
        return 0.0
    return float(np.mean([np.sqrt(((pf - p) ** 2).sum(axis=1)).min() <= tol for p in ref]))


def diversity(pf):
    if len(pf) < 2:
        return 0.0
    return float(np.linalg.norm(np.max(pf, axis=0) - np.min(pf, axis=0)))


def centroid(pf):
    if len(pf) == 0:
        return np.array([math.nan, math.nan])
    return np.nanmean(pf, axis=0)


def attainment_curve(points, grid):
    y = np.full(len(grid), np.nan)
    if len(points) == 0:
        return y
    pts = points[np.argsort(points[:, 0])]
    for i, gx in enumerate(grid):
        eligible = pts[pts[:, 0] <= gx]
        if len(eligible):
            y[i] = np.min(eligible[:, 1])
    return y


def eaf_width(fronts):
    grid = np.linspace(0, 1, 101)
    curves = np.vstack([attainment_curve(f, grid) for f in fronts if len(f)])
    if curves.size == 0:
        return math.nan
    return float(np.nanmean(np.nanpercentile(curves, 75, axis=0) - np.nanpercentile(curves, 25, axis=0)))


def main():
    out_root = Path(os.environ.get("ECMADE_TUNING_ROOT", latest_tuning_root()))
    manifest = pd.read_csv(MANIFEST)
    rows = []
    pfs = {}
    fronts_by_instance = {}
    for _, row in manifest.iterrows():
        for method in METHODS:
            method_dir = out_root / row["split"] / row["instance"] / f"K_{int(row['K']):02d}" / method
            if not method_dir.exists():
                continue
            for run_dir in sorted(method_dir.glob("run_*")):
                run = int(run_dir.name.split("_")[-1])
                pf = read_matrix(run_dir / "pf_obj.csv")
                if len(pf) == 0:
                    continue
                key = (row["instance"], method, run)
                pfs[key] = pf
                fronts_by_instance.setdefault(row["instance"], []).append(pf)
                rows.append(
                    {
                        "split": row["split"],
                        "instance": row["instance"],
                        "assets": int(row["assets"]),
                        "K": int(row["K"]),
                        "method": method,
                        "run": run,
                        "PF_Size": len(pf),
                        "Runtime": read_runtime(run_dir / "runtime.csv"),
                    }
                )
    run_df = pd.DataFrame(rows)
    if run_df.empty:
        raise RuntimeError(f"No tuning runs found under {out_root}")

    ref_info = {}
    for instance, fronts in fronts_by_instance.items():
        union = np.vstack(fronts)
        ideal = union.min(axis=0)
        nadir = union.max(axis=0)
        ref = thin(nondominated(normalize(union, ideal, nadir)))
        ref_info[instance] = (ideal, nadir, ref)

    metric_rows = []
    norm_fronts = {}
    for rec in rows:
        key = (rec["instance"], rec["method"], rec["run"])
        ideal, nadir, ref = ref_info[rec["instance"]]
        nf = thin(nondominated(normalize(pfs[key], ideal, nadir)))
        norm_fronts[key] = nf
        metric_rows.append(
            {
                **rec,
                "HV": hv2d(nf),
                "IGD": igd(nf, ref),
                "PF_Overlap": overlap(nf, ref),
                "Diversity": diversity(nf),
            }
        )
    run_metrics = pd.DataFrame(metric_rows)

    inst_rows = []
    for (instance, method), base in run_metrics.groupby(["instance", "method"]):
        fronts = [norm_fronts[(instance, method, int(r))] for r in base["run"]]
        centroids = np.vstack([centroid(f) for f in fronts if len(f)])
        mean_c = np.nanmean(centroids, axis=0)
        drifts = [float(np.sqrt(((centroid(f) - mean_c) ** 2).sum())) for f in fronts if len(f)]
        meta = base.iloc[0]
        inst_rows.append(
            {
                "split": meta["split"],
                "instance": instance,
                "assets": int(meta["assets"]),
                "K": int(meta["K"]),
                "method": method,
                "HV": base["HV"].mean(),
                "IGD": base["IGD"].mean(),
                "PF_Overlap": base["PF_Overlap"].mean(),
                "EAF": eaf_width(fronts),
                "PF_Drift": float(np.nanmean(drifts)),
                "Diversity": base["Diversity"].mean(),
                "Runtime": base["Runtime"].mean(),
            }
        )
    inst = pd.DataFrame(inst_rows)
    overall = inst.groupby("method").agg(
        mean_HV=("HV", "mean"),
        mean_IGD=("IGD", "mean"),
        mean_PF_Overlap=("PF_Overlap", "mean"),
        mean_EAF=("EAF", "mean"),
        mean_PF_Drift=("PF_Drift", "mean"),
        mean_Diversity=("Diversity", "mean"),
        mean_Runtime=("Runtime", "mean"),
    )
    specs = [
        ("HV", "max"),
        ("IGD", "min"),
        ("PF_Overlap", "max"),
        ("EAF", "min"),
        ("PF_Drift", "min"),
        ("Runtime", "min"),
    ]
    for metric, direction in specs:
        overall[f"rank_{metric}"] = overall[f"mean_{metric}"].rank(ascending=(direction == "min"))
    overall["RankScore"] = overall[[f"rank_{m}" for m, _ in specs]].mean(axis=1)
    overall = overall.sort_values("RankScore")

    report = out_root / "tuning_report"
    report.mkdir(exist_ok=True)
    run_metrics.to_csv(report / "run_metrics.csv", index=False, encoding="utf-8-sig")
    inst.to_csv(report / "instance_method_metrics.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(report / "overall_method_summary.csv", encoding="utf-8-sig")
    print(f"OUT_ROOT={out_root}")
    print(f"REPORT={report}")
    print(overall.to_string())


if __name__ == "__main__":
    main()
