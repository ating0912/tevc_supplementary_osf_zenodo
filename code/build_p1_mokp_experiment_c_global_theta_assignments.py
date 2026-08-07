from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from build_p1_mokp_experiment_c_stability_assignments import mokp_manifest


ROOT = Path(__file__).resolve().parent
THETA_TABLE = ROOT / "p0_lite_outputs" / "experiment_c_stability_selector_training" / "theta_candidate_table.csv"
OUT_DIR = ROOT / "p0_lite_outputs" / "p1_mokp_experiment_c_global_theta_assignments_20260729"
GLOBAL_THETA = ["theta_034", "theta_037"]


def build_assignment(manifest: pd.DataFrame, theta_row: pd.Series, theta_index: int) -> pd.DataFrame:
    rows = []
    for _, inst in manifest.iterrows():
        rows.append(
            {
                "split": inst["split"],
                "instance": inst["instance"],
                "items": int(inst["items"]),
                "objectives": int(inst["objectives"]),
                "capacity_ratio": float(inst["capacity_ratio"]),
                "profit_mode": inst["profit_mode"],
                "replicate": int(inst["replicate"]),
                "seed": int(inst["seed"]),
                "theta_index": theta_index,
                "theta_id": theta_row["method"],
                "predicted_score": float("nan"),
                "S": int(theta_row["subpops"]),
                "operator": theta_row["source_operator"],
                "migration": theta_row["source_migration"],
                "elite_ratio": float(theta_row["eliteRatio"]),
                "stagnation_threshold": int(theta_row["stagnationThreshold"]),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = mokp_manifest()
    theta = pd.read_csv(THETA_TABLE, encoding="utf-8-sig")
    protocol_rows = []

    for theta_id in GLOBAL_THETA:
        matches = theta.index[theta["method"].astype(str).eq(theta_id)]
        if len(matches) != 1:
            raise RuntimeError(f"Expected exactly one theta row for {theta_id}, found {len(matches)}")
        idx = int(matches[0])
        assignment = build_assignment(manifest, theta.iloc[idx], idx + 1)
        path = OUT_DIR / f"p1_mokp_global_{theta_id}_assignment.csv"
        assignment.to_csv(path, index=False, encoding="utf-8-sig")
        protocol_rows.append(
            {
                "theta_id": theta_id,
                "theta_index": idx + 1,
                "assignment_path": str(path),
                "instances": int(len(assignment)),
                "S": int(theta.iloc[idx]["subpops"]),
                "operator": theta.iloc[idx]["source_operator"],
                "migration": theta.iloc[idx]["source_migration"],
                "elite_ratio": float(theta.iloc[idx]["eliteRatio"]),
                "stagnation_threshold": int(theta.iloc[idx]["stagnationThreshold"]),
            }
        )

    manifest.to_csv(OUT_DIR / "p1_mokp_global_theta_manifest.csv", index=False, encoding="utf-8-sig")
    theta.to_csv(OUT_DIR / "theta_candidate_table.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(protocol_rows).to_csv(OUT_DIR / "p1_mokp_global_theta_assignment_manifest.csv", index=False, encoding="utf-8-sig")
    with (OUT_DIR / "p1_mokp_global_theta_diagnostic_protocol.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "purpose": "global-theta diagnostic for Experiment C MOKP direct-transfer selected thetas",
                "global_theta": GLOBAL_THETA,
                "runs_per_instance_planned": 30,
                "N": 100,
                "maxFE": 10000,
                "instances": int(len(manifest)),
            },
            f,
            indent=2,
        )
    print(f"OUT_DIR={OUT_DIR}")
    print(pd.DataFrame(protocol_rows).to_string(index=False))


if __name__ == "__main__":
    main()
