from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


ROOT = Path(__file__).resolve().parent
ANALYSIS = ROOT / "p0_lite_outputs" / "p1_mokp_config_comparison_20260719"
OUT_DIR = ROOT / "p0_lite_outputs" / "p1_mokp_feature_failure_20260719"

BASELINES = ["NSGAII", "SPEA2", "MOEAD", "GDE3", "A_MPMO"]
ECMADE = "ECMADE_MOO"
BAYES = "BayesianConfig_ECMADE_MOO"
CONFIG_METHODS = ["RandomConfig_ECMADE_MOO", "MetaTransfer_ECMADE_MOO", BAYES]


def make_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def make_model(numeric: list[str], categorical: list[str], seed: int = 20260719) -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            ("num", "passthrough", numeric),
            ("cat", make_encoder(), categorical),
        ],
        remainder="drop",
    )
    rf = RandomForestRegressor(
        n_estimators=300,
        min_samples_leaf=1,
        random_state=seed,
        n_jobs=1,
    )
    return Pipeline([("preprocess", preprocess), ("model", rf)])


def transformed_names(model: Pipeline, numeric: list[str], categorical: list[str]) -> list[str]:
    names = list(numeric)
    if categorical:
        encoder = model.named_steps["preprocess"].named_transformers_["cat"]
        names.extend(encoder.get_feature_names_out(categorical).tolist())
    return names


def grouped_importance(
    model: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
    numeric: list[str],
    categorical: list[str],
    out_prefix: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    names = transformed_names(model, numeric, categorical)
    native = pd.DataFrame(
        {
            "feature": names,
            "importance": model.named_steps["model"].feature_importances_,
        }
    ).sort_values("importance", ascending=False)

    perm = permutation_importance(
        model,
        X[numeric + categorical],
        y,
        n_repeats=30,
        random_state=20260719,
        n_jobs=1,
    )
    perm_df = pd.DataFrame(
        {
            "feature": numeric + categorical,
            "permutation_importance_mean": perm.importances_mean,
            "permutation_importance_std": perm.importances_std,
        }
    ).sort_values("permutation_importance_mean", ascending=False)

    native.to_csv(OUT_DIR / f"{out_prefix}_native_feature_importance.csv", index=False, encoding="utf-8-sig")
    perm_df.to_csv(OUT_DIR / f"{out_prefix}_permutation_feature_importance.csv", index=False, encoding="utf-8-sig")
    return native, perm_df


def train_regression(frame: pd.DataFrame, target: str, numeric: list[str], categorical: list[str], prefix: str) -> dict:
    data = frame.dropna(subset=[target]).copy()
    model = make_model(numeric, categorical)
    X = data[numeric + categorical]
    y = pd.to_numeric(data[target])
    model.fit(X, y)
    pred = model.predict(X)
    residual = y.to_numpy() - pred
    native, perm = grouped_importance(model, data, y, numeric, categorical, prefix)
    pd.DataFrame(
        {
            "actual": y,
            "predicted": pred,
            "residual": residual,
            **{col: data[col].to_numpy() for col in numeric + categorical},
        }
    ).to_csv(OUT_DIR / f"{prefix}_in_sample_predictions.csv", index=False, encoding="utf-8-sig")
    return {
        "target": target,
        "rows": int(len(data)),
        "numeric": numeric,
        "categorical": categorical,
        "rmse_in_sample": float(np.sqrt(np.mean(residual**2))),
        "top_native_features": native.head(8).to_dict("records"),
        "top_permutation_features": perm.head(8).to_dict("records"),
    }


def build_instance_targets(ranked: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (split, instance), group in ranked.groupby(["split", "instance"], sort=False):
        by_method = group.set_index("method")
        best_baseline_rank = by_method.loc[BASELINES, "RankScore"].min()
        best_baseline_method = by_method.loc[BASELINES, "RankScore"].idxmin()
        ecmade_rank = by_method.loc[ECMADE, "RankScore"]
        bayes_rank = by_method.loc[BAYES, "RankScore"]
        best_config_rank = by_method.loc[CONFIG_METHODS, "RankScore"].min()
        best_config_method = by_method.loc[CONFIG_METHODS, "RankScore"].idxmin()
        meta = group.iloc[0]
        rows.append(
            {
                "split": split,
                "instance": instance,
                "items": int(meta["items"]),
                "capacity_ratio": float(meta["capacity_ratio"]),
                "profit_mode": str(meta["profit_mode"]),
                "ecmade_vs_best_baseline_rank_gain": float(best_baseline_rank - ecmade_rank),
                "bayesian_vs_ecmade_rank_gain": float(ecmade_rank - bayes_rank),
                "best_config_vs_ecmade_rank_gain": float(ecmade_rank - best_config_rank),
                "best_baseline_method": best_baseline_method,
                "best_config_method": best_config_method,
                "ecmade_rank_score": float(ecmade_rank),
                "bayesian_rank_score": float(bayes_rank),
                "best_baseline_rank_score": float(best_baseline_rank),
                "best_config_rank_score": float(best_config_rank),
            }
        )
    return pd.DataFrame(rows)


def classify_failure(row: pd.Series, instance_group: pd.DataFrame) -> list[str]:
    labels = []
    best_hv = instance_group["HV"].max()
    best_overlap = instance_group["PF_Overlap"].max()
    best_rank = instance_group["RankScore"].min()
    fastest = instance_group["Runtime"].min()

    if row["PF_Overlap"] <= 0.01:
        labels.append("zero_or_near_zero_pf_overlap")
    if row["HV"] < 0.95 * best_hv:
        labels.append("hypervolume_gap")
    if row["PF_Overlap"] < 0.50 * best_overlap:
        labels.append("reference_overlap_gap")
    if row["PF_Drift"] > instance_group["PF_Drift"].quantile(0.75):
        labels.append("high_run_to_run_drift")
    if row["Runtime"] > 1.50 * fastest:
        labels.append("runtime_overhead")
    if row["PF_Size"] < instance_group["PF_Size"].median() * 0.50:
        labels.append("small_archive")
    if row["RankScore"] > best_rank + 1.0:
        labels.append("inferior_instance_rank")
    if not labels:
        labels.append("no_major_failure")
    return labels


def build_failure_taxonomy(ranked: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for _, group in ranked.groupby(["split", "instance"], sort=False):
        best_method = group.sort_values(["RankScore", "method"]).iloc[0]["method"]
        for _, row in group.iterrows():
            labels = classify_failure(row, group)
            rows.append(
                {
                    "split": row["split"],
                    "instance": row["instance"],
                    "items": int(row["items"]),
                    "capacity_ratio": float(row["capacity_ratio"]),
                    "profit_mode": row["profit_mode"],
                    "method": row["method"],
                    "best_method_on_instance": best_method,
                    "RankScore": row["RankScore"],
                    "OverallInstanceRank": row["OverallInstanceRank"],
                    "HV": row["HV"],
                    "IGD": row["IGD"],
                    "PF_Overlap": row["PF_Overlap"],
                    "PF_Drift": row["PF_Drift"],
                    "Diversity": row["Diversity"],
                    "Runtime": row["Runtime"],
                    "PF_Size": row["PF_Size"],
                    "failure_labels": ";".join(labels),
                    "primary_failure": labels[0],
                    "has_major_failure": labels != ["no_major_failure"],
                }
            )
    taxonomy = pd.DataFrame(rows)
    counts = (
        taxonomy.assign(failure_label=taxonomy["failure_labels"].str.split(";"))
        .explode("failure_label")
        .groupby(["method", "failure_label"])
        .size()
        .reset_index(name="instance_count")
        .sort_values(["method", "instance_count"], ascending=[True, False])
    )
    return taxonomy, counts


def write_summary(model_summaries: list[dict], instance_targets: pd.DataFrame, taxonomy: pd.DataFrame, counts: pd.DataFrame) -> None:
    bayes_gain = instance_targets["bayesian_vs_ecmade_rank_gain"]
    ecmade_gain = instance_targets["ecmade_vs_best_baseline_rank_gain"]
    lines = [
        "# P1 MOKP Feature Importance and Failure Taxonomy",
        "",
        "## Scope",
        "",
        "- Source: P1 MOKP config comparison, 18 instances x 9 methods.",
        "- Feature importance uses RandomForestRegressor with native and permutation importance.",
        "- Instance-only models have 18 rows, so treat importance as descriptive evidence, not a high-power statistical claim.",
        "",
        "## Key Targets",
        "",
        f"- ECMADE vs best baseline mean RankScore gain: {ecmade_gain.mean():.4f}.",
        f"- BayesianConfig vs original ECMADE mean RankScore gain: {bayes_gain.mean():.4f}.",
        f"- BayesianConfig improves over original ECMADE on {(bayes_gain > 0).sum()}/18 instances.",
        "",
        "## Model Diagnostics",
        "",
    ]
    for summary in model_summaries:
        lines.append(
            f"- {summary['target']}: rows={summary['rows']}, in-sample RMSE={summary['rmse_in_sample']:.4f}."
        )
    lines.extend(
        [
            "",
            "## Failure Counts",
            "",
            counts.pivot_table(
                index="method",
                columns="failure_label",
                values="instance_count",
                fill_value=0,
                aggfunc="sum",
            ).to_markdown(),
            "",
            "## Main Files",
            "",
            "- `instance_targets.csv`: per-instance ECMADE/Bayesian gains.",
            "- `method_failure_taxonomy.csv`: method-instance failure labels.",
            "- `method_rankscore_*_feature_importance.csv`: method + instance feature model.",
            "- `ecmade_advantage_*_feature_importance.csv`: instance-only ECMADE generalization model.",
            "- `bayesian_gain_*_feature_importance.csv`: instance-only Bayesian gain model.",
        ]
    )
    (OUT_DIR / "README_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ranked = pd.read_csv(ANALYSIS / "instance_method_metrics_ranked.csv", encoding="utf-8-sig")
    ranked["items"] = pd.to_numeric(ranked["items"])
    ranked["capacity_ratio"] = pd.to_numeric(ranked["capacity_ratio"])
    ranked["profit_mode"] = ranked["profit_mode"].astype(str)
    ranked["method"] = ranked["method"].astype(str)

    instance_targets = build_instance_targets(ranked)
    taxonomy, counts = build_failure_taxonomy(ranked)

    summaries = []
    summaries.append(
        train_regression(
            ranked,
            "RankScore",
            ["items", "capacity_ratio"],
            ["profit_mode", "method"],
            "method_rankscore",
        )
    )
    summaries.append(
        train_regression(
            instance_targets,
            "ecmade_vs_best_baseline_rank_gain",
            ["items", "capacity_ratio"],
            ["profit_mode"],
            "ecmade_advantage",
        )
    )
    summaries.append(
        train_regression(
            instance_targets,
            "bayesian_vs_ecmade_rank_gain",
            ["items", "capacity_ratio"],
            ["profit_mode"],
            "bayesian_gain",
        )
    )

    instance_targets.to_csv(OUT_DIR / "instance_targets.csv", index=False, encoding="utf-8-sig")
    taxonomy.to_csv(OUT_DIR / "method_failure_taxonomy.csv", index=False, encoding="utf-8-sig")
    counts.to_csv(OUT_DIR / "method_failure_counts.csv", index=False, encoding="utf-8-sig")
    (OUT_DIR / "model_summaries.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    write_summary(summaries, instance_targets, taxonomy, counts)

    print(f"Wrote P1 feature/failure report to {OUT_DIR}")
    print(instance_targets[["instance", "ecmade_vs_best_baseline_rank_gain", "bayesian_vs_ecmade_rank_gain", "best_config_method"]].to_string(index=False))
    print(counts[counts["method"].isin([ECMADE, BAYES])].to_string(index=False))


if __name__ == "__main__":
    main()
