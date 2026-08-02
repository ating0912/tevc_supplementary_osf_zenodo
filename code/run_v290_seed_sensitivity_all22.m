% Test random-seed sensitivity under the closest paper-reproduction setup.
%
% Fixed conditions:
%   PlatEMO v2.9 NSGA-II, N=100, maxFE=10000
%   SBX proC=1 etaC=20
%   polynomial mutation proM=1 (effective probability 1/D), etaM=20
%   built-in PF(10000), feasible nondominated final solutions, native IGD.m
%
% Seed blocks:
%   S01:   1:30
%   S02:  31:60
%   S03: 101:130
%   S04: 1001:1030

clear; clc;

root = fileparts(mfilename('fullpath'));
outputRoot = fullfile(root,'nsga2_outputs','v290_seed_sensitivity_all22_rerun2');
if ~exist(outputRoot,'dir'); mkdir(outputRoot); end

restoredefaultpath;
addpath(fullfile(root,'v290_metric_compat'));
addpath(genpath(fullfile(root,'PlatEMO_v2.9.0','PlatEMO')));
addpath(fullfile(root,'platemo_v43_compat'));

problems = {
    'ZDT1', @ZDT1, 2,30,0.14621,'platemo_v290_zdt_seeded_r2020b';
    'ZDT2', @ZDT2, 2,30,0.50813,'platemo_v290_zdt_seeded_r2020b';
    'ZDT3', @ZDT3, 2,30,0.17787,'platemo_v290_zdt_seeded_r2020b';
    'ZDT4', @ZDT4, 2,10,0.53146,'platemo_v290_zdt_seeded_r2020b';
    'ZDT6', @ZDT6, 2,10,0.07429,'platemo_v290_zdt_seeded_r2020b';
    'DTLZ1',@DTLZ1,3, 7,0.23828,'platemo_v290_dtlz1_7_seeded_r2020b';
    'DTLZ2',@DTLZ2,3,12,0.054881,'platemo_v290_dtlz1_7_seeded_r2020b';
    'DTLZ3',@DTLZ3,3,12,13.357, 'platemo_v290_dtlz1_7_seeded_r2020b';
    'DTLZ4',@DTLZ4,3,12,0.40388,'platemo_v290_dtlz1_7_seeded_r2020b';
    'DTLZ5',@DTLZ5,3,12,0.032473,'platemo_v290_dtlz1_7_seeded_r2020b';
    'DTLZ6',@DTLZ6,3,12,0.11635, 'platemo_v290_dtlz1_7_seeded_r2020b';
    'DTLZ7',@DTLZ7,3,22,0.1708,  'platemo_v290_dtlz1_7_seeded_r2020b';
    'UF1',  @UF1,  2,30,0.31352,'platemo_v290_uf1_5_seeded_r2020b';
    'UF2',  @UF2,  2,30,0.21196,'platemo_v290_uf1_5_seeded_r2020b';
    'UF3',  @UF3,  2,30,0.33463,'platemo_v290_uf1_5_seeded_r2020b';
    'UF4',  @UF4,  2,30,0.12713,'platemo_v290_uf1_5_seeded_r2020b';
    'UF5',  @UF5,  2,30,1.3074, 'platemo_v290_uf1_5_seeded_r2020b';
    'UF6',  @UF6,  2,30,0.5948, 'platemo_v290_uf6_10_seeded_r2020b';
    'UF7',  @UF7,  2,30,0.43887,'platemo_v290_uf6_10_seeded_r2020b';
    'UF8',  @UF8,  3,30,0.58545,'platemo_v290_uf6_10_seeded_r2020b';
    'UF9',  @UF9,  3,30,0.52501,'platemo_v290_uf6_10_seeded_r2020b';
    'UF10', @UF10, 3,30,0.74415,'platemo_v290_uf6_10_seeded_r2020b';
};

blocks = {
    'S01_seed_1_30',       1:30;
    'S02_seed_31_60',     31:60;
    'S03_seed_101_130',  101:130;
    'S04_seed_1001_1030',1001:1030;
};

detailRows = {};
summaryRows = {};

for p = 1:size(problems,1)
    name = problems{p,1};
    problemFcn = problems{p,2};
    M = problems{p,3};
    D = problems{p,4};
    paperIGD = problems{p,5};
    baselineBatch = problems{p,6};

    referenceGlobal = GLOBAL('-algorithm',@NSGAII,'-problem',problemFcn, ...
        '-N',100,'-M',M,'-D',D,'-evaluation',10000, ...
        '-outputFcn',@(varargin)[]);
    PF = referenceGlobal.problem.PF(10000);

    problemMeans = nan(size(blocks,1),1);
    problemStds = nan(size(blocks,1),1);

    for b = 1:size(blocks,1)
        blockName = blocks{b,1};
        seeds = blocks{b,2};
        blockDir = fullfile(outputRoot,blockName,name);
        if ~exist(blockDir,'dir'); mkdir(blockDir); end
        values = nan(numel(seeds),1);

        for r = 1:numel(seeds)
            seed = seeds(r);
            runDir = fullfile(blockDir,sprintf('seed_%04d',seed));
            resultFile = fullfile(runDir,'igd.csv');

            if exist(resultFile,'file')
                old = readtable(resultFile);
                values(r) = old.igd(1);
                continue;
            end
            if ~exist(runDir,'dir'); mkdir(runDir); end

            rng(seed,'twister');
            Global = GLOBAL('-algorithm',@NSGAII,'-problem',problemFcn, ...
                '-N',100,'-M',M,'-D',D,'-evaluation',10000, ...
                '-run',seed,'-outputFcn',@(varargin)[]);
            Global.Start();
            Population = Global.result{end,2};
            Obj = Population.objs;
            Dec = Population.decs;
            value = nativeMetricFromObjectives(Obj,PF);
            writematrix(Obj,fullfile(runDir,'obj.csv'));
            writematrix(Dec,fullfile(runDir,'dec.csv'));
            source = "new_run";

            values(r) = value;
            writetable(table(seed,value,source,'VariableNames', ...
                {'seed','igd','source'}),resultFile);
            fprintf('%s %s seed=%d IGD=%.12g\n',blockName,name,seed,value);
        end

        problemMeans(b) = mean(values);
        problemStds(b) = std(values);
        ci = meanCI95(values);
        relDiff = abs(problemMeans(b)-paperIGD)/paperIGD*100;
        writetable(table(seeds(:),values,'VariableNames',{'seed','igd'}), ...
            fullfile(blockDir,'igd_runs.csv'));

        summaryRows(end+1,:) = {blockName,name,M,D,100,10000,numel(seeds), ...
            seeds(1),seeds(end),paperIGD,problemMeans(b),problemStds(b), ...
            ci(1),ci(2),problemStds(b)/problemMeans(b)*100, ...
            problemMeans(b)-paperIGD,abs(problemMeans(b)-paperIGD),relDiff}; %#ok<SAGROW>
        for r = 1:numel(seeds)
            detailRows(end+1,:) = {blockName,name,M,D,seeds(r),values(r)}; %#ok<SAGROW>
        end
        writePartial(outputRoot,summaryRows,detailRows);
    end

    fprintf('%s seed-block mean range %.12g (%.3f%% of grand mean)\n', ...
        name,max(problemMeans)-min(problemMeans), ...
        (max(problemMeans)-min(problemMeans))/mean(problemMeans)*100);
end

summary = cell2table(summaryRows,'VariableNames',summaryNames());
detail = cell2table(detailRows,'VariableNames',detailNames());
writetable(summary,fullfile(outputRoot,'summary.csv'));
writetable(detail,fullfile(outputRoot,'per_seed_igd.csv'));

effectRows = {};
problemNames = unique(summary.problem,'stable');
for p = 1:numel(problemNames)
    name = problemNames{p};
    rows = summary(strcmp(summary.problem,name),:);
    [bestDiff,bestIndex] = min(rows.relative_diff_percent);
    meanRange = max(rows.mean_igd)-min(rows.mean_igd);
    grandMean = mean(rows.mean_igd);
    pooledStd = std(detail.igd(strcmp(detail.problem,name)));
    betweenStd = std(rows.mean_igd);
    baseline = rows.mean_igd(strcmp(rows.seed_block,'S01_seed_1_30'));
    maxShiftFromBaseline = max(abs(rows.mean_igd-baseline));
    effectRows(end+1,:) = {name,rows.M(1),rows.D(1),rows.paper_igd(1), ...
        grandMean,pooledStd,betweenStd,meanRange,meanRange/grandMean*100, ...
        maxShiftFromBaseline,maxShiftFromBaseline/baseline*100, ...
        rows.seed_block{bestIndex},bestDiff}; %#ok<SAGROW>
end

effect = cell2table(effectRows,'VariableNames', ...
    {'problem','M','D','paper_igd','grand_mean_igd','pooled_run_std', ...
     'std_of_block_means','range_of_block_means','block_mean_range_percent', ...
     'max_abs_shift_from_seed_1_30','max_shift_from_seed_1_30_percent', ...
     'closest_seed_block','closest_relative_diff_percent'});
effect = sortrows(effect,'block_mean_range_percent','descend');
writetable(effect,fullfile(outputRoot,'seed_effect_by_problem.csv'));

ranking = groupsummary(summary,'seed_block',{'mean','median'}, ...
    'relative_diff_percent');
ranking = sortrows(ranking,'mean_relative_diff_percent');
writetable(ranking,fullfile(outputRoot,'seed_block_paper_closeness_ranking.csv'));

disp(effect);
disp(ranking);

function value = nativeMetricFromObjectives(Obj,PF)
    nonDominated = NDSort(Obj,1)==1;
    value = IGD(Obj(nonDominated,:),PF);
end

function ci = meanCI95(values)
    n = numel(values);
    % t(0.975,29), since every seed block contains exactly 30 runs.
    halfWidth = 2.045229642132703*std(values)/sqrt(n);
    ci = [mean(values)-halfWidth,mean(values)+halfWidth];
end

function writePartial(outputRoot,summaryRows,detailRows)
    summary = cell2table(summaryRows,'VariableNames',summaryNames());
    detail = cell2table(detailRows,'VariableNames',detailNames());
    writetable(summary,fullfile(outputRoot,'summary_partial.csv'));
    writetable(detail,fullfile(outputRoot,'per_seed_igd_partial.csv'));
end

function names = summaryNames()
    names = {'seed_block','problem','M','D','N','maxFE','runs', ...
        'first_seed','last_seed','paper_igd','mean_igd','sample_std', ...
        'mean_ci95_low','mean_ci95_high','run_cv_percent','signed_diff', ...
        'abs_diff','relative_diff_percent'};
end

function names = detailNames()
    names = {'seed_block','problem','M','D','seed','igd'};
end
