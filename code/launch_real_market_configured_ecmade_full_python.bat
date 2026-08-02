@echo off
setlocal

cd /d "%~dp0"

set BASE=p0_lite_outputs\p1_rolling_window_market_validation_20260719
set RAW=%BASE%\raw_configured_ecmade
set LOGDIR=%BASE%\logs_configured_ecmade_python

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

python run_real_market_ecmade_configured_python.py ^
  --runs 10 ^
  --max-fe 10000 ^
  --pop-size 100 ^
  --transaction-cost 0.001 ^
  --out-root "%RAW%" ^
  > "%LOGDIR%\configured_ecmade_full_python.log" 2>&1

if errorlevel 1 (
  echo Full configured ECMADE-MOO run failed. See "%LOGDIR%\configured_ecmade_full_python.log".
  exit /b 1
)

python analyze_real_market_ecmade_config_comparison.py ^
  --raw-root "%RAW%" ^
  --out-dir "%BASE%\configured_ecmade_comparison_summary" ^
  > "%LOGDIR%\configured_ecmade_analysis_python.log" 2>&1

if errorlevel 1 (
  echo Configured ECMADE-MOO analysis failed. See "%LOGDIR%\configured_ecmade_analysis_python.log".
  exit /b 1
)

echo Done.
echo Raw outputs: "%RAW%"
echo Summary: "%BASE%\configured_ecmade_comparison_summary"
