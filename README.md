# TEVC Reproducibility Package - GitHub Version

This repository contains the GitHub-ready **no-replicate** reproducibility package for the TEVC portfolio-optimization study. It provides the code-facing, reviewer-readable control layer for tracing the reported results from experimental settings to selector inputs, metrics, statistical tests, and paper-ready summary tables.

This lightweight GitHub version intentionally excludes heavyweight artifacts such as frozen model binaries, full run-level CSVs, raw Pareto-front archives, and market-price files. Those files are listed in `manifest/external_artifacts.csv`.

## Project Purpose

The purpose of this project is to make the TEVC study reproducible and auditable. The package records the experimental protocol for synthetic portfolio instances, ECMADE-MOO theta selection, no-replicate selector training, final synthetic comparisons, ablation checks, and real-market rolling-window validation.

The central methodological question is whether a meta-designed, stability-aware ECMADE-MOO configuration protocol can improve robustness and Pareto-front quality without relying on the synthetic `replicate` identifier as a selector input.

## Main Conclusions

- The formal GitHub package is the **no-replicate** version: the selector feature list excludes `replicate`, while the official synthetic split remains 112 train / 48 validation / 32 test instances.
- In the 32-instance synthetic final comparison, `ExperimentC_NoReplicate_ECMADE_MOO` achieves the best mean stability-weighted rank among the five ECMADE-MOO configuration protocols (`mean_StabilityWeightedRank = 2.375`) and ties the best mean rank-based composite rank (`mean_RankBasedCompositeRank = 2.46875`).
- The synthetic no-replicate comparison is based on 960 runs for `ExperimentC_NoReplicate_ECMADE_MOO`, with all test-instance theta predictions and selections included in `selector/`.
- In the real-market configured ECMADE-MOO validation, protocol differences are statistically detectable for RankScore (`Friedman chi-square = 24.6966`, `p = 1.7868e-05`, `n = 33` universe-window units). However, the stability-aware protocol is not the best real-market protocol by overall RankScore in the included summary; this result should be interpreted as external robustness evidence rather than a dominance claim.

## Version

- Selector version: **no-replicate**
- Formal selector input policy: the `replicate` field is **not** used as a selector feature.
- Official split authority: `data/synthetic/split_manifest.csv`
- Synthetic split: 112 train / 48 validation / 32 test instances.

The `replicate` column may still appear in the synthetic instance manifest as a data-generation identifier. In this package, it must not appear in `selector/feature_columns_no_replicate.json`.

## Included Files

- Experiment configuration files in `configs/`.
- Official synthetic split manifest in `data/synthetic/split_manifest.csv`.
- L24 theta candidate table in `configs/theta_L24.csv`.
- Formal no-replicate selector feature columns and prediction tables in `selector/`.
- Label formula and RNG policy.
- Paper-ready summary tables.
- Statistical-test outputs that are small enough for GitHub.
- Small CSV samples under `samples/` for large artifacts.
- `manifest/external_artifacts.csv`, which lists every omitted large artifact and where it should be restored.

## Excluded Large Artifacts

Large artifacts are excluded from git and listed in:

```text
manifest/external_artifacts.csv
```

Before a full archival release, upload those files to Zenodo, OSF, GitHub Releases, or Git LFS and fill the `external_url` column.

## Quick Validation

```bash
python scripts/check_github_package.py
```

This script checks the GitHub package structure, confirms the official 112/48/32 split, and verifies that the formal selector feature list excludes `replicate`.

## Full Reproduction

The complete local package can be rebuilt from the parent workspace with:

```bash
python build_tevc_reproducibility_package.py
python build_tevc_github_package.py
```

For full reruns, restore external artifacts first, then use the stage wrappers copied from the full package or connect the original MATLAB/Python runners listed in `manifest/source_file_map.csv`.

## Recommended GitHub Workflow

1. Commit this folder as the public repository root.
2. Keep large outputs out of git.
3. Upload large artifacts separately and update `manifest/external_artifacts.csv`.
4. Add a release tag that matches the paper submission version.
