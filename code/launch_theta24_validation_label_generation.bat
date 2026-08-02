@echo off
cd /d C:\Users\yiting\Documents\Playground
matlab -batch "THETA24_FULL_OUT_ROOT='C:\Users\yiting\Documents\Playground\p0_lite_outputs\theta24_70_15_15_validation_label_full_20260713'; THETA24_FULL_SPLITS={'Validation'}; THETA24_FULL_MAX_INSTANCES=29; run_theta24_192instance_label_full"
