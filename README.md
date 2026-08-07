# TEVC Complete Supplementary Package (No-Replicate)

[Traditional Chinese](README.zh-TW.md)

This repository is the complete supplementary and reproducibility package for the TEVC portfolio-optimization study. It connects the experimental settings, executable research code, run-level outputs, metric tables, statistical tests, figures, and raw Pareto-front (PF) CSV archives used to audit the reported results.

## Project Purpose

The study evaluates whether a meta-designed, stability-aware ECMADE-MOO configuration protocol improves robustness and Pareto-front quality across synthetic constrained portfolio instances and rolling real-market windows. The formal selector is the **no-replicate** version: the synthetic `replicate` identifier is retained only for instance provenance and is excluded from selector inputs.

## Main Conclusions

- The official synthetic split contains 112 training, 48 validation, and 32 held-out test instances.
- On the held-out synthetic comparison, `ExperimentC_NoReplicate_ECMADE_MOO` has the best mean stability-weighted rank among the five configuration protocols (`2.375`) and ties the best mean rank-based composite rank (`2.46875`).
- The reported synthetic comparison contains 960 runs for `ExperimentC_NoReplicate_ECMADE_MOO`; test-instance theta predictions and selected theta values are provided in `selector/`.
- Real-market RankScore differences are statistically detectable (`Friedman chi-square = 24.6966`, `p = 1.7868e-05`, `n = 33`). The stability-aware protocol is not the best protocol by overall real-market RankScore, so this evidence supports robustness rather than universal dominance.

## Package Contents

| Requirement | Location |
| --- | --- |
| Research code | `code/` and `manifest/code_inventory.csv` |
| English and Chinese README | `README.md`, `README.zh-TW.md` |
| Python environment | `environment.yml`, `requirements.txt` |
| MATLAB, PlatEMO, CPU, GPU, OS | `system/software_environment.md` |
| Experimental settings | `configs/` |
| Official split and selector inputs | `data/synthetic/`, `selector/`, `labels/` |
| Full run-level tables | `labels/`, `experiments/`, `real_market/` |
| Run logs | `logs/full_run_logs.zip` |
| Paper tables and statistical tests | `paper_outputs/`, `experiments/`, `real_market/` |
| Paper figures | `figures/` and `figures/paper_figures.zip` |
| Raw PF/objective/archive CSV | `raw_pf/raw_pf_csv_part*.zip` |
| Integrity checksums | `manifest/artifact_checksums.sha256` |

The ZIP archives and the frozen selector are stored with Git LFS. The raw PF data is split into independently valid ZIP parts to stay below portable single-object limits. Install Git LFS before cloning:

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

The recorded MATLAB environment is MATLAB 9.9.0.2037887 (R2020b) Update 8. PlatEMO v2.9.0 is the R2020b baseline implementation; PlatEMO v4.3 is retained for compatibility and reference-PF checks. See `system/software_environment.md` for the complete hardware and software record.

## Validate the Package

```bash
python scripts/fetch_artifacts.py
python scripts/check_github_package.py
python scripts/check_github_package.py --full-zip-test
```

The validator checks required files, artifact sizes and SHA-256 hashes, ZIP readability, the 112/48/32 split, the no-replicate feature policy, and key CSV shapes. `--full-zip-test` additionally performs CRC testing of every archived member and may take several minutes.

## Reproducibility Trace

1. Experimental settings are fixed in `configs/` and the RNG policy in `manifest/rng_policy.md`.
2. The official synthetic allocation is recorded in `data/synthetic/split_manifest.csv`; deterministic instance generation code is in `code/generate_synthetic_portfolio_instances.py`.
3. MATLAB/Python runners are in `code/`; `manifest/source_file_map.csv` maps package outputs to their producing scripts and source locations.
4. Run-level metrics are provided in `labels/`, `experiments/`, and `real_market/`; original logs are archived in `logs/`.
5. Statistical outputs are provided beside their experiment tables, including Friedman and Wilcoxon-Holm results.
6. Paper-ready tables are in `paper_outputs/`; figures and raw PF files are in `figures/` and `raw_pf/`.

The precomputed outputs are the authoritative paper snapshot. A full optimizer rerun requires MATLAB R2020b and the stated PlatEMO versions; runtime depends on machine capacity and can be substantial.

## Data Use

Synthetic instances, derived metrics, and raw optimization fronts are redistributed for research verification. Raw market prices are not redistributed because provider terms may apply. `code/download_market_universe_prices.py`, the market configuration, ticker/universe metadata in the run archive, and derived real-market results are included so an authorized user can reconstruct the market inputs.

## Citation and Release

Use `CITATION.cff` when citing this package. Release `v1.0.0` is the package snapshot intended for the TEVC supplementary submission; a Zenodo DOI can be added to the citation and README after archival deposition.
