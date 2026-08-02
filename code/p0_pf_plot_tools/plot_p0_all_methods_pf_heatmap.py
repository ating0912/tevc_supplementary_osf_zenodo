from pathlib import Path
import argparse
import warnings

import matplotlib.pyplot as plt
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
            "Plot PF density heatmaps for all methods and all runs "
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
        "--bins",
        type=int,
        default=60,
        help="Number of grid bins per objective axis.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Plot raw objective values instead of global min-max normalized values.",
    )
    parser.add_argument(
        "--linear",
        action="store_true",
        help="Use raw counts as color values. This is the default; kept for compatibility.",
    )
    parser.add_argument(
        "--log-counts",
        action="store_true",
        help="Use log1p(count) as color values instead of raw counts.",
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


def merge_runs_to_xy(data, x_idx: int, y_idx: int):
    xy_data = {}
    for method, runs in data.items():
        if not runs:
            xy_data[method] = np.empty((0, 2), dtype=float)
            continue
        xy_data[method] = np.vstack([points[:, [x_idx, y_idx]] for _, _, points in runs])
    return xy_data


def normalize_global(xy_data):
    all_points = np.vstack([xy for xy in xy_data.values() if xy.size > 0])
    obj_min = np.min(all_points, axis=0)
    obj_max = np.max(all_points, axis=0)
    span = obj_max - obj_min
    span[span == 0.0] = 1.0

    return {
        method: (xy - obj_min) / span if xy.size > 0 else xy
        for method, xy in xy_data.items()
    }


def data_range(xy_data, normalized: bool):
    if normalized:
        return [[0.0, 1.0], [0.0, 1.0]]

    all_points = np.vstack([xy for xy in xy_data.values() if xy.size > 0])
    x_min, y_min = np.min(all_points, axis=0)
    x_max, y_max = np.max(all_points, axis=0)
    if x_min == x_max:
        x_min -= 0.5
        x_max += 0.5
    if y_min == y_max:
        y_min -= 0.5
        y_max += 0.5
    return [[x_min, x_max], [y_min, y_max]]


def compute_heatmaps(xy_data, bins: int, hist_range, log_scale: bool):
    heatmaps = {}
    vmax = 0.0
    for method, xy in xy_data.items():
        if xy.size == 0:
            heat = np.zeros((bins, bins), dtype=float)
        else:
            heat, _, _ = np.histogram2d(
                xy[:, 0],
                xy[:, 1],
                bins=bins,
                range=hist_range,
            )
        if log_scale:
            heat = np.log1p(heat)
        heatmaps[method] = heat
        vmax = max(vmax, float(np.max(heat)))
    return heatmaps, vmax


def plot_heatmap_grid(
    heatmaps,
    raw_counts,
    point_counts,
    instance_dir: Path,
    hist_range,
    normalized: bool,
    x_obj: int,
    y_obj: int,
    vmax: float,
):
    fig, axes = plt.subplots(2, 3, figsize=(16, 9.5), dpi=180, sharex=True, sharey=True)
    axes = axes.ravel()

    x_range, y_range = hist_range
    extent = [x_range[0], x_range[1], y_range[0], y_range[1]]
    image = None

    for ax, method in zip(axes, METHODS):
        heat = heatmaps.get(method)
        if heat is None:
            heat = np.zeros_like(next(iter(heatmaps.values())))

        image = ax.imshow(
            heat.T,
            origin="lower",
            extent=extent,
            aspect="auto",
            cmap="YlOrRd",
            vmin=0,
            vmax=vmax if vmax > 0 else None,
            interpolation="nearest",
        )
        ax.set_title(
            f"{method} ({point_counts.get(method, 0)} PF points)",
            fontsize=12,
            fontweight="bold",
        )
        ax.grid(False)

    scale_label = "global-normalized" if normalized else "raw"
    for ax in axes[::3]:
        ax.set_ylabel(f"{scale_label} f{y_obj}")
    for ax in axes[-3:]:
        ax.set_xlabel(f"{scale_label} f{x_obj}")

    color_label = "出現次數" if raw_counts else "log1p(出現次數)"
    if image is not None:
        cbar_ax = fig.add_axes([0.91, 0.18, 0.018, 0.64])
        cbar = fig.colorbar(image, cax=cbar_ax)
        cbar.set_label(color_label)

    fig.suptitle(
        f"PF Density Heatmap by Method Across 30 Runs\n{instance_label(instance_dir)}",
        fontsize=16,
        fontweight="bold",
        y=0.995,
    )
    fig.subplots_adjust(left=0.06, right=0.88, bottom=0.08, top=0.86, wspace=0.10, hspace=0.28)
    return fig


def save_outputs(fig, output_dir: Path, normalized: bool, raw_counts: bool, png_only: bool):
    output_dir.mkdir(parents=True, exist_ok=True)
    scale_suffix = "global_normalized" if normalized else "raw"
    count_suffix = "linear_counts" if raw_counts else "log_counts"
    stem = f"all_methods_pf_heatmap_30runs_{scale_suffix}_{count_suffix}"
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
    xy_data = merge_runs_to_xy(data, x_idx, y_idx)

    if args.raw:
        plot_data = xy_data
    else:
        plot_data = normalize_global(xy_data)

    point_counts = {method: int(xy.shape[0]) for method, xy in plot_data.items()}
    hist_range = data_range(plot_data, normalized=not args.raw)
    use_log_counts = args.log_counts and not args.linear
    heatmaps, vmax = compute_heatmaps(
        xy_data=plot_data,
        bins=args.bins,
        hist_range=hist_range,
        log_scale=use_log_counts,
    )

    fig = plot_heatmap_grid(
        heatmaps=heatmaps,
        raw_counts=not use_log_counts,
        point_counts=point_counts,
        instance_dir=args.instance_dir,
        hist_range=hist_range,
        normalized=not args.raw,
        x_obj=args.x_obj,
        y_obj=args.y_obj,
        vmax=vmax,
    )
    outputs = save_outputs(
        fig,
        output_dir,
        normalized=not args.raw,
        raw_counts=not use_log_counts,
        png_only=args.png_only,
    )
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
