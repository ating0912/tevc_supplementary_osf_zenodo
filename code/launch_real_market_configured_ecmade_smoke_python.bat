@echo off
setlocal

cd /d "%~dp0"

set BASE=p0_lite_outputs\p1_rolling_window_market_validation_20260719
set RAW=%BASE%\raw_configured_ecmade_smoke_py
set OUT=%BASE%\configured_ecmade_comparison_summary_smoke_py
set LOGDIR=%BASE%\logs_configured_ecmade_python

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

python run_real_market_ecmade_configured_python.py ^
  --max-windows 1 ^
  --runs 1 ^
  --max-fe 1000 ^
  --out-root "%RAW%" ^
  --force ^
  > "%LOGDIR%\configured_ecmade_smoke_python.log" 2>&1

if errorlevel 1 (
  echo Smoke configured ECMADE-MOO run failed. See "%LOGDIR%\configured_ecmade_smoke_python.log".
  exit /b 1
)

python analyze_real_market_ecmade_config_comparison.py ^
  --raw-root "%RAW%" ^
  --out-dir "%OUT%" ^
  > "%LOGDIR%\configured_ecmade_smoke_analysis_python.log" 2>&1

if errorlevel 1 (
  echo Smoke configured ECMADE-MOO analysis failed. See "%LOGDIR%\configured_ecmade_smoke_analysis_python.log".
  exit /b 1
)

echo Done.
echo Smoke summary: "%OUT%"
