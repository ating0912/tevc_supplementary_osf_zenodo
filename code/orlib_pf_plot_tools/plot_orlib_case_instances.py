from pathlib import Path
import argparse
import csv
from datetime import datetime
import subprocess
import sys


TOOL_DIR = Path(__file__).resolve().parent
ROOT = TOOL_DIR.parent
CASE_CSV = TOOL_DIR / "orlib_case_instances.csv"
GRID_SCRIPT = TOOL_DIR / "plot_orlib_all_methods_runs_grid.py"
OVERLAY_SCRIPT = TOOL_DIR / "plot_orlib_all_methods_pf_overlay.py"
HEATMAP_SCRIPT = TOOL_DIR / "plot_orlib_all_methods_pf_heatmap.py"
EAF_SCRIPT = TOOL_DIR / "plot_orlib_all_methods_eaf.py"
DEFAULT_OUTPUT_ROOT = ROOT / "orlib_pf_plot_outputs"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate OR-Library PF plots for selected Experiment A case instances."
    )
    parser.add_argument(
        "--case",
        choices=["typical", "good", "unstable", "all"],
        default="all",
        help="Which OR-Library case to plot.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Root folder for generated PNG outputs.",
    )
    parser.add_argument("--runs", type=int, default=30, help="Number of runs per method.")
    parser.add_argument("--raw", action="store_true", help="Use raw objective scale instead of normalized global scale.")
    parser.add_argument("--heatmap-bins", type=int, default=70, help="Heatmap bin count.")
    parser.add_argument("--eaf-grid-size", type=int, default=160, help="EAF grid resolution.")
    parser.add_argument("--skip-grid", action="store_true", help="Skip 2x3 per-method runs grid.")
    parser.add_argument("--skip-overlay", action="store_true", help="Skip all-method overlay.")
    parser.add_argument("--skip-heatmap", action="store_true", help="Skip heatmap grid.")
    parser.add_argument("--skip-eaf", action="store_true", help="Skip EAF band grid.")
    parser.add_argument(
        "--batch-id",
        default=None,
        help="Optional filename prefix batch id. Defaults to batch_<timestamp>.",
    )
    return parser.parse_args()


def load_cases():
    with CASE_CSV.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 10_000):
        candidate = path.with_name(f"{stem}_{index:03d}{suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Could not find a unique filename for {path}")


def safe_name(value):
    keep = []
    for ch in str(value):
        if ch.isalnum() or ch in {"-", "_", "."}:
            keep.append(ch)
        else:
            keep.append("_")
    return "".join(keep).strip("._") or "case"


def run_script(script, instance_dir, output_dir, output_prefix, extra_args):
    cmd = [
        sys.executable,
        str(script),
        "--instance-dir",
        str(instance_dir),
        "--output-dir",
        str(output_dir),
    ] + extra_args
    print("RUN", " ".join(f'"{x}"' if " " in x else x for x in cmd))
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        print("\nPlot script failed:")
        print(" ".join(cmd))
        if exc.stdout:
            print("\nstdout:")
            print(exc.stdout)
        if exc.stderr:
            print("\nstderr:")
            print(exc.stderr)
        raise

    outputs = []
    for line in result.stdout.splitlines():
        text = line.strip()
        if not text:
            continue
        output = Path(text)
        if output.exists():
            renamed = unique_path(output.with_name(f"{output_prefix}{output.name}"))
            output.rename(renamed)
            outputs.append(str(renamed))
        else:
            outputs.append(text)
    return outputs


def default_batch_id():
    return datetime.now().strftime("batch_%Y%m%d_%H%M%S_%f")


def main():
    args = parse_args()
    cases = load_cases()
    if args.case != "all":
        cases = [c for c in cases if c["case_label"] == args.case]
    if not cases:
        raise SystemExit(f"No cases selected for --case {args.case}")

    batch_id = safe_name(args.batch_id) if args.batch_id else default_batch_id()
    print(f"Output root: {args.output_root}")
    print(f"Batch id: {batch_id}")
    for case in cases:
        instance_dir = Path(case["instance_dir"])
        if not instance_dir.exists():
            raise FileNotFoundError(instance_dir)
        output_prefix = f"{batch_id}_{safe_name(case['case_label'])}_{safe_name(case['instance'])}_"
        overlay_dir = args.output_root / "overlay"
        heatmap_dir = args.output_root / "heatmap"
        eaf_dir = args.output_root / "eaf"
        print(f"=== {case['case_label']} | {case['instance']} | {instance_dir} ===")
        print(f"Output file prefix: {output_prefix}")
        print(f"Overlay output folder: {overlay_dir}")
        print(f"Heatmap output folder: {heatmap_dir}")
        print(f"EAF output folder: {eaf_dir}")

        common = ["--run-count", str(args.runs), "--png-only"]
        if args.raw:
            common.append("--raw")

        if not args.skip_grid:
            run_script(
                GRID_SCRIPT,
                instance_dir,
                overlay_dir,
                output_prefix,
                common,
            )
        if not args.skip_overlay:
            run_script(
                OVERLAY_SCRIPT,
                instance_dir,
                overlay_dir,
                output_prefix,
                common,
            )
        if not args.skip_heatmap:
            run_script(
                HEATMAP_SCRIPT,
                instance_dir,
                heatmap_dir,
                output_prefix,
                common + ["--bins", str(args.heatmap_bins)],
            )
        if not args.skip_eaf:
            run_script(
                EAF_SCRIPT,
                instance_dir,
                eaf_dir,
                output_prefix,
                common + ["--grid-size", str(args.eaf_grid_size)],
            )

    print(f"Outputs written under: {args.output_root}")


if __name__ == "__main__":
    main()
