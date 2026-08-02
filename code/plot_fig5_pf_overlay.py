from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

base = Path(r"\\wsl$\Ubuntu\home\yiting\lab\PEATSD\fig5_ng_outputs\raw")
out = Path(r"C:\Users\yiting\Documents\Playground")
ng_values = [1, 10, 20, 40, 80]
colors = {1:'#1f77b4', 10:'#ff7f0e', 20:'#2ca02c', 40:'#d62728', 80:'#9467bd'}
problems_by_group = {
    'uf1237': ['UF1', 'UF2', 'UF3', 'UF7'],
    'lsmop1459': ['LSMOP1', 'LSMOP4', 'LSMOP5', 'LSMOP9'],
}

def latest_obj(problem: str, ng: int, run: int = 20) -> Path:
    run_dir = base / problem / f"ng_{ng:03d}" / f"run_{run:03d}"
    files = sorted(run_dir.glob('*_obj_*'))
    if not files:
        raise FileNotFoundError(f'No obj file in {run_dir}')
    return files[-1]

def load_obj(path: Path):
    pts = []
    with path.open('r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 2:
                continue
            try:
                pts.append((float(parts[0]), float(parts[1])))
            except ValueError:
                pass
    arr = np.array(pts, dtype=float)
    if arr.size == 0:
        return arr
    order = np.argsort(arr[:, 0])
    return arr[order]

def plot_group(group_key: str, title_prefix: str, label_prefix: str):
    problems = problems_by_group[group_key]
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), dpi=180)
    axes = axes.ravel()
    handles = []
    labels = []
    for ax, problem in zip(axes, problems):
        for ng in ng_values:
            arr = load_obj(latest_obj(problem, ng, 20))
            if arr.size == 0:
                continue
            sc = ax.scatter(arr[:, 0], arr[:, 1], s=9, alpha=0.65, c=colors[ng], edgecolors='none', label=f'{label_prefix}={ng}')
            if problem == problems[0]:
                handles.append(sc)
                labels.append(f'{label_prefix}={ng}')
        ax.set_title(problem, fontsize=14, fontweight='bold')
        ax.set_xlabel('f1')
        ax.set_ylabel('f2')
        ax.grid(True, color='#e4e7ee', linestyle='--', linewidth=0.8, alpha=0.9)
    fig.suptitle(f'{title_prefix} PF Overlay by {label_prefix} (run=20)', fontsize=18, fontweight='bold', y=0.98)
    fig.legend(handles, labels, loc='upper center', ncol=5, frameon=True, title=label_prefix, bbox_to_anchor=(0.5, 0.94))
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    png = out / f'fig5_{group_key}_pf_overlay_run020_{label_prefix.lower()}_labeled.png'
    svg = out / f'fig5_{group_key}_pf_overlay_run020_{label_prefix.lower()}_labeled.svg'
    fig.savefig(png, bbox_inches='tight')
    fig.savefig(svg, bbox_inches='tight')
    plt.close(fig)
    print(png)
    print(svg)

plot_group('uf1237', 'UF1/2/3/7', 'NG')
plot_group('lsmop1459', 'LSMOP1/4/5/9', 'NG')
