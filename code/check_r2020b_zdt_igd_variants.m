% Recalculate IGD variants for the fresh R2020b ZDT run.
% Checks whether the discrepancy is caused by PF source or using all final
% population instead of the feasible non-dominated subset.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
workspaceFile = fullfile(scriptDir, 'nsga2_outputs', 'latest_r2020b_zdt_workspace.txt');
if exist(workspaceFile, 'file')
    out = strtrim(fileread(workspaceFile));
else
    out = fullfile(scriptDir, 'nsga2_outputs', 'platemo_v290_zdt_fresh_r2020b_20260616');
end

platemoRoot = fullfile(scriptDir, 'PlatEMO_v2.9.0', 'PlatEMO');
externalPfRoot = fullfile(scriptDir, 'zdt_reference_v43');

restoredefaultpath;
addpath(genpath(platemoRoot));
addpath(fullfile(scriptDir, 'platemo_v43_compat'));

problems = {
    'ZDT1', @ZDT1, 30, 0.14621;
    'ZDT2', @ZDT2, 30, 0.50813;
    'ZDT3', @ZDT3, 30, 0.17787;
    'ZDT4', @ZDT4, 10, 0.53146;
    'ZDT6', @ZDT6, 10, 0.07429
};

rows = {};
for p = 1:size(problems, 1)
    name = problems{p, 1};
    problemFcn = problems{p, 2};
    D = problems{p, 3};
    paperMean = problems{p, 4};

    Global = GLOBAL('-problem', problemFcn, '-M', 2, '-D', D, '-N', 100, '-evaluation', 10000, '-outputFcn', @(varargin)[]);
    builtInPF = Global.problem.PF(10000);
    externalPF = readmatrix(fullfile(externalPfRoot, [name, '.csv']));

    allExternal = nan(30, 1);
    ndExternal = nan(30, 1);
    allBuiltIn = nan(30, 1);
    ndBuiltIn = nan(30, 1);
    ndCount = nan(30, 1);

    for run = 1:30
        objFile = fullfile(out, name, sprintf('run_%03d', run), 'obj.csv');
        Obj = readmatrix(objFile);
        nd = NDSort(Obj, 1) == 1;
        ndCount(run) = sum(nd);
        allExternal(run) = local_igd(Obj, externalPF);
        ndExternal(run) = local_igd(Obj(nd, :), externalPF);
        allBuiltIn(run) = local_igd(Obj, builtInPF);
        ndBuiltIn(run) = local_igd(Obj(nd, :), builtInPF);
    end

    rows(end + 1, :) = { ...
        name, paperMean, mean(ndCount), ...
        mean(allExternal), std(allExternal), abs(mean(allExternal) - paperMean), ...
        mean(ndExternal), std(ndExternal), abs(mean(ndExternal) - paperMean), ...
        mean(allBuiltIn), std(allBuiltIn), abs(mean(allBuiltIn) - paperMean), ...
        mean(ndBuiltIn), std(ndBuiltIn), abs(mean(ndBuiltIn) - paperMean) ...
    }; %#ok<SAGROW>
end

T = cell2table(rows, 'VariableNames', { ...
    'problem', 'paper_mean', 'mean_nd_count', ...
    'all_external_mean', 'all_external_std', 'all_external_abs_error', ...
    'nd_external_mean', 'nd_external_std', 'nd_external_abs_error', ...
    'all_builtin_mean', 'all_builtin_std', 'all_builtin_abs_error', ...
    'nd_builtin_mean', 'nd_builtin_std', 'nd_builtin_abs_error' ...
});

writetable(T, fullfile(out, 'igd_variant_check.csv'));
disp(T);

function value = local_igd(approximation, reference)
    distances = inf(size(reference, 1), 1);
    for i = 1:size(approximation, 1)
        diff = reference - approximation(i, :);
        distances = min(distances, sqrt(sum(diff .* diff, 2)));
    end
    value = mean(distances);
end
