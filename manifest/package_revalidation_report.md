# Package Revalidation Report

- Package: `C:\Users\yiting\Documents\Playground\tevc_supplementary_osf_zenodo`
- Label: osf-zenodo-no-replicate
- Generated: 2026-08-02T20:01:11
- Overall status: **PASS**

## Code Audit

- Code inventory entries: 363
- Python files compiled: 140
- Python compile failures: 0

## Data Audit

- `data/synthetic/split_manifest.csv`: 192 rows, 12 columns
- Split counts: {'train': 112, 'validation': 48, 'test': 32}
- No-replicate feature list contains `replicate`: False

## Key CSV Shapes

- `configs/theta_L24.csv`: 24 rows, 18 columns
- `selector/test_theta_predictions.csv`: 768 rows, 32 columns
- `selector/test_selected_theta.csv`: 32 rows, 15 columns
- `paper_outputs/table_experiment_a.csv`: 1272 rows, 19 columns
- `paper_outputs/table_experiment_c.csv`: 5 rows, 29 columns
- `paper_outputs/table_real_market.csv`: 4 rows, 33 columns

## Supplementary Artifacts

- `logs/full_run_logs.zip`: present, 15.19 MB
- `figures/paper_figures.zip`: present, 12.07 MB
- `raw_pf/raw_pf_csv.zip`: present, 615.64 MB

## Checklist Snapshot

- code: complete_for_workspace_research_code (code/ and manifest/code_inventory.csv)
- README: complete (README.md and README.zh-TW.md)
- environment.yml: complete (environment.yml)
- MATLAB/PlatEMO version: complete (system/software_environment.md)
- CPU/GPU/OS: complete (system/software_environment.md)
- run logs: included (logs/full_run_logs.zip)
- tables: complete_for_summary_tables (paper_outputs/ and experiments/)
- figures: included (figures/ and figures/paper_figures.zip)
- raw PF csv: included (raw_pf/raw_pf_csv.zip)
