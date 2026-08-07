from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "README.zh-TW.md",
    "LICENSE",
    "CITATION.cff",
    "environment.yml",
    "requirements.txt",
    "system/software_environment.md",
    "configs/common_experiment_config.yaml",
    "configs/algorithm_parameters.yaml",
    "configs/theta_L24.csv",
    "data/synthetic/split_manifest.csv",
    "labels/label_formula.md",
    "labels/train_raw_run_metrics.csv",
    "labels/validation_raw_run_metrics.csv",
    "selector/selector_no_replicate.joblib",
    "selector/feature_columns_no_replicate.json",
    "selector/test_theta_predictions.csv",
    "selector/test_selected_theta.csv",
    "experiments/experiment_a/experiment_A_run_metrics.csv",
    "experiments/experiment_a/experiment_A_instance_method_summary.csv",
    "experiments/experiment_a/experiment_A_statistical_tests.csv",
    "experiments/experiment_bc/formal_five_run_metrics.csv",
    "experiments/experiment_bc/formal_five_friedman_tests.csv",
    "experiments/experiment_bc/formal_five_primary_method_wilcoxon_holm.csv",
    "real_market/configured_run_metrics_with_pf_stability.csv",
    "real_market/configured_friedman_tests.csv",
    "real_market/configured_pairwise_wilcoxon_holm.csv",
    "paper_outputs/table_experiment_a.csv",
    "paper_outputs/table_experiment_c.csv",
    "paper_outputs/table_real_market.csv",
    "logs/full_run_logs.zip",
    "figures/paper_figures.zip",
    "manifest/raw_pf_archive_parts.csv",
    "manifest/code_inventory.csv",
    "manifest/external_artifacts.csv",
    "manifest/supplementary_package_checklist.csv",
    "manifest/artifact_checksums.sha256",
]

MINIMUM_BYTES = {
    "selector/selector_no_replicate.joblib": 50_000_000,
    "logs/full_run_logs.zip": 10_000_000,
    "figures/paper_figures.zip": 10_000_000,
}

EXPECTED_CSV_ROWS = {
    "data/synthetic/split_manifest.csv": 192,
    "configs/theta_L24.csv": 24,
    "selector/test_theta_predictions.csv": 768,
    "selector/test_selected_theta.csv": 32,
    "paper_outputs/table_experiment_a.csv": 1272,
    "paper_outputs/table_experiment_c.csv": 5,
    "paper_outputs/table_real_market.csv": 4,
}

ARCHIVES = [
    "logs/full_run_logs.zip",
    "figures/paper_figures.zip",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def check_required_files() -> None:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        fail("missing required files:\n- " + "\n- ".join(missing))
    for relative, minimum in MINIMUM_BYTES.items():
        path = ROOT / relative
        if path.stat().st_size < minimum:
            fail(f"{relative} is too small ({path.stat().st_size} bytes); Git LFS may not be materialized")
        with path.open("rb") as handle:
            if handle.read(80).startswith(b"version https://git-lfs.github.com/spec/"):
                fail(f"{relative} is still a Git LFS pointer")
    raw_parts = read_csv(ROOT / "manifest/raw_pf_archive_parts.csv")
    if not raw_parts:
        fail("raw PF archive-parts manifest is empty")
    for row in raw_parts:
        relative = row.get("package_path", "")
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size < 1_000_000:
            fail(f"raw PF archive part is missing or too small: {relative}")
        if path.stat().st_size >= 2_000_000_000:
            fail(f"raw PF archive part exceeds the portable Git LFS target: {relative}")
        with path.open("rb") as handle:
            if handle.read(80).startswith(b"version https://git-lfs.github.com/spec/"):
                fail(f"{relative} is still a Git LFS pointer")


def check_split_and_selector() -> None:
    rows = read_csv(ROOT / "data/synthetic/split_manifest.csv")
    counts = Counter(row.get("split", "") for row in rows)
    expected = {"train": 112, "validation": 48, "test": 32}
    if counts != expected:
        fail(f"split mismatch: observed={dict(counts)}, expected={expected}")
    identifiers = [row.get("instance", "") for row in rows]
    if len(identifiers) != len(set(identifiers)):
        fail("split manifest contains duplicate instance identifiers")
    features = json.loads((ROOT / "selector/feature_columns_no_replicate.json").read_text(encoding="utf-8"))
    if "replicate" in json.dumps(features).lower():
        fail("replicate appears in the formal no-replicate selector features")


def check_csv_shapes() -> None:
    for relative, expected_rows in EXPECTED_CSV_ROWS.items():
        observed = len(read_csv(ROOT / relative))
        if observed != expected_rows:
            fail(f"{relative} has {observed} rows; expected {expected_rows}")


def check_manifests() -> None:
    artifacts = read_csv(ROOT / "manifest/external_artifacts.csv")
    unresolved = [
        row.get("package_path", "")
        for row in artifacts
        if row.get("included_in_github", "").lower() != "yes"
        or row.get("external_url", "").strip().upper() in {"", "TODO"}
    ]
    if unresolved:
        fail("artifact manifest still contains unresolved entries:\n- " + "\n- ".join(unresolved))
    checklist = read_csv(ROOT / "manifest/supplementary_package_checklist.csv")
    incomplete = [
        row.get("requested_item", "")
        for row in checklist
        if row.get("status", "").lower() != "complete"
    ]
    if incomplete:
        fail("supplementary checklist is incomplete:\n- " + "\n- ".join(incomplete))
    code_inventory = read_csv(ROOT / "manifest/code_inventory.csv")
    if len(code_inventory) < 300:
        fail(f"code inventory has only {len(code_inventory)} entries")


def check_checksums() -> None:
    manifest = ROOT / "manifest/artifact_checksums.sha256"
    entries: list[tuple[str, str]] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split(None, 1)
        entries.append((expected, relative.strip()))
    if not entries:
        fail("checksum manifest is empty")
    for expected, relative in entries:
        path = ROOT / relative
        if not path.is_file():
            fail(f"checksum target is missing: {relative}")
        observed = sha256(path)
        if observed.lower() != expected.lower():
            fail(f"SHA-256 mismatch for {relative}")


def check_archives(full_zip_test: bool) -> None:
    raw_parts = [row["package_path"] for row in read_csv(ROOT / "manifest/raw_pf_archive_parts.csv")]
    for relative in ARCHIVES + raw_parts:
        path = ROOT / relative
        try:
            with zipfile.ZipFile(path) as archive:
                members = archive.infolist()
                if not members:
                    fail(f"archive is empty: {relative}")
                if full_zip_test:
                    corrupt = archive.testzip()
                    if corrupt:
                        fail(f"CRC failure in {relative}: {corrupt}")
        except zipfile.BadZipFile as exc:
            fail(f"invalid ZIP archive {relative}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the complete TEVC supplementary package.")
    parser.add_argument("--full-zip-test", action="store_true", help="CRC-test every archived member.")
    args = parser.parse_args()

    check_required_files()
    check_split_and_selector()
    check_csv_shapes()
    check_manifests()
    check_checksums()
    check_archives(args.full_zip_test)

    print("PASS: complete TEVC supplementary package validated")
    print("PASS: code, bilingual README, environment, hardware/software record")
    print("PASS: logs, full tables, figures, and raw PF CSV archive")
    print("PASS: 112/48/32 split and no-replicate selector policy")
    print(f"PASS: SHA-256 checksums verified ({len((ROOT / 'manifest/artifact_checksums.sha256').read_text().splitlines())} artifacts)")
    if args.full_zip_test:
        print("PASS: full ZIP CRC test")


if __name__ == "__main__":
    main()
