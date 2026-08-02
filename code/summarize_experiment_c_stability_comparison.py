from __future__ import annotations

import argparse
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
EXPERIMENT_C_METHOD = "ExperimentC_StabilityAware_ECMADE_MOO"

BASELINE_METHODS = {
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


def latest_c_root() -> Path:
    candidates = sorted(OUT_ROOT.glob("experiment_c_stability_ecmade_moo_*"))
    if not candidates:
        return OUT_ROOT / "experiment_c_stability_ecmade_moo_20260717"
    return candidates[-1]


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
    }


def discover_runs(methods: dict[str, Path]) -> tuple[pd.DataFrame, dict, dict]:
    rows = []
    pfs = {}
    fronts_by_instance = {}
    for method, folder in methods.items():
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
                    "method": method,
                    "run": rec["run"],
                    "PF_Size": len(pf),
                    "Runtime": read_runtime(rec["run_dir"] / "runtime.csv"),
                    "source_folder": str(folder),
                }
            )
    run_df = pd.DataFrame(rows)
    if run_df.empty:
        raise RuntimeError("No Experiment C comparison runs found.")
    counts = run_df.groupby("method").size()
    if counts.nunique() != 1:
        raise RuntimeError(f"Run count mismatch by method:\n{counts}")
    return run_df, pfs, fronts_by_instance


def compute_common_reference_metrics(methods: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    run_df, pfs, fronts_by_instance = discover_runs(methods)
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


def build_win_loss(ranked: pd.DataFrame) -> pd.DataFrame:
    rows = []
    methods = sorted(ranked["method"].unique())
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-c-root", type=Path, default=latest_c_root())
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUT_ROOT / "experiment_c_stability_comparison_20260717",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    c_root = args.experiment_c_root if args.experiment_c_root.is_absolute() else ROOT / args.experiment_c_root
    out_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    methods = dict(BASELINE_METHODS)
    methods[EXPERIMENT_C_METHOD] = c_root

    out_dir.mkdir(parents=True, exist_ok=True)
    instance_metrics, run_metrics = compute_common_reference_metrics(methods)
    ranked = add_instance_ranks(instance_metrics)
    overall = build_overall(ranked)
    win_loss = build_win_loss(ranked)

    run_metrics.to_csv(out_dir / "combined_run_metrics_common_reference.csv", index=False, encoding="utf-8-sig")
    instance_metrics.to_csv(out_dir / "combined_instance_method_metrics_raw.csv", index=False, encoding="utf-8-sig")
    ranked.to_csv(out_dir / "combined_instance_method_metrics_ranked.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(out_dir / "overall_configuration_comparison.csv", index=False, encoding="utf-8-sig")
    win_loss.to_csv(out_dir / "pairwise_win_tie_loss_by_metric.csv", index=False, encoding="utf-8-sig")

    print(f"OUT_DIR={out_dir}")
    print(overall.to_string(index=False))


if __name__ == "__main__":
    main()
