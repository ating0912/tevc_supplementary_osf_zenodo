#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Compute stability-aware score J and weight-sensitivity tables for TEVC experiments.

This script supports two workflows:
1. Formal workflow: read an instance-level CSV with metrics such as
   method/theta_id/instance/HV/IGD/PF_Overlap/EAF_Band_Width/Diversity/Runtime.
2. Current Experiment B sanity-check workflow: read the existing Experiment B DOCX
   report and reconstruct the method-level summary tables.

Outputs:
  - <prefix>_scored.csv
  - <prefix>_rankings.csv
  - <prefix>_sensitivity.csv

Score definitions:
  J_perf  = + normalized HV - normalized IGD
  J_equal = equal-weight stability-aware score over available metrics
  J_rank  = Borda/rank-based aggregate over available metrics

For sensitivity analysis, alpha_stability controls the total weight assigned to
stability/diversity metrics. The remaining weight is split across performance
metrics. Runtime/cost receives a small penalty weight when available.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


BENEFIT_METRICS = {
    "HV",
    "PF_Overlap",
    "PFOverlap",
    "Diversity",
    "Archive_Diversity",
    "Feasible_Rate",
}

COST_METRICS = {
    "IGD",
    "EAF_Band_Width",
    "EAFWidth",
    "PF_Drift",
    "Runtime",
    "Configuration_Cost",
    "ConfigurationCost",
}

METRIC_ALIASES = {
    "PF overlap": "PF_Overlap",
    "PF Overlap": "PF_Overlap",
    "PF drift": "PF_Drift",
    "PF Drift": "PF_Drift",
    "EAF width": "EAF_Band_Width",
    "EAF Width": "EAF_Band_Width",
    "Rank Score": "RankScore",
}


@dataclass(frozen=True)
class MetricSpec:
    name: str
    direction: str  # "benefit" or "cost"


def canonical_col(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[↑↓▲▼]", "", name).strip()
    return METRIC_ALIASES.get(name, name.strip().replace(" ", "_"))


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [canonical_col(str(c)) for c in out.columns]
    return out


def numeric_or_nan(value) -> float:
    if value is None:
        return math.nan
    text = str(value).strip()
    if not text:
        return math.nan
    text = text.replace(",", "")
    try:
        return float(text)
    except ValueError:
        return math.nan


def discover_metrics(df: pd.DataFrame) -> list[MetricSpec]:
    specs: list[MetricSpec] = []
    for col in df.columns:
        if col in BENEFIT_METRICS:
            specs.append(MetricSpec(col, "benefit"))
        elif col in COST_METRICS:
            specs.append(MetricSpec(col, "cost"))
    return specs


def minmax_normalize(series: pd.Series, direction: str) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    mn = values.min(skipna=True)
    mx = values.max(skipna=True)
    if pd.isna(mn) or pd.isna(mx):
        return pd.Series([math.nan] * len(series), index=series.index)
    if abs(mx - mn) < 1e-12:
        return pd.Series([0.5] * len(series), index=series.index)
    normalized = (values - mn) / (mx - mn)
    if direction == "cost":
        normalized = 1.0 - normalized
    return normalized


def default_group_columns(df: pd.DataFrame) -> list[str]:
    # Normalize within each instance when possible; otherwise one global group.
    candidates = ["dataset", "split", "instance", "K"]
    return [c for c in candidates if c in df.columns]


def add_normalized_metrics(
    df: pd.DataFrame,
    metrics: list[MetricSpec],
    group_cols: list[str],
) -> pd.DataFrame:
    out = df.copy()
    if not group_cols:
        group_iter = [(None, out.index)]
    else:
        group_iter = [(key, group.index) for key, group in out.groupby(group_cols, dropna=False)]

    for spec in metrics:
        norm_col = f"n_{spec.name}"
        out[norm_col] = math.nan
        for _, idx in group_iter:
            out.loc[idx, norm_col] = minmax_normalize(out.loc[idx, spec.name], spec.direction)
    return out


def mean_available(row: pd.Series, columns: Iterable[str]) -> float:
    vals = [numeric_or_nan(row.get(c)) for c in columns]
    vals = [v for v in vals if not math.isnan(v)]
    if not vals:
        return math.nan
    return sum(vals) / len(vals)


def add_scores(df: pd.DataFrame, metrics: list[MetricSpec]) -> pd.DataFrame:
    out = df.copy()
    norm = {spec.name: f"n_{spec.name}" for spec in metrics}

    perf_cols = [norm[m] for m in ["HV", "IGD"] if m in norm]
    stability_cols = [norm[m] for m in ["PF_Overlap", "EAF_Band_Width", "PF_Drift"] if m in norm]
    diversity_cols = [norm[m] for m in ["Diversity", "Archive_Diversity"] if m in norm]
    runtime_cols = [norm[m] for m in ["Runtime", "Configuration_Cost", "ConfigurationCost"] if m in norm]

    out["J_perf"] = out.apply(lambda r: mean_available(r, perf_cols), axis=1)
    equal_cols = perf_cols + stability_cols + diversity_cols + runtime_cols
    out["J_equal"] = out.apply(lambda r: mean_available(r, equal_cols), axis=1)

    # Explicit weighted score with a conservative stability-aware default.
    weighted_terms = []
    weights = []
    for col in perf_cols:
        weighted_terms.append(col)
        weights.append(0.25 / max(len(perf_cols), 1))
    for col in stability_cols:
        weighted_terms.append(col)
        weights.append(0.45 / max(len(stability_cols), 1))
    for col in diversity_cols:
        weighted_terms.append(col)
        weights.append(0.20 / max(len(diversity_cols), 1))
    for col in runtime_cols:
        weighted_terms.append(col)
        weights.append(0.10 / max(len(runtime_cols), 1))

    def weighted_score(row: pd.Series) -> float:
        total = 0.0
        wsum = 0.0
        for col, w in zip(weighted_terms, weights):
            value = numeric_or_nan(row.get(col))
            if not math.isnan(value):
                total += w * value
                wsum += w
        return total / wsum if wsum > 0 else math.nan

    out["J_stability_weighted"] = out.apply(weighted_score, axis=1)
    return out


def add_rank_score(df: pd.DataFrame, metrics: list[MetricSpec], group_cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    norm_cols = [f"n_{spec.name}" for spec in metrics]
    if not norm_cols:
        out["J_rank"] = math.nan
        return out

    rank_parts = []
    if group_cols:
        grouped = out.groupby(group_cols, dropna=False)
        for col in norm_cols:
            rank_parts.append(grouped[col].rank(ascending=False, method="average", na_option="bottom"))
    else:
        for col in norm_cols:
            rank_parts.append(out[col].rank(ascending=False, method="average", na_option="bottom"))

    avg_rank = sum(rank_parts) / len(rank_parts)
    # Higher J_rank is better. Convert average rank to a 0..1-like score.
    if group_cols:
        group_size = out.groupby(group_cols, dropna=False)[norm_cols[0]].transform("count").clip(lower=1)
    else:
        group_size = pd.Series([len(out)] * len(out), index=out.index).clip(lower=1)
    out["RankScore"] = avg_rank
    out["J_rank"] = 1.0 - ((avg_rank - 1.0) / group_size.clip(lower=2))
    return out


def make_rankings(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    id_cols = [c for c in ["dataset", "split", "instance", "K", "method", "theta_id", "configuration"] if c in df.columns]
    score_cols = [c for c in ["J_perf", "J_equal", "J_stability_weighted", "J_rank"] if c in df.columns]
    out = df[id_cols + score_cols].copy()

    for score in score_cols:
        rank_col = f"{score}_rank"
        if group_cols:
            out[rank_col] = out.groupby(group_cols, dropna=False)[score].rank(
                ascending=False, method="dense", na_option="bottom"
            )
        else:
            out[rank_col] = out[score].rank(ascending=False, method="dense", na_option="bottom")
    return out


def sensitivity_score_row(
    row: pd.Series,
    perf_cols: list[str],
    stability_cols: list[str],
    diversity_cols: list[str],
    runtime_cols: list[str],
    alpha_stability: float,
    runtime_weight: float,
) -> float:
    runtime_weight = runtime_weight if runtime_cols else 0.0
    alpha_stability = max(0.0, min(1.0 - runtime_weight, alpha_stability))
    perf_weight = 1.0 - alpha_stability - runtime_weight
    stability_bucket = stability_cols + diversity_cols

    buckets = [
        (perf_cols, perf_weight),
        (stability_bucket, alpha_stability),
        (runtime_cols, runtime_weight),
    ]
    total = 0.0
    wsum = 0.0
    for cols, bucket_weight in buckets:
        vals = [numeric_or_nan(row.get(c)) for c in cols]
        vals = [v for v in vals if not math.isnan(v)]
        if vals and bucket_weight > 0:
            total += bucket_weight * (sum(vals) / len(vals))
            wsum += bucket_weight
    return total / wsum if wsum > 0 else math.nan


def make_sensitivity(
    scored: pd.DataFrame,
    metrics: list[MetricSpec],
    group_cols: list[str],
    alphas: list[float],
    runtime_weight: float,
) -> pd.DataFrame:
    norm = {spec.name: f"n_{spec.name}" for spec in metrics}
    perf_cols = [norm[m] for m in ["HV", "IGD"] if m in norm]
    stability_cols = [norm[m] for m in ["PF_Overlap", "EAF_Band_Width", "PF_Drift"] if m in norm]
    diversity_cols = [norm[m] for m in ["Diversity", "Archive_Diversity"] if m in norm]
    runtime_cols = [norm[m] for m in ["Runtime", "Configuration_Cost", "ConfigurationCost"] if m in norm]

    id_cols = [c for c in ["dataset", "split", "instance", "K", "method", "theta_id", "configuration"] if c in scored.columns]
    rows = []
    for alpha in alphas:
        tmp = scored.copy()
        tmp["J_alpha"] = tmp.apply(
            lambda r: sensitivity_score_row(
                r, perf_cols, stability_cols, diversity_cols, runtime_cols, alpha, runtime_weight
            ),
            axis=1,
        )
        if group_cols:
            tmp["alpha_rank"] = tmp.groupby(group_cols, dropna=False)["J_alpha"].rank(
                ascending=False, method="dense", na_option="bottom"
            )
        else:
            tmp["alpha_rank"] = tmp["J_alpha"].rank(ascending=False, method="dense", na_option="bottom")
        tmp["alpha_stability"] = alpha
        rows.append(tmp[id_cols + ["alpha_stability", "J_alpha", "alpha_rank"]])
    return pd.concat(rows, ignore_index=True)


def read_csv_input(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = normalize_columns(df)
    for col in df.columns:
        if col in BENEFIT_METRICS or col in COST_METRICS:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def read_experiment_b_docx(path: Path) -> pd.DataFrame:
    try:
        from docx import Document
    except ImportError as exc:
        raise SystemExit("python-docx is required to parse Experiment B DOCX.") from exc

    doc = Document(path)
    tables = []
    for table in doc.tables:
        rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
        if not rows:
            continue
        header = [canonical_col(c) for c in rows[0]]
        body = rows[1:]
        tables.append((header, body))

    by_method: dict[str, dict[str, object]] = {}
    for header, body in tables:
        if not header or header[0] != "Method":
            continue
        for row in body:
            if not row:
                continue
            method = row[0].strip()
            if not method:
                continue
            rec = by_method.setdefault(method, {"method": method})
            for col, value in zip(header[1:], row[1:]):
                if col == "Top_selected_configurations_/_usage":
                    rec["Top_selected_configurations"] = value
                else:
                    rec[col] = numeric_or_nan(value)

    if not by_method:
        raise SystemExit(f"No method-level metric tables found in {path}")

    df = pd.DataFrame(by_method.values())
    df["dataset"] = "Experiment_B"
    df["split"] = "unseen_test"
    df["instance"] = "aggregate_32_instances"
    return normalize_columns(df)


def parse_alphas(text: str) -> list[float]:
    values = []
    for part in re.split(r"[,; ]+", text.strip()):
        if not part:
            continue
        values.append(float(part))
    return values


def write_outputs(scored: pd.DataFrame, rankings: pd.DataFrame, sensitivity: pd.DataFrame, out_dir: Path, prefix: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    scored.to_csv(out_dir / f"{prefix}_scored.csv", index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    rankings.to_csv(out_dir / f"{prefix}_rankings.csv", index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    sensitivity.to_csv(out_dir / f"{prefix}_sensitivity.csv", index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute TEVC stability-aware J score and sensitivity tables.")
    parser.add_argument("--input", type=Path, help="Instance-level CSV input. If omitted, use --experiment-b-docx.")
    parser.add_argument("--experiment-b-docx", type=Path, help="Experiment B report DOCX fallback/sanity-check input.")
    parser.add_argument("--out-dir", type=Path, required=True, help="Output directory.")
    parser.add_argument("--prefix", default="tevc_j", help="Output file prefix.")
    parser.add_argument(
        "--group-cols",
        default="auto",
        help="Comma-separated normalization/ranking group columns. Use 'auto' or '' for global.",
    )
    parser.add_argument(
        "--alphas",
        default="0,0.25,0.5,0.75,0.9",
        help="Comma-separated stability-weight values for sensitivity analysis.",
    )
    parser.add_argument(
        "--runtime-weight",
        type=float,
        default=0.10,
        help="Total runtime/cost penalty weight used in sensitivity scores when runtime/cost columns exist.",
    )
    args = parser.parse_args()

    if args.input:
        df = read_csv_input(args.input)
    elif args.experiment_b_docx:
        df = read_experiment_b_docx(args.experiment_b_docx)
    else:
        raise SystemExit("Provide --input CSV or --experiment-b-docx DOCX.")

    metrics = discover_metrics(df)
    if not metrics:
        raise SystemExit("No supported metric columns found. Expected columns such as HV, IGD, PF_Overlap, EAF_Band_Width, Diversity, Runtime.")

    if args.group_cols == "auto":
        group_cols = default_group_columns(df)
    elif args.group_cols.strip() == "":
        group_cols = []
    else:
        group_cols = [c.strip() for c in args.group_cols.split(",") if c.strip()]
        missing = [c for c in group_cols if c not in df.columns]
        if missing:
            raise SystemExit(f"Group columns not found in input: {missing}")

    scored = add_normalized_metrics(df, metrics, group_cols)
    scored = add_scores(scored, metrics)
    scored = add_rank_score(scored, metrics, group_cols)
    rankings = make_rankings(scored, group_cols)
    sensitivity = make_sensitivity(scored, metrics, group_cols, parse_alphas(args.alphas), args.runtime_weight)

    write_outputs(scored, rankings, sensitivity, args.out_dir, args.prefix)

    print("Input rows:", len(df))
    print("Metrics:", ", ".join(f"{m.name}({m.direction})" for m in metrics))
    print("Group columns:", ", ".join(group_cols) if group_cols else "GLOBAL")
    print("Outputs:")
    print(" ", args.out_dir / f"{args.prefix}_scored.csv")
    print(" ", args.out_dir / f"{args.prefix}_rankings.csv")
    print(" ", args.out_dir / f"{args.prefix}_sensitivity.csv")


if __name__ == "__main__":
    main()
