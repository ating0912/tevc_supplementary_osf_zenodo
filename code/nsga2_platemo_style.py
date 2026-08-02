import random
import statistics
from dataclasses import dataclass
from typing import Callable, List, Sequence, Tuple


Vector = List[float]
Objectives = Tuple[float, ...]


@dataclass
class Individual:
    x: Vector
    f: Objectives
    rank: int = 0
    crowding: float = 0.0


@dataclass(frozen=True)
class Problem:
    name: str
    objective: Callable[[Sequence[float]], Objectives]
    lower: Vector
    upper: Vector
    true_front: List[Objectives]
    paper_mean: float
    paper_std: float


def zdt1(x: Sequence[float]) -> Objectives:
    f1 = x[0]
    g = 1.0 + 9.0 * sum(x[1:]) / (len(x) - 1)
    h = 1.0 - (f1 / g) ** 0.5
    return f1, g * h


def zdt2(x: Sequence[float]) -> Objectives:
    f1 = x[0]
    g = 1.0 + 9.0 * sum(x[1:]) / (len(x) - 1)
    h = 1.0 - (f1 / g) ** 2
    return f1, g * h


def zdt3(x: Sequence[float]) -> Objectives:
    f1 = x[0]
    g = 1.0 + 9.0 * sum(x[1:]) / (len(x) - 1)
    h = 1.0 - (f1 / g) ** 0.5 - (f1 / g) * sin_10pi(f1)
    return f1, g * h


def zdt4(x: Sequence[float]) -> Objectives:
    f1 = x[0]
    g = 1.0 + 10.0 * (len(x) - 1)
    g += sum(xi * xi - 10.0 * cos_4pi(xi) for xi in x[1:])
    h = 1.0 - (f1 / g) ** 0.5
    return f1, g * h


def zdt6(x: Sequence[float]) -> Objectives:
    f1 = 1.0 - exp_neg4(x[0]) * sin_6pi(x[0]) ** 6
    g = 1.0 + 9.0 * (sum(x[1:]) / (len(x) - 1)) ** 0.25
    h = 1.0 - (f1 / g) ** 2
    return f1, g * h


def sin_10pi(x: float) -> float:
    import math

    return math.sin(10.0 * math.pi * x)


def sin_6pi(x: float) -> float:
    import math

    return math.sin(6.0 * math.pi * x)


def cos_4pi(x: float) -> float:
    import math

    return math.cos(4.0 * math.pi * x)


def exp_neg4(x: float) -> float:
    import math

    return math.exp(-4.0 * x)


def dominates(a: Individual, b: Individual) -> bool:
    return all(x <= y for x, y in zip(a.f, b.f)) and any(x < y for x, y in zip(a.f, b.f))


def fast_non_dominated_sort(pop: List[Individual]) -> List[List[Individual]]:
    if pop and len(pop[0].f) == 2:
        return fast_non_dominated_sort_2d(pop)

    dominates_set = {id(p): [] for p in pop}
    dominated_count = {id(p): 0 for p in pop}
    fronts: List[List[Individual]] = [[]]

    for p in pop:
        for q in pop:
            if p is q:
                continue
            if dominates(p, q):
                dominates_set[id(p)].append(q)
            elif dominates(q, p):
                dominated_count[id(p)] += 1
        if dominated_count[id(p)] == 0:
            p.rank = 0
            fronts[0].append(p)

    i = 0
    while fronts[i]:
        next_front = []
        for p in fronts[i]:
            for q in dominates_set[id(p)]:
                dominated_count[id(q)] -= 1
                if dominated_count[id(q)] == 0:
                    q.rank = i + 1
                    next_front.append(q)
        i += 1
        fronts.append(next_front)

    return fronts[:-1]


def fast_non_dominated_sort_2d(pop: List[Individual]) -> List[List[Individual]]:
    fronts: List[List[Individual]] = []

    # For two minimization objectives, sorting by f1 lets each front keep a
    # decreasing f2 boundary. This gives the same rank structure much faster.
    sorted_pop = sorted(pop, key=lambda ind: (ind.f[0], ind.f[1]))
    front_tails: List[float] = []

    for ind in sorted_pop:
        placed = False
        for rank, tail_f2 in enumerate(front_tails):
            if ind.f[1] < tail_f2:
                ind.rank = rank
                fronts[rank].append(ind)
                front_tails[rank] = ind.f[1]
                placed = True
                break

        if not placed:
            ind.rank = len(fronts)
            fronts.append([ind])
            front_tails.append(ind.f[1])

    return fronts


def assign_crowding_distance(front: List[Individual]) -> None:
    if not front:
        return

    for ind in front:
        ind.crowding = 0.0

    n_obj = len(front[0].f)
    for m in range(n_obj):
        front.sort(key=lambda ind: ind.f[m])
        front[0].crowding = float("inf")
        front[-1].crowding = float("inf")

        f_min = front[0].f[m]
        f_max = front[-1].f[m]
        if f_max == f_min:
            continue

        for i in range(1, len(front) - 1):
            front[i].crowding += (front[i + 1].f[m] - front[i - 1].f[m]) / (f_max - f_min)


def environmental_selection(pop: List[Individual], n: int) -> List[Individual]:
    selected = []
    for front in fast_non_dominated_sort(pop):
        assign_crowding_distance(front)
        if len(selected) + len(front) <= n:
            selected.extend(front)
        else:
            front.sort(key=lambda ind: ind.crowding, reverse=True)
            selected.extend(front[: n - len(selected)])
            break
    return selected


def tournament(pop: List[Individual]) -> Individual:
    a, b = random.sample(pop, 2)
    if a.rank != b.rank:
        return a if a.rank < b.rank else b
    return a if a.crowding > b.crowding else b


def sbx_crossover(
    p1: Vector,
    p2: Vector,
    lower: Vector,
    upper: Vector,
    pro_c: float = 1.0,
    eta_c: float = 20.0,
) -> Tuple[Vector, Vector]:
    c1, c2 = p1[:], p2[:]
    if random.random() > pro_c:
        return c1, c2

    for i, (xl, xu) in enumerate(zip(lower, upper)):
        if random.random() > 0.5 or abs(p1[i] - p2[i]) < 1e-14:
            continue

        y1, y2 = sorted((p1[i], p2[i]))
        rand = random.random()

        beta = 1.0 + 2.0 * (y1 - xl) / (y2 - y1)
        alpha = 2.0 - beta ** -(eta_c + 1.0)
        if rand <= 1.0 / alpha:
            betaq = (rand * alpha) ** (1.0 / (eta_c + 1.0))
        else:
            betaq = (1.0 / (2.0 - rand * alpha)) ** (1.0 / (eta_c + 1.0))
        child1 = 0.5 * ((y1 + y2) - betaq * (y2 - y1))

        beta = 1.0 + 2.0 * (xu - y2) / (y2 - y1)
        alpha = 2.0 - beta ** -(eta_c + 1.0)
        if rand <= 1.0 / alpha:
            betaq = (rand * alpha) ** (1.0 / (eta_c + 1.0))
        else:
            betaq = (1.0 / (2.0 - rand * alpha)) ** (1.0 / (eta_c + 1.0))
        child2 = 0.5 * ((y1 + y2) + betaq * (y2 - y1))

        c1[i] = min(max(child1, xl), xu)
        c2[i] = min(max(child2, xl), xu)
        if random.random() < 0.5:
            c1[i], c2[i] = c2[i], c1[i]

    return c1, c2


def polynomial_mutation(
    x: Vector,
    lower: Vector,
    upper: Vector,
    pro_m: float = 1.0,
    eta_m: float = 20.0,
) -> Vector:
    y = x[:]
    d = len(y)
    per_variable_probability = pro_m / d

    for i, (xl, xu) in enumerate(zip(lower, upper)):
        if random.random() > per_variable_probability:
            continue

        delta1 = (y[i] - xl) / (xu - xl)
        delta2 = (xu - y[i]) / (xu - xl)
        rand = random.random()
        mut_pow = 1.0 / (eta_m + 1.0)

        if rand < 0.5:
            xy = 1.0 - delta1
            val = 2.0 * rand + (1.0 - 2.0 * rand) * (xy ** (eta_m + 1.0))
            deltaq = val ** mut_pow - 1.0
        else:
            xy = 1.0 - delta2
            val = 2.0 * (1.0 - rand) + 2.0 * (rand - 0.5) * (xy ** (eta_m + 1.0))
            deltaq = 1.0 - val ** mut_pow

        y[i] = min(max(y[i] + deltaq * (xu - xl), xl), xu)

    return y


def make_individual(x: Vector, objective: Callable[[Sequence[float]], Objectives]) -> Individual:
    return Individual(x=x, f=objective(x))


def euclidean_distance(a: Objectives, b: Objectives) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def igd(approximation: Sequence[Objectives], true_front: Sequence[Objectives]) -> float:
    distances = [
        min(euclidean_distance(reference, solution) for solution in approximation)
        for reference in true_front
    ]
    return sum(distances) / len(distances)


def zdt1_true_front(points: int = 1000) -> List[Objectives]:
    front = []
    for i in range(points):
        f1 = i / (points - 1)
        f2 = 1.0 - f1 ** 0.5
        front.append((f1, f2))
    return front


def zdt2_true_front(points: int = 1000) -> List[Objectives]:
    front = []
    for i in range(points):
        f1 = i / (points - 1)
        f2 = 1.0 - f1 * f1
        front.append((f1, f2))
    return front


def zdt3_true_front(points_per_segment: int = 200) -> List[Objectives]:
    intervals = [
        (0.0, 0.0830015349),
        (0.1822287280, 0.2577623634),
        (0.4093136748, 0.4538821041),
        (0.6183967944, 0.6525117038),
        (0.8233317983, 0.8518328654),
    ]
    front = []
    for lo, hi in intervals:
        for i in range(points_per_segment):
            f1 = lo + (hi - lo) * i / (points_per_segment - 1)
            f2 = 1.0 - f1 ** 0.5 - f1 * sin_10pi(f1)
            front.append((f1, f2))
    return front


def zdt6_true_front(points: int = 1000) -> List[Objectives]:
    candidates = []
    for i in range(points * 20):
        x1 = i / (points * 20 - 1)
        f1 = 1.0 - exp_neg4(x1) * sin_6pi(x1) ** 6
        f2 = 1.0 - f1 * f1
        candidates.append(Individual([x1], (f1, f2)))
    front = fast_non_dominated_sort(candidates)[0]
    front.sort(key=lambda ind: ind.f[0])
    if len(front) <= points:
        return [ind.f for ind in front]
    step = (len(front) - 1) / (points - 1)
    return [front[round(i * step)].f for i in range(points)]


def nsga2(
    objective: Callable[[Sequence[float]], Objectives],
    lower: Vector,
    upper: Vector,
    n: int = 100,
    max_it: int = 10000,
    pro_c: float = 1.0,
    eta_c: float = 20.0,
    pro_m: float = 1.0,
    eta_m: float = 20.0,
    seed: int | None = None,
) -> List[Individual]:
    if seed is not None:
        random.seed(seed)

    d = len(lower)
    pop = [
        make_individual([random.uniform(lower[j], upper[j]) for j in range(d)], objective)
        for _ in range(n)
    ]
    pop = environmental_selection(pop, n)

    evaluations = n
    while evaluations < max_it:
        offspring = []
        while len(offspring) < n and evaluations < max_it:
            p1 = tournament(pop)
            p2 = tournament(pop)
            c1, c2 = sbx_crossover(p1.x, p2.x, lower, upper, pro_c, eta_c)
            c1 = polynomial_mutation(c1, lower, upper, pro_m, eta_m)
            c2 = polynomial_mutation(c2, lower, upper, pro_m, eta_m)
            offspring.append(make_individual(c1, objective))
            evaluations += 1
            if len(offspring) < n and evaluations < max_it:
                offspring.append(make_individual(c2, objective))
                evaluations += 1

        pop = environmental_selection(pop + offspring, n)

    return pop


def run_problem(
    problem: Problem,
    runs: int = 30,
    seed_start: int = 1,
) -> Tuple[List[float], float, float]:
    igd_values = []

    for run in range(runs):
        result = nsga2(
            objective=problem.objective,
            lower=problem.lower,
            upper=problem.upper,
            n=100,
            max_it=10000,
            pro_c=1.0,
            eta_c=20.0,
            pro_m=1.0,
            eta_m=20.0,
            seed=seed_start + run,
        )

        first_front = fast_non_dominated_sort(result)[0]
        approximation = [ind.f for ind in first_front]
        value = igd(approximation, problem.true_front)
        igd_values.append(value)
        print(f"{problem.name} Run {run + 1:02d}: IGD = {value:.6e}", flush=True)

    mean_igd = statistics.mean(igd_values)
    std_igd = statistics.stdev(igd_values) if len(igd_values) > 1 else 0.0
    return igd_values, mean_igd, std_igd


def zdt_problems() -> List[Problem]:
    # Paper Table 3, NSGA-II IGD mean and std on the ZDT benchmark suite.
    return [
        Problem("ZDT1", zdt1, [0.0] * 30, [1.0] * 30, zdt1_true_front(), 1.4621e-1, 5.53e-2),
        Problem("ZDT2", zdt2, [0.0] * 30, [1.0] * 30, zdt2_true_front(), 5.0813e-1, 8.79e-2),
        Problem("ZDT3", zdt3, [0.0] * 30, [1.0] * 30, zdt3_true_front(), 1.7787e-1, 7.34e-2),
        Problem("ZDT4", zdt4, [0.0] + [-5.0] * 9, [1.0] + [5.0] * 9, zdt1_true_front(), 5.3146e-1, 2.51e-1),
        Problem("ZDT6", zdt6, [0.0] * 10, [1.0] * 10, zdt6_true_front(), 7.4290e-2, 1.71e-2),
    ]


def run_zdt_series(runs: int = 30) -> None:
    rows = []
    header = [
        "problem",
        "ours_mean",
        "ours_std",
        "paper_mean",
        "paper_std",
        "mean_abs_error",
        "mean_rel_error_percent",
        "std_abs_error",
        "std_rel_error_percent",
    ]

    for problem in zdt_problems():
        _, mean_value, std_value = run_problem(problem, runs=runs)
        mean_abs_error = abs(mean_value - problem.paper_mean)
        std_abs_error = abs(std_value - problem.paper_std)
        mean_rel_error = mean_abs_error / abs(problem.paper_mean) * 100.0
        std_rel_error = std_abs_error / abs(problem.paper_std) * 100.0
        rows.append(
            [
                problem.name,
                mean_value,
                std_value,
                problem.paper_mean,
                problem.paper_std,
                mean_abs_error,
                mean_rel_error,
                std_abs_error,
                std_rel_error,
            ]
        )

    print("\n" + ",".join(header), flush=True)
    for row in rows:
        print(
            ",".join([row[0]] + [f"{value:.6e}" for value in row[1:]]),
            flush=True,
        )

    with open("zdt_nsga2_igd_comparison.csv", "w", encoding="utf-8") as file:
        file.write(",".join(header) + "\n")
        for row in rows:
            file.write(",".join([row[0]] + [f"{value:.12e}" for value in row[1:]]) + "\n")


if __name__ == "__main__":
    run_zdt_series(runs=30)
