"""Reproducible ECMADE implementation for Mean-CVaR portfolio optimization.

Based on:
Song et al. (2023), "An enhanced distributed differential evolution
algorithm for portfolio optimization problems".

The paper's original 286-day Choice terminal return data is not included in
the article. This script therefore supports two reproducible modes:
1. Load your own daily-return CSV with one stock per column.
2. Run a deterministic synthetic demo generated from Table 4 mean returns.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


STOCK_CODES = [
    "600583",
    "600179",
    "600325",
    "600814",
    "600612",
    "601113",
    "600156",
    "600438",
    "600594",
    "600329",
    "600288",
    "600582",
    "600977",
    "600800",
]

TABLE4_MEAN_RETURNS = np.array(
    [
        -0.00002,
        -0.00019,
        0.00008,
        0.00102,
        0.00005,
        0.00130,
        0.00012,
        0.00031,
        0.00101,
        0.00136,
        0.00111,
        0.00125,
        -0.00032,
        0.00006,
    ],
    dtype=float,
)


@dataclass(frozen=True)
class ECMADEConfig:
    population_size: int = 60
    max_generations: int = 3000
    independent_runs: int = 30
    archive_size: int = 20
    theta: float = 1.0 / 13.0
    stagnation_threshold: int = 50
    exploitation_alpha: float = 0.8
    initial_mu_f: tuple[float, float, float] = (0.9, 0.8, 0.8)
    initial_mu_cr: tuple[float, float, float] = (0.9, 0.5, 0.5)
    seed: int = 202305
    lower_bound: float = 0.0
    upper_bound: float = 1.0


@dataclass
class ECMADEOutput:
    best_x: np.ndarray
    best_fitness: float
    history: np.ndarray
    evaluations: int


def cauchy_location_scale(rng: np.random.Generator, location: float, scale: float) -> float:
    value = location + scale * rng.standard_cauchy()
    attempts = 0
    while value <= 0.0 and attempts < 100:
        value = location + scale * rng.standard_cauchy()
        attempts += 1
    return float(np.clip(value, 1e-12, 1.0))


def weighted_lehmer_mean(values: list[tuple[float, int]], current_generation: int) -> float:
    if not values:
        raise ValueError("weighted_lehmer_mean requires at least one archived value")
    weights = np.array([np.exp((generation - current_generation) / max(current_generation, 1)) for _, generation in values])
    data = np.array([value for value, _ in values], dtype=float)
    numerator = np.sum(weights * data * data)
    denominator = np.sum(weights * data)
    return float(numerator / denominator) if denominator > 0.0 else float(np.mean(data))


def weighted_arithmetic_mean(values: list[tuple[float, int]], current_generation: int) -> float:
    if not values:
        raise ValueError("weighted_arithmetic_mean requires at least one archived value")
    weights = np.array([np.exp((generation - current_generation) / max(current_generation, 1)) for _, generation in values])
    data = np.array([value for value, _ in values], dtype=float)
    return float(np.sum(weights * data) / np.sum(weights))


class ECMADE:
    """Co-evolutionary multi-swarm adaptive differential evolution."""

    def __init__(self, objective, dimension: int, config: ECMADEConfig):
        self.objective = objective
        self.dimension = dimension
        self.config = config

    def optimize(self, seed: int | None = None) -> ECMADEOutput:
        cfg = self.config
        rng = np.random.default_rng(cfg.seed if seed is None else seed)
        population = rng.uniform(cfg.lower_bound, cfg.upper_bound, size=(cfg.population_size, self.dimension))
        fitness = np.apply_along_axis(self.objective, 1, population)
        evaluations = cfg.population_size

        subpop_ids = self._random_subpop_ids(rng)
        mu_f = np.array([cfg.initial_mu_f[i] for i in subpop_ids], dtype=float)
        mu_cr = np.array([cfg.initial_mu_cr[i] for i in subpop_ids], dtype=float)
        recent_f: list[list[tuple[float, int]]] = [[] for _ in range(cfg.population_size)]
        recent_cr: list[list[tuple[float, int]]] = [[] for _ in range(cfg.population_size)]

        best_index = int(np.argmin(fitness))
        best_fitness = float(fitness[best_index])
        best_x = population[best_index].copy()
        stagnation = 0
        history = [best_fitness]

        for generation in range(1, cfg.max_generations + 1):
            previous_best = best_fitness
            order = rng.permutation(cfg.population_size)

            for i in order:
                f_i = cauchy_location_scale(rng, mu_f[i], 0.1)
                cr_i = float(np.clip(rng.normal(mu_cr[i], 0.1), 0.0, 1.0))
                mutant = self._mutate(i, population, fitness, subpop_ids[i], f_i, generation, rng)
                mutant = np.clip(mutant, cfg.lower_bound, cfg.upper_bound)
                trial = self._binomial_crossover(population[i], mutant, cr_i, rng)
                trial_fitness = float(self.objective(trial))
                evaluations += 1

                if trial_fitness <= fitness[i]:
                    population[i] = trial
                    fitness[i] = trial_fitness
                    recent_f[i].append((f_i, generation))
                    recent_cr[i].append((cr_i, generation))
                    recent_f[i] = recent_f[i][-cfg.archive_size :]
                    recent_cr[i] = recent_cr[i][-cfg.archive_size :]

                    mu_f[i] = (1.0 - cfg.theta) * mu_f[i] + cfg.theta * weighted_lehmer_mean(recent_f[i], generation)
                    mu_cr[i] = (1.0 - cfg.theta) * mu_cr[i] + cfg.theta * weighted_arithmetic_mean(recent_cr[i], generation)

                    if trial_fitness < best_fitness:
                        best_fitness = trial_fitness
                        best_x = trial.copy()

            history.append(best_fitness)
            stagnation = stagnation + 1 if best_fitness >= previous_best else 0
            if stagnation > cfg.stagnation_threshold:
                subpop_ids = self._exchange_information(population, fitness, rng)
                stagnation = 0

        return ECMADEOutput(best_x=best_x, best_fitness=best_fitness, history=np.array(history), evaluations=evaluations)

    def _random_subpop_ids(self, rng: np.random.Generator) -> np.ndarray:
        ids = np.repeat(np.arange(3), self.config.population_size // 3)
        remainder = self.config.population_size - ids.size
        if remainder:
            ids = np.concatenate([ids, np.arange(remainder)])
        rng.shuffle(ids)
        return ids

    def _choose_indices(self, i: int, count: int, rng: np.random.Generator) -> np.ndarray:
        candidates = np.delete(np.arange(self.config.population_size), i)
        replace = candidates.size < count
        return rng.choice(candidates, size=count, replace=replace)

    def _mutate(
        self,
        i: int,
        population: np.ndarray,
        fitness: np.ndarray,
        subpop_id: int,
        f_i: float,
        generation: int,
        rng: np.random.Generator,
    ) -> np.ndarray:
        best = population[int(np.argmin(fitness))]
        if subpop_id == 0:
            r1, r2, r3, r4, r5 = self._choose_indices(i, 5, rng)
            return population[r1] + f_i * (population[r2] - population[r3]) + f_i * (population[r4] - population[r5])
        if subpop_id == 1:
            r1, r2, r3, r4 = self._choose_indices(i, 4, rng)
            return self.config.exploitation_alpha * best + f_i * (population[r1] - population[r2]) + f_i * (population[r3] - population[r4])

        r1, r2, r3, r4, r5 = self._choose_indices(i, 5, rng)
        omega = generation / max(self.config.max_generations, 1)
        rand_1 = population[r1] + f_i * (population[r2] - population[r3])
        current_to_best_1 = population[i] + f_i * (best - population[i]) + f_i * (population[r4] - population[r5])
        return (1.0 - omega) * rand_1 + omega * current_to_best_1

    def _binomial_crossover(
        self,
        target: np.ndarray,
        mutant: np.ndarray,
        cr: float,
        rng: np.random.Generator,
    ) -> np.ndarray:
        mask = rng.random(self.dimension) <= cr
        mask[int(rng.integers(0, self.dimension))] = True
        return np.where(mask, mutant, target)

    def _exchange_information(self, population: np.ndarray, fitness: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        subpop_ids = self._random_subpop_ids(rng)
        elite_count = max(1, int(np.ceil(0.05 * self.config.population_size)))
        elite_indices = np.argsort(fitness)[:elite_count]
        for subpop_id in range(3):
            members = np.where(subpop_ids == subpop_id)[0]
            if members.size == 0:
                continue
            worst_members = members[np.argsort(fitness[members])[-min(elite_count, members.size) :]]
            for dst, src in zip(worst_members, np.resize(elite_indices, worst_members.size)):
                population[dst] = population[src].copy()
                fitness[dst] = fitness[src]
        return subpop_ids


def project_to_simplex(raw: np.ndarray) -> np.ndarray:
    weights = np.clip(np.asarray(raw, dtype=float), 0.0, 1.0)
    total = float(np.sum(weights))
    if total <= 0.0:
        return np.full(weights.size, 1.0 / weights.size)
    return weights / total


class MeanCVaRObjective:
    def __init__(
        self,
        daily_returns: np.ndarray,
        confidence: float,
        transaction_cost: float = 0.00132,
        expected_threshold: float = 0.0005,
        penalty_return: float = 1e3,
        penalty_sum: float = 1e3,
    ):
        self.daily_returns = np.asarray(daily_returns, dtype=float)
        self.confidence = confidence
        self.transaction_cost = transaction_cost
        self.expected_threshold = expected_threshold
        self.penalty_return = penalty_return
        self.penalty_sum = penalty_sum
        self.mean_returns = np.mean(self.daily_returns, axis=0)

    def __call__(self, x: np.ndarray) -> float:
        weights_raw = np.clip(x, 0.0, 1.0)
        weights = project_to_simplex(weights_raw)
        losses = -self.daily_returns @ weights + self.transaction_cost * np.sum(weights)
        var_alpha = float(np.quantile(losses, self.confidence, method="higher"))
        tail_excess = np.maximum(losses - var_alpha, 0.0)
        cvar = var_alpha + np.mean(tail_excess) / (1.0 - self.confidence)

        # The paper includes transaction cost in the loss function. Applying the
        # same cost again to Table 4's daily mean return constraint would make
        # s=0.0005 infeasible, so the threshold is checked against gross returns.
        expected_return = float(np.dot(weights, self.mean_returns))
        return_penalty = self.penalty_return * max(self.expected_threshold - expected_return, 0.0)
        sum_penalty = self.penalty_sum * abs(1.0 - np.sum(weights_raw))
        return float(cvar + return_penalty + sum_penalty)

    def portfolio_metrics(self, x: np.ndarray) -> dict[str, float | np.ndarray]:
        weights = project_to_simplex(x)
        losses = -self.daily_returns @ weights + self.transaction_cost
        var_alpha = float(np.quantile(losses, self.confidence, method="higher"))
        cvar = float(var_alpha + np.mean(np.maximum(losses - var_alpha, 0.0)) / (1.0 - self.confidence))
        return {
            "weights": weights,
            "var": var_alpha,
            "cvar": cvar,
            "expected_return": float(np.dot(weights, self.mean_returns)),
        }


def synthetic_returns(days: int, seed: int) -> pd.DataFrame:
    """Create a deterministic substitute when the original Choice data is absent."""
    rng = np.random.default_rng(seed)
    n_assets = TABLE4_MEAN_RETURNS.size
    market = rng.normal(0.0, 0.008, size=(days, 1))
    loadings = rng.uniform(-0.45, 0.65, size=(1, n_assets))
    idiosyncratic = rng.normal(0.0, 0.012, size=(days, n_assets))
    returns = TABLE4_MEAN_RETURNS + market @ loadings + idiosyncratic
    return pd.DataFrame(returns, columns=STOCK_CODES)


def load_returns(path: Path | None, seed: int) -> pd.DataFrame:
    if path is None:
        return synthetic_returns(days=286, seed=seed)
    data = pd.read_csv(path)
    numeric = data.select_dtypes(include=[np.number])
    if numeric.empty:
        raise ValueError("CSV must contain numeric daily-return columns")
    return numeric.dropna(axis=0, how="any")


def run_experiment(returns: pd.DataFrame, confidence: float, cfg: ECMADEConfig) -> dict:
    objective = MeanCVaRObjective(returns.to_numpy(), confidence=confidence)
    run_results = []
    histories = []

    for run in range(cfg.independent_runs):
        optimizer = ECMADE(objective, dimension=returns.shape[1], config=cfg)
        output = optimizer.optimize(seed=cfg.seed + run)
        metrics = objective.portfolio_metrics(output.best_x)
        run_results.append((metrics["cvar"], metrics, output))
        histories.append(output.history)

    best_cvar, best_metrics, best_output = min(run_results, key=lambda item: item[0])
    cvars = np.array([item[0] for item in run_results], dtype=float)
    return {
        "confidence": confidence,
        "optimal_value": float(np.min(cvars)),
        "average_value": float(np.mean(cvars)),
        "standard_deviation": float(np.std(cvars, ddof=1)) if cvars.size > 1 else 0.0,
        "best_weights": best_metrics["weights"],
        "best_var": best_metrics["var"],
        "best_expected_return": best_metrics["expected_return"],
        "best_fitness": best_output.best_fitness,
        "average_history": np.mean(np.vstack(histories), axis=0),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ECMADE for Mean-CVaR portfolio optimization.")
    parser.add_argument("--returns-csv", type=Path, default=None, help="CSV containing daily returns, one asset per numeric column.")
    parser.add_argument("--runs", type=int, default=30, help="Independent runs. Paper setting: 30.")
    parser.add_argument("--generations", type=int, default=3000, help="Maximum generations. Paper setting: 3000.")
    parser.add_argument("--seed", type=int, default=202305, help="Base random seed.")
    parser.add_argument("--output-dir", type=Path, default=Path("ecmade_results"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = ECMADEConfig(max_generations=args.generations, independent_runs=args.runs, seed=args.seed)
    returns = load_returns(args.returns_csv, seed=args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    weight_rows = []
    for confidence in (0.75, 0.90, 0.99):
        result = run_experiment(returns, confidence, cfg)
        summary_rows.append(
            {
                "confidence": confidence,
                "optimal_value": result["optimal_value"],
                "average_value": result["average_value"],
                "standard_deviation": result["standard_deviation"],
                "best_var": result["best_var"],
                "best_expected_return": result["best_expected_return"],
            }
        )
        weight_rows.append(pd.Series(result["best_weights"], index=returns.columns, name=f"alpha_{confidence:.2f}"))
        pd.DataFrame({"generation": np.arange(result["average_history"].size), "best_cvar": result["average_history"]}).to_csv(
            args.output_dir / f"history_alpha_{confidence:.2f}.csv",
            index=False,
        )

    summary = pd.DataFrame(summary_rows)
    weights = pd.DataFrame(weight_rows).T
    summary.to_csv(args.output_dir / "summary.csv", index=False)
    weights.to_csv(args.output_dir / "weights.csv")

    print("ECMADE Mean-CVaR results")
    print(summary.to_string(index=False))
    print()
    print("Best weights")
    print(weights.to_string())
    print()
    print(f"Wrote CSV outputs to: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
