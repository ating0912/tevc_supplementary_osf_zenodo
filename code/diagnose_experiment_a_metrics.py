import math
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd


ROOT = Path(r"C:\Users\yiting\Documents\Playground")
OUT_ROOT = ROOT / "p0_lite_outputs" / "synthetic_constrained_portfolio"
REPORT = OUT_ROOT / "experiment_A_report_20260703_081032"
MANIFEST = ROOT / "data" / "synthetic_constrained_portfolio" / "manifest.csv"
METHODS = ["NSGAII", "SPEA2", "MOEAD", "GDE3", "A_MPMO", "ECMADE_MOO"]
RUNS = range(1, 31)


def read_pf(path):
    try:
        arr = np.loadtxt(path, delimiter=",")
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        return arr[:, :2]
    except Exception:
        return np.empty((0, 2))


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


def thin_front(points, max_points=300):
    points = np.asarray(points, dtype=float)
    if len(points) <= max_points:
        return points
    order = np.argsort(points[:, 0])
    pts = points[order]
    idx = np.linspace(0, len(pts) - 1, max_points).round().astype(int)
    return pts[idx]


def overlap(run_pf, ref_pf, tol):
    if len(run_pf) == 0 or len(ref_pf) == 0:
        return 0.0
    covered = 0
    for p in ref_pf:
        if np.sqrt(((run_pf - p) ** 2).sum(axis=1)).min() <= tol:
            covered += 1
    return covered / len(ref_pf)


def main():
    manifest = pd.read_csv(MANIFEST)
    tasks = []
    for _, row in manifest.iterrows():
        for method in METHODS:
            for run in RUNS:
                pf_path = OUT_ROOT / row["split"] / row["instance"] / f"K_{int(row['K']):02d}" / method / f"run_{run:03d}" / "pf_obj.csv"
                tasks.append((row["split"], row["instance"], int(row["assets"]), int(row["K"]), method, run, pf_path))

    fronts_by_instance = {}
    run_fronts = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(read_pf, task[-1]): task for task in tasks}
        for n, fut in enumerate(as_completed(futures), 1):
            split, instance, assets, k, method, run, _ = futures[fut]
            pf = fut.result()
            if len(pf):
                fronts_by_instance.setdefault(instance, []).append(pf)
                run_fronts.append((split, instance, assets, k, method, run, pf))
            if n % 2000 == 0:
                print(f"read {n}/{len(tasks)} PF files", flush=True)

    ref_info = {}
    for key, fronts in fronts_by_instance.items():
        union = np.vstack(fronts)
        ideal = union.min(axis=0)
        nadir = union.max(axis=0)
        ref = thin_front(nondominated(normalize(union, ideal, nadir)), 120)
        ref_info[key] = (ideal, nadir, ref)

    rows = []
    for split, instance, assets, k, method, run, pf in run_fronts:
        ideal, nadir, ref = ref_info[instance]
        norm_pf = thin_front(nondominated(normalize(pf, ideal, nadir)), 120)
        row = {"split": split, "instance": instance, "assets": assets, "K": k, "method": method, "run": run}
        for tol in [0.005, 0.01, 0.02, 0.05]:
            row[f"overlap_tol_{tol:g}"] = overlap(norm_pf, ref, tol)
        rows.append(row)

    sens = pd.DataFrame(rows)
    overall = sens.groupby("method")[[c for c in sens.columns if c.startswith("overlap_tol_")]].mean().reset_index()
    by_k = sens.groupby(["K", "method"])[[c for c in sens.columns if c.startswith("overlap_tol_")]].mean().reset_index()
    out_dir = REPORT / "diagnostics"
    out_dir.mkdir(exist_ok=True)
    sens.to_csv(out_dir / "pf_overlap_tolerance_run_level.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(out_dir / "pf_overlap_tolerance_overall.csv", index=False, encoding="utf-8-sig")
    by_k.to_csv(out_dir / "pf_overlap_tolerance_by_k.csv", index=False, encoding="utf-8-sig")

    inst = pd.read_csv(REPORT / "instance_method_metrics.csv")
    by_k_metrics = inst.groupby(["K", "method"]).agg(
        HV=("HV", "mean"),
        IGD=("IGD", "mean"),
        PF_Overlap=("PF_Overlap", "mean"),
        EAF=("EAF_Band_Width", "mean"),
        Drift=("PF_Drift", "mean"),
        Diversity=("Diversity", "mean"),
        Runtime=("Runtime", "mean"),
    ).reset_index()
    by_k_metrics.to_csv(out_dir / "quality_stability_by_k.csv", index=False, encoding="utf-8-sig")
    print(f"OUT_DIR={out_dir}")
    print("OVERLAP_TOLERANCE_OVERALL")
    print(overall.to_string(index=False))


if __name__ == "__main__":
    main()
