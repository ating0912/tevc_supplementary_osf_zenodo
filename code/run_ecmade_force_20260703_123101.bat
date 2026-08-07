@echo off
cd /d "."
matlab -batch "cd('.'); SYNTHETIC_SPLITS={'train','validation','test'}; SYNTHETIC_SKIP_SUMMARY=true; SYNTHETIC_FORCE_RERUN=true; run_p0_lite_synthetic_ecmade_moo;" >> "p0_lite_outputs\synthetic_constrained_portfolio\logs\ECMADE_MOO_force_rerun_20260703_123101.log" 2>&1

