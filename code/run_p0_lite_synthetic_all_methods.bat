@echo off
setlocal enabledelayedexpansion

rem Sequential launcher for all synthetic constrained portfolio methods.
rem Each method is still launched through its own MATLAB script.

set "ROOT=."
set "OUT=%ROOT%\p0_lite_outputs\synthetic_constrained_portfolio"
set "LOGDIR=%OUT%\logs"

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

set "PREFIX=SYNTHETIC_SPLITS={'train','validation','test'}; SYNTHETIC_SKIP_SUMMARY=true;"
if /I "%~1"=="smoke" (
    set "PREFIX=SYNTHETIC_SMOKE=true; SYNTHETIC_SPLITS={'train','validation','test'}; SYNTHETIC_SKIP_SUMMARY=true;"
)

call :run_one NSGAII run_p0_lite_synthetic_nsga2
if errorlevel 1 exit /b %errorlevel%

call :run_one SPEA2 run_p0_lite_synthetic_spea2
if errorlevel 1 exit /b %errorlevel%

call :run_one MOEAD run_p0_lite_synthetic_moead
if errorlevel 1 exit /b %errorlevel%

call :run_one ECMADE_MOO run_p0_lite_synthetic_ecmade_moo
if errorlevel 1 exit /b %errorlevel%

call :run_one GDE3 run_p0_lite_synthetic_gde3
if errorlevel 1 exit /b %errorlevel%

call :run_one A_MPMO run_p0_lite_synthetic_ampmo
if errorlevel 1 exit /b %errorlevel%

echo All synthetic methods finished.
exit /b 0

:run_one
set "METHOD=%~1"
set "SCRIPT=%~2"
set "LOG=%LOGDIR%\%METHOD%.log"
echo [%date% %time%] Starting %METHOD%
echo.>> "%LOG%"
echo ===== Resume %METHOD% at %date% %time% =====>> "%LOG%"
matlab -batch "cd('%ROOT%'); %PREFIX% %SCRIPT%;" >> "%LOG%" 2>&1
set "STATUS=%errorlevel%"
if not "%STATUS%"=="0" (
    echo [%date% %time%] %METHOD% failed with exit code %STATUS%. See "%LOG%".
    exit /b %STATUS%
)
echo [%date% %time%] Finished %METHOD%. Log: "%LOG%"
exit /b 0
