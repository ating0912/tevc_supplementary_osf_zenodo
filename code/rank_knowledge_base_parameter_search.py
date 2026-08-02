import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd


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
    for point in pts:
        if point[1] < best_y - 1e-12:
            keep.append(point)
            best_y = point[1]
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


def parse_run_dir(run_dir, root):
    rel = run_dir.relative_to(root).parts
    run = int(run_dir.name.split("_")[-1])
    if len(rel) >= 5 and rel[-3].startswith("K_"):
        return {
            "split": rel[-5],
            "instance": rel[-4],
            "K": int(rel[-3].split("_")[-1]),
            "method": rel[-2],
            "run": run,
        }
    if len(rel) >= 3 and rel[-3].startswith("K_"):
        return {
            "split": "orlib",
            "instance": "port1",
            "K": int(rel[-3].split("_")[-1]),
            "method": rel[-2],
            "run": run,
        }
    return None


def discover_runs(root):
    rows = []
    pfs = {}
    fronts_by_instance = {}
    for pf_file in root.glob("**/pf_obj.csv"):
        run_dir = pf_file.parent
        rec = parse_run_dir(run_dir, root)
        if rec is None:
            continue
        pf = read_matrix(pf_file)
        if len(pf) == 0:
            continue
        key = (rec["split"], rec["instance"], rec["K"], rec["method"], rec["run"])
        pfs[key] = pf
        instance_key = (rec["split"], rec["instance"], rec["K"])
        fronts_by_instance.setdefault(instance_key, []).append(pf)
        rows.append(
            {
                **rec,
                "PF_Size": len(pf),
                "Runtime": read_runtime(run_dir / "runtime.csv"),
            }
        )
    return pd.DataFrame(rows), pfs, fronts_by_instance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    root = Path(args.root)
    run_df, pfs, fronts_by_instance = discover_runs(root)
    if run_df.empty:
        raise RuntimeError(f"No pf_obj.csv runs found under {root}")

    ref_info = {}
    for instance_key, fronts in fronts_by_instance.items():
        union = np.vstack(fronts)
        ideal = union.min(axis=0)
        nadir = union.max(axis=0)
        ref = thin(nondominated(normalize(union, ideal, nadir)))
        ref_info[instance_key] = (ideal, nadir, ref)

    metric_rows = []
    norm_fronts = {}
    for rec in run_df.to_dict("records"):
        key = (rec["split"], rec["instance"], rec["K"], rec["method"], rec["run"])
        instance_key = (rec["split"], rec["instance"], rec["K"])
        ideal, nadir, ref = ref_info[instance_key]
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
    group_cols = ["split", "instance", "K", "method"]
    for keys, base in run_metrics.groupby(group_cols):
        split, instance, k_value, method = keys
        fronts = [
            norm_fronts[(split, instance, int(k_value), method, int(run))]
            for run in base["run"]
        ]
        centroids = np.vstack([centroid(front) for front in fronts if len(front)])
        mean_c = np.nanmean(centroids, axis=0)
        drifts = [
            float(np.sqrt(((centroid(front) - mean_c) ** 2).sum()))
            for front in fronts
            if len(front)
        ]
        inst_rows.append(
            {
                "split": split,
                "instance": instance,
                "K": int(k_value),
                "method": method,
                "HV": base["HV"].mean(),
                "IGD": base["IGD"].mean(),
                "PF_Overlap": base["PF_Overlap"].mean(),
                "PF_Drift": float(np.nanmean(drifts)),
                "Diversity": base["Diversity"].mean(),
                "Runtime": base["Runtime"].mean(),
            }
        )
    inst = pd.DataFrame(inst_rows)
    label_specs = [
        ("HV", False),
        ("IGD", True),
        ("PF_Overlap", False),
        ("PF_Drift", True),
        ("Runtime", True),
    ]
    label_frames = []
    for _, base in inst.groupby(["split", "instance", "K"]):
        ranked = base.copy()
        rank_cols = []
        for metric, ascending in label_specs:
            col = f"rank_{metric}"
            ranked[col] = ranked[metric].rank(ascending=ascending)
            rank_cols.append(col)
        ranked["LabelScore"] = ranked[rank_cols].mean(axis=1)
        ranked["ThetaRank"] = ranked["LabelScore"].rank(method="first", ascending=True).astype(int)
        label_frames.append(ranked.sort_values("ThetaRank"))
    label_df = pd.concat(label_frames, ignore_index=True)

    overall = inst.groupby("method").agg(
        mean_HV=("HV", "mean"),
        mean_IGD=("IGD", "mean"),
        mean_PF_Overlap=("PF_Overlap", "mean"),
        mean_PF_Drift=("PF_Drift", "mean"),
        mean_Diversity=("Diversity", "mean"),
        mean_Runtime=("Runtime", "mean"),
    )
    specs = [
        ("HV", "max"),
        ("IGD", "min"),
        ("PF_Overlap", "max"),
        ("PF_Drift", "min"),
        ("Runtime", "min"),
    ]
    for metric, direction in specs:
        overall[f"rank_{metric}"] = overall[f"mean_{metric}"].rank(ascending=(direction == "min"))
    overall["RankScore"] = overall[[f"rank_{metric}" for metric, _ in specs]].mean(axis=1)
    overall = overall.sort_values("RankScore")

    candidate_file = root / "kb_theta_candidates.csv"
    if candidate_file.exists():
        candidates = pd.read_csv(candidate_file)
        label_df = label_df.merge(candidates, on="method", how="left")
        overall = overall.merge(candidates, left_index=True, right_on="method", how="left")
        overall = overall.set_index("method")

    report = root / "knowledge_base_parameter_report"
    report.mkdir(exist_ok=True)
    run_metrics.to_csv(report / "run_metrics.csv", index=False, encoding="utf-8-sig")
    inst.to_csv(report / "instance_method_metrics.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(report / "overall_method_summary.csv", encoding="utf-8-sig")
    label_df.to_csv(report / "theta_ranking_labels.csv", index=False, encoding="utf-8-sig")
    top1 = label_df[label_df["ThetaRank"] == 1].copy()
    top1.rename(columns={"method": "label_method"}, inplace=True)
    top1.to_csv(report / "top1_classification_labels.csv", index=False, encoding="utf-8-sig")
    label_df.to_csv(report / "regression_score_labels.csv", index=False, encoding="utf-8-sig")
    label_df[label_df["split"] != "test"].to_csv(
        report / "train_val_theta_selection_labels.csv", index=False, encoding="utf-8-sig"
    )
    print(f"REPORT={report}")
    print(overall.head(20).to_string())


if __name__ == "__main__":
    main()
