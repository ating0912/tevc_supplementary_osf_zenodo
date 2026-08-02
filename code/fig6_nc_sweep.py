#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_PROBLEMS = [f"UF{i}" for i in range(1, 8)] + [f"LSMOP{i}" for i in range(1, 10)]
DEFAULT_NC_VALUES = [1, 2, 4, 10, 20]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the PEATSD Fig. 6 nc sweep and aggregate runtime/IGD results."
    )
    parser.add_argument("--repo", type=Path, default=Path("."), help="PEATSD repository root")
    parser.add_argument("--problems", nargs="+", default=DEFAULT_PROBLEMS)
    parser.add_argument("--nc-values", nargs="+", type=int, default=DEFAULT_NC_VALUES)
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--num-obj", type=int, default=2)
    parser.add_argument("--num-var", type=int, default=500)
    parser.add_argument("--pop-size", type=int, default=100)
    parser.add_argument("--fe-limit", type=int, default=5_000_000)
    parser.add_argument("--binary", default="./bin/main", help="Binary used for experiments")
    parser.add_argument(
        "--build-command",
        nargs="+",
        default=["make", "main"],
        help="Command used to build the binary before running the sweep",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("fig6_outputs"),
        help="Directory used for summaries and archived raw outputs",
    )
    parser.add_argument("--skip-build", action="store_true", help="Skip rebuilding the binary before the sweep")
    parser.add_argument("--resume", action="store_true", help="Reuse rows already present in the summary CSV")
    return parser.parse_args()


def run_command(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def read_value(path: Path) -> float:
    return float(path.read_text(encoding="utf-8").strip().split()[0])


def load_existing(summary_csv: Path) -> dict[tuple[str, int, int], dict[str, object]]:
    rows: dict[tuple[str, int, int], dict[str, object]] = {}
    if not summary_csv.exists():
        return rows
    with summary_csv.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            normalized = {
                "problem": row["problem"],
                "nc": int(row["nc"]),
                "run": int(row["run"]),
                "runtime": float(row["runtime"]),
                "igd": float(row["igd"]),
            }
            rows[(normalized["problem"], normalized["nc"], normalized["run"])] = normalized
    return rows


def archive_new_files(files: list[Path], destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for src in files:
        shutil.move(str(src), str(destination / src.name))


def latest_metric(files: list[Path], metric: str) -> Path:
    metric_files = [path for path in files if f"_{metric}_" in path.name]
    if not metric_files:
        raise RuntimeError(f"Missing {metric} output in this run.")
    return max(metric_files, key=lambda path: path.name)


def write_summary(summary_csv: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = ["problem", "nc", "run", "runtime", "igd"]
    with summary_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def aggregate(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, int], dict[str, list[float]]] = {}
    for row in rows:
        key = (str(row["problem"]), int(row["nc"]))
        grouped.setdefault(key, {"runtime": [], "igd": []})
        grouped[key]["runtime"].append(float(row["runtime"]))
        grouped[key]["igd"].append(float(row["igd"]))

    result = []
    for (problem, nc), values in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1])):
        result.append(
            {
                "problem": problem,
                "nc": nc,
                "runtime_mean": statistics.mean(values["runtime"]),
                "runtime_std": statistics.pstdev(values["runtime"]) if len(values["runtime"]) > 1 else 0.0,
                "igd_mean": statistics.mean(values["igd"]),
                "igd_std": statistics.pstdev(values["igd"]) if len(values["igd"]) > 1 else 0.0,
            }
        )
    return result


def write_aggregate_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = ["problem", "nc", "runtime_mean", "runtime_std", "igd_mean", "igd_std"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def scale_linear(value: float, min_value: float, max_value: float, length: float) -> float:
    if max_value <= min_value:
        return 0.0
    return (value - min_value) / (max_value - min_value) * length


def nice_step(span: float) -> float:
    if span <= 0:
        return 1.0
    raw = span / 5.0
    magnitude = 10 ** math.floor(math.log10(raw))
    residual = raw / magnitude
    if residual <= 1:
        return magnitude
    if residual <= 2:
        return 2 * magnitude
    if residual <= 5:
        return 5 * magnitude
    return 10 * magnitude


def render_svg(path: Path, rows: list[dict[str, object]], problems: list[str], nc_values: list[int]) -> None:
    uf_problems = [problem for problem in problems if problem.startswith("UF")]
    lsmop_problems = [problem for problem in problems if problem.startswith("LSMOP")]
    groups = []
    if uf_problems:
        groups.append(("UF1-UF7", uf_problems))
    if lsmop_problems:
        groups.append(("LSMOP1-LSMOP9", lsmop_problems))
    if not groups:
        groups.append(("Problems", problems))

    rows_of_panels = len(groups)
    width = 1700
    height = 560 if rows_of_panels == 1 else 1055
    margin_left = 115
    margin_right = 35
    margin_top = 55
    margin_bottom = 85
    col_gap = 95
    row_gap = 120
    panel_width = (width - margin_left - margin_right - col_gap) / 2
    panel_height = (height - margin_top - margin_bottom - (row_gap if rows_of_panels > 1 else 0)) / rows_of_panels

    runtime_rows = {(row["problem"], row["nc"]): float(row["runtime_mean"]) for row in rows}
    igd_rows = {(row["problem"], row["nc"]): float(row["igd_mean"]) for row in rows}
    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22"]
    markers = ["circle", "square", "triangle", "diamond", "cross", "x", "star", "triangle_down", "plus"]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text { font-family: 'Times New Roman', serif; fill: #111; }",
        ".axis { stroke: #222; stroke-width: 1.2; }",
        ".grid { stroke: #d9d9d9; stroke-width: 1; }",
        ".panel-title { font-size: 26px; font-weight: bold; }",
        ".axis-label { font-size: 22px; font-weight: bold; }",
        ".tick { font-size: 18px; }",
        ".legend { font-size: 15px; }",
        "</style>",
    ]

    def panel_range(panel_problems: list[str], metric: str) -> tuple[float, float, list[float]]:
        source = runtime_rows if metric == "runtime" else igd_rows
        values = [source[(problem, nc)] for problem in panel_problems for nc in nc_values if (problem, nc) in source]
        if not values:
            return 0.0, 1.0, [0.0, 0.5, 1.0]
        lower = min(values)
        upper = max(values)
        step = nice_step(upper - lower)
        lower = math.floor(lower / step) * step
        upper = math.ceil(upper / step) * step
        if metric == "igd":
            lower = max(0.0, lower)
        if upper <= lower:
            upper = lower + step
        ticks = []
        tick = lower
        while tick <= upper + step * 0.5:
            ticks.append(tick)
            tick += step
        return lower, upper, ticks

    def draw_marker(x: float, y: float, marker: str, color: str) -> str:
        if marker == "circle":
            return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5.5" fill="{color}" stroke="{color}" />'
        if marker == "square":
            return f'<rect x="{x-5:.2f}" y="{y-5:.2f}" width="10" height="10" fill="{color}" stroke="{color}" />'
        if marker == "triangle":
            return f'<polygon points="{x:.2f},{y-6:.2f} {x-6:.2f},{y+5:.2f} {x+6:.2f},{y+5:.2f}" fill="{color}" stroke="{color}" />'
        if marker == "diamond":
            return f'<polygon points="{x:.2f},{y-6:.2f} {x-6:.2f},{y:.2f} {x:.2f},{y+6:.2f} {x+6:.2f},{y:.2f}" fill="{color}" stroke="{color}" />'
        if marker == "cross":
            return (
                f'<line x1="{x-5:.2f}" y1="{y:.2f}" x2="{x+5:.2f}" y2="{y:.2f}" stroke="{color}" stroke-width="2" />'
                f'<line x1="{x:.2f}" y1="{y-5:.2f}" x2="{x:.2f}" y2="{y+5:.2f}" stroke="{color}" stroke-width="2" />'
            )
        if marker == "x":
            return (
                f'<line x1="{x-5:.2f}" y1="{y-5:.2f}" x2="{x+5:.2f}" y2="{y+5:.2f}" stroke="{color}" stroke-width="2" />'
                f'<line x1="{x-5:.2f}" y1="{y+5:.2f}" x2="{x+5:.2f}" y2="{y-5:.2f}" stroke="{color}" stroke-width="2" />'
            )
        if marker == "triangle_down":
            return f'<polygon points="{x-6:.2f},{y-5:.2f} {x+6:.2f},{y-5:.2f} {x:.2f},{y+6:.2f}" fill="{color}" stroke="{color}" />'
        return (
            f'<line x1="{x-6:.2f}" y1="{y:.2f}" x2="{x+6:.2f}" y2="{y:.2f}" stroke="{color}" stroke-width="2" />'
            f'<line x1="{x:.2f}" y1="{y-6:.2f}" x2="{x:.2f}" y2="{y+6:.2f}" stroke="{color}" stroke-width="2" />'
        )

    def draw_panel(panel_x: float, panel_y: float, title: str, panel_problems: list[str], metric: str, y_label: str) -> None:
        min_y, max_y, y_ticks = panel_range(panel_problems, metric)
        source = runtime_rows if metric == "runtime" else igd_rows
        x0 = panel_x
        y0 = panel_y + panel_height
        x1 = panel_x + panel_width
        y1 = panel_y
        parts.append(f'<text x="{panel_x + panel_width / 2}" y="{panel_y - 12}" text-anchor="middle" class="panel-title">{title}</text>')
        parts.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" class="axis" />')
        parts.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" class="axis" />')
        for tick in y_ticks:
            y = y0 - scale_linear(tick, min_y, max_y, panel_height)
            parts.append(f'<line x1="{x0}" y1="{y:.2f}" x2="{x1}" y2="{y:.2f}" class="grid" />')
            label = f"{tick:.0f}" if metric == "runtime" else f"{tick:.3f}"
            parts.append(f'<text x="{x0 - 10}" y="{y + 6:.2f}" text-anchor="end" class="tick">{label}</text>')
        x_positions = {}
        for nc in nc_values:
            x = x0 + scale_linear(nc, min(nc_values), max(nc_values), panel_width)
            x_positions[nc] = x
            parts.append(f'<line x1="{x:.2f}" y1="{y0}" x2="{x:.2f}" y2="{y1}" class="grid" />')
            parts.append(f'<text x="{x:.2f}" y="{y0 + 30}" text-anchor="middle" class="tick">{nc}</text>')
        parts.append(f'<text x="{panel_x + panel_width / 2}" y="{y0 + 62}" text-anchor="middle" class="axis-label">Number of Cores ($n_c$)</text>')
        parts.append(f'<text x="{x0 - 72}" y="{panel_y + panel_height / 2}" text-anchor="middle" transform="rotate(-90 {x0 - 72} {panel_y + panel_height / 2})" class="axis-label">{y_label}</text>')
        for idx, problem in enumerate(panel_problems):
            color = palette[idx % len(palette)]
            marker = markers[idx % len(markers)]
            points = []
            for nc in nc_values:
                if (problem, nc) not in source:
                    continue
                x = x_positions[nc]
                y = y0 - scale_linear(source[(problem, nc)], min_y, max_y, panel_height)
                points.append((x, y))
            if len(points) < 2:
                continue
            parts.append(f'<polyline points="{" ".join(f"{x:.2f},{y:.2f}" for x, y in points)}" fill="none" stroke="{color}" stroke-width="2.4" />')
            for x, y in points:
                parts.append(draw_marker(x, y, marker, color))
        legend_x = panel_x + panel_width * 0.58
        legend_y = panel_y + panel_height * 0.16
        legend_h = 24
        legend_w = 118 if "UF" in title else 145
        parts.append(f'<rect x="{legend_x - 10:.2f}" y="{legend_y - 18:.2f}" width="{legend_w + 20:.2f}" height="{12 + legend_h * len(panel_problems):.2f}" fill="white" stroke="#888" stroke-width="0.8" />')
        for idx, problem in enumerate(panel_problems):
            color = palette[idx % len(palette)]
            marker = markers[idx % len(markers)]
            y = legend_y + idx * legend_h
            parts.append(f'<line x1="{legend_x:.2f}" y1="{y:.2f}" x2="{legend_x + 24:.2f}" y2="{y:.2f}" stroke="{color}" stroke-width="2.4" />')
            parts.append(draw_marker(legend_x + 12, y, marker, color))
            parts.append(f'<text x="{legend_x + 32:.2f}" y="{y + 5:.2f}" class="legend">{problem}</text>')

    for row_idx, (group_title, group_problems) in enumerate(groups):
        panel_y = margin_top + row_idx * (panel_height + row_gap)
        draw_panel(margin_left, panel_y, group_title, group_problems, "runtime", "Runtime (s)")
        draw_panel(margin_left + panel_width + col_gap, panel_y, group_title, group_problems, "igd", "IGD")
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    output_root = (repo / args.output_root).resolve()
    raw_root = output_root / "raw"
    summary_csv = output_root / "fig6_nc_runs.csv"
    aggregate_csv = output_root / "fig6_nc_aggregate.csv"
    figure_svg = output_root / "fig6_nc_summary.svg"
    output_root.mkdir(parents=True, exist_ok=True)
    raw_root.mkdir(parents=True, exist_ok=True)
    (repo / "output").mkdir(parents=True, exist_ok=True)

    existing = load_existing(summary_csv) if args.resume else {}
    rows: list[dict[str, object]] = list(existing.values())

    if not args.skip_build:
        run_command(args.build_command, repo)

    for problem in args.problems:
        for nc in args.nc_values:
            output_dir = repo / "output"
            for run in range(1, args.runs + 1):
                key = (problem, nc, run)
                if key in existing:
                    print(f"Skipping existing result for {problem} nc={nc} run={run}", flush=True)
                    continue
                before = {path.name for path in output_dir.iterdir() if path.is_file()}
                command = [
                    "mpiexec",
                    "-n",
                    str(nc),
                    args.binary,
                    "PTSD",
                    problem,
                    str(args.num_obj),
                    str(args.num_var),
                    str(args.pop_size),
                    str(args.fe_limit),
                    str(run),
                ]
                started = time.time()
                run_command(command, repo, env=dict(os.environ))
                elapsed = time.time() - started
                new_files = [path for path in output_dir.iterdir() if path.is_file() and path.name not in before]
                time_file = latest_metric(new_files, "time")
                igd_file = latest_metric(new_files, "igd")
                archived = raw_root / problem / f"nc_{nc:03d}" / f"run_{run:03d}"
                archive_new_files(new_files, archived)
                row = {
                    "problem": problem,
                    "nc": nc,
                    "run": run,
                    "runtime": read_value(archived / time_file.name),
                    "igd": read_value(archived / igd_file.name),
                }
                rows.append(row)
                write_summary(summary_csv, sorted(rows, key=lambda item: (item["problem"], item["nc"], item["run"])))
                print(
                    f"Recorded {problem} nc={nc} run={run} runtime={row['runtime']:.6f} "
                    f"igd={row['igd']:.6e} wall={elapsed:.1f}s",
                    flush=True,
                )

    aggregated = aggregate(rows)
    write_aggregate_csv(aggregate_csv, aggregated)
    render_svg(figure_svg, aggregated, args.problems, args.nc_values)
    print(f"Wrote run summary to {summary_csv}")
    print(f"Wrote aggregate summary to {aggregate_csv}")
    print(f"Wrote figure to {figure_svg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
