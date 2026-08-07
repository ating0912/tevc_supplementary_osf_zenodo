@echo off
set OUT=p0_lite_outputs\theta24_70_15_15_training_label_full_20260706
if not exist "%OUT%" mkdir "%OUT%"
matlab -batch "cd('.'); THETA24_FULL_OUT_ROOT='p0_lite_outputs\theta24_70_15_15_training_label_full_20260706'; diary(fullfile(THETA24_FULL_OUT_ROOT,'matlab_full.log')); run_theta24_192instance_label_full; diary off" > "%OUT%\outer_stdout.log" 2> "%OUT%\outer_stderr.log"
