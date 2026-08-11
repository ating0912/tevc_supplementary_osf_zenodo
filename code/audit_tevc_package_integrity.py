from __future__ import annotations

import argparse
import csv
import json
import py_compile
from datetime import datetime
from pathlib import Path


def csv_shape(path: Path) -> tuple[int, int]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return len(rows), len(reader.fieldnames or [])


def compile_python(code_root: Path) -> tuple[int, list[str]]:
    failures: list[str] = []
    count = 0
    if not code_root.exists():
        return 0, [f"missing code root: {code_root}"]
    for path in sorted(code_root.rglob("*.py")):
        count += 1
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            failures.append(f"{path}: {exc}")
    return count, failures


def read_checklist(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("package_dir")
    parser.add_argument("--label", default="")
    args = parser.parse_args()

    root = Path(args.package_dir).resolve()
    report_path = root / "manifest/package_revalidation_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    py_count, py_failures = compile_python(root / "code")
    code_inventory_rows = read_checklist(root / "manifest/code_inventory.csv")
    checklist = read_checklist(root / "manifest/supplementary_package_checklist.csv")

    split_rows, split_cols = csv_shape(root / "data/synthetic/split_manifest.csv")
    split_data = read_checklist(root / "data/synthetic/split_manifest.csv")
    split_counts = {name: sum(1 for row in split_data if row.get("split") == name) for name in ["train", "validation", "test"]}

    key_csvs = [
        "configs/theta_L24.csv",
        "selector/test_theta_predictions.csv",
        "selector/test_selected_theta.csv",
        "paper_outputs/table_experiment_a.csv",
        "paper_outputs/table_experiment_c.csv",
        "paper_outputs/table_selector_final_test_ablation.csv",
        "paper_outputs/table_real_market_six_algorithm.csv",
        "paper_outputs/table_real_market_configuration_protocols.csv",
        "paper_outputs/table_mokp.csv",
    ]
    csv_lines = []
    for rel in key_csvs:
        path = root / rel
        if path.exists():
            rows, cols = csv_shape(path)
            csv_lines.append(f"- `{rel}`: {rows} rows, {cols} columns")
        else:
            csv_lines.append(f"- `{rel}`: missing")

    feature_path = root / "selector/feature_columns_no_replicate.json"
    contains_replicate = "not_checked"
    if feature_path.exists():
        features = json.loads(feature_path.read_text(encoding="utf-8"))
        contains_replicate = str("replicate" in json.dumps(features))

    archive_lines = []
    archives = ["logs/full_run_logs.zip", "figures/paper_figures.zip"]
    archives.extend(f"raw_pf/raw_pf_csv_part{part:02d}.zip" for part in range(1, 7))
    for rel in archives:
        path = root / rel
        if path.exists():
            archive_lines.append(f"- `{rel}`: present, {path.stat().st_size / (1024 * 1024):.2f} MB")
        else:
            archive_lines.append(f"- `{rel}`: not present in this package")

    checklist_lines = []
    for row in checklist:
        checklist_lines.append(f"- {row.get('requested_item')}: {row.get('status')} ({row.get('package_location')})")

    status = "PASS" if not py_failures and split_counts == {"train": 112, "validation": 48, "test": 32} and contains_replicate == "False" else "CHECK"
    lines = [
        "# Package Revalidation Report",
        "",
        f"- Package: `{root}`",
        f"- Label: {args.label or root.name}",
        f"- Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"- Overall status: **{status}**",
        "",
        "## Code Audit",
        "",
        f"- Code inventory entries: {len(code_inventory_rows)}",
        f"- Python files compiled: {py_count}",
        f"- Python compile failures: {len(py_failures)}",
    ]
    if py_failures:
        lines += ["", "### Python Compile Failures", ""]
        lines += [f"- {failure}" for failure in py_failures[:50]]
    lines += [
        "",
        "## Data Audit",
        "",
        f"- `data/synthetic/split_manifest.csv`: {split_rows} rows, {split_cols} columns",
        f"- Split counts: {split_counts}",
        f"- No-replicate feature list contains `replicate`: {contains_replicate}",
        "",
        "## Key CSV Shapes",
        "",
        *csv_lines,
        "",
        "## Supplementary Artifacts",
        "",
        *archive_lines,
        "",
        "## Checklist Snapshot",
        "",
        *checklist_lines,
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(report_path)
    print(status)


if __name__ == "__main__":
    main()
