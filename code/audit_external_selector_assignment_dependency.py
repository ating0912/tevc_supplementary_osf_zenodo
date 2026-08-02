"""Check whether external validation assignments depend on replicate feature."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

from build_p1_mokp_experiment_c_stability_assignments import mokp_manifest, theta_index
from build_real_market_ecmade_config_assignments import (
    WINDOW_MANIFEST,
    complete_theta_table,
    market_meta_features,
)


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs" / "experiment_c_external_selector_dependency_audit_20260731"
NO_REP_DIR = ROOT / "p0_lite_outputs" / "experiment_c_stability_selector_training"
REP_DIR = ROOT / "outputs" / "experiment_c_replicate_audit_20260730" / "replicate_included_audit"
THETA_TABLE = NO_REP_DIR / "theta_candidate_table.csv"
OLD_REAL_MARKET_ASSIGNMENT = (
    ROOT
    / "p0_lite_outputs"
    / "p1_rolling_window_market_validation_20260719"
    / "config_protocol_assignments"
    / "ExperimentC_StabilityAware_ECMADE_MOO_assignment.csv"
)
OLD_MOKP_ASSIGNMENT = (
    ROOT
    / "p0_lite_outputs"
    / "p1_mokp_experiment_c_stability_assignments_20260729"
    / "p1_mokp_experiment_c_stability_theta_assignment.csv"
)


def read_features(model_dir: Path) -> list[str]:
    data = json.loads((model_dir / "feature_columns.json").read_text(encoding="utf-8"))
    return data["numeric"] + data["categorical"]


def selector_assignment(model_dir: Path, manifest: pd.DataFrame, domain: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    model = joblib.load(model_dir / "experiment_c_stability_random_forest.joblib")
    theta = complete_theta_table(pd.read_csv(THETA_TABLE, encoding="utf-8-sig"))
    feature_names = list(model.named_steps["preprocess"].feature_names_in_)
    score_rows = []
    assignment_rows = []
    for _, inst in manifest.iterrows():
        tiled = pd.concat([inst.to_frame().T] * len(theta), ignore_index=True)
        tiled = pd.concat([tiled.reset_index(drop=True), theta.reset_index(drop=True)], axis=1)
        missing = [col for col in feature_names if col not in tiled.columns]
        if missing:
            raise RuntimeError(f"{domain}: missing selector feature columns: {missing}")
        for col in feature_names:
            if col in tiled.columns:
                tiled[col] = tiled[col]
        tiled["predicted_C_LabelScore"] = model.predict(tiled[feature_names])
        tiled["predicted_rank"] = tiled["predicted_C_LabelScore"].rank(method="first", ascending=False).astype(int)
        score_rows.append(tiled.copy())
        selected = tiled.sort_values(["predicted_C_LabelScore", "method"], ascending=[False, True]).iloc[0]
        base = {
            "domain": domain,
            "split": inst.get("split", ""),
            "instance": selected["instance"],
            "theta_index": theta_index(theta, str(selected["method"])),
            "theta_id": selected["method"],
            "predicted_score": float(selected["predicted_C_LabelScore"]),
            "S": int(selected["subpops"]),
            "operator": selected["source_operator"],
            "migration": selected["source_migration"],
            "elite_ratio": float(selected["eliteRatio"]),
            "stagnation_threshold": int(selected["stagnationThreshold"]),
        }
        if domain == "real_market":
            base.update(
                {
                    "universe": inst["universe"],
                    "window_id": inst["window_id"],
                    "assets": int(inst["assets"]),
                    "K": int(inst["K"]),
                    "k_ratio": float(inst["k_ratio"]),
                }
            )
        else:
            base.update(
                {
                    "items": int(inst["items"]),
                    "objectives": int(inst["objectives"]),
                    "capacity_ratio": float(inst["capacity_ratio"]),
                    "profit_mode": inst["profit_mode"],
                    "replicate": int(inst["replicate"]),
                    "seed": int(inst["seed"]),
                }
            )
        assignment_rows.append(base)
    return pd.DataFrame(assignment_rows), pd.concat(score_rows, ignore_index=True)


def real_market_manifest() -> pd.DataFrame:
    windows = pd.read_csv(WINDOW_MANIFEST, encoding="utf-8-sig")
    return pd.DataFrame([market_meta_features(row) for _, row in windows.iterrows()])


def compare_assignments(no_rep: pd.DataFrame, with_rep: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    cols = keys + ["theta_id", "predicted_score", "S", "operator", "migration", "elite_ratio", "stagnation_threshold"]
    merged = no_rep[cols].merge(with_rep[cols], on=keys, suffixes=("_no_replicate", "_replicate_included"))
    merged["theta_changed"] = merged["theta_id_no_replicate"] != merged["theta_id_replicate_included"]
    return merged.sort_values(keys).reset_index(drop=True)


def compare_to_old(no_rep: pd.DataFrame, old_path: Path, keys: list[str]) -> pd.DataFrame:
    if not old_path.exists():
        return pd.DataFrame()
    old = pd.read_csv(old_path, encoding="utf-8-sig")
    cols = keys + ["theta_id"]
    merged = no_rep[cols].merge(old[cols], on=keys, suffixes=("_no_replicate", "_old_used"))
    merged["theta_changed_vs_old_used"] = merged["theta_id_no_replicate"] != merged["theta_id_old_used"]
    return merged.sort_values(keys).reset_index(drop=True)


def write_summary(domain: str, diff: pd.DataFrame, old_diff: pd.DataFrame, rows: list[dict]) -> None:
    rows.append(
        {
            "domain": domain,
            "groups": int(len(diff)),
            "changed_no_replicate_vs_replicate_included": int(diff["theta_changed"].sum()),
            "changed_no_replicate_vs_old_used": int(old_diff["theta_changed_vs_old_used"].sum())
            if not old_diff.empty
            else None,
            "requires_external_rerun": bool(diff["theta_changed"].any() or (not old_diff.empty and old_diff["theta_changed_vs_old_used"].any())),
        }
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_rows = []

    protocol = {
        "no_replicate_selector_dir": str(NO_REP_DIR),
        "replicate_included_selector_dir": str(REP_DIR),
        "no_replicate_features": read_features(NO_REP_DIR),
        "replicate_included_features": read_features(REP_DIR),
    }

    for domain, manifest, keys, old_path in [
        ("real_market", real_market_manifest(), ["universe", "window_id"], OLD_REAL_MARKET_ASSIGNMENT),
        ("mokp", mokp_manifest(), ["instance"], OLD_MOKP_ASSIGNMENT),
    ]:
        no_rep, no_rep_scores = selector_assignment(NO_REP_DIR, manifest, domain)
        with_rep, with_rep_scores = selector_assignment(REP_DIR, manifest, domain)
        diff = compare_assignments(no_rep, with_rep, keys)
        old_diff = compare_to_old(no_rep, old_path, keys)
        no_rep.to_csv(OUT_DIR / f"{domain}_no_replicate_assignment.csv", index=False, encoding="utf-8-sig")
        with_rep.to_csv(OUT_DIR / f"{domain}_replicate_included_assignment.csv", index=False, encoding="utf-8-sig")
        no_rep_scores.to_csv(OUT_DIR / f"{domain}_no_replicate_scores.csv", index=False, encoding="utf-8-sig")
        with_rep_scores.to_csv(OUT_DIR / f"{domain}_replicate_included_scores.csv", index=False, encoding="utf-8-sig")
        diff.to_csv(OUT_DIR / f"{domain}_assignment_diff_no_replicate_vs_replicate.csv", index=False, encoding="utf-8-sig")
        old_diff.to_csv(OUT_DIR / f"{domain}_assignment_diff_no_replicate_vs_old_used.csv", index=False, encoding="utf-8-sig")
        write_summary(domain, diff, old_diff, summary_rows)

    pd.DataFrame(summary_rows).to_csv(OUT_DIR / "external_selector_dependency_summary.csv", index=False, encoding="utf-8-sig")
    with (OUT_DIR / "external_selector_dependency_protocol.json").open("w", encoding="utf-8") as fh:
        json.dump(protocol, fh, indent=2)
    print(pd.DataFrame(summary_rows).to_string(index=False))
    print(f"OUT_DIR={OUT_DIR}")


if __name__ == "__main__":
    main()
