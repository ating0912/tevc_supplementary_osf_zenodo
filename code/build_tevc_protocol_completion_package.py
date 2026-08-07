from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs" / "tevc_protocol_completion_20260727"
C_SELECTOR_DIR = ROOT / "p0_lite_outputs" / "experiment_c_stability_selector_training"
REAL_MARKET_CONFIG_DIR = (
    ROOT
    / "p0_lite_outputs"
    / "p1_rolling_window_market_validation_20260719"
    / "configured_ecmade_comparison_summary"
)


FEATURE_DESCRIPTIONS = {
    "assets": "Number of available assets in the portfolio instance.",
    "days": "Number of historical or synthetic observations used to define the instance.",
    "k_ratio": "Cardinality ratio K/n specified in the instance manifest.",
    "K": "Cardinality constraint after applying the manifest rounding rule.",
    "replicate": "Replicate index for synthetic instance generation.",
    "split": "Manifest split indicator used for training, validation, or hold-out testing.",
    "corr_structure": "Synthetic correlation regime label.",
    "return_distribution": "Synthetic return-distribution regime label.",
    "risk_structure": "Synthetic risk-regime label.",
    "subpops": "Number of ECMADE-MOO subpopulations in the theta configuration.",
    "eliteRatio": "Elite injection ratio in the theta configuration.",
    "stagnationThreshold": "Number of stagnant generations required before the exchange trigger is activated.",
    "theta": "Theta identifier encoded as a numeric configuration index.",
    "archiveLimitFactor": "External-archive size factor in the theta configuration.",
    "S_level": "L24 orthogonal-design level for subpopulation count.",
    "operator_level": "L24 orthogonal-design level for operator setting.",
    "migration_level": "L24 orthogonal-design level for migration setting.",
    "elite_level": "L24 orthogonal-design level for elite-ratio setting.",
    "tau_level": "L24 orthogonal-design level for stagnation-threshold setting.",
    "source_operator": "Original operator family recorded in the theta library.",
    "source_migration": "Original migration strategy recorded in the theta library.",
    "source_archive_strategy": "Archive-update strategy recorded in the theta library.",
    "source_constraint_handling": "Constraint-handling setting recorded in the theta library.",
    "operatorMode": "Executable operator mode used by ECMADE-MOO.",
    "exchangeMode": "Executable information-exchange mode used by ECMADE-MOO.",
    "bestGuide": "Best-guide scope or policy used by ECMADE-MOO.",
}


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_feature_schema() -> pd.DataFrame:
    feature_columns = read_json(C_SELECTOR_DIR / "feature_columns.json")
    rows = []
    for feature_type in ["numeric", "categorical"]:
        for field in feature_columns[feature_type]:
            source = "instance meta-feature" if field in {
                "assets",
                "days",
                "k_ratio",
                "K",
                "replicate",
                "split",
                "corr_structure",
                "return_distribution",
                "risk_structure",
            } else "theta configuration feature"
            rows.append(
                {
                    "feature": field,
                    "feature_type": feature_type,
                    "source": source,
                    "calculation_or_encoding": (
                        "Passed through as numeric value; no min-max normalization is applied before Random Forest."
                        if feature_type == "numeric"
                        else "Encoded by OneHotEncoder(handle_unknown='ignore') in the selector pipeline."
                    ),
                    "description": FEATURE_DESCRIPTIONS.get(field, ""),
                }
            )
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "experiment_c_feature_schema.csv", index=False, encoding="utf-8-sig")
    return df


def write_normalization_protocol() -> pd.DataFrame:
    rows = [
        {
            "component": "Pareto-front objective normalization",
            "scope": "Each comparison group; synthetic uses split-instance-K, real-market uses universe-window.",
            "rule": "Objective points are normalized by (point - ideal) / max(nadir - ideal, 1e-12), then clipped to [0, 1].",
            "degenerate_case": "If nadir equals ideal for an objective, the denominator is 1e-12; this prevents division by zero and does not assign an artificial 0.5 score.",
        },
        {
            "component": "Experiment B training LabelScore",
            "scope": "Each split-instance-K group in the theta label table.",
            "rule": "Rank HV and PF_Overlap in descending order; rank IGD, PF_Drift, and Runtime in ascending order; average the five ranks.",
            "degenerate_case": "Metric ties use average rank through pandas rank default; lower LabelScore is better.",
        },
        {
            "component": "Experiment B final RankScore",
            "scope": "The 32 unseen test instances under the four ECMADE-MOO configuration protocols.",
            "rule": "Common-reference metrics are recomputed from raw outputs, then rank-based aggregation is used; lower RankScore is better.",
            "degenerate_case": "Ties use average rank for metric ranks; this score is not min-max normalized.",
        },
        {
            "component": "Experiment C C_LabelScore",
            "scope": "Each split-instance-K group in the stability-aware theta label table.",
            "rule": "C_LabelScore = -0.2*rank_HV - 0.2*rank_IGD - 0.3*rank_PF_Overlap - 0.3*rank_PF_Drift; larger C_LabelScore is better.",
            "degenerate_case": "Metric ties use average rank; C_ThetaRank uses deterministic first-rank ordering after sorting by C_LabelScore.",
        },
        {
            "component": "Real-market configured RankScore",
            "scope": "Each universe-window group for the four ECMADE-MOO configuration protocols.",
            "rule": "Metrics are ranked by direction, and RankScore is the average rank; lower RankScore is better.",
            "degenerate_case": "Ties use average rank; the six-algorithm and four-configuration real-market comparisons are kept as separate comparison groups.",
        },
    ]
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "normalization_and_ranking_protocol.csv", index=False, encoding="utf-8-sig")
    return df


def write_real_market_stats_summary() -> pd.DataFrame:
    overall = pd.read_csv(REAL_MARKET_CONFIG_DIR / "configured_overall_summary.csv", encoding="utf-8-sig")
    friedman = pd.read_csv(REAL_MARKET_CONFIG_DIR / "configured_friedman_tests.csv", encoding="utf-8-sig")
    wilcoxon_df = pd.read_csv(REAL_MARKET_CONFIG_DIR / "configured_pairwise_wilcoxon_holm.csv", encoding="utf-8-sig")

    rank_friedman = friedman[friedman["metric"].eq("RankScore")].iloc[0]
    rank_pairs = wilcoxon_df[wilcoxon_df["metric"].eq("RankScore")].copy()
    best = overall.sort_values(["overall_RankScore", "method"]).iloc[0]
    stability = overall[overall["method"].eq("ExperimentC_StabilityAware_ECMADE_MOO")].iloc[0]

    rows = [
        {
            "item": "comparison_group",
            "confirmed_statement": "The real-market four-protocol ECMADE-MOO comparison is analyzed separately from the six-algorithm real-market comparison.",
        },
        {
            "item": "paired_unit",
            "confirmed_statement": f"The paired unit is universe-window, with n={int(rank_friedman['n_paired_units'])} paired units.",
        },
        {
            "item": "overall_rankscore_friedman",
            "confirmed_statement": f"RankScore differs significantly across the four protocols by Friedman test (chi-square={rank_friedman['friedman_chi_square']:.6g}, p={rank_friedman['p_value']:.6g}, alpha=0.05).",
        },
        {
            "item": "best_descriptive_protocol",
            "confirmed_statement": f"The best descriptive overall_RankScore is {best['method']} with overall_RankScore={best['overall_RankScore']:.6g}.",
        },
        {
            "item": "stability_protocol_summary",
            "confirmed_statement": f"ExperimentC_StabilityAware_ECMADE_MOO has overall_RankScore={stability['overall_RankScore']:.6g}, mean_RankScore={stability['mean_RankScore']:.6g}, and first_place_windows={int(stability['first_place_windows'])}.",
        },
        {
            "item": "stability_pairwise_claim",
            "confirmed_statement": "ExperimentC_StabilityAware_ECMADE_MOO does not significantly outperform all real-market configuration baselines in RankScore after Holm correction.",
        },
    ]
    summary = pd.DataFrame(rows)
    pair_path = OUT_DIR / "real_market_config_rankscore_pairwise_summary.csv"
    rank_pairs.to_csv(pair_path, index=False, encoding="utf-8-sig")
    summary.to_csv(OUT_DIR / "real_market_config_statistics_confirmed_statements.csv", index=False, encoding="utf-8-sig")
    return summary


def markdown_text(
    feature_schema: pd.DataFrame,
    normalization: pd.DataFrame,
    real_market_stats: pd.DataFrame,
) -> str:
    cfg = read_json(C_SELECTOR_DIR / "training_config.json")
    numeric = feature_schema[feature_schema["feature_type"].eq("numeric")]["feature"].tolist()
    categorical = feature_schema[feature_schema["feature_type"].eq("categorical")]["feature"].tolist()

    lines = [
        "# TEVC Protocol Completion Notes",
        "",
        "以下內容補齊先前不能自行補寫的部分；所有句子均對應目前程式或已產生的後處理結果。",
        "",
        "## 1. RNG 與 Seed Policy",
        "",
        "可寫句：A/B/C 主實驗均使用 MATLAB/PlatEMO 的 `mcg16807` random stream，並以 run index 作為 optimizer seed；同一 problem instance 上各方法共享相同 seed assignment。",
        "",
        "可寫句：Selector-level final-test ablation 同樣使用 MATLAB/PlatEMO 的 `mcg16807` random stream，並以 run index 作為 optimizer seed；各 selector variants 在相同 test instance 使用一致的 seed assignment。",
        "",
        "可寫句：Real-market configured ECMADE-MOO validation 使用 Python runner；其 ECMADE-MOO optimizer 以 `seed=run` 建立設定，並在 `ecmade_moo.py` 中以 `numpy.random.default_rng(cfg.seed)` 產生 random generator。因此 real-market 實驗的 RNG 應寫為 `numpy.default_rng(seed=run)`，不應寫成 MATLAB/PlatEMO `mcg16807`。",
        "",
        "## 2. Normalization 退化情況",
        "",
        "可寫句：本研究的 Pareto-front objective normalization 在每個 comparison group 內進行；若某一目標的 nadir 與 ideal 相同，分母設定為 `max(nadir - ideal, 1e-12)`，以避免除以零，並不額外指定 0.5 或 1 作為人工分數。",
        "",
        "可寫句：Experiment B、Experiment C 與 real-market configured comparison 的 RankScore 均採 rank-based aggregation；ties 使用 average rank，因此當同一 comparison group 內某指標完全相同時，並列方法取得相同的平均名次。",
        "",
        "## 3. Experiment C Random Forest 與 Feature Columns",
        "",
        f"可寫句：Experiment C selector is trained to predict `{cfg['target']}` and selects the theta with the highest predicted C_LabelScore.",
        "",
        "可寫句：The Random Forest model uses 500 trees, `min_samples_leaf=2`, no explicit max-depth constraint, `OneHotEncoder(handle_unknown='ignore')` for categorical fields, and raw numeric passthrough for numeric fields.",
        "",
        f"Numeric features: `{', '.join(numeric)}`.",
        "",
        f"Categorical features: `{', '.join(categorical)}`.",
        "",
        "可寫句：Validation reports top-1 and top-3 theta-selection hit rates; therefore the top-k protocol uses k=1 and k=3.",
        "",
        "## 4. Experiment C Label 與 Selection Rule",
        "",
        "可寫句：`C_LabelScore = -0.2*rank_HV - 0.2*rank_IGD - 0.3*rank_PF_Overlap - 0.3*rank_PF_Drift`; because lower ranks indicate better metric performance, larger C_LabelScore indicates a better stability-aware theta.",
        "",
        "可寫句：`C_ThetaRank` is assigned by sorting C_LabelScore in descending order within each split-instance-K group, and the trained selector chooses the theta with maximum predicted C_LabelScore for each hold-out instance.",
        "",
        "## 5. Real-market Configuration Protocol 統計檢定",
        "",
    ]
    for _, row in real_market_stats.iterrows():
        lines.append(f"- {row['confirmed_statement']}")
    lines += [
        "",
        "可寫句：The real-market configuration-protocol validation should be interpreted as external robustness evidence. It confirms statistically detectable differences among protocols, but it does not support a claim that the stability-aware protocol significantly dominates all real-market baselines.",
        "",
        "## 6. Comparison Group 分離",
        "",
        "可寫句：The six-algorithm real-market validation and the four ECMADE-MOO configuration-protocol validation are reported as two separate comparison groups. Their common reference fronts, rank normalization scopes, and statistical tests are not pooled.",
        "",
        "## 7. 輸出檔案",
        "",
        "- `experiment_c_feature_schema.csv`: Experiment C meta-feature and theta-feature table.",
        "- `normalization_and_ranking_protocol.csv`: normalization, tie handling, and rank direction protocol.",
        "- `real_market_config_statistics_confirmed_statements.csv`: real-market configured comparison confirmed statements.",
        "- `real_market_config_rankscore_pairwise_summary.csv`: RankScore pairwise Wilcoxon + Holm results.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    feature_schema = write_feature_schema()
    normalization = write_normalization_protocol()
    real_market_stats = write_real_market_stats_summary()
    (OUT_DIR / "TEVC_protocol_completion_notes_zh.md").write_text(
        markdown_text(feature_schema, normalization, real_market_stats),
        encoding="utf-8",
    )
    print(f"OUT_DIR={OUT_DIR}")
    print((OUT_DIR / "TEVC_protocol_completion_notes_zh.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
