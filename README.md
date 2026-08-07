# TEVC Supplementary Package (No-Replicate)

[Traditional Chinese](README.zh-TW.md)

This repository is the archived supplementary package for the TEVC portfolio-optimization study. It provides the experimental settings, research code, precomputed run-level outputs, metric tables, statistical tests, figures, logs, and raw Pareto-front (PF) CSV archives used to inspect the reported results.

## Scope and Intended Use

This repository supports artifact inspection and targeted reruns. It is **not a fully automated end-to-end reproduction pipeline**. In particular, `audit_all_artifacts.py` calls the package validators for each documented stage using `--audit-only`; it does not launch optimizers, regenerate labels, retrain the selector, recompute every table, or reproduce the manuscript from scratch.

The precomputed outputs are the authoritative package snapshot. Full optimizer reruns require MATLAB R2020b, the recorded PlatEMO versions, the relevant producer scripts in `code/`, and substantial compute time. Some historical runners also expect their original worksheet-formatted theta workbooks under repository-relative `external_data/`; the frozen configuration used for inspection is included as `configs/theta_L24.csv`. The repository-relative producer and provenance paths are listed in `manifest/source_file_map.csv`.

## Project Purpose

The study evaluates whether a meta-designed, stability-aware ECMADE-MOO configuration protocol improves robustness and Pareto-front quality across synthetic constrained portfolio instances and rolling real-market windows. The formal synthetic selector is the **no-replicate** version: `replicate` remains an instance-provenance field but is excluded from selector inputs.

## Result Snapshot

The statements below are tied to the archived CSV rows listed in `manifest/paper_value_crosscheck.csv`. They must be synchronized with the final manuscript and appendix before submission.

- **Synthetic split:** 112 training, 48 validation, and 32 held-out test instances.
- **Experiment C synthetic comparison:** `ExperimentC_NoReplicate_ECMADE_MOO` has 960 runs over 32 test instances. Its mean stability-weighted rank is `2.375`, versus `2.4375` for `MetaDesigned_ECMADE_MOO`; the corresponding Holm-adjusted pairwise p-value is `0.9091220347`, so this pairwise difference is not statistically significant. The two methods tie on mean rank-based composite rank at `2.46875`; the adjusted pairwise p-value is `1.0`.
- **Selector ablation:** the package currently includes the ablation protocol and assignment manifest, but not a final ablation result/statistical table. Therefore, this README makes no quantitative ablation conclusion.
- **Real market:** the archived real-market method identifier is `ExperimentC_StabilityAware_ECMADE_MOO`. Across 33 universe-window units, the RankScore Friedman test gives `chi-square = 24.6965944272` and `p = 1.7868365549e-05`. Its mean RankScore is `2.5688705234`, while `HandCrafted_ECMADE_MOO` has the lowest mean RankScore (`2.2052341598`). The Holm-adjusted RankScore comparisons of Experiment C against Bayesian, HandCrafted, and MetaDesigned are `1.0`, `1.0`, and `0.5125780637`, respectively.
- **Transaction cost sensitivity:** at 10, 20, and 50 bps, Experiment C's mean annual net returns are `0.3219427032`, `0.3207092913`, and `0.3170134141`; its annual-return rank is third in all three scenarios. These are descriptive sensitivity results, not adjusted significance claims.

## Package Contents

| Requirement | Location |
| --- | --- |
| Research code | `code/`, `manifest/code_inventory.csv` |
| English and Chinese README | `README.md`, `README.zh-TW.md` |
| Python environment | `environment.yml`, `requirements.txt` |
| MATLAB, PlatEMO, CPU, GPU, OS | `system/software_environment.md` |
| Experimental settings | `configs/` |
| Official split and selector artifacts | `data/synthetic/`, `selector/`, `labels/` |
| Run-level tables | `labels/`, `experiments/`, `real_market/` |
| Run logs | `logs/full_run_logs.zip` |
| Tables and statistical tests | `paper_outputs/`, `experiments/`, `real_market/` |
| Figures | `figures/`, `figures/paper_figures.zip` |
| Raw PF/objective/archive CSV | `raw_pf/raw_pf_csv_part*.zip` |
| Integrity checksums | `manifest/artifact_checksums.sha256` |
| Paper-value cross-check | `manifest/paper_value_crosscheck.csv` |

The ZIP archives and frozen selector are stored with Git LFS. Install Git LFS before cloning:

```bash
git lfs install
git clone https://github.com/ating0912/tevc_supplementary_osf_zenodo.git
cd tevc_supplementary_osf_zenodo
git lfs pull
```

## Environment

```bash
conda env create -f environment.yml
conda activate tevc-reproducibility
```

The recorded environment is MATLAB 9.9.0.2037887 (R2020b) Update 8. PlatEMO v2.9.0 is the R2020b baseline implementation; PlatEMO v4.3 is retained for compatibility and reference-PF checks. See `system/software_environment.md` for the hardware and software record.

## Audit the Archived Artifacts

```bash
python scripts/fetch_artifacts.py
python scripts/check_github_package.py
python scripts/check_github_package.py --full-zip-test
python scripts/check_paper_values.py
python scripts/check_no_personal_paths.py
python audit_all_artifacts.py
```

These commands validate the archived package. They do not constitute an end-to-end experimental rerun. The validator checks required files, artifact sizes and SHA-256 hashes, ZIP readability, the 112/48/32 split, the no-replicate feature policy, and key CSV shapes. `--full-zip-test` additionally performs CRC testing of every archived member.

## Reproducibility Trace

1. Settings are fixed in `configs/`; the RNG policy is in `manifest/rng_policy.md`.
2. The official allocation is in `data/synthetic/split_manifest.csv`.
3. Producer scripts are in `code/`; repository-relative provenance is in `manifest/source_file_map.csv`.
4. Precomputed metrics are in `labels/`, `experiments/`, and `real_market/`; logs are in `logs/`.
5. Statistical outputs include Friedman and Wilcoxon-Holm tables beside their experiment outputs.
6. Paper tables, figures, and raw PF files are in `paper_outputs/`, `figures/`, and `raw_pf/`.

## Data Use

Synthetic instances, derived metrics, and raw optimization fronts are redistributed for research verification. Raw market prices are not redistributed because provider terms may apply. The market download code, configuration, ticker/universe metadata in the run archive, and derived results are included so an authorized user can reconstruct the inputs.

## Citation and Archival Release

No Zenodo DOI has been assigned to this repository yet. Until a DOI is minted, cite the GitHub version/tag recorded in `CITATION.cff`; do not cite a placeholder DOI. For formal submission, create the GitHub `v1.0.0` release, archive that release through Zenodo, then update `README.md`, `README.zh-TW.md`, `CITATION.cff`, and the manuscript with the minted DOI. The required steps are in `docs/zenodo_release_checklist.md`.
