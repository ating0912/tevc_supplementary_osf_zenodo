% ECMADE-MOO tuning subset runner.
% Configure SYNTHETIC_OUT_ROOT, SYNTHETIC_RUNS, and SYNTHETIC_INSTANCE_NAMES
% from the MATLAB base workspace before calling this script.

SyntheticRunner.runAlgorithm(@ECMADE_MOO_TUNE_DEFAULT,'ECMADE_TUNE_DEFAULT');
SyntheticRunner.runAlgorithm(@ECMADE_MOO_TUNE_CONSERVATIVE,'ECMADE_TUNE_CONSERVATIVE');
SyntheticRunner.runAlgorithm(@ECMADE_MOO_TUNE_REFERENCE,'ECMADE_TUNE_REFERENCE');
SyntheticRunner.runAlgorithm(@ECMADE_MOO_TUNE_CONSENSUS,'ECMADE_TUNE_CONSENSUS');
