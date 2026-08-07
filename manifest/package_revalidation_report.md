# Package Revalidation Report

- Package: TEVC supplementary artifact package, no-replicate release
- Version: `v1.0.0`
- Generated: 2026-08-07T16:01:48+08:00
- Overall status: **PASS**
- Scope: precomputed-artifact archive and audit; not an automated end-to-end rerun

## Code Audit

- Code inventory entries: 363
- Python source files: 140
- MATLAB source files: 181
- Tracked Python bytecode/cache files: 0
- Personal absolute paths in tracked text: 0

## Data Audit

- `data/synthetic/split_manifest.csv`: 192 rows
- Split counts: {'train': 112, 'validation': 48, 'test': 32}
- Formal selector policy: no-replicate (`selector/feature_columns_no_replicate.json`)
- Full run-level tables: included under `labels/`, `experiments/`, and `real_market/`

## Supplementary Artifacts

- Run logs: `logs/full_run_logs.zip`, 5738 files, 15.19 MB
- Figures: `figures/paper_figures.zip`, 64 files, 12.07 MB
- Raw PF CSV: 6 ZIP parts, 68832 files, 832.34 MB
- SHA-256 manifest: 25 verified artifacts
- Paper-value cross-check: `manifest/paper_value_crosscheck.csv`

## Reviewer Checklist

- code: complete
- bilingual README: complete
- environment.yml: complete
- MATLAB/PlatEMO versions: complete
- CPU/GPU/OS: complete
- run logs: complete
- tables and statistical tests: complete
- figures: complete
- raw PF CSV: complete

Validation commands:

- `python scripts/check_github_package.py --full-zip-test`
- `python scripts/check_paper_values.py`
- `python scripts/check_no_personal_paths.py`
