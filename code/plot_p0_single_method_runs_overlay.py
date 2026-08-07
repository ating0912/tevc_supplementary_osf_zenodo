from pathlib import Path
import argparse
import warnings

import matplotlib.pyplot as plt
import numpy as np


DEFAULT_INSTANCE_DIR = Path(
    r"p0_lite_outputs"
    r"\synthetic_constrained_portfolio\test"
    r"\syn_n500_k30_pathological_cov_normal_extreme_events_r02_s20260818"
    r"\K_150"
)

DEFAULT_METHOD = "ECMADE_MOO"
RUN_COUNT = 30


def parse_args():
    parser = argparse.ArgumentParser(
        description="Plot one method's PF points overlaid across all runs."
    )
    parser.add_argument(
        "--instance-dir",
        type=Path,
        default=DEFAULT_INSTANCE_DIR,
        help="Instance folder containing method/run_XXX/pf_obj.csv outputs.",
    )
    parser.add_argument(
        "--method",
        default=DEFAULT_METHOD,
        help="Method folder name, e.g. A_MPMO, ECMADE_MOO, GDE3, MOEAD, NSGAII, SPEA2.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output folder. Defaults to <instance-dir>/figures.",
    )
    parser.add_argument(
        "--run-count",
        type=int,
        default=RUN_COUNT,
        help="Number of runs to scan from run_001 to run_N.",
    )
    parser.add_argument(
        "--x-obj",
        type=int,
        default=1,
        help="1-based objective index for x-axis.",
    )
    parser.add_argument(
        "--y-obj",
        type=int,
        default=2,
        help="1-based objective index for y-axis.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Plot raw objective values instead of min-max normalized values.",
    )
    parser.add_argument(
        "--show-legend",
        action="store_true",
        help="Show a compact run legend. Off by default because 30 runs is visually dense.",
    )
    return parser.parse_args()


def pf_path(instance_dir: Path, method: str, run_id: int) -> Path:
    return instance_dir / method / f"run_{run_id:03d}" / "pf_obj.csv"


def load_pf_obj(path: Path) -> np.ndarray:
    arr = np.genfromtxt(path, delimiter=",", dtype=float)
    if arr.size == 0:
        return np.empty((0, 0), dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    arr = arr[np.all(np.isfinite(arr), axis=1)]
    return arr


def load_method_runs(instance_dir: Path, method: str, run_count: int):
    runs = []
    for run_id in range(1, run_count + 1):
        path = pf_path(instance_dir, method, run_id)
        if not path.exists():
            warnings.warn(f"Missing PF file: {path}")
            continue
        points = load_pf_obj(path)
        if points.size == 0:
            warnings.warn(f"Empty PF file: {path}")
            continue
        runs.append((run_id, path, points))
    if not runs:
        raise FileNotFoundError(f"No usable pf_obj.csv files found for method {method}")
    return runs


def objective_bounds(runs, x_idx: int, y_idx: int):
    all_points = np.vstack([points[:, [x_idx, y_idx]] for _, _, points in runs])
    obj_min = np.min(all_points, axis=0)
    obj_max = np.max(all_points, axis=0)
    span = obj_max - obj_min
    span[span == 0.0] = 1.0
    return obj_min, span


def normalize_runs(runs, x_idx: int, y_idx: int):
    obj_min, span = objective_bounds(runs, x_idx, y_idx)
    normalized = []
    for run_id, path, points in runs:
        xy = points[:, [x_idx, y_idx]]
        normalized.append((run_id, path, (xy - obj_min) / span))
    return normalized


def select_raw_runs(runs, x_idx: int, y_idx: int):
    return [(run_id, path, points[:, [x_idx, y_idx]]) for run_id, path, points in runs]


def validate_objective_indices(runs, x_obj: int, y_obj: int):
    x_idx = x_obj - 1
    y_idx = y_obj - 1
    if x_idx < 0 or y_idx < 0:
        raise ValueError("Objective indices are 1-based and must be >= 1.")
    n_obj = min(points.shape[1] for _, _, points in runs)
    if x_idx >= n_obj or y_idx >= n_obj:
        raise ValueError(
            f"Requested objectives ({x_obj}, {y_obj}), but loaded PF files have only {n_obj} columns."
        )
    return x_idx, y_idx


def instance_label(instance_dir: Path) -> str:
    return f"{instance_dir.parent.name}/{instance_dir.name}"


def plot_runs_overlay(
    runs_xy,
    method: str,
    instance_dir: Path,
    normalized: bool,
    x_obj: int,
    y_obj: int,
    show_legend: bool,
):
    fig, ax = plt.subplots(figsize=(8.5, 6.5), dpi=180)
    cmap = plt.get_cmap("tab20")

    for i, (run_id, _, xy) in enumerate(runs_xy):
        order = np.argsort(xy[:, 0])
        xy = xy[order]
        color = cmap(i % cmap.N)
        ax.scatter(
            xy[:, 0],
            xy[:, 1],
            s=18,
            alpha=0.58,
            color=color,
            edgecolors="none",
            label=f"run_{run_id:03d}",
        )
        ax.plot(xy[:, 0], xy[:, 1], color=color, alpha=0.28, linewidth=0.9)

    scale_label = "normalized" if normalized else "raw"
    ax.set_title(
        f"{method} PF Overlay Across Runs\n{instance_label(instance_dir)}",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xlabel(f"{scale_label} f{x_obj}")
    ax.set_ylabel(f"{scale_label} f{y_obj}")
    ax.grid(True, color="#e4e7ee", linestyle="--", linewidth=0.8, alpha=0.9)

    if show_legend:
        ax.legend(
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            fontsize=7,
            frameon=True,
            ncol=1,
            title="Run",
        )

    fig.tight_layout()
    return fig


def save_outputs(fig, output_dir: Path, method: str, normalized: bool):
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "normalized" if normalized else "raw"
    stem = f"{method.lower()}_pf_runs_overlay_{suffix}"
    png = output_dir / f"{stem}.png"
    svg = output_dir / f"{stem}.svg"
    fig.savefig(png, bbox_inches="tight")
    fig.savefig(svg, bbox_inches="tight")
    plt.close(fig)
    return png, svg


def main():
    args = parse_args()
    output_dir = args.output_dir or (args.instance_dir / "figures")

    runs = load_method_runs(args.instance_dir, args.method, args.run_count)
    x_idx, y_idx = validate_objective_indices(runs, args.x_obj, args.y_obj)

    if args.raw:
        runs_xy = select_raw_runs(runs, x_idx, y_idx)
    else:
        runs_xy = normalize_runs(runs, x_idx, y_idx)

    fig = plot_runs_overlay(
        runs_xy=runs_xy,
        method=args.method,
        instance_dir=args.instance_dir,
        normalized=not args.raw,
        x_obj=args.x_obj,
        y_obj=args.y_obj,
        show_legend=args.show_legend,
    )
    png, svg = save_outputs(fig, output_dir, args.method, normalized=not args.raw)

    print(png)
    print(svg)


if __name__ == "__main__":
    main()
