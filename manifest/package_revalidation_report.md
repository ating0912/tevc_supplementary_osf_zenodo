# TEVC Reproducibility Package Revalidation Report

- Generated: `2026-08-11T14:27:05+08:00`
- Validated numerical-content revision: `70799c6`
- Report metadata corrections: included in the Git commit containing this report
- Authority: `20260811` formal manuscript and appendix tables
- Package role: precomputed-artifact archive and audit package; **not a fully automated end-to-end reproduction**
- Release metadata: `0.9.0-pre-release`; Zenodo DOI not yet minted

## 1. Completion Status

| Check | Status | Evidence |
| --- | --- | --- |
| Requested package items | PASS | `9` checklist rows |
| Formal paper-value sync | PASS | `48/48` rows confirmed against 20260811 tables |
| Synthetic split | PASS | train `112`, validation `48`, test `32` |
| Authority boundary | PASS | `6` historical files explicitly marked audit-only |
| Run logs | PASS | `5738` archived members |
| Raw PF CSV | PASS | `68832` files in `6` ZIP parts |
| SHA-256 manifest | PASS after validator | `43` tracked artifacts |

## 2. Changes in This Revalidation

1. Replaced Experiment C tables with the corrected 20260809 selector outputs adopted by the 20260811 formal tables.
2. Added the complete four-variant selector final-test ablation: assignments, 3,840 run records, completeness, summary, Friedman, and Wilcoxon-Holm tables.
3. Split real-market evidence into the six-algorithm protocol and four-configuration protocol; removed rank-derived quantities from formal inference.
4. Added formal six-algorithm cost sensitivity, 16-endpoint four-configuration tests, and six-endpoint MOKP inference.
5. Moved legacy RankScore inference and ambiguous tables to `artifacts/deprecated_or_audit_only/` and documented replacements in `manifest/artifact_authority.csv`.
6. Rebuilt bilingual README conclusions, paper-value cross-checks, provenance, validators, checksums, and pre-release citation metadata.

## 3. Formal Result Cross-Check

### Experiment C

- 32 held-out groups and `960` runs per method.
- MetaDesigned: J-stability `0.6963`, StabilityWeightedRank `2.1875`.
- Stability-aware: J-stability `0.6211`, StabilityWeightedRank `2.7812`, Diversity `0.8299`.
- Friedman: chi-square `18.8000`, p `0.000860`.
- All four named pairwise StabilityWeightedRank comparisons are nonsignificant after Holm correction.

### Selector Final-Test Ablation

- FullSelector mean RankScore `2.6042`; NoThetaFeatures `2.3854`; RandomizedLabels `2.1979`.
- Friedman: chi-square `19.3956`, p `0.000226`.
- FullSelector has no significant RankScore pairwise superiority after Holm correction.

### Real Market and Cost

- Six-algorithm original financial endpoint Friedman p-values are 0.1112-0.8115; none is significant.
- Stability-aware annual net return vs MetaDesigned: `26/0/7`, Holm p `0.034893`, significantly higher.
- Stability-aware annual volatility vs HandCrafted: `12/0/21`, Holm p `0.022167`, significantly worse.
- Fixed-path MOEAD annual net return changes from `0.3481` at 10 bps to `0.3432` at 50 bps; this is descriptive and not cost-aware reoptimization.

### MOKP

Formal inference is restricted to HV, IGD, PF overlap, PF drift, Diversity, and Runtime. Rank-derived values are descriptive only.

## 4. Recorded Environment

- OS: Microsoft Windows NT 10.0.26200.0 (Windows 11 generation), 64-bit
- CPU: Intel64 Family 6 Model 186 Stepping 2, GenuineIntel
- GPU: NVIDIA GeForce RTX 4050 Laptop GPU and Intel Iris Xe Graphics
- MATLAB: 9.9.0.2037887 (R2020b) Update 8
- PlatEMO baseline: PlatEMO v2.9.0

## 5. Audit and Release Boundary

`audit_all_artifacts.py` audits the frozen package with `--audit-only`. Targeted runners remain available under `code/`, but complete label generation, selector training, optimizer execution, table construction, and manuscript generation are not orchestrated as one command.

Before final submission, run the validators, freeze a GitHub `v1.0.0` release with all Git LFS objects, archive that exact release on Zenodo, and then update the DOI in both READMEs, `CITATION.cff`, `.zenodo.json`, and the manuscript.
