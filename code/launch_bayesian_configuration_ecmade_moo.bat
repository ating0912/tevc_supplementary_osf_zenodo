@echo off
setlocal
cd /d .
if not exist p0_lite_outputs\bayesian_config_launch_logs mkdir p0_lite_outputs\bayesian_config_launch_logs
set OUTLOG=p0_lite_outputs\bayesian_config_launch_logs\bayesian_config_manual.out.log
set ERRLOG=p0_lite_outputs\bayesian_config_launch_logs\bayesian_config_manual.err.log
echo Started %DATE% %TIME% > "%OUTLOG%"
echo Started %DATE% %TIME% > "%ERRLOG%"
matlab -batch "cd('.'); run_bayesian_configuration_ecmade_moo" >> "%OUTLOG%" 2>> "%ERRLOG%"
echo Finished %DATE% %TIME% with exit code %ERRORLEVEL% >> "%OUTLOG%"
echo Finished %DATE% %TIME% with exit code %ERRORLEVEL% >> "%ERRLOG%"
endlocal
