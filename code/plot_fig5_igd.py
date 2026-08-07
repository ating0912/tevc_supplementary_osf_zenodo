import csv
from pathlib import Path

import matplotlib.pyplot as plt

base = Path(r"\\wsl$\Ubuntu\home\yiting\lab\PEATSD\fig5_ng_outputs")
out = Path(r"C:\Users\yiting\Documents\Playground")
agg_path = base / "fig5_ng_aggregate.csv"

rows = []
with agg_path.open("r", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        rows.append({
            "problem": row["problem"],
            "ng": int(row["ng"]),
            "igd_mean": float(row["igd_mean"]),
            "igd_std": float(row["igd_std"]),
        })

ng_values = [1, 10, 20, 40, 80]
styles = {
    "UF1": ("#1f77b4", "o"),
    "UF2": ("#ff7f0e", "s"),
    "UF3": ("#2ca02c", "^"),
    "UF7": ("#d62728", "D"),
    "LSMOP1": ("#1f77b4", "o"),
    "LSMOP4": ("#ff7f0e", "s"),
    "LSMOP5": ("#2ca02c", "^"),
    "LSMOP9": ("#d62728", "D"),
}

def plot_group(problems, title, stem):
    by_key = {(r["problem"], r["ng"]): r for r in rows}
    fig, ax = plt.subplots(figsize=(8.2, 5.2), dpi=180)
    for problem in problems:
        xs, ys = [], []
        for ng in ng_values:
            row = by_key.get((problem, ng))
            if row is None:
                continue
            xs.append(ng)
            ys.append(row["igd_mean"])
        color, marker = styles[problem]
        ax.plot(xs, ys, marker=marker, linewidth=2.2, markersize=6.5, color=color, label=problem)
    ax.set_title(title, fontsize=15, fontweight="bold")
    ax.set_xlabel("Number of Generations ($n_g$)", fontsize=12)
    ax.set_ylabel("IGD", fontsize=12)
    ax.set_xlim(1, 80)
    ax.set_xticks(ng_values)
    ax.grid(True, color="#d9d9d9", linewidth=0.8, alpha=0.9)
    ax.legend(frameon=True, fontsize=10)
    fig.tight_layout()
    fig.savefig(out / f"{stem}.png", bbox_inches="tight")
    fig.savefig(out / f"{stem}.svg", bbox_inches="tight")
    plt.close(fig)

plot_group(["UF1", "UF2", "UF3", "UF7"], "Fig. 5 UF IGD", "fig5_uf1237_igd")
plot_group(["LSMOP1", "LSMOP4", "LSMOP5", "LSMOP9"], "Fig. 5 LSMOP IGD", "fig5_lsmop1459_igd")
print(out / "fig5_uf1237_igd.png")
print(out / "fig5_lsmop1459_igd.png")
