from __future__ import annotations

import json
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.io import loadmat


ROOT = Path(__file__).resolve().parent
BASE_DIR = ROOT / "p0_lite_outputs" / "p1_rolling_window_market_validation_20260719"
WINDOW_MANIFEST = BASE_DIR / "windows" / "rolling_window_manifest.csv"
OUT_DIR = BASE_DIR / "config_protocol_assignments"

META_DIR = ROOT / "p0_lite_outputs" / "meta_designed_ecmade_moo_training"
C_DIR = ROOT / "p0_lite_outputs" / "experiment_c_stability_selector_training"
BAYESIAN_SELECTED = ROOT / "p0_lite_outputs" / "bayesian_config_ecmade_moo_20260713_140251" / "bayesian_selected_theta.csv"
BAYESIAN_THETA = ROOT / "p0_lite_outputs" / "bayesian_config_ecmade_moo_20260713_140251" / "l24_theta_candidates.csv"

CONFIG_COLUMNS = [
    "subpops",
    "operatorMode",
    "exchangeMode",
    "eliteRatio",
    "stagnationThreshold",
    "theta",
    "archiveLimitFactor",
    "consensusArchive",
    "archiveConsWeight",
    "bestGuide",
    "minSubpopSize",
]


def window_number(window_id: str) -> int:
    match = re.search(r"(\d+)$", str(window_id))
    return int(match.group(1)) if match else 1


def safe_corr_summary(returns: np.ndarray) -> tuple[float, float, float]:
    if returns.shape[1] < 2:
        return 0.0, 1.0, 0.0
    corr = np.corrcoef(returns, rowvar=False)
    corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)
    off = corr[~np.eye(corr.shape[0], dtype=bool)]
    abs_mean = float(np.mean(np.abs(off)))
    eigvals = np.linalg.eigvalsh(0.5 * (corr + corr.T))
    eigvals = np.maximum(eigvals, 1e-10)
    cond = float(eigvals.max() / eigvals.min())
    neg_ratio = float(np.mean(off < 0))
    return abs_mean, cond, neg_ratio


def market_meta_features(row: pd.Series) -> dict:
    mat = loadmat(row["data_path"])
    train = np.asarray(mat["trainReturns"], dtype=float)
    train = train[np.all(np.isfinite(train), axis=1)]
    assets = int(row["assets"])
    k_value = int(row["K"])
    days = int(row["train_days"])
    k_ratio = float(k_value / max(assets, 1))
    daily_std = np.nanstd(train, axis=0)
    ann_vol = float(np.nanmean(daily_std) * np.sqrt(252))
    mean_abs_corr, corr_cond, neg_corr_ratio = safe_corr_summary(train)
    centered = train - np.nanmean(train, axis=0)
    std = np.nanstd(train, axis=0)
    std = np.where(std <= 1e-12, np.nan, std)
    skew = np.nanmean((centered / std) ** 3, axis=0)
    kurt = np.nanmean((centered / std) ** 4, axis=0)
    mean_abs_skew = float(np.nanmean(np.abs(skew)))
    mean_kurtosis = float(np.nanmean(kurt))
    q05 = np.nanpercentile(train, 5, axis=0)
    tail_loss = float(np.nanmean(np.maximum(-q05, 0)))

    if corr_cond > 1000:
        corr_structure = "pathological_cov"
    elif mean_abs_corr > 0.35:
        corr_structure = "cluster_corr"
    elif mean_abs_corr > 0.18:
        corr_structure = "high_corr"
    else:
        corr_structure = "low_corr"

    if mean_kurtosis > 7 and mean_abs_skew > 0.7:
        return_distribution = "mixed"
    elif mean_kurtosis > 7:
        return_distribution = "heavy_tail"
    elif mean_abs_skew > 0.7:
        return_distribution = "skewed"
    else:
        return_distribution = "normal"

    if tail_loss > 0.04:
        risk_structure = "extreme_events"
    elif ann_vol > 0.28:
        risk_structure = "high_vol"
    else:
        risk_structure = "low_vol"

    return {
        "split": "real_market",
        "instance": f"{row['universe']}_{row['window_id']}",
        "universe": row["universe"],
        "window_id": row["window_id"],
        "assets": assets,
        "days": days,
        "K": k_value,
        "k_ratio": k_ratio,
        "replicate": window_number(row["window_id"]),
        "corr_structure": corr_structure,
        "return_distribution": return_distribution,
        "risk_structure": risk_structure,
        "mean_abs_corr": mean_abs_corr,
        "corr_condition_number": corr_cond,
        "negative_corr_ratio": neg_corr_ratio,
        "annualized_mean_volatility": ann_vol,
        "mean_abs_skew": mean_abs_skew,
        "mean_kurtosis": mean_kurtosis,
        "tail_loss_5pct": tail_loss,
        "data_path": row["data_path"],
    }


def read_feature_columns(path: Path) -> tuple[list[str], list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["numeric"], data["categorical"]


def complete_theta_table(theta: pd.DataFrame) -> pd.DataFrame:
    out = theta.copy()
    defaults = {
        "theta": 1 / 13,
        "archiveLimitFactor": 5,
        "consensusArchive": 0,
        "archiveConsWeight": 0,
        "bestGuide": "rank",
        "minSubpopSize": 1,
    }
    for key, value in defaults.items():
        if key not in out.columns:
            out[key] = value
    return out


def select_with_model(
    method_name: str,
    model_path: Path,
    feature_json: Path,
    theta_path: Path,
    market_manifest: pd.DataFrame,
    score_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    model = joblib.load(model_path)
    numeric, categorical = read_feature_columns(feature_json)
    theta = complete_theta_table(pd.read_csv(theta_path, encoding="utf-8-sig"))
    rows = []
    score_frames = []
    for _, instance in market_manifest.iterrows():
        tiled = pd.concat([instance.to_frame().T] * len(theta), ignore_index=True)
        tiled = pd.concat([tiled.reset_index(drop=True), theta.reset_index(drop=True)], axis=1)
        for col in numeric:
            tiled[col] = pd.to_numeric(tiled[col], errors="coerce")
        for col in categorical:
            if col not in tiled.columns:
                tiled[col] = "unknown"
        tiled[score_name] = model.predict(tiled[numeric + categorical])
        tiled["predicted_rank"] = tiled[score_name].rank(method="first", ascending=False).astype(int)
        tiled["protocol_method"] = method_name
        score_frames.append(tiled.copy())
        best = tiled.sort_values(score_name, ascending=False).iloc[0]
        rows.append(assignment_row(method_name, instance, best, best[score_name]))
    return pd.DataFrame(rows), pd.concat(score_frames, ignore_index=True)


def theta_config_from_row(theta_row: pd.Series) -> dict:
    out = {}
    for col in CONFIG_COLUMNS:
        if col in theta_row.index:
            out[col] = theta_row[col]
    return out


def assignment_row(method: str, instance: pd.Series, theta_row: pd.Series, score: float | None = None) -> dict:
    config = theta_config_from_row(theta_row)
    out = {
        "method": method,
        "universe": instance["universe"],
        "window_id": instance["window_id"],
        "instance": instance["instance"],
        "assets": int(instance["assets"]),
        "K": int(instance["K"]),
        "k_ratio": float(instance["k_ratio"]),
        "theta_id": theta_row.get("method", theta_row.get("theta_id", "hand-crafted")),
        "source_theta_id": theta_row.get("source_theta_id", theta_row.get("theta_id", "")),
        "operator": theta_row.get("source_operator", theta_row.get("operator", "")),
        "migration": theta_row.get("source_migration", theta_row.get("migration", "")),
        "elite_ratio": theta_row.get("eliteRatio", theta_row.get("elite_ratio", "")),
        "stagnation_threshold": theta_row.get("stagnationThreshold", theta_row.get("stagnation_threshold", "")),
        "predicted_score": score,
    }
    out.update(config)
    return out


def fixed_assignments(method: str, theta_row: pd.Series, market_manifest: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([assignment_row(method, row, theta_row, None) for _, row in market_manifest.iterrows()])


def hand_crafted_theta() -> pd.Series:
    return pd.Series(
        {
            "method": "hand-crafted",
            "source_theta_id": "hand-crafted-default",
            "source_operator": "mixed",
            "source_migration": "fixed",
            "subpops": 3,
            "operatorMode": "mixed",
            "exchangeMode": "paper",
            "eliteRatio": 0.05,
            "stagnationThreshold": 50,
            "theta": 1 / 13,
            "archiveLimitFactor": 5,
            "consensusArchive": 0,
            "archiveConsWeight": 0,
            "bestGuide": "rank",
            "minSubpopSize": 1,
        }
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    windows = pd.read_csv(WINDOW_MANIFEST, encoding="utf-8-sig")
    market_manifest = pd.DataFrame([market_meta_features(row) for _, row in windows.iterrows()])
    market_manifest.to_csv(OUT_DIR / "real_market_meta_feature_manifest.csv", index=False, encoding="utf-8-sig")

    hand = fixed_assignments("HandCrafted_ECMADE_MOO", hand_crafted_theta(), market_manifest)

    bayes_theta = complete_theta_table(pd.read_csv(BAYESIAN_THETA, encoding="utf-8-sig"))
    selected = pd.read_csv(BAYESIAN_SELECTED, encoding="utf-8-sig").iloc[0]
    bayes_row = bayes_theta[bayes_theta["method"].astype(str) == str(selected["theta_id"])].iloc[0]
    bayes = fixed_assignments("BayesianConfig_ECMADE_MOO", bayes_row, market_manifest)

    meta, meta_scores = select_with_model(
        "MetaDesigned_ECMADE_MOO",
        META_DIR / "meta_learner_random_forest.joblib",
        META_DIR / "feature_columns.json",
        META_DIR / "theta_candidate_table.csv",
        market_manifest,
        "predicted_meta_score",
    )
    stab, stab_scores = select_with_model(
        "ExperimentC_StabilityAware_ECMADE_MOO",
        C_DIR / "experiment_c_stability_random_forest.joblib",
        C_DIR / "feature_columns.json",
        C_DIR / "theta_candidate_table.csv",
        market_manifest,
        "predicted_C_LabelScore",
    )

    all_assignments = pd.concat([hand, bayes, meta, stab], ignore_index=True)
    all_assignments.to_csv(
        OUT_DIR / "real_market_ecmade_configuration_assignment.csv",
        index=False,
        encoding="utf-8-sig",
    )
    meta_scores.to_csv(OUT_DIR / "real_market_meta_designed_theta_scores.csv", index=False, encoding="utf-8-sig")
    stab_scores.to_csv(OUT_DIR / "real_market_stability_aware_theta_scores.csv", index=False, encoding="utf-8-sig")
    for method, group in all_assignments.groupby("method", sort=False):
        group.to_csv(OUT_DIR / f"{method}_assignment.csv", index=False, encoding="utf-8-sig")
    usage = (
        all_assignments.groupby(["method", "theta_id"])
        .size()
        .reset_index(name="windows")
        .sort_values(["method", "windows", "theta_id"], ascending=[True, False, True])
    )
    usage.to_csv(OUT_DIR / "real_market_theta_usage_by_method.csv", index=False, encoding="utf-8-sig")
    print(f"Wrote assignments to {OUT_DIR}")
    print(usage.to_string(index=False))


if __name__ == "__main__":
    main()
