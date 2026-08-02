import csv
from pathlib import Path

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.optimize import minimize
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting

from run_paper_matrix_nsga2_pymoo_h import (
    BENCHMARKS,
    N,
    N_GEN,
    PAPER,
    RUNS,
    get_pymoo_problem,
    igd,
    pf_for,
)


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "nsga2_outputs" / "version_matrix_rerun"
OUT.mkdir(parents=True, exist_ok=True)

CONFIGS = [
    ("V11", "pymoo; generation=100; per-variable proM; final population; raw analytic PF", False),
    ("V12", "pymoo; generation=100; per-variable proM; nondominated front; raw analytic PF", True),
]


def nondominated_only(obj):
    idx = NonDominatedSorting().do(obj, only_non_dominated_front=True)
    return obj[idx]


def run_once(problem, seed):
    algorithm = NSGA2(
        pop_size=N,
        crossover=SBX(prob=1.0, eta=20),
        mutation=PM(prob=1.0, prob_var=1.0, eta=20),
        eliminate_duplicates=False,
    )
    res = minimize(problem, algorithm, ("n_gen", N_GEN), seed=seed, verbose=False)
    return res.pop.get("F")


def main():
    rows = []
    partial = OUT / "version_matrix_pymoo_partial_summary.csv"
    if partial.exists():
        with partial.open(newline="") as f:
            rows = list(csv.DictReader(f))

    done = {(r["config"], r["problem"]) for r in rows}

    for config, desc, use_nd in CONFIGS:
        for name, m, d in BENCHMARKS:
            if (config, name) in done:
                continue
            problem = get_pymoo_problem(name, m, d)
            pf = pf_for(name, m)
            values = []
            problem_dir = OUT / config / name
            problem_dir.mkdir(parents=True, exist_ok=True)
            print(f"=== {config} | {name} M={m} D={d} generations={N_GEN} ===", flush=True)
            for run in range(1, RUNS + 1):
                run_dir = problem_dir / f"run_{run:03d}"
                run_dir.mkdir(exist_ok=True)
                obj_path = run_dir / "obj.csv"
                if obj_path.exists():
                    obj = np.loadtxt(obj_path, delimiter=",", skiprows=1)
                else:
                    obj = run_once(problem, run)
                    np.savetxt(
                        obj_path,
                        obj,
                        delimiter=",",
                        header=",".join([f"f{i+1}" for i in range(obj.shape[1])]),
                        comments="",
                    )
                eval_obj = nondominated_only(obj) if use_nd else obj
                score = igd(eval_obj, pf)
                values.append(score)
                print(f"{config} {name} run={run:02d} IGD={score:.12g}", flush=True)

            values = np.array(values)
            np.savetxt(
                problem_dir / f"{config}_{name}_igd_runs.csv",
                np.column_stack([np.arange(1, RUNS + 1), values]),
                delimiter=",",
                header="run,igd",
                comments="",
            )
            paper = PAPER[name]
            rows.append(
                {
                    "config": config,
                    "description": desc,
                    "problem": name,
                    "M": m,
                    "D": d,
                    "N": N,
                    "generations": N_GEN,
                    "runs": RUNS,
                    "nondominated_only": use_nd,
                    "paper_nsga2_igd": paper,
                    "mean_igd": float(values.mean()),
                    "sample_std": float(values.std(ddof=1)),
                    "ours_minus_paper": float(values.mean() - paper),
                    "abs_diff": float(abs(values.mean() - paper)),
                    "relative_diff_percent": float(abs(values.mean() - paper) / paper * 100),
                }
            )
            with partial.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

    final = OUT / "version_matrix_pymoo_summary.csv"
    with final.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(final)


if __name__ == "__main__":
    main()
