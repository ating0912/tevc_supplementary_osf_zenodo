from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.problems import get_problem
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM


N = 100
M = 2
D = 30
MAX_IT = 10000
RUNS = 30
PRO_C = 1.0
ETA_C = 20
PRO_M = 1.0
ETA_M = 20


def main() -> None:
    out_dir = Path(__file__).resolve().parent / "nsga2_outputs" / "pymoo"
    out_dir.mkdir(parents=True, exist_ok=True)

    problem = get_problem("zdt1", n_var=D)
    all_runs = []

    for run in range(1, RUNS + 1):
        run_dir = out_dir / f"run_{run:03d}"
        run_dir.mkdir(parents=True, exist_ok=True)

        algorithm = NSGA2(
            pop_size=N,
            crossover=SBX(prob=PRO_C, eta=ETA_C),
            mutation=PM(prob=PRO_M, prob_var=PRO_M / D, eta=ETA_M),
        )
        result = minimize(
            problem,
            algorithm,
            ("n_gen", MAX_IT),
            seed=run,
            verbose=False,
        )

        obj_path = run_dir / "obj.csv"
        np.savetxt(obj_path, result.F, delimiter=",", header="f1,f2", comments="")
        all_runs.append((run, result.F))
        print(f"run {run:03d}: saved {obj_path}")

    final_F = all_runs[-1][1]
    obj_path = out_dir / "pymoo_nsga2_zdt1_last_run_obj.csv"
    np.savetxt(obj_path, final_F, delimiter=",", header="f1,f2", comments="")

    pf = problem.pareto_front()
    plt.figure(figsize=(6, 4))
    plt.plot(pf[:, 0], pf[:, 1], "k-", linewidth=1.2, label="True PF")
    plt.scatter(final_F[:, 0], final_F[:, 1], s=14, c="#d62728", label="NSGA-II")
    plt.xlabel("f1")
    plt.ylabel("f2")
    plt.title("pymoo NSGA-II on ZDT1, last run")
    plt.legend()
    plt.tight_layout()
    fig_path = out_dir / "pymoo_nsga2_zdt1_last_run.png"
    plt.savefig(fig_path, dpi=180)

    print(f"Saved objectives: {obj_path}")
    print(f"Saved figure:     {fig_path}")
    print(f"Runs:             {RUNS}")
    print(f"Solutions/run:    {len(final_F)}")


if __name__ == "__main__":
    main()
