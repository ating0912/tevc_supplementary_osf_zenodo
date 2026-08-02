@echo off
setlocal
cd /d C:\Users\yiting\Documents\Playground

set LOGDIR=C:\Users\yiting\Documents\Playground\p0_lite_outputs\p1_mokp_config_full_logs_20260719
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

"C:\Program Files\MATLAB\R2026a\bin\matlab.exe" -batch "cd('C:\Users\yiting\Documents\Playground'); P1_MOKP_RANDOM_RUNS=30; P1_MOKP_RANDOM_MAXFE=10000; P1_MOKP_RANDOM_FORCE_RERUN=true; run_p1_mokp_random_config_full" > "%LOGDIR%\RandomConfig.log" 2>&1
"C:\Program Files\MATLAB\R2026a\bin\matlab.exe" -batch "cd('C:\Users\yiting\Documents\Playground'); P1_MOKP_CONFIG_RUNS=30; P1_MOKP_CONFIG_MAXFE=10000; P1_MOKP_CONFIG_FORCE_RERUN=true; run_p1_mokp_meta_transfer_full" > "%LOGDIR%\MetaTransfer.log" 2>&1
"C:\Program Files\MATLAB\R2026a\bin\matlab.exe" -batch "cd('C:\Users\yiting\Documents\Playground'); P1_MOKP_BAYES_CONFIG_RUNS=3; P1_MOKP_BAYES_FINAL_RUNS=30; P1_MOKP_BAYES_CONFIG_MAXFE=5000; P1_MOKP_BAYES_FINAL_MAXFE=10000; P1_MOKP_BAYES_BUDGET=12; P1_MOKP_BAYES_INITIAL_POINTS=5; P1_MOKP_BAYES_FORCE_RERUN=true; run_p1_mokp_bayesian_config_full" > "%LOGDIR%\BayesianConfig.log" 2>&1

endlocal
