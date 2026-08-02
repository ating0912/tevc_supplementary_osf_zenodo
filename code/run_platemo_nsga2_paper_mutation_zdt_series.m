% Run paper-style NSGA-II on ZDT1, ZDT2, ZDT3, ZDT4, and ZDT6.

clear; clc;

N = 100;
M = 2;
maxFE = 10000;
Runs = 30;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir, 'PlatEMO', 'PlatEMO');
outRoot = fullfile(scriptDir, 'nsga2_outputs', 'platemo_paper_mutation_zdt_series');

problems = {
    'ZDT1', @ZDT1, 30;
    'ZDT2', @ZDT2, 30;
    'ZDT3', @ZDT3, 30;
    'ZDT4', @ZDT4, 10;
    'ZDT6', @ZDT6, 10;
};

if ~exist(outRoot, 'dir')
    mkdir(outRoot);
end

addpath(genpath(platemoRoot));

for p = 1 : size(problems,1)
    problemName = problems{p,1};
    problemFcn  = problems{p,2};
    D           = problems{p,3};
    outDir      = fullfile(outRoot, problemName);
    if ~exist(outDir, 'dir')
        mkdir(outDir);
    end

    fprintf('\n=== %s M=%d D=%d ===\n', problemName, M, D);
    lastObj = [];
    for run = 1 : Runs
        rng(run);
        runDir = fullfile(outDir, sprintf('run_%03d', run));
        if ~exist(runDir, 'dir')
            mkdir(runDir);
        end

        [~,Obj,~] = platemo( ...
            'algorithm', @NSGAII_PaperMutation, ...
            'problem', problemFcn, ...
            'N', N, ...
            'M', M, ...
            'D', D, ...
            'maxFE', maxFE, ...
            'run', run);

        objPath = fullfile(runDir, 'obj.csv');
        writematrix(Obj, objPath);
        lastObj = Obj;
        fprintf('%s run %03d: saved %s\n', problemName, run, objPath);
    end

    writematrix(lastObj, fullfile(outDir, sprintf('%s_last_run_obj.csv', problemName)));
end
