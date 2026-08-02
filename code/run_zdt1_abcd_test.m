% ZDT1 A/B/C/D reproduction checks for NSGA-II.
%
% A: maxFE=10000, PlatEMO built-in mutation semantics proM/D.
% B: maxFE=10000, paper-style per-variable mutation semantics proM.
% C/D are computed from B outputs using different IGD reference sizes.

clear; clc;

N = 100;
M = 2;
D = 30;
maxFE = 10000;
Runs = 30;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir, 'PlatEMO', 'PlatEMO');
outRoot = fullfile(scriptDir, 'nsga2_outputs', 'zdt1_abcd_test');

if ~exist(outRoot, 'dir')
    mkdir(outRoot);
end

addpath(genpath(platemoRoot));

settings = {
    'A_platemo_proM_over_D', @NSGAII;
    'B_paper_proM', @NSGAII_PaperMutation;
};

for s = 1 : size(settings,1)
    settingName = settings{s,1};
    algorithmFcn = settings{s,2};
    outDir = fullfile(outRoot, settingName);
    if ~exist(outDir, 'dir')
        mkdir(outDir);
    end

    fprintf('\n=== %s ===\n', settingName);
    for run = 1 : Runs
        rng(run);
        runDir = fullfile(outDir, sprintf('run_%03d', run));
        if ~exist(runDir, 'dir')
            mkdir(runDir);
        end

        [~,Obj,~] = platemo( ...
            'algorithm', algorithmFcn, ...
            'problem', @ZDT1, ...
            'N', N, ...
            'M', M, ...
            'D', D, ...
            'maxFE', maxFE, ...
            'run', run);

        writematrix(Obj, fullfile(runDir, 'obj.csv'));
        fprintf('%s run %03d saved\n', settingName, run);
    end
end
