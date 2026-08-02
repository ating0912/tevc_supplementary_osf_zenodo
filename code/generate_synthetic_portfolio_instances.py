# -*- coding: utf-8 -*-
"""Generate synthetic constrained portfolio instances for TEVC experiments.

The generated .txt files follow the OR-Library portfolio layout already used by
PortfolioORLIB.m:

    n
    mean_1 std_1
    ...
    mean_n std_n
    i j corr_ij
    ...

By default this script creates a P0-lite balanced design with all levels from
the experiment table represented:

- n: 50, 100, 200, 500
- K/n: 0.05, 0.10, 0.20, 0.30
- correlation: low, clustered, high, pathological
- return distribution: normal, skewed, heavy-tail, mixed
- risk structure: low volatility, high volatility, extreme events

Use --design full_factorial to create every combination. The P0-lite default
uses three replicates per n x K/n x correlation stratum, giving 192 instances.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np


ASSET_LEVELS = (50, 100, 200, 500)
K_RATIO_LEVELS = (0.05, 0.10, 0.20, 0.30)
CORR_LEVELS = ("low_corr", "cluster_corr", "high_corr", "pathological_cov")
RETURN_LEVELS = ("normal", "skewed", "heavy_tail", "mixed")
RISK_LEVELS = ("low_vol", "high_vol", "extreme_events")
SPLITS = ("train", "validation", "test")


@dataclass(frozen=True)
class InstanceSpec:
    name: str
    split: str
    assets: int
    days: int
    k_ratio: float
    k: int
    corr_structure: str
    return_distribution: str
    risk_structure: str
    replicate: int
    seed: int


def _nearest_correlation(cov: np.ndarray) -> np.ndarray:
    cov = 0.5 * (cov + cov.T)
    min_eig = float(np.min(np.linalg.eigvalsh(cov)))
    if min_eig < 1e-10:
        cov = cov + np.eye(cov.shape[0]) * (1e-10 - min_eig)
    std = np.sqrt(np.maximum(np.diag(cov), 1e-14))
    corr = cov / np.outer(std, std)
    corr = 0.5 * (corr + corr.T)
    np.fill_diagonal(corr, 1.0)
    return corr


def build_correlation(rng: np.random.Generator, n: int, structure: str) -> np.ndarray:
    if structure == "low_corr":
        loadings = rng.normal(0.0, 0.10, size=(n, 3))
        idio_var = rng.uniform(0.85, 1.10, size=n)
        cov = loadings @ loadings.T + np.diag(idio_var)

    elif structure == "cluster_corr":
        clusters = min(8, max(3, n // 50))
        loadings = np.zeros((n, clusters + 1))
        asset_clusters = np.arange(n) % clusters
        rng.shuffle(asset_clusters)
        loadings[:, 0] = rng.uniform(0.12, 0.25, size=n)
        for c in range(clusters):
            idx = asset_clusters == c
            loadings[idx, c + 1] = rng.uniform(0.45, 0.75, size=int(np.sum(idx)))
        idio_var = rng.uniform(0.40, 0.75, size=n)
        cov = loadings @ loadings.T + np.diag(idio_var)

    elif structure == "high_corr":
        loadings = np.zeros((n, 3))
        loadings[:, 0] = rng.uniform(0.80, 1.10, size=n)
        loadings[:, 1:] = rng.normal(0.0, 0.12, size=(n, 2))
        idio_var = rng.uniform(0.08, 0.22, size=n)
        cov = loadings @ loadings.T + np.diag(idio_var)

    elif structure == "pathological_cov":
        factors = 4
        loadings = rng.normal(0.0, 0.02, size=(n, factors))
        loadings[:, 0] = rng.uniform(0.90, 1.15, size=n)
        loadings[:, 1] = loadings[:, 0] + rng.normal(0.0, 0.01, size=n)
        loadings[:, 2:] += rng.normal(0.0, 0.05, size=(n, 2))
        idio_var = rng.uniform(0.003, 0.035, size=n)
        cov = loadings @ loadings.T + np.diag(idio_var)

    else:
        raise ValueError(f"Unknown correlation structure: {structure}")

    return _nearest_correlation(cov)


def annual_volatility(rng: np.random.Generator, n: int, risk_structure: str) -> np.ndarray:
    if risk_structure == "low_vol":
        return rng.uniform(0.08, 0.18, size=n)
    if risk_structure == "high_vol":
        return rng.uniform(0.22, 0.48, size=n)
    if risk_structure == "extreme_events":
        return rng.uniform(0.12, 0.35, size=n)
    raise ValueError(f"Unknown risk structure: {risk_structure}")


def base_daily_mean(rng: np.random.Generator, n: int, risk_structure: str) -> np.ndarray:
    if risk_structure == "low_vol":
        annual_mu = rng.uniform(0.02, 0.12, size=n)
    elif risk_structure == "high_vol":
        annual_mu = rng.uniform(0.04, 0.22, size=n)
    else:
        annual_mu = rng.uniform(-0.02, 0.20, size=n)
    return annual_mu / 252.0


def simulate_returns(spec: InstanceSpec) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(spec.seed)
    n = spec.assets
    corr = build_correlation(rng, n, spec.corr_structure)
    annual_std = annual_volatility(rng, n, spec.risk_structure)
    daily_std = annual_std / np.sqrt(252.0)
    daily_cov = corr * np.outer(daily_std, daily_std)
    daily_mu = base_daily_mean(rng, n, spec.risk_structure)

    z = rng.multivariate_normal(np.zeros(n), daily_cov, size=spec.days)

    if spec.return_distribution == "normal":
        returns = daily_mu + z

    elif spec.return_distribution == "skewed":
        skew_direction = rng.choice((-1.0, 1.0), size=n, p=(0.65, 0.35))
        skew_component = rng.exponential(scale=daily_std, size=(spec.days, n)) * skew_direction
        returns = daily_mu + 0.82 * z + 0.18 * (skew_component - skew_component.mean(axis=0))

    elif spec.return_distribution == "heavy_tail":
        df = 4.0
        scale = np.sqrt(rng.chisquare(df, size=(spec.days, 1)) / df)
        returns = daily_mu + z / np.maximum(scale, 1e-8)

    elif spec.return_distribution == "mixed":
        calm = rng.random(spec.days) < 0.82
        crisis_shift = rng.normal(-0.020, 0.008, size=(spec.days, 1))
        boom_shift = rng.normal(0.010, 0.006, size=(spec.days, 1))
        regime_shift = np.where(calm[:, None], 0.0, crisis_shift)
        boom_days = (~calm) & (rng.random(spec.days) < 0.25)
        regime_shift[boom_days, :] = boom_shift[boom_days, :]
        returns = daily_mu + z + regime_shift

    else:
        raise ValueError(f"Unknown return distribution: {spec.return_distribution}")

    if spec.risk_structure == "extreme_events":
        shock_count = max(2, spec.days // 45)
        shock_days = rng.choice(spec.days, size=shock_count, replace=False)
        market_shocks = rng.normal(-0.035, 0.015, size=(shock_count, 1))
        asset_load = rng.uniform(0.60, 1.25, size=(1, n))
        returns[shock_days, :] += market_shocks @ asset_load

    mean = np.mean(returns, axis=0)
    cov = np.cov(returns, rowvar=False)
    std = np.sqrt(np.maximum(np.diag(cov), 1e-14))
    corr_est = cov / np.outer(std, std)
    corr_est = 0.5 * (corr_est + corr_est.T)
    np.fill_diagonal(corr_est, 1.0)
    return mean, std, corr_est


def split_for_index(index_in_group: int, group_size: int) -> str:
    train_cut = max(1, int(round(group_size * 0.60)))
    val_cut = max(train_cut + 1, int(round(group_size * 0.80)))
    if index_in_group < train_cut:
        return "train"
    if index_in_group < val_cut:
        return "validation"
    return "test"


def ratio_to_k(n: int, k_ratio: float) -> int:
    return max(1, int(np.floor(n * k_ratio + 0.5)))


def build_specs(args: argparse.Namespace) -> list[InstanceSpec]:
    specs: list[InstanceSpec] = []
    seed_seq = np.random.SeedSequence(args.seed)

    if args.design == "full_factorial":
        grouped: dict[tuple[int, float], list[tuple[str, str, str, int]]] = {}
        for n in ASSET_LEVELS:
            for k_ratio in K_RATIO_LEVELS:
                group: list[tuple[str, str, str, int]] = []
                for corr in CORR_LEVELS:
                    for ret in RETURN_LEVELS:
                        for risk in RISK_LEVELS:
                            group.append((corr, ret, risk, 1))
                grouped[(n, k_ratio)] = group
    else:
        grouped = {}
        for n in ASSET_LEVELS:
            for k_ratio in K_RATIO_LEVELS:
                group = []
                for rep in range(1, args.replicates + 1):
                    for corr_idx, corr in enumerate(CORR_LEVELS):
                        ret = RETURN_LEVELS[(corr_idx + rep - 1) % len(RETURN_LEVELS)]
                        risk = RISK_LEVELS[(corr_idx + 2 * (rep - 1)) % len(RISK_LEVELS)]
                        group.append((corr, ret, risk, rep))
                grouped[(n, k_ratio)] = group

    seed_children = seed_seq.spawn(sum(len(v) for v in grouped.values()))
    seed_idx = 0
    for (n, k_ratio), group in grouped.items():
        shuffled = list(group)
        rng = np.random.default_rng(args.seed + n + int(k_ratio * 1000))
        rng.shuffle(shuffled)
        for idx, (corr, ret, risk, rep) in enumerate(shuffled):
            split = split_for_index(idx, len(shuffled))
            k = ratio_to_k(n, k_ratio)
            short_ratio = f"k{int(round(k_ratio * 100)):02d}"
            name = (
                f"syn_n{n}_{short_ratio}_{corr}_{ret}_{risk}"
                f"_r{rep:02d}_s{int(seed_children[seed_idx].entropy) + seed_idx:08d}"
            )
            specs.append(
                InstanceSpec(
                    name=name,
                    split=split,
                    assets=n,
                    days=args.days,
                    k_ratio=k_ratio,
                    k=k,
                    corr_structure=corr,
                    return_distribution=ret,
                    risk_structure=risk,
                    replicate=rep,
                    seed=int(seed_children[seed_idx].generate_state(1)[0]),
                )
            )
            seed_idx += 1
    return specs


def write_orlibrary_file(path: Path, mean: np.ndarray, std: np.ndarray, corr: np.ndarray) -> None:
    n = len(mean)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(f"{n}\n")
        for mu_i, std_i in zip(mean, std):
            f.write(f"{mu_i:.12g} {std_i:.12g}\n")
        for i in range(n):
            for j in range(i + 1, n):
                f.write(f"{i + 1} {j + 1} {corr[i, j]:.12g}\n")


def write_vector_csv(path: Path, values: np.ndarray, value_name: str) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["asset_index", value_name])
        for idx, value in enumerate(values, start=1):
            writer.writerow([idx, f"{value:.12g}"])


def write_matrix_csv(path: Path, matrix: np.ndarray) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([f"asset_{i:03d}" for i in range(1, matrix.shape[1] + 1)])
        writer.writerows([[f"{x:.12g}" for x in row] for row in matrix])


def generate_instance(args: argparse.Namespace, spec: InstanceSpec) -> dict[str, object]:
    split_dir = args.out_dir / "instances" / spec.split
    meta_dir = args.out_dir / "metadata" / spec.split
    split_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    mean, std, corr = simulate_returns(spec)
    txt_path = split_dir / f"{spec.name}.txt"
    write_orlibrary_file(txt_path, mean, std, corr)

    if args.write_csv:
        csv_dir = args.out_dir / "csv" / spec.split / spec.name
        csv_dir.mkdir(parents=True, exist_ok=True)
        write_vector_csv(csv_dir / "mean.csv", mean, "mean_return")
        write_vector_csv(csv_dir / "std.csv", std, "std_return")
        write_matrix_csv(csv_dir / "correlation.csv", corr)
        if args.write_covariance:
            write_matrix_csv(csv_dir / "covariance.csv", corr * np.outer(std, std))

    metadata = asdict(spec)
    metadata["path"] = str(txt_path)
    metadata["objectives"] = ["minimize_variance", "maximize_return"]
    metadata["constraints"] = ["sum(w)=1", "w>=0", "cardinality<=K"]
    metadata["format"] = "orlib_portfolio_txt"
    metadata["mean_scale"] = "daily_estimated_from_synthetic_returns"
    metadata["std_scale"] = "daily_estimated_from_synthetic_returns"
    (meta_dir / f"{spec.name}.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return {
        "instance": spec.name,
        "split": spec.split,
        "assets": spec.assets,
        "days": spec.days,
        "k_ratio": spec.k_ratio,
        "K": spec.k,
        "corr_structure": spec.corr_structure,
        "return_distribution": spec.return_distribution,
        "risk_structure": spec.risk_structure,
        "replicate": spec.replicate,
        "seed": spec.seed,
        "path": str(txt_path),
    }


def write_manifest(out_dir: Path, rows: list[dict[str, object]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = out_dir / "manifest.csv"
    fields = [
        "instance",
        "split",
        "assets",
        "days",
        "k_ratio",
        "K",
        "corr_structure",
        "return_distribution",
        "risk_structure",
        "replicate",
        "seed",
        "path",
    ]
    with manifest.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "total_instances": len(rows),
        "splits": {split: sum(1 for r in rows if r["split"] == split) for split in SPLITS},
        "asset_levels": list(ASSET_LEVELS),
        "k_ratio_levels": list(K_RATIO_LEVELS),
        "correlation_levels": list(CORR_LEVELS),
        "return_distribution_levels": list(RETURN_LEVELS),
        "risk_structure_levels": list(RISK_LEVELS),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic constrained portfolio instances.")
    parser.add_argument("--out-dir", type=Path, default=Path("data/synthetic_constrained_portfolio"))
    parser.add_argument("--design", choices=("p0_lite", "full_factorial"), default="p0_lite")
    parser.add_argument("--replicates", type=int, default=3, help="Only used by --design p0_lite.")
    parser.add_argument("--days", type=int, default=756)
    parser.add_argument("--seed", type=int, default=20260627)
    parser.add_argument("--write-csv", action="store_true", help="Also write mean/std/correlation CSV files.")
    parser.add_argument("--write-covariance", action="store_true", help="Also write covariance.csv when --write-csv is used.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.replicates < 1:
        raise ValueError("--replicates must be >= 1")
    specs = build_specs(args)
    rows = [generate_instance(args, spec) for spec in specs]
    write_manifest(args.out_dir, rows)
    print(f"Generated {len(rows)} synthetic constrained portfolio instances")
    print(args.out_dir / "manifest.csv")
    for split in SPLITS:
        print(f"{split}: {sum(1 for r in rows if r['split'] == split)}")


if __name__ == "__main__":
    main()
