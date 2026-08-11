from __future__ import annotations

import csv
import math
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def rows(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def one(relative: str, **criteria: str) -> dict[str, str]:
    matches = [
        row for row in rows(relative)
        if all(row.get(column) == value for column, value in criteria.items())
    ]
    if len(matches) != 1:
        raise SystemExit(f"FAIL: expected one row in {relative} for {criteria}, found {len(matches)}")
    return matches[0]


def close(label: str, observed: str | float, expected: float) -> None:
    value = float(observed)
    if not math.isclose(value, expected, rel_tol=1e-10, abs_tol=1e-12):
        raise SystemExit(f"FAIL: {label}: observed={value}, expected={expected}")


def check_split() -> None:
    counts = Counter(row["split"] for row in rows("data/synthetic/split_manifest.csv"))
    expected = Counter({"train": 112, "validation": 48, "test": 32})
    if counts != expected:
        raise SystemExit(f"FAIL: split counts: observed={counts}, expected={expected}")


def check_experiment_c() -> None:
    summary = "experiments/experiment_bc/formal_five_overall_summary.csv"
    meta = one(summary, method="MetaDesigned_ECMADE_MOO")
    stability = one(summary, method="ExperimentC_StabilityAware_ECMADE_MOO")
    if stability["instances"] != "32" or stability["runs"] != "960":
        raise SystemExit("FAIL: Experiment C is not 32 groups/960 runs per method")
    close("MetaDesigned J-stability", meta["mean_J_stability"], 0.6962839426927118)
    close("MetaDesigned StabilityWeightedRank", meta["mean_StabilityWeightedRank"], 2.1875)
    close("stability-aware J-stability", stability["mean_J_stability"], 0.6211132494594517)
    close("stability-aware StabilityWeightedRank", stability["mean_StabilityWeightedRank"], 2.78125)
    close("stability-aware Diversity", stability["mean_Diversity"], 0.8298852283973107)

    friedman = one("experiments/experiment_bc/formal_five_friedman_tests.csv", endpoint="J_stability")
    close("Experiment C Friedman chi-square", friedman["friedman_chi_square"], 18.8)
    close("Experiment C Friedman p", friedman["p_value"], 0.0008603302817889492)

    expected = {
        "HandCrafted_ECMADE_MOO": 0.8085624479228251,
        "RandomConfig_ECMADE_MOO": 0.12052342675068557,
        "BayesianConfig_ECMADE_MOO": 1.0,
        "MetaDesigned_ECMADE_MOO": 0.2749623071153569,
    }
    path = "experiments/experiment_bc/formal_five_primary_method_wilcoxon_holm.csv"
    for baseline, adjusted_p in expected.items():
        result = one(
            path,
            endpoint="StabilityWeightedRank",
            method_a=baseline,
            method_b="ExperimentC_StabilityAware_ECMADE_MOO",
        )
        close(f"Experiment C Holm p vs {baseline}", result["holm_two_sided_p_value"], adjusted_p)
        if result["significant_0_05"].lower() != "false":
            raise SystemExit(f"FAIL: Experiment C pairwise result vs {baseline} should be nonsignificant")


def check_selector_ablation() -> None:
    completeness = rows("experiments/selector_ablation/run_completeness.csv")
    if len(completeness) != 4 or any(row["instances"] != "32" or row["runs"] != "960" for row in completeness):
        raise SystemExit("FAIL: selector ablation completeness is not four variants x 32 groups x 960 runs")
    summary = "experiments/selector_ablation/selector_final_test_summary.csv"
    expected = {
        "SelectorAblation_FullSelector_ECMADE_MOO": (2.6041666666666665, 3.0),
        "SelectorAblation_NoInstanceFeatures_ECMADE_MOO": (2.8125, 2.3333333333333335),
        "SelectorAblation_NoThetaFeatures_ECMADE_MOO": (2.3854166666666665, 2.1666666666666665),
        "SelectorAblation_RandomizedLabels_ECMADE_MOO": (2.1979166666666665, 2.5),
    }
    for method, (mean_rank, overall_rank) in expected.items():
        result = one(summary, method=method)
        close(f"{method} mean RankScore", result["mean_RankScore"], mean_rank)
        close(f"{method} overall RankScore", result["overall_RankScore"], overall_rank)
    friedman = one("experiments/selector_ablation/friedman.csv", metric="RankScore")
    close("selector ablation Friedman chi-square", friedman["friedman_chi_square"], 19.395569620253152)
    close("selector ablation Friedman p", friedman["p_value"], 0.00022644791718851452)
    pair_path = "experiments/selector_ablation/pairwise_wilcoxon_holm.csv"
    pair_expected = {
        "SelectorAblation_NoInstanceFeatures_ECMADE_MOO": 0.19180603307237346,
        "SelectorAblation_NoThetaFeatures_ECMADE_MOO": 1.0,
        "SelectorAblation_RandomizedLabels_ECMADE_MOO": 1.0,
    }
    for baseline, adjusted_p in pair_expected.items():
        result = one(pair_path, metric="RankScore", baseline=baseline)
        close(f"selector Holm p vs {baseline}", result["holm_p_value"], adjusted_p)


def check_six_algorithm_market() -> None:
    overall = "real_market/six_algorithm_overall_summary.csv"
    close("GDE3 Sharpe", one(overall, method="GDE3")["mean_sharpe"], 1.2856362633762435)
    close("GDE3 Sortino", one(overall, method="GDE3")["mean_sortino"], 2.12207822370455)
    close("ECMADE CVaR95", one(overall, method="ECMADE_MOO")["mean_cvar95_loss"], 0.03380085459490298)
    close("NSGA-II descriptive cross-window rank", one(overall, method="NSGAII")["stability_rank_score"], 2.1666666666666665)
    close(
        "ECMADE annual volatility",
        one("real_market/six_algorithm_method_overall_summary_with_volatility.csv", method="ECMADE_MOO")["mean_annual_volatility"],
        0.26110296669437827,
    )
    tests = rows("real_market/six_algorithm_endpoint_friedman_tests.csv")
    original = {
        row["metric"]: float(row["raw_p_value"])
        for row in tests
        if row["metric"] in {
            "annual_net_return_mean", "sharpe_mean", "sortino_mean",
            "max_drawdown_mean", "annual_volatility_mean", "rebalance_turnover_mean",
        }
    }
    if len(original) != 6 or min(original.values()) < 0.1111 or max(original.values()) > 0.8116:
        raise SystemExit(f"FAIL: six-algorithm original financial endpoint p-values are unexpected: {original}")
    if any(value < 0.05 for value in original.values()):
        raise SystemExit("FAIL: an original six-algorithm financial endpoint is unexpectedly significant")
    forbidden = {"RankScore", "WindowRank", "CrossWindowOverallRank"}
    if any(row["metric"] in forbidden for row in tests):
        raise SystemExit("FAIL: rank-derived metric appears in formal six-algorithm inference")


def check_cost() -> None:
    path = "real_market/six_algorithm_transaction_cost_overall.csv"
    expected = {
        ("10bps", "MOEAD"): 0.34808877158444745,
        ("50bps", "MOEAD"): 0.34322281052697506,
        ("10bps", "NSGAII"): 0.3368788479710617,
        ("50bps", "NSGAII"): 0.3320378904623018,
        ("10bps", "ECMADE_MOO"): 0.3271466665095526,
        ("50bps", "ECMADE_MOO"): 0.32223993654333816,
    }
    for (scenario, method), annual_return in expected.items():
        result = one(path, cost_scenario=scenario, method=method)
        close(f"{method} annual net return at {scenario}", result["mean_annual_net_return"], annual_return)
    expected_order = ["MOEAD", "NSGAII", "GDE3", "A_MPMO", "ECMADE_MOO", "SPEA2"]
    for scenario in ("10bps", "20bps", "50bps"):
        scenario_rows = [row for row in rows(path) if row["cost_scenario"] == scenario]
        observed = [row["method"] for row in sorted(scenario_rows, key=lambda row: float(row["rank_annual_net_return"]))]
        if observed != expected_order:
            raise SystemExit(f"FAIL: transaction-cost order at {scenario}: {observed}")


def check_configuration_protocol() -> None:
    path = "real_market/configuration_protocol_endpoint_pairwise_wilcoxon_holm.csv"
    annual = one(path, metric="annual_net_return_mean", baseline_method="MetaDesigned_ECMADE_MOO")
    if (annual["wins"], annual["ties"], annual["losses"]) != ("26", "0", "7"):
        raise SystemExit("FAIL: annual-net-return win/tie/loss count mismatch")
    close("annual net return vs MetaDesigned Holm p", annual["holm_adjusted_p_value"], 0.034893042175099254)
    volatility = one(path, metric="annual_volatility_mean", baseline_method="HandCrafted_ECMADE_MOO")
    if (volatility["wins"], volatility["ties"], volatility["losses"]) != ("12", "0", "21"):
        raise SystemExit("FAIL: annual-volatility win/tie/loss count mismatch")
    close("annual volatility vs HandCrafted Holm p", volatility["holm_adjusted_p_value"], 0.022167447488754988)


def check_mokp_scope() -> None:
    allowed = {"HV", "IGD", "PF_Overlap", "PF_Drift", "Diversity", "Runtime"}
    actual = {row["metric"] for row in rows("experiments/mokp/mokp_endpoint_friedman_tests.csv")}
    if actual != allowed:
        raise SystemExit(f"FAIL: MOKP endpoint scope: observed={actual}, expected={allowed}")


def check_crosscheck_manifest() -> None:
    manifest = rows("manifest/paper_value_crosscheck.csv")
    if len(manifest) < 45:
        raise SystemExit(f"FAIL: paper-value cross-check has only {len(manifest)} rows")
    invalid = [row for row in manifest if not row["source_file"] or row["package_value_status"] != "verified"]
    if invalid:
        raise SystemExit("FAIL: paper-value cross-check contains unverified or unsourced rows")
    pending = [row for row in manifest if row["manuscript_sync_status"] != "confirmed_20260811_formal_table"]
    if pending:
        raise SystemExit("FAIL: paper-value cross-check contains rows not confirmed against 20260811 formal tables")
    missing_sources = sorted({row["source_file"] for row in manifest if not (ROOT / row["source_file"]).is_file()})
    if missing_sources:
        raise SystemExit("FAIL: paper-value source files are missing: " + ", ".join(missing_sources))


def main() -> None:
    check_split()
    check_experiment_c()
    check_selector_ablation()
    check_six_algorithm_market()
    check_cost()
    check_configuration_protocol()
    check_mokp_scope()
    check_crosscheck_manifest()
    print("PASS: package values match the 20260811 formal manuscript/appendix tables")
    print("PASS: rank-derived real-market and MOKP quantities are excluded from formal inference")


if __name__ == "__main__":
    main()
