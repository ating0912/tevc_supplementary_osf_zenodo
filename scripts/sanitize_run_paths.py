from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PERSONAL_ROOT = str(Path("C:/") / "Users" / "yiting" / "Documents" / "Playground")
FILES = {
    "experiments/experiment_bc/formal_five_run_metrics.csv": (
        PERSONAL_ROOT,
        "producer_outputs",
    ),
    "experiments/mokp/run_metrics.csv": (
        PERSONAL_ROOT,
        "producer_outputs",
    ),
    "real_market/configured_run_metrics_with_pf_stability.csv": (
        PERSONAL_ROOT,
        "producer_outputs",
    ),
    "experiments/selector_ablation/run_metrics.csv": (
        PERSONAL_ROOT,
        "producer_outputs",
    ),
}


def sanitize(relative: str, source_prefix: str, replacement: str) -> int:
    path = ROOT / relative
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        records = list(reader)
    if not fieldnames or "run_dir" not in fieldnames:
        raise SystemExit(f"Missing run_dir column: {relative}")
    changed = 0
    normalized_prefix = source_prefix.replace("\\", "/").rstrip("/")
    for record in records:
        original = record["run_dir"]
        normalized = original.replace("\\", "/")
        if normalized.lower().startswith(normalized_prefix.lower() + "/"):
            suffix = normalized[len(normalized_prefix):].lstrip("/")
            record["run_dir"] = f"{replacement}/{suffix}"
            changed += 1
        elif ":/" in normalized or normalized.startswith("/"):
            raise SystemExit(f"Unexpected absolute run_dir in {relative}: {original}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
    return changed


def main() -> None:
    total = 0
    for relative, (source_prefix, replacement) in FILES.items():
        changed = sanitize(relative, source_prefix, replacement)
        total += changed
        print(f"Sanitized {changed} run paths in {relative}")
    print(f"Sanitized {total} repository-external run paths")


if __name__ == "__main__":
    main()
