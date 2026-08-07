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

METHODS = [
    "A_MPMO",
    "ECMADE_MOO",
    "GDE3",
    "MOEAD",
    "NSGAII",
    "SPEA2",
]

RUN_COUNT = 30


def parse_args():
    parser = argparse.ArgumentParser(
        description="Plot six methods as a 2x3 grid, with each subplot overlaying all runs."
    )
    parser.add_argument(
        "--instance-dir",
        type=Path,
        default=DEFAULT_INSTANCE_DIR,
        help="Instance folder containing method/run_XXX/pf_obj.csv outputs.",
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
        help="Plot raw objective values instead of global min-max normalized values.",
    )
    parser.add_argument(
        "--method-normalize",
        action="store_true",
        help="Normalize each method subplot independently instead of using one global scale.",
    )
    parser.add_argument(
        "--png-only",
        action="store_true",
        help="Save only PNG output and skip SVG output.",
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


def load_all_method_runs(instance_dir: Path, methods: list[str], run_count: int):
    data = {}
    for method in methods:
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
            warnings.warn(f"No usable pf_obj.csv files found for method {method}")
        data[method] = runs
    if not any(data.values()):
        raise FileNotFoundError("No usable pf_obj.csv files found for any method.")
    return data


def validate_objective_indices(data, x_obj: int, y_obj: int):
    x_idx = x_obj - 1
    y_idx = y_obj - 1
    if x_idx < 0 or y_idx < 0:
        raise ValueError("Objective indices are 1-based and must be >= 1.")
    n_obj = min(
        points.shape[1]
        for runs in data.values()
        for _, _, points in runs
    )
    if x_idx >= n_obj or y_idx >= n_obj:
        raise ValueError(
            f"Requested objectives ({x_obj}, {y_obj}), but loaded PF files have only {n_obj} columns."
        )
    return x_idx, y_idx


def bounds_from_xy_arrays(xy_arrays):
    all_points = np.vstack(xy_arrays)
    obj_min = np.min(all_points, axis=0)
    obj_max = np.max(all_points, axis=0)
    span = obj_max - obj_min
    span[span == 0.0] = 1.0
    return obj_min, span


def to_xy_data(data, x_idx: int, y_idx: int, raw: bool, method_normalize: bool):
    xy_data = {
        method: [(run_id, points[:, [x_idx, y_idx]]) for run_id, _, points in runs]
        for method, runs in data.items()
    }

    if raw:
        return xy_data, "raw"

    if method_normalize:
        normalized = {}
        for method, runs in xy_data.items():
            if not runs:
                normalized[method] = []
                continue
            obj_min, span = bounds_from_xy_arrays([xy for _, xy in runs])
            normalized[method] = [(run_id, (xy - obj_min) / span) for run_id, xy in runs]
        return normalized, "method-normalized"

    obj_min, span = bounds_from_xy_arrays(
        [xy for runs in xy_data.values() for _, xy in runs]
    )
    normalized = {
        method: [(run_id, (xy - obj_min) / span) for run_id, xy in runs]
        for method, runs in xy_data.items()
    }
    return normalized, "global-normalized"


def instance_label(instance_dir: Path) -> str:
    return f"{instance_dir.parent.name}/{instance_dir.name}"


def plot_method_grid(xy_data, instance_dir: Path, scale_label: str, x_obj: int, y_obj: int):
    fig, axes = plt.subplots(2, 3, figsize=(16, 9.5), dpi=180, sharex=True, sharey=True)
    axes = axes.ravel()
    cmap = plt.get_cmap("tab20")

    for ax, method in zip(axes, METHODS):
        runs = xy_data.get(method, [])
        for i, (run_id, xy) in enumerate(runs):
            order = np.argsort(xy[:, 0])
            xy = xy[order]
            color = cmap(i % cmap.N)
            ax.scatter(
                xy[:, 0],
                xy[:, 1],
                s=12,
                alpha=0.52,
                color=color,
                edgecolors="none",
            )
            ax.plot(xy[:, 0], xy[:, 1], color=color, alpha=0.22, linewidth=0.75)

        ax.set_title(f"{method} ({len(runs)} runs)", fontsize=12, fontweight="bold")
        ax.grid(True, color="#e4e7ee", linestyle="--", linewidth=0.8, alpha=0.9)

    for ax in axes[::3]:
        ax.set_ylabel(f"{scale_label} f{y_obj}")
    for ax in axes[-3:]:
        ax.set_xlabel(f"{scale_label} f{x_obj}")

    fig.suptitle(
        f"PF Overlay Across Runs by Method\n{instance_label(instance_dir)}",
        fontsize=16,
        fontweight="bold",
        y=0.995,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.965])
    return fig


def save_outputs(fig, output_dir: Path, scale_label: str, png_only: bool):
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"all_methods_pf_runs_grid_{scale_label}"
    png = output_dir / f"{stem}.png"
    svg = output_dir / f"{stem}.svg"
    fig.savefig(png, bbox_inches="tight")
    outputs = [png]
    if not png_only:
        fig.savefig(svg, bbox_inches="tight")
        outputs.append(svg)
    plt.close(fig)
    return outputs


def main():
    args = parse_args()
    output_dir = args.output_dir or (args.instance_dir / "figures")

    data = load_all_method_runs(args.instance_dir, METHODS, args.run_count)
    x_idx, y_idx = validate_objective_indices(data, args.x_obj, args.y_obj)
    xy_data, scale_label = to_xy_data(
        data=data,
        x_idx=x_idx,
        y_idx=y_idx,
        raw=args.raw,
        method_normalize=args.method_normalize,
    )
    fig = plot_method_grid(
        xy_data=xy_data,
        instance_dir=args.instance_dir,
        scale_label=scale_label,
        x_obj=args.x_obj,
        y_obj=args.y_obj,
    )
    outputs = save_outputs(fig, output_dir, scale_label, png_only=args.png_only)
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
