from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "manifest" / "artifact_checksums.sha256"

TARGETS = [
    "logs/full_run_logs.zip",
    "figures/paper_figures.zip",
    "selector/selector_no_replicate.joblib",
    "selector/figure_data/corrected_grouped_permutation_importance.csv",
    "selector/figure_data/corrected_grouped_impurity_importance.csv",
    "selector/figure_data/corrected_grouped_shap_importance.csv",
    "code/plot_grouped_feature_importance.py",
    "code/compute_corrected_selector_shap_20260809.py",
    "labels/train_raw_run_metrics.csv",
    "labels/validation_raw_run_metrics.csv",
    "labels/train_theta_summary.csv",
    "labels/validation_theta_summary.csv",
    "labels/train_theta_ranking_labels.csv",
    "labels/validation_theta_ranking_labels.csv",
    "experiments/experiment_a/experiment_A_run_metrics.csv",
    "experiments/experiment_a/experiment_A_instance_method_summary.csv",
    "experiments/experiment_bc/formal_five_run_metrics.csv",
    "experiments/experiment_bc/formal_five_instance_method_metrics_raw.csv",
    "experiments/experiment_bc/formal_five_instance_method_endpoints_ranked.csv",
    "experiments/experiment_bc/formal_five_overall_summary.csv",
    "experiments/experiment_bc/formal_five_friedman_tests.csv",
    "experiments/experiment_bc/formal_five_pairwise_wilcoxon_holm.csv",
    "experiments/experiment_bc/formal_five_primary_method_wilcoxon_holm.csv",
    "experiments/selector_ablation/assignments.csv",
    "experiments/selector_ablation/run_metrics.csv",
    "experiments/selector_ablation/selector_final_test_summary.csv",
    "experiments/selector_ablation/friedman.csv",
    "experiments/selector_ablation/pairwise_wilcoxon_holm.csv",
    "real_market/six_algorithm_run_metrics.csv",
    "real_market/six_algorithm_endpoint_friedman_tests.csv",
    "real_market/six_algorithm_endpoint_primary_wilcoxon_holm.csv",
    "real_market/six_algorithm_transaction_cost_overall.csv",
    "real_market/six_algorithm_transaction_cost_run_sensitivity.csv",
    "real_market/configured_run_metrics_with_pf_stability.csv",
    "real_market/configuration_protocol_endpoint_pairwise_wilcoxon_holm.csv",
    "experiments/mokp/run_metrics.csv",
    "experiments/mokp/mokp_endpoint_friedman_tests.csv",
    "experiments/mokp/mokp_endpoint_pairwise_wilcoxon_holm.csv",
    "manifest/paper_value_crosscheck.csv",
    "manifest/source_file_map.csv",
    "manifest/artifact_authority.csv",
    "manifest/code_authority.csv",
    "raw_pf/raw_pf_csv_part01.zip",
    "raw_pf/raw_pf_csv_part02.zip",
    "raw_pf/raw_pf_csv_part03.zip",
    "raw_pf/raw_pf_csv_part04.zip",
    "raw_pf/raw_pf_csv_part05.zip",
    "raw_pf/raw_pf_csv_part06.zip",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    missing = [relative for relative in TARGETS if not (ROOT / relative).is_file()]
    if missing:
        raise SystemExit("Missing checksum targets:\n- " + "\n- ".join(missing))
    lines = [f"{sha256(ROOT / relative)}  {relative}" for relative in TARGETS]
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {len(lines)} SHA-256 entries")


if __name__ == "__main__":
    main()
