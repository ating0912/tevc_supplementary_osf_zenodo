@echo off
setlocal
cd /d C:\Users\yiting\Documents\Playground

set ASSIGN=C:\Users\yiting\Documents\Playground\p0_lite_outputs\p1_rolling_window_market_validation_20260719\config_protocol_assignments\real_market_ecmade_configuration_assignment.csv
set OUTROOT=C:\Users\yiting\Documents\Playground\p0_lite_outputs\p1_rolling_window_market_validation_20260719\raw_configured_ecmade_smoke
set LOGDIR=C:\Users\yiting\Documents\Playground\p0_lite_outputs\p1_rolling_window_market_validation_20260719\logs_configured_ecmade_smoke
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

matlab -batch "cd('C:\Users\yiting\Documents\Playground'); P1_ROLLING_METHOD='HandCrafted_ECMADE_MOO'; P1_ROLLING_THETA_ASSIGNMENT='%ASSIGN%'; P1_ROLLING_OUT_ROOT='%OUTROOT%'; P1_ROLLING_MAX_WINDOWS=1; P1_ROLLING_RUNS=1; P1_ROLLING_MAXFE=1000; P1_ROLLING_FORCE_RERUN=true; run_p1_rolling_market_configured_ecmade_moo" > "%LOGDIR%\HandCrafted_ECMADE_MOO.log" 2>&1
matlab -batch "cd('C:\Users\yiting\Documents\Playground'); P1_ROLLING_METHOD='BayesianConfig_ECMADE_MOO'; P1_ROLLING_THETA_ASSIGNMENT='%ASSIGN%'; P1_ROLLING_OUT_ROOT='%OUTROOT%'; P1_ROLLING_MAX_WINDOWS=1; P1_ROLLING_RUNS=1; P1_ROLLING_MAXFE=1000; P1_ROLLING_FORCE_RERUN=true; run_p1_rolling_market_configured_ecmade_moo" > "%LOGDIR%\BayesianConfig_ECMADE_MOO.log" 2>&1
matlab -batch "cd('C:\Users\yiting\Documents\Playground'); P1_ROLLING_METHOD='MetaDesigned_ECMADE_MOO'; P1_ROLLING_THETA_ASSIGNMENT='%ASSIGN%'; P1_ROLLING_OUT_ROOT='%OUTROOT%'; P1_ROLLING_MAX_WINDOWS=1; P1_ROLLING_RUNS=1; P1_ROLLING_MAXFE=1000; P1_ROLLING_FORCE_RERUN=true; run_p1_rolling_market_configured_ecmade_moo" > "%LOGDIR%\MetaDesigned_ECMADE_MOO.log" 2>&1
matlab -batch "cd('C:\Users\yiting\Documents\Playground'); P1_ROLLING_METHOD='ExperimentC_StabilityAware_ECMADE_MOO'; P1_ROLLING_THETA_ASSIGNMENT='%ASSIGN%'; P1_ROLLING_OUT_ROOT='%OUTROOT%'; P1_ROLLING_MAX_WINDOWS=1; P1_ROLLING_RUNS=1; P1_ROLLING_MAXFE=1000; P1_ROLLING_FORCE_RERUN=true; run_p1_rolling_market_configured_ecmade_moo" > "%LOGDIR%\ExperimentC_StabilityAware_ECMADE_MOO.log" 2>&1

endlocal
