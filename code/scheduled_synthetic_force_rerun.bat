@echo off
setlocal

set "ROOT=C:\Users\yiting\Documents\Playground"
set "METHOD=%~1"
set "SMOKE=%~2"
set "SCRIPT="
set "SMOKE_PREFIX="

if /I "%METHOD%"=="ECMADE_MOO" set "SCRIPT=run_p0_lite_synthetic_ecmade_moo"
if /I "%METHOD%"=="A_MPMO" set "SCRIPT=run_p0_lite_synthetic_ampmo"

if "%SCRIPT%"=="" (
    echo Unknown method: %METHOD%
    exit /b 2
)

set "LOGDIR=%ROOT%\p0_lite_outputs\synthetic_constrained_portfolio\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%i"
set "LOG=%LOGDIR%\%METHOD%_scheduled_force_rerun_%STAMP%.log"
if /I "%SMOKE%"=="smoke" set "SMOKE_PREFIX=SYNTHETIC_SMOKE=true;"

cd /d "%ROOT%"
matlab.exe -batch "cd('%ROOT%'); diary('%LOG%'); %SMOKE_PREFIX% SYNTHETIC_SPLITS={'train','validation','test'}; SYNTHETIC_SKIP_SUMMARY=true; SYNTHETIC_FORCE_RERUN=true; %SCRIPT%; diary off;"
