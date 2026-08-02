% Seed-block sensitivity under the final selected reproduction settings.
%
% Final settings:
% R2020b, PlatEMO v2.9, NSGAII_RandomTie_v290, mcg16807, N=100,
% maxFE=10000, feasible nondominated final set, PlatEMO native IGD and PF.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir, 'PlatEMO_v2.9.0', 'PlatEMO');
compatRoot = fullfile(scriptDir, 'platemo_v43_compat');
metricCompatRoot = fullfile(scriptDir, 'v290_metric_compat');
out = fullfile(scriptDir, 'nsga2_outputs', 'seed_blocks_final_params_all22');
if ~exist(out, 'dir'); mkdir(out); end

diary(fullfile(out, 'run.log'));
fprintf('MATLAB version: %s\n', version);
fprintf('MATLAB release: %s\n', version('-release'));
fprintf('Output workspace: %s\n', out);

restoredefaultpath;
if exist(metricCompatRoot, 'dir'); addpath(metricCompatRoot); end
addpath(genpath(platemoRoot));
addpath(compatRoot);
addpath(scriptDir);

problems = {
    'DTLZ1', @DTLZ1, 3,  7, 0.23828;
    'DTLZ2', @DTLZ2, 3, 12, 0.054881;
    'DTLZ3', @DTLZ3, 3, 12, 13.357;
    'DTLZ4', @DTLZ4, 3, 12, 0.40388;
    'DTLZ5', @DTLZ5, 3, 12, 0.032473;
    'DTLZ6', @DTLZ6, 3, 12, 0.11635;
    'DTLZ7', @DTLZ7, 3, 22, 0.17080;
    'ZDT1',  @ZDT1,  2, 30, 0.14621;
    'ZDT2',  @ZDT2,  2, 30, 0.50813;
    'ZDT3',  @ZDT3,  2, 30, 0.17787;
    'ZDT4',  @ZDT4,  2, 10, 0.53146;
    'ZDT6',  @ZDT6,  2, 10, 0.074290;
    'UF1',   @UF1,   2, 30, 0.31352;
    'UF2',   @UF2,   2, 30, 0.21196;
    'UF3',   @UF3,   2, 30, 0.33463;
    'UF4',   @UF4,   2, 30, 0.075733;
    'UF5',   @UF5,   2, 30, 0.68720;
    'UF6',   @UF6,   2, 30, 0.40233;
    'UF7',   @UF7,   2, 30, 0.15936;
    'UF8',   @UF8,   3, 30, 0.30495;
    'UF9',   @UF9,   3, 30, 0.47414;
    'UF10',  @UF10,  3, 30, 1.1774
};

blocks = {
    'S01_seed_1_30',       1:30;
    'S02_seed_31_60',     31:60;
    'S03_seed_101_130',  101:130;
    'S04_seed_1001_1030',1001:1030
};

summaryRows = {};
detailRows = {};
for p = 1:size(problems, 1)
    name = problems{p, 1};
    problemFcn = problems{p, 2};
    M = problems{p, 3};
    D = problems{p, 4};
    paperMean = problems{p, 5};

    referenceGlobal = GLOBAL( ...
        '-algorithm', @NSGAII, '-problem', problemFcn, '-N', 100, ...
        '-M', M, '-D', D, '-evaluation', 10000, '-outputFcn', @(varargin)[] ...
    );
    PF = referenceGlobal.problem.PF(10000);

    for b = 1:size(blocks, 1)
        blockName = blocks{b, 1};
        seeds = blocks{b, 2};
        blockDir = fullfile(out, blockName, name);
        if ~exist(blockDir, 'dir'); mkdir(blockDir); end

        values = nan(numel(seeds), 1);
        ndSizes = nan(numel(seeds), 1);
        for r = 1:numel(seeds)
            seed = seeds(r);
            resultFile = fullfile(blockDir, sprintf('seed_%04d.csv', seed));
            if exist(resultFile, 'file')
                old = readtable(resultFile);
                values(r) = old.igd(1);
                ndSizes(r) = old.feasible_nd_size(1);
                continue;
            end

            RandStream.setGlobalStream(RandStream('mcg16807', 'Seed', seed));
            Global = GLOBAL( ...
                '-algorithm', @NSGAII_RandomTie_v290, ...
                '-problem', problemFcn, '-N', 100, '-M', M, '-D', D, ...
                '-evaluation', 10000, '-run', seed, '-outputFcn', @(varargin)[] ...
            );
            Global.Start();
            Population = Global.result{end, 2};
            Obj = Population.objs;
            feasible = all(Population.cons <= 0, 2);
            Obj = Obj(feasible, :);
            Obj = Obj(NDSort(Obj, 1) == 1, :);

            values(r) = IGD(Obj, PF);
            ndSizes(r) = size(Obj, 1);
            writetable(table(seed, values(r), ndSizes(r), ...
                'VariableNames', {'seed', 'igd', 'feasible_nd_size'}), resultFile);
            fprintf('%s %s seed %d IGD %.12g ND %d\n', blockName, name, seed, values(r), ndSizes(r));
        end

        meanIgd = mean(values);
        stdIgd = std(values);
        relDiff = abs(meanIgd - paperMean) / abs(paperMean) * 100;
        cv = stdIgd / meanIgd * 100;
        summaryRows(end + 1, :) = {blockName, name, M, D, 100, 10000, 30, ...
            seeds(1), seeds(end), paperMean, meanIgd, stdIgd, cv, ...
            meanIgd - paperMean, abs(meanIgd - paperMean), relDiff, mean(ndSizes)}; %#ok<SAGROW>
        for r = 1:numel(seeds)
            detailRows(end + 1, :) = {blockName, name, M, D, seeds(r), values(r), ndSizes(r)}; %#ok<SAGROW>
        end
        write_outputs(out, summaryRows, detailRows);
    end
end

write_outputs(out, summaryRows, detailRows);
diary off;

function write_outputs(out, summaryRows, detailRows)
    summary = cell2table(summaryRows, 'VariableNames', summary_names());
    detail = cell2table(detailRows, 'VariableNames', detail_names());
    writetable(summary, fullfile(out, 'summary.csv'));
    writetable(detail, fullfile(out, 'per_seed_igd.csv'));

    blockRanking = groupsummary(summary, 'seed_block', {'mean', 'median'}, 'relative_diff_percent');
    blockRanking = sortrows(blockRanking, 'mean_relative_diff_percent');
    writetable(blockRanking, fullfile(out, 'seed_block_paper_closeness_ranking.csv'));

    problemRows = {};
    problemNames = unique(summary.problem, 'stable');
    for i = 1:numel(problemNames)
        mask = strcmp(summary.problem, problemNames{i});
        rows = summary(mask, :);
        grandMean = mean(rows.mean_igd);
        rangeMeans = max(rows.mean_igd) - min(rows.mean_igd);
        [bestRel, bestIdx] = min(rows.relative_diff_percent);
        problemRows(end + 1, :) = {problemNames{i}, rows.M(1), rows.D(1), ...
            rows.paper_igd(1), grandMean, rangeMeans, rangeMeans / grandMean * 100, ...
            rows.seed_block{bestIdx}, bestRel}; %#ok<AGROW>
    end
    effect = cell2table(problemRows, 'VariableNames', ...
        {'problem', 'M', 'D', 'paper_igd', 'grand_mean_igd', ...
         'range_of_block_means', 'block_mean_range_percent', ...
         'closest_seed_block', 'closest_relative_diff_percent'});
    effect = sortrows(effect, 'block_mean_range_percent', 'descend');
    writetable(effect, fullfile(out, 'seed_effect_by_problem.csv'));
end

function names = summary_names()
    names = {'seed_block', 'problem', 'M', 'D', 'N', 'maxFE', 'runs', ...
        'first_seed', 'last_seed', 'paper_igd', 'mean_igd', 'sample_std', ...
        'run_cv_percent', 'signed_diff', 'abs_diff', ...
        'relative_diff_percent', 'mean_feasible_nd_size'};
end

function names = detail_names()
    names = {'seed_block', 'problem', 'M', 'D', 'seed', 'igd', 'feasible_nd_size'};
end
