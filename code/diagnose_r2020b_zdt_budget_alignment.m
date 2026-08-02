% Quick budget diagnostic: check whether paper Table 3 NSGA-II values look
% closer to a smaller FE budget than 10000.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir, 'PlatEMO_v2.9.0', 'PlatEMO');
restoredefaultpath;
addpath(genpath(platemoRoot));
addpath(fullfile(scriptDir, 'platemo_v43_compat'));

out = fullfile(scriptDir, 'nsga2_outputs', 'r2020b_zdt_budget_alignment');
if ~exist(out, 'dir'); mkdir(out); end

problems = {
    'ZDT1', @ZDT1, 30, 0.14621;
    'ZDT2', @ZDT2, 30, 0.50813;
    'ZDT3', @ZDT3, 30, 0.17787;
    'ZDT4', @ZDT4, 10, 0.53146;
    'ZDT6', @ZDT6, 10, 0.07429
};
budgets = [500, 1000, 2000, 5000, 10000];

rows = {};
for p = 1:size(problems, 1)
    name = problems{p, 1};
    problemFcn = problems{p, 2};
    D = problems{p, 3};
    paperMean = problems{p, 4};

    refGlobal = GLOBAL('-problem', problemFcn, '-M', 2, '-D', D, '-N', 100, '-evaluation', 10000, '-outputFcn', @(varargin)[]);
    PF = refGlobal.problem.PF(10000);

    for b = 1:numel(budgets)
        maxFE = budgets(b);
        values = nan(30, 1);
        for run = 1:30
            rng(run, 'twister');
            Global = GLOBAL( ...
                '-algorithm', @NSGAII, ...
                '-problem', problemFcn, ...
                '-N', 100, ...
                '-M', 2, ...
                '-D', D, ...
                '-evaluation', maxFE, ...
                '-run', run, ...
                '-outputFcn', @(varargin)[] ...
            );
            Global.Start();
            Obj = Global.result{end, 2}.objs;
            Obj = Obj(NDSort(Obj, 1) == 1, :);
            values(run) = local_igd(Obj, PF);
        end
        rows(end + 1, :) = {name, maxFE, paperMean, mean(values), std(values), abs(mean(values) - paperMean)}; %#ok<SAGROW>
        fprintf('%s FE=%d mean=%.6e std=%.6e paper=%.6e absdiff=%.6e\n', name, maxFE, mean(values), std(values), paperMean, abs(mean(values)-paperMean));
    end
end

T = cell2table(rows, 'VariableNames', {'problem', 'maxFE', 'paper_mean', 'mean_igd', 'std_igd', 'abs_error'});
writetable(T, fullfile(out, 'budget_alignment.csv'));
disp(T);

function value = local_igd(approximation, reference)
    distances = inf(size(reference, 1), 1);
    for i = 1:size(approximation, 1)
        diff = reference - approximation(i, :);
        distances = min(distances, sqrt(sum(diff .* diff, 2)));
    end
    value = mean(distances);
end
