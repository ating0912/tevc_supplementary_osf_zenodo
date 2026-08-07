from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BASE = ROOT / "tevc_reproducibility_github"
OUT = ROOT / "tevc_reproducibility_github_replicate"
REPLICATE_SELECTOR = ROOT / "outputs/experiment_c_replicate_audit_20260730/replicate_included_audit"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def copy2(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def github_readme() -> str:
    return """
# TEVC Reproducibility Package - GitHub Replicate Version

This folder is the **replicate selector version** of the TEVC reproducibility package. It is intentionally separate from the formal no-replicate version.

## Version Definition

In this version, the selector feature set **includes `replicate`** as an input feature. This is useful for legacy comparison and audit reproduction, but it should not be described as the formal no-replicate selector unless the paper explicitly reports the replicate-included audit.

The relevant files are:

- `selector/feature_columns_replicate.json`
- `selector/test_theta_predictions_replicate.csv`
- `selector/test_selected_theta_replicate.csv`
- `selector/selector_performance_replicate.csv`

For convenience, compatibility aliases are also provided:

- `selector/feature_columns.json`
- `selector/test_theta_predictions.csv`
- `selector/test_selected_theta.csv`
- `selector/selector_performance.csv`

## Included Content

- Experiment configs and RNG policy.
- Official 112/48/32 split manifest.
- L24 theta candidate table.
- Replicate-included selector feature columns and prediction outputs.
- Paper summary tables and small statistical-test outputs.
- Samples for large CSV artifacts.
- `manifest/external_artifacts.csv` listing omitted heavyweight files, including the replicate selector model binary.

## Quick Check

```bash
python scripts/check_github_package.py
```

Expected checks:

- GitHub folder structure is valid.
- Split manifest is 112/48/32.
- Replicate selector feature list **contains** `replicate`.
- External artifacts are listed.

## Important Note

The `replicate` field appears in both the instance manifest and selector feature columns in this version. This is the distinguishing difference from the no-replicate package.
"""


def check_script() -> str:
    return """
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
    "manifest/run_metric_schema.csv",
    "manifest/meta_feature_schema.csv",
    "selector/feature_columns_replicate.json",
    "selector/test_theta_predictions_replicate.csv",
    "selector/test_selected_theta_replicate.csv",
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
        fail("missing required GitHub replicate files: " + ", ".join(missing))
    rows = read_csv(ROOT / "data/synthetic/split_manifest.csv")
    counts = Counter(row.get("split", "") for row in rows)
    expected = {"train": 112, "validation": 48, "test": 32}
    if counts != expected:
        fail(f"split mismatch: observed={dict(counts)}, expected={expected}")
    feature_columns = json.loads((ROOT / "selector/feature_columns_replicate.json").read_text(encoding="utf-8"))
    if "replicate" not in json.dumps(feature_columns):
        fail("replicate is missing from replicate selector feature columns")
    artifacts = read_csv(ROOT / "manifest/external_artifacts.csv")
    if not artifacts:
        fail("external artifact manifest is empty")
    print("OK: GitHub replicate package structure is valid")
    print("OK: split manifest has 112/48/32 instances")
    print("OK: replicate selector feature list contains replicate")
    print(f"OK: external artifacts listed: {len(artifacts)}")


if __name__ == "__main__":
    main()
"""


def update_external_artifacts() -> None:
    path = OUT / "manifest/external_artifacts.csv"
    rows = read_csv(path)
    for row in rows:
        if row["package_path"] == "selector/selector_no_replicate.joblib":
            row["package_path"] = "selector/selector_replicate.joblib"
            row["restore_to"] = "selector/selector_replicate.joblib"
            row["size_bytes"] = str((REPLICATE_SELECTOR / "experiment_c_stability_random_forest.joblib").stat().st_size)
            row["notes"] = "Replicate-included selector model. Store in Zenodo/OSF/GitHub Release/Git LFS, then fill external_url."
    write_csv(path, rows)


def write_version_manifest() -> None:
    feature_columns = json.loads((REPLICATE_SELECTOR / "feature_columns.json").read_text(encoding="utf-8"))
    numeric = feature_columns.get("numeric", [])
    categorical = feature_columns.get("categorical", [])
    rows = [
        {
            "version": "replicate",
            "selector_feature_policy": "replicate included",
            "contains_replicate_feature": "yes",
            "numeric_features": json.dumps(numeric),
            "categorical_features": json.dumps(categorical),
            "source_dir": str(REPLICATE_SELECTOR),
        }
    ]
    write_csv(OUT / "manifest/version_manifest.csv", rows)


def main() -> None:
    if not BASE.exists():
        raise SystemExit("Build tevc_reproducibility_github first.")
    if not REPLICATE_SELECTOR.exists():
        raise SystemExit(f"Missing replicate selector source: {REPLICATE_SELECTOR}")
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(BASE, OUT)
    for stale in [
        OUT / "selector/feature_columns_no_replicate.json",
    ]:
        if stale.exists():
            stale.unlink()

    write_text(OUT / "README.md", github_readme())
    write_text(OUT / "scripts/check_github_package.py", check_script())

    selector_map = {
        "feature_columns.json": "feature_columns_replicate.json",
        "test_theta_predicted_scores.csv": "test_theta_predictions_replicate.csv",
        "experiment_c_stability_theta_assignment.csv": "test_selected_theta_replicate.csv",
        "validation_predictions.csv": "validation_theta_predictions_replicate.csv",
        "validation_selector_summary.csv": "selector_performance_replicate.csv",
        "feature_importance_grouped.csv": "feature_importance_grouped_replicate.csv",
        "feature_importance_transformed.csv": "feature_importance_transformed_replicate.csv",
    }
    for src_name, dst_name in selector_map.items():
        copy2(REPLICATE_SELECTOR / src_name, OUT / "selector" / dst_name)

    compatibility_aliases = {
        "feature_columns_replicate.json": "feature_columns.json",
        "test_theta_predictions_replicate.csv": "test_theta_predictions.csv",
        "test_selected_theta_replicate.csv": "test_selected_theta.csv",
        "validation_theta_predictions_replicate.csv": "validation_theta_predictions.csv",
        "selector_performance_replicate.csv": "selector_performance.csv",
    }
    for src_name, dst_name in compatibility_aliases.items():
        copy2(OUT / "selector" / src_name, OUT / "selector" / dst_name)

    update_external_artifacts()
    write_version_manifest()
    print(f"Replicate GitHub package built at: {OUT}")


if __name__ == "__main__":
    main()
