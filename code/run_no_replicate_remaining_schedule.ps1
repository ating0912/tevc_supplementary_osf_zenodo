$ErrorActionPreference = "Stop"

Write-Host "Step 1/5: Resume selector-level final-test ablation to 30 runs"
matlab -batch "SELECTOR_ABLATION_RUNS=30; SELECTOR_ABLATION_FORCE_RERUN=false; run_selector_level_ablation_final_test"

Write-Host "Step 2/5: Rebuild selector-level final-test ablation analysis"
python analyze_selector_level_ablation_final_test.py

Write-Host "Step 3/5: Build reproducibility manifest"
python build_no_replicate_repro_manifest.py

Write-Host "Step 4/5: Refresh data existence audit"
python audit_no_replicate_data_existence_20260731.py

Write-Host "Step 5/5: Refresh Chinese no-replicate audit report"
python build_experiment_c_no_replicate_audit_report_zh.py

Write-Host "No-replicate remaining schedule complete."
