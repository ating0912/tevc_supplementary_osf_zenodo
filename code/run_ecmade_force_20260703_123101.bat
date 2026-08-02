@echo off
cd /d "C:\Users\yiting\Documents\Playground"
matlab -batch "cd('C:\Users\yiting\Documents\Playground'); SYNTHETIC_SPLITS={'train','validation','test'}; SYNTHETIC_SKIP_SUMMARY=true; SYNTHETIC_FORCE_RERUN=true; run_p0_lite_synthetic_ecmade_moo;" >> "C:\Users\yiting\Documents\Playground\p0_lite_outputs\synthetic_constrained_portfolio\logs\ECMADE_MOO_force_rerun_20260703_123101.log" 2>&1

