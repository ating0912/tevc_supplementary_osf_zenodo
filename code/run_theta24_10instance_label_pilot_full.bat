@echo off
set OUT=C:\Users\yiting\Documents\Playground\p0_lite_outputs\theta24_10instance_label_pilot_20260704_full
if not exist "%OUT%" mkdir "%OUT%"
matlab -batch "cd('C:\Users\yiting\Documents\Playground'); THETA24_PILOT_OUT_ROOT='C:\Users\yiting\Documents\Playground\p0_lite_outputs\theta24_10instance_label_pilot_20260704_full'; diary(fullfile(THETA24_PILOT_OUT_ROOT,'matlab_full.log')); run_theta24_10instance_label_pilot; diary off" > "%OUT%\outer_stdout.log" 2> "%OUT%\outer_stderr.log"
