from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


STAGES = {
    "generate_instances": "Artifacts for the 192 synthetic instances and split manifest.",
    "generate_labels": "Artifacts for train/validation theta-label generation.",
    "train_selector_no_replicate": "Artifacts for the formal no-replicate selector.",
    "run_final_experiment": "Artifacts for Experiment A/B/C, ablation, and real-market runs.",
    "compute_metrics": "Artifacts for optimization and market metrics.",
    "run_statistical_tests": "Artifacts for Friedman, Wilcoxon-Holm, and effect-size analyses.",
    "generate_tables": "Archived paper-ready tables.",
    "generate_figures": "Archived paper-ready figures.",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit the archived package artifacts associated with one documented stage."
    )
    parser.add_argument("--stage", required=True, choices=sorted(STAGES))
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="Required safety flag: inspect precomputed artifacts without launching research jobs.",
    )
    args = parser.parse_args()
    if not args.audit_only:
        parser.error(
            "This command audits precomputed artifacts only. Pass --audit-only; "
            "use the producer scripts listed in manifest/source_file_map.csv for reruns."
        )
    print(f"Stage: {args.stage}")
    print(STAGES[args.stage])
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "check_package.py")])


if __name__ == "__main__":
    main()
