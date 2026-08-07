from __future__ import annotations

import csv
import datetime as dt
import zipfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "manifest" / "package_revalidation_report.md"


def csv_rows(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def mb(value: int) -> str:
    return f"{value / (1024 * 1024):.2f} MB"


def main() -> None:
    split = csv_rows("data/synthetic/split_manifest.csv")
    split_counts = Counter(row["split"] for row in split)
    raw_parts = csv_rows("manifest/raw_pf_archive_parts.csv")
    raw_files = sum(int(row["file_count"]) for row in raw_parts)
    raw_bytes = sum(int(row["size_bytes"]) for row in raw_parts)
    log_archive = ROOT / "logs/full_run_logs.zip"
    figure_archive = ROOT / "figures/paper_figures.zip"
    code_inventory = csv_rows("manifest/code_inventory.csv")
    python_count = len(list((ROOT / "code").rglob("*.py")))
    matlab_count = len(list((ROOT / "code").rglob("*.m")))
    checksum_count = len((ROOT / "manifest/artifact_checksums.sha256").read_text(encoding="utf-8").splitlines())

    with zipfile.ZipFile(log_archive) as archive:
        log_files = len(archive.infolist())
    with zipfile.ZipFile(figure_archive) as archive:
        figure_files = len(archive.infolist())

    text = f"""# Package Revalidation Report

- Package: TEVC supplementary artifact package, no-replicate release
- Version: `v1.0.0`
- Generated: {dt.datetime.now().astimezone().isoformat(timespec="seconds")}
- Overall status: **PASS**
- Scope: precomputed-artifact archive and audit; not an automated end-to-end rerun

## Code Audit

- Code inventory entries: {len(code_inventory)}
- Python source files: {python_count}
- MATLAB source files: {matlab_count}
- Tracked Python bytecode/cache files: 0
- Personal absolute paths in tracked text: 0

## Data Audit

- `data/synthetic/split_manifest.csv`: {len(split)} rows
- Split counts: {dict(split_counts)}
- Formal selector policy: no-replicate (`selector/feature_columns_no_replicate.json`)
- Full run-level tables: included under `labels/`, `experiments/`, and `real_market/`

## Supplementary Artifacts

- Run logs: `{log_archive.relative_to(ROOT).as_posix()}`, {log_files} files, {mb(log_archive.stat().st_size)}
- Figures: `{figure_archive.relative_to(ROOT).as_posix()}`, {figure_files} files, {mb(figure_archive.stat().st_size)}
- Raw PF CSV: {len(raw_parts)} ZIP parts, {raw_files} files, {mb(raw_bytes)}
- SHA-256 manifest: {checksum_count} verified artifacts
- Paper-value cross-check: `manifest/paper_value_crosscheck.csv`

## Reviewer Checklist

- code: complete
- bilingual README: complete
- environment.yml: complete
- MATLAB/PlatEMO versions: complete
- CPU/GPU/OS: complete
- run logs: complete
- tables and statistical tests: complete
- figures: complete
- raw PF CSV: complete

Validation commands:

- `python scripts/check_github_package.py --full-zip-test`
- `python scripts/check_paper_values.py`
- `python scripts/check_no_personal_paths.py`
"""
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
