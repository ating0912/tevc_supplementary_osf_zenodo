import os
import math
from collections import defaultdict
from datetime import datetime

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from build_synthetic_experiment_a_report import (
    MANIFEST,
    OUT_ROOT,
    METHODS,
    RUNS,
    safe_read_matrix,
    read_runtime,
    read_feasible,
    normalize,
    nondominated,
    thin_front,
    hv2d,
    igd,
    pf_overlap,
    diversity_spread,
    spacing,
    eaf_band_width,
    centroid,
)


def run_dir(split, instance, k, method, run):
    return os.path.join(OUT_ROOT, split, instance, f"K_{int(k):02d}", method, f"run_{run:03d}")


def load_subset():
    manifest = pd.read_csv(MANIFEST).head(10)
    run_pfs = {}
    records = []
    missing = []
    by_instance_points = defaultdict(list)
    by_instance_method = defaultdict(list)
    for _, row in manifest.iterrows():
        for method in METHODS:
            for run in RUNS:
                rd = run_dir(row["split"], row["instance"], row["K"], method, run)
                required = ["pf_obj.csv", "runtime.csv", "feasible_rate.csv"]
                absent = [name for name in required if not os.path.exists(os.path.join(rd, name))]
                if absent:
                    missing.append(
                        {
                            "split": row["split"],
                            "instance": row["instance"],
                            "K": int(row["K"]),
                            "method": method,
                            "run": run,
                            "missing": ";".join(absent),
                            "run_dir": rd,
                        }
                    )
                    continue
                pf = safe_read_matrix(os.path.join(rd, "pf_obj.csv"))
                rt = read_runtime(os.path.join(rd, "runtime.csv"))
                pf_feas, pop_feas = read_feasible(os.path.join(rd, "feasible_rate.csv"))
                key = (row["instance"], method, run)
                run_pfs[key] = pf
                by_instance_points[row["instance"]].append(pf)
                by_instance_method[(row["instance"], method)].append(pf)
                records.append(
                    {
                        "split": row["split"],
                        "instance": row["instance"],
                        "assets": int(row["assets"]),
                        "K": int(row["K"]),
                        "k_ratio": row["k_ratio"],
                        "corr_structure": row["corr_structure"],
                        "return_distribution": row["return_distribution"],
                        "risk_structure": row["risk_structure"],
                        "method": method,
                        "run": run,
                        "PF_Size": len(pf),
                        "Runtime": rt,
                        "PF_Feasible_Rate": pf_feas,
                        "Population_Feasible_Rate": pop_feas,
                    }
                )
    return manifest, run_pfs, records, by_instance_points, by_instance_method, missing


def draw_stability_dashboard(path, overall):
    metrics = [
        ("mean_PF_Overlap", "PF overlap", True),
        ("mean_EAF_Band_Width", "EAF width", False),
        ("mean_PF_Drift", "PF drift", False),
        ("StabilityRankScore", "Stability rank", False),
    ]
    colors = {
        "NSGAII": (51, 102, 204),
        "SPEA2": (220, 57, 18),
        "MOEAD": (16, 150, 24),
        "GDE3": (153, 0, 153),
        "A_MPMO": (255, 153, 0),
        "ECMADE_MOO": (0, 137, 123),
    }
    w, h = 1600, 950
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    try:
        font_title = ImageFont.truetype("arial.ttf", 34)
        font = ImageFont.truetype("arial.ttf", 20)
        font_small = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font_title = font = font_small = None
    d.text((40, 24), "First 10 Instances Stability Comparison", fill=(20, 40, 70), font=font_title)
    panel_w, panel_h = 740, 390
    for idx, (col, label, higher_better) in enumerate(metrics):
        x0 = 40 + (idx % 2) * 780
        y0 = 90 + (idx // 2) * 420
        d.rectangle([x0, y0, x0 + panel_w, y0 + panel_h], outline=(210, 220, 230), width=2)
        d.text((x0 + 18, y0 + 14), label, fill=(30, 60, 90), font=font)
        vals = overall[col].to_dict()
        finite_vals = [v for v in vals.values() if math.isfinite(v)]
        max_v = max(finite_vals) if finite_vals else 1
        min_v = min(finite_vals) if finite_vals else 0
        span = max(max_v - min_v, 1e-12)
        methods = list(overall.index)
        bar_top = y0 + 70
        for j, method in enumerate(methods):
            v = vals[method]
            if higher_better:
                length = int((v / max_v) * 470) if max_v > 0 else 0
            else:
                length = int(((max_v - v) / span) * 470)
            yy = bar_top + j * 47
            d.text((x0 + 18, yy + 3), method, fill=(40, 40, 40), font=font_small)
            d.rectangle([x0 + 160, yy, x0 + 160 + max(length, 2), yy + 24], fill=colors.get(method, (100, 100, 100)))
            d.text((x0 + 650, yy + 2), f"{v:.4g}", fill=(40, 40, 40), font=font_small)
    img.save(path)


def main():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(OUT_ROOT, f"ecmade_consensus_first10_stability_{stamp}")
    os.makedirs(out_dir, exist_ok=True)

    manifest, run_pfs, records, by_instance_points, by_instance_method, missing = load_subset()
    pd.DataFrame(missing).to_csv(os.path.join(out_dir, "missing_outputs.csv"), index=False, encoding="utf-8-sig")
    if missing:
        print(f"MISSING_OUTPUTS={len(missing)}")
        print(f"OUT_DIR={out_dir}")
        return

    ref_info = {}
    for instance, fronts in by_instance_points.items():
        union = np.vstack([f for f in fronts if len(f) > 0])
        ideal = union.min(axis=0)
        nadir = union.max(axis=0)
        norm_union = normalize(union, ideal, nadir)
        ref_info[instance] = {
            "ideal": ideal,
            "nadir": nadir,
            "ref": thin_front(nondominated(norm_union), 120),
        }

    metric_rows = []
    for rec in records:
        instance, method, run = rec["instance"], rec["method"], rec["run"]
        info = ref_info[instance]
        pf = run_pfs[(instance, method, run)]
        norm_pf = thin_front(nondominated(normalize(pf, info["ideal"], info["nadir"])), 120)
        metric_rows.append(
            {
                **rec,
                "HV": hv2d(norm_pf),
                "IGD": igd(norm_pf, info["ref"]),
                "PF_Overlap": pf_overlap(norm_pf, info["ref"]),
                "Diversity": diversity_spread(norm_pf),
                "Spacing": spacing(norm_pf),
            }
        )
    run_metrics = pd.DataFrame(metric_rows)

    inst_rows = []
    for (instance, method), fronts in by_instance_method.items():
        info = ref_info[instance]
        norm_fronts = [thin_front(nondominated(normalize(f, info["ideal"], info["nadir"])), 120) for f in fronts]
        centroids = np.vstack([centroid(f) for f in norm_fronts if len(f) > 0])
        mean_centroid = np.nanmean(centroids, axis=0)
        drifts = [float(np.sqrt(((centroid(f) - mean_centroid) ** 2).sum())) for f in norm_fronts if len(f) > 0]
        base = run_metrics[(run_metrics["instance"] == instance) & (run_metrics["method"] == method)]
        meta = base.iloc[0].to_dict()
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
                "EAF_Band_Width": eaf_band_width(norm_fronts),
                "PF_Drift": float(np.nanmean(drifts)),
                "Diversity": base["Diversity"].mean(),
                "Runtime": base["Runtime"].mean(),
            }
        )
    inst_metrics = pd.DataFrame(inst_rows)
    overall = inst_metrics.groupby("method").agg(
        mean_HV=("HV", "mean"),
        mean_IGD=("IGD", "mean"),
        mean_PF_Overlap=("PF_Overlap", "mean"),
        mean_EAF_Band_Width=("EAF_Band_Width", "mean"),
        mean_PF_Drift=("PF_Drift", "mean"),
        mean_Diversity=("Diversity", "mean"),
        mean_Runtime=("Runtime", "mean"),
    )
    overall["rank_PF_Overlap"] = overall["mean_PF_Overlap"].rank(ascending=False, method="average")
    overall["rank_EAF_Band_Width"] = overall["mean_EAF_Band_Width"].rank(ascending=True, method="average")
    overall["rank_PF_Drift"] = overall["mean_PF_Drift"].rank(ascending=True, method="average")
    overall["StabilityRankScore"] = overall[["rank_PF_Overlap", "rank_EAF_Band_Width", "rank_PF_Drift"]].mean(axis=1)
    overall = overall.sort_values("StabilityRankScore")

    winner_counts = []
    for metric, direction in [("PF_Overlap", "max"), ("EAF_Band_Width", "min"), ("PF_Drift", "min")]:
        idx = inst_metrics.groupby("instance")[metric].idxmax() if direction == "max" else inst_metrics.groupby("instance")[metric].idxmin()
        counts = inst_metrics.loc[idx, "method"].value_counts().reindex(METHODS).fillna(0).astype(int)
        for method, count in counts.items():
            winner_counts.append({"metric": metric, "method": method, "winner_instances": count})
    winners = pd.DataFrame(winner_counts)

    run_metrics.to_csv(os.path.join(out_dir, "run_metrics_first10.csv"), index=False, encoding="utf-8-sig")
    inst_metrics.to_csv(os.path.join(out_dir, "instance_method_stability_first10.csv"), index=False, encoding="utf-8-sig")
    overall.to_csv(os.path.join(out_dir, "overall_stability_summary_first10.csv"), encoding="utf-8-sig")
    winners.to_csv(os.path.join(out_dir, "stability_winner_counts_first10.csv"), index=False, encoding="utf-8-sig")
    draw_stability_dashboard(os.path.join(out_dir, "stability_dashboard_first10.png"), overall)

    print(f"OUT_DIR={out_dir}")
    print(f"EXPECTED_RUNS={len(manifest) * len(METHODS) * len(list(RUNS))}")
    print("OVERALL_STABILITY")
    print(overall.to_string())
    print("WINNER_COUNTS")
    print(winners.pivot(index="method", columns="metric", values="winner_instances").fillna(0).astype(int).to_string())


if __name__ == "__main__":
    main()
