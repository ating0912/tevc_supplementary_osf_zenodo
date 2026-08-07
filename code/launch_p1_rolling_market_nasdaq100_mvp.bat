@echo off
setlocal
cd /d .

set LOGDIR=p0_lite_outputs\p1_rolling_window_market_validation_20260719\logs_nasdaq100_mvp
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

"C:\Program Files\MATLAB\R2026a\bin\matlab.exe" -batch "cd('.'); P1_ROLLING_UNIVERSES={'NASDAQ100'}; P1_ROLLING_RUNS=10; P1_ROLLING_MAXFE=10000; P1_ROLLING_FORCE_RERUN=true; run_p1_rolling_market_nsga2" > "%LOGDIR%\NSGAII.log" 2>&1
"C:\Program Files\MATLAB\R2026a\bin\matlab.exe" -batch "cd('.'); P1_ROLLING_UNIVERSES={'NASDAQ100'}; P1_ROLLING_RUNS=10; P1_ROLLING_MAXFE=10000; P1_ROLLING_FORCE_RERUN=true; run_p1_rolling_market_spea2" > "%LOGDIR%\SPEA2.log" 2>&1
"C:\Program Files\MATLAB\R2026a\bin\matlab.exe" -batch "cd('.'); P1_ROLLING_UNIVERSES={'NASDAQ100'}; P1_ROLLING_RUNS=10; P1_ROLLING_MAXFE=10000; P1_ROLLING_FORCE_RERUN=true; run_p1_rolling_market_moead" > "%LOGDIR%\MOEAD.log" 2>&1
"C:\Program Files\MATLAB\R2026a\bin\matlab.exe" -batch "cd('.'); P1_ROLLING_UNIVERSES={'NASDAQ100'}; P1_ROLLING_RUNS=10; P1_ROLLING_MAXFE=10000; P1_ROLLING_FORCE_RERUN=true; run_p1_rolling_market_gde3" > "%LOGDIR%\GDE3.log" 2>&1
"C:\Program Files\MATLAB\R2026a\bin\matlab.exe" -batch "cd('.'); P1_ROLLING_UNIVERSES={'NASDAQ100'}; P1_ROLLING_RUNS=10; P1_ROLLING_MAXFE=10000; P1_ROLLING_FORCE_RERUN=true; run_p1_rolling_market_ampmo" > "%LOGDIR%\A_MPMO.log" 2>&1
"C:\Program Files\MATLAB\R2026a\bin\matlab.exe" -batch "cd('.'); P1_ROLLING_UNIVERSES={'NASDAQ100'}; P1_ROLLING_RUNS=10; P1_ROLLING_MAXFE=10000; P1_ROLLING_FORCE_RERUN=true; run_p1_rolling_market_ecmade_moo" > "%LOGDIR%\ECMADE_MOO.log" 2>&1

endlocal
