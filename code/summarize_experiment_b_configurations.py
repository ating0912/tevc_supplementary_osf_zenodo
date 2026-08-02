from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from rank_knowledge_base_parameter_search import (
    centroid,
    diversity,
    hv2d,
    igd,
    nondominated,
    normalize,
    overlap,
    read_matrix,
    read_runtime,
    thin,
)


ROOT = Path(__file__).resolve().parent
OUT_ROOT = ROOT / "p0_lite_outputs"

METHODS = {
    "HandCrafted_ECMADE_MOO": OUT_ROOT / "synthetic_constrained_portfolio",
    "RandomConfig_ECMADE_MOO": OUT_ROOT / "random_config_ecmade_moo_20260711_074253",
    "BayesianConfig_ECMADE_MOO": OUT_ROOT / "bayesian_config_ecmade_moo_20260713_140251",
    "MetaDesigned_ECMADE_MOO": OUT_ROOT / "meta_designed_ecmade_moo_20260713_164632",
}

METRIC_SPECS = [
    ("HV", "max"),
    ("IGD", "min"),
    ("PF_Overlap", "max"),
    ("PF_Drift", "min"),
    ("Diversity", "max"),
    ("Runtime", "min"),
]


def parse_run(pf_file: Path, method: str) -> dict | None:
    parts = pf_file.parts
    run_dir = pf_file.parent
    run = int(run_dir.name.split("_")[-1])
    if method == "BayesianConfig_ECMADE_MOO":
        try:
            idx = parts.index("final_test")
        except ValueError:
            return None
        if parts[idx + 1] != "test":
            return None
        instance = parts[idx + 2]
        k_value = int(parts[idx + 3].split("_")[-1])
        method_dir = parts[idx + 4]
    else:
        try:
            idx = parts.index("test")
        except ValueError:
            return None
        instance = parts[idx + 1]
        k_value = int(parts[idx + 2].split("_")[-1])
        method_dir = parts[idx + 3]

    if method == "HandCrafted_ECMADE_MOO" and method_dir != "ECMADE_MOO":
        return None
    if method != "HandCrafted_ECMADE_MOO" and method_dir != method:
        return None

    return {
        "split": "test",
        "instance": instance,
        "K": k_value,
        "method": method,
        "run": run,
        "run_dir": run_dir,
        "pf_file": pf_file,
    }


def discover_selected_runs() -> tuple[pd.DataFrame, dict, dict]:
    rows = []
    pfs = {}
    fronts_by_instance = {}
    for method, folder in METHODS.items():
        if method == "BayesianConfig_ECMADE_MOO":
            files = (folder / "final_test").glob("test/*/K_*/*/run_*/pf_obj.csv")
        elif method == "HandCrafted_ECMADE_MOO":
            files = folder.glob("test/*/K_*/ECMADE_MOO/run_*/pf_obj.csv")
        else:
            files = folder.glob("test/*/K_*/*/run_*/pf_obj.csv")

        for pf_file in files:
            rec = parse_run(pf_file, method)
            if rec is None:
                continue
            pf = read_matrix(pf_file)
            if len(pf) == 0:
                continue
            key = (rec["split"], rec["instance"], rec["K"], rec["method"], rec["run"])
            instance_key = (rec["split"], rec["instance"], rec["K"])
            pfs[key] = pf
            fronts_by_instance.setdefault(instance_key, []).append(pf)
            rows.append(
                {
                    "split": rec["split"],
                    "instance": rec["instance"],
                    "K": rec["K"],
                    "method": rec["method"],
                    "run": rec["run"],
                    "PF_Size": len(pf),
                    "Runtime": read_runtime(rec["run_dir"] / "runtime.csv"),
                    "source_folder": str(folder),
                }
            )
    run_df = pd.DataFrame(rows)
    if run_df.empty:
        raise RuntimeError("No selected Experiment B runs found.")
    expected_runs = run_df.groupby("method").size()
    if expected_runs.nunique() != 1:
        raise RuntimeError(f"Run count mismatch by method:\n{expected_runs}")
    expected_instances = run_df.groupby("method")["instance"].nunique()
    if expected_instances.nunique() != 1:
        raise RuntimeError(f"Instance count mismatch by method:\n{expected_instances}")
    return run_df, pfs, fronts_by_instance


def compute_common_reference_metrics() -> tuple[pd.DataFrame, pd.DataFrame]:
    run_df, pfs, fronts_by_instance = discover_selected_runs()

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
        key = (rec["split"], rec["instance"], int(rec["K"]), rec["method"], int(rec["run"]))
        instance_key = (rec["split"], rec["instance"], int(rec["K"]))
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
    for keys, base in run_metrics.groupby(["split", "instance", "K", "method"]):
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
                "runs": int(base["run"].nunique()),
                "source_folder": base["source_folder"].iloc[0],
            }
        )
    return pd.DataFrame(inst_rows), run_metrics


def add_instance_ranks(df: pd.DataFrame) -> pd.DataFrame:
    ranked_frames = []
    for _, base in df.groupby(["split", "instance", "K"], sort=False):
        ranked = base.copy()
        rank_cols = []
        for metric, direction in METRIC_SPECS:
            col = f"rank_{metric}"
            ranked[col] = ranked[metric].rank(ascending=(direction == "min"), method="average")
            rank_cols.append(col)
        ranked["RankScore"] = ranked[rank_cols].mean(axis=1)
        ranked["OverallInstanceRank"] = ranked["RankScore"].rank(ascending=True, method="average")
        ranked_frames.append(ranked)
    return pd.concat(ranked_frames, ignore_index=True)


def build_overall(ranked: pd.DataFrame) -> pd.DataFrame:
    overall = ranked.groupby("method").agg(
        instances=("instance", "nunique"),
        mean_HV=("HV", "mean"),
        mean_IGD=("IGD", "mean"),
        mean_PF_Overlap=("PF_Overlap", "mean"),
        mean_PF_Drift=("PF_Drift", "mean"),
        mean_Diversity=("Diversity", "mean"),
        mean_Runtime=("Runtime", "mean"),
        mean_RankScore=("RankScore", "mean"),
        mean_InstanceRank=("OverallInstanceRank", "mean"),
        first_place_instances=("OverallInstanceRank", lambda s: int((s == 1).sum())),
    ).reset_index()

    for metric, direction in METRIC_SPECS:
        overall[f"overall_rank_{metric}"] = overall[f"mean_{metric}"].rank(
            ascending=(direction == "min"), method="average"
        )
    overall["overall_RankScore"] = overall[
        [f"overall_rank_{metric}" for metric, _ in METRIC_SPECS]
    ].mean(axis=1)
    return overall.sort_values(["overall_RankScore", "mean_RankScore", "method"])


def build_win_loss(ranked: pd.DataFrame) -> pd.DataFrame:
    rows = []
    methods = list(METHODS)
    for metric, direction in METRIC_SPECS:
        pivot = ranked.pivot_table(
            index=["split", "instance", "K"], columns="method", values=metric, aggfunc="mean"
        )
        for a in methods:
            for b in methods:
                if a == b:
                    continue
                if direction == "max":
                    wins = int((pivot[a] > pivot[b]).sum())
                    losses = int((pivot[a] < pivot[b]).sum())
                else:
                    wins = int((pivot[a] < pivot[b]).sum())
                    losses = int((pivot[a] > pivot[b]).sum())
                ties = int(np.isclose(pivot[a], pivot[b], rtol=1e-10, atol=1e-12).sum())
                rows.append(
                    {
                        "metric": metric,
                        "direction": direction,
                        "method_a": a,
                        "method_b": b,
                        "wins": wins,
                        "ties": ties,
                        "losses": losses,
                        "total_instances": len(pivot),
                    }
                )
    return pd.DataFrame(rows)


def build_theta_usage() -> pd.DataFrame:
    frames = []
    assignment_files = {
        "HandCrafted_ECMADE_MOO": None,
        "RandomConfig_ECMADE_MOO": METHODS["RandomConfig_ECMADE_MOO"] / "random_config_assignment.csv",
        "BayesianConfig_ECMADE_MOO": METHODS["BayesianConfig_ECMADE_MOO"] / "bayesian_config_summary_by_instance.csv",
        "MetaDesigned_ECMADE_MOO": METHODS["MetaDesigned_ECMADE_MOO"] / "meta_designed_theta_assignment_used.csv",
    }
    for method, path in assignment_files.items():
        if path is None:
            frames.append(pd.DataFrame([{"method": method, "theta_id": "hand-crafted", "instances": 32}]))
            continue
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if "theta_id" not in df.columns:
            continue
        usage = (
            df.groupby("theta_id")
            .size()
            .rename("instances")
            .reset_index()
            .sort_values(["instances", "theta_id"], ascending=[False, True])
        )
        usage.insert(0, "method", method)
        frames.append(usage)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_markdown(overall: pd.DataFrame, out_dir: Path) -> None:
    cols = [
        "method",
        "instances",
        "mean_HV",
        "mean_IGD",
        "mean_PF_Overlap",
        "mean_PF_Drift",
        "mean_Runtime",
        "overall_RankScore",
        "mean_InstanceRank",
        "first_place_instances",
    ]
    md = ["# Experiment B Configuration Summary", ""]
    md.append("## Overall")
    md.append("")
    md.append(overall[cols].to_markdown(index=False, floatfmt=".6f"))
    md.append("")
    md.append("Metrics are re-ranked across Random, Bayesian, and Meta-designed outputs on the same 32 unseen test instances.")
    (out_dir / "README_summary.md").write_text("\n".join(md), encoding="utf-8")


def main() -> None:
    out_dir = OUT_ROOT / "experiment_b_configuration_summary_20260713"
    out_dir.mkdir(parents=True, exist_ok=True)

    instance_metrics, run_metrics = compute_common_reference_metrics()
    ranked = add_instance_ranks(instance_metrics)
    overall = build_overall(ranked)
    win_loss = build_win_loss(ranked)
    theta_usage = build_theta_usage()

    run_metrics.to_csv(out_dir / "combined_run_metrics_common_reference.csv", index=False, encoding="utf-8-sig")
    instance_metrics.to_csv(out_dir / "combined_instance_method_metrics_raw.csv", index=False, encoding="utf-8-sig")
    ranked.to_csv(out_dir / "combined_instance_method_metrics_ranked.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(out_dir / "overall_configuration_comparison.csv", index=False, encoding="utf-8-sig")
    win_loss.to_csv(out_dir / "pairwise_win_tie_loss_by_metric.csv", index=False, encoding="utf-8-sig")
    if not theta_usage.empty:
        theta_usage.to_csv(out_dir / "theta_usage_by_method.csv", index=False, encoding="utf-8-sig")
    build_markdown(overall, out_dir)

    print(f"OUT_DIR={out_dir}")
    print(overall.to_string(index=False))


if __name__ == "__main__":
    main()
