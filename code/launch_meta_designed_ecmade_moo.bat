@echo off
setlocal
cd /d .
if not exist p0_lite_outputs\meta_designed_launch_logs mkdir p0_lite_outputs\meta_designed_launch_logs
set OUTLOG=p0_lite_outputs\meta_designed_launch_logs\meta_designed_manual.out.log
set ERRLOG=p0_lite_outputs\meta_designed_launch_logs\meta_designed_manual.err.log
echo Started %DATE% %TIME% > "%OUTLOG%"
echo Started %DATE% %TIME% > "%ERRLOG%"
matlab -batch "cd('.'); run_meta_designed_ecmade_moo" >> "%OUTLOG%" 2>> "%ERRLOG%"
echo Finished %DATE% %TIME% with exit code %ERRORLEVEL% >> "%OUTLOG%"
echo Finished %DATE% %TIME% with exit code %ERRORLEVEL% >> "%ERRLOG%"
endlocal
