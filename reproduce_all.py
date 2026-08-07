from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STAGES = [
    "generate_instances",
    "generate_labels",
    "train_selector_no_replicate",
    "run_final_experiment",
    "compute_metrics",
    "run_statistical_tests",
    "generate_tables",
    "generate_figures",
]


def main() -> None:
    for stage in STAGES:
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "run_stage.py"), "--stage", stage, "--audit-only"])
    print("All package-stage audits completed. Remove --audit-only in stage wrappers after connecting full runners.")


if __name__ == "__main__":
    main()
