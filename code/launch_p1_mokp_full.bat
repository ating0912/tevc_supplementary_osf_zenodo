@echo off
setlocal
cd /d C:\Users\yiting\Documents\Playground

set OUTROOT=C:\Users\yiting\Documents\Playground\p0_lite_outputs\p1_multi_objective_knapsack_full_independent_20260719
set LOGDIR=%OUTROOT%\logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

if "%P1_MOKP_LAUNCH_DRY_RUN%"=="1" (
    echo dry-run-ok > "%LOGDIR%\launcher_dry_run.txt"
    exit /b 0
)

"C:\Program Files\MATLAB\R2026a\bin\matlab.exe" -batch "cd('C:\Users\yiting\Documents\Playground'); P1_MOKP_OUT_ROOT='C:\Users\yiting\Documents\Playground\p0_lite_outputs\p1_multi_objective_knapsack_full_independent_20260719'; run_p1_mokp_nsga2" > "%LOGDIR%\NSGAII.log" 2>&1
"C:\Program Files\MATLAB\R2026a\bin\matlab.exe" -batch "cd('C:\Users\yiting\Documents\Playground'); P1_MOKP_OUT_ROOT='C:\Users\yiting\Documents\Playground\p0_lite_outputs\p1_multi_objective_knapsack_full_independent_20260719'; run_p1_mokp_spea2" > "%LOGDIR%\SPEA2.log" 2>&1
"C:\Program Files\MATLAB\R2026a\bin\matlab.exe" -batch "cd('C:\Users\yiting\Documents\Playground'); P1_MOKP_OUT_ROOT='C:\Users\yiting\Documents\Playground\p0_lite_outputs\p1_multi_objective_knapsack_full_independent_20260719'; run_p1_mokp_moead" > "%LOGDIR%\MOEAD.log" 2>&1
"C:\Program Files\MATLAB\R2026a\bin\matlab.exe" -batch "cd('C:\Users\yiting\Documents\Playground'); P1_MOKP_OUT_ROOT='C:\Users\yiting\Documents\Playground\p0_lite_outputs\p1_multi_objective_knapsack_full_independent_20260719'; run_p1_mokp_gde3" > "%LOGDIR%\GDE3.log" 2>&1
"C:\Program Files\MATLAB\R2026a\bin\matlab.exe" -batch "cd('C:\Users\yiting\Documents\Playground'); P1_MOKP_OUT_ROOT='C:\Users\yiting\Documents\Playground\p0_lite_outputs\p1_multi_objective_knapsack_full_independent_20260719'; run_p1_mokp_ecmade_moo" > "%LOGDIR%\ECMADE_MOO.log" 2>&1
"C:\Program Files\MATLAB\R2026a\bin\matlab.exe" -batch "cd('C:\Users\yiting\Documents\Playground'); P1_MOKP_OUT_ROOT='C:\Users\yiting\Documents\Playground\p0_lite_outputs\p1_multi_objective_knapsack_full_independent_20260719'; run_p1_mokp_ampmo" > "%LOGDIR%\A_MPMO.log" 2>&1

"C:\Program Files\MATLAB\R2026a\bin\matlab.exe" -batch "cd('C:\Users\yiting\Documents\Playground'); addpath('C:\Users\yiting\Documents\Playground'); P1KnapsackRunner.rebuildSummary('C:\Users\yiting\Documents\Playground\p0_lite_outputs\p1_multi_objective_knapsack_full_independent_20260719',{'NSGAII','SPEA2','MOEAD','GDE3','ECMADE_MOO','A_MPMO'});" > "%LOGDIR%\rebuild_summary.log" 2>&1
endlocal
