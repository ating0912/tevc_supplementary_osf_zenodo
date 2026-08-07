"""Run Table-3-style ECMADE component experiments.

This script compares the three algorithms reported in Song et al. (2023)
Table 3:

- ECMADE: adaptive F/CR plus the three subpopulation mutation strategies.
- ECMADE-1: adaptive F/CR, but every subpopulation uses DE/rand/1/bin.
- ECMADE-2: three subpopulation mutation strategies, but fixed F=CR=0.5.

The benchmark functions are imported from ``ecmade_table2_benchmarks.py``.
Run a quick smoke test first, then increase to the paper setting:

    python ecmade_table3_components.py --runs 3 --generations 300
    python ecmade_table3_components.py --runs 30 --generations 3000
"""

from __future__ import annotations

import argparse
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ecmade_mcvar import ECMADEConfig
from ecmade_table2_benchmarks import (
    BENCHMARKS,
    Benchmark,
    choose_indices_from_pool,
    random_subpop_ids,
    sample_f,
    weighted_lehmer,
    weighted_mean,
)


REPORTED_TABLE3 = {
    ("f1", "ECMADE"): (4.44e-16, 0.00e00),
    ("f1", "ECMADE-1"): (2.57e-03, 5.84e-03),
    ("f1", "ECMADE-2"): (6.13e-15, 1.83e-15),
    ("f2", "ECMADE"): (0.00e00, 0.00e00),
    ("f2", "ECMADE-1"): (6.79e-03, 2.15e-02),
    ("f2", "ECMADE-2"): (2.98e-01, 9.44e-01),
    ("f3", "ECMADE"): (6.49e-37, 1.76e-36),
    ("f3", "ECMADE-1"): (4.17e-01, 1.12e-01),
    ("f3", "ECMADE-2"): (6.26e-20, 6.84e-20),
    ("f4", "ECMADE"): (0.00e00, 0.00e00),
    ("f4", "ECMADE-1"): (2.21e-05, 6.80e-05),
    ("f4", "ECMADE-2"): (0.00e00, 0.00e00),
    ("f5", "ECMADE"): (2.01e01, 1.21e00),
    ("f5", "ECMADE-1"): (2.46e01, 2.14e00),
    ("f5", "ECMADE-2"): (2.67e01, 1.80e00),
    ("f6", "ECMADE"): (-1.20e04, 5.97e02),
    ("f6", "ECMADE-1"): (-7.76e03, 2.90e03),
    ("f6", "ECMADE-2"): (-5.45e03, 2.64e02),
    ("f7", "ECMADE"): (3.91e-01, 6.00e-02),
    ("f7", "ECMADE-1"): (2.39e00, 2.46e-01),
    ("f7", "ECMADE-2"): (4.15e-01, 3.52e-01),
    ("f8", "ECMADE"): (0.00e00, 0.00e00),
    ("f8", "ECMADE-1"): (1.65e00, 3.55e00),
    ("f8", "ECMADE-2"): (8.97e-02, 1.19e-01),
    ("f9", "ECMADE"): (0.00e00, 0.00e00),
    ("f9", "ECMADE-1"): (5.53e-05, 1.75e-04),
    ("f9", "ECMADE-2"): (0.00e00, 0.00e00),
    ("f10", "ECMADE"): (0.00e00, 0.00e00),
    ("f10", "ECMADE-1"): (0.00e00, 0.00e00),
    ("f10", "ECMADE-2"): (9.97e06, 1.05e07),
    ("f11", "ECMADE"): (5.30e-05, 3.31e-05),
    ("f11", "ECMADE-1"): (4.12e-03, 1.53e-03),
    ("f11", "ECMADE-2"): (4.05e-05, 2.26e-05),
    ("f12", "ECMADE"): (0.00e00, 0.00e00),
    ("f12", "ECMADE-1"): (1.17e02, 3.54e02),
    ("f12", "ECMADE-2"): (7.24e-34, 1.32e-33),
    ("f13", "ECMADE"): (1.70e-20, 0.00e00),
    ("f13", "ECMADE-1"): (1.46e-03, 1.22e-01),
    ("f13", "ECMADE-2"): (1.34e-03, 3.59e-04),
}


@dataclass(frozen=True)
class Variant:
    name: str
    adaptive_parameters: bool
    multi_operator: bool
    fixed_f: float = 0.5
    fixed_cr: float = 0.5


VARIANTS = {
    "ECMADE": Variant("ECMADE", adaptive_parameters=True, multi_operator=True),
    "ECMADE-1": Variant("ECMADE-1", adaptive_parameters=True, multi_operator=False),
    "ECMADE-2": Variant("ECMADE-2", adaptive_parameters=False, multi_operator=True, fixed_f=0.5, fixed_cr=0.8),
}


def repair_bounds(
    x: np.ndarray,
    lower: float,
    upper: float,
    rng: np.random.Generator,
    mode: str,
    target: np.ndarray | None = None,
) -> np.ndarray:
    if mode == "clip":
        return np.clip(x, lower, upper)

    repaired = np.asarray(x, dtype=float).copy()
    mask = (repaired < lower) | (repaired > upper)
    if not np.any(mask):
        return repaired

    if mode == "random":
        repaired[mask] = rng.uniform(lower, upper, size=int(np.sum(mask)))
        return repaired

    if mode == "reflect":
        width = upper - lower
        if width <= 0.0:
            return np.full_like(repaired, lower)
        shifted = np.mod(repaired - lower, 2.0 * width)
        reflected = np.where(shifted <= width, lower + shifted, upper - (shifted - width))
        return np.clip(reflected, lower, upper)

    if mode == "midpoint":
        if target is None:
            raise ValueError("midpoint boundary repair requires the target vector")
        repaired[repaired < lower] = (lower + target[repaired < lower]) / 2.0
        repaired[repaired > upper] = (upper + target[repaired > upper]) / 2.0
        return repaired

    raise ValueError(f"Unknown boundary repair mode: {mode}")


def sample_f_configured(
    rng: np.random.Generator,
    mu_f: float,
    f_max: float,
    repair: str,
) -> float:
    if f_max <= 0.0:
        raise ValueError("f_max must be positive")

    value = mu_f + 0.1 * rng.standard_cauchy()
    attempts = 0
    if repair == "clip":
        while value <= 0.0 and attempts < 1000:
            value = mu_f + 0.1 * rng.standard_cauchy()
            attempts += 1
        return float(np.clip(value, 1e-12, f_max))

    if repair == "resample":
        while (value <= 0.0 or value > f_max) and attempts < 1000:
            value = mu_f + 0.1 * rng.standard_cauchy()
            attempts += 1
        return float(np.clip(value, 1e-12, f_max))

    raise ValueError(f"Unknown F repair mode: {repair}")


def sample_cr_configured(
    rng: np.random.Generator,
    mu_cr: float,
    repair: str,
) -> float:
    value = rng.normal(mu_cr, 0.1)
    if repair == "clip":
        return float(np.clip(value, 0.0, 1.0))
    if repair == "resample":
        attempts = 0
        while (value < 0.0 or value > 1.0) and attempts < 1000:
            value = rng.normal(mu_cr, 0.1)
            attempts += 1
        return float(np.clip(value, 0.0, 1.0))
    raise ValueError(f"Unknown CR repair mode: {repair}")


def archive_weights(
    entries: list[tuple[float, int, float]],
    current_generation: int,
    mode: str,
) -> np.ndarray:
    if mode == "time":
        return np.array(
            [np.exp((entry_generation - current_generation) / max(current_generation, 1)) for _, entry_generation, _ in entries],
            dtype=float,
        )
    if mode == "improvement":
        improvements = np.array([improvement for _, _, improvement in entries], dtype=float)
        return np.maximum(improvements, np.finfo(float).eps)
    if mode == "equal":
        return np.ones(len(entries), dtype=float)
    raise ValueError(f"Unknown archive weighting mode: {mode}")


def archive_lehmer_mean(
    entries: list[tuple[float, int, float]],
    current_generation: int,
    mode: str,
) -> float:
    data = np.array([value for value, _, _ in entries], dtype=float)
    if mode == "paper_literal":
        products = archive_weights(entries, current_generation, "time") * data
        denominator = np.sum(products)
        return float(np.sum(products * products) / denominator) if denominator > 0.0 else float(np.mean(products))
    weights = archive_weights(entries, current_generation, mode)
    denominator = np.sum(weights * data)
    return float(np.sum(weights * data * data) / denominator) if denominator > 0.0 else float(np.mean(data))


def archive_arithmetic_mean(
    entries: list[tuple[float, int, float]],
    current_generation: int,
    mode: str,
) -> float:
    data = np.array([value for value, _, _ in entries], dtype=float)
    if mode == "paper_literal":
        products = archive_weights(entries, current_generation, "time") * data
        return float(np.mean(products))
    weights = archive_weights(entries, current_generation, mode)
    return float(np.sum(weights * data) / np.sum(weights))


def mutate_rand_1(
    rng: np.random.Generator,
    i: int,
    pop: np.ndarray,
    pool: np.ndarray,
    f_i: float,
) -> np.ndarray:
    r1, r2, r3 = choose_indices_from_pool(rng, i, 3, pool)
    return pop[r1] + f_i * (pop[r2] - pop[r3])


def mutate_multi_operator(
    rng: np.random.Generator,
    i: int,
    pop: np.ndarray,
    fitness: np.ndarray,
    pool: np.ndarray,
    subpop_id: int,
    f_i: float,
    generation: int,
    cfg: ECMADEConfig,
    omega_scale: float,
    best_scope: str,
) -> np.ndarray:
    if best_scope == "global":
        best_x = pop[int(np.argmin(fitness))]
    elif best_scope == "subpop":
        best_x = pop[int(pool[int(np.argmin(fitness[pool]))])]
    else:
        raise ValueError(f"Unknown best scope: {best_scope}")
    if subpop_id == 0:
        r1, r2, r3, r4, r5 = choose_indices_from_pool(rng, i, 5, pool)
        return pop[r1] + f_i * (pop[r2] - pop[r3]) + f_i * (pop[r4] - pop[r5])
    if subpop_id == 1:
        r1, r2, r3, r4 = choose_indices_from_pool(rng, i, 4, pool)
        return cfg.exploitation_alpha * best_x + f_i * (pop[r1] - pop[r2]) + f_i * (pop[r3] - pop[r4])

    r1, r2, r3, r4, r5 = choose_indices_from_pool(rng, i, 5, pool)
    omega = min(1.0, omega_scale * generation / max(cfg.max_generations, 1))
    rand_1 = pop[r1] + f_i * (pop[r2] - pop[r3])
    current_to_best_1 = pop[i] + f_i * (best_x - pop[i]) + f_i * (pop[r4] - pop[r5])
    return (1.0 - omega) * rand_1 + omega * current_to_best_1


def optimize_variant(
    benchmark: Benchmark,
    variant: Variant,
    cfg: ECMADEConfig,
    seed: int,
    boundary: str = "clip",
    sampling: str = "subpop",
    archive: str = "individual",
    stagnation_mode: str = "global",
    omega_scale: float = 1.0,
    parameter_mean: str = "individual",
    f_max: float = 1.0,
    f_repair: str = "clip",
    archive_weighting: str = "time",
    update_mode: str = "synchronous",
    f11_report_clean: bool = False,
    exchange_mode: str = "clone",
    elite_fraction: float = 0.05,
    elite_state: str = "position",
    cr_repair: str = "clip",
    best_scope: str = "global",
    parameter_update_mode: str = "archive",
    redivision_parameter: str = "keep",
    reevaluate_parents: bool = False,
) -> float:
    rng = np.random.default_rng(seed)
    if benchmark.name == "f11" and os.environ.get("ECMADE_F11_NOISE", "0") == "1":
        np.random.seed(seed)
    np_size = cfg.population_size
    dim = 30
    pop = rng.uniform(cfg.lower_bound, cfg.upper_bound, size=(np_size, dim))
    fitness = benchmark.vector_objective(pop)
    subpop_ids = random_subpop_ids(rng, np_size)
    mu_f = np.array([cfg.initial_mu_f[i] for i in subpop_ids], dtype=float)
    mu_cr = np.array([cfg.initial_mu_cr[i] for i in subpop_ids], dtype=float)

    archive_count = np_size if archive == "individual" else 3 if archive == "subpop" else 1
    recent_f: list[list[tuple[float, int, float]]] = [[] for _ in range(archive_count)]
    recent_cr: list[list[tuple[float, int, float]]] = [[] for _ in range(archive_count)]
    best = float(np.min(fitness))
    stagnation = 0
    subpop_stagnation = np.zeros(3, dtype=int)

    def archive_index(i: int) -> int:
        if archive == "individual":
            return i
        if archive == "subpop":
            return int(subpop_ids[i])
        return 0

    def perform_exchange(strong: bool = False) -> None:
        nonlocal subpop_ids, fitness, pop
        subpop_ids = random_subpop_ids(rng, np_size)
        if exchange_mode == "redistribute" and not strong:
            return

        fraction = 0.10 if strong else elite_fraction
        elite_count = max(1, int(np.ceil(fraction * np_size)))
        elite_indices = np.argsort(fitness)[:elite_count]
        for subpop_id in range(3):
            members = np.where(subpop_ids == subpop_id)[0]
            if members.size == 0:
                continue
            worst_members = members[np.argsort(fitness[members])[-min(elite_count, members.size) :]]
            if exchange_mode == "random" and not strong:
                pop[worst_members] = rng.uniform(cfg.lower_bound, cfg.upper_bound, size=(worst_members.size, dim))
                fitness[worst_members] = benchmark.vector_objective(pop[worst_members])
            elif exchange_mode == "clone" or strong:
                for dst, src in zip(worst_members, np.resize(elite_indices, worst_members.size)):
                    pop[dst] = pop[src].copy()
                    fitness[dst] = fitness[src]
                    if elite_state == "full":
                        mu_f[dst] = mu_f[src]
                        mu_cr[dst] = mu_cr[src]
                        if archive == "individual":
                            recent_f[dst] = list(recent_f[src])
                            recent_cr[dst] = list(recent_cr[src])
                    elif elite_state != "position":
                        raise ValueError(f"Unknown elite state mode: {elite_state}")
            else:
                raise ValueError(f"Unknown exchange mode: {exchange_mode}")

        if strong:
            reset_count = max(1, int(np.ceil(0.10 * np_size)))
            reset_indices = np.argsort(fitness)[-reset_count:]
            pop[reset_indices] = rng.uniform(cfg.lower_bound, cfg.upper_bound, size=(reset_count, dim))
            fitness[reset_indices] = benchmark.vector_objective(pop[reset_indices])

        if redivision_parameter in {"role-reset", "role-reset-clear"}:
            for i in range(np_size):
                role = int(subpop_ids[i])
                mu_f[i] = cfg.initial_mu_f[role]
                mu_cr[i] = cfg.initial_mu_cr[role]
            if redivision_parameter == "role-reset-clear":
                for archive_values in recent_f:
                    archive_values.clear()
                for archive_values in recent_cr:
                    archive_values.clear()
        elif redivision_parameter != "keep":
            raise ValueError(f"Unknown redivision parameter mode: {redivision_parameter}")

    for generation in range(1, cfg.max_generations + 1):
        previous_best = best
        if reevaluate_parents and benchmark.name == "f11" and os.environ.get("ECMADE_F11_NOISE", "0") == "1":
            fitness = benchmark.vector_objective(pop)
            best = float(np.min(fitness))
        members_by_subpop = [np.where(subpop_ids == subpop_id)[0] for subpop_id in range(3)]
        previous_subpop_best = np.array(
            [float(np.min(fitness[m])) if m.size else np.inf for m in members_by_subpop],
            dtype=float,
        )
        global_pool = np.arange(np_size)
        f_values = np.empty(np_size)
        cr_values = np.empty(np_size)
        trials = pop.copy()
        trial_fitness = fitness.copy()
        improved = np.zeros(np_size, dtype=bool)
        improvements = np.zeros(np_size, dtype=float)

        if update_mode == "synchronous":
            mutants = np.empty_like(pop)
            for i in range(np_size):
                if variant.adaptive_parameters:
                    f_i = sample_f_configured(rng, mu_f[i], f_max, f_repair)
                    cr_i = sample_cr_configured(rng, mu_cr[i], cr_repair)
                else:
                    f_i = variant.fixed_f
                    cr_i = variant.fixed_cr
                f_values[i] = f_i
                cr_values[i] = cr_i

                pool = global_pool if sampling == "global" else members_by_subpop[int(subpop_ids[i])]
                if variant.multi_operator:
                    mutant = mutate_multi_operator(rng, i, pop, fitness, pool, int(subpop_ids[i]), f_i, generation, cfg, omega_scale, best_scope)
                else:
                    mutant = mutate_rand_1(rng, i, pop, pool, f_i)
                mutants[i] = repair_bounds(mutant, cfg.lower_bound, cfg.upper_bound, rng, boundary, pop[i])

            crossover_mask = rng.random((np_size, dim)) <= cr_values[:, None]
            forced_dims = rng.integers(0, dim, size=np_size)
            crossover_mask[np.arange(np_size), forced_dims] = True
            trials = np.where(crossover_mask, mutants, pop)
            trial_fitness = benchmark.vector_objective(trials)
            improved = trial_fitness <= fitness
            improvements = np.maximum(fitness - trial_fitness, 0.0)
        elif update_mode == "asynchronous":
            for i in rng.permutation(np_size):
                if variant.adaptive_parameters:
                    f_i = sample_f_configured(rng, mu_f[i], f_max, f_repair)
                    cr_i = sample_cr_configured(rng, mu_cr[i], cr_repair)
                else:
                    f_i = variant.fixed_f
                    cr_i = variant.fixed_cr
                f_values[i] = f_i
                cr_values[i] = cr_i

                pool = global_pool if sampling == "global" else members_by_subpop[int(subpop_ids[i])]
                if variant.multi_operator:
                    mutant = mutate_multi_operator(rng, i, pop, fitness, pool, int(subpop_ids[i]), f_i, generation, cfg, omega_scale, best_scope)
                else:
                    mutant = mutate_rand_1(rng, i, pop, pool, f_i)
                mutant = repair_bounds(mutant, cfg.lower_bound, cfg.upper_bound, rng, boundary, pop[i])
                mask = rng.random(dim) <= cr_i
                mask[int(rng.integers(0, dim))] = True
                trial = np.where(mask, mutant, pop[i])
                value = float(benchmark.objective(trial))
                trials[i] = trial
                trial_fitness[i] = value
                if value <= fitness[i]:
                    improvements[i] = max(float(fitness[i] - value), 0.0)
                    improved[i] = True
                    pop[i] = trial
                    fitness[i] = value
        else:
            raise ValueError(f"Unknown update mode: {update_mode}")

        if variant.adaptive_parameters:
            for i in np.where(improved)[0]:
                ai = archive_index(int(i))
                improvement = float(improvements[i])
                recent_f[ai].append((float(f_values[i]), generation, improvement))
                recent_cr[ai].append((float(cr_values[i]), generation, improvement))
                recent_f[ai] = recent_f[ai][-cfg.archive_size :]
                recent_cr[ai] = recent_cr[ai][-cfg.archive_size :]

            if parameter_mean == "individual":
                for i in range(np_size):
                    if parameter_update_mode == "success-only" and not improved[i]:
                        continue
                    ai = archive_index(i)
                    if not recent_f[ai]:
                        continue
                    mu_f[i] = (1.0 - cfg.theta) * mu_f[i] + cfg.theta * archive_lehmer_mean(recent_f[ai], generation, archive_weighting)
                    mu_cr[i] = (1.0 - cfg.theta) * mu_cr[i] + cfg.theta * archive_arithmetic_mean(recent_cr[ai], generation, archive_weighting)
            elif parameter_mean == "subpop":
                for subpop_id in range(3):
                    members = np.where(subpop_ids == subpop_id)[0]
                    if members.size == 0:
                        continue
                    if parameter_update_mode == "success-only" and not np.any(improved[members]):
                        continue
                    ai = subpop_id if archive == "subpop" else 0 if archive == "global" else int(members[0])
                    if not recent_f[ai]:
                        continue
                    next_mu_f = (1.0 - cfg.theta) * float(np.mean(mu_f[members])) + cfg.theta * archive_lehmer_mean(recent_f[ai], generation, archive_weighting)
                    next_mu_cr = (1.0 - cfg.theta) * float(np.mean(mu_cr[members])) + cfg.theta * archive_arithmetic_mean(recent_cr[ai], generation, archive_weighting)
                    mu_f[members] = next_mu_f
                    mu_cr[members] = next_mu_cr
            else:
                raise ValueError(f"Unknown parameter mean mode: {parameter_mean}")

            if parameter_update_mode not in {"archive", "success-only"}:
                raise ValueError(f"Unknown parameter update mode: {parameter_update_mode}")

        if update_mode == "synchronous":
            pop[improved] = trials[improved]
            fitness[improved] = trial_fitness[improved]
        best = float(np.min(fitness))
        stagnation = stagnation + 1 if best >= previous_best else 0

        members_by_subpop = [np.where(subpop_ids == subpop_id)[0] for subpop_id in range(3)]
        current_subpop_best = np.array(
            [float(np.min(fitness[m])) if m.size else np.inf for m in members_by_subpop],
            dtype=float,
        )
        subpop_stagnation = np.where(current_subpop_best >= previous_subpop_best, subpop_stagnation + 1, 0)

        should_exchange = False
        strong_exchange = False
        if stagnation_mode == "global":
            should_exchange = stagnation > cfg.stagnation_threshold
        elif stagnation_mode == "subpop":
            should_exchange = bool(np.any(subpop_stagnation > cfg.stagnation_threshold))
        elif stagnation_mode == "strong":
            should_exchange = stagnation > cfg.stagnation_threshold
            strong_exchange = should_exchange
        else:
            raise ValueError(f"Unknown stagnation mode: {stagnation_mode}")

        if should_exchange:
            perform_exchange(strong=strong_exchange)
            stagnation = 0
            subpop_stagnation[:] = 0

    if benchmark.name == "f11" and f11_report_clean:
        best_x = pop[int(np.argmin(fitness))]
        indices = np.arange(1, dim + 1, dtype=float)
        return float(np.sum(indices * best_x**4))
    return best

def run_one(task: tuple) -> tuple[int, str, int, float]:
    benchmark_index, variant_name, run, seed, boundary, sampling, archive, stagnation_mode, exploitation_alpha, omega_scale, parameter_mean, f_max, f_repair, archive_weighting, update_mode, f11_report_clean, exchange_mode, elite_fraction, elite_state, cr_repair, best_scope, parameter_update_mode, redivision_parameter, reevaluate_parents, archive_size, theta, stagnation_threshold, initial_mu_f, initial_mu_cr, generations = task
    benchmark = BENCHMARKS[benchmark_index]
    cfg = ECMADEConfig(
        max_generations=generations,
        seed=seed,
        lower_bound=benchmark.lower,
        upper_bound=benchmark.upper,
        exploitation_alpha=exploitation_alpha,
        archive_size=archive_size,
        theta=theta,
        stagnation_threshold=stagnation_threshold,
        initial_mu_f=tuple(initial_mu_f),
        initial_mu_cr=tuple(initial_mu_cr),
    )
    value = optimize_variant(
        benchmark,
        VARIANTS[variant_name],
        cfg,
        seed + run,
        boundary,
        sampling,
        archive,
        stagnation_mode,
        omega_scale,
        parameter_mean,
        f_max,
        f_repair,
        archive_weighting,
        update_mode,
        f11_report_clean,
        exchange_mode,
        elite_fraction,
        elite_state,
        cr_repair,
        best_scope,
        parameter_update_mode,
        redivision_parameter,
        reevaluate_parents,
    )
    return benchmark_index, variant_name, run, value

def summarize_values(
    benchmark: Benchmark,
    variant_name: str,
    values: list[float],
    runs: int,
    generations: int,
) -> dict:
    values_array = np.array(values, dtype=float)
    reported_mean, reported_std = REPORTED_TABLE3[(benchmark.name, variant_name)]
    mean = float(np.mean(values_array))
    std = float(np.std(values_array, ddof=1)) if values_array.size > 1 else 0.0
    return {
        "function": benchmark.name,
        "algorithm": variant_name,
        "mean": mean,
        "std": std,
        "reported_mean": reported_mean,
        "reported_std": reported_std,
        "abs_mean_diff": abs(mean - reported_mean),
        "best": float(np.min(values_array)),
        "worst": float(np.max(values_array)),
        "runs": runs,
        "generations": generations,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Table 3 ECMADE component comparison.")
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--generations", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=202305)
    parser.add_argument("--output", type=Path, default=Path("ecmade_table3_component_results.csv"))
    parser.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument("--functions", nargs="*", default=[b.name for b in BENCHMARKS])
    parser.add_argument("--algorithms", nargs="*", default=list(VARIANTS))
    parser.add_argument("--boundary", choices=["clip", "random", "reflect", "midpoint"], default="clip")
    parser.add_argument("--sampling", choices=["subpop", "global"], default="subpop")
    parser.add_argument("--archive", choices=["individual", "subpop", "global"], default="individual")
    parser.add_argument("--stagnation", choices=["global", "subpop", "strong"], default="global")
    parser.add_argument("--f11-noise", action="store_true", help="Use the random[0,1] term in Table 1 f11.")
    parser.add_argument("--f11-report-clean", action="store_true", help="Report f11 without the random term after noisy optimization.")
    parser.add_argument("--exploitation-alpha", type=float, default=0.8)
    parser.add_argument("--omega-scale", type=float, default=1.0)
    parser.add_argument("--parameter-mean", choices=["individual", "subpop"], default="individual")
    parser.add_argument("--f-max", type=float, default=1.0)
    parser.add_argument("--f-repair", choices=["clip", "resample"], default="clip")
    parser.add_argument("--archive-weighting", choices=["time", "paper_literal", "improvement", "equal"], default="time")
    parser.add_argument("--update-mode", choices=["synchronous", "asynchronous"], default="synchronous")
    parser.add_argument("--exchange-mode", choices=["clone", "redistribute", "random"], default="clone")
    parser.add_argument("--elite-fraction", type=float, default=0.05)
    parser.add_argument("--elite-state", choices=["position", "full"], default="position")
    parser.add_argument("--cr-repair", choices=["clip", "resample"], default="clip")
    parser.add_argument("--best-scope", choices=["global", "subpop"], default="global")
    parser.add_argument("--parameter-update", choices=["archive", "success-only"], default="archive")
    parser.add_argument("--redivision-parameter", choices=["keep", "role-reset", "role-reset-clear"], default="keep")
    parser.add_argument("--reevaluate-parents", action="store_true", help="Reevaluate noisy f11 parents once per generation.")
    parser.add_argument("--diagnostic-power-precedence", action="store_true", help="Test **1/4 and **1/2 Python precedence for f3/f7; this does not match Table 1.")
    parser.add_argument("--archive-size", type=int, default=20)
    parser.add_argument("--theta", type=float, default=1.0 / 13.0)
    parser.add_argument("--stagnation-threshold", type=int, default=50)
    parser.add_argument("--initial-mu-f", type=float, nargs=3, default=(0.9, 0.8, 0.8), metavar=("P1", "P2", "P3"))
    parser.add_argument("--initial-mu-cr", type=float, nargs=3, default=(0.9, 0.5, 0.5), metavar=("P1", "P2", "P3"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.environ["ECMADE_F11_NOISE"] = "1" if args.f11_noise else "0"
    os.environ["ECMADE_POWER_PRECEDENCE"] = "1" if args.diagnostic_power_precedence else "0"
    selected_indices = [index for index, b in enumerate(BENCHMARKS) if b.name in set(args.functions)]
    selected_variants = [name for name in VARIANTS if name in set(args.algorithms)]
    rows_by_key: dict[tuple[int, str], dict] = {}
    if args.jobs <= 1:
        for index in selected_indices:
            benchmark = BENCHMARKS[index]
            for variant_name in selected_variants:
                values = []
                base_seed = args.seed + index * 10000 + list(VARIANTS).index(variant_name) * 1000000
                for run in range(args.runs):
                    cfg = ECMADEConfig(
                        max_generations=args.generations,
                        independent_runs=args.runs,
                        seed=base_seed,
                        lower_bound=benchmark.lower,
                        upper_bound=benchmark.upper,
                        exploitation_alpha=args.exploitation_alpha,
                        archive_size=args.archive_size,
                        theta=args.theta,
                        stagnation_threshold=args.stagnation_threshold,
                        initial_mu_f=tuple(args.initial_mu_f),
                        initial_mu_cr=tuple(args.initial_mu_cr),
                    )
                    values.append(optimize_variant(benchmark, VARIANTS[variant_name], cfg, base_seed + run, args.boundary, args.sampling, args.archive, args.stagnation, args.omega_scale, args.parameter_mean, args.f_max, args.f_repair, args.archive_weighting, args.update_mode, args.f11_report_clean, args.exchange_mode, args.elite_fraction, args.elite_state, args.cr_repair, args.best_scope, args.parameter_update, args.redivision_parameter, args.reevaluate_parents))
                row = summarize_values(benchmark, variant_name, values, args.runs, args.generations)
                rows_by_key[(index, variant_name)] = row
                print(
                    f"{benchmark.name} {variant_name} mean={row['mean']:.6E} "
                    f"std={row['std']:.6E} reported={row['reported_mean']:.6E}",
                    flush=True,
                )
    else:
        values_by_key = {(index, variant_name): [] for index in selected_indices for variant_name in selected_variants}
        tasks = []
        for index in selected_indices:
            for variant_name in selected_variants:
                base_seed = args.seed + index * 10000 + list(VARIANTS).index(variant_name) * 1000000
                tasks.extend((index, variant_name, run, base_seed, args.boundary, args.sampling, args.archive, args.stagnation, args.exploitation_alpha, args.omega_scale, args.parameter_mean, args.f_max, args.f_repair, args.archive_weighting, args.update_mode, args.f11_report_clean, args.exchange_mode, args.elite_fraction, args.elite_state, args.cr_repair, args.best_scope, args.parameter_update, args.redivision_parameter, args.reevaluate_parents, args.archive_size, args.theta, args.stagnation_threshold, tuple(args.initial_mu_f), tuple(args.initial_mu_cr), args.generations) for run in range(args.runs))

        with ProcessPoolExecutor(max_workers=args.jobs) as executor:
            futures = [executor.submit(run_one, task) for task in tasks]
            completed_by_key = {key: 0 for key in values_by_key}
            for future in as_completed(futures):
                index, variant_name, _run, value = future.result()
                key = (index, variant_name)
                values_by_key[key].append(value)
                completed_by_key[key] += 1
                if completed_by_key[key] == args.runs:
                    benchmark = BENCHMARKS[index]
                    row = summarize_values(benchmark, variant_name, values_by_key[key], args.runs, args.generations)
                    rows_by_key[key] = row
                    print(
                        f"{benchmark.name} {variant_name} mean={row['mean']:.6E} "
                        f"std={row['std']:.6E} reported={row['reported_mean']:.6E}",
                        flush=True,
                    )

    rows = [
        rows_by_key[(index, variant_name)]
        for index in selected_indices
        for variant_name in selected_variants
    ]
    results = pd.DataFrame(rows)
    results.to_csv(args.output, index=False)
    print()
    print(results[["function", "algorithm", "mean", "std", "reported_mean", "reported_std"]].to_string(index=False))
    print(f"Wrote: {args.output.resolve()}")


if __name__ == "__main__":
    main()



