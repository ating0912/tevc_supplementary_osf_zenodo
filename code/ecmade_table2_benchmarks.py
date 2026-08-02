"""Compute Table-2-style benchmark statistics for ECMADE.

This reproduces the ECMADE part of Song et al. (2023) Table 2:
13 benchmark functions, 30 dimensions, NP=60, MG=3000, 30 independent runs.

The paper compares ECMADE with IBDDE and DDE-SD, but it does not provide
complete definitions for those two algorithms. This script therefore computes
the ECMADE rows faithfully from the parameters described in the paper.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from ecmade_mcvar import ECMADEConfig


Objective = Callable[[np.ndarray], float]
VectorObjective = Callable[[np.ndarray], np.ndarray]


@dataclass(frozen=True)
class Benchmark:
    name: str
    objective: Objective
    vector_objective: VectorObjective
    lower: float
    upper: float
    f_min: float


def f1_ackley(x: np.ndarray) -> float:
    d = x.size
    return float(-20.0 * np.exp(-0.2 * np.sqrt(np.sum(x * x) / d)) - np.exp(np.sum(np.cos(2.0 * np.pi * x)) / d) + 20.0 + np.e)


def vf1_ackley(x: np.ndarray) -> np.ndarray:
    d = x.shape[1]
    return -20.0 * np.exp(-0.2 * np.sqrt(np.sum(x * x, axis=1) / d)) - np.exp(np.sum(np.cos(2.0 * np.pi * x), axis=1) / d) + 20.0 + np.e


def f2_rastrigin(x: np.ndarray) -> float:
    return float(np.sum(x * x - 10.0 * np.cos(2.0 * np.pi * x) + 10.0))


def vf2_rastrigin(x: np.ndarray) -> np.ndarray:
    return np.sum(x * x - 10.0 * np.cos(2.0 * np.pi * x) + 10.0, axis=1)


def f3_happy_cat(x: np.ndarray) -> float:
    d = x.size
    sum_sq = np.sum(x * x)
    exponent = 1.0 if os.environ.get("ECMADE_POWER_PRECEDENCE", "0") == "1" else 0.25
    scale = 0.25 if exponent == 1.0 else 1.0
    return float(scale * abs(sum_sq - d) ** exponent + (0.5 * sum_sq + np.sum(x)) / d + 0.5)


def vf3_happy_cat(x: np.ndarray) -> np.ndarray:
    d = x.shape[1]
    sum_sq = np.sum(x * x, axis=1)
    exponent = 1.0 if os.environ.get("ECMADE_POWER_PRECEDENCE", "0") == "1" else 0.25
    scale = 0.25 if exponent == 1.0 else 1.0
    return scale * np.abs(sum_sq - d) ** exponent + (0.5 * sum_sq + np.sum(x, axis=1)) / d + 0.5


def f4_griewank(x: np.ndarray) -> float:
    indices = np.arange(1, x.size + 1, dtype=float)
    return float(np.sum(x * x) / 4000.0 - np.prod(np.cos(x / np.sqrt(indices))) + 1.0)


def vf4_griewank(x: np.ndarray) -> np.ndarray:
    indices = np.arange(1, x.shape[1] + 1, dtype=float)
    return np.sum(x * x, axis=1) / 4000.0 - np.prod(np.cos(x / np.sqrt(indices)), axis=1) + 1.0


def f5_rosenbrock(x: np.ndarray) -> float:
    return float(np.sum(100.0 * (x[:-1] * x[:-1] - x[1:]) ** 2 + (x[:-1] - 1.0) ** 2))


def vf5_rosenbrock(x: np.ndarray) -> np.ndarray:
    return np.sum(100.0 * (x[:, :-1] * x[:, :-1] - x[:, 1:]) ** 2 + (x[:, :-1] - 1.0) ** 2, axis=1)


def f6_schwefel(x: np.ndarray) -> float:
    return float(np.sum(-x * np.sin(np.sqrt(np.abs(x)))))


def vf6_schwefel(x: np.ndarray) -> np.ndarray:
    return np.sum(-x * np.sin(np.sqrt(np.abs(x))), axis=1)


def f7_expanded_happy_cat_like(x: np.ndarray) -> float:
    d = x.size
    sum_sq = np.sum(x * x)
    exponent = 1.0 if os.environ.get("ECMADE_POWER_PRECEDENCE", "0") == "1" else 0.5
    scale = 0.5 if exponent == 1.0 else 1.0
    return float(scale * abs(sum_sq * sum_sq - np.sum(x) ** 2) ** exponent + (0.5 * sum_sq + np.sum(x)) / d + 0.5)


def vf7_expanded_happy_cat_like(x: np.ndarray) -> np.ndarray:
    d = x.shape[1]
    sum_sq = np.sum(x * x, axis=1)
    sum_x = np.sum(x, axis=1)
    exponent = 1.0 if os.environ.get("ECMADE_POWER_PRECEDENCE", "0") == "1" else 0.5
    scale = 0.5 if exponent == 1.0 else 1.0
    return scale * np.abs(sum_sq * sum_sq - sum_x * sum_x) ** exponent + (0.5 * sum_sq + sum_x) / d + 0.5


def f8_weierstrass(x: np.ndarray) -> float:
    a = 0.5
    b = 3.0
    k_max = 20
    k = np.arange(k_max + 1, dtype=float)
    ak = a**k
    bk = b**k
    first = np.sum([np.sum(ak * np.cos(2.0 * np.pi * bk * (xi + 0.5))) for xi in x])
    second = x.size * np.sum(ak * np.cos(2.0 * np.pi * bk * 0.5))
    return float(first - second)


def vf8_weierstrass(x: np.ndarray) -> np.ndarray:
    a = 0.5
    b = 3.0
    k_max = 20
    k = np.arange(k_max + 1, dtype=float)
    ak = a**k
    bk = b**k
    first = np.sum(np.sum(ak * np.cos(2.0 * np.pi * bk * (x[:, :, None] + 0.5)), axis=2), axis=1)
    second = x.shape[1] * np.sum(ak * np.cos(2.0 * np.pi * bk * 0.5))
    return first - second


def f9_sphere(x: np.ndarray) -> float:
    return float(np.sum(x * x))


def vf9_sphere(x: np.ndarray) -> np.ndarray:
    return np.sum(x * x, axis=1)


def f10_elliptic(x: np.ndarray) -> float:
    d = x.size
    coeffs = (1e6) ** (np.arange(d, dtype=float) / max(d - 1, 1))
    return float(np.sum(coeffs * x * x))


def vf10_elliptic(x: np.ndarray) -> np.ndarray:
    d = x.shape[1]
    coeffs = (1e6) ** (np.arange(d, dtype=float) / max(d - 1, 1))
    return np.sum(coeffs * x * x, axis=1)


def f11_quartic_noise(x: np.ndarray) -> float:
    indices = np.arange(1, x.size + 1, dtype=float)
    value = np.sum(indices * x**4)
    if os.environ.get("ECMADE_F11_NOISE", "0").lower() in {"1", "true", "yes"}:
        value += np.random.random()
    return float(value)


def vf11_quartic_noise(x: np.ndarray) -> np.ndarray:
    indices = np.arange(1, x.shape[1] + 1, dtype=float)
    values = np.sum(indices * x**4, axis=1)
    if os.environ.get("ECMADE_F11_NOISE", "0").lower() in {"1", "true", "yes"}:
        values = values + np.random.random(size=x.shape[0])
    return values


def f12_discus(x: np.ndarray) -> float:
    return float(x[0] * x[0] + 1e6 * np.sum(x[1:] * x[1:]))


def vf12_discus(x: np.ndarray) -> np.ndarray:
    return x[:, 0] * x[:, 0] + 1e6 * np.sum(x[:, 1:] * x[:, 1:], axis=1)


def f13_infinity_norm(x: np.ndarray) -> float:
    return float(np.max(np.abs(x)))


def vf13_infinity_norm(x: np.ndarray) -> np.ndarray:
    return np.max(np.abs(x), axis=1)


BENCHMARKS = [
    Benchmark("f1", f1_ackley, vf1_ackley, -32.0, 32.0, 0.0),
    Benchmark("f2", f2_rastrigin, vf2_rastrigin, -5.12, 5.12, 0.0),
    Benchmark("f3", f3_happy_cat, vf3_happy_cat, -100.0, 100.0, 0.0),
    Benchmark("f4", f4_griewank, vf4_griewank, -600.0, 600.0, 0.0),
    Benchmark("f5", f5_rosenbrock, vf5_rosenbrock, -10.0, 10.0, 0.0),
    Benchmark("f6", f6_schwefel, vf6_schwefel, -500.0, 500.0, -12569.5),
    Benchmark("f7", f7_expanded_happy_cat_like, vf7_expanded_happy_cat_like, -100.0, 100.0, 0.0),
    Benchmark("f8", f8_weierstrass, vf8_weierstrass, -100.0, 100.0, 0.0),
    Benchmark("f9", f9_sphere, vf9_sphere, -100.0, 100.0, 0.0),
    Benchmark("f10", f10_elliptic, vf10_elliptic, -100.0, 100.0, 0.0),
    Benchmark("f11", f11_quartic_noise, vf11_quartic_noise, -1.28, 1.28, 0.0),
    Benchmark("f12", f12_discus, vf12_discus, -10.0, 10.0, 0.0),
    Benchmark("f13", f13_infinity_norm, vf13_infinity_norm, -100.0, 100.0, 0.0),
]


def random_subpop_ids(rng: np.random.Generator, population_size: int) -> np.ndarray:
    ids = np.repeat(np.arange(3), population_size // 3)
    remainder = population_size - ids.size
    if remainder:
        ids = np.concatenate([ids, np.arange(remainder)])
    rng.shuffle(ids)
    return ids


def choose_indices(rng: np.random.Generator, excluded: int, count: int, population_size: int) -> np.ndarray:
    selected: list[int] = []
    while len(selected) < count:
        value = int(rng.integers(0, population_size))
        if value != excluded and value not in selected:
            selected.append(value)
    return np.array(selected, dtype=int)


def choose_indices_from_pool(rng: np.random.Generator, excluded: int, count: int, pool: np.ndarray) -> np.ndarray:
    candidates = pool[pool != excluded]
    if candidates.size >= count:
        return rng.choice(candidates, size=count, replace=False)
    return choose_indices(rng, excluded, count, int(np.max(pool)) + 1)


def sample_f(rng: np.random.Generator, mu_f: float) -> float:
    value = mu_f + 0.1 * rng.standard_cauchy()
    attempts = 0
    while value <= 0.0 and attempts < 100:
        value = mu_f + 0.1 * rng.standard_cauchy()
        attempts += 1
    return float(np.clip(value, 1e-12, 1.0))


def weighted_lehmer(archive: list[tuple[float, int]], generation: int) -> float:
    data = np.array([value for value, _ in archive], dtype=float)
    weights = np.array([np.exp((gen - generation) / max(generation, 1)) for _, gen in archive], dtype=float)
    weighted_data = weights * data
    denominator = np.sum(weighted_data)
    return float(np.sum(weighted_data * weighted_data) / denominator) if denominator > 0.0 else float(np.mean(data))


def weighted_mean(archive: list[tuple[float, int]], generation: int) -> float:
    data = np.array([value for value, _ in archive], dtype=float)
    weights = np.array([np.exp((gen - generation) / max(generation, 1)) for _, gen in archive], dtype=float)
    return float(np.sum(weights * data) / np.sum(weights))


def optimize_fast(benchmark: Benchmark, cfg: ECMADEConfig, seed: int) -> float:
    rng = np.random.default_rng(seed)
    np_size = cfg.population_size
    dim = 30
    pop = rng.uniform(cfg.lower_bound, cfg.upper_bound, size=(np_size, dim))
    fitness = benchmark.vector_objective(pop)
    subpop_ids = random_subpop_ids(rng, np_size)
    mu_f = np.array([cfg.initial_mu_f[i] for i in subpop_ids], dtype=float)
    mu_cr = np.array([cfg.initial_mu_cr[i] for i in subpop_ids], dtype=float)
    recent_f: list[list[tuple[float, int]]] = [[] for _ in range(np_size)]
    recent_cr: list[list[tuple[float, int]]] = [[] for _ in range(np_size)]
    best = float(np.min(fitness))
    stagnation = 0

    for generation in range(1, cfg.max_generations + 1):
        previous_best = best
        best_x = pop[int(np.argmin(fitness))]
        members_by_subpop = [np.where(subpop_ids == subpop_id)[0] for subpop_id in range(3)]
        mutants = np.empty_like(pop)
        f_values = np.empty(np_size)
        cr_values = np.empty(np_size)

        for i in range(np_size):
            f_i = sample_f(rng, mu_f[i])
            cr_i = float(np.clip(rng.normal(mu_cr[i], 0.1), 0.0, 1.0))
            f_values[i] = f_i
            cr_values[i] = cr_i
            pool = members_by_subpop[int(subpop_ids[i])]

            if subpop_ids[i] == 0:
                r1, r2, r3, r4, r5 = choose_indices_from_pool(rng, i, 5, pool)
                mutant = pop[r1] + f_i * (pop[r2] - pop[r3]) + f_i * (pop[r4] - pop[r5])
            elif subpop_ids[i] == 1:
                r1, r2, r3, r4 = choose_indices_from_pool(rng, i, 4, pool)
                mutant = cfg.exploitation_alpha * best_x + f_i * (pop[r1] - pop[r2]) + f_i * (pop[r3] - pop[r4])
            else:
                r1, r2, r3, r4, r5 = choose_indices_from_pool(rng, i, 5, pool)
                omega = generation / cfg.max_generations
                rand_1 = pop[r1] + f_i * (pop[r2] - pop[r3])
                current_to_best_1 = pop[i] + f_i * (best_x - pop[i]) + f_i * (pop[r4] - pop[r5])
                mutant = (1.0 - omega) * rand_1 + omega * current_to_best_1
            mutants[i] = np.clip(mutant, cfg.lower_bound, cfg.upper_bound)

        crossover_mask = rng.random((np_size, dim)) <= cr_values[:, None]
        forced_dims = rng.integers(0, dim, size=np_size)
        crossover_mask[np.arange(np_size), forced_dims] = True
        trials = np.where(crossover_mask, mutants, pop)
        trial_fitness = benchmark.vector_objective(trials)
        improved = trial_fitness <= fitness

        for i in np.where(improved)[0]:
            recent_f[i].append((float(f_values[i]), generation))
            recent_cr[i].append((float(cr_values[i]), generation))
            recent_f[i] = recent_f[i][-cfg.archive_size :]
            recent_cr[i] = recent_cr[i][-cfg.archive_size :]

        for i in range(np_size):
            if not recent_f[i]:
                continue
            mu_f[i] = (1.0 - cfg.theta) * mu_f[i] + cfg.theta * weighted_lehmer(recent_f[i], generation)
            mu_cr[i] = (1.0 - cfg.theta) * mu_cr[i] + cfg.theta * weighted_mean(recent_cr[i], generation)

        pop[improved] = trials[improved]
        fitness[improved] = trial_fitness[improved]
        best = float(np.min(fitness))
        stagnation = stagnation + 1 if best >= previous_best else 0

        if stagnation > cfg.stagnation_threshold:
            subpop_ids = random_subpop_ids(rng, np_size)
            elite_count = max(1, int(np.ceil(0.05 * np_size)))
            elite_indices = np.argsort(fitness)[:elite_count]
            for subpop_id in range(3):
                members = np.where(subpop_ids == subpop_id)[0]
                if members.size == 0:
                    continue
                worst_members = members[np.argsort(fitness[members])[-min(elite_count, members.size) :]]
                for dst, src in zip(worst_members, np.resize(elite_indices, worst_members.size)):
                    pop[dst] = pop[src].copy()
                    fitness[dst] = fitness[src]
            stagnation = 0

    return best


def run_one(task: tuple[int, int, int, int]) -> tuple[int, int, float]:
    benchmark_index, run, generations, seed = task
    benchmark = BENCHMARKS[benchmark_index]
    cfg = ECMADEConfig(
        max_generations=generations,
        seed=seed,
        lower_bound=benchmark.lower,
        upper_bound=benchmark.upper,
    )
    return benchmark_index, run, optimize_fast(benchmark, cfg, seed + run)


def summarize_benchmark(benchmark: Benchmark, values: list[float], runs: int, generations: int) -> dict:
    values_array = np.array(values, dtype=float)
    return {
        "function": benchmark.name,
        "algorithm": "ECMADE",
        "mean": float(np.mean(values_array)),
        "std": float(np.std(values_array, ddof=1)) if values_array.size > 1 else 0.0,
        "best": float(np.min(values_array)),
        "worst": float(np.max(values_array)),
        "runs": runs,
        "generations": generations,
    }


def run_benchmark(benchmark: Benchmark, runs: int, generations: int, seed: int) -> dict:
    cfg = ECMADEConfig(
        max_generations=generations,
        independent_runs=runs,
        seed=seed,
        lower_bound=benchmark.lower,
        upper_bound=benchmark.upper,
    )
    values = []
    for run in range(runs):
        values.append(optimize_fast(benchmark, cfg, seed + run))
    return summarize_benchmark(benchmark, values, runs, generations)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ECMADE on the 13 30-D Table 1 benchmark functions.")
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--generations", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=202305)
    parser.add_argument("--output", type=Path, default=Path("ecmade_table2_results.csv"))
    parser.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows_by_index: dict[int, dict] = {}
    if args.jobs <= 1:
        for index, benchmark in enumerate(BENCHMARKS):
            row = run_benchmark(benchmark, args.runs, args.generations, args.seed + index * 10000)
            rows_by_index[index] = row
            print(
                f"{row['function']} ECMADE mean={row['mean']:.6E} "
                f"std={row['std']:.6E} best={row['best']:.6E}",
                flush=True,
            )
    else:
        values_by_index = {index: [] for index in range(len(BENCHMARKS))}
        tasks = [
            (index, run, args.generations, args.seed + index * 10000)
            for index in range(len(BENCHMARKS))
            for run in range(args.runs)
        ]
        with ProcessPoolExecutor(max_workers=args.jobs) as executor:
            futures = [executor.submit(run_one, task) for task in tasks]
            completed_by_index = {index: 0 for index in range(len(BENCHMARKS))}
            for future in as_completed(futures):
                index, _run, value = future.result()
                values_by_index[index].append(value)
                completed_by_index[index] += 1
                if completed_by_index[index] == args.runs:
                    benchmark = BENCHMARKS[index]
                    row = summarize_benchmark(benchmark, values_by_index[index], args.runs, args.generations)
                    rows_by_index[index] = row
                    print(
                        f"{row['function']} ECMADE mean={row['mean']:.6E} "
                        f"std={row['std']:.6E} best={row['best']:.6E}",
                        flush=True,
                    )

    rows = [rows_by_index[index] for index in range(len(BENCHMARKS))]
    results = pd.DataFrame(rows)
    results.to_csv(args.output, index=False)
    print()
    print(results[["function", "algorithm", "mean", "std"]].to_string(index=False))
    print(f"Wrote: {args.output.resolve()}")


if __name__ == "__main__":
    main()
