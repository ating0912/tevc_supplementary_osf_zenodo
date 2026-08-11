from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PKG = ROOT / "tevc_reproducibility_package"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def copy_if_exists(source: Path, target: Path, copied: list[dict[str, str]]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "package_path": str(target.relative_to(PKG)).replace("\\", "/"),
        "source_path": str(source),
        "status": "missing_source",
        "notes": "",
    }
    if source.exists():
        shutil.copy2(source, target)
        row["status"] = "copied"
        row["notes"] = f"{source.stat().st_size} bytes"
    copied.append(row)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def derive_official_label_splits() -> None:
    manifest_rows = read_csv_rows(PKG / "data/synthetic/split_manifest.csv")
    split_by_instance = {row["instance"]: row["split"] for row in manifest_rows}
    label_sets = [
        ("raw_run_metrics", "training_raw_run_metrics.csv", "validation_raw_run_metrics.csv"),
        ("theta_summary", "training_theta_summary.csv", "validation_theta_summary.csv"),
        ("theta_ranking_labels", "training_theta_ranking_labels.csv", "validation_theta_ranking_labels.csv"),
    ]
    legacy_dir = PKG / "labels/legacy_70_15_15"
    for label_name, train_name, validation_name in label_sets:
        rows = read_csv_rows(legacy_dir / train_name) + read_csv_rows(legacy_dir / validation_name)
        if not rows or "instance" not in rows[0]:
            continue
        seen: set[tuple[str, ...]] = set()
        official = {"train": [], "validation": []}
        for row in rows:
            split = split_by_instance.get(row.get("instance", ""))
            if split not in official:
                continue
            row = dict(row)
            if "split" in row:
                row["split"] = split
            key = tuple(row.get(k, "") for k in row.keys())
            if key in seen:
                continue
            seen.add(key)
            official[split].append(row)
        for split, out_rows in official.items():
            write_csv(PKG / f"labels/{split}_{label_name}.csv", out_rows)


README = r"""
# TEVC Reproducibility Package

This package is the reproducibility control layer for the TEVC portfolio-optimization study. It is organized so a third party can trace the paper results from experimental settings to raw execution outputs, metric computation, statistical tests, and paper-ready tables or figures.

## Scope

The package covers five result blocks:

1. Experiment A: six-algorithm synthetic comparison: NSGA-II, SPEA2, MOEA/D, GDE3, A-MPMO, and ECMADE-MOO.
2. Experiment B: ECMADE-MOO configuration comparison with HandCrafted, RandomConfig, BayesianConfig, and MetaDesigned protocols.
3. Experiment C: stability-aware no-replicate selector and the final five-method comparison.
4. Ablation studies: selector-level, stability objective, adaptive exchange, elite injection, subpopulation, feature groups, and theta-factor effects.
5. Real-market validation: S&P 100, NASDAQ 100, and Taiwan 50 rolling-window experiments with transaction-cost sensitivity.

## Directory Layout

```text
tevc_reproducibility_package/
├── README.md
├── environment.yml
├── requirements.txt
├── configs/
├── data/
├── labels/
├── selector/
├── experiments/
├── real_market/
├── paper_outputs/
├── manifest/
└── scripts/
```

## Quick Verification

Run the package audit first:

```bash
python scripts/check_package.py
```

The audit checks the mandatory file inventory, the 112/48/32 split manifest, label leakage against the test split when label files are present, and the no-replicate selector artifacts.

## Artifact Audit Entry Point

This command audits the precomputed artifacts. It does not launch a fully automated end-to-end reproduction:

```bash
python audit_all_artifacts.py
```

The wrapper scripts are deliberately small: they document the official order and call the package checks. Connect the heavy MATLAB/Python runners listed in `manifest/source_file_map.csv` when preparing a fully self-contained archive.

## Core Settings

- Population size: 100.
- Max function evaluations: 10000.
- Synthetic experiments: 30 runs per method/configuration.
- Real-market experiments: 10 runs per method-window.
- HV reference point: `(1.1, 1.1)` after objective normalization.
- PF Overlap tolerance: `0.02`.
- Ties in metric ranks: average rank.
- Synthetic split authority: `data/synthetic/split_manifest.csv`, with 112 train, 48 validation, and 32 test instances.
- Formal selector: no-replicate Random Forest selector using problem features and theta design features, not the replicate field.

## What Must Be Self-Contained Before Submission

The package currently includes the key CSV/model artifacts available in this workspace and records large raw-run sources in `manifest/source_file_map.csv`. Before uploading as a journal artifact, confirm that every row in that manifest is either copied into this package or replaced by a public download/rebuild instruction.

## Reviewer Notes

The `replicate` column may remain in manifests for instance identification and legacy auditing, but it must not be used as an input feature for the formal no-replicate selector. The formal selector feature list is frozen in `selector/feature_columns_no_replicate.json`.
"""


ENVIRONMENT_YML = r"""
name: tevc-reproducibility
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.11
  - numpy
  - pandas
  - scipy
  - scikit-learn
  - joblib
  - matplotlib
  - seaborn
  - openpyxl
  - pyyaml
  - pip
  - pip:
      - statsmodels
"""


REQUIREMENTS = r"""
numpy
pandas
scipy
scikit-learn
joblib
matplotlib
seaborn
openpyxl
pyyaml
statsmodels
"""


COMMON_CONFIG = r"""
experiment:
  population_size: 100
  maxFE: 10000
  synthetic_runs_per_method: 30
  real_market_runs_per_method_window: 10
  hv_reference_point: [1.1, 1.1]
  pf_overlap_tolerance: 0.02
  tie_handling: average_rank
  split_authority: data/synthetic/split_manifest.csv
randomness:
  synthetic_optimizer_rng: MATLAB/PlatEMO mcg16807
  python_runner_rng: numpy.random.default_rng(seed)
  optimizer_seed_rule: seed = run_index unless a runner-specific manifest overrides it
  selector_seed: 20260717
normalization:
  objective_rule: (point - ideal) / max(nadir - ideal, 1e-12), clipped to [0, 1]
  group_scope:
    synthetic: split-instance-K or comparison group
    real_market: universe-window
metrics:
  maximize: [HV, PF_Overlap, annual_return, sharpe, sortino]
  minimize: [IGD, PF_Drift, Runtime, cvar95_loss, max_drawdown, turnover]
"""


ALGORITHM_PARAMETERS = r"""
algorithms:
  NSGAII:
    population_size: 100
    maxFE: 10000
    source: PlatEMO/MATLAB-compatible runner
  SPEA2:
    population_size: 100
    maxFE: 10000
    source: PlatEMO/MATLAB-compatible runner
  MOEAD:
    population_size: 100
    maxFE: 10000
    source: PlatEMO/MATLAB-compatible runner
  GDE3:
    population_size: 100
    maxFE: 10000
    source: PlatEMO/MATLAB-compatible runner
  A_MPMO:
    population_size: 100
    maxFE: 10000
    source: A_MPMO_NSGAII_v290.m
  ECMADE_MOO:
    population_size: 100
    maxFE: 10000
    source: ECMADE_MOO.m and ecmade_moo.py
    theta_library: configs/theta_L24.csv
selector:
  model: RandomForestRegressor
  n_estimators: 500
  min_samples_leaf: 2
  max_depth: null
  target: C_LabelScore
  preprocessing:
    categorical: OneHotEncoder(handle_unknown='ignore')
    numeric: passthrough
"""


HANDCRAFTED_THETA = r"""
name: HandCrafted
description: Hand-crafted ECMADE-MOO theta used as a fixed baseline in Experiment B/C.
source_file: configs/theta_L24.csv
selection_rule: locked by protocol; see Experiment B/C method assignment tables.
"""


BAYESIAN_SPACE = r"""
name: BayesianConfig
search_space:
  subpops: [2, 4, 8]
  eliteRatio: [0.01, 0.03, 0.05]
  stagnationThreshold: [10, 20, 30]
  archiveLimitFactor: [3, 5, 8]
  operatorMode: [rand1, rand2, current-to-best]
  exchangeMode: [paper, ring, global]
  bestGuide: [rank, crowding, feasibility]
required_to_report:
  - search_seed
  - number_of_iterations
  - acquisition_rule
  - best_global_theta
"""


ABLATION_CONFIGS = r"""
selector_level:
  FullSelector: all no-replicate problem and theta features
  NoInstanceFeatures: theta features only
  NoThetaFeatures: problem features only
  RandomizedLabels: all formal features with shuffled labels
algorithmic:
  WithoutMetaLearning: fixed or non-selector theta assignment
  WithoutStabilityObjective: removes PF stability component from label score
  WithoutAdaptiveExchange: disables adaptive exchange mechanism
  WithoutEliteInjection: disables elite injection
  SubpopulationNumber: varies subpopulation count
  FeatureGroupAblation: removes feature groups
  ThetaFactorMainEffect: evaluates theta factor effects
required_fields:
  - variant
  - removed_or_fixed_component
  - optimizer_seed
  - selector_seed
  - raw_run_metrics
  - paired_statistical_test
"""


REAL_MARKET_CONFIG = r"""
universes:
  - S&P 100
  - NASDAQ 100
  - Taiwan 50
price_type: Adjusted Close unless the data-source manifest states otherwise
rolling_windows: 33
window_definition:
  training_period: 3 years
  out_of_sample_period: 6 months
runs_per_method_window: 10
transaction_cost_scenarios_bps: [10, 20, 50]
required_outputs:
  - ticker list
  - download date
  - cleaning log
  - rolling window dates
  - selected holdings and weights
  - OOS return path
  - turnover
  - transaction cost sensitivity
  - annual return
  - volatility
  - Sharpe
  - Sortino
  - CVaR
  - MDD
"""


LABEL_FORMULA = r"""
# Label Formula

## Experiment B LabelScore

For each `instance x theta` group, aggregate run-level metrics and rank theta candidates within the same instance/K comparison group.

- Higher is better: HV, PF_Overlap.
- Lower is better: IGD, PF_Drift, Runtime.
- Ties use average rank.
- Lower LabelScore is better when using the average of ranks.

## Experiment C C_LabelScore

The formal stability-aware selector target is:

```text
C_LabelScore = -0.2 * rank_HV
             - 0.2 * rank_IGD
             - 0.3 * rank_PF_Overlap
             - 0.3 * rank_PF_Drift
```

Because smaller metric ranks are better, a larger `C_LabelScore` indicates a better stability-aware theta. `C_ThetaRank` is assigned by sorting `C_LabelScore` descending within each comparison group.

## Leakage Rule

Test instances must not appear in selector training labels. The split authority is `data/synthetic/split_manifest.csv`.
"""


RNG_POLICY = r"""
# RNG and Seed Policy

- Synthetic MATLAB/PlatEMO-style optimizer runs use the MATLAB `mcg16807` stream unless a runner manifest explicitly states otherwise.
- Python real-market configured ECMADE-MOO uses `numpy.random.default_rng(cfg.seed)`.
- The default optimizer seed rule is `seed = run_index`.
- The formal selector seed is `20260717`.
- Selector seed and optimizer seed are distinct and must both be reported for ablation experiments.
- Train/validation/test split must be read from `data/synthetic/split_manifest.csv`; scripts must not re-split instances independently.
"""


DATA_USE = r"""
# Data Use Statement

Synthetic instances and derived metrics may be redistributed with the reproducibility archive. Real-market price data may be subject to data-provider restrictions. If raw prices cannot be redistributed, include ticker lists, date ranges, data-download scripts, cleaning scripts, hashes or summaries, and a small public sample that exercises the full pipeline.
"""


THIRD_PARTY = r"""
# Third-Party Software and Licenses

Record exact versions before final submission:

- Python and packages listed in `environment.yml` / `requirements.txt`.
- MATLAB release.
- PlatEMO release or commit.
- NumPy, pandas, SciPy, scikit-learn, joblib, matplotlib, seaborn, openpyxl, PyYAML, statsmodels.
- Any market-data API client and its license or terms.
"""


CHECK_PACKAGE = r"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED = [
    "README.md",
    "environment.yml",
    "configs/common_experiment_config.yaml",
    "configs/algorithm_parameters.yaml",
    "configs/theta_L24.csv",
    "data/synthetic/split_manifest.csv",
    "labels/label_formula.md",
    "selector/feature_columns_no_replicate.json",
    "selector/test_theta_predictions.csv",
    "selector/test_selected_theta.csv",
    "experiments/experiment_a/experiment_A_run_metrics.csv",
    "experiments/experiment_a/experiment_A_statistical_tests.csv",
    "manifest/source_file_map.csv",
    "manifest/reproducibility_checklist.csv",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def check_required() -> None:
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    if missing:
        fail("missing required files: " + ", ".join(missing))
    print(f"OK: required file set present ({len(REQUIRED)} files)")


def check_split_manifest() -> None:
    path = ROOT / "data/synthetic/split_manifest.csv"
    rows = read_csv(path)
    counts = Counter(row.get("split", "") for row in rows)
    expected = {"train": 112, "validation": 48, "test": 32}
    if counts != expected:
        fail(f"split counts mismatch: observed={dict(counts)}, expected={expected}")
    ids = [row["instance"] for row in rows]
    if len(ids) != len(set(ids)):
        fail("split_manifest.csv contains duplicate instance ids")
    print("OK: split manifest has 112/48/32 instances and unique ids")


def check_label_leakage() -> None:
    manifest = read_csv(ROOT / "data/synthetic/split_manifest.csv")
    test_ids = {row["instance"] for row in manifest if row["split"] == "test"}
    label_files = [
        ROOT / "labels/train_theta_ranking_labels.csv",
        ROOT / "labels/validation_theta_ranking_labels.csv",
        ROOT / "labels/train_raw_run_metrics.csv",
        ROOT / "labels/validation_raw_run_metrics.csv",
    ]
    for path in label_files:
        if not path.exists():
            continue
        rows = read_csv(path)
        if not rows or "instance" not in rows[0]:
            continue
        leaked = sorted({row["instance"] for row in rows if row.get("instance") in test_ids})
        if leaked:
            fail(f"test instances appear in {path.name}: {leaked[:5]}")
    print("OK: no test-instance leakage detected in present label files")


def check_selector_features() -> None:
    path = ROOT / "selector/feature_columns_no_replicate.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    text = json.dumps(data)
    if "replicate" in text:
        fail("formal feature_columns_no_replicate.json still contains replicate")
    print("OK: no-replicate selector feature list excludes replicate")


def main() -> None:
    check_required()
    check_split_manifest()
    check_label_leakage()
    check_selector_features()
    print("Package audit completed.")


if __name__ == "__main__":
    main()
"""


RUN_STAGE = r"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


STAGES = {
    "generate_instances": "Build or verify the 192 synthetic instances and split manifest.",
    "generate_labels": "Recompute train/validation theta labels from raw run metrics.",
    "train_selector_no_replicate": "Train the formal no-replicate selector.",
    "run_final_experiment": "Run Experiment A/B/C/ablation/real-market optimizers.",
    "compute_metrics": "Compute HV, IGD, PF Overlap, PF Drift, EAF width, diversity, runtime, and market metrics.",
    "run_statistical_tests": "Run Friedman, Wilcoxon, Holm correction, and Vargha-Delaney A12 analyses.",
    "generate_tables": "Build paper-ready CSV/XLSX tables.",
    "generate_figures": "Build paper-ready figures.",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=sorted(STAGES))
    parser.add_argument("--audit-only", action="store_true", help="Only run the package audit for this skeleton.")
    args = parser.parse_args()
    print(f"Stage: {args.stage}")
    print(STAGES[args.stage])
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "check_package.py")])
    if args.audit_only:
        return
    print("This wrapper records the official order. Connect the heavy runner listed in manifest/source_file_map.csv for this stage before full archive release.")


if __name__ == "__main__":
    main()
"""


AUDIT_ALL = r"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STAGES = [
    "generate_instances",
    "generate_labels",
    "train_selector_no_replicate",
    "run_final_experiment",
    "compute_metrics",
    "run_statistical_tests",
    "generate_tables",
    "generate_figures",
]


def main() -> None:
    for stage in STAGES:
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "run_stage.py"), "--stage", stage, "--audit-only"])
    print("All precomputed package-artifact audits completed. No research jobs were launched.")


if __name__ == "__main__":
    main()
"""


def stage_wrapper(stage: str) -> str:
    return f"""from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
subprocess.check_call([sys.executable, str(ROOT / "scripts" / "run_stage.py"), "--stage", "{stage}", "--audit-only"])
"""


def build_source_map() -> list[tuple[str, Path]]:
    return [
        ("data/synthetic/split_manifest.csv", ROOT / "data/synthetic_constrained_portfolio/manifest.csv"),
        ("data/synthetic/split_manifest_legacy_70_15_15.csv", ROOT / "data/synthetic_constrained_portfolio/manifest_70_15_15.csv"),
        ("configs/theta_L24.csv", ROOT / "outputs/selector_level_ablation_20260728/theta_candidate_table_used.csv"),
        ("labels/legacy_70_15_15/training_raw_run_metrics.csv", ROOT / "p0_lite_outputs/theta24_70_15_15_training_label_full_20260706/knowledge_base_parameter_report/run_metrics.csv"),
        ("labels/legacy_70_15_15/validation_raw_run_metrics.csv", ROOT / "p0_lite_outputs/theta24_70_15_15_validation_label_full_20260713/knowledge_base_parameter_report/run_metrics.csv"),
        ("labels/legacy_70_15_15/training_theta_summary.csv", ROOT / "p0_lite_outputs/theta24_70_15_15_training_label_full_20260706/knowledge_base_parameter_report/instance_method_metrics.csv"),
        ("labels/legacy_70_15_15/validation_theta_summary.csv", ROOT / "p0_lite_outputs/theta24_70_15_15_validation_label_full_20260713/knowledge_base_parameter_report/instance_method_metrics.csv"),
        ("labels/legacy_70_15_15/training_theta_ranking_labels.csv", ROOT / "p0_lite_outputs/theta24_70_15_15_training_label_full_20260706/knowledge_base_parameter_report/experiment_c_stability_theta_ranking_labels.csv"),
        ("labels/legacy_70_15_15/validation_theta_ranking_labels.csv", ROOT / "p0_lite_outputs/theta24_70_15_15_validation_label_full_20260713/knowledge_base_parameter_report/experiment_c_stability_theta_ranking_labels.csv"),
        ("selector/selector_no_replicate.joblib", ROOT / "outputs/experiment_c_replicate_audit_20260730/full_selector_no_replicate/experiment_c_stability_random_forest.joblib"),
        ("selector/feature_columns_no_replicate.json", ROOT / "outputs/experiment_c_replicate_audit_20260730/full_selector_no_replicate/feature_columns.json"),
        ("selector/validation_theta_predictions.csv", ROOT / "outputs/experiment_c_replicate_audit_20260730/full_selector_no_replicate/validation_predictions.csv"),
        ("selector/test_theta_predictions.csv", ROOT / "outputs/experiment_c_replicate_audit_20260730/full_selector_no_replicate/test_theta_predicted_scores.csv"),
        ("selector/test_selected_theta.csv", ROOT / "outputs/experiment_c_replicate_audit_20260730/full_selector_no_replicate/experiment_c_stability_theta_assignment.csv"),
        ("selector/selector_performance.csv", ROOT / "outputs/experiment_c_replicate_audit_20260730/full_selector_no_replicate/validation_selector_summary.csv"),
        ("experiments/experiment_a/experiment_A_run_metrics.csv", ROOT / "outputs/experiment_A_stats_delivery_20260706/experiment_A_run_metrics.csv"),
        ("experiments/experiment_a/experiment_A_instance_method_summary.csv", ROOT / "outputs/experiment_A_stats_delivery_20260706/experiment_A_instance_method_summary.csv"),
        ("experiments/experiment_a/experiment_A_statistical_tests.csv", ROOT / "outputs/experiment_A_stats_delivery_20260706/experiment_A_statistical_tests.csv"),
        ("experiments/experiment_bc/formal_five_run_metrics.csv", ROOT / "p0_lite_outputs/experiment_c_formal_five_method_no_replicate_20260731/formal_five_run_metrics.csv"),
        ("experiments/experiment_bc/formal_five_instance_method_metrics_raw.csv", ROOT / "p0_lite_outputs/experiment_c_formal_five_method_no_replicate_20260731/formal_five_instance_method_metrics_raw.csv"),
        ("experiments/experiment_bc/formal_five_instance_method_endpoints_ranked.csv", ROOT / "p0_lite_outputs/experiment_c_formal_five_method_no_replicate_20260731/formal_five_instance_method_endpoints_ranked.csv"),
        ("experiments/experiment_bc/formal_five_primary_method_wilcoxon_holm.csv", ROOT / "p0_lite_outputs/experiment_c_formal_five_method_no_replicate_20260731/formal_five_primary_method_wilcoxon_holm.csv"),
        ("experiments/experiment_bc/formal_five_pairwise_wilcoxon_holm.csv", ROOT / "p0_lite_outputs/experiment_c_formal_five_method_no_replicate_20260731/formal_five_pairwise_wilcoxon_holm.csv"),
        ("experiments/experiment_bc/formal_five_friedman_tests.csv", ROOT / "p0_lite_outputs/experiment_c_formal_five_method_no_replicate_20260731/formal_five_friedman_tests.csv"),
        ("experiments/experiment_bc/formal_five_overall_summary.csv", ROOT / "p0_lite_outputs/experiment_c_formal_five_method_no_replicate_20260731/formal_five_overall_summary.csv"),
        ("experiments/no_replicate_audit/replicate_audit_protocol.json", ROOT / "outputs/experiment_c_replicate_audit_20260730/replicate_audit_protocol.json"),
        ("experiments/no_replicate_audit/test_assignment_diff_no_replicate_vs_replicate.csv", ROOT / "outputs/experiment_c_replicate_audit_20260730/test_assignment_diff_no_replicate_vs_replicate.csv"),
        ("experiments/ablation/selector_level_ablation_protocol.json", ROOT / "outputs/selector_level_ablation_20260728/selector_level_ablation_protocol.json"),
        ("experiments/ablation/selector_level_ablation_assignment_manifest.csv", ROOT / "outputs/selector_level_ablation_20260728/selector_level_ablation_assignment_manifest.csv"),
        ("experiments/ablation/theta_candidate_table_used.csv", ROOT / "outputs/selector_level_ablation_20260728/theta_candidate_table_used.csv"),
        ("real_market/configured_run_metrics_with_pf_stability.csv", ROOT / "p0_lite_outputs/p1_rolling_window_market_validation_20260719/configured_ecmade_comparison_summary/configured_run_metrics_with_pf_stability.csv"),
        ("real_market/configured_window_method_summary.csv", ROOT / "p0_lite_outputs/p1_rolling_window_market_validation_20260719/configured_ecmade_comparison_summary/configured_window_method_summary.csv"),
        ("real_market/configured_window_method_ranked.csv", ROOT / "p0_lite_outputs/p1_rolling_window_market_validation_20260719/configured_ecmade_comparison_summary/configured_window_method_ranked.csv"),
        ("real_market/configured_overall_summary.csv", ROOT / "p0_lite_outputs/p1_rolling_window_market_validation_20260719/configured_ecmade_comparison_summary/configured_overall_summary.csv"),
        ("real_market/configured_friedman_tests.csv", ROOT / "p0_lite_outputs/p1_rolling_window_market_validation_20260719/configured_ecmade_comparison_summary/configured_friedman_tests.csv"),
        ("real_market/configured_pairwise_wilcoxon_holm.csv", ROOT / "p0_lite_outputs/p1_rolling_window_market_validation_20260719/configured_ecmade_comparison_summary/configured_pairwise_wilcoxon_holm.csv"),
        ("real_market/configured_transaction_cost_overall.csv", ROOT / "p0_lite_outputs/p1_rolling_window_market_validation_20260719/configured_ecmade_comparison_summary/configured_transaction_cost_overall.csv"),
        ("paper_outputs/table_experiment_a.csv", ROOT / "outputs/experiment_A_stats_delivery_20260706/experiment_A_instance_method_summary.csv"),
        ("paper_outputs/table_experiment_c.csv", ROOT / "p0_lite_outputs/experiment_c_formal_five_method_no_replicate_20260731/formal_five_overall_summary.csv"),
        ("paper_outputs/table_real_market.csv", ROOT / "p0_lite_outputs/p1_rolling_window_market_validation_20260719/configured_ecmade_comparison_summary/configured_overall_summary.csv"),
    ]


def write_docs() -> None:
    write_text(PKG / "README.md", README)
    write_text(PKG / "environment.yml", ENVIRONMENT_YML)
    write_text(PKG / "requirements.txt", REQUIREMENTS)
    write_text(PKG / "DATA_USE_STATEMENT.md", DATA_USE)
    write_text(PKG / "LICENSES_THIRD_PARTY.md", THIRD_PARTY)
    write_text(PKG / "configs/common_experiment_config.yaml", COMMON_CONFIG)
    write_text(PKG / "configs/algorithm_parameters.yaml", ALGORITHM_PARAMETERS)
    write_text(PKG / "configs/handcrafted_theta.yaml", HANDCRAFTED_THETA)
    write_text(PKG / "configs/bayesian_search_space.yaml", BAYESIAN_SPACE)
    write_text(PKG / "configs/ablation_configs.yaml", ABLATION_CONFIGS)
    write_text(PKG / "configs/real_market_config.yaml", REAL_MARKET_CONFIG)
    write_text(PKG / "labels/label_formula.md", LABEL_FORMULA)
    write_text(PKG / "manifest/rng_policy.md", RNG_POLICY)
    write_text(PKG / "scripts/check_package.py", CHECK_PACKAGE)
    write_text(PKG / "scripts/run_stage.py", RUN_STAGE)
    write_text(PKG / "audit_all_artifacts.py", AUDIT_ALL)
    stage_files = [
        ("01_generate_instances.py", "generate_instances"),
        ("02_generate_labels.py", "generate_labels"),
        ("03_train_selector_no_replicate.py", "train_selector_no_replicate"),
        ("04_run_final_experiment.py", "run_final_experiment"),
        ("05_compute_metrics.py", "compute_metrics"),
        ("06_run_statistical_tests.py", "run_statistical_tests"),
        ("07_generate_tables.py", "generate_tables"),
        ("08_generate_figures.py", "generate_figures"),
    ]
    for filename, stage in stage_files:
        write_text(PKG / filename, stage_wrapper(stage))
    readmes = {
        "data/README.md": "Synthetic data manifests, meta-feature tables, and market-data reconstruction notes live here. The split manifest is the only split authority.",
        "labels/README.md": "Selector label-generation files live here. Test instances must not appear in train/validation labels.",
        "selector/README.md": "Formal no-replicate selector artifacts live here, including frozen model, feature columns, validation predictions, and all 24 theta predictions for each test instance.",
        "experiments/README.md": "Experiment A, B/C, no-replicate audit, and ablation run-level metrics and statistical-test outputs live here.",
        "real_market/README.md": "Real-market rolling-window results and transaction-cost sensitivity outputs live here. Raw prices may need public reconstruction scripts or data-provider permission.",
        "paper_outputs/README.md": "Paper-ready tables and figures live here. See manifest/table_figure_map.csv for input-output mapping.",
    }
    for rel, text in readmes.items():
        write_text(PKG / rel, "# " + Path(rel).parent.name + "\n\n" + text)


def write_manifests(copied: list[dict[str, str]]) -> None:
    checklist = [
        ("source_code", "Complete Python/MATLAB source code and runner scripts", "partial", "Workspace scripts are referenced in source_file_map.csv; full raw runner archive still needs final packaging."),
        ("environment", "Python/MATLAB/PlatEMO versions and third-party licenses", "partial", "Python requirements included; fill exact MATLAB and PlatEMO release before submission."),
        ("synthetic_instances", "192 synthetic instances or deterministic generation code", "partial", "Split manifest copied; raw instance files remain in workspace data path."),
        ("split_manifest", "Train/Validation/Test split manifest", "complete", "data/synthetic/split_manifest.csv"),
        ("theta_L24", "L24 24-theta table", "complete_if_copied", "configs/theta_L24.csv"),
        ("rng_policy", "All seeds and RNG policy", "draft", "manifest/rng_policy.md"),
        ("no_replicate_features", "No-replicate meta-features and feature columns", "partial", "Formal feature columns copied; full meta-feature table should be added if not already present."),
        ("labels", "Train/Validation ranking labels", "partial", "labels/train_* and labels/validation_* are filtered from available legacy 70/15/15 outputs by the official 112/48/32 split authority; legacy source files are retained under labels/legacy_70_15_15."),
        ("frozen_selector", "Frozen no-replicate selector", "complete_if_copied", "selector/selector_no_replicate.joblib"),
        ("test_predictions", "Test per-theta predictions and selected theta", "complete_if_copied", "selector/test_theta_predictions.csv and selector/test_selected_theta.csv"),
        ("run_level_metrics", "Experiment A/B/C/ablation run-level metrics", "partial", "Key CSVs copied; raw final archive/objective files should be materialized for full archive."),
        ("statistical_tests", "Statistical-test inputs and outputs", "partial", "Main test CSVs copied; Vargha-Delaney A12 scripts/results should be confirmed."),
        ("real_market", "33 real-market windows and configured results", "partial", "Configured result CSVs copied; raw prices/ticker manifests still need rights-aware packaging."),
        ("paper_outputs", "Paper table/figure reconstruction scripts", "partial", "Paper table CSVs copied; figure scripts should be connected."),
        ("readme_license", "README, license, and data-use statement", "complete", "README.md, DATA_USE_STATEMENT.md, LICENSES_THIRD_PARTY.md"),
    ]
    write_csv(
        PKG / "manifest/reproducibility_checklist.csv",
        [
            {"item": item, "requirement": req, "status": status, "notes": notes}
            for item, req, status, notes in checklist
        ],
    )
    write_csv(PKG / "manifest/source_file_map.csv", copied)
    write_csv(
        PKG / "manifest/table_figure_map.csv",
        [
            {"paper_artifact": "Experiment A table", "package_output": "paper_outputs/table_experiment_a.csv", "inputs": "experiments/experiment_a/experiment_A_instance_method_summary.csv", "script": "outputs/experiment_A_stats_delivery_20260706/build_delivery_csvs.ps1"},
            {"paper_artifact": "Experiment C table", "package_output": "paper_outputs/table_experiment_c.csv", "inputs": "experiments/experiment_bc/formal_five_overall_summary.csv", "script": "summarize_experiment_c_formal_five_method.py"},
            {"paper_artifact": "Real-market table", "package_output": "paper_outputs/table_real_market.csv", "inputs": "real_market/configured_overall_summary.csv", "script": "analyze_real_market_ecmade_config_statistics.py"},
            {"paper_artifact": "Selector performance figure", "package_output": "paper_outputs/figure_selector_performance.pdf", "inputs": "selector/selector_performance.csv", "script": "to be connected"},
            {"paper_artifact": "PF overlay figure", "package_output": "paper_outputs/figure_pf_overlay.pdf", "inputs": "raw final PF/objective files", "script": "to be connected"},
        ],
    )


def write_schema_files() -> None:
    write_csv(
        PKG / "manifest/run_metric_schema.csv",
        [
            {"column": "instance", "type": "string", "description": "Synthetic or market instance/window identifier"},
            {"column": "method", "type": "string", "description": "Algorithm or configuration protocol"},
            {"column": "run", "type": "integer", "description": "Run index and optimizer seed unless overridden"},
            {"column": "HV", "type": "float", "description": "Hypervolume; higher is better"},
            {"column": "IGD", "type": "float", "description": "Inverted generational distance; lower is better"},
            {"column": "PF_Overlap", "type": "float", "description": "Pareto-front overlap at tolerance 0.02; higher is better"},
            {"column": "PF_Drift", "type": "float", "description": "Pareto-front drift; lower is better"},
            {"column": "Diversity", "type": "float", "description": "Diversity measure; direction stated by analysis script"},
            {"column": "Spacing", "type": "float", "description": "Spacing measure; lower is usually better"},
            {"column": "Runtime", "type": "float", "description": "Wall-clock runtime in seconds; lower is better"},
            {"column": "seed", "type": "integer", "description": "Explicit seed when present"},
            {"column": "run_dir", "type": "path", "description": "Path to raw objective/archive/decision files"},
        ],
    )
    write_csv(
        PKG / "manifest/meta_feature_schema.csv",
        [
            {"column": "assets", "formal_selector": "yes", "description": "Number of assets"},
            {"column": "days", "formal_selector": "yes", "description": "Number of observations"},
            {"column": "k_ratio", "formal_selector": "yes", "description": "Cardinality ratio"},
            {"column": "K", "formal_selector": "yes", "description": "Cardinality constraint"},
            {"column": "corr_structure", "formal_selector": "yes", "description": "Synthetic correlation regime"},
            {"column": "return_distribution", "formal_selector": "yes", "description": "Return-distribution regime"},
            {"column": "risk_structure", "formal_selector": "yes", "description": "Risk regime"},
            {"column": "replicate", "formal_selector": "no", "description": "Generation identifier only; excluded from formal selector"},
            {"column": "subpops", "formal_selector": "yes", "description": "Theta design feature"},
            {"column": "eliteRatio", "formal_selector": "yes", "description": "Theta design feature"},
            {"column": "stagnationThreshold", "formal_selector": "yes", "description": "Theta design feature"},
            {"column": "theta", "formal_selector": "yes", "description": "Theta numeric value/id feature"},
            {"column": "archiveLimitFactor", "formal_selector": "yes", "description": "Theta design feature"},
            {"column": "operatorMode", "formal_selector": "yes", "description": "Executable operator mode"},
            {"column": "exchangeMode", "formal_selector": "yes", "description": "Exchange mode"},
            {"column": "bestGuide", "formal_selector": "yes", "description": "Best-guide policy"},
            {"column": "source_operator", "formal_selector": "yes", "description": "Original theta operator family"},
            {"column": "source_migration", "formal_selector": "yes", "description": "Original theta migration strategy"},
            {"column": "source_archive_strategy", "formal_selector": "yes", "description": "Original archive strategy"},
            {"column": "source_constraint_handling", "formal_selector": "yes", "description": "Constraint handling rule"},
        ],
    )


def main() -> None:
    raise SystemExit(
        "DEPRECATED: this historical builder maps superseded pre-20260811 artifacts. "
        "Use manifest/source_file_map.csv and the current repository validators."
    )
    copied: list[dict[str, str]] = []
    write_docs()
    write_schema_files()
    for rel_target, source in build_source_map():
        copy_if_exists(source, PKG / rel_target, copied)
    derive_official_label_splits()
    write_manifests(copied)
    print(f"Package built at: {PKG}")
    status_count = {}
    for row in copied:
        status_count[row["status"]] = status_count.get(row["status"], 0) + 1
    print("Copy status:", status_count)


if __name__ == "__main__":
    sys.exit(main())
