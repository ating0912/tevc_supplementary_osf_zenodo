% Fresh R2020b workspace rerun:
% PlatEMO v2.9.0 NSGA-II on ZDT1/ZDT2/ZDT3/ZDT4/ZDT6.
% Settings follow the paper table setup:
% N = 100, maxFE = 10000, runs = 30, SBX + polynomial mutation.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir, 'PlatEMO_v2.9.0', 'PlatEMO');
pfRoot = fullfile(scriptDir, 'zdt_reference_v43');

baseOut = fullfile(scriptDir, 'nsga2_outputs', 'platemo_v290_zdt_fresh_r2020b_20260616');
out = baseOut;
suffix = 1;
while exist(out, 'dir')
    suffix = suffix + 1;
    out = sprintf('%s_%02d', baseOut, suffix);
end
mkdir(out);

diary(fullfile(out, 'matlab_r2020b_run.log'));
fprintf('MATLAB version: %s\n', version);
fprintf('MATLAB release: %s\n', version('-release'));
fprintf('Output workspace: %s\n', out);

restoredefaultpath;
addpath(genpath(platemoRoot));
addpath(fullfile(scriptDir, 'platemo_v43_compat'));

problems = {
    'ZDT1', @ZDT1, 30, 0.14621, 0.0553;
    'ZDT2', @ZDT2, 30, 0.50813, 0.0879;
    'ZDT3', @ZDT3, 30, 0.17787, 0.0734;
    'ZDT4', @ZDT4, 10, 0.53146, 0.2510;
    'ZDT6', @ZDT6, 10, 0.07429, 0.0171
};

rows = {};
for p = 1:size(problems, 1)
    name = problems{p, 1};
    problemFcn = problems{p, 2};
    D = problems{p, 3};
    paperMean = problems{p, 4};
    paperStd = problems{p, 5};

    problemDir = fullfile(out, name);
    mkdir(problemDir);
    PF = readmatrix(fullfile(pfRoot, [name, '.csv']));
    igdValues = nan(30, 1);

    fprintf('\n=== %s ===\n', name);
    for run = 1:30
        runDir = fullfile(problemDir, sprintf('run_%03d', run));
        mkdir(runDir);

        rng(run, 'twister');
        Global = GLOBAL( ...
            '-algorithm', @NSGAII, ...
            '-problem', problemFcn, ...
            '-N', 100, ...
            '-M', 2, ...
            '-D', D, ...
            '-evaluation', 10000, ...
            '-run', run, ...
            '-outputFcn', @(varargin)[] ...
        );
        Global.Start();

        Pop = Global.result{end, 2};
        Obj = Pop.objs;
        Dec = Pop.decs;
        igdValues(run) = local_igd(Obj, PF);

        writematrix(Obj, fullfile(runDir, 'obj.csv'));
        writematrix(Dec, fullfile(runDir, 'dec.csv'));
        writetable(table(run, igdValues(run), 'VariableNames', {'seed', 'igd'}), fullfile(runDir, 'igd.csv'));
        fprintf('%s run %02d IGD = %.12e\n', name, run, igdValues(run));
    end

    writetable(table((1:30)', igdValues, 'VariableNames', {'seed', 'igd'}), fullfile(problemDir, 'igd_runs.csv'));

    meanIgd = mean(igdValues);
    stdIgd = std(igdValues);
    meanAbsError = abs(meanIgd - paperMean);
    stdAbsError = abs(stdIgd - paperStd);
    meanRelError = meanAbsError / abs(paperMean) * 100;
    stdRelError = stdAbsError / abs(paperStd) * 100;

    rows(end + 1, :) = { ...
        name, 2, D, 100, 10000, 30, size(PF, 1), ...
        paperMean, paperStd, meanIgd, stdIgd, ...
        meanIgd - paperMean, meanAbsError, meanRelError, ...
        stdIgd - paperStd, stdAbsError, stdRelError ...
    }; %#ok<SAGROW>
end

summary = cell2table(rows, 'VariableNames', { ...
    'problem', 'M', 'D', 'N', 'maxFE', 'runs', 'pf_points', ...
    'paper_mean_igd', 'paper_std_igd', 'mean_igd', 'std_igd', ...
    'mean_signed_error', 'mean_abs_error', 'mean_relative_error_percent', ...
    'std_signed_error', 'std_abs_error', 'std_relative_error_percent' ...
});
writetable(summary, fullfile(out, 'summary.csv'));
writetable(summary, fullfile(scriptDir, 'nsga2_outputs', 'latest_r2020b_zdt_summary.csv'));

fid = fopen(fullfile(scriptDir, 'nsga2_outputs', 'latest_r2020b_zdt_workspace.txt'), 'w');
fprintf(fid, '%s\n', out);
fclose(fid);

disp(summary);
diary off;

function value = local_igd(approximation, reference)
    distances = inf(size(reference, 1), 1);
    for i = 1:size(approximation, 1)
        diff = reference - approximation(i, :);
        distances = min(distances, sqrt(sum(diff .* diff, 2)));
    end
    value = mean(distances);
end
