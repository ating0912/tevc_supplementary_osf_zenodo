#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_PROBLEMS = [f"UF{i}" for i in range(1, 8)] + [f"LSMOP{i}" for i in range(1, 10)]
DEFAULT_NG_VALUES = [1, 10, 20, 40, 80]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the PEATSD Fig. 5 ng sweep and aggregate runtime/IGD results."
    )
    parser.add_argument("--repo", type=Path, default=Path("."), help="PEATSD repository root")
    parser.add_argument("--problems", nargs="+", default=DEFAULT_PROBLEMS)
    parser.add_argument("--ng-values", nargs="+", type=int, default=DEFAULT_NG_VALUES)
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--num-obj", type=int, default=2)
    parser.add_argument("--num-var", type=int, default=500)
    parser.add_argument("--pop-size", type=int, default=100)
    parser.add_argument("--fe-limit", type=int, default=5_000_000)
    parser.add_argument("--nsp", type=int, default=20)
    parser.add_argument("--nis", type=int, default=10)
    parser.add_argument("--cores", type=int, default=4)
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
        default=Path("fig5_outputs"),
        help="Directory used for summaries and archived raw outputs",
    )
    parser.add_argument("--skip-build", action="store_true", help="Skip rebuilding the binary before the sweep")
    parser.add_argument("--resume", action="store_true", help="Reuse rows already present in the summary CSV")
    parser.add_argument(
        "--rebuild-per-ng",
        action="store_true",
        help="Build a temporary workspace per ng by patching a copied ptsd.cpp for each ng setting.",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path.home() / "lab" / "PEATSD_workspaces",
        help="Temporary workspaces used when --rebuild-per-ng is enabled",
    )
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
                "ng": int(row["ng"]),
                "run": int(row["run"]),
                "runtime": float(row["runtime"]),
                "igd": float(row["igd"]),
            }
            rows[(normalized["problem"], normalized["ng"], normalized["run"])] = normalized
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
    fieldnames = ["problem", "ng", "run", "runtime", "igd"]
    with summary_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def aggregate(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, int], dict[str, list[float]]] = {}
    for row in rows:
        key = (str(row["problem"]), int(row["ng"]))
        grouped.setdefault(key, {"runtime": [], "igd": []})
        grouped[key]["runtime"].append(float(row["runtime"]))
        grouped[key]["igd"].append(float(row["igd"]))

    result = []
    for (problem, ng), values in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1])):
        result.append(
            {
                "problem": problem,
                "ng": ng,
                "runtime_mean": statistics.mean(values["runtime"]),
                "runtime_std": statistics.pstdev(values["runtime"]) if len(values["runtime"]) > 1 else 0.0,
                "igd_mean": statistics.mean(values["igd"]),
                "igd_std": statistics.pstdev(values["igd"]) if len(values["igd"]) > 1 else 0.0,
            }
        )
    return result


def write_aggregate_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = ["problem", "ng", "runtime_mean", "runtime_std", "igd_mean", "igd_std"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def patch_ptsd_constants(ptsd_path: Path, nsp: int, nis: int, ngl: int) -> None:
    text = ptsd_path.read_text(encoding="utf-8")
    patterns = {
        "NSP": (r"int\s+NSP\s*=\s*\d+;", f"int\t\tNSP = {nsp};"),
        "NIS": (r"int\s+NIS\s*=\s*\d+;", f"int\t\tNIS = {nis};"),
        "NGL": (r"int\s+NGL\s*=\s*\d+;", f"int\t\tNGL = {ngl};"),
    }
    for label, (pattern, replacement) in patterns.items():
        updated, count = re.subn(pattern, replacement, text, count=1)
        if count != 1:
            raise RuntimeError(f"Failed to patch {label} in {ptsd_path}")
        text = updated
    ptsd_path.write_text(text, encoding="utf-8")


def prepare_workspace(
    base_repo: Path,
    workspace_root: Path,
    build_command: list[str],
    nsp: int,
    nis: int,
    ngl: int,
    extra_ignores: set[str] | None = None,
) -> Path:
    workspace = workspace_root / f"ng_{ngl:03d}"
    if workspace.exists():
        shutil.rmtree(workspace)

    ignore_names = {
        ".git",
        "__pycache__",
        "raw",
        "bin",
        "output",
        "profile",
        "fig3_outputs",
        "fig4_outputs",
        "fig5_outputs",
        workspace_root.name,
    }
    if extra_ignores:
        ignore_names.update(extra_ignores)

    shutil.copytree(base_repo, workspace, ignore=shutil.ignore_patterns(*ignore_names, "*.o", "*.d"))
    (workspace / "bin").mkdir(exist_ok=True)
    (workspace / "output").mkdir(exist_ok=True)
    patch_ptsd_constants(workspace / "algorithm" / "ptsd.cpp", nsp, nis, ngl)
    run_command(build_command, workspace)
    return workspace


def ensure_no_recursive_workspace(base_repo: Path, workspace_root: Path, output_root: Path) -> None:
    try:
        workspace_root.relative_to(base_repo)
    except ValueError:
        pass
    else:
        raise RuntimeError(
            f"workspace_root ({workspace_root}) must not be inside the repository ({base_repo}); "
            "this can cause recursive self-copying."
        )

    try:
        output_root.relative_to(base_repo)
    except ValueError:
        pass
    else:
        return


def scale_linear(value: float, min_value: float, max_value: float, length: float) -> float:
    if max_value <= min_value:
        return 0.0
    return (value - min_value) / (max_value - min_value) * length


def render_svg(path: Path, rows: list[dict[str, object]], problems: list[str], ng_values: list[int]) -> None:
    uf_problems = [problem for problem in problems if problem.startswith("UF")]
    lsmop_problems = [problem for problem in problems if problem.startswith("LSMOP")]
    groups = []
    if uf_problems:
        groups.append(("UF", uf_problems))
    if lsmop_problems:
        groups.append(("LSMOP", lsmop_problems))
    if not groups:
        groups.append(("Problems", problems))

    single_problem = len(problems) == 1
    cols = 2
    rows_of_panels = 1 if single_problem else len(groups)
    width = 1700
    height = 560 if single_problem else 560 + (rows_of_panels - 1) * 495
    margin_left = 115
    margin_right = 35
    margin_top = 55
    margin_bottom = 85
    col_gap = 95
    row_gap = 120
    panel_width = (width - margin_left - margin_right - col_gap) / cols
    panel_height = (height - margin_top - margin_bottom - (row_gap if rows_of_panels > 1 else 0)) / rows_of_panels

    runtime_rows = {(row["problem"], row["ng"]): float(row["runtime_mean"]) for row in rows}
    igd_rows = {(row["problem"], row["ng"]): float(row["igd_mean"]) for row in rows}

    def nice_step(span: float) -> float:
        if span <= 0:
            return 1.0
        raw = span / 5.0
        magnitude = 10 ** math.floor(math.log10(raw))
        residual = raw / magnitude
        if residual <= 1:
            return 1 * magnitude
        if residual <= 2:
            return 2 * magnitude
        if residual <= 5:
            return 5 * magnitude
        return 10 * magnitude

    def panel_range(panel_problems: list[str], metric: str) -> tuple[float, float, list[float]]:
        source = runtime_rows if metric == "runtime" else igd_rows
        values = [source[(problem, ng)] for problem in panel_problems for ng in ng_values if (problem, ng) in source]
        if not values:
            return 0.0, 1.0, [0.0, 0.5, 1.0]
        min_value = min(values)
        max_value = max(values)
        step = nice_step(max_value - min_value)
        lower = math.floor(min_value / step) * step
        upper = math.ceil(max_value / step) * step
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
        if marker == "plus":
            return (
                f'<line x1="{x-6:.2f}" y1="{y:.2f}" x2="{x+6:.2f}" y2="{y:.2f}" stroke="{color}" stroke-width="2" />'
                f'<line x1="{x:.2f}" y1="{y-6:.2f}" x2="{x:.2f}" y2="{y+6:.2f}" stroke="{color}" stroke-width="2" />'
            )
        return (
            f'<line x1="{x-6:.2f}" y1="{y:.2f}" x2="{x+6:.2f}" y2="{y:.2f}" stroke="{color}" stroke-width="2" />'
            f'<line x1="{x:.2f}" y1="{y-6:.2f}" x2="{x:.2f}" y2="{y+6:.2f}" stroke="{color}" stroke-width="2" />'
            f'<line x1="{x-4:.2f}" y1="{y-4:.2f}" x2="{x+4:.2f}" y2="{y+4:.2f}" stroke="{color}" stroke-width="2" />'
            f'<line x1="{x-4:.2f}" y1="{y+4:.2f}" x2="{x+4:.2f}" y2="{y-4:.2f}" stroke="{color}" stroke-width="2" />'
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

        x_positions: dict[int, float] = {}
        min_ng = min(ng_values)
        max_ng = max(ng_values)
        for ng in ng_values:
            x = x0 + scale_linear(ng, min_ng, max_ng, panel_width)
            x_positions[ng] = x
            parts.append(f'<line x1="{x:.2f}" y1="{y0}" x2="{x:.2f}" y2="{y1}" class="grid" />')
            parts.append(f'<text x="{x:.2f}" y="{y0 + 30}" text-anchor="middle" class="tick">{ng}</text>')

        parts.append(f'<text x="{panel_x + panel_width / 2}" y="{y0 + 62}" text-anchor="middle" class="axis-label">Number of Generations ($n_g$)</text>')
        parts.append(f'<text x="{x0 - 72}" y="{panel_y + panel_height / 2}" text-anchor="middle" transform="rotate(-90 {x0 - 72} {panel_y + panel_height / 2})" class="axis-label">{y_label}</text>')

        for idx, problem in enumerate(panel_problems):
            color = palette[idx % len(palette)]
            marker = markers[idx % len(markers)]
            points = []
            for ng in ng_values:
                if (problem, ng) not in source:
                    continue
                x = x_positions[ng]
                value = source[(problem, ng)]
                y = y0 - scale_linear(value, min_y, max_y, panel_height)
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
        box_height = 12 + legend_h * len(panel_problems)
        box_width = legend_w + 20
        parts.append(f'<rect x="{legend_x - 10:.2f}" y="{legend_y - 18:.2f}" width="{box_width:.2f}" height="{box_height:.2f}" fill="white" stroke="#888" stroke-width="0.8" />')
        for idx, problem in enumerate(panel_problems):
            color = palette[idx % len(palette)]
            marker = markers[idx % len(markers)]
            y = legend_y + idx * legend_h
            parts.append(f'<line x1="{legend_x:.2f}" y1="{y:.2f}" x2="{legend_x + 24:.2f}" y2="{y:.2f}" stroke="{color}" stroke-width="2.4" />')
            parts.append(draw_marker(legend_x + 12, y, marker, color))
            parts.append(f'<text x="{legend_x + 32:.2f}" y="{y + 5:.2f}" class="legend">{problem}</text>')

    if single_problem:
        label = problems[0]
        draw_panel(margin_left, margin_top, f"{label} Runtime", [label], "runtime", "Runtime (s)")
        draw_panel(margin_left + panel_width + col_gap, margin_top, f"{label} IGD", [label], "igd", "IGD")
    else:
        for row, (group_name, group_problems) in enumerate(groups):
            panel_y = margin_top + row * (panel_height + row_gap)
            group_title = "UF1-UF7" if group_name == "UF" else "LSMOP1-LSMOP9" if group_name == "LSMOP" else group_name
            draw_panel(margin_left, panel_y, group_title, group_problems, "runtime", "Runtime (s)")
            draw_panel(margin_left + panel_width + col_gap, panel_y, group_title, group_problems, "igd", "IGD")
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    output_root = (repo / args.output_root).resolve()
    raw_root = output_root / "raw"
    workspace_root = args.workspace_root.resolve()
    summary_csv = output_root / "fig5_ng_runs.csv"
    aggregate_csv = output_root / "fig5_ng_aggregate.csv"
    figure_svg = output_root / "fig5_ng_summary.svg"
    output_root.mkdir(parents=True, exist_ok=True)
    raw_root.mkdir(parents=True, exist_ok=True)
    if args.rebuild_per_ng:
        ensure_no_recursive_workspace(repo, workspace_root, output_root)
        workspace_root.mkdir(parents=True, exist_ok=True)
    else:
        (repo / "output").mkdir(parents=True, exist_ok=True)

    existing = load_existing(summary_csv) if args.resume else {}
    rows: list[dict[str, object]] = list(existing.values())

    workspaces: dict[int, Path] = {}
    if not args.skip_build and not args.rebuild_per_ng:
        run_command(args.build_command, repo)

    for problem in args.problems:
        for ng in args.ng_values:
            run_repo = repo
            if args.rebuild_per_ng:
                if ng not in workspaces:
                    extra_ignores = {args.output_root.name}
                    workspaces[ng] = prepare_workspace(
                        repo,
                        workspace_root,
                        args.build_command,
                        args.nsp,
                        args.nis,
                        ng,
                        extra_ignores=extra_ignores,
                    )
                run_repo = workspaces[ng]
            output_dir = run_repo / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            for run in range(1, args.runs + 1):
                key = (problem, ng, run)
                if key in existing:
                    print(f"Skipping existing result for {problem} ng={ng} run={run}", flush=True)
                    continue

                before = {path.name for path in output_dir.iterdir() if path.is_file()}
                env = dict(os.environ)
                if not args.rebuild_per_ng:
                    env["PTSD_NSP"] = str(args.nsp)
                    env["PTSD_NIS"] = str(args.nis)
                    env["PTSD_NGL"] = str(ng)
                command = [
                    "mpiexec",
                    "-n",
                    str(args.cores),
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
                run_command(command, run_repo, env=env)
                elapsed = time.time() - started

                new_files = [path for path in output_dir.iterdir() if path.is_file() and path.name not in before]
                time_file = latest_metric(new_files, "time")
                igd_file = latest_metric(new_files, "igd")
                archived = raw_root / problem / f"ng_{ng:03d}" / f"run_{run:03d}"
                archive_new_files(new_files, archived)

                row = {
                    "problem": problem,
                    "ng": ng,
                    "run": run,
                    "runtime": read_value(archived / time_file.name),
                    "igd": read_value(archived / igd_file.name),
                }
                rows.append(row)
                write_summary(summary_csv, sorted(rows, key=lambda item: (item["problem"], item["ng"], item["run"])))
                print(
                    f"Recorded {problem} ng={ng} run={run} runtime={row['runtime']:.6f} "
                    f"igd={row['igd']:.6e} wall={elapsed:.1f}s",
                    flush=True,
                )

    aggregated = aggregate(rows)
    write_aggregate_csv(aggregate_csv, aggregated)
    render_svg(figure_svg, aggregated, args.problems, args.ng_values)
    print(f"Wrote run summary to {summary_csv}")
    print(f"Wrote aggregate summary to {aggregate_csv}")
    print(f"Wrote figure to {figure_svg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
