% Run PlatEMO's NSGA-II on ZDT1 and save the final objective values.
% Command:
%   matlab -batch "run('run_platemo_nsga2.m')"

clear; clc;

N = 100;
M = 2;
D = 30;
MaxIt = 10000;
Runs = 30;
maxFE = N * MaxIt;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir, 'PlatEMO', 'PlatEMO');
outDir = fullfile(scriptDir, 'nsga2_outputs', 'platemo');

if ~exist(platemoRoot, 'dir')
    error('PlatEMO root not found: %s', platemoRoot);
end

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

    [Dec, Obj, Con] = platemo( ...
        'algorithm', @NSGAII, ...
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

objPath = fullfile(outDir, 'platemo_nsga2_zdt1_last_run_obj.csv');
writematrix(lastObj, objPath);

fig = figure('Visible', 'off');
scatter(lastObj(:,1), lastObj(:,2), 18, 'filled');
xlabel('f1');
ylabel('f2');
title('PlatEMO NSGA-II on ZDT1, last run');
grid on;
figPath = fullfile(outDir, 'platemo_nsga2_zdt1_last_run.png');
exportgraphics(fig, figPath, 'Resolution', 180);
close(fig);

fprintf('Saved objectives: %s\n', objPath);
fprintf('Saved figure:     %s\n', figPath);
fprintf('Runs:             %d\n', Runs);
fprintf('Solutions/run:    %d\n', size(lastObj, 1));
