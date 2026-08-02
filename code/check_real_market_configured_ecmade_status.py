from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
BASE = ROOT / "p0_lite_outputs" / "p1_rolling_window_market_validation_20260719"
RAW = BASE / "raw_configured_ecmade"
LOG = BASE / "logs_configured_ecmade_python" / "configured_ecmade_full_python.log"
ASSIGNMENT = BASE / "config_protocol_assignments" / "real_market_ecmade_configuration_assignment.csv"


def main() -> None:
    assignment = pd.read_csv(ASSIGNMENT, encoding="utf-8-sig")
    expected = len(assignment) * 10
    completed = list(RAW.glob("*/*/*/run_*/pf_obj.csv"))
    print(f"completed_runs={len(completed)} / {expected}")
    if completed:
        rows = []
        for path in completed:
            run_dir = path.parent
            rows.append(
                {
                    "universe": run_dir.parent.parent.parent.name,
                    "window_id": run_dir.parent.parent.name,
                    "method": run_dir.parent.name,
                }
            )
        progress = (
            pd.DataFrame(rows)
            .groupby(["method", "universe"], sort=False)
            .size()
            .reset_index(name="completed_runs")
        )
        print(progress.to_string(index=False))
    if LOG.exists():
        print("\nlast_log_lines:")
        print("\n".join(LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-8:]))


if __name__ == "__main__":
    main()
