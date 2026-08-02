"""ECMADE-MOO for portfolio optimization and standard MOO benchmarks.

This script implements an Enhanced Co-evolutionary Multi-swarm Adaptive
Differential Evolution framework with NSGA-II environmental selection:

* Multi-subpopulation DE evolution
* Adaptive F/CR control
* Pareto dominance, fast non-dominated sorting, crowding distance
* Elitist environmental selection
* Inputs: OR-Library-style portfolio files, returns CSV, ZDT, DTLZ, UF

Examples
--------
python ecmade_moo.py --problem ZDT1 --max-fe 10000 --pop-size 100
python ecmade_moo.py --problem DTLZ2 --dimension 12 --objectives 3
python ecmade_moo.py --problem UF10 --max-fe 30000
python ecmade_moo.py --problem ORLIB --orlib-path port1.txt
python ecmade_moo.py --problem PORTFOLIO --returns-csv returns.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np


Array = np.ndarray


@dataclass(frozen=True)
class Problem:
    name: str
    num_obj: int
    num_var: int
    lower: Array
    upper: Array
    evaluate: Callable[[Array], Array]
    repair: Callable[[Array], Array]
    pareto_front: Callable[[int], Array] | None = None


@dataclass(frozen=True)
class ECMADEMOOConfig:
    pop_size: int = 100
    max_fe: int = 10000
    subpops: int = 3
    archive_size: int = 20
    theta: float = 1.0 / 13.0
    stagnation_threshold: int = 50
    exploitation_alpha: float = 0.8
    seed: int = 2026
    initial_mu_f: tuple[float, ...] = (0.9, 0.8, 0.8)
    initial_mu_cr: tuple[float, ...] = (0.9, 0.5, 0.5)
    f_scale: float = 0.1
    cr_scale: float = 0.1
    f_max: float = 1.0
    exchange_mode: str = "paper"
    elite_ratio: float = 0.05
    operator_mode: str = "mixed"
    consensus_archive: bool = False
    consensus_bins: int = 24
    archive_consensus_weight: float = 0.0
    best_guide: str = "rank"
    best_consensus_weight: float = 0.55
    best_centrality_weight: float = 0.30
    min_subpop_size: int = 1
    archive_limit_factor: int = 5


@dataclass
class ECMADEMOOResult:
    variables: Array
    objectives: Array
    pareto_variables: Array
    pareto_objectives: Array
    evaluations: int
    history: list[dict[str, float | int]]


def default_repair(x: Array, lower: Array, upper: Array) -> Array:
    return np.clip(x, lower, upper)


def simplex_repair(x: Array, lower: Array, upper: Array) -> Array:
    y = np.clip(x, lower, upper)
    total = float(np.sum(y))
    if total <= 1e-15:
        y = np.ones_like(y) / len(y)
    else:
        y = y / total
    return np.clip(y, lower, upper) / max(float(np.sum(np.clip(y, lower, upper))), 1e-15)


def cardinality_simplex_repair(x: Array, lower: Array, upper: Array, cardinality: int) -> Array:
    y = np.clip(x, lower, upper)
    k = int(max(1, min(cardinality, len(y))))
    if k < len(y):
        keep = np.argpartition(y, -k)[-k:]
        mask = np.zeros(len(y), dtype=bool)
        mask[keep] = True
        y = np.where(mask, y, 0.0)
    total = float(np.sum(y))
    if total <= 1e-15:
        keep = np.argpartition(x, -k)[-k:]
        y = np.zeros(len(x), dtype=float)
        y[keep] = 1.0 / k
    else:
        y = y / total
    return y


def dominates(a: Array, b: Array) -> bool:
    return bool(np.all(a <= b) and np.any(a < b))


def nondominated_sort(objs: Array) -> list[list[int]]:
    n = len(objs)
    if n == 0:
        return []
    less_equal = np.all(objs[:, None, :] <= objs[None, :, :], axis=2)
    strictly_less = np.any(objs[:, None, :] < objs[None, :, :], axis=2)
    dom = less_equal & strictly_less
    dominated_count = np.sum(dom, axis=0).astype(int)
    dominates_list = [np.where(dom[i])[0].tolist() for i in range(n)]
    fronts: list[list[int]] = [np.where(dominated_count == 0)[0].tolist()]
    i = 0
    while i < len(fronts) and fronts[i]:
        next_front: list[int] = []
        for p in fronts[i]:
            for q in dominates_list[p]:
                dominated_count[q] -= 1
                if dominated_count[q] == 0:
                    next_front.append(q)
        if next_front:
            fronts.append(next_front)
        i += 1
    return fronts


def crowding_distance(objs: Array) -> Array:
    n = len(objs)
    if n == 0:
        return np.array([])
    if n <= 2:
        return np.full(n, np.inf)
    distance = np.zeros(n)
    for m in range(objs.shape[1]):
        order = np.argsort(objs[:, m])
        distance[order[0]] = np.inf
        distance[order[-1]] = np.inf
        span = objs[order[-1], m] - objs[order[0], m]
        if span <= 0.0:
            continue
        distance[order[1:-1]] += (objs[order[2:], m] - objs[order[:-2], m]) / span
    return distance


def ranks_and_crowding(objs: Array) -> tuple[Array, Array]:
    ranks = np.empty(len(objs), dtype=int)
    crowd = np.zeros(len(objs), dtype=float)
    for rank, front in enumerate(nondominated_sort(objs)):
        idx = np.asarray(front, dtype=int)
        ranks[idx] = rank
        crowd[idx] = crowding_distance(objs[idx])
    return ranks, crowd


def environmental_selection_indices(objs: Array, target_size: int) -> Array:
    chosen: list[int] = []
    for front in nondominated_sort(objs):
        if len(chosen) + len(front) <= target_size:
            chosen.extend(front)
            continue
        idx = np.asarray(front, dtype=int)
        cd = crowding_distance(objs[idx])
        keep = idx[np.argsort(-cd)[: target_size - len(chosen)]]
        chosen.extend(keep.tolist())
        break
    return np.asarray(chosen, dtype=int)


def nondominated_indices(objs: Array) -> Array:
    fronts = nondominated_sort(objs)
    return np.asarray(fronts[0], dtype=int) if fronts else np.array([], dtype=int)


def rank_order(objs: Array) -> Array:
    ranks, crowd = ranks_and_crowding(objs)
    return np.lexsort((-crowd, ranks))


def sample_f(rng: np.random.Generator, mu: float, scale: float = 0.1, f_max: float = 1.0) -> float:
    value = mu + scale * rng.standard_cauchy()
    attempts = 0
    while value <= 0.0 and attempts < 100:
        value = mu + scale * rng.standard_cauchy()
        attempts += 1
    return float(np.clip(value, 1e-8, f_max))


def sample_cr(rng: np.random.Generator, mu: float, scale: float = 0.1) -> float:
    return float(np.clip(rng.normal(mu, scale), 0.0, 1.0))


def weighted_lehmer_mean(values: list[tuple[float, int]], current_generation: int) -> float:
    data = np.asarray([value for value, _ in values], dtype=float)
    weights = successful_parameter_weights(values, current_generation)
    weighted_denom = float(np.sum(weights * data))
    return float(np.sum(weights * data * data) / weighted_denom) if weighted_denom > 0.0 else float(np.mean(data))


def weighted_arithmetic_mean(values: list[tuple[float, int]], current_generation: int) -> float:
    data = np.asarray([value for value, _ in values], dtype=float)
    weights = successful_parameter_weights(values, current_generation)
    return float(np.sum(weights * data))


def successful_parameter_weights(values: list[tuple[float, int]], current_generation: int) -> Array:
    generations = np.asarray([generation for _, generation in values], dtype=float)
    weights = np.exp(generations / max(float(current_generation), 1.0) - 1.0)
    total = float(np.sum(weights))
    if total <= 0.0:
        return np.full(len(values), 1.0 / max(len(values), 1))
    return weights / total


def choose_indices(rng: np.random.Generator, n: int, excluded: int, count: int) -> Array:
    pool = np.array([i for i in range(n) if i != excluded], dtype=int)
    replace = len(pool) < count
    return rng.choice(pool, size=count, replace=replace)


def choose_indices_from_subpop(rng: np.random.Generator, pool: Array, excluded: int, count: int) -> Array:
    candidates = pool[pool != excluded]
    if len(candidates) < count:
        raise ValueError(
            f"Subpopulation has {len(candidates) + 1} individuals, but this mutation strategy requires at least {count + 1}."
        )
    return rng.choice(candidates, size=count, replace=False)


def binomial_crossover(target: Array, mutant: Array, cr: float, rng: np.random.Generator) -> Array:
    mask = rng.random(len(target)) <= cr
    mask[int(rng.integers(0, len(target)))] = True
    return np.where(mask, mutant, target)


class ECMADEMOO:
    def __init__(self, problem: Problem, config: ECMADEMOOConfig):
        self.problem = problem
        self.config = config

    def run(self) -> ECMADEMOOResult:
        cfg = self.config
        rng = np.random.default_rng(cfg.seed)
        pop = rng.uniform(self.problem.lower, self.problem.upper, size=(cfg.pop_size, self.problem.num_var))
        pop = np.asarray([self.problem.repair(x) for x in pop])
        objs = np.asarray([self.problem.evaluate(x) for x in pop])
        subpop_ids = self._initial_subpop_ids(rng)
        evaluations = cfg.pop_size

        mu_f = np.array([cfg.initial_mu_f[sid % len(cfg.initial_mu_f)] for sid in subpop_ids], dtype=float)
        mu_cr = np.array([cfg.initial_mu_cr[sid % len(cfg.initial_mu_cr)] for sid in subpop_ids], dtype=float)
        recent_f: list[list[tuple[float, int]]] = [[] for _ in range(cfg.pop_size)]
        recent_cr: list[list[tuple[float, int]]] = [[] for _ in range(cfg.pop_size)]
        history: list[dict[str, float | int]] = []
        generation = 0
        archive_vars, archive_objs, archive_hits, archive_masks = self._pareto_archive(pop, objs, subpop_ids)
        stagnation = 0
        exchanges = 0

        while evaluations < cfg.max_fe:
            generation += 1
            best_indices = self._select_best_guides(objs, subpop_ids)
            off_vars: list[Array] = []
            off_subpops: list[int] = []
            off_mu_f: list[float] = []
            off_mu_cr: list[float] = []
            off_recent_f: list[list[tuple[float, int]]] = []
            off_recent_cr: list[list[tuple[float, int]]] = []
            trial_params: list[tuple[int, float, float]] = []

            for sid in range(cfg.subpops):
                members = np.where(subpop_ids == sid)[0]
                if len(members) == 0:
                    continue
                for i in members:
                    if evaluations + len(off_vars) >= cfg.max_fe:
                        break
                    f_i = sample_f(rng, mu_f[i], cfg.f_scale, cfg.f_max)
                    cr_i = sample_cr(rng, mu_cr[i], cfg.cr_scale)
                    best_index = int(best_indices[sid])
                    mutant = self._mutate(i, sid, pop, subpop_ids, best_index, f_i, generation, rng)
                    mutant = default_repair(mutant, self.problem.lower, self.problem.upper)
                    trial = binomial_crossover(pop[i], mutant, cr_i, rng)
                    trial = self.problem.repair(trial)
                    off_vars.append(trial)
                    off_subpops.append(sid)
                    off_mu_f.append(float(mu_f[i]))
                    off_mu_cr.append(float(mu_cr[i]))
                    off_recent_f.append(list(recent_f[i]))
                    off_recent_cr.append(list(recent_cr[i]))
                    trial_params.append((i, f_i, cr_i))

            if not off_vars:
                break
            offspring = np.asarray(off_vars)
            off_objs = np.asarray([self.problem.evaluate(x) for x in offspring])
            evaluations += len(offspring)

            pool_vars = np.vstack((pop, offspring))
            pool_objs = np.vstack((objs, off_objs))
            pool_subpops = np.concatenate((subpop_ids, np.asarray(off_subpops, dtype=int)))
            pool_mu_f = np.concatenate((mu_f, np.asarray(off_mu_f, dtype=float)))
            pool_mu_cr = np.concatenate((mu_cr, np.asarray(off_mu_cr, dtype=float)))
            pool_recent_f = list(recent_f) + off_recent_f
            pool_recent_cr = list(recent_cr) + off_recent_cr
            selected = environmental_selection_indices(pool_objs, cfg.pop_size)

            survived_offspring = selected[selected >= cfg.pop_size] - cfg.pop_size
            for off_idx in survived_offspring:
                parent_idx, f_i, cr_i = trial_params[int(off_idx)]
                pool_idx = cfg.pop_size + int(off_idx)
                pool_recent_f[pool_idx] = (list(recent_f[parent_idx]) + [(f_i, generation)])[-cfg.archive_size :]
                pool_recent_cr[pool_idx] = (list(recent_cr[parent_idx]) + [(cr_i, generation)])[-cfg.archive_size :]
                pool_mu_f[pool_idx] = (1.0 - cfg.theta) * pool_mu_f[pool_idx] + cfg.theta * weighted_lehmer_mean(
                    pool_recent_f[pool_idx], generation
                )
                pool_mu_cr[pool_idx] = (1.0 - cfg.theta) * pool_mu_cr[pool_idx] + cfg.theta * weighted_arithmetic_mean(
                    pool_recent_cr[pool_idx], generation
                )
                pool_mu_f[pool_idx] = float(np.clip(pool_mu_f[pool_idx], 1e-8, cfg.f_max))
                pool_mu_cr[pool_idx] = float(np.clip(pool_mu_cr[pool_idx], 0.0, 1.0))

            pop = pool_vars[selected]
            objs = pool_objs[selected]
            subpop_ids = pool_subpops[selected]
            mu_f = pool_mu_f[selected]
            mu_cr = pool_mu_cr[selected]
            recent_f = [pool_recent_f[int(idx)] for idx in selected]
            recent_cr = [pool_recent_cr[int(idx)] for idx in selected]
            subpop_ids = self._ensure_subpop_balance(subpop_ids, objs, rng)

            archive_vars, archive_objs, archive_hits, archive_masks, archive_changed = self._update_pareto_archive(
                archive_vars, archive_objs, archive_hits, archive_masks, pop, objs, subpop_ids
            )
            stagnation = 0 if archive_changed else stagnation + 1
            if cfg.stagnation_threshold > 0 and stagnation > cfg.stagnation_threshold:
                pop, objs, subpop_ids, mu_f, mu_cr, recent_f, recent_cr = self._exchange_information(
                    pop, objs, subpop_ids, mu_f, mu_cr, recent_f, recent_cr, rng
                )
                stagnation = 0
                exchanges += 1

            nd_count = len(nondominated_indices(objs))
            history.append(
                {
                    "generation": generation,
                    "evaluations": evaluations,
                    "nondominated": nd_count,
                    "archive_size": len(archive_objs),
                    "stagnation": stagnation,
                    "exchanges": exchanges,
                }
            )

        nd = nondominated_indices(archive_objs)
        return ECMADEMOOResult(
            variables=pop,
            objectives=objs,
            pareto_variables=archive_vars[nd],
            pareto_objectives=archive_objs[nd],
            evaluations=evaluations,
            history=history,
        )

    def _initial_subpop_ids(self, rng: np.random.Generator) -> Array:
        ids = np.arange(self.config.pop_size) % self.config.subpops
        rng.shuffle(ids)
        return ids.astype(int)

    def _mutate(
        self,
        i: int,
        sid: int,
        pop: Array,
        subpop_ids: Array,
        best_index: int,
        f_i: float,
        generation: int,
        rng: np.random.Generator,
    ) -> Array:
        best = pop[best_index]
        members = np.where(subpop_ids == sid)[0]

        def mutation_pool(count: int) -> Array:
            candidates = members[members != i]
            if len(candidates) >= count:
                return members
            return np.arange(len(pop), dtype=int)

        mode = self.config.operator_mode.lower()
        if mode == "mixed":
            mode = ("rand2", "best2", "hybrid")[sid % 3]
        if mode == "rand2":
            r1, r2, r3, r4, r5 = choose_indices_from_subpop(rng, mutation_pool(5), i, 5)
            return pop[r1] + f_i * (pop[r2] - pop[r3]) + f_i * (pop[r4] - pop[r5])
        if mode == "best2":
            r1, r2, r3, r4 = choose_indices_from_subpop(rng, mutation_pool(4), i, 4)
            return self.config.exploitation_alpha * best + f_i * (pop[r1] - pop[r2]) + f_i * (pop[r3] - pop[r4])
        if mode != "hybrid":
            raise ValueError("operator_mode must be one of: mixed, rand2, best2, hybrid")
        r1, r2, r3, r4, r5 = choose_indices_from_subpop(rng, mutation_pool(5), i, 5)
        omega = min(1.0, generation / max(1.0, cfg_float(self.config.max_fe, self.config.pop_size)))
        rand_1 = pop[r1] + f_i * (pop[r2] - pop[r3])
        current_to_best_1 = pop[i] + f_i * (best - pop[i]) + f_i * (pop[r4] - pop[r5])
        return (1.0 - omega) * rand_1 + omega * current_to_best_1

    def _ensure_subpop_balance(self, subpop_ids: Array, objs: Array, rng: np.random.Generator) -> Array:
        ids = subpop_ids.copy()
        min_size = min(self.config.min_subpop_size, len(ids) // max(1, self.config.subpops))
        ranks, crowd = ranks_and_crowding(objs)
        order_worst = np.lexsort((crowd, -ranks))
        for sid in range(self.config.subpops):
            while np.sum(ids == sid) < min_size:
                counts = np.bincount(ids, minlength=self.config.subpops)
                donors = np.where(counts > min_size)[0]
                donor = int(donors[np.argmax(counts[donors])]) if len(donors) else int(np.argmax(counts))
                donor_candidates = [idx for idx in order_worst.tolist() if ids[idx] == donor]
                if donor_candidates:
                    ids[donor_candidates[0]] = sid
                else:
                    ids[int(rng.integers(0, len(ids)))] = sid
        return ids

    def _select_best_guides(self, objs: Array, subpop_ids: Array) -> Array:
        guide = self.config.best_guide.lower()
        if guide == "rank":
            return np.full(self.config.subpops, int(rank_order(objs)[0]), dtype=int)
        if guide == "ideal":
            representative = self._select_ideal_best(objs)
            return np.full(self.config.subpops, representative, dtype=int)
        if guide == "consensus":
            representative = self._select_consensus_best(objs, subpop_ids)
            return np.full(self.config.subpops, representative, dtype=int)
        if guide != "reference":
            raise ValueError("--best-guide must be one of: rank, ideal, reference, consensus")
        return self._select_reference_best_guides(objs, subpop_ids)

    def _select_ideal_best(self, objs: Array) -> int:
        ranks, crowd = ranks_and_crowding(objs)
        front = np.where(ranks == 0)[0]
        if len(front) == 0:
            return int(rank_order(objs)[0])
        normalized = self._normalize_objectives(objs)
        distance = np.linalg.norm(normalized[front], axis=1)
        order = np.lexsort((-crowd[front], distance))
        return int(front[int(order[0])])

    def _select_consensus_best(self, objs: Array, subpop_ids: Array) -> int:
        if not self.config.consensus_archive:
            return int(rank_order(objs)[0])
        ranks, crowd = ranks_and_crowding(objs)
        front = np.where(ranks == 0)[0]
        if len(front) == 0:
            return int(rank_order(objs)[0])
        hits = np.ones(len(objs), dtype=float)
        masks = self._subpop_masks(subpop_ids)
        consensus = self._consensus_scores(objs, hits, masks)
        centrality = self._centrality_scores(objs)
        crowd_norm = self._normalized_crowding(crowd)
        crowd_weight = max(0.0, 1.0 - self.config.best_consensus_weight - self.config.best_centrality_weight)
        score = (
            self.config.best_consensus_weight * consensus
            + self.config.best_centrality_weight * centrality
            + crowd_weight * crowd_norm
        )
        return int(front[int(np.argmax(score[front]))])

    def _select_reference_best_guides(self, objs: Array, subpop_ids: Array) -> Array:
        ranks, crowd = ranks_and_crowding(objs)
        front = np.where(ranks == 0)[0]
        if len(front) == 0:
            return np.full(self.config.subpops, int(rank_order(objs)[0]), dtype=int)
        normalized = self._normalize_objectives(objs)
        weights = self._reference_weights()
        guides = np.empty(self.config.subpops, dtype=int)
        for sid in range(self.config.subpops):
            local = front[subpop_ids[front] == sid]
            candidates = local if len(local) > 0 else front
            scalar = np.max(weights[sid] * normalized[candidates], axis=1)
            order = np.lexsort((-crowd[candidates], scalar))
            guides[sid] = int(candidates[int(order[0])])
        return guides

    def _reference_weights(self) -> Array:
        k = self.config.subpops
        m = self.problem.num_obj
        eps = 1e-3
        if m == 2:
            if k == 1:
                weights = np.array([[0.5, 0.5]], dtype=float)
            else:
                t = np.linspace(0.0, 1.0, k)
                weights = np.column_stack((1.0 - t, t))
        else:
            weights = uniform_simplex_points(k, m, 1.0)
        weights = np.maximum(weights, eps)
        return weights / np.sum(weights, axis=1, keepdims=True)

    def _normalize_objectives(self, objs: Array) -> Array:
        lo = np.min(objs, axis=0)
        hi = np.max(objs, axis=0)
        span = np.where(hi > lo, hi - lo, 1.0)
        return np.clip((objs - lo) / span, 0.0, 1.0)

    def _pareto_archive(self, vars_: Array, objs: Array, subpop_ids: Array) -> tuple[Array, Array, Array, Array]:
        nd = nondominated_indices(objs)
        hits = np.ones(len(nd), dtype=float)
        masks = self._subpop_masks(subpop_ids)[nd]
        return vars_[nd].copy(), objs[nd].copy(), hits, masks

    def _update_pareto_archive(
        self,
        archive_vars: Array,
        archive_objs: Array,
        archive_hits: Array,
        archive_masks: Array,
        pop: Array,
        objs: Array,
        subpop_ids: Array,
    ) -> tuple[Array, Array, Array, Array, bool]:
        old_objs = archive_objs.copy()
        merged_vars = np.vstack((archive_vars, pop))
        merged_objs = np.vstack((archive_objs, objs))
        merged_hits = np.concatenate((archive_hits, np.ones(len(objs), dtype=float)))
        merged_masks = np.concatenate((archive_masks, self._subpop_masks(subpop_ids)))
        nd = nondominated_indices(merged_objs)
        new_vars = merged_vars[nd]
        new_objs = merged_objs[nd]
        new_hits = merged_hits[nd]
        new_masks = merged_masks[nd]
        new_vars, new_objs, new_hits, new_masks = self._unique_archive_entries(new_vars, new_objs, new_hits, new_masks)
        limit = max(self.config.pop_size * self.config.archive_limit_factor, self.config.pop_size)
        if len(new_objs) > limit:
            keep = self._archive_pruning_indices(new_objs, new_hits, new_masks, limit)
            new_vars = new_vars[keep]
            new_objs = new_objs[keep]
            new_hits = new_hits[keep]
            new_masks = new_masks[keep]
        changed = self._archive_changed(old_objs, new_objs)
        return new_vars, new_objs, new_hits, new_masks, changed

    def _archive_pruning_indices(self, objs: Array, hits: Array, masks: Array, target_size: int) -> Array:
        if not self.config.consensus_archive:
            return environmental_selection_indices(objs, target_size)
        consensus = self._consensus_scores(objs, hits, masks)
        crowd_norm = self._normalized_crowding(crowding_distance(objs))
        score = self.config.archive_consensus_weight * consensus + (1.0 - self.config.archive_consensus_weight) * crowd_norm
        return np.argsort(-score)[:target_size]

    def _unique_objectives(self, objs: Array) -> Array:
        seen: set[tuple[float, ...]] = set()
        keep: list[int] = []
        for i, row in enumerate(objs):
            key = tuple(np.round(row, 12).tolist())
            if key in seen:
                continue
            seen.add(key)
            keep.append(i)
        return np.asarray(keep, dtype=int)

    def _unique_archive_entries(self, vars_: Array, objs: Array, hits: Array, masks: Array) -> tuple[Array, Array, Array, Array]:
        key_to_pos: dict[tuple[float, ...], int] = {}
        keep: list[int] = []
        combined_hits: list[float] = []
        combined_masks: list[int] = []
        for i, row in enumerate(objs):
            key = tuple(np.round(row, 12).tolist())
            if key in key_to_pos:
                pos = key_to_pos[key]
                combined_hits[pos] += float(hits[i])
                combined_masks[pos] = int(combined_masks[pos]) | int(masks[i])
                continue
            key_to_pos[key] = len(keep)
            keep.append(i)
            combined_hits.append(float(hits[i]))
            combined_masks.append(int(masks[i]))
        idx = np.asarray(keep, dtype=int)
        return vars_[idx], objs[idx], np.asarray(combined_hits, dtype=float), np.asarray(combined_masks, dtype=object)

    def _subpop_masks(self, subpop_ids: Array) -> Array:
        return np.asarray([1 << int(sid) for sid in subpop_ids], dtype=object)

    def _objective_cells(self, objs: Array) -> list[tuple[int, ...]]:
        if len(objs) == 0:
            return []
        scaled = self._normalize_objectives(objs)
        bins = max(2, int(self.config.consensus_bins))
        cell_values = np.minimum((scaled * bins).astype(int), bins - 1)
        return [tuple(row.tolist()) for row in cell_values]

    def _consensus_scores(self, objs: Array, hits: Array, masks: Array) -> Array:
        if len(objs) == 0:
            return np.array([])
        cells = self._objective_cells(objs)
        cell_hits: dict[tuple[int, ...], float] = {}
        cell_masks: dict[tuple[int, ...], int] = {}
        for cell, hit, mask in zip(cells, hits, masks):
            cell_hits[cell] = cell_hits.get(cell, 0.0) + float(hit)
            cell_masks[cell] = cell_masks.get(cell, 0) | int(mask)
        max_hits = max(cell_hits.values()) if cell_hits else 1.0
        scores = np.zeros(len(objs), dtype=float)
        for i, cell in enumerate(cells):
            subpop_score = int(cell_masks[cell]).bit_count() / max(1, self.config.subpops)
            hit_score = math.log1p(cell_hits[cell]) / max(math.log1p(max_hits), 1e-12)
            scores[i] = 0.65 * subpop_score + 0.35 * hit_score
        return scores

    def _centrality_scores(self, objs: Array) -> Array:
        if len(objs) == 0:
            return np.array([])
        lo = np.min(objs, axis=0)
        hi = np.max(objs, axis=0)
        span = np.where(hi > lo, hi - lo, 1.0)
        scaled = (objs - lo) / span
        center = np.median(scaled, axis=0)
        distance = np.linalg.norm(scaled - center, axis=1)
        max_distance = float(np.max(distance))
        if max_distance <= 0.0:
            return np.ones(len(objs), dtype=float)
        return 1.0 - distance / max_distance

    def _normalized_crowding(self, crowd: Array) -> Array:
        if len(crowd) == 0:
            return np.array([])
        finite = crowd[np.isfinite(crowd)]
        if len(finite) == 0:
            return np.ones(len(crowd), dtype=float)
        max_finite = float(np.max(finite))
        if max_finite <= 0.0:
            norm = np.zeros(len(crowd), dtype=float)
        else:
            norm = np.where(np.isfinite(crowd), crowd / max_finite, 1.0)
        return np.clip(norm, 0.0, 1.0)

    def _archive_changed(self, old_objs: Array, new_objs: Array) -> bool:
        if len(old_objs) != len(new_objs):
            return True
        old_keys = {tuple(np.round(row, 12).tolist()) for row in old_objs}
        new_keys = {tuple(np.round(row, 12).tolist()) for row in new_objs}
        return old_keys != new_keys

    def _exchange_information(
        self,
        pop: Array,
        objs: Array,
        subpop_ids: Array,
        mu_f: Array,
        mu_cr: Array,
        recent_f: list[list[tuple[float, int]]],
        recent_cr: list[list[tuple[float, int]]],
        rng: np.random.Generator,
    ) -> tuple[Array, Array, Array, Array, Array, list[list[tuple[float, int]]], list[list[tuple[float, int]]]]:
        if self.config.exchange_mode == "none":
            return pop, objs, subpop_ids, mu_f, mu_cr, recent_f, recent_cr
        if self.config.exchange_mode == "stable":
            return self._stable_exchange_information(pop, objs, subpop_ids, mu_f, mu_cr, recent_f, recent_cr)
        if self.config.exchange_mode != "paper":
            raise ValueError("--exchange-mode must be one of: none, paper, stable")
        new_pop = pop.copy()
        new_objs = objs.copy()
        new_mu_f = mu_f.copy()
        new_mu_cr = mu_cr.copy()
        new_recent_f = [list(values) for values in recent_f]
        new_recent_cr = [list(values) for values in recent_cr]
        ranks, crowd = ranks_and_crowding(objs)
        elite_order = np.lexsort((-crowd, ranks))
        elite_count = max(1, int(math.ceil(self.config.elite_ratio * len(pop)))) if self.config.elite_ratio > 0 else 0
        elites = elite_order[:elite_count]

        ids = self._initial_subpop_ids(rng)
        worst_order = np.lexsort((crowd, -ranks))
        for sid in range(self.config.subpops):
            members = np.where(ids == sid)[0]
            if len(members) == 0:
                continue
            member_set = set(members.tolist())
            worst_members = [idx for idx in worst_order.tolist() if idx in member_set]
            replace_count = min(len(worst_members), elite_count)
            for pos in range(replace_count):
                target = worst_members[pos]
                source = int(elites[pos % len(elites)])
                if target == source:
                    continue
                new_pop[target] = pop[source]
                new_objs[target] = objs[source]
                new_mu_f[target] = mu_f[source]
                new_mu_cr[target] = mu_cr[source]
                new_recent_f[target] = list(recent_f[source])
                new_recent_cr[target] = list(recent_cr[source])
                ids[target] = sid
        return new_pop, new_objs, ids, new_mu_f, new_mu_cr, new_recent_f, new_recent_cr

    def _stable_exchange_information(
        self,
        pop: Array,
        objs: Array,
        subpop_ids: Array,
        mu_f: Array,
        mu_cr: Array,
        recent_f: list[list[tuple[float, int]]],
        recent_cr: list[list[tuple[float, int]]],
    ) -> tuple[Array, Array, Array, Array, Array, list[list[tuple[float, int]]], list[list[tuple[float, int]]]]:
        new_pop = pop.copy()
        new_objs = objs.copy()
        new_mu_f = mu_f.copy()
        new_mu_cr = mu_cr.copy()
        new_recent_f = [list(values) for values in recent_f]
        new_recent_cr = [list(values) for values in recent_cr]
        ids = subpop_ids.copy()

        ranks, crowd = ranks_and_crowding(objs)
        elite_order = np.lexsort((-crowd, ranks))
        elite_count = max(1, int(math.ceil(self.config.elite_ratio * len(pop)))) if self.config.elite_ratio > 0 else 0
        elites = elite_order[:elite_count]
        worst_order = np.lexsort((crowd, -ranks))

        for sid in range(self.config.subpops):
            members = np.where(ids == sid)[0]
            if len(members) == 0:
                continue
            member_set = set(members.tolist())
            worst_members = [idx for idx in worst_order.tolist() if idx in member_set]
            replace_count = min(len(worst_members), elite_count)
            for pos in range(replace_count):
                target = worst_members[pos]
                source = int(elites[pos % len(elites)])
                if target == source:
                    continue
                new_pop[target] = pop[source]
                new_objs[target] = objs[source]
                new_mu_f[target] = mu_f[source]
                new_mu_cr[target] = mu_cr[source]
                new_recent_f[target] = list(recent_f[source])
                new_recent_cr[target] = list(recent_cr[source])
                ids[target] = sid
        return new_pop, new_objs, ids, new_mu_f, new_mu_cr, new_recent_f, new_recent_cr


def cfg_float(max_fe: int, pop_size: int) -> float:
    return max(1.0, max_fe / max(1, pop_size))


def uniform_simplex_points(n: int, m: int, total: float = 1.0) -> Array:
    rng = np.random.default_rng(12345 + n + m)
    return rng.dirichlet(np.ones(m), size=n) * total


def sphere_front(n: int, m: int) -> Array:
    pts = uniform_simplex_points(n, m, 1.0)
    return pts / np.linalg.norm(pts, axis=1, keepdims=True)


def build_problem(name: str, dimension: int | None = None, objectives: int | None = None, args: argparse.Namespace | None = None) -> Problem:
    n = name.upper()
    if n.startswith("ZDT"):
        return build_zdt(n, dimension)
    if n.startswith("DTLZ"):
        return build_dtlz(n, dimension, objectives)
    if n.startswith("UF"):
        return build_uf(n, dimension)
    if n == "ORLIB":
        if args is None or args.orlib_path is None:
            raise ValueError("--problem ORLIB requires --orlib-path")
        return build_orlibrary_problem(Path(args.orlib_path), getattr(args, "cardinality", None))
    if n == "PORTFOLIO":
        if args is None or args.returns_csv is None:
            raise ValueError("--problem PORTFOLIO requires --returns-csv")
        return build_returns_csv_problem(Path(args.returns_csv), getattr(args, "cardinality", None))
    raise ValueError("Supported problems: ZDT1-4/ZDT6, DTLZ1-7, UF1-10, ORLIB, PORTFOLIO")


def build_zdt(name: str, dimension: int | None = None) -> Problem:
    num_var = dimension if dimension is not None else (10 if name in {"ZDT4", "ZDT6"} else 30)
    lower = np.zeros(num_var)
    upper = np.ones(num_var)
    if name == "ZDT4":
        lower[1:] = -5.0
        upper[1:] = 5.0

    def evaluate(x: Array) -> Array:
        f1 = float(x[0])
        if name == "ZDT1":
            g = 1.0 + 9.0 * np.sum(x[1:]) / (num_var - 1)
            h = 1.0 - math.sqrt(max(f1 / g, 0.0))
        elif name == "ZDT2":
            g = 1.0 + 9.0 * np.sum(x[1:]) / (num_var - 1)
            h = 1.0 - (f1 / g) ** 2
        elif name == "ZDT3":
            g = 1.0 + 9.0 * np.sum(x[1:]) / (num_var - 1)
            h = 1.0 - math.sqrt(max(f1 / g, 0.0)) - (f1 / g) * math.sin(10.0 * math.pi * f1)
        elif name == "ZDT4":
            g = 1.0 + 10.0 * (num_var - 1) + np.sum(x[1:] ** 2 - 10.0 * np.cos(4.0 * math.pi * x[1:]))
            h = 1.0 - math.sqrt(max(f1 / g, 0.0))
        elif name == "ZDT6":
            f1 = 1.0 - math.exp(-4.0 * x[0]) * math.sin(6.0 * math.pi * x[0]) ** 6
            g = 1.0 + 9.0 * (np.sum(x[1:]) / (num_var - 1)) ** 0.25
            h = 1.0 - (f1 / g) ** 2
        else:
            raise ValueError(name)
        return np.array([f1, g * h], dtype=float)

    def pf(count: int) -> Array:
        x = np.linspace(0.0, 1.0, count)
        if name in {"ZDT1", "ZDT4"}:
            return np.column_stack((x, 1.0 - np.sqrt(x)))
        if name == "ZDT2":
            return np.column_stack((x, 1.0 - x**2))
        if name == "ZDT3":
            segments = np.array([[0.0, 0.0830015349], [0.1822287280, 0.2577623634], [0.4093136748, 0.4538821041], [0.6183967944, 0.6525117038], [0.8233317983, 0.8518328654]])
            per = max(2, math.ceil(count / len(segments)))
            xs = np.concatenate([np.linspace(lo, hi, per) for lo, hi in segments])[:count]
            return np.column_stack((xs, 1.0 - np.sqrt(xs) - xs * np.sin(10.0 * math.pi * xs)))
        if name == "ZDT6":
            f1 = np.linspace(0.2807753191, 1.0, count)
            return np.column_stack((f1, 1.0 - f1**2))
        raise ValueError(name)

    return Problem(name, 2, num_var, lower, upper, evaluate, lambda x: default_repair(x, lower, upper), pf)


def build_dtlz(name: str, dimension: int | None = None, objectives: int | None = None) -> Problem:
    problem_id = int(name[4:])
    num_obj = objectives if objectives is not None else 3
    default_dim = 7 if problem_id == 1 and num_obj == 3 else (22 if problem_id == 7 and num_obj == 3 else num_obj + 9)
    num_var = dimension if dimension is not None else default_dim
    lower = np.zeros(num_var)
    upper = np.ones(num_var)

    def evaluate(x: Array) -> Array:
        m = num_obj
        if problem_id == 1:
            k = num_var - m + 1
            xm = x[-k:]
            g = 100.0 * (k + np.sum((xm - 0.5) ** 2 - np.cos(20.0 * math.pi * (xm - 0.5))))
            f = np.full(m, 0.5 * (1.0 + g))
            for i in range(m):
                for j in range(m - i - 1):
                    f[i] *= x[j]
                if i > 0:
                    f[i] *= 1.0 - x[m - i - 1]
            return f
        if problem_id in {2, 3, 4, 5, 6}:
            k = num_var - m + 1
            xm = x[-k:]
            if problem_id == 3:
                g = 100.0 * (k + np.sum((xm - 0.5) ** 2 - np.cos(20.0 * math.pi * (xm - 0.5))))
            elif problem_id == 6:
                g = np.sum(xm**0.1)
            else:
                g = np.sum((xm - 0.5) ** 2)
            if problem_id in {5, 6}:
                theta = np.empty(m - 1)
                theta[0] = x[0] * math.pi / 2.0
                theta[1:] = math.pi / (4.0 * (1.0 + g)) * (1.0 + 2.0 * g * x[1 : m - 1])
            else:
                alpha = 100.0 if problem_id == 4 else 1.0
                theta = (x[: m - 1] ** alpha) * math.pi / 2.0
            f = np.full(m, 1.0 + g)
            for i in range(m):
                for j in range(m - i - 1):
                    f[i] *= math.cos(theta[j])
                if i > 0:
                    f[i] *= math.sin(theta[m - i - 1])
            return f
        if problem_id == 7:
            k = num_var - m + 1
            f = np.empty(m)
            f[: m - 1] = x[: m - 1]
            g = 1.0 + 9.0 * np.sum(x[-k:]) / k
            h = m - np.sum((f[: m - 1] / (1.0 + g)) * (1.0 + np.sin(3.0 * math.pi * f[: m - 1])))
            f[-1] = (1.0 + g) * h
            return f
        raise ValueError(name)

    def pf(count: int) -> Array:
        if problem_id == 1:
            return uniform_simplex_points(count, num_obj, 0.5)
        if problem_id in {2, 3, 4}:
            return sphere_front(count, num_obj)
        if problem_id in {5, 6} and num_obj == 3:
            x = np.linspace(0.0, 1.0, count)
            theta = x * math.pi / 2.0
            fixed = math.pi / 4.0
            return np.column_stack((np.cos(theta) * math.cos(fixed), np.cos(theta) * math.sin(fixed), np.sin(theta)))
        if problem_id == 7:
            pts = uniform_simplex_points(count, num_obj - 1, 1.0)
            g = 1.0
            h = num_obj - np.sum((pts / (1.0 + g)) * (1.0 + np.sin(3.0 * math.pi * pts)), axis=1)
            return np.column_stack((pts, (1.0 + g) * h))
        return sphere_front(count, num_obj)

    return Problem(name, num_obj, num_var, lower, upper, evaluate, lambda x: default_repair(x, lower, upper), pf)


def build_uf(name: str, dimension: int | None = None) -> Problem:
    problem_id = int(name[2:])
    num_var = dimension if dimension is not None else 30
    num_obj = 3 if problem_id in {8, 9, 10} else 2
    lower = np.full(num_var, -1.0)
    upper = np.full(num_var, 1.0)
    lower[0] = 0.0
    upper[0] = 1.0
    if problem_id == 3:
        lower[1:] = 0.0
        upper[1:] = 1.0
    elif problem_id == 4:
        lower[1:] = -2.0
        upper[1:] = 2.0
    elif problem_id in {8, 9, 10}:
        lower[1] = 0.0
        upper[1] = 1.0
        lower[2:] = -2.0
        upper[2:] = 2.0

    def evaluate(x: Array) -> Array:
        if problem_id <= 7:
            return evaluate_uf_2obj(problem_id, x)
        return evaluate_uf_3obj(problem_id, x)

    return Problem(name, num_obj, num_var, lower, upper, evaluate, lambda x: default_repair(x, lower, upper), lambda count: uf_pareto_front(problem_id, count))


def evaluate_uf_2obj(problem_id: int, x: Array) -> Array:
    n = len(x)
    j = np.arange(2, n + 1)
    if problem_id == 2:
        carrier = 0.3 * x[0] ** 2 * np.cos(24.0 * math.pi * x[0] + 4.0 * j * math.pi / n) + 0.6 * x[0]
        y = x[1:] - carrier * np.where(j % 2 == 1, np.cos(6.0 * math.pi * x[0] + j * math.pi / n), np.sin(6.0 * math.pi * x[0] + j * math.pi / n))
    elif problem_id == 3:
        y = x[1:] - x[0] ** (0.5 * (1.0 + 3.0 * (j - 2.0) / (n - 2.0)))
    else:
        y = x[1:] - np.sin(6.0 * math.pi * x[0] + j * math.pi / n)
    odd = y[(j % 2) == 1]
    even = y[(j % 2) == 0]
    if problem_id in {1, 2}:
        return np.array([x[0] + 2.0 * np.sum(odd**2) / len(odd), 1.0 - math.sqrt(x[0]) + 2.0 * np.sum(even**2) / len(even)])
    if problem_id == 3:
        odd_j = j[(j % 2) == 1]
        even_j = j[(j % 2) == 0]
        odd_term = 4.0 * np.sum(odd**2) - 2.0 * np.prod(np.cos(20.0 * odd * math.pi / np.sqrt(odd_j))) + 2.0
        even_term = 4.0 * np.sum(even**2) - 2.0 * np.prod(np.cos(20.0 * even * math.pi / np.sqrt(even_j))) + 2.0
        return np.array([x[0] + 2.0 * odd_term / len(odd), 1.0 - math.sqrt(x[0]) + 2.0 * even_term / len(even)])
    if problem_id == 4:
        h_odd = np.abs(odd) / (1.0 + np.exp(2.0 * np.abs(odd)))
        h_even = np.abs(even) / (1.0 + np.exp(2.0 * np.abs(even)))
        return np.array([x[0] + 2.0 * np.sum(h_odd) / len(odd), 1.0 - x[0] ** 2 + 2.0 * np.sum(h_even) / len(even)])
    if problem_id == 5:
        n_param, eps = 10, 0.1
        bump = (0.5 / n_param + eps) * abs(math.sin(2.0 * n_param * math.pi * x[0]))
        h_odd = 2.0 * odd**2 - np.cos(4.0 * math.pi * odd) + 1.0
        h_even = 2.0 * even**2 - np.cos(4.0 * math.pi * even) + 1.0
        return np.array([x[0] + bump + 2.0 * np.sum(h_odd) / len(odd), 1.0 - x[0] + bump + 2.0 * np.sum(h_even) / len(even)])
    if problem_id == 6:
        n_param, eps = 2, 0.1
        bump = max(0.0, 2.0 * (0.5 / n_param + eps) * math.sin(2.0 * n_param * math.pi * x[0]))
        odd_j = j[(j % 2) == 1]
        even_j = j[(j % 2) == 0]
        odd_term = 4.0 * np.sum(odd**2) - 2.0 * np.prod(np.cos(20.0 * odd * math.pi / np.sqrt(odd_j))) + 2.0
        even_term = 4.0 * np.sum(even**2) - 2.0 * np.prod(np.cos(20.0 * even * math.pi / np.sqrt(even_j))) + 2.0
        return np.array([x[0] + bump + 2.0 * odd_term / len(odd), 1.0 - x[0] + bump + 2.0 * even_term / len(even)])
    if problem_id == 7:
        y0 = x[0] ** 0.2
        return np.array([y0 + 2.0 * np.sum(odd**2) / len(odd), 1.0 - y0 + 2.0 * np.sum(even**2) / len(even)])
    raise ValueError(f"UF{problem_id}")


def evaluate_uf_3obj(problem_id: int, x: Array) -> Array:
    n = len(x)
    f = np.empty(3)
    for group, start in enumerate((3, 4, 2)):
        idx = np.arange(start, n, 3)
        j = idx + 1
        y = x[idx] - 2.0 * x[1] * np.sin(2.0 * math.pi * x[0] + j * math.pi / n)
        contribution = np.sum(4.0 * y * y - np.cos(8.0 * math.pi * y) + 1.0) if problem_id == 10 else np.sum(y * y)
        if group == 0:
            if problem_id == 9:
                t = max(0.0, 1.1 * (1.0 - 4.0 * (2.0 * x[0] - 1.0) ** 2))
                base = 0.5 * (t + 2.0 * x[0]) * x[1]
            else:
                base = math.cos(0.5 * math.pi * x[0]) * math.cos(0.5 * math.pi * x[1])
        elif group == 1:
            if problem_id == 9:
                t = max(0.0, 1.1 * (1.0 - 4.0 * (2.0 * x[0] - 1.0) ** 2))
                base = 0.5 * (t - 2.0 * x[0] + 2.0) * x[1]
            else:
                base = math.cos(0.5 * math.pi * x[0]) * math.sin(0.5 * math.pi * x[1])
        else:
            base = 1.0 - x[1] if problem_id == 9 else math.sin(0.5 * math.pi * x[0])
        f[group] = base + 2.0 * contribution / max(1, len(idx))
    return f


def uf_pareto_front(problem_id: int, count: int) -> Array:
    x = np.linspace(0.0, 1.0, count)
    if problem_id in {1, 2, 3}:
        return np.column_stack((x, 1.0 - np.sqrt(x)))
    if problem_id == 4:
        return np.column_stack((x, 1.0 - x**2))
    if problem_id == 5:
        xs = np.linspace(0.0, 1.0, min(count, 21))
        return np.column_stack((xs, 1.0 - xs))
    if problem_id == 6:
        first = np.linspace(0.25, 0.5, max(2, count // 2))
        second = np.linspace(0.75, 1.0, max(2, count // 2))
        xs = np.concatenate(([0.0], first, second))[:count]
        return np.column_stack((xs, 1.0 - xs))
    if problem_id == 7:
        return np.column_stack((x, 1.0 - x))
    if problem_id in {8, 10}:
        return sphere_front(count, 3)
    if problem_id == 9:
        base = uniform_simplex_points(count * 4, 3, 1.0)
        keep = (4.0 * base[:, 0] < 1.0 - base[:, 2]) | (4.0 * base[:, 0] > 3.0 * (1.0 - base[:, 2]))
        filtered = base[keep]
        return filtered[:count] if len(filtered) >= count else filtered
    raise ValueError(f"UF{problem_id}")


def parse_numeric_line(line: str) -> list[float]:
    return [float(x) for x in re.findall(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", line)]


def build_returns_csv_problem(path: Path, cardinality: int | None = None) -> Problem:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    numeric_rows: list[list[float]] = []
    for row in rows:
        vals: list[float] = []
        for cell in row:
            try:
                vals.append(float(cell))
            except ValueError:
                pass
        if vals:
            numeric_rows.append(vals)
    data = np.asarray(numeric_rows, dtype=float)
    if data.ndim != 2 or min(data.shape) < 2:
        raise ValueError(f"Could not parse returns matrix from {path}")
    mean = np.mean(data, axis=0)
    cov = np.cov(data, rowvar=False)
    return build_portfolio_problem(path.stem, mean, cov, cardinality)


def build_orlibrary_problem(path: Path, cardinality: int | None = None) -> Problem:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    numeric_lines = [parse_numeric_line(line) for line in lines]
    numeric_lines = [line for line in numeric_lines if line]
    if not numeric_lines:
        raise ValueError(f"No numeric data found in {path}")
    n = int(round(numeric_lines[0][0]))
    asset_lines = numeric_lines[1 : 1 + n]
    tail_lines = numeric_lines[1 + n :]
    mean = np.zeros(n, dtype=float)
    for i, nums in enumerate(asset_lines):
        if len(nums) >= 2 and int(round(nums[0])) == i + 1:
            mean[i] = nums[1]
        else:
            mean[i] = nums[0]

    cov = np.zeros((n, n), dtype=float)
    tail_flat = np.asarray([v for line in tail_lines for v in line], dtype=float)
    if tail_lines and all(len(line) >= 3 and 1 <= int(round(line[0])) <= n and 1 <= int(round(line[1])) <= n for line in tail_lines):
        for line in tail_lines:
            i = int(round(line[0])) - 1
            j = int(round(line[1])) - 1
            value = float(line[2])
            cov[i, j] = value
            cov[j, i] = value
    elif tail_flat.size >= n * n:
        cov = tail_flat[: n * n].reshape(n, n)
    else:
        all_nums = np.asarray([v for line in numeric_lines[1:] for v in line], dtype=float)
        if all_nums.size == n + n * n:
            mean = all_nums[:n]
            cov = all_nums[n : n + n * n].reshape(n, n)
        elif all_nums.size >= 2 * n + n * n:
            first = all_nums[: 2 * n].reshape(n, 2)
            if np.allclose(first[:, 0], np.arange(1, n + 1)):
                mean = first[:, 1]
            cov = all_nums[2 * n : 2 * n + n * n].reshape(n, n)
        else:
            raise ValueError(f"Could not infer OR-Library covariance format from {path}")

    cov = 0.5 * (cov + cov.T)
    return build_portfolio_problem(path.stem, mean, cov, cardinality)


def build_portfolio_problem(name: str, mean: Array, cov: Array, cardinality: int | None = None) -> Problem:
    n = len(mean)
    cov = np.asarray(cov, dtype=float)
    lower = np.zeros(n)
    upper = np.ones(n)

    def evaluate(w: Array) -> Array:
        weights = repair(w)
        risk = float(weights @ cov @ weights)
        ret = float(weights @ mean)
        return np.array([risk, -ret], dtype=float)

    def repair(x: Array) -> Array:
        if cardinality is not None and cardinality > 0:
            return cardinality_simplex_repair(x, lower, upper, cardinality)
        return simplex_repair(x, lower, upper)

    suffix = f"_K{cardinality}" if cardinality is not None and cardinality > 0 else ""
    return Problem(f"PORTFOLIO_{name}{suffix}", 2, n, lower, upper, evaluate, repair, None)


def igd(approximation: Array, reference: Array) -> float:
    if len(approximation) == 0 or len(reference) == 0:
        return float("nan")
    return float(np.mean([np.min(np.linalg.norm(approximation - p, axis=1)) for p in reference]))


def save_outputs(out_dir: Path, problem: Problem, result: ECMADEMOOResult, pf_samples: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savetxt(out_dir / f"{problem.name}_population_variables.csv", result.variables, delimiter=",")
    np.savetxt(out_dir / f"{problem.name}_population_objectives.csv", result.objectives, delimiter=",")
    np.savetxt(out_dir / f"{problem.name}_pareto_variables.csv", result.pareto_variables, delimiter=",")
    np.savetxt(out_dir / f"{problem.name}_pareto_objectives.csv", result.pareto_objectives, delimiter=",")
    with (out_dir / f"{problem.name}_history.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["generation", "evaluations", "nondominated", "archive_size", "stagnation", "exchanges"])
        writer.writeheader()
        writer.writerows(result.history)
    if problem.pareto_front is not None:
        ref = problem.pareto_front(pf_samples)
        np.savetxt(out_dir / f"{problem.name}_reference_front.csv", ref, delimiter=",")
        metric = igd(result.pareto_objectives, ref)
        (out_dir / f"{problem.name}_metrics.txt").write_text(f"evaluations={result.evaluations}\npareto_size={len(result.pareto_objectives)}\nigd={metric:.12g}\n", encoding="utf-8")
    else:
        (out_dir / f"{problem.name}_metrics.txt").write_text(f"evaluations={result.evaluations}\npareto_size={len(result.pareto_objectives)}\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ECMADE-MOO on OR-Library portfolio data or UF/DTLZ/ZDT benchmarks.")
    parser.add_argument("--problem", default="ZDT1", help="ZDT1-4/ZDT6, DTLZ1-7, UF1-10, ORLIB, or PORTFOLIO")
    parser.add_argument("--problems", nargs="+", help="Optional batch list, e.g. --problems ZDT1 DTLZ2 UF1")
    parser.add_argument("--orlib-path", type=Path, help="OR-Library-style portfolio file path")
    parser.add_argument("--returns-csv", type=Path, help="CSV of asset returns, one asset per column")
    parser.add_argument("--cardinality", type=int, help="Portfolio cardinality constraint K. This is a problem constraint, not an algorithm-tuning profile.")
    parser.add_argument("--dimension", type=int, help="Decision-variable dimension")
    parser.add_argument("--objectives", type=int, help="Number of objectives for DTLZ")
    parser.add_argument("--pop-size", type=int, default=100)
    parser.add_argument("--max-fe", type=int, default=10000)
    parser.add_argument("--subpops", type=int, default=3)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--stability-profile", choices=["none", "paper-stable", "robust"], default="none", help="Optional global stability preset; baseline is unchanged when set to none.")
    parser.add_argument("--enable-consensus-archive", action="store_true", help="Enable experimental consensus archive pruning.")
    parser.add_argument("--consensus-bins", type=int, default=24, help="Objective-space grid bins used for consensus-front scoring.")
    parser.add_argument("--archive-consensus-weight", type=float, help="Archive pruning score weight for consensus; remaining weight uses crowding distance.")
    parser.add_argument("--best-guide", choices=["rank", "ideal", "reference", "consensus"], help="MOO definition of x_best for ECMADE mutation formulas.")
    parser.add_argument("--min-subpop-size", type=int, help="Minimum survivors retained per subpopulation after environmental selection.")
    parser.add_argument("--f-scale", type=float, help="Scale of Cauchy perturbation for F; paper default is 0.1.")
    parser.add_argument("--cr-scale", type=float, help="Scale of normal perturbation for CR; paper default is 0.1.")
    parser.add_argument("--f-max", type=float, help="Upper bound for sampled and adapted F; paper default is 1.0.")
    parser.add_argument("--exchange-mode", choices=["paper", "stable"], help="paper re-divides subpopulations; stable keeps subpopulation roles during elite exchange.")
    parser.add_argument("--out-dir", type=Path, default=Path("ecmade_moo_outputs"))
    parser.add_argument("--pf-samples", type=int, default=10000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.stability_profile == "paper-stable":
        profile_best_guide = "ideal"
        profile_consensus_archive = False
        profile_archive_consensus_weight = 0.0
        profile_min_subpop_size = 1
        profile_f_scale = 0.1
        profile_cr_scale = 0.1
        profile_f_max = 1.0
        profile_exchange_mode = "paper"
    elif args.stability_profile == "robust":
        profile_best_guide = "reference"
        profile_consensus_archive = True
        profile_archive_consensus_weight = 0.25
        profile_min_subpop_size = 6
        profile_f_scale = 0.05
        profile_cr_scale = 0.05
        profile_f_max = 0.7
        profile_exchange_mode = "stable"
    else:
        profile_best_guide = "rank"
        profile_consensus_archive = True
        profile_archive_consensus_weight = 0.10
        profile_min_subpop_size = 6
        profile_f_scale = 0.1
        profile_cr_scale = 0.1
        profile_f_max = 1.0
        profile_exchange_mode = "paper"
    names = args.problems if args.problems else [args.problem]
    for name in names:
        problem = build_problem(name, args.dimension, args.objectives, args)
        cfg = ECMADEMOOConfig(
            pop_size=args.pop_size,
            max_fe=args.max_fe,
            subpops=args.subpops,
            seed=args.seed,
            f_scale=args.f_scale if args.f_scale is not None else profile_f_scale,
            cr_scale=args.cr_scale if args.cr_scale is not None else profile_cr_scale,
            f_max=args.f_max if args.f_max is not None else profile_f_max,
            exchange_mode=args.exchange_mode if args.exchange_mode is not None else profile_exchange_mode,
            consensus_archive=args.enable_consensus_archive or profile_consensus_archive,
            consensus_bins=args.consensus_bins,
            archive_consensus_weight=args.archive_consensus_weight if args.archive_consensus_weight is not None else profile_archive_consensus_weight,
            best_guide=args.best_guide if args.best_guide is not None else profile_best_guide,
            min_subpop_size=args.min_subpop_size if args.min_subpop_size is not None else profile_min_subpop_size,
        )
        result = ECMADEMOO(problem, cfg).run()
        save_outputs(args.out_dir, problem, result, args.pf_samples)
        metric_text = ""
        if problem.pareto_front is not None:
            metric_text = f", IGD={igd(result.pareto_objectives, problem.pareto_front(args.pf_samples)):.6e}"
        print(f"{problem.name}: FE={result.evaluations}, PF size={len(result.pareto_objectives)}{metric_text}")
        print(f"  outputs: {args.out_dir.resolve()}")


if __name__ == "__main__":
    main()
