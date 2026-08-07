from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "manifest" / "artifact_checksums.sha256"

ARTIFACTS = [
    "logs/full_run_logs.zip",
    "figures/paper_figures.zip",
    "selector/selector_no_replicate.joblib",
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
    "experiments/experiment_bc/formal_five_pairwise_wilcoxon_holm.csv",
    "real_market/configured_run_metrics_with_pf_stability.csv",
    "real_market/configured_window_method_summary.csv",
    "real_market/configured_window_method_ranked.csv",
    "real_market/configured_transaction_cost_overall.csv",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    raw_pf_parts = sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / "raw_pf").glob("raw_pf_csv_part*.zip"))
    artifacts = ARTIFACTS + raw_pf_parts
    missing = [path for path in artifacts if not (ROOT / path).is_file()]
    if missing:
        raise SystemExit("Missing artifacts:\n- " + "\n- ".join(missing))
    if not raw_pf_parts:
        raise SystemExit("No raw PF archive parts found")
    lines = [f"{sha256(ROOT / path)}  {path}" for path in artifacts]
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {len(lines)} SHA-256 entries to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
