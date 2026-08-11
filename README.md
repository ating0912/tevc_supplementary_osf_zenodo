# TEVC Supplementary Package (No-Replicate)

[Traditional Chinese](README.zh-TW.md)

This repository is the pre-release GitHub supplementary package for the TEVC portfolio-optimization study and is intended for later archival on OSF and Zenodo after the package is frozen. It preserves the experimental settings, complete research code, precomputed run-level outputs, statistical tests, paper tables, figures, run logs, and raw Pareto-front (PF) CSV archives needed to inspect the reported evidence.

## 1. Project Purpose and Main Conclusion

The study evaluates meta-designed and stability-aware ECMADE-MOO configuration protocols on synthetic constrained portfolio instances, rolling real-market windows, and MOKP transfer tests. The formal synthetic selector is the **no-replicate** version: `replicate` is retained only for provenance and is excluded from selector inputs.

Using the `20260811` manuscript and appendix tables as the authority, the results support differences among methods at several omnibus endpoints, but they do **not** support a blanket claim that the stability-aware method is superior on every endpoint. In Experiment C its pairwise StabilityWeightedRank comparisons are not significant after Holm correction. In the four-configuration real-market protocol, annual net return is significantly higher than MetaDesigned, annual volatility is significantly worse than HandCrafted, runtime is faster, and several PF-quality endpoints are worse. Rank-derived quantities are descriptive only.

## 2. Scope and Intended Use

This repository supports artifact inspection and targeted reruns. It is **not a fully automated end-to-end reproduction pipeline**. `audit_all_artifacts.py` invokes package validators with `--audit-only`; it does not launch every optimizer, regenerate labels, retrain the selector, rebuild every table, or regenerate the manuscript. Current and historical producer roles are listed in `manifest/code_authority.csv`.

Targeted MATLAB/Python runners are included in `code/`. Full optimizer reruns require MATLAB R2020b, the recorded PlatEMO versions, the original data rights, and substantial compute time. The current CSV outputs constitute the evidence snapshot for this pre-release; the formal submission snapshot will be frozen in the `v1.0.0` release. Repository-relative producer/provenance paths are listed in `manifest/source_file_map.csv`; authoritative and audit-only artifacts are distinguished in `manifest/artifact_authority.csv`.

## 3. Data Split and Formal Selector

- Synthetic split: 112 training, 48 validation, and 32 held-out test instances.
- Formal selector: `selector/selector_no_replicate.joblib`.
- Feature policy: `selector/feature_columns_no_replicate.json` contains no `replicate` input.
- Formal test assignments and predictions are in `selector/`.

## 4. Experiment A

Experiment A run-level metrics, instance-method summaries, and statistical tests are in `experiments/experiment_a/`; the paper-ready table is `paper_outputs/table_experiment_a.csv`. These files remain part of the formal artifact inventory and are not replaced by RankScore-only inference.

## 5. Experiments B and C

The corrected five-method Experiment C comparison uses 32 test groups and 960 runs per method. MetaDesigned has mean J-stability `0.6963` and mean StabilityWeightedRank `2.1875`. Stability-aware ECMADE-MOO has mean J-stability `0.6211`, mean StabilityWeightedRank `2.7813`, and mean Diversity `0.8299`.

For J-stability/StabilityWeightedRank, Friedman gives `chi-square = 18.8000`, `p = 0.000860`. Holm-adjusted comparisons of stability-aware ECMADE-MOO against HandCrafted, RandomConfig, BayesianConfig, and MetaDesigned are `0.8086`, `0.1205`, `1.0000`, and `0.2750`; none is significant at 0.05. Formal tables are in `experiments/experiment_bc/`.

## 6. Selector Final-Test Ablation

Four variants were evaluated over 32 groups with 960 runs per variant: FullSelector, NoInstanceFeatures, NoThetaFeatures, and RandomizedLabels. Their mean RankScores are `2.6042`, `2.8125`, `2.3854`, and `2.1979`, respectively. NoThetaFeatures has overall RankScore `2.1667`; FullSelector has `3.0000`.

The RankScore Friedman result is `chi-square = 19.3956`, `p = 0.000226`. FullSelector comparisons against NoInstanceFeatures, NoThetaFeatures, and RandomizedLabels have Holm-adjusted p-values `0.1918`, `1.0000`, and `1.0000`; none is significant. Inputs, assignments, run completeness, run metrics, and tests are in `experiments/selector_ablation/`.

## 7. Validation Feature and Label Ablations

Feature-group and label-objective validation ablation code is included in `code/`. Their archived outputs remain supporting analyses; the final-test selector ablation in Section 6 is the formal held-out selector comparison used for the `20260811` cross-check.

## 8. Mechanism and Parameter Ablations

Mechanism and parameter ablation producers and archived outputs are included in `code/`, `experiments/`, and `artifacts/`. Historical RankScore-based inference is retained only under `artifacts/deprecated_or_audit_only/` and is not used as manuscript evidence.

## 9. Six-Algorithm Real-Market Comparison

The six-algorithm study contains 33 rolling windows. At 10 bps, MOEAD has mean annual net return `34.81%`. GDE3 has mean Sharpe `1.286` and Sortino `2.122`. ECMADE-MOO has mean annual volatility `26.11%` and CVaR95 loss `3.38%`. NSGA-II's CrossWindowOverallRank `2.167` is descriptive only.

For the original financial endpoints, Friedman p-values range from `0.1112` to `0.8115`; none is significant at 0.05. `RankScore`, `WindowRank`, and `CrossWindowOverallRank` are not inferential endpoints. Formal endpoint tests are in `real_market/six_algorithm_endpoint_*.csv`.

## 10. Four-Configuration Real-Market Protocol

Across 33 paired windows, stability-aware ECMADE-MOO has significantly higher annual net return than MetaDesigned (`26/0/7`, Holm `p = 0.034893`) and significantly worse annual volatility than HandCrafted (`12/0/21`, Holm `p = 0.022167`). Sharpe, Sortino, maximum drawdown, CVaR95, turnover, and the other original financial comparisons are not significant after Holm correction.

The stability-aware method is faster than the three baselines, while the formal endpoint table records disadvantages on PF size, HV, IGD, and PF overlap. See `real_market/configuration_protocol_endpoint_pairwise_wilcoxon_holm.csv` for all 16 endpoints and exact multiplicity scope.

## 11. Transaction-Cost Sensitivity

Transaction-cost sensitivity revalues fixed portfolio paths; it does not rerun or cost-condition the optimizer. Raising cost from 10 to 50 bps lowers mean annual net return by about 0.48-0.49 percentage points. MOEAD changes from `0.3481` to `0.3432`, NSGA-II from `0.3369` to `0.3320`, and ECMADE-MOO from `0.3271` to `0.3222`. The ordering is MOEAD, NSGA-II, GDE3, A-MPMO, ECMADE-MOO, SPEA2 in every scenario. These results are descriptive sensitivity evidence only.

## 12. MOKP Transfer Validation

Formal MOKP inference is limited to HV, IGD, PF overlap, PF drift, Diversity, and Runtime. MOKP rank-derived scores are descriptive only. The endpoint-level Friedman and Wilcoxon-Holm files are in `experiments/mokp/`.

## 13. Package Inventory and Audit

| Requirement | Location |
| --- | --- |
| Complete research code | `code/`, `manifest/code_inventory.csv` |
| English/Chinese documentation | `README.md`, `README.zh-TW.md` |
| Python environment | `environment.yml`, `requirements.txt` |
| MATLAB/PlatEMO/CPU/GPU/OS | `system/software_environment.md` |
| Settings and RNG policy | `configs/`, `manifest/rng_policy.md` |
| Run-level outputs and statistics | `labels/`, `experiments/`, `real_market/` |
| Run logs | `logs/full_run_logs.zip` |
| Tables and figures | `paper_outputs/`, `figures/` |
| Raw PF CSV archives | `raw_pf/raw_pf_csv_part*.zip` |
| Provenance, authority, and checksums | `manifest/` |

Large archives and the frozen selector use Git LFS. After cloning, run:

```bash
git lfs install
git lfs pull
conda env create -f environment.yml
conda activate tevc-reproducibility
python scripts/check_github_package.py
python scripts/check_paper_values.py
python scripts/check_no_personal_paths.py
python audit_all_artifacts.py
```

These commands audit the archived snapshot; they are not an end-to-end experimental rerun. `--full-zip-test` additionally CRC-tests every ZIP member.

## Data Use and Release Status

Synthetic instances, derived metrics, and raw optimization fronts are redistributed for research verification. Raw market prices are excluded where provider terms may apply; see `DATA_USE_STATEMENT.md`.

This metadata is `0.9.0-pre-release`. No Zenodo DOI or final `v1.0.0` archive has been minted. After the manuscript, CSV cross-check, and Git LFS release archive are frozen, create the GitHub release, archive it through Zenodo, and then add the DOI to both READMEs, `CITATION.cff`, `.zenodo.json`, and the paper.
