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
    "audit_all_artifacts.py",
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
    "selector/figure_data/corrected_grouped_permutation_importance.csv",
    "selector/figure_data/corrected_grouped_impurity_importance.csv",
    "selector/figure_data/corrected_grouped_shap_importance.csv",
    "code/plot_grouped_feature_importance.py",
    "code/compute_corrected_selector_shap_20260809.py",
    "experiments/experiment_a/experiment_A_run_metrics.csv",
    "experiments/experiment_a/experiment_A_instance_method_summary.csv",
    "experiments/experiment_a/experiment_A_statistical_tests.csv",
    "experiments/experiment_bc/formal_five_run_metrics.csv",
    "experiments/experiment_bc/formal_five_run_completeness.csv",
    "experiments/experiment_bc/formal_five_friedman_tests.csv",
    "experiments/experiment_bc/formal_five_primary_method_wilcoxon_holm.csv",
    "experiments/selector_ablation/protocol.json",
    "experiments/selector_ablation/assignments.csv",
    "experiments/selector_ablation/run_completeness.csv",
    "experiments/selector_ablation/run_metrics.csv",
    "experiments/selector_ablation/selector_final_test_summary.csv",
    "experiments/selector_ablation/friedman.csv",
    "experiments/selector_ablation/pairwise_wilcoxon_holm.csv",
    "real_market/configured_run_metrics_with_pf_stability.csv",
    "real_market/six_algorithm_run_metrics.csv",
    "real_market/six_algorithm_endpoint_friedman_tests.csv",
    "real_market/six_algorithm_endpoint_primary_wilcoxon_holm.csv",
    "real_market/six_algorithm_transaction_cost_overall.csv",
    "real_market/configuration_protocol_endpoint_inventory.csv",
    "real_market/configuration_protocol_endpoint_pairwise_wilcoxon_holm.csv",
    "experiments/mokp/run_metrics.csv",
    "experiments/mokp/mokp_endpoint_friedman_tests.csv",
    "experiments/mokp/mokp_endpoint_pairwise_wilcoxon_holm.csv",
    "paper_outputs/table_experiment_a.csv",
    "paper_outputs/table_experiment_c.csv",
    "paper_outputs/table_selector_final_test_ablation.csv",
    "paper_outputs/table_real_market_six_algorithm.csv",
    "paper_outputs/table_real_market_configuration_protocols.csv",
    "paper_outputs/table_mokp.csv",
    "logs/full_run_logs.zip",
    "figures/paper_figures.zip",
    "manifest/raw_pf_archive_parts.csv",
    "manifest/code_inventory.csv",
    "manifest/external_artifacts.csv",
    "manifest/supplementary_package_checklist.csv",
    "manifest/artifact_checksums.sha256",
    "manifest/artifact_authority.csv",
    "manifest/code_authority.csv",
    "manifest/paper_value_crosscheck.csv",
    "docs/zenodo_release_checklist.md",
    "scripts/check_paper_values.py",
    "scripts/check_no_personal_paths.py",
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
    "selector/figure_data/corrected_grouped_permutation_importance.csv": 13,
    "selector/figure_data/corrected_grouped_impurity_importance.csv": 13,
    "selector/figure_data/corrected_grouped_shap_importance.csv": 13,
    "paper_outputs/table_experiment_a.csv": 1272,
    "paper_outputs/table_experiment_c.csv": 5,
    "paper_outputs/table_selector_final_test_ablation.csv": 4,
    "paper_outputs/table_real_market_six_algorithm.csv": 6,
    "paper_outputs/table_real_market_configuration_protocols.csv": 4,
    "experiments/selector_ablation/assignments.csv": 128,
    "experiments/selector_ablation/run_completeness.csv": 4,
    "experiments/experiment_bc/formal_five_run_completeness.csv": 5,
    "real_market/configuration_protocol_endpoint_inventory.csv": 16,
    "experiments/mokp/mokp_endpoint_friedman_tests.csv": 6,
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
    authority = read_csv(ROOT / "manifest/artifact_authority.csv")
    if not authority or not any(row["status"] == "audit_only" for row in authority):
        fail("artifact authority manifest does not identify audit-only historical files")
    invalid_authority = [
        row["path"]
        for row in authority
        if row["status"] == "audit_only" and row["used_in_manuscript"].lower() != "false"
    ]
    if invalid_authority:
        fail("audit-only artifacts are marked for manuscript use: " + ", ".join(invalid_authority))
    code_authority = read_csv(ROOT / "manifest/code_authority.csv")
    if not any(row["status"] == "disabled_legacy" for row in code_authority):
        fail("code authority manifest does not identify disabled legacy package builders")


def check_formal_inference_scope() -> None:
    six_friedman = read_csv(ROOT / "real_market/six_algorithm_endpoint_friedman_tests.csv")
    six_pairwise = read_csv(ROOT / "real_market/six_algorithm_endpoint_primary_wilcoxon_holm.csv")
    forbidden = {"rankscore", "windowrank", "crosswindowoverallrank"}
    observed = {
        row.get("metric", "").replace("_", "").lower()
        for row in six_friedman + six_pairwise
    }
    if observed & forbidden:
        fail(f"rank-derived metrics appear in formal six-algorithm inference: {observed & forbidden}")
    mokp = read_csv(ROOT / "experiments/mokp/mokp_endpoint_friedman_tests.csv")
    allowed = {"HV", "IGD", "PF_Overlap", "PF_Drift", "Diversity", "Runtime"}
    actual = {row["metric"] for row in mokp}
    if actual != allowed:
        fail(f"MOKP formal endpoint scope mismatch: observed={actual}, expected={allowed}")


def check_release_metadata() -> None:
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    zenodo = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
    if "version: 0.9.0-pre-release" not in citation or "date-released:" in citation:
        fail("CITATION.cff must remain pre-release and undated until the final archive exists")
    if zenodo.get("version") != "0.9.0-pre-release" or "publication_date" in zenodo:
        fail(".zenodo.json must remain pre-release and undated until the final archive exists")
    readmes = (ROOT / "README.md").read_text(encoding="utf-8") + (ROOT / "README.zh-TW.md").read_text(encoding="utf-8")
    if "ExperimentC_NoReplicate_ECMADE_MOO" in readmes or "24.6965944272" in readmes:
        fail("bilingual README still contains superseded Experiment C or RankScore conclusions")
    if "GitHub/OSF/Zenodo supplementary package" in readmes or "GitHub/OSF/Zenodo 預發行" in readmes:
        fail("README implies that OSF/Zenodo pre-release archives already exist")

    figure_map = read_csv(ROOT / "manifest/table_figure_map.csv")
    expected_figures = {
        "Fig. S2": (
            "figures/fig_feature_importance_no_replicate.png",
            "selector/figure_data/corrected_grouped_permutation_importance.csv;selector/figure_data/corrected_grouped_impurity_importance.csv",
        ),
        "Fig. S3": (
            "figures/fig_shap_global_importance_grouped.png",
            "selector/figure_data/corrected_grouped_shap_importance.csv",
        ),
    }
    mapped = {row["paper_artifact"]: row for row in figure_map}
    for label, (path, inputs) in expected_figures.items():
        row = mapped.get(label, {})
        if row.get("package_output") != path:
            fail(f"{label} is not explicitly mapped to {path}")
        if row.get("inputs") != inputs:
            fail(f"{label} does not identify its formal grouped CSV inputs")
        if row.get("script") != "code/plot_grouped_feature_importance.py":
            fail(f"{label} does not identify its executable renderer")

    report = (ROOT / "manifest/package_revalidation_report.md").read_text(encoding="utf-8")
    if "Core manuscript numerical-content revision: `70799c6`" not in report:
        fail("revalidation report does not identify 70799c6 as the core manuscript revision")
    if (
        "Figure-reconstruction inputs and reproducibility metadata: added in `d1cae50` "
        "without changing the reported manuscript values"
        not in report
    ):
        fail("revalidation report does not identify d1cae50 as the figure-reconstruction revision")
    if "Validated numerical-content revision:" in report:
        fail("revalidation report still uses the superseded numerical-content wording")
    if "Report metadata corrections:" in report:
        fail("revalidation report still describes d1cae50 as metadata-only")
    if "Base Git revision: `12a90a0`" in report:
        fail("revalidation report still identifies the superseded base revision")


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
    check_formal_inference_scope()
    check_release_metadata()
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
