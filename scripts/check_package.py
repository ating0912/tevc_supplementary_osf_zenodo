from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED = [
    "README.md",
    "environment.yml",
    "configs/common_experiment_config.yaml",
    "configs/algorithm_parameters.yaml",
    "configs/theta_L24.csv",
    "data/synthetic/split_manifest.csv",
    "labels/label_formula.md",
    "selector/feature_columns_no_replicate.json",
    "selector/test_theta_predictions.csv",
    "selector/test_selected_theta.csv",
    "experiments/experiment_a/experiment_A_run_metrics.csv",
    "experiments/experiment_a/experiment_A_statistical_tests.csv",
    "manifest/source_file_map.csv",
    "manifest/reproducibility_checklist.csv",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def check_required() -> None:
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    if missing:
        fail("missing required files: " + ", ".join(missing))
    print(f"OK: required file set present ({len(REQUIRED)} files)")


def check_split_manifest() -> None:
    path = ROOT / "data/synthetic/split_manifest.csv"
    rows = read_csv(path)
    counts = Counter(row.get("split", "") for row in rows)
    expected = {"train": 112, "validation": 48, "test": 32}
    if counts != expected:
        fail(f"split counts mismatch: observed={dict(counts)}, expected={expected}")
    ids = [row["instance"] for row in rows]
    if len(ids) != len(set(ids)):
        fail("split_manifest.csv contains duplicate instance ids")
    print("OK: split manifest has 112/48/32 instances and unique ids")


def check_label_leakage() -> None:
    manifest = read_csv(ROOT / "data/synthetic/split_manifest.csv")
    test_ids = {row["instance"] for row in manifest if row["split"] == "test"}
    label_files = [
        ROOT / "labels/train_theta_ranking_labels.csv",
        ROOT / "labels/validation_theta_ranking_labels.csv",
        ROOT / "labels/train_raw_run_metrics.csv",
        ROOT / "labels/validation_raw_run_metrics.csv",
    ]
    for path in label_files:
        if not path.exists():
            continue
        rows = read_csv(path)
        if not rows or "instance" not in rows[0]:
            continue
        leaked = sorted({row["instance"] for row in rows if row.get("instance") in test_ids})
        if leaked:
            fail(f"test instances appear in {path.name}: {leaked[:5]}")
    print("OK: no test-instance leakage detected in present label files")


def check_selector_features() -> None:
    path = ROOT / "selector/feature_columns_no_replicate.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    text = json.dumps(data)
    if "replicate" in text:
        fail("formal feature_columns_no_replicate.json still contains replicate")
    print("OK: no-replicate selector feature list excludes replicate")


def main() -> None:
    check_required()
    check_split_manifest()
    check_label_leakage()
    check_selector_features()
    print("Package audit completed.")


if __name__ == "__main__":
    main()
