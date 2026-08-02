from pathlib import Path
import argparse
import warnings

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np


plt.rcParams["font.sans-serif"] = [
    "Microsoft JhengHei",
    "Microsoft YaHei",
    "SimHei",
    "Arial Unicode MS",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False


DEFAULT_INSTANCE_DIR = Path(
    r"C:\Users\yiting\Documents\Playground\p0_lite_outputs"
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
        description=(
            "Plot empirical attainment function contours for all methods and all runs "
            "under one instance folder."
        )
    )
    parser.add_argument(
        "--instance-dir",
        type=Path,
        default=DEFAULT_INSTANCE_DIR,
        help="Instance K folder containing method/run_XXX/pf_obj.csv outputs.",
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
        "--grid-size",
        type=int,
        default=120,
        help="Number of objective-space grid points per axis.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Plot raw objective values instead of global min-max normalized values.",
    )
    parser.add_argument(
        "--png-only",
        action="store_true",
        help="Save only PNG output and skip SVG output.",
    )
    return parser.parse_args()


def instance_label(instance_dir: Path) -> str:
    return f"{instance_dir.parent.name}/{instance_dir.name}"


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


def load_all_runs(instance_dir: Path, methods: list[str], run_count: int):
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
        data[method] = runs

    if not any(data.values()):
        raise FileNotFoundError(f"No usable pf_obj.csv files found under {instance_dir}")
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
            f"Requested objectives ({x_obj}, {y_obj}), but PF files have only {n_obj} columns."
        )
    return x_idx, y_idx


def select_xy_runs(data, x_idx: int, y_idx: int):
    return {
        method: [(run_id, path, points[:, [x_idx, y_idx]]) for run_id, path, points in runs]
        for method, runs in data.items()
    }


def normalize_global(xy_runs):
    all_points = np.vstack([
        xy
        for runs in xy_runs.values()
        for _, _, xy in runs
    ])
    obj_min = np.min(all_points, axis=0)
    obj_max = np.max(all_points, axis=0)
    span = obj_max - obj_min
    span[span == 0.0] = 1.0

    return {
        method: [(run_id, path, (xy - obj_min) / span) for run_id, path, xy in runs]
        for method, runs in xy_runs.items()
    }


def eaf_range(xy_runs, normalized: bool):
    if normalized:
        return (0.0, 1.0), (0.0, 1.0)

    all_points = np.vstack([
        xy
        for runs in xy_runs.values()
        for _, _, xy in runs
    ])
    mins = np.min(all_points, axis=0)
    maxs = np.max(all_points, axis=0)
    pad = (maxs - mins) * 0.03
    pad[pad == 0.0] = 0.5
    return (mins[0] - pad[0], maxs[0] + pad[0]), (mins[1] - pad[1], maxs[1] + pad[1])


def compute_eaf_for_method(runs, x_grid: np.ndarray, y_grid: np.ndarray):
    x_flat = x_grid.ravel()
    y_flat = y_grid.ravel()
    attained_count = np.zeros_like(x_flat, dtype=float)

    for _, _, xy in runs:
        if xy.size == 0:
            continue
        # Minimization EAF: a grid point is attained if any PF point dominates it.
        attained = np.any((xy[:, [0]] <= x_flat) & (xy[:, [1]] <= y_flat), axis=0)
        attained_count += attained.astype(float)

    if not runs:
        return np.zeros_like(x_grid, dtype=float)
    return (attained_count / len(runs)).reshape(x_grid.shape)


def compute_all_eafs(xy_runs, x_range, y_range, grid_size: int):
    x_values = np.linspace(x_range[0], x_range[1], grid_size)
    y_values = np.linspace(y_range[0], y_range[1], grid_size)
    x_grid, y_grid = np.meshgrid(x_values, y_values)

    eafs = {
        method: compute_eaf_for_method(runs, x_grid, y_grid)
        for method, runs in xy_runs.items()
    }
    return x_grid, y_grid, eafs


def plot_eaf_grid(
    x_grid,
    y_grid,
    eafs,
    xy_runs,
    instance_dir: Path,
    normalized: bool,
    x_obj: int,
    y_obj: int,
):
    fig, axes = plt.subplots(2, 3, figsize=(16, 9.5), dpi=180, sharex=True, sharey=True)
    axes = axes.ravel()

    for ax, method in zip(axes, METHODS):
        eaf = eafs.get(method, np.zeros_like(x_grid))

        if np.nanmin(eaf) <= 0.75 and np.nanmax(eaf) >= 0.25:
            ax.contourf(
                x_grid,
                y_grid,
                eaf,
                levels=[0.25, 0.75],
                colors=["#FDE68A"],
                alpha=0.58,
            )

        if np.nanmin(eaf) <= 0.25 <= np.nanmax(eaf):
            ax.contour(
                x_grid,
                y_grid,
                eaf,
                levels=[0.25],
                colors=["#FBBF24"],
                linewidths=[1.0],
                linestyles=["--"],
                alpha=0.9,
            )

        if np.nanmin(eaf) <= 0.75 <= np.nanmax(eaf):
            ax.contour(
                x_grid,
                y_grid,
                eaf,
                levels=[0.75],
                colors=["#F59E0B"],
                linewidths=[1.0],
                linestyles=["--"],
                alpha=0.9,
            )

        if np.nanmin(eaf) <= 0.50 <= np.nanmax(eaf):
            median = ax.contour(
                x_grid,
                y_grid,
                eaf,
                levels=[0.50],
                colors=["#111827"],
                linewidths=[2.0],
                linestyles=["-"],
            )
            ax.clabel(
                median,
                inline=True,
                fontsize=8,
                fmt={0.50: "50%"},
            )

        runs = xy_runs.get(method, [])
        ax.set_title(f"{method} ({len(runs)} runs)", fontsize=12, fontweight="bold")
        ax.grid(True, color="#E5E7EB", linestyle="--", linewidth=0.6, alpha=0.75)

    scale_label = "global-normalized" if normalized else "raw"
    for ax in axes[::3]:
        ax.set_ylabel(f"{scale_label} f{y_obj}")
    for ax in axes[-3:]:
        ax.set_xlabel(f"{scale_label} f{x_obj}")

    legend_handles = [
        Patch(facecolor="#FDE68A", edgecolor="none", alpha=0.58, label="25%-75% attainment band"),
        Line2D([0], [0], color="#111827", linewidth=2.0, label="50% attainment curve"),
        Line2D([0], [0], color="#F59E0B", linewidth=1.0, linestyle="--", label="25% / 75% boundaries"),
    ]
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.905),
        ncol=3,
        frameon=True,
    )

    fig.suptitle(
        f"EAF 25%-75% Band and 50% Curve by Method\n{instance_label(instance_dir)}",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )
    fig.subplots_adjust(left=0.06, right=0.98, bottom=0.08, top=0.82, wspace=0.10, hspace=0.28)
    return fig


def save_outputs(fig, output_dir: Path, normalized: bool, png_only: bool):
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "global_normalized" if normalized else "raw"
    stem = f"all_methods_eaf_band_30runs_{suffix}"
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

    data = load_all_runs(args.instance_dir, METHODS, args.run_count)
    x_idx, y_idx = validate_objective_indices(data, args.x_obj, args.y_obj)
    xy_runs = select_xy_runs(data, x_idx, y_idx)

    if args.raw:
        plot_runs = xy_runs
    else:
        plot_runs = normalize_global(xy_runs)

    x_range, y_range = eaf_range(plot_runs, normalized=not args.raw)
    x_grid, y_grid, eafs = compute_all_eafs(
        plot_runs,
        x_range=x_range,
        y_range=y_range,
        grid_size=args.grid_size,
    )
    fig = plot_eaf_grid(
        x_grid=x_grid,
        y_grid=y_grid,
        eafs=eafs,
        xy_runs=plot_runs,
        instance_dir=args.instance_dir,
        normalized=not args.raw,
        x_obj=args.x_obj,
        y_obj=args.y_obj,
    )
    outputs = save_outputs(fig, output_dir, normalized=not args.raw, png_only=args.png_only)
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
