@echo off
setlocal
cd /d C:\Users\yiting\Documents\Playground

set ASSIGN=C:\Users\yiting\Documents\Playground\p0_lite_outputs\p1_rolling_window_market_validation_20260719\config_protocol_assignments\real_market_ecmade_configuration_assignment.csv
set OUTROOT=C:\Users\yiting\Documents\Playground\p0_lite_outputs\p1_rolling_window_market_validation_20260719\raw_configured_ecmade
set LOGDIR=C:\Users\yiting\Documents\Playground\p0_lite_outputs\p1_rolling_window_market_validation_20260719\logs_configured_ecmade
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

matlab -batch "cd('C:\Users\yiting\Documents\Playground'); P1_ROLLING_METHOD='HandCrafted_ECMADE_MOO'; P1_ROLLING_THETA_ASSIGNMENT='%ASSIGN%'; P1_ROLLING_OUT_ROOT='%OUTROOT%'; P1_ROLLING_RUNS=10; P1_ROLLING_MAXFE=10000; P1_ROLLING_FORCE_RERUN=false; run_p1_rolling_market_configured_ecmade_moo" > "%LOGDIR%\HandCrafted_ECMADE_MOO.log" 2>&1
matlab -batch "cd('C:\Users\yiting\Documents\Playground'); P1_ROLLING_METHOD='BayesianConfig_ECMADE_MOO'; P1_ROLLING_THETA_ASSIGNMENT='%ASSIGN%'; P1_ROLLING_OUT_ROOT='%OUTROOT%'; P1_ROLLING_RUNS=10; P1_ROLLING_MAXFE=10000; P1_ROLLING_FORCE_RERUN=false; run_p1_rolling_market_configured_ecmade_moo" > "%LOGDIR%\BayesianConfig_ECMADE_MOO.log" 2>&1
matlab -batch "cd('C:\Users\yiting\Documents\Playground'); P1_ROLLING_METHOD='MetaDesigned_ECMADE_MOO'; P1_ROLLING_THETA_ASSIGNMENT='%ASSIGN%'; P1_ROLLING_OUT_ROOT='%OUTROOT%'; P1_ROLLING_RUNS=10; P1_ROLLING_MAXFE=10000; P1_ROLLING_FORCE_RERUN=false; run_p1_rolling_market_configured_ecmade_moo" > "%LOGDIR%\MetaDesigned_ECMADE_MOO.log" 2>&1
matlab -batch "cd('C:\Users\yiting\Documents\Playground'); P1_ROLLING_METHOD='ExperimentC_StabilityAware_ECMADE_MOO'; P1_ROLLING_THETA_ASSIGNMENT='%ASSIGN%'; P1_ROLLING_OUT_ROOT='%OUTROOT%'; P1_ROLLING_RUNS=10; P1_ROLLING_MAXFE=10000; P1_ROLLING_FORCE_RERUN=false; run_p1_rolling_market_configured_ecmade_moo" > "%LOGDIR%\ExperimentC_StabilityAware_ECMADE_MOO.log" 2>&1

python analyze_real_market_ecmade_config_comparison.py > "%LOGDIR%\configured_analysis.log" 2>&1

endlocal
