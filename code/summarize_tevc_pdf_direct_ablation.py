"""Summarize PDF-aligned direct ablation outputs.

Usage:
  python summarize_tevc_pdf_direct_ablation.py --root p0_lite_outputs/tevc_pdf_direct_ablation_...

The root must contain outputs produced by run_tevc_pdf_direct_ablation.m and
rank_knowledge_base_parameter_search.py.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


METRIC_SPECS = [
    ("HV", "max"),
    ("IGD", "min"),
    ("PF_Overlap", "max"),
    ("PF_Drift", "min"),
    ("Diversity", "max"),
    ("Runtime", "min"),
]


def latest_root() -> Path:
    roots = sorted(Path("p0_lite_outputs").glob("tevc_pdf_direct_ablation_*"))
    if not roots:
        raise RuntimeError("No tevc_pdf_direct_ablation_* output folders found.")
    return roots[-1]


def load_inputs(root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    report = root / "knowledge_base_parameter_report"
    inst_path = report / "instance_method_metrics.csv"
    candidates_path = root / "kb_theta_candidates.csv"
    if not inst_path.exists():
        raise RuntimeError(f"Missing {inst_path}. Run rank_knowledge_base_parameter_search.py first.")
    if not candidates_path.exists():
        raise RuntimeError(f"Missing {candidates_path}.")
    inst = pd.read_csv(inst_path, encoding="utf-8-sig")
    candidates = pd.read_csv(candidates_path, encoding="utf-8-sig")
    keep = [
        "method",
        "ablation_family",
        "ablation_level",
        "subpops",
        "source_operator",
        "source_migration",
        "source_elite_ratio",
        "stagnationThreshold",
    ]
    candidates = candidates[[c for c in keep if c in candidates.columns]]
    merged = inst.merge(candidates, on="method", how="left")
    missing = merged["ablation_family"].isna().sum()
    if missing:
        raise RuntimeError(f"{missing} instance rows did not match kb_theta_candidates.csv")
    return merged, candidates


def rank_within_family(inst: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for _, group in inst.groupby(["ablation_family", "split", "instance", "K"], sort=False):
        ranked = group.copy()
        rank_cols = []
        for metric, direction in METRIC_SPECS:
            col = f"rank_{metric}"
            ranked[col] = ranked[metric].rank(ascending=(direction == "min"), method="average")
            rank_cols.append(col)
        ranked["RankScore"] = ranked[rank_cols].mean(axis=1)
        ranked["FamilyInstanceRank"] = ranked["RankScore"].rank(ascending=True, method="average")
        frames.append(ranked)
    return pd.concat(frames, ignore_index=True)


def build_overall(ranked: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (family, method), group in ranked.groupby(["ablation_family", "method"], sort=False):
        row = {
            "ablation_family": family,
            "method": method,
            "ablation_level": group["ablation_level"].iloc[0],
            "instances": int(group["instance"].nunique()),
            "mean_RankScore": group["RankScore"].mean(),
            "mean_FamilyInstanceRank": group["FamilyInstanceRank"].mean(),
            "first_place_instances": int((group["FamilyInstanceRank"] == 1).sum()),
        }
        for metric, _ in METRIC_SPECS:
            row[f"mean_{metric}"] = group[metric].mean()
        rows.append(row)
    overall = pd.DataFrame(rows)
    ranked_frames = []
    for _, group in overall.groupby("ablation_family", sort=False):
        out = group.copy()
        rank_cols = []
        for metric, direction in METRIC_SPECS:
            col = f"overall_rank_{metric}"
            out[col] = out[f"mean_{metric}"].rank(ascending=(direction == "min"), method="average")
            rank_cols.append(col)
        out["overall_RankScore"] = out[rank_cols].mean(axis=1)
        ranked_frames.append(out)
    return pd.concat(ranked_frames, ignore_index=True).sort_values(
        ["ablation_family", "overall_RankScore", "mean_RankScore", "method"],
        kind="stable",
    )


def build_win_loss(ranked: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for family, family_df in ranked.groupby("ablation_family", sort=False):
        methods = sorted(family_df["method"].unique())
        for metric, direction in METRIC_SPECS:
            pivot = family_df.pivot_table(
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
                            "ablation_family": family,
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


def completion_status(root: Path, candidates: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, candidate in candidates.iterrows():
        method = candidate["method"]
        files = list(root.glob(f"test/*/K_*/{method}/run_*/pf_obj.csv"))
        rows.append(
            {
                "method": method,
                "ablation_family": candidate.get("ablation_family", ""),
                "ablation_level": candidate.get("ablation_level", ""),
                "completed_runs": len(files),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args()
    root = args.root or latest_root()
    inst, candidates = load_inputs(root)
    ranked = rank_within_family(inst)
    overall = build_overall(ranked)
    win_loss = build_win_loss(ranked)
    status = completion_status(root, candidates)

    out = root / "pdf_direct_ablation_summary"
    out.mkdir(exist_ok=True)
    ranked.to_csv(out / "pdf_direct_ablation_instance_ranked.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(out / "pdf_direct_ablation_overall.csv", index=False, encoding="utf-8-sig")
    win_loss.to_csv(out / "pdf_direct_ablation_pairwise_win_loss.csv", index=False, encoding="utf-8-sig")
    status.to_csv(out / "pdf_direct_ablation_completion_status.csv", index=False, encoding="utf-8-sig")
    print(f"Wrote {out}")
    print(overall[["ablation_family", "ablation_level", "overall_RankScore", "mean_RankScore"]].to_string(index=False))


if __name__ == "__main__":
    main()
