#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_PROBLEMS = [f"UF{i}" for i in range(1, 8)] + [f"LSMOP{i}" for i in range(1, 10)]
DEFAULT_VARIANTS = ["RC1", "RC10", "RC20", "RC40", "RC80", "DVA20"]
VARIANT_LABELS = {
    "RC1": "RC, md=1",
    "RC10": "RC, md=10",
    "RC20": "RC, md=20",
    "RC40": "RC, md=40",
    "RC80": "RC, md=80",
    "DVA20": "DVA, md=20",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the PEATSD Table 2 DDS construction sweep and summarize IGD results."
    )
    parser.add_argument("--repo", type=Path, default=Path("."), help="PEATSD repository root")
    parser.add_argument("--problems", nargs="+", default=DEFAULT_PROBLEMS)
    parser.add_argument("--variants", nargs="+", default=DEFAULT_VARIANTS, choices=DEFAULT_VARIANTS)
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--num-obj", type=int, default=2)
    parser.add_argument("--num-var", type=int, default=500)
    parser.add_argument("--pop-size", type=int, default=100)
    parser.add_argument("--fe-limit", type=int, default=5_000_000)
    parser.add_argument("--nsp", type=int, default=20)
    parser.add_argument("--nis", type=int, default=10)
    parser.add_argument("--ngl", type=int, default=20)
    parser.add_argument("--cores", type=int, default=4)
    parser.add_argument("--binary", default="./bin/main", help="Binary used for experiments")
    parser.add_argument("--build-command", nargs="+", default=["make", "main"])
    parser.add_argument("--output-root", type=Path, default=Path("table2_dds_outputs"))
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path.home() / "lab" / "PEATSD_workspaces",
        help="Temporary workspaces used for patched DDS variants",
    )
    parser.add_argument("--resume", action="store_true", help="Reuse rows already present in the run CSV")
    parser.add_argument(
        "--skip-existing-workspace-build",
        action="store_true",
        help="Reuse an existing variant workspace and binary if present",
    )
    return parser.parse_args()


def variant_config(variant: str) -> tuple[int, int]:
    if variant.startswith("RC"):
        return 0, int(variant[2:])
    if variant.startswith("DVA"):
        return 1, int(variant[3:])
    raise ValueError(f"Unknown variant: {variant}")


def run_command(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def read_value(path: Path) -> float:
    return float(path.read_text(encoding="utf-8").strip().split()[0])


def load_existing(path: Path) -> dict[tuple[str, str, int], dict[str, object]]:
    rows: dict[tuple[str, str, int], dict[str, object]] = {}
    if not path.exists():
        return rows
    with path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            normalized = {
                "problem": row["problem"],
                "variant": row["variant"],
                "variant_label": row["variant_label"],
                "run": int(row["run"]),
                "runtime": float(row["runtime"]),
                "igd": float(row["igd"]),
            }
            rows[(normalized["problem"], normalized["variant"], normalized["run"])] = normalized
    return rows


def latest_metric(files: list[Path], metric: str) -> Path:
    candidates = [path for path in files if f"_{metric}_" in path.name]
    if not candidates:
        raise RuntimeError(f"Missing {metric} output in this run.")
    return max(candidates, key=lambda path: path.name)


def archive_new_files(files: list[Path], destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for src in files:
        shutil.move(str(src), str(destination / src.name))


def patch_regex(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"Failed to patch {label}")
    return updated


def patch_ptsd(
    ptsd_path: Path,
    dds_type: int,
    dds_max_dimension: int,
    nsp: int,
    nis: int,
    ngl: int,
) -> None:
    text = ptsd_path.read_text(encoding="utf-8")
    text = patch_regex(
        text,
        r"^#define\s+DDS_CONSTRUCTION_TYPE\s+\d+.*$",
        f"#define DDS_CONSTRUCTION_TYPE {dds_type}\t// 0: random construction; 1: by DVA (decision variable analysis, default)",
        "DDS_CONSTRUCTION_TYPE",
    )
    text = patch_regex(
        text,
        r"^#define\s+DDS_MAX_DIMENSION\s+\d+.*$",
        f"#define DDS_MAX_DIMENSION {dds_max_dimension}\t// maximum dimension of DDS",
        "DDS_MAX_DIMENSION",
    )
    text = patch_regex(text, r"int\s+NSP\s*=\s*\d+;", f"int\t\tNSP = {nsp};", "NSP")
    text = patch_regex(text, r"int\s+NIS\s*=\s*\d+;", f"int\t\tNIS = {nis};", "NIS")
    text = patch_regex(text, r"int\s+NGL\s*=\s*\d+;", f"int\t\tNGL = {ngl};", "NGL")
    ptsd_path.write_text(text, encoding="utf-8")


def prepare_workspace(
    base_repo: Path,
    workspace_root: Path,
    variant: str,
    build_command: list[str],
    nsp: int,
    nis: int,
    ngl: int,
    skip_existing_build: bool,
    extra_ignores: set[str],
) -> Path:
    workspace = workspace_root / f"table2_{variant.lower()}"
    binary = workspace / "bin" / "main"
    if skip_existing_build and binary.exists():
        return workspace
    if workspace.exists():
        shutil.rmtree(workspace)

    ignore_names = {
        ".git",
        "__pycache__",
        "raw",
        "bin",
        "output",
        "profile",
        workspace_root.name,
        *extra_ignores,
    }
    shutil.copytree(base_repo, workspace, ignore=shutil.ignore_patterns(*ignore_names, "*.o", "*.d"))
    (workspace / "bin").mkdir(exist_ok=True)
    (workspace / "output").mkdir(exist_ok=True)
    dds_type, md = variant_config(variant)
    patch_ptsd(workspace / "algorithm" / "ptsd.cpp", dds_type, md, nsp, nis, ngl)
    run_command(build_command, workspace)
    return workspace


def write_runs(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = ["problem", "variant", "variant_label", "run", "runtime", "igd"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def aggregate(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], dict[str, list[float]]] = {}
    for row in rows:
        key = (str(row["problem"]), str(row["variant"]))
        grouped.setdefault(key, {"runtime": [], "igd": []})
        grouped[key]["runtime"].append(float(row["runtime"]))
        grouped[key]["igd"].append(float(row["igd"]))

    result = []
    for (problem, variant), values in sorted(grouped.items(), key=lambda item: (item[0][0], DEFAULT_VARIANTS.index(item[0][1]))):
        result.append(
            {
                "problem": problem,
                "variant": variant,
                "variant_label": VARIANT_LABELS[variant],
                "runtime_mean": statistics.mean(values["runtime"]),
                "runtime_std": statistics.pstdev(values["runtime"]) if len(values["runtime"]) > 1 else 0.0,
                "igd_mean": statistics.mean(values["igd"]),
                "igd_std": statistics.pstdev(values["igd"]) if len(values["igd"]) > 1 else 0.0,
                "runs": len(values["igd"]),
            }
        )
    return result


def write_aggregate(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "problem",
        "variant",
        "variant_label",
        "runtime_mean",
        "runtime_std",
        "igd_mean",
        "igd_std",
        "runs",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def format_cell(mean: float, std: float) -> str:
    return f"{mean:.4e}({std:.2e})"


def write_table(path: Path, rows: list[dict[str, object]], problems: list[str], variants: list[str]) -> None:
    by_key = {(row["problem"], row["variant"]): row for row in rows}
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Pro.", *[VARIANT_LABELS[variant] for variant in variants]])
        for problem in problems:
            values = [problem]
            for variant in variants:
                row = by_key.get((problem, variant))
                if row is None:
                    values.append("")
                else:
                    values.append(format_cell(float(row["igd_mean"]), float(row["igd_std"])))
            writer.writerow(values)


def write_markdown_table(path: Path, rows: list[dict[str, object]], problems: list[str], variants: list[str]) -> None:
    by_key = {(row["problem"], row["variant"]): row for row in rows}
    headers = ["Pro.", *[VARIANT_LABELS[variant] for variant in variants]]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for problem in problems:
        cells = [problem]
        for variant in variants:
            row = by_key.get((problem, variant))
            cells.append("" if row is None else format_cell(float(row["igd_mean"]), float(row["igd_std"])))
        lines.append("| " + " | ".join(cells) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_workspace_outside_repo(repo: Path, workspace_root: Path) -> None:
    try:
        workspace_root.resolve().relative_to(repo.resolve())
    except ValueError:
        return
    raise RuntimeError("workspace_root must not be inside repo; otherwise copytree can recursively copy itself.")


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    output_root = (repo / args.output_root).resolve()
    raw_root = output_root / "raw"
    workspace_root = args.workspace_root.resolve()
    ensure_workspace_outside_repo(repo, workspace_root)
    output_root.mkdir(parents=True, exist_ok=True)
    raw_root.mkdir(parents=True, exist_ok=True)
    workspace_root.mkdir(parents=True, exist_ok=True)

    runs_csv = output_root / "table2_dds_runs.csv"
    aggregate_csv = output_root / "table2_dds_aggregate.csv"
    table_csv = output_root / "table2_igd_table.csv"
    table_md = output_root / "table2_igd_table.md"

    existing = load_existing(runs_csv) if args.resume else {}
    rows: list[dict[str, object]] = list(existing.values())
    workspaces: dict[str, Path] = {}

    for variant in args.variants:
        workspaces[variant] = prepare_workspace(
            repo,
            workspace_root,
            variant,
            args.build_command,
            args.nsp,
            args.nis,
            args.ngl,
            args.skip_existing_workspace_build,
            extra_ignores={args.output_root.name},
        )

    for problem in args.problems:
        for variant in args.variants:
            run_repo = workspaces[variant]
            output_dir = run_repo / "output"
            for run in range(1, args.runs + 1):
                key = (problem, variant, run)
                if key in existing:
                    print(f"Skipping existing result for {problem} {variant} run={run}", flush=True)
                    continue

                before = {path.name for path in output_dir.iterdir() if path.is_file()}
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
                run_command(command, run_repo, env=dict(os.environ))
                elapsed = time.time() - started

                new_files = [path for path in output_dir.iterdir() if path.is_file() and path.name not in before]
                time_file = latest_metric(new_files, "time")
                igd_file = latest_metric(new_files, "igd")
                archived = raw_root / problem / variant / f"run_{run:03d}"
                archive_new_files(new_files, archived)

                row = {
                    "problem": problem,
                    "variant": variant,
                    "variant_label": VARIANT_LABELS[variant],
                    "run": run,
                    "runtime": read_value(archived / time_file.name),
                    "igd": read_value(archived / igd_file.name),
                }
                rows.append(row)
                rows = sorted(rows, key=lambda item: (str(item["problem"]), DEFAULT_VARIANTS.index(str(item["variant"])), int(item["run"])))
                write_runs(runs_csv, rows)
                print(
                    f"Recorded {problem} {variant} run={run} runtime={row['runtime']:.6f} "
                    f"igd={row['igd']:.6e} wall={elapsed:.1f}s",
                    flush=True,
                )

    aggregated = aggregate(rows)
    write_aggregate(aggregate_csv, aggregated)
    write_table(table_csv, aggregated, args.problems, args.variants)
    write_markdown_table(table_md, aggregated, args.problems, args.variants)
    print(f"Wrote run summary to {runs_csv}")
    print(f"Wrote aggregate summary to {aggregate_csv}")
    print(f"Wrote Table 2 CSV to {table_csv}")
    print(f"Wrote Table 2 Markdown to {table_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
