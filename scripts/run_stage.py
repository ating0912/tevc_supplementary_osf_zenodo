from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


STAGES = {
    "generate_instances": "Build or verify the 192 synthetic instances and split manifest.",
    "generate_labels": "Recompute train/validation theta labels from raw run metrics.",
    "train_selector_no_replicate": "Train the formal no-replicate selector.",
    "run_final_experiment": "Run Experiment A/B/C/ablation/real-market optimizers.",
    "compute_metrics": "Compute HV, IGD, PF Overlap, PF Drift, EAF width, diversity, runtime, and market metrics.",
    "run_statistical_tests": "Run Friedman, Wilcoxon, Holm correction, and Vargha-Delaney A12 analyses.",
    "generate_tables": "Build paper-ready CSV/XLSX tables.",
    "generate_figures": "Build paper-ready figures.",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=sorted(STAGES))
    parser.add_argument("--audit-only", action="store_true", help="Only run the package audit for this skeleton.")
    args = parser.parse_args()
    print(f"Stage: {args.stage}")
    print(STAGES[args.stage])
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "check_package.py")])
    if args.audit_only:
        return
    print("This wrapper records the official order. Connect the heavy runner listed in manifest/source_file_map.csv for this stage before full archive release.")


if __name__ == "__main__":
    main()
