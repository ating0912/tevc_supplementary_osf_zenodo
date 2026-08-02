import csv
from pathlib import Path

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.optimize import minimize
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.problems import get_problem


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "nsga2_outputs" / "paper_matrix_nsga2" / "H"
OUT.mkdir(parents=True, exist_ok=True)

N = 100
RUNS = 30
N_GEN = 100
PF_POINTS = 10000

PAPER = {
    "DTLZ1": 2.3828e1, "DTLZ2": 5.4881e-2, "DTLZ3": 1.3357e1,
    "DTLZ4": 4.0388e-2, "DTLZ5": 3.2473e-2, "DTLZ6": 1.1635e-1,
    "DTLZ7": 1.7080e-1, "ZDT1": 1.4621e-1, "ZDT2": 5.0813e-1,
    "ZDT3": 1.7787e-1, "ZDT4": 5.3146e-1, "ZDT6": 7.4290e-2,
    "UF1": 3.1352e-1, "UF2": 2.1196e-1, "UF3": 3.3463e-1,
    "UF4": 1.2713e-1, "UF5": 1.3074e0, "UF6": 5.9480e-1,
    "UF7": 4.3887e-1, "UF8": 5.8545e-1, "UF9": 5.2501e-1,
    "UF10": 7.4415e-1,
}

BENCHMARKS = [
    ("DTLZ1", 3, 7), ("DTLZ2", 3, 12), ("DTLZ3", 3, 12), ("DTLZ4", 3, 12),
    ("DTLZ5", 3, 12), ("DTLZ6", 3, 12), ("DTLZ7", 3, 22),
    ("ZDT1", 2, 30), ("ZDT2", 2, 30), ("ZDT3", 2, 30), ("ZDT4", 2, 10), ("ZDT6", 2, 10),
    ("UF1", 2, 30), ("UF2", 2, 30), ("UF3", 2, 30), ("UF4", 2, 30), ("UF5", 2, 30),
    ("UF6", 2, 30), ("UF7", 2, 30), ("UF8", 3, 30), ("UF9", 3, 30), ("UF10", 3, 30),
]


def uniform_sphere(n, m):
    x = np.random.default_rng(12345).dirichlet(np.ones(m), n)
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def pf_2d(kind, n=PF_POINTS):
    x = np.linspace(0.0, 1.0, n)
    if kind in {"zdt1", "uf1", "uf2", "uf3"}:
        return np.column_stack([x, 1 - np.sqrt(x)])
    if kind in {"zdt2", "uf4"}:
        return np.column_stack([x, 1 - x * x])
    if kind == "zdt3":
        intervals = [(0, 0.0830015349), (0.1822287280, 0.2577623634), (0.4093136748, 0.4538821041),
                     (0.6183967944, 0.6525117038), (0.8233317983, 0.8518328654)]
        xs = np.concatenate([np.linspace(a, b, max(2, n // 5)) for a, b in intervals])
        return np.column_stack([xs, 1 - np.sqrt(xs) - xs * np.sin(10 * np.pi * xs)])
    if kind == "zdt4":
        return np.column_stack([x, 1 - np.sqrt(x)])
    if kind == "zdt6":
        f1 = np.linspace(0.2807753191, 1.0, n)
        return np.column_stack([f1, 1 - (f1 / 1.0) ** 2])
    if kind in {"uf7", "uf5"}:
        if kind == "uf5":
            x = np.arange(21) / 20
        return np.column_stack([x, 1 - x])
    if kind == "uf6":
        x = np.linspace(0, 1, n)
        pf = np.column_stack([x, 1 - x])
        keep = ~(((pf[:, 0] > 0) & (pf[:, 0] < 0.25)) | ((pf[:, 0] > 0.5) & (pf[:, 0] < 0.75)))
        return pf[keep]
    raise ValueError(kind)


def pf_for(name, m):
    lname = name.lower()
    if lname.startswith("dtlz"):
        if lname == "dtlz1":
            x = np.random.default_rng(12345).dirichlet(np.ones(m), PF_POINTS) * 0.5
            return x
        if lname == "dtlz7":
            # Use pymoo's PF for DTLZ7 when available; fallback to sampled points.
            try:
                return get_problem("dtlz7", n_var=22, n_obj=3).pareto_front(n_pareto_points=PF_POINTS)
            except Exception:
                x = np.random.default_rng(12345).random((PF_POINTS, m - 1))
                f_m = 2 * (m - np.sum((x / 2) * (1 + np.sin(3 * np.pi * x)), axis=1))
                return np.column_stack([x, f_m])
        return uniform_sphere(PF_POINTS, m)
    if lname.startswith("zdt") or lname in {f"uf{i}" for i in range(1, 8)}:
        return pf_2d(lname)
    if lname in {"uf8", "uf10"}:
        return uniform_sphere(PF_POINTS, 3)
    if lname == "uf9":
        r = np.random.default_rng(12345).dirichlet(np.ones(3), PF_POINTS)
        keep = ~((r[:, 0] > (1 - r[:, 2]) / 4) & (r[:, 0] < (1 - r[:, 2]) * 3 / 4))
        return r[keep]
    raise ValueError(name)


class UFProblem(Problem):
    def __init__(self, name, n_var=30):
        self.name = name.lower()
        n_obj = 3 if self.name in {"uf8", "uf9", "uf10"} else 2
        xl = np.zeros(n_var)
        xu = np.ones(n_var)
        if self.name in {"uf1", "uf2", "uf5", "uf6", "uf7"}:
            xl[1:] = -1
        if self.name in {"uf4", "uf8", "uf9", "uf10"}:
            xl[1 if n_obj == 2 else 2:] = -2
            xu[1 if n_obj == 2 else 2:] = 2
        super().__init__(n_var=n_var, n_obj=n_obj, xl=xl, xu=xu)

    def _evaluate(self, X, out, *args, **kwargs):
        D = self.n_var
        idx = np.arange(1, D + 1)
        f = np.zeros((len(X), self.n_obj))
        if self.name in {"uf1", "uf4", "uf5", "uf6", "uf7"}:
            J1 = np.arange(3, D + 1, 2) - 1
            J2 = np.arange(2, D + 1, 2) - 1
            Y = X - np.sin(6 * np.pi * X[:, [0]] + idx * np.pi / D)
            if self.name == "uf1":
                f[:, 0] = X[:, 0] + 2 * np.mean(Y[:, J1] ** 2, axis=1)
                f[:, 1] = 1 - np.sqrt(X[:, 0]) + 2 * np.mean(Y[:, J2] ** 2, axis=1)
            elif self.name == "uf4":
                h = np.abs(Y) / (1 + np.exp(2 * np.abs(Y)))
                f[:, 0] = X[:, 0] + 2 * np.mean(h[:, J1], axis=1)
                f[:, 1] = 1 - X[:, 0] ** 2 + 2 * np.mean(h[:, J2], axis=1)
            elif self.name == "uf5":
                h = 2 * Y ** 2 - np.cos(4 * np.pi * Y) + 1
                bump = (1 / 20 + 0.1) * np.abs(np.sin(20 * np.pi * X[:, 0]))
                f[:, 0] = X[:, 0] + bump + 2 * np.mean(h[:, J1], axis=1)
                f[:, 1] = 1 - X[:, 0] + bump + 2 * np.mean(h[:, J2], axis=1)
            elif self.name == "uf6":
                add = np.maximum(0, 2 * (1 / 4 + 0.1) * np.sin(4 * np.pi * X[:, 0]))
                f[:, 0] = X[:, 0] + add + 2 / len(J1) * (4 * np.sum(Y[:, J1] ** 2, axis=1) - 2 * np.prod(np.cos(20 * Y[:, J1] * np.pi / np.sqrt(J1 + 1)), axis=1) + 2)
                f[:, 1] = 1 - X[:, 0] + add + 2 / len(J2) * (4 * np.sum(Y[:, J2] ** 2, axis=1) - 2 * np.prod(np.cos(20 * Y[:, J2] * np.pi / np.sqrt(J2 + 1)), axis=1) + 2)
            else:
                f[:, 0] = X[:, 0] ** 0.2 + 2 * np.mean(Y[:, J1] ** 2, axis=1)
                f[:, 1] = 1 - X[:, 0] ** 0.2 + 2 * np.mean(Y[:, J2] ** 2, axis=1)
        elif self.name == "uf2":
            J1 = np.arange(3, D + 1, 2) - 1
            J2 = np.arange(2, D + 1, 2) - 1
            Y = np.zeros_like(X)
            for J, trig in [(J1, np.cos), (J2, np.sin)]:
                jj = J + 1
                x1 = X[:, [0]]
                Y[:, J] = X[:, J] - (0.3 * x1 ** 2 * np.cos(24 * np.pi * x1 + 4 * jj * np.pi / D) + 0.6 * x1) * trig(6 * np.pi * x1 + jj * np.pi / D)
            f[:, 0] = X[:, 0] + 2 * np.mean(Y[:, J1] ** 2, axis=1)
            f[:, 1] = 1 - np.sqrt(X[:, 0]) + 2 * np.mean(Y[:, J2] ** 2, axis=1)
        elif self.name == "uf3":
            J1 = np.arange(3, D + 1, 2) - 1
            J2 = np.arange(2, D + 1, 2) - 1
            Y = X - X[:, [0]] ** (0.5 * (1 + 3 * (idx - 2) / (D - 2)))
            f[:, 0] = X[:, 0] + 2 / len(J1) * (4 * np.sum(Y[:, J1] ** 2, axis=1) - 2 * np.prod(np.cos(20 * Y[:, J1] * np.pi / np.sqrt(J1 + 1)), axis=1) + 2)
            f[:, 1] = 1 - np.sqrt(X[:, 0]) + 2 / len(J2) * (4 * np.sum(Y[:, J2] ** 2, axis=1) - 2 * np.prod(np.cos(20 * Y[:, J2] * np.pi / np.sqrt(J2 + 1)), axis=1) + 2)
        else:
            J1 = np.arange(4, D + 1, 3) - 1
            J2 = np.arange(5, D + 1, 3) - 1
            J3 = np.arange(3, D + 1, 3) - 1
            Y = X - 2 * X[:, [1]] * np.sin(2 * np.pi * X[:, [0]] + idx * np.pi / D)
            if self.name == "uf10":
                Yv = 4 * Y ** 2 - np.cos(8 * np.pi * Y) + 1
            else:
                Yv = Y ** 2
            if self.name == "uf9":
                h = np.maximum(0, 1.1 * (1 - 4 * (2 * X[:, 0] - 1) ** 2))
                f[:, 0] = 0.5 * (h + 2 * X[:, 0]) * X[:, 1] + 2 * np.mean(Yv[:, J1], axis=1)
                f[:, 1] = 0.5 * (h - 2 * X[:, 0] + 2) * X[:, 1] + 2 * np.mean(Yv[:, J2], axis=1)
                f[:, 2] = 1 - X[:, 1] + 2 * np.mean(Yv[:, J3], axis=1)
            else:
                f[:, 0] = np.cos(0.5 * X[:, 0] * np.pi) * np.cos(0.5 * X[:, 1] * np.pi) + 2 * np.mean(Yv[:, J1], axis=1)
                f[:, 1] = np.cos(0.5 * X[:, 0] * np.pi) * np.sin(0.5 * X[:, 1] * np.pi) + 2 * np.mean(Yv[:, J2], axis=1)
                f[:, 2] = np.sin(0.5 * X[:, 0] * np.pi) + 2 * np.mean(Yv[:, J3], axis=1)
        out["F"] = f


def get_pymoo_problem(name, m, d):
    lname = name.lower()
    if lname.startswith("uf"):
        return UFProblem(lname, d)
    if lname.startswith("dtlz"):
        return get_problem(lname, n_var=d, n_obj=m)
    return get_problem(lname, n_var=d)


def igd(pop, pf):
    # Chunked IGD to avoid one large distance matrix for all runs.
    mins = np.full(len(pf), np.inf)
    for row in pop:
        dist = np.sqrt(np.sum((pf - row) ** 2, axis=1))
        mins = np.minimum(mins, dist)
    return float(np.mean(mins))


def main():
    rows = []
    summary_path = OUT.parent / "paper_matrix_pymoo_h_summary.csv"
    for name, m, d in BENCHMARKS:
        problem = get_pymoo_problem(name, m, d)
        pf = pf_for(name, m)
        values = []
        problem_dir = OUT / name
        problem_dir.mkdir(parents=True, exist_ok=True)
        print(f"=== H pymoo | {name} M={m} D={d} generations={N_GEN} ===", flush=True)
        for run in range(1, RUNS + 1):
            run_dir = problem_dir / f"run_{run:03d}"
            run_dir.mkdir(exist_ok=True)
            obj_path = run_dir / "obj.csv"
            if obj_path.exists():
                obj = np.loadtxt(obj_path, delimiter=",", skiprows=1)
            else:
                algorithm = NSGA2(
                    pop_size=N,
                    crossover=SBX(prob=1.0, eta=20),
                    mutation=PM(prob=1.0, prob_var=1.0, eta=20),
                    eliminate_duplicates=False,
                )
                res = minimize(problem, algorithm, ("n_gen", N_GEN), seed=run, verbose=False)
                obj = res.F
                np.savetxt(obj_path, obj, delimiter=",", header=",".join([f"f{i+1}" for i in range(obj.shape[1])]), comments="")
            score = igd(obj, pf)
            values.append(score)
            print(f"H {name} run={run:02d} IGD={score:.12g}", flush=True)
        values = np.array(values)
        np.savetxt(problem_dir / f"H_{name}_igd_runs.csv", np.column_stack([np.arange(1, RUNS + 1), values]), delimiter=",", header="run,igd", comments="")
        paper = PAPER[name]
        rows.append({
            "config": "H",
            "description": "generation=100; pymoo; per-variable proM; analytic PF",
            "problem": name,
            "M": m,
            "D": d,
            "N": N,
            "generations": N_GEN,
            "runs": RUNS,
            "paper_nsga2_igd": paper,
            "mean_igd": float(values.mean()),
            "sample_std": float(values.std(ddof=1)),
            "ours_minus_paper": float(values.mean() - paper),
            "abs_diff": float(abs(values.mean() - paper)),
            "relative_diff_percent": float(abs(values.mean() - paper) / paper * 100),
        })
        with summary_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    print(summary_path)


if __name__ == "__main__":
    main()
