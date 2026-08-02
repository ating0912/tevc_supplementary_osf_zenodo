"""Common-reference final-test comparison including both replicate variants."""

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
OUT_DIR = OUT_ROOT / "experiment_c_replicate_audit_final_test_20260730"
METHODS = {
    "HandCrafted_ECMADE_MOO": OUT_ROOT / "synthetic_constrained_portfolio",
    "RandomConfig_ECMADE_MOO": OUT_ROOT / "random_config_ecmade_moo_20260711_074253",
    "BayesianConfig_ECMADE_MOO": OUT_ROOT / "bayesian_config_ecmade_moo_20260713_140251" / "final_test",
    "MetaDesigned_ECMADE_MOO": OUT_ROOT / "meta_designed_ecmade_moo_20260713_164632",
    "ExperimentC_ReplicateIncludedAudit_ECMADE_MOO": OUT_ROOT / "experiment_c_stability_ecmade_moo_20260717",
    "ExperimentC_NoReplicate_ECMADE_MOO": OUT_ROOT / "experiment_c_stability_ecmade_moo_no_replicate_20260730",
}
ACTUAL_DIR = {
    "HandCrafted_ECMADE_MOO": "ECMADE_MOO",
    "ExperimentC_ReplicateIncludedAudit_ECMADE_MOO": "ExperimentC_StabilityAware_ECMADE_MOO",
    "ExperimentC_NoReplicate_ECMADE_MOO": "ExperimentC_StabilityAware_ECMADE_MOO",
}
METRIC_SPECS = [
    ("HV", "max"),
    ("IGD", "min"),
    ("PF_Overlap", "max"),
    ("PF_Drift", "min"),
    ("Diversity", "max"),
    ("Runtime", "min"),
]


def iter_pf_files(method: str, folder: Path):
    actual = ACTUAL_DIR.get(method, method)
    if method == "BayesianConfig_ECMADE_MOO":
        yield from folder.glob(f"test/*/K_*/{actual}/run_*/pf_obj.csv")
    else:
        yield from folder.glob(f"test/*/K_*/{actual}/run_*/pf_obj.csv")


def parse_run(pf_file: Path, method: str) -> dict:
    run_dir = pf_file.parent
    return {
        "split": run_dir.parent.parent.parent.parent.name,
        "instance": run_dir.parent.parent.parent.name,
        "K": int(run_dir.parent.parent.name.split("_")[-1]),
        "method": method,
        "run": int(run_dir.name.split("_")[-1]),
        "run_dir": run_dir,
    }


def discover_runs() -> tuple[pd.DataFrame, dict, dict]:
    rows = []
    pfs = {}
    fronts_by_instance = {}
    for method, folder in METHODS.items():
        for pf_file in iter_pf_files(method, folder):
            rec = parse_run(pf_file, method)
            pf = read_matrix(pf_file)
            if len(pf) == 0:
                continue
            key = (rec["split"], rec["instance"], rec["K"], method, rec["run"])
            instance_key = (rec["split"], rec["instance"], rec["K"])
            pfs[key] = pf
            fronts_by_instance.setdefault(instance_key, []).append(pf)
            rows.append(
                {
                    "split": rec["split"],
                    "instance": rec["instance"],
                    "K": rec["K"],
                    "method": method,
                    "run": rec["run"],
                    "PF_Size": len(pf),
                    "Runtime": read_runtime(rec["run_dir"] / "runtime.csv"),
                    "source_folder": str(folder),
                }
            )
    run_df = pd.DataFrame(rows)
    if run_df.empty:
        raise RuntimeError("No final-test runs found.")
    return run_df, pfs, fronts_by_instance


def compute_common_reference_metrics() -> tuple[pd.DataFrame, pd.DataFrame]:
    run_df, pfs, fronts_by_instance = discover_runs()
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
    frames = []
    for _, base in df.groupby(["split", "instance", "K"], sort=False):
        ranked = base.copy()
        rank_cols = []
        for metric, direction in METRIC_SPECS:
            col = f"rank_{metric}"
            ranked[col] = ranked[metric].rank(ascending=(direction == "min"), method="average")
            rank_cols.append(col)
        ranked["RankScore"] = ranked[rank_cols].mean(axis=1)
        ranked["OverallInstanceRank"] = ranked["RankScore"].rank(ascending=True, method="average")
        frames.append(ranked)
    return pd.concat(frames, ignore_index=True)


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


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    instance_metrics, run_metrics = compute_common_reference_metrics()
    ranked = add_instance_ranks(instance_metrics)
    overall = build_overall(ranked)
    run_counts = (
        run_metrics.groupby(["method", "split", "instance", "K"], as_index=False)
        .agg(runs=("run", "nunique"))
        .groupby("method", as_index=False)
        .agg(instances=("instance", "count"), min_runs=("runs", "min"), max_runs=("runs", "max"))
    )

    run_metrics.to_csv(OUT_DIR / "replicate_audit_run_metrics.csv", index=False, encoding="utf-8-sig")
    instance_metrics.to_csv(OUT_DIR / "replicate_audit_instance_method_metrics_raw.csv", index=False, encoding="utf-8-sig")
    ranked.to_csv(OUT_DIR / "replicate_audit_instance_method_ranked.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(OUT_DIR / "replicate_audit_overall_summary.csv", index=False, encoding="utf-8-sig")
    run_counts.to_csv(OUT_DIR / "replicate_audit_run_completeness.csv", index=False, encoding="utf-8-sig")
    print(overall.to_string(index=False))
    print(run_counts.to_string(index=False))


if __name__ == "__main__":
    main()
