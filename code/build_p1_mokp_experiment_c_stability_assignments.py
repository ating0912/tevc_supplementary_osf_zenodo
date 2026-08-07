from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd


ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "p0_lite_outputs" / "experiment_c_stability_selector_training"
MODEL_PATH = MODEL_DIR / "experiment_c_stability_random_forest.joblib"
THETA_TABLE = MODEL_DIR / "theta_candidate_table.csv"
OUT_DIR = ROOT / "p0_lite_outputs" / "p1_mokp_experiment_c_stability_assignments_20260729"


def mokp_manifest() -> pd.DataFrame:
    rows = []
    for di, items in enumerate([100, 250, 500], start=1):
        for ci, capacity_ratio in enumerate([0.35, 0.50, 0.65], start=1):
            for mi, profit_mode in enumerate(["independent", "conflicting"], start=1):
                seed = 20260718 + 10000 * di + 1000 * ci + 100 * mi + 1
                rows.append(
                    {
                        "split": "test",
                        "instance": (
                            f"mokp_m02_d{items:03d}_c{round(100 * capacity_ratio):02d}_"
                            f"{profit_mode}_r01_s{seed}"
                        ),
                        "items": items,
                        "objectives": 2,
                        "capacity_ratio": capacity_ratio,
                        "profit_mode": profit_mode,
                        "replicate": 1,
                        "seed": seed,
                        # Domain-transfer pseudo-features for the portfolio-trained selector.
                        "assets": items,
                        "days": 0,
                        "k_ratio": capacity_ratio,
                        "K": round(items * capacity_ratio),
                        "corr_structure": "cluster_corr" if profit_mode == "conflicting" else "low_corr",
                        "return_distribution": "mixed" if profit_mode == "conflicting" else "normal",
                        "risk_structure": (
                            "high_vol"
                            if capacity_ratio <= 0.35
                            else ("low_vol" if capacity_ratio >= 0.65 else "extreme_events")
                        ),
                    }
                )
    return pd.DataFrame(rows)


def theta_index(theta: pd.DataFrame, method: str) -> int:
    matches = theta.index[theta["method"].astype(str).eq(str(method))]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one theta row for {method}, found {len(matches)}")
    return int(matches[0]) + 1


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model = joblib.load(MODEL_PATH)
    theta = pd.read_csv(THETA_TABLE, encoding="utf-8-sig")
    manifest = mokp_manifest()

    feature_names = list(model.named_steps["preprocess"].feature_names_in_)
    score_rows = []
    assignment_rows = []

    for _, inst in manifest.iterrows():
        tiled = pd.concat([inst.to_frame().T] * len(theta), ignore_index=True)
        tiled = pd.concat([tiled.reset_index(drop=True), theta.reset_index(drop=True)], axis=1)
        for col in feature_names:
            if col not in tiled.columns:
                raise RuntimeError(f"Missing selector feature column: {col}")
        tiled["predicted_C_LabelScore"] = model.predict(tiled[feature_names])
        tiled["predicted_C_ThetaRank"] = (
            tiled["predicted_C_LabelScore"].rank(method="first", ascending=False).astype(int)
        )
        score_rows.append(tiled.copy())

        selected = tiled.sort_values(["predicted_C_LabelScore", "method"], ascending=[False, True]).iloc[0]
        assignment_rows.append(
            {
                "split": selected["split"],
                "instance": selected["instance"],
                "items": int(selected["items"]),
                "objectives": int(selected["objectives"]),
                "capacity_ratio": float(selected["capacity_ratio"]),
                "profit_mode": selected["profit_mode"],
                "replicate": int(selected["replicate"]),
                "seed": int(selected["seed"]),
                "theta_index": theta_index(theta, str(selected["method"])),
                "theta_id": selected["method"],
                "predicted_score": float(selected["predicted_C_LabelScore"]),
                "S": int(selected["subpops"]),
                "operator": selected["source_operator"],
                "migration": selected["source_migration"],
                "elite_ratio": float(selected["eliteRatio"]),
                "stagnation_threshold": int(selected["stagnationThreshold"]),
            }
        )

    scores = pd.concat(score_rows, ignore_index=True)
    assignments = pd.DataFrame(assignment_rows)

    scores.to_csv(OUT_DIR / "p1_mokp_experiment_c_theta_predicted_scores.csv", index=False, encoding="utf-8-sig")
    assignments.to_csv(
        OUT_DIR / "p1_mokp_experiment_c_stability_theta_assignment.csv",
        index=False,
        encoding="utf-8-sig",
    )
    manifest.to_csv(OUT_DIR / "p1_mokp_experiment_c_pseudo_feature_manifest.csv", index=False, encoding="utf-8-sig")
    theta.to_csv(OUT_DIR / "theta_candidate_table.csv", index=False, encoding="utf-8-sig")
    with (OUT_DIR / "p1_mokp_experiment_c_transfer_protocol.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "purpose": "non-financial MOKP transfer assignment for Experiment C stability-aware selector",
                "selector_model": str(MODEL_PATH),
                "theta_table": str(THETA_TABLE),
                "selection_rule": "maximize predicted_C_LabelScore",
                "mokp_instances": int(len(manifest)),
                "theta_candidates": int(theta["method"].nunique()),
                "pseudo_feature_mapping": {
                    "assets": "items",
                    "days": 0,
                    "k_ratio": "capacity_ratio",
                    "K": "round(items * capacity_ratio)",
                    "corr_structure": "conflicting -> cluster_corr; independent -> low_corr",
                    "return_distribution": "conflicting -> mixed; independent -> normal",
                    "risk_structure": "0.35 -> high_vol; 0.50 -> extreme_events; 0.65 -> low_vol",
                },
            },
            f,
            indent=2,
        )
    print(f"OUT_DIR={OUT_DIR}")
    print(assignments[["instance", "theta_id", "predicted_score", "S", "operator", "migration"]].to_string(index=False))


if __name__ == "__main__":
    main()
