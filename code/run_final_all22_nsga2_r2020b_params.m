% Final all-22 NSGA-II reproducibility run.
%
% Priority rule:
% 1) Use paper settings when explicitly reported.
% 2) Use PlatEMO v2.9 native settings where the paper is silent.
% 3) Use fixed reproducibility settings only where both are silent.
%
% Runs 22 benchmark problems x 30 independent runs and writes comparison
% tables against paper Table 3 NSGA-II IGD values.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir, 'PlatEMO_v2.9.0', 'PlatEMO');
compatRoot = fullfile(scriptDir, 'platemo_v43_compat');
metricCompatRoot = fullfile(scriptDir, 'v290_metric_compat');

baseOut = fullfile(scriptDir, 'nsga2_outputs', 'final_all22_r2020b_v290_mcg_randomtie');
out = baseOut;
suffix = 1;
while exist(out, 'dir')
    suffix = suffix + 1;
    out = sprintf('%s_%02d', baseOut, suffix);
end
mkdir(out);

diary(fullfile(out, 'run.log'));
fprintf('MATLAB version: %s\n', version);
fprintf('MATLAB release: %s\n', version('-release'));
fprintf('Output workspace: %s\n', out);

restoredefaultpath;
if exist(metricCompatRoot, 'dir')
    addpath(metricCompatRoot);
end
addpath(genpath(platemoRoot));
addpath(compatRoot);
addpath(scriptDir);

problems = {
    'DTLZ1', @DTLZ1, 3,  7, 0.23828, 0.443;
    'DTLZ2', @DTLZ2, 3, 12, 0.054881, 0.000170;
    'DTLZ3', @DTLZ3, 3, 12, 13.357, 10.0;
    'DTLZ4', @DTLZ4, 3, 12, 0.40388, 0.313;
    'DTLZ5', @DTLZ5, 3, 12, 0.032473, 0.000641;
    'DTLZ6', @DTLZ6, 3, 12, 0.11635, 0.251;
    'DTLZ7', @DTLZ7, 3, 22, 0.17080, 0.121;
    'ZDT1',  @ZDT1,  2, 30, 0.14621, 0.0553;
    'ZDT2',  @ZDT2,  2, 30, 0.50813, 0.0879;
    'ZDT3',  @ZDT3,  2, 30, 0.17787, 0.0734;
    'ZDT4',  @ZDT4,  2, 10, 0.53146, 0.251;
    'ZDT6',  @ZDT6,  2, 10, 0.074290, 0.0171;
    'UF1',   @UF1,   2, 30, 0.31352, 0.0933;
    'UF2',   @UF2,   2, 30, 0.21196, 0.0676;
    'UF3',   @UF3,   2, 30, 0.33463, 0.0248;
    'UF4',   @UF4,   2, 30, 0.075733, 0.00384;
    'UF5',   @UF5,   2, 30, 0.68720, 0.169;
    'UF6',   @UF6,   2, 30, 0.40233, 0.0937;
    'UF7',   @UF7,   2, 30, 0.15936, 0.114;
    'UF8',   @UF8,   3, 30, 0.30495, 0.0551;
    'UF9',   @UF9,   3, 30, 0.47414, 0.0926;
    'UF10',  @UF10,  3, 30, 1.1774, 0.592
};

rows = {};
for p = 1:size(problems, 1)
    name = problems{p, 1};
    problemFcn = problems{p, 2};
    M = problems{p, 3};
    D = problems{p, 4};
    paperMean = problems{p, 5};
    paperStd = problems{p, 6};

    problemDir = fullfile(out, name);
    mkdir(problemDir);

    referenceGlobal = GLOBAL( ...
        '-algorithm', @NSGAII, ...
        '-problem', problemFcn, ...
        '-N', 100, ...
        '-M', M, ...
        '-D', D, ...
        '-evaluation', 10000, ...
        '-outputFcn', @(varargin)[] ...
    );
    PF = referenceGlobal.problem.PF(10000);

    igdValues = nan(30, 1);
    ndSizes = nan(30, 1);
    for run = 1:30
        RandStream.setGlobalStream(RandStream('mcg16807', 'Seed', run));
        Global = GLOBAL( ...
            '-algorithm', @NSGAII_RandomTie_v290, ...
            '-problem', problemFcn, ...
            '-N', 100, ...
            '-M', M, ...
            '-D', D, ...
            '-evaluation', 10000, ...
            '-run', run, ...
            '-outputFcn', @(varargin)[] ...
        );
        Global.Start();

        Population = Global.result{end, 2};
        Obj = Population.objs;
        Dec = Population.decs;
        feasible = all(Population.cons <= 0, 2);
        ObjFeasible = Obj(feasible, :);
        nd = NDSort(ObjFeasible, 1) == 1;
        ObjReported = ObjFeasible(nd, :);

        igdValues(run) = IGD(ObjReported, PF);
        ndSizes(run) = size(ObjReported, 1);

        runDir = fullfile(problemDir, sprintf('run_%03d', run));
        mkdir(runDir);
        writematrix(Obj, fullfile(runDir, 'obj_final_population.csv'));
        writematrix(Dec, fullfile(runDir, 'dec_final_population.csv'));
        writematrix(ObjReported, fullfile(runDir, 'obj_feasible_nd.csv'));
        writetable(table(run, igdValues(run), ndSizes(run), 'VariableNames', ...
            {'seed', 'igd', 'feasible_nd_size'}), fullfile(runDir, 'igd.csv'));

        fprintf('%s run %02d IGD %.12g ND %d\n', name, run, igdValues(run), ndSizes(run));
    end

    writetable(table((1:30)', igdValues, ndSizes, 'VariableNames', ...
        {'seed', 'igd', 'feasible_nd_size'}), fullfile(problemDir, 'igd_runs.csv'));

    meanIgd = mean(igdValues);
    stdIgd = std(igdValues);
    meanAbsDiff = abs(meanIgd - paperMean);
    meanRelDiff = meanAbsDiff / abs(paperMean) * 100;
    stdAbsDiff = abs(stdIgd - paperStd);
    stdRelDiff = stdAbsDiff / abs(paperStd) * 100;

    rows(end + 1, :) = { ...
        name, M, D, 100, 10000, 30, ...
        paperMean, paperStd, meanIgd, stdIgd, ...
        meanIgd - paperMean, meanAbsDiff, meanRelDiff, ...
        stdIgd - paperStd, stdAbsDiff, stdRelDiff, mean(ndSizes) ...
    }; %#ok<SAGROW>

    write_outputs(out, rows);
end

write_outputs(out, rows);
diary off;

function write_outputs(out, rows)
    T = cell2table(rows, 'VariableNames', summary_names());
    writetable(T, fullfile(out, 'comparison_table.csv'));

    familyRows = {};
    families = {'DTLZ', 'ZDT', 'UF'};
    for i = 1:numel(families)
        mask = startsWith(T.problem, families{i});
        familyRows(end + 1, :) = {families{i}, sum(mask), ...
            mean(T.mean_relative_diff_percent(mask)), ...
            median(T.mean_relative_diff_percent(mask))}; %#ok<AGROW>
    end
    familyRows(end + 1, :) = {'ALL', height(T), ...
        mean(T.mean_relative_diff_percent), ...
        median(T.mean_relative_diff_percent)}; %#ok<AGROW>
    S = cell2table(familyRows, 'VariableNames', ...
        {'family', 'problem_count', 'mean_relative_diff_percent', ...
         'median_relative_diff_percent'});
    writetable(S, fullfile(out, 'relative_diff_summary.csv'));
    writetable(S, fullfile(fileparts(out), 'latest_final_all22_relative_diff_summary.csv'));
    writetable(T, fullfile(fileparts(out), 'latest_final_all22_comparison_table.csv'));

    fid = fopen(fullfile(fileparts(out), 'latest_final_all22_workspace.txt'), 'w');
    fprintf(fid, '%s\n', out);
    fclose(fid);

    disp(T);
    disp(S);
end

function names = summary_names()
    names = { ...
        'problem', 'M', 'D', 'N', 'maxFE', 'runs', ...
        'paper_mean_igd', 'paper_std_igd', 'reproduced_mean_igd', ...
        'reproduced_std_igd', 'mean_signed_diff', 'mean_abs_diff', ...
        'mean_relative_diff_percent', 'std_signed_diff', 'std_abs_diff', ...
        'std_relative_diff_percent', 'mean_feasible_nd_size' ...
    };
end
