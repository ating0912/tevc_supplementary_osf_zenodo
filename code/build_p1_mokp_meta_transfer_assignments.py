from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from train_meta_designed_ecmade_moo import load_theta_table, theta_excel_default


ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "p0_lite_outputs" / "meta_designed_ecmade_moo_training"
MODEL_PATH = MODEL_DIR / "meta_learner_random_forest.joblib"
OUT_DIR = ROOT / "p0_lite_outputs" / "p1_mokp_meta_transfer_assignments_20260719"


def mokp_manifest() -> pd.DataFrame:
    rows = []
    for di, items in enumerate([100, 250, 500], start=1):
        for ci, capacity_ratio in enumerate([0.35, 0.50, 0.65], start=1):
            for mi, profit_mode in enumerate(["independent", "conflicting"], start=1):
                seed = 20260718 + 10000 * di + 1000 * ci + 100 * mi + 1
                rows.append(
                    {
                        "split": "test",
                        "instance": f"mokp_m02_d{items:03d}_c{round(100*capacity_ratio):02d}_{profit_mode}_r01_s{seed}",
                        "items": items,
                        "objectives": 2,
                        "capacity_ratio": capacity_ratio,
                        "profit_mode": profit_mode,
                        "replicate": 1,
                        "seed": seed,
                        # P0 meta-learner transfer pseudo-features.
                        "assets": items,
                        "days": 0,
                        "k_ratio": capacity_ratio,
                        "K": round(items * capacity_ratio),
                        "corr_structure": "cluster_corr" if profit_mode == "conflicting" else "low_corr",
                        "return_distribution": "mixed" if profit_mode == "conflicting" else "normal",
                        "risk_structure": "high_vol" if capacity_ratio <= 0.35 else ("low_vol" if capacity_ratio >= 0.65 else "extreme_events"),
                    }
                )
    return pd.DataFrame(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model = joblib.load(MODEL_PATH)
    theta = load_theta_table(theta_excel_default(ROOT))
    manifest = mokp_manifest()

    score_rows = []
    assignment_rows = []
    for _, inst in manifest.iterrows():
        tiled = pd.concat([inst.to_frame().T] * len(theta), ignore_index=True)
        tiled = pd.concat([tiled.reset_index(drop=True), theta.reset_index(drop=True)], axis=1)
        features = list(model.named_steps["preprocess"].feature_names_in_)
        tiled["predicted_score"] = model.predict(tiled[features])
        score_rows.append(tiled.copy())
        selected = tiled.sort_values("predicted_score", ascending=False).iloc[0]
        theta_index = int(theta.index[theta["method"] == selected["method"]][0]) + 1
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
                "theta_index": theta_index,
                "theta_id": selected["method"],
                "predicted_score": float(selected["predicted_score"]),
                "S": int(selected["subpops"]),
                "operator": selected["source_operator"],
                "migration": selected["source_migration"],
                "elite_ratio": float(selected["eliteRatio"]),
                "stagnation_threshold": int(selected["stagnationThreshold"]),
            }
        )

    pd.concat(score_rows, ignore_index=True).to_csv(
        OUT_DIR / "p1_mokp_theta_predicted_scores.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(assignment_rows).to_csv(
        OUT_DIR / "p1_mokp_meta_transfer_theta_assignment.csv", index=False, encoding="utf-8-sig"
    )
    manifest.to_csv(OUT_DIR / "p1_mokp_pseudo_feature_manifest.csv", index=False, encoding="utf-8-sig")
    theta.to_csv(OUT_DIR / "theta_candidate_table.csv", index=False, encoding="utf-8-sig")
    print(f"Wrote P1 MOKP meta-transfer assignments to {OUT_DIR}")


if __name__ == "__main__":
    main()
