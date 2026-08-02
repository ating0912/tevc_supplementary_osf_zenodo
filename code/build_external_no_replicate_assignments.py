"""Materialize no-replicate Experiment C assignments for external validation."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

from build_p1_mokp_experiment_c_stability_assignments import mokp_manifest, theta_index
from build_real_market_ecmade_config_assignments import (
    WINDOW_MANIFEST,
    assignment_row,
    complete_theta_table,
    market_meta_features,
)


ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "p0_lite_outputs" / "experiment_c_stability_selector_training"
OUT_DIR = ROOT / "p0_lite_outputs" / "experiment_c_no_replicate_external_assignments_20260731"
REAL_METHOD = "ExperimentC_NoReplicate_ECMADE_MOO"
MOKP_METHOD = "ExperimentC_NoReplicate_ECMADE_MOO"


def feature_names(model) -> list[str]:
    return list(model.named_steps["preprocess"].feature_names_in_)


def select_real_market(model, theta: pd.DataFrame, manifest: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    features = feature_names(model)
    rows = []
    scores = []
    for _, inst in manifest.iterrows():
        tiled = pd.concat([inst.to_frame().T] * len(theta), ignore_index=True)
        tiled = pd.concat([tiled.reset_index(drop=True), theta.reset_index(drop=True)], axis=1)
        missing = [col for col in features if col not in tiled.columns]
        if missing:
            raise RuntimeError(f"real_market missing selector features: {missing}")
        tiled["predicted_C_LabelScore"] = model.predict(tiled[features])
        tiled["predicted_rank"] = tiled["predicted_C_LabelScore"].rank(method="first", ascending=False).astype(int)
        scores.append(tiled.copy())
        best = tiled.sort_values(["predicted_C_LabelScore", "method"], ascending=[False, True]).iloc[0]
        rows.append(assignment_row(REAL_METHOD, inst, best, float(best["predicted_C_LabelScore"])))
    return pd.DataFrame(rows), pd.concat(scores, ignore_index=True)


def select_mokp(model, theta: pd.DataFrame, manifest: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    features = feature_names(model)
    rows = []
    scores = []
    for _, inst in manifest.iterrows():
        tiled = pd.concat([inst.to_frame().T] * len(theta), ignore_index=True)
        tiled = pd.concat([tiled.reset_index(drop=True), theta.reset_index(drop=True)], axis=1)
        missing = [col for col in features if col not in tiled.columns]
        if missing:
            raise RuntimeError(f"mokp missing selector features: {missing}")
        tiled["predicted_C_LabelScore"] = model.predict(tiled[features])
        tiled["predicted_rank"] = tiled["predicted_C_LabelScore"].rank(method="first", ascending=False).astype(int)
        scores.append(tiled.copy())
        selected = tiled.sort_values(["predicted_C_LabelScore", "method"], ascending=[False, True]).iloc[0]
        rows.append(
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
    return pd.DataFrame(rows), pd.concat(scores, ignore_index=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model = joblib.load(MODEL_DIR / "experiment_c_stability_random_forest.joblib")
    theta = complete_theta_table(pd.read_csv(MODEL_DIR / "theta_candidate_table.csv", encoding="utf-8-sig"))

    windows = pd.read_csv(WINDOW_MANIFEST, encoding="utf-8-sig")
    real_manifest = pd.DataFrame([market_meta_features(row) for _, row in windows.iterrows()])
    mokp = mokp_manifest()

    real_assignment, real_scores = select_real_market(model, theta, real_manifest)
    mokp_assignment, mokp_scores = select_mokp(model, theta, mokp)

    real_assignment.to_csv(OUT_DIR / "real_market_no_replicate_assignment.csv", index=False, encoding="utf-8-sig")
    real_scores.to_csv(OUT_DIR / "real_market_no_replicate_theta_scores.csv", index=False, encoding="utf-8-sig")
    real_manifest.to_csv(OUT_DIR / "real_market_no_replicate_meta_feature_manifest.csv", index=False, encoding="utf-8-sig")
    mokp_assignment.to_csv(OUT_DIR / "mokp_no_replicate_assignment.csv", index=False, encoding="utf-8-sig")
    mokp_scores.to_csv(OUT_DIR / "mokp_no_replicate_theta_scores.csv", index=False, encoding="utf-8-sig")
    mokp.to_csv(OUT_DIR / "mokp_no_replicate_pseudo_feature_manifest.csv", index=False, encoding="utf-8-sig")
    with (OUT_DIR / "external_no_replicate_assignment_protocol.json").open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "selector_model": str(MODEL_DIR / "experiment_c_stability_random_forest.joblib"),
                "feature_mapping": "no replicate feature consumed by model; MOKP manifest still records replicate for instance identity only",
                "real_market_method": REAL_METHOD,
                "mokp_method": MOKP_METHOD,
                "real_market_windows": int(len(real_assignment)),
                "mokp_instances": int(len(mokp_assignment)),
            },
            fh,
            indent=2,
        )
    print(f"OUT_DIR={OUT_DIR}")
    print("real_market theta usage")
    print(real_assignment["theta_id"].value_counts().to_string())
    print("mokp theta usage")
    print(mokp_assignment["theta_id"].value_counts().to_string())


if __name__ == "__main__":
    main()
