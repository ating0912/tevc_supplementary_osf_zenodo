from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED = [
    "README.md",
    "LICENSE",
    "environment.yml",
    "configs/common_experiment_config.yaml",
    "configs/algorithm_parameters.yaml",
    "configs/theta_L24.csv",
    "data/synthetic/split_manifest.csv",
    "labels/label_formula.md",
    "manifest/external_artifacts.csv",
    "manifest/supplementary_package_checklist.csv",
    "manifest/run_metric_schema.csv",
    "manifest/meta_feature_schema.csv",
    "system/software_environment.md",
    "selector/feature_columns_no_replicate.json",
    "selector/test_theta_predictions.csv",
    "selector/test_selected_theta.csv",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main() -> None:
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    if missing:
        fail("missing required GitHub files: " + ", ".join(missing))
    rows = read_csv(ROOT / "data/synthetic/split_manifest.csv")
    counts = Counter(row.get("split", "") for row in rows)
    expected = {"train": 112, "validation": 48, "test": 32}
    if counts != expected:
        fail(f"split mismatch: observed={dict(counts)}, expected={expected}")
    feature_columns = json.loads((ROOT / "selector/feature_columns_no_replicate.json").read_text(encoding="utf-8"))
    if "replicate" in json.dumps(feature_columns):
        fail("replicate appears in formal no-replicate feature columns")
    artifacts = read_csv(ROOT / "manifest/external_artifacts.csv")
    if not artifacts:
        fail("external artifact manifest is empty")
    checklist = read_csv(ROOT / "manifest/supplementary_package_checklist.csv")
    if not checklist:
        fail("supplementary package checklist is empty")
    print("OK: GitHub package structure is valid")
    print("OK: split manifest has 112/48/32 instances")
    print("OK: no-replicate selector feature list excludes replicate")
    print(f"OK: external artifacts listed: {len(artifacts)}")
    print(f"OK: supplementary checklist items listed: {len(checklist)}")


if __name__ == "__main__":
    main()
