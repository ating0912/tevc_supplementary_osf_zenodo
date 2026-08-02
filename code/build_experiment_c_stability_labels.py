"""Build Experiment C stability-aware theta labels.

The input is a completed knowledge_base_parameter_report produced by
rank_knowledge_base_parameter_search.py.  The output keeps the same row
schema as the original theta label files, with C-specific score/rank
columns and C-specific filenames.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_REPORTS = [
    Path(
        "p0_lite_outputs/theta24_70_15_15_training_label_full_20260706/"
        "knowledge_base_parameter_report"
    ),
    Path(
        "p0_lite_outputs/theta24_70_15_15_validation_label_full_20260713/"
        "knowledge_base_parameter_report"
    ),
]

RANK_COLUMNS = ["rank_HV", "rank_IGD", "rank_PF_Overlap", "rank_PF_Drift"]


def workspace_root() -> Path:
    return Path(__file__).resolve().parent


def resolve(path: Path, root: Path) -> Path:
    return path if path.is_absolute() else root / path


def build_labels(report_dir: Path) -> pd.DataFrame:
    source = report_dir / "theta_ranking_labels.csv"
    if not source.exists():
        raise FileNotFoundError(f"Missing source labels: {source}")

    labels = pd.read_csv(source)
    missing = [col for col in RANK_COLUMNS if col not in labels.columns]
    if missing:
        raise RuntimeError(f"{source} is missing rank columns: {missing}")

    out = labels.copy()
    out["C_LabelScore"] = (
        -0.2 * out["rank_HV"]
        - 0.2 * out["rank_IGD"]
        - 0.3 * out["rank_PF_Overlap"]
        - 0.3 * out["rank_PF_Drift"]
    )
    out["C_ThetaRank"] = (
        out.groupby(["split", "instance", "K"])["C_LabelScore"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    out = out.sort_values(["split", "instance", "K", "C_ThetaRank", "method"])
    return out


def write_outputs(report_dir: Path) -> pd.DataFrame:
    labels = build_labels(report_dir)
    labels.to_csv(
        report_dir / "experiment_c_stability_theta_ranking_labels.csv",
        index=False,
        encoding="utf-8-sig",
    )
    labels.to_csv(
        report_dir / "experiment_c_stability_regression_labels.csv",
        index=False,
        encoding="utf-8-sig",
    )
    top1 = labels[labels["C_ThetaRank"] == 1].copy()
    top1 = top1.rename(columns={"method": "label_method"})
    top1.to_csv(
        report_dir / "experiment_c_stability_top1_labels.csv",
        index=False,
        encoding="utf-8-sig",
    )
    return labels


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report-dir",
        type=Path,
        action="append",
        help="knowledge_base_parameter_report directory; may be repeated.",
    )
    return parser.parse_args()


def main() -> None:
    root = workspace_root()
    args = parse_args()
    report_dirs = args.report_dir or DEFAULT_REPORTS
    for report_dir in report_dirs:
        resolved = resolve(report_dir, root)
        labels = write_outputs(resolved)
        groups = labels[["split", "instance", "K"]].drop_duplicates().shape[0]
        methods = labels["method"].nunique()
        print(f"REPORT={resolved}")
        print(f"rows={len(labels)} instance_groups={groups} methods={methods}")
        print(labels[labels["C_ThetaRank"] == 1]["method"].value_counts().to_string())


if __name__ == "__main__":
    main()
