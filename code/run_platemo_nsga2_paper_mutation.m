% Run NSGA-II on ZDT1 with proM interpreted as per-variable mutation rate.
% This matches the paper-style reading of proM = 1.

clear; clc;

N = 100;
M = 2;
D = 30;
maxFE = 10000;
Runs = 30;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir, 'PlatEMO', 'PlatEMO');
outDir = fullfile(scriptDir, 'nsga2_outputs', 'platemo_paper_mutation');

if ~exist(outDir, 'dir')
    mkdir(outDir);
end

addpath(genpath(platemoRoot));

lastObj = [];
for run = 1 : Runs
    rng(run);
    runDir = fullfile(outDir, sprintf('run_%03d', run));
    if ~exist(runDir, 'dir')
        mkdir(runDir);
    end

    [~,Obj,~] = platemo( ...
        'algorithm', @NSGAII_PaperMutation, ...
        'problem', @ZDT1, ...
        'N', N, ...
        'M', M, ...
        'D', D, ...
        'maxFE', maxFE, ...
        'run', run);

    objPath = fullfile(runDir, 'obj.csv');
    writematrix(Obj, objPath);
    lastObj = Obj;
    fprintf('run %03d: saved %s\n', run, objPath);
end

objPath = fullfile(outDir, 'platemo_nsga2_paper_mutation_zdt1_last_run_obj.csv');
writematrix(lastObj, objPath);
fprintf('Saved objectives: %s\n', objPath);
fprintf('Runs:             %d\n', Runs);
fprintf('Solutions/run:    %d\n', size(lastObj, 1));
