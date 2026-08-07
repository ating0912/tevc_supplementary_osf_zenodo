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

METHOD_COLORS = {
    "A_MPMO": "#1f77b4",
    "ECMADE_MOO": "#d62728",
    "GDE3": "#2ca02c",
    "MOEAD": "#9467bd",
    "NSGAII": "#ff7f0e",
    "SPEA2": "#17becf",
}

RUN_COUNT = 30


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Plot normalized PF overlay for all methods and all runs "
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
        "--raw",
        action="store_true",
        help="Plot raw objective values instead of global min-max normalized values.",
    )
    parser.add_argument(
        "--no-lines",
        action="store_true",
        help="Only draw scatter points, without connecting each run's PF points.",
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


def select_xy(data, x_idx: int, y_idx: int):
    return {
        method: [(run_id, path, points[:, [x_idx, y_idx]]) for run_id, path, points in runs]
        for method, runs in data.items()
    }


def normalize_global(xy_data):
    all_points = np.vstack([
        xy
        for runs in xy_data.values()
        for _, _, xy in runs
    ])
    obj_min = np.min(all_points, axis=0)
    obj_max = np.max(all_points, axis=0)
    span = obj_max - obj_min
    span[span == 0.0] = 1.0

    return {
        method: [(run_id, path, (xy - obj_min) / span) for run_id, path, xy in runs]
        for method, runs in xy_data.items()
    }


def plot_overlay(
    xy_data,
    instance_dir: Path,
    normalized: bool,
    x_obj: int,
    y_obj: int,
    draw_lines: bool,
):
    fig, ax = plt.subplots(figsize=(10.5, 7.5), dpi=180)

    handles = []
    labels = []
    for method in METHODS:
        runs = xy_data.get(method, [])
        color = METHOD_COLORS.get(method, "#444444")

        first_handle = None
        for run_id, _, xy in runs:
            order = np.argsort(xy[:, 0])
            xy = xy[order]

            sc = ax.scatter(
                xy[:, 0],
                xy[:, 1],
                s=12,
                alpha=0.38,
                color=color,
                edgecolors="none",
            )
            if first_handle is None:
                first_handle = sc

            if draw_lines:
                ax.plot(xy[:, 0], xy[:, 1], color=color, alpha=0.16, linewidth=0.7)

        if first_handle is not None:
            handles.append(first_handle)
            labels.append(f"{method} ({len(runs)} runs)")

    scale_label = "global-normalized" if normalized else "raw"
    ax.set_title(
        f"PF Overlay by Method Across 30 Runs\n{instance_label(instance_dir)}",
        fontsize=15,
        fontweight="bold",
    )
    ax.set_xlabel(f"{scale_label} f{x_obj}")
    ax.set_ylabel(f"{scale_label} f{y_obj}")
    ax.grid(True, color="#e4e7ee", linestyle="--", linewidth=0.8, alpha=0.9)
    ax.legend(
        handles,
        labels,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=True,
        title="Method",
    )

    fig.tight_layout()
    return fig


def save_outputs(fig, output_dir: Path, normalized: bool, png_only: bool):
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "global_normalized" if normalized else "raw"
    stem = f"all_methods_pf_overlay_30runs_{suffix}"
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
    xy_data = select_xy(data, x_idx, y_idx)

    if args.raw:
        plot_data = xy_data
    else:
        plot_data = normalize_global(xy_data)

    fig = plot_overlay(
        xy_data=plot_data,
        instance_dir=args.instance_dir,
        normalized=not args.raw,
        x_obj=args.x_obj,
        y_obj=args.y_obj,
        draw_lines=not args.no_lines,
    )
    outputs = save_outputs(fig, output_dir, normalized=not args.raw, png_only=args.png_only)
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
