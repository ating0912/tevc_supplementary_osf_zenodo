% Rebuild summary files from separated NSGA-II and SPEA2 outputs.

clear; clc;
scriptDir = fileparts(mfilename('fullpath'));
outRoot = fullfile(scriptDir,'p0_lite_outputs','port1_nsga2_spea2');
addpath(scriptDir);
P0LiteUtils.rebuildSummary(outRoot,{'NSGAII','SPEA2'});
fprintf('Rebuilt summary: %s\n',outRoot);
