"""A-MPMO reproduction script based on Zhao et al. (2025).

The paper uses PlatEMO/MATLAB.  This Python version implements the published
A-MPMO framework with NSGA-II environmental selection, SBX crossover, and
polynomial mutation so the experiment can be rerun from this workspace.
"""

from __future__ import annotations

import argparse
import csv
import math
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
    pareto_front: Callable[[int], Array]


@dataclass(frozen=True)
class AMPMOConfig:
    population_size: int = 100
    max_evaluations: int = 10000
    runs: int = 30
    subpopulations: int = 3
    beta: float = 0.2
    delta: float = 0.05
    eta_c: float = 20.0
    eta_m: float = 20.0
    seed: int = 2025
    pf_samples: int = 10000
    parameter_groups: tuple[tuple[float, float], ...] = ((1.0, 0.5), (1.0, 1.0), (0.5, 1.0))


TABLE3_PROBLEMS = [
    "DTLZ1",
    "DTLZ2",
    "DTLZ3",
    "DTLZ4",
    "DTLZ5",
    "DTLZ6",
    "DTLZ7",
    "ZDT1",
    "ZDT2",
    "ZDT3",
    "ZDT4",
    "ZDT6",
    "UF1",
    "UF2",
    "UF3",
    "UF4",
    "UF5",
    "UF6",
    "UF7",
    "UF8",
    "UF9",
    "UF10",
]


def dominates(a: Array, b: Array) -> bool:
    return bool(np.all(a <= b) and np.any(a < b))


def nondominated_sort(objs: Array) -> list[list[int]]:
    n = len(objs)
    if n == 0:
        return []
    less_equal = np.all(objs[:, None, :] <= objs[None, :, :], axis=2)
    strictly_less = np.any(objs[:, None, :] < objs[None, :, :], axis=2)
    dominates_matrix = less_equal & strictly_less
    dominated_by_count = np.sum(dominates_matrix, axis=0).astype(int)
    dominates_list = [np.where(dominates_matrix[p])[0].tolist() for p in range(n)]
    first = np.where(dominated_by_count == 0)[0].tolist()
    fronts = [first]

    i = 0
    while i < len(fronts) and fronts[i]:
        next_front: list[int] = []
        for p in fronts[i]:
            for q in dominates_list[p]:
                dominated_by_count[q] -= 1
                if dominated_by_count[q] == 0:
                    next_front.append(q)
        if next_front:
            fronts.append(next_front)
        i += 1
    return fronts


def nondominated_sort_slow(objs: Array) -> list[list[int]]:
    n = len(objs)
    dominated_by_count = np.zeros(n, dtype=int)
    dominates_list: list[list[int]] = [[] for _ in range(n)]
    fronts: list[list[int]] = [[]]

    for p in range(n):
        for q in range(p + 1, n):
            if dominates(objs[p], objs[q]):
                dominates_list[p].append(q)
                dominated_by_count[q] += 1
            elif dominates(objs[q], objs[p]):
                dominates_list[q].append(p)
                dominated_by_count[p] += 1
        if dominated_by_count[p] == 0:
            fronts[0].append(p)

    i = 0
    while i < len(fronts) and fronts[i]:
        next_front: list[int] = []
        for p in fronts[i]:
            for q in dominates_list[p]:
                dominated_by_count[q] -= 1
                if dominated_by_count[q] == 0:
                    next_front.append(q)
        if next_front:
            fronts.append(next_front)
        i += 1
    return fronts


def crowding_distance(objs: Array) -> Array:
    n = len(objs)
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
        for i in range(1, n - 1):
            distance[order[i]] += (objs[order[i + 1], m] - objs[order[i - 1], m]) / span
    return distance


def ranks_and_crowding(objs: Array) -> tuple[Array, Array]:
    ranks = np.empty(len(objs), dtype=int)
    crowd = np.empty(len(objs), dtype=float)
    for rank, front in enumerate(nondominated_sort(objs)):
        idx = np.array(front, dtype=int)
        ranks[idx] = rank
        crowd[idx] = crowding_distance(objs[idx])
    return ranks, crowd


def environmental_selection(vars_: Array, objs: Array, skills: Array, target_size: int) -> tuple[Array, Array, Array]:
    chosen_idx = environmental_selection_indices(objs, target_size)
    return vars_[chosen_idx], objs[chosen_idx], skills[chosen_idx]


def environmental_selection_indices(objs: Array, target_size: int) -> Array:
    chosen: list[int] = []
    for front in nondominated_sort(objs):
        if len(chosen) + len(front) <= target_size:
            chosen.extend(front)
            continue
        idx = np.array(front, dtype=int)
        cd = crowding_distance(objs[idx])
        keep = idx[np.argsort(-cd)[: target_size - len(chosen)]]
        chosen.extend(keep.tolist())
        break
    return np.array(chosen, dtype=int)


def environmental_selection_with_skill_floor(
    vars_: Array,
    objs: Array,
    skills: Array,
    target_size: int,
    min_per_skill: int,
    num_skills: int,
) -> tuple[Array, Array, Array]:
    selected = environmental_selection_indices(objs, target_size)
    selected_set = set(selected.tolist())
    counts = np.bincount(skills[selected], minlength=num_skills)
    ranks, crowd = ranks_and_crowding(objs)

    for skill in range(num_skills):
        while counts[skill] < min_per_skill:
            candidates = [idx for idx in np.where(skills == skill)[0].tolist() if idx not in selected_set]
            if not candidates:
                break
            add = min(candidates, key=lambda idx: (ranks[idx], -crowd[idx]))
            replace_candidates = [idx for idx in selected.tolist() if counts[skills[idx]] > min_per_skill]
            if not replace_candidates:
                break
            drop = max(replace_candidates, key=lambda idx: (ranks[idx], -crowd[idx]))
            selected_set.remove(drop)
            selected_set.add(add)
            selected = np.array(list(selected_set), dtype=int)
            counts[skills[drop]] -= 1
            counts[skill] += 1

    order = sorted(selected_set, key=lambda idx: (ranks[idx], -crowd[idx]))[:target_size]
    chosen_idx = np.array(order, dtype=int)
    return vars_[chosen_idx], objs[chosen_idx], skills[chosen_idx]


def tournament_selection(objs: Array, rng: np.random.Generator, count: int) -> Array:
    ranks, crowd = ranks_and_crowding(objs)
    return tournament_selection_by_rank(ranks, crowd, rng, count)


def tournament_selection_by_rank(ranks: Array, crowd: Array, rng: np.random.Generator, count: int) -> Array:
    picks = np.empty(count, dtype=int)
    for i in range(count):
        a, b = rng.integers(0, len(ranks), size=2)
        if ranks[a] < ranks[b] or (ranks[a] == ranks[b] and crowd[a] > crowd[b]):
            picks[i] = a
        else:
            picks[i] = b
    return picks


def sbx_pair(p1: Array, p2: Array, lower: Array, upper: Array, pro_c: float, eta_c: float, rng: np.random.Generator) -> tuple[Array, Array]:
    # PlatEMO OperatorGA-style SBX: proC is the crossover probability for
    # a mating pair, eta_c is the SBX distribution index.
    mu = rng.random(len(p1))
    beta = np.empty(len(p1), dtype=float)
    left = mu <= 0.5
    beta[left] = (2.0 * mu[left]) ** (1.0 / (eta_c + 1.0))
    beta[~left] = (2.0 - 2.0 * mu[~left]) ** (-1.0 / (eta_c + 1.0))
    beta *= np.where(rng.integers(0, 2, size=len(p1)) == 0, -1.0, 1.0)
    beta[rng.random(len(p1)) < 0.5] = 1.0
    if rng.random() > pro_c:
        beta[:] = 1.0
    c1 = 0.5 * (p1 + p2) + 0.5 * beta * (p1 - p2)
    c2 = 0.5 * (p1 + p2) - 0.5 * beta * (p1 - p2)
    return np.clip(c1, lower, upper), np.clip(c2, lower, upper)


def polynomial_mutation(x: Array, lower: Array, upper: Array, pro_m: float, eta_m: float, rng: np.random.Generator) -> Array:
    y = x.copy()
    per_var_probability = pro_m / len(y)
    for j in range(len(y)):
        if rng.random() > per_var_probability:
            continue
        lb, ub = lower[j], upper[j]
        if ub <= lb:
            continue
        delta1 = (y[j] - lb) / (ub - lb)
        delta2 = (ub - y[j]) / (ub - lb)
        rnd = rng.random()
        mut_pow = 1.0 / (eta_m + 1.0)
        if rnd <= 0.5:
            xy = 1.0 - delta1
            val = 2.0 * rnd + (1.0 - 2.0 * rnd) * xy ** (eta_m + 1.0)
            deltaq = val ** mut_pow - 1.0
        else:
            xy = 1.0 - delta2
            val = 2.0 * (1.0 - rnd) + 2.0 * (rnd - 0.5) * xy ** (eta_m + 1.0)
            deltaq = 1.0 - val ** mut_pow
        y[j] = np.clip(y[j] + deltaq * (ub - lb), lb, ub)
    return y


def integer_sizes_from_weights(weights: Array, total: int, min_size: int) -> Array:
    weights = np.maximum(weights, 0.0)
    if np.sum(weights) <= 0.0:
        weights = np.ones_like(weights) / len(weights)
    else:
        weights = weights / np.sum(weights)
    raw = np.maximum(weights * total, min_size)
    sizes = np.floor(raw).astype(int)
    remainder = total - int(np.sum(sizes))
    fractions = raw - np.floor(raw)
    if remainder > 0:
        for idx in np.argsort(-fractions)[:remainder]:
            sizes[idx] += 1
    while remainder < 0:
        candidates = np.where(sizes > min_size)[0]
        idx = candidates[np.argmax(sizes[candidates] - raw[candidates])]
        sizes[idx] -= 1
        remainder += 1
    return sizes


class AMPMO:
    def __init__(self, problem: Problem, config: AMPMOConfig):
        self.problem = problem
        self.config = config

    def run(self, seed: int) -> dict[str, object]:
        cfg = self.config
        rng = np.random.default_rng(seed)
        sizes = integer_sizes_from_weights(np.ones(cfg.subpopulations), cfg.population_size, 1)
        sub_vars = []
        sub_objs = []
        sub_skills = []
        evaluations = 0
        for skill, size in enumerate(sizes):
            vars_ = rng.uniform(self.problem.lower, self.problem.upper, size=(size, self.problem.num_var))
            objs = np.asarray([self.problem.evaluate(x) for x in vars_])
            sub_vars.append(vars_)
            sub_objs.append(objs)
            sub_skills.append(np.full(size, skill, dtype=int))
            evaluations += size

        history: list[dict[str, object]] = []
        early_budget = cfg.beta * cfg.max_evaluations
        generation = 0
        while evaluations < cfg.max_evaluations:
            generation += 1
            all_skills = np.concatenate(sub_skills)
            contribution = np.bincount(all_skills, minlength=cfg.subpopulations) / cfg.population_size
            if evaluations < early_budget:
                target_sizes = integer_sizes_from_weights(np.ones(cfg.subpopulations), cfg.population_size, 1)
                phase = "early"
                new_vars = []
                new_objs = []
                new_skills = []
                parent_objs_all = np.vstack(sub_objs)
                parent_skills_all = np.concatenate(sub_skills)
                global_ranks, global_crowd = ranks_and_crowding(parent_objs_all)
                for skill in range(cfg.subpopulations):
                    pro_c, pro_m = cfg.parameter_groups[skill % len(cfg.parameter_groups)]
                    mask = parent_skills_all == skill
                    offspring = self._offspring(
                        sub_vars[skill],
                        sub_objs[skill],
                        target_sizes[skill],
                        pro_c,
                        pro_m,
                        rng,
                        parent_ranks=global_ranks[mask],
                        parent_crowd=global_crowd[mask],
                    )
                    remaining = cfg.max_evaluations - evaluations
                    if len(offspring) > remaining:
                        offspring = offspring[:remaining]
                    off_objs = np.asarray([self.problem.evaluate(x) for x in offspring])
                    evaluations += len(offspring)
                    off_skills = np.full(len(offspring), skill, dtype=int)
                    pool_vars = np.vstack((sub_vars[skill], offspring))
                    pool_objs = np.vstack((sub_objs[skill], off_objs))
                    pool_skills = np.concatenate((sub_skills[skill], off_skills))
                    keep_size = min(target_sizes[skill], len(pool_vars))
                    vars_i, objs_i, skills_i = environmental_selection(pool_vars, pool_objs, pool_skills, keep_size)
                    new_vars.append(vars_i)
                    new_objs.append(objs_i)
                    new_skills.append(skills_i)
                    if evaluations >= cfg.max_evaluations:
                        break

                sub_vars, sub_objs, sub_skills = self._rebalance(new_vars, new_objs, new_skills, rng)
            else:
                target_sizes = integer_sizes_from_weights(contribution, cfg.population_size, max(1, int(math.ceil(cfg.population_size * cfg.delta))))
                phase = "later"
                off_vars = []
                off_objs = []
                off_skills = []
                parent_objs_all = np.vstack(sub_objs)
                parent_skills_all = np.concatenate(sub_skills)
                global_ranks, global_crowd = ranks_and_crowding(parent_objs_all)
                for skill in range(cfg.subpopulations):
                    pro_c, pro_m = cfg.parameter_groups[skill % len(cfg.parameter_groups)]
                    mask = parent_skills_all == skill
                    offspring = self._offspring(
                        sub_vars[skill],
                        sub_objs[skill],
                        target_sizes[skill],
                        pro_c,
                        pro_m,
                        rng,
                        parent_ranks=global_ranks[mask],
                        parent_crowd=global_crowd[mask],
                    )
                    remaining = cfg.max_evaluations - evaluations
                    if len(offspring) > remaining:
                        offspring = offspring[:remaining]
                    objs_i = np.asarray([self.problem.evaluate(x) for x in offspring])
                    evaluations += len(offspring)
                    off_vars.append(offspring)
                    off_objs.append(objs_i)
                    off_skills.append(np.full(len(offspring), skill, dtype=int))
                    if evaluations >= cfg.max_evaluations:
                        break

                parent_vars = np.vstack(sub_vars)
                parent_objs = np.vstack(sub_objs)
                parent_skills = np.concatenate(sub_skills)
                pool_vars = np.vstack([parent_vars] + [v for v in off_vars if len(v)])
                pool_objs = np.vstack([parent_objs] + [o for o in off_objs if len(o)])
                pool_skills = np.concatenate([parent_skills] + [s for s in off_skills if len(s)])
                vars_all, objs_all, skills_all = environmental_selection_with_skill_floor(
                    pool_vars,
                    pool_objs,
                    pool_skills,
                    cfg.population_size,
                    max(1, int(math.ceil(cfg.population_size * cfg.delta))),
                    cfg.subpopulations,
                )
                sub_vars, sub_objs, sub_skills = [], [], []
                for skill in range(cfg.subpopulations):
                    mask = skills_all == skill
                    sub_vars.append(vars_all[mask])
                    sub_objs.append(objs_all[mask])
                    sub_skills.append(skills_all[mask])
            history.append({"generation": generation, "evaluations": evaluations, "phase": phase, "sizes": [len(v) for v in sub_vars]})

        vars_all = np.vstack(sub_vars)
        objs_all = np.vstack(sub_objs)
        skills_all = np.concatenate(sub_skills)
        vars_all, objs_all, skills_all = environmental_selection(vars_all, objs_all, skills_all, cfg.population_size)
        pf = self.problem.pareto_front(cfg.pf_samples)
        nd = objs_all[np.array([not any(dominates(objs_all[j], objs_all[i]) for j in range(len(objs_all)) if j != i) for i in range(len(objs_all))])]
        return {
            "objectives": objs_all,
            "variables": vars_all,
            "skills": skills_all,
            "igd": igd(nd, pf),
            "hv": hypervolume_2d(nd, np.array([1.1, 1.1])) if self.problem.num_obj == 2 else float("nan"),
            "history": history,
        }

    def _offspring(
        self,
        vars_: Array,
        objs: Array,
        target_size: int,
        pro_c: float,
        pro_m: float,
        rng: np.random.Generator,
        parent_ranks: Array | None = None,
        parent_crowd: Array | None = None,
    ) -> Array:
        if len(vars_) == 0:
            vars_ = rng.uniform(self.problem.lower, self.problem.upper, size=(2, self.problem.num_var))
            objs = np.asarray([self.problem.evaluate(x) for x in vars_])
            parent_ranks = None
            parent_crowd = None
        if len(vars_) == 1:
            vars_ = np.vstack((vars_, rng.uniform(self.problem.lower, self.problem.upper, size=self.problem.num_var)))
            objs = np.vstack((objs, self.problem.evaluate(vars_[-1])))
            parent_ranks = None
            parent_crowd = None
        parent_count = max(2, 2 * math.ceil(target_size / 2))
        if parent_ranks is not None and parent_crowd is not None and len(parent_ranks) == len(vars_):
            parents = tournament_selection_by_rank(parent_ranks, parent_crowd, rng, parent_count)
        else:
            parents = tournament_selection(objs, rng, parent_count)
        children = []
        for a, b in parents.reshape(-1, 2):
            c1, c2 = sbx_pair(vars_[a], vars_[b], self.problem.lower, self.problem.upper, pro_c, self.config.eta_c, rng)
            children.append(polynomial_mutation(c1, self.problem.lower, self.problem.upper, pro_m, self.config.eta_m, rng))
            if len(children) < target_size:
                children.append(polynomial_mutation(c2, self.problem.lower, self.problem.upper, pro_m, self.config.eta_m, rng))
        return np.asarray(children[:target_size])

    def _rebalance(self, vars_list: list[Array], objs_list: list[Array], skills_list: list[Array], rng: np.random.Generator) -> tuple[list[Array], list[Array], list[Array]]:
        missing = self.config.subpopulations - len(vars_list)
        for _ in range(missing):
            vars_list.append(np.empty((0, self.problem.num_var)))
            objs_list.append(np.empty((0, self.problem.num_obj)))
            skills_list.append(np.empty((0,), dtype=int))
        total = sum(len(v) for v in vars_list)
        if total == self.config.population_size:
            return vars_list, objs_list, skills_list
        all_vars = np.vstack([v for v in vars_list if len(v)])
        all_objs = np.vstack([o for o in objs_list if len(o)])
        all_skills = np.concatenate([s for s in skills_list if len(s)])
        all_vars, all_objs, all_skills = environmental_selection(all_vars, all_objs, all_skills, self.config.population_size)
        rebuilt_vars, rebuilt_objs, rebuilt_skills = [], [], []
        for skill in range(self.config.subpopulations):
            mask = all_skills == skill
            rebuilt_vars.append(all_vars[mask])
            rebuilt_objs.append(all_objs[mask])
            rebuilt_skills.append(all_skills[mask])
        _ = rng
        return rebuilt_vars, rebuilt_objs, rebuilt_skills


class NSGAII:
    def __init__(self, problem: Problem, config: AMPMOConfig):
        self.problem = problem
        self.config = config

    def run(self, seed: int) -> dict[str, object]:
        cfg = self.config
        rng = np.random.default_rng(seed)
        vars_ = rng.uniform(self.problem.lower, self.problem.upper, size=(cfg.population_size, self.problem.num_var))
        objs = np.asarray([self.problem.evaluate(x) for x in vars_])
        skills = np.zeros(cfg.population_size, dtype=int)
        evaluations = cfg.population_size

        while evaluations < cfg.max_evaluations:
            offspring = self._offspring(vars_, objs, cfg.population_size, rng)
            remaining = cfg.max_evaluations - evaluations
            if len(offspring) > remaining:
                offspring = offspring[:remaining]
            off_objs = np.asarray([self.problem.evaluate(x) for x in offspring])
            evaluations += len(offspring)

            pool_vars = np.vstack((vars_, offspring))
            pool_objs = np.vstack((objs, off_objs))
            pool_skills = np.zeros(len(pool_vars), dtype=int)
            vars_, objs, skills = environmental_selection(pool_vars, pool_objs, pool_skills, cfg.population_size)

        pf = self.problem.pareto_front(cfg.pf_samples)
        nd = objs[np.array([not any(dominates(objs[j], objs[i]) for j in range(len(objs)) if j != i) for i in range(len(objs))])]
        return {
            "objectives": objs,
            "variables": vars_,
            "skills": skills,
            "igd": igd(nd, pf),
            "hv": hypervolume_2d(nd, np.array([1.1, 1.1])) if self.problem.num_obj == 2 else float("nan"),
        }

    def _offspring(self, vars_: Array, objs: Array, target_size: int, rng: np.random.Generator) -> Array:
        parent_count = max(2, 2 * math.ceil(target_size / 2))
        parents = tournament_selection(objs, rng, parent_count)
        children = []
        for a, b in parents.reshape(-1, 2):
            c1, c2 = sbx_pair(vars_[a], vars_[b], self.problem.lower, self.problem.upper, 1.0, self.config.eta_c, rng)
            children.append(polynomial_mutation(c1, self.problem.lower, self.problem.upper, 1.0, self.config.eta_m, rng))
            if len(children) < target_size:
                children.append(polynomial_mutation(c2, self.problem.lower, self.problem.upper, 1.0, self.config.eta_m, rng))
        return np.asarray(children[:target_size])


def igd(approximation: Array, reference: Array) -> float:
    if len(approximation) == 0:
        return float("inf")
    return float(np.mean([np.min(np.linalg.norm(approximation - p, axis=1)) for p in reference]))


def hypervolume_2d(points: Array, reference: Array) -> float:
    nd = points[np.array([not any(dominates(points[j], points[i]) for j in range(len(points)) if i != j) for i in range(len(points))])]
    nd = nd[np.all(nd <= reference, axis=1)]
    if len(nd) == 0:
        return 0.0
    nd = nd[np.argsort(nd[:, 0])]
    hv = 0.0
    prev_f2 = reference[1]
    for f1, f2 in nd:
        hv += max(0.0, reference[0] - f1) * max(0.0, prev_f2 - f2)
        prev_f2 = min(prev_f2, f2)
    return float(hv)


def uniform_simplex_points(n: int, m: int, total: float = 1.0) -> Array:
    rng = np.random.default_rng(12345 + m + n)
    pts = rng.dirichlet(np.ones(m), size=n) * total
    return pts


def sphere_front(n: int, m: int) -> Array:
    pts = uniform_simplex_points(n, m, 1.0)
    pts = pts / np.linalg.norm(pts, axis=1, keepdims=True)
    return pts


def build_problem(name: str) -> Problem:
    n = name.upper()
    if n.startswith("ZDT"):
        return build_zdt(n)
    if n.startswith("DTLZ"):
        return build_dtlz(n)
    if n.startswith("UF"):
        return build_uf(n)
    raise ValueError(f"Unsupported problem: {name}. Supported: DTLZ1-7, ZDT1-4/ZDT6, UF1-10.")


def build_zdt(name: str) -> Problem:
    num_var = 10 if name in {"ZDT4", "ZDT6"} else 30
    lower = np.zeros(num_var)
    upper = np.ones(num_var)
    if name == "ZDT4":
        lower[1:] = -5.0
        upper[1:] = 5.0

    def evaluate(x: Array) -> Array:
        f1 = x[0]
        if name == "ZDT1":
            g = 1.0 + 9.0 * np.sum(x[1:]) / (num_var - 1)
            h = 1.0 - math.sqrt(f1 / g)
        elif name == "ZDT2":
            g = 1.0 + 9.0 * np.sum(x[1:]) / (num_var - 1)
            h = 1.0 - (f1 / g) ** 2
        elif name == "ZDT3":
            g = 1.0 + 9.0 * np.sum(x[1:]) / (num_var - 1)
            h = 1.0 - math.sqrt(f1 / g) - (f1 / g) * math.sin(10.0 * math.pi * f1)
        elif name == "ZDT4":
            g = 1.0 + 10.0 * (num_var - 1) + np.sum(x[1:] ** 2 - 10.0 * np.cos(4.0 * math.pi * x[1:]))
            h = 1.0 - math.sqrt(f1 / g)
        elif name == "ZDT6":
            f1 = 1.0 - math.exp(-4.0 * x[0]) * (math.sin(6.0 * math.pi * x[0]) ** 6)
            g = 1.0 + 9.0 * (np.sum(x[1:]) / (num_var - 1)) ** 0.25
            h = 1.0 - (f1 / g) ** 2
        else:
            raise ValueError(name)
        return np.array([f1, g * h])

    def pf(count: int) -> Array:
        x = np.linspace(0.0, 1.0, count)
        if name in {"ZDT1", "ZDT4"}:
            return np.column_stack((x, 1.0 - np.sqrt(x)))
        if name == "ZDT2":
            return np.column_stack((x, 1.0 - x**2))
        if name == "ZDT3":
            segments = np.array(
                [
                    [0.0, 0.0830015349],
                    [0.1822287280, 0.2577623634],
                    [0.4093136748, 0.4538821041],
                    [0.6183967944, 0.6525117038],
                    [0.8233317983, 0.8518328654],
                ]
            )
            per_segment = max(2, math.ceil(count / len(segments)))
            xs = np.concatenate([np.linspace(lo, hi, per_segment) for lo, hi in segments])[:count]
            return np.column_stack((xs, 1.0 - np.sqrt(xs) - xs * np.sin(10.0 * math.pi * xs)))
        if name == "ZDT6":
            f1 = np.linspace(0.2807753191, 1.0, count)
            return np.column_stack((f1, 1.0 - f1**2))
        raise ValueError(name)

    return Problem(name, 2, num_var, lower, upper, evaluate, pf)


def build_dtlz(name: str) -> Problem:
    problem_id = int(name[4:])
    num_obj = 3
    num_var = 7 if problem_id == 1 else (22 if problem_id == 7 else 12)
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
            theta = np.empty(m - 1)
            if problem_id in {5, 6}:
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
        if problem_id in {5, 6}:
            x = np.linspace(0.0, 1.0, count)
            theta = x * math.pi / 2.0
            fixed = math.pi / 4.0
            return np.column_stack((np.cos(theta) * math.cos(fixed), np.cos(theta) * math.sin(fixed), np.sin(theta)))
        if problem_id == 7:
            pts = uniform_simplex_points(count, num_obj - 1, 1.0)
            g = 1.0
            h = num_obj - np.sum((pts / (1.0 + g)) * (1.0 + np.sin(3.0 * math.pi * pts)), axis=1)
            return np.column_stack((pts, (1.0 + g) * h))
        raise ValueError(name)

    return Problem(name, num_obj, num_var, lower, upper, evaluate, pf)


def build_uf(name: str) -> Problem:
    problem_id = int(name[2:])
    num_var = 30
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
        if problem_id in {1, 2, 3, 4, 5, 6, 7}:
            return evaluate_uf_2obj(problem_id, x)
        return evaluate_uf_3obj(problem_id, x)

    def pf(count: int) -> Array:
        return uf_pareto_front(problem_id, count)

    return Problem(name, num_obj, num_var, lower, upper, evaluate, pf)


def evaluate_uf_2obj(problem_id: int, x: Array) -> Array:
    n = len(x)
    j = np.arange(2, n + 1)
    if problem_id == 2:
        carrier = 0.3 * x[0] * x[0] * np.cos(24.0 * math.pi * x[0] + 4.0 * j * math.pi / n) + 0.6 * x[0]
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
        return np.array([x[0] + 2.0 * np.sum(h_odd) / len(odd), 1.0 - x[0] * x[0] + 2.0 * np.sum(h_even) / len(even)])
    if problem_id == 5:
        n_param = 10
        epsilon = 0.1
        bump = (0.5 / n_param + epsilon) * abs(math.sin(2.0 * n_param * math.pi * x[0]))
        h_odd = 2.0 * odd**2 - np.cos(4.0 * math.pi * odd) + 1.0
        h_even = 2.0 * even**2 - np.cos(4.0 * math.pi * even) + 1.0
        return np.array([x[0] + bump + 2.0 * np.sum(h_odd) / len(odd), 1.0 - x[0] + bump + 2.0 * np.sum(h_even) / len(even)])
    if problem_id == 6:
        n_param = 2
        epsilon = 0.1
        bump = max(0.0, 2.0 * (0.5 / n_param + epsilon) * math.sin(2.0 * n_param * math.pi * x[0]))
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
        if problem_id == 10:
            contribution = np.sum(4.0 * y * y - np.cos(8.0 * math.pi * y) + 1.0)
        else:
            contribution = np.sum(y * y)
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
        f[group] = base + 2.0 * contribution / len(idx)
    return f


def uf_pareto_front(problem_id: int, count: int) -> Array:
    x = np.linspace(0.0, 1.0, count)
    if problem_id in {1, 2, 3}:
        return np.column_stack((x, 1.0 - np.sqrt(x)))
    if problem_id == 4:
        return np.column_stack((x, 1.0 - x**2))
    if problem_id == 5:
        x = np.linspace(0.0, 1.0, 21)
        return np.column_stack((x, 1.0 - x))
    if problem_id == 6:
        first = np.linspace(0.25, 0.5, max(2, count // 2))
        second = np.linspace(0.75, 1.0, max(2, count // 2))
        x = np.concatenate(([0.0], first, second))
        return np.column_stack((x, 1.0 - x))
    if problem_id == 7:
        return np.column_stack((x, 1.0 - x))
    if problem_id in {8, 10}:
        return sphere_front(count, 3)
    if problem_id == 9:
        base = uniform_simplex_points(count * 3, 3, 1.0)
        keep = (4.0 * base[:, 0] < 1.0 - base[:, 2]) | (4.0 * base[:, 0] > 3.0 * (1.0 - base[:, 2]))
        filtered = base[keep]
        if len(filtered) < count:
            return filtered
        return filtered[:count]
    raise ValueError(f"UF{problem_id}")


def make_optimizer(algorithm: str, problem: Problem, config: AMPMOConfig):
    normalized = algorithm.lower().replace("-", "").replace("_", "")
    if normalized in {"ampmmo", "ampmo"}:
        return AMPMO(problem, config)
    if normalized in {"nsga2", "nsgaii"}:
        return NSGAII(problem, config)
    raise ValueError(f"Unsupported algorithm: {algorithm}")


def algorithm_label(algorithm: str) -> str:
    normalized = algorithm.lower().replace("-", "").replace("_", "")
    if normalized in {"ampmmo", "ampmo"}:
        return "A-MPMO"
    if normalized in {"nsga2", "nsgaii"}:
        return "NSGAII"
    raise ValueError(f"Unsupported algorithm: {algorithm}")


def algorithm_file_prefix(algorithm: str) -> str:
    normalized = algorithm.lower().replace("-", "").replace("_", "")
    if normalized in {"ampmmo", "ampmo"}:
        return "ampmmo"
    if normalized in {"nsga2", "nsgaii"}:
        return "nsgaii"
    raise ValueError(f"Unsupported algorithm: {algorithm}")


def run_experiment(
    config: AMPMOConfig,
    problems: list[str],
    output_dir: Path,
    algorithm: str = "ampmmo",
    save_objectives: bool = True,
    save_history: bool = False,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    label = algorithm_label(algorithm)
    file_prefix = algorithm_file_prefix(algorithm)
    summary_path = output_dir / f"{file_prefix}_summary.csv"
    runs_path = output_dir / f"{file_prefix}_runs.csv"
    run_rows = []
    summary_rows = []
    for problem_name in problems:
        problem = build_problem(problem_name)
        igd_values = []
        hv_values = []
        for run in range(1, config.runs + 1):
            seed = config.seed + 1000 * (len(run_rows) + 1)
            result = make_optimizer(algorithm, problem, config).run(seed)
            igd_values.append(float(result["igd"]))
            hv_values.append(float(result["hv"]))
            run_rows.append({"algorithm": label, "problem": problem.name, "run": run, "seed": seed, "igd": result["igd"], "hv": result["hv"]})
            if save_objectives:
                np.savetxt(output_dir / f"{label}_{problem.name}_run{run:02d}_obj.csv", result["objectives"], delimiter=",", header=",".join(f"f{i+1}" for i in range(problem.num_obj)), comments="")
            if save_history and "history" in result:
                history_path = output_dir / f"{label}_{problem.name}_run{run:02d}_history.csv"
                with history_path.open("w", newline="", encoding="utf-8") as f:
                    fieldnames = ["generation", "evaluations", "phase"] + [f"subpop_{i+1}" for i in range(config.subpopulations)]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for entry in result["history"]:
                        row = {
                            "generation": entry["generation"],
                            "evaluations": entry["evaluations"],
                            "phase": entry["phase"],
                        }
                        for i, size in enumerate(entry["sizes"]):
                            row[f"subpop_{i+1}"] = size
                        writer.writerow(row)
        finite_hv = np.array([v for v in hv_values if np.isfinite(v)], dtype=float)
        summary_rows.append(
            {
                "problem": problem.name,
                "M": problem.num_obj,
                "D": problem.num_var,
                "runs": config.runs,
                "igd_mean": np.mean(igd_values),
                "igd_std": np.std(igd_values, ddof=1) if len(igd_values) > 1 else 0.0,
                "hv_mean": np.mean(finite_hv) if len(finite_hv) else float("nan"),
                "hv_std": np.std(finite_hv, ddof=1) if len(finite_hv) > 1 else 0.0,
            }
        )
        print(f"{label} {problem.name}: IGD={summary_rows[-1]['igd_mean']:.6e} ({summary_rows[-1]['igd_std']:.2e}), HV={summary_rows[-1]['hv_mean']:.6e}")

    with runs_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["algorithm", "problem", "run", "seed", "igd", "hv"])
        writer.writeheader()
        writer.writerows(run_rows)
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["problem", "M", "D", "runs", "igd_mean", "igd_std", "hv_mean", "hv_std"])
        writer.writeheader()
        writer.writerows(summary_rows)
    table3_path = output_dir / f"table3_{file_prefix}_igd.csv"
    with table3_path.open("w", newline="", encoding="utf-8") as f:
        igd_column = f"{label}_IGD"
        writer = csv.DictWriter(f, fieldnames=["Problem", "M", "D", igd_column])
        writer.writeheader()
        for row in summary_rows:
            writer.writerow(
                {
                    "Problem": row["problem"],
                    "M": row["M"],
                    "D": row["D"],
                    igd_column: f"{row['igd_mean']:.4e}({row['igd_std']:.2e})",
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reproduce the A-MPMO experiment settings from Zhao et al. (2025).")
    parser.add_argument("--problems", nargs="+", default=["ZDT1", "ZDT2", "ZDT3", "ZDT4", "ZDT6", "UF1", "DTLZ1", "DTLZ2", "DTLZ3", "DTLZ4", "DTLZ5", "DTLZ6", "DTLZ7"])
    parser.add_argument("--output-dir", type=Path, default=Path("ampmmo_outputs"))
    parser.add_argument("--population-size", type=int, default=100)
    parser.add_argument("--max-evaluations", type=int, default=10000)
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--seed", type=int, default=2025)
    parser.add_argument("--pf-samples", type=int, default=10000, help="Number of reference PF points for IGD; local UF source uses 10000.")
    parser.add_argument("--algorithm", choices=["ampmmo", "nsga2"], default="ampmmo")
    parser.add_argument("--table3", action="store_true", help="Run the Table 3 problem set in the same order as the paper.")
    parser.add_argument("--no-save-objs", action="store_true", help="Only save run and summary CSV files, not every final objective set.")
    parser.add_argument("--save-history", action="store_true", help="Save A-MPMO per-generation subpopulation sizes for Eq.(2)-(3) checks.")
    parser.add_argument("--smoke", action="store_true", help="Run a tiny deterministic check instead of the full 30-run experiment.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.table3:
        args.problems = TABLE3_PROBLEMS
    if args.smoke:
        args.problems = ["ZDT1"]
        args.population_size = 30
        args.max_evaluations = 300
        args.runs = 2
    config = AMPMOConfig(
        population_size=args.population_size,
        max_evaluations=args.max_evaluations,
        runs=args.runs,
        seed=args.seed,
        pf_samples=args.pf_samples,
    )
    run_experiment(
        config,
        args.problems,
        args.output_dir,
        algorithm=args.algorithm,
        save_objectives=not args.no_save_objs,
        save_history=args.save_history,
    )


if __name__ == "__main__":
    main()
