from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
SUMMARY_DIR = ROOT / "p0_lite_outputs" / "experiment_b_configuration_summary_20260713"
OUT = SUMMARY_DIR / "experiment_b_paper_section_zh.md"

NAME = {
    "MetaDesigned_ECMADE_MOO": "Meta-designed ECMADE-MOO",
    "BayesianConfig_ECMADE_MOO": "Bayesian configuration ECMADE-MOO",
    "RandomConfig_ECMADE_MOO": "Random configuration ECMADE-MOO",
    "HandCrafted_ECMADE_MOO": "Hand-crafted ECMADE-MOO",
}


def fmt(x: float, digits: int = 4) -> str:
    return f"{float(x):.{digits}f}"


def p_fmt(x: float) -> str:
    x = float(x)
    if x < 0.001:
        return f"{x:.2e}"
    return f"{x:.4f}"


def compact_overall_table(overall: pd.DataFrame) -> str:
    cols = [
        "Method",
        "HV ↑",
        "IGD ↓",
        "PF overlap ↑",
        "PF drift ↓",
        "Runtime ↓",
        "RankScore ↓",
        "First-place",
    ]
    rows = []
    for _, r in overall.iterrows():
        rows.append(
            [
                NAME[r["method"]],
                fmt(r["mean_HV"]),
                fmt(r["mean_IGD"]),
                fmt(r["mean_PF_Overlap"]),
                fmt(r["mean_PF_Drift"]),
                fmt(r["mean_Runtime"]),
                fmt(r["overall_RankScore"], 3),
                f"{int(r['first_place_instances'])}/32",
            ]
        )
    return pd.DataFrame(rows, columns=cols).to_markdown(index=False)


def rankscore_stats_table(stats: pd.DataFrame) -> str:
    sub = stats[stats["metric"] == "RankScore"].copy()
    rows = []
    for _, r in sub.iterrows():
        rows.append(
            [
                f"Meta-designed vs {NAME[r['baseline']]}",
                f"{int(r['wins'])}/{int(r['ties'])}/{int(r['losses'])}",
                fmt(r["median_improvement"], 3),
                p_fmt(r["holm_p_value"]),
                "Yes" if str(r["significant_0_05"]).lower() == "true" else "No",
            ]
        )
    return pd.DataFrame(
        rows,
        columns=["Comparison", "W/T/L", "Median RankScore improvement", "Holm p", "Significant"],
    ).to_markdown(index=False)


def method_section(overall: pd.DataFrame, stats: pd.DataFrame, friedman: pd.DataFrame) -> str:
    meta = overall[overall["method"] == "MetaDesigned_ECMADE_MOO"].iloc[0]
    bayes = overall[overall["method"] == "BayesianConfig_ECMADE_MOO"].iloc[0]
    random = overall[overall["method"] == "RandomConfig_ECMADE_MOO"].iloc[0]
    hand = overall[overall["method"] == "HandCrafted_ECMADE_MOO"].iloc[0]
    rank_friedman = friedman[friedman["metric"] == "RankScore"].iloc[0]

    lines = [
        "# Experiment B: Configuration Strategy Comparison",
        "",
        "## Experimental Setting",
        "",
        "Experiment B evaluates whether configuration selection can improve ECMADE-MOO on unseen portfolio optimization instances. Four strategies were compared: hand-crafted ECMADE-MOO, random configuration ECMADE-MOO, Bayesian configuration ECMADE-MOO, and meta-designed ECMADE-MOO. All methods were evaluated on the same 32 unseen test instances with 30 independent runs per instance. The population size was fixed at N=100 and the termination budget was fixed at maxFE=10000. Random, Bayesian, and meta-designed strategies all selected configurations from the same L24 theta configuration library.",
        "",
        "For fair post-processing, all raw Pareto fronts from the four methods were pooled per test instance to reconstruct a common reference front. HV, IGD, PF overlap, PF drift, diversity, runtime, and per-instance RankScore were then recomputed under this common-reference setting. Therefore, the reported comparison is based on a shared evaluation reference rather than method-specific reference fronts.",
        "",
        "## Overall Performance",
        "",
        "Table B1 summarizes the overall results across the 32 unseen test instances. Meta-designed ECMADE-MOO achieved the best overall RankScore among the four strategies. It obtained the best average HV, IGD, PF overlap, and PF drift, indicating that the meta-learner selected configurations that improved both convergence quality and Pareto-front stability. In terms of first-place instance ranks, Meta-designed ECMADE-MOO ranked first on 14 out of 32 instances, more than the other strategies.",
        "",
        compact_overall_table(overall),
        "",
        f"Specifically, Meta-designed ECMADE-MOO achieved mean HV={fmt(meta['mean_HV'], 6)}, mean IGD={fmt(meta['mean_IGD'], 6)}, mean PF overlap={fmt(meta['mean_PF_Overlap'], 6)}, and mean PF drift={fmt(meta['mean_PF_Drift'], 6)}. Its overall RankScore was {fmt(meta['overall_RankScore'], 3)}, compared with {fmt(bayes['overall_RankScore'], 3)} for Bayesian configuration, {fmt(random['overall_RankScore'], 3)} for random configuration, and {fmt(hand['overall_RankScore'], 3)} for hand-crafted ECMADE-MOO.",
        "",
        "## Statistical Significance",
        "",
        f"A Friedman test on per-instance RankScore showed a significant difference among the four configuration strategies (χ²={fmt(rank_friedman['friedman_chi_square'], 3)}, p={p_fmt(rank_friedman['p_value'])}). Pairwise one-sided Wilcoxon signed-rank tests with Holm correction were then used to compare Meta-designed ECMADE-MOO against each baseline.",
        "",
        rankscore_stats_table(stats),
        "",
        "The pairwise tests show that Meta-designed ECMADE-MOO significantly outperformed all three baselines in per-instance RankScore. The improvement was strongest against random configuration, where Meta-designed ECMADE-MOO achieved 22 wins, 1 tie, and 9 losses with a Holm-adjusted p-value of 0.0050. It also significantly outperformed hand-crafted ECMADE-MOO and Bayesian configuration, supporting the conclusion that the learned configuration policy generalizes to unseen instances.",
        "",
        "## Runtime Trade-off",
        "",
        f"Runtime results show a trade-off. Bayesian configuration ECMADE-MOO was the fastest during final testing, with mean runtime={fmt(bayes['mean_Runtime'], 4)}, while Meta-designed ECMADE-MOO required mean runtime={fmt(meta['mean_Runtime'], 4)}. However, Bayesian configuration selected a single global theta for all test instances, whereas Meta-designed ECMADE-MOO selected instance-specific theta configurations. Thus, Meta-designed ECMADE-MOO sacrifices some runtime efficiency in exchange for better solution quality and stability.",
        "",
        "## Interpretation",
        "",
        "The results suggest that instance-aware configuration selection is beneficial for ECMADE-MOO. Random configuration can occasionally identify strong settings, but its performance is less stable because the selected theta is not tied to instance characteristics. Bayesian configuration is efficient and robust as a global tuning baseline, but using a single selected theta limits its ability to adapt across heterogeneous test instances. In contrast, Meta-designed ECMADE-MOO uses learned mappings from instance features to theta configurations, enabling it to adapt the algorithm design to the structure of each unseen problem.",
        "",
        "## Limitations",
        "",
        "Although Meta-designed ECMADE-MOO achieved the best overall quality, its runtime was not the best. In addition, the current meta-learner depends on the quality and coverage of the generated label dataset. Future work can extend the training set with more portfolio instances, richer instance features, and additional configuration candidates. It may also be useful to incorporate runtime-aware objectives into the meta-learner so that the selected configuration balances quality and computational cost.",
        "",
        "## Figure Captions",
        "",
        "Figure B1. Overall rank score of four ECMADE-MOO configuration strategies on 32 unseen test instances. Lower RankScore indicates better overall performance across HV, IGD, PF overlap, PF drift, diversity, and runtime.",
        "",
        "Figure B2. Distribution of per-instance RankScore across test instances. Meta-designed ECMADE-MOO shows the best average rank distribution, indicating more stable configuration selection across unseen instances.",
        "",
        "Figure B3. Median improvement of Meta-designed ECMADE-MOO over each baseline across quality and runtime metrics. Positive values indicate that Meta-designed ECMADE-MOO is better under the metric direction.",
        "",
        "Figure B4. Distribution of theta configurations selected by the meta-designed strategy. The meta-learner selected multiple theta settings rather than a single global configuration, reflecting instance-dependent algorithm design.",
        "",
        "## Table Captions",
        "",
        "Table B1. Overall comparison of four ECMADE-MOO configuration strategies on unseen test instances using common-reference performance metrics.",
        "",
        "Table B2. Pairwise Wilcoxon signed-rank tests comparing Meta-designed ECMADE-MOO with each baseline using per-instance RankScore.",
        "",
        "Table B3. Pairwise win/tie/loss counts between configuration strategies for HV, IGD, PF overlap, PF drift, diversity, runtime, and RankScore.",
        "",
        "Table B4. Theta usage distribution for random, Bayesian, and meta-designed configuration strategies.",
    ]
    return "\n".join(lines)


def main() -> None:
    overall = pd.read_csv(SUMMARY_DIR / "overall_configuration_comparison.csv")
    stats = pd.read_csv(SUMMARY_DIR / "statistical_tests_meta_vs_baselines.csv")
    friedman = pd.read_csv(SUMMARY_DIR / "friedman_tests_all_methods.csv")
    text = method_section(overall, stats, friedman)
    OUT.write_text(text, encoding="utf-8-sig")
    print(f"OUT={OUT}")


if __name__ == "__main__":
    main()
