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
        row
        for row in rows(relative)
        if all(row.get(column) == value for column, value in criteria.items())
    ]
    if len(matches) != 1:
        raise SystemExit(
            f"FAIL: expected one row in {relative} for {criteria}, found {len(matches)}"
        )
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


def check_synthetic() -> None:
    summary_path = "experiments/experiment_bc/formal_five_overall_summary.csv"
    primary = one(summary_path, method="ExperimentC_NoReplicate_ECMADE_MOO")
    meta = one(summary_path, method="MetaDesigned_ECMADE_MOO")
    if primary["instances"] != "32" or primary["runs"] != "960":
        raise SystemExit("FAIL: Experiment C synthetic sample size is not 32 instances/960 runs")
    close("Experiment C mean StabilityWeightedRank", primary["mean_StabilityWeightedRank"], 2.375)
    close("MetaDesigned mean StabilityWeightedRank", meta["mean_StabilityWeightedRank"], 2.4375)
    close("Experiment C mean RankBasedCompositeRank", primary["mean_RankBasedCompositeRank"], 2.46875)
    close("MetaDesigned mean RankBasedCompositeRank", meta["mean_RankBasedCompositeRank"], 2.46875)

    pair_path = "experiments/experiment_bc/formal_five_primary_method_wilcoxon_holm.csv"
    stability = one(
        pair_path,
        endpoint="StabilityWeightedRank",
        method_a="MetaDesigned_ECMADE_MOO",
        method_b="ExperimentC_NoReplicate_ECMADE_MOO",
    )
    composite = one(
        pair_path,
        endpoint="RankBasedCompositeRank",
        method_a="MetaDesigned_ECMADE_MOO",
        method_b="ExperimentC_NoReplicate_ECMADE_MOO",
    )
    close("synthetic StabilityWeightedRank Holm p", stability["holm_two_sided_p_value"], 0.9091220346944111)
    close("synthetic RankBasedCompositeRank Holm p", composite["holm_two_sided_p_value"], 1.0)


def check_real_market() -> None:
    overall_path = "real_market/configured_overall_summary.csv"
    primary = one(overall_path, method="ExperimentC_StabilityAware_ECMADE_MOO")
    handcrafted = one(overall_path, method="HandCrafted_ECMADE_MOO")
    if primary["windows"] != "33":
        raise SystemExit("FAIL: real-market Experiment C sample size is not 33 windows")
    close("real-market Experiment C mean RankScore", primary["mean_RankScore"], 2.568870523415978)
    close("real-market HandCrafted mean RankScore", handcrafted["mean_RankScore"], 2.2052341597796143)

    friedman = one("real_market/configured_friedman_tests.csv", metric="RankScore")
    close("real-market RankScore Friedman chi-square", friedman["friedman_chi_square"], 24.696594427244538)
    close("real-market RankScore Friedman p", friedman["p_value"], 1.786836554880703e-05)

    pair_path = "real_market/configured_pairwise_wilcoxon_holm.csv"
    expected = {
        "BayesianConfig_ECMADE_MOO": 1.0,
        "HandCrafted_ECMADE_MOO": 1.0,
        "MetaDesigned_ECMADE_MOO": 0.5125780636805797,
    }
    for baseline, adjusted_p in expected.items():
        result = one(
            pair_path,
            metric="RankScore",
            primary="ExperimentC_StabilityAware_ECMADE_MOO",
            baseline=baseline,
        )
        close(f"real-market RankScore Holm p vs {baseline}", result["holm_p_value"], adjusted_p)


def check_cost() -> None:
    path = "real_market/configured_transaction_cost_overall.csv"
    expected = {
        "10bps": 0.3219427031792904,
        "20bps": 0.320709291265399,
        "50bps": 0.31701341409248174,
    }
    for scenario, annual_return in expected.items():
        result = one(
            path,
            cost_scenario=scenario,
            method="ExperimentC_StabilityAware_ECMADE_MOO",
        )
        close(f"Experiment C annual net return at {scenario}", result["mean_annual_net_return"], annual_return)
        close(f"Experiment C annual-return rank at {scenario}", result["rank_annual_net_return"], 3.0)


def check_crosscheck_manifest() -> None:
    manifest = rows("manifest/paper_value_crosscheck.csv")
    if len(manifest) != 17:
        raise SystemExit(f"FAIL: paper-value cross-check row count is {len(manifest)}, expected 17")
    invalid = [row for row in manifest if not row["source_file"] or not row["package_value_status"]]
    if invalid:
        raise SystemExit("FAIL: paper-value cross-check contains rows without sources or status")


def main() -> None:
    check_split()
    check_synthetic()
    check_real_market()
    check_cost()
    check_crosscheck_manifest()
    print("PASS: archived paper values and method identifiers match their source tables")
    print("NOTE: final manuscript/appendix confirmation remains an author-controlled step")


if __name__ == "__main__":
    main()
