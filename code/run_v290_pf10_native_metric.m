% PF10: reproduce PlatEMO v2.9 native IGD metric behavior.
%
% PF10a: problem.PF(10000) + full final population + native IGD.m
% PF10b: problem.PF(10000) + feasible/non-dominated final population
%        + native IGD.m, matching GLOBAL.Metric.

clear; clc;

root = fileparts(mfilename('fullpath'));
outputRoot = fullfile(root,'nsga2_outputs','v290_pf10_native_metric');
if ~exist(outputRoot,'dir'); mkdir(outputRoot); end

restoredefaultpath;
addpath(fullfile(root,'v290_metric_compat'));
addpath(genpath(fullfile(root,'PlatEMO_v2.9.0','PlatEMO')));

problems = {
    'DTLZ1', 3,  7, 0.23828, 'platemo_v290_dtlz1_7_seeded_r2020b';
    'DTLZ2', 3, 12, 0.054881,'platemo_v290_dtlz1_7_seeded_r2020b';
    'DTLZ3', 3, 12, 13.357,  'platemo_v290_dtlz1_7_seeded_r2020b';
    'DTLZ4', 3, 12, 0.40388, 'platemo_v290_dtlz1_7_seeded_r2020b';
    'DTLZ5', 3, 12, 0.032473,'platemo_v290_dtlz1_7_seeded_r2020b';
    'DTLZ6', 3, 12, 0.11635, 'platemo_v290_dtlz1_7_seeded_r2020b';
    'DTLZ7', 3, 22, 0.1708,  'platemo_v290_dtlz1_7_seeded_r2020b';
    'ZDT1',  2, 30, 0.14621, 'platemo_v290_zdt_seeded_r2020b';
    'ZDT2',  2, 30, 0.50813, 'platemo_v290_zdt_seeded_r2020b';
    'ZDT3',  2, 30, 0.17787, 'platemo_v290_zdt_seeded_r2020b';
    'ZDT4',  2, 10, 0.53146, 'platemo_v290_zdt_seeded_r2020b';
    'ZDT6',  2, 10, 0.07429, 'platemo_v290_zdt_seeded_r2020b';
    'UF1',   2, 30, 0.31352, 'platemo_v290_uf1_5_seeded_r2020b';
    'UF2',   2, 30, 0.21196, 'platemo_v290_uf1_5_seeded_r2020b';
    'UF3',   2, 30, 0.33463, 'platemo_v290_uf1_5_seeded_r2020b';
    'UF4',   2, 30, 0.12713, 'platemo_v290_uf1_5_seeded_r2020b';
    'UF5',   2, 30, 1.3074,  'platemo_v290_uf1_5_seeded_r2020b';
    'UF6',   2, 30, 0.59480, 'platemo_v290_uf6_10_seeded_r2020b';
    'UF7',   2, 30, 0.43887, 'platemo_v290_uf6_10_seeded_r2020b';
    'UF8',   3, 30, 0.58545, 'platemo_v290_uf6_10_seeded_r2020b';
    'UF9',   3, 30, 0.52501, 'platemo_v290_uf6_10_seeded_r2020b';
    'UF10',  3, 30, 0.74415, 'platemo_v290_uf6_10_seeded_r2020b';
};

variants = {'PF10a_native_full','PF10b_GLOBAL_Metric_ND'};
detailRows = cell(size(problems,1)*30*2,9);
summaryRows = cell(size(problems,1)*2,15);
detailIndex = 0;
summaryIndex = 0;

for p = 1:size(problems,1)
    name = problems{p,1}; M = problems{p,2}; D = problems{p,3};
    paperIGD = problems{p,4}; batch = problems{p,5};
    problemFcn = str2func(name);
    Global = GLOBAL('-problem',problemFcn,'-N',100,'-M',M,'-D',D, ...
        '-evaluation',10000,'-outputFcn',@(varargin)[]);
    PF = Global.problem.PF(10000);

    values = nan(30,2);
    ndSizes = nan(30,1);
    for run = 1:30
        Obj = readmatrix(fullfile(root,'nsga2_outputs',batch,name, ...
            sprintf('run_%03d',run),'obj.csv'));

        values(run,1) = IGD(Obj,PF);
        nonDominated = NDSort(Obj,1)==1;
        NDObj = Obj(nonDominated,:);
        ndSizes(run) = size(NDObj,1);
        values(run,2) = IGD(NDObj,PF);

        for variant = 1:2
            detailIndex = detailIndex+1;
            detailRows(detailIndex,:) = {variants{variant},name,M,D,run, ...
                size(PF,1),size(Obj,1),ndSizes(run),values(run,variant)};
        end
    end

    for variant = 1:2
        meanIGD = mean(values(:,variant));
        sampleStd = std(values(:,variant));
        signedDiff = meanIGD-paperIGD;
        summaryIndex = summaryIndex+1;
        summaryRows(summaryIndex,:) = {variants{variant},name,M,D,30, ...
            size(PF,1),mean(ndSizes),paperIGD,meanIGD,sampleStd,signedDiff, ...
            abs(signedDiff),abs(signedDiff)/paperIGD*100, ...
            sprintf('%.4e (%.4e)',meanIGD,sampleStd), ...
            max(abs(values(:,1)-values(:,2)))};
    end
    fprintf('%s: full %.12g, native metric ND %.12g, mean ND size %.2f\n', ...
        name,mean(values(:,1)),mean(values(:,2)),mean(ndSizes));
end

detail = cell2table(detailRows,'VariableNames', ...
    {'variant','problem','M','D','run','pf_points','full_size','nd_size','igd'});
summary = cell2table(summaryRows,'VariableNames', ...
    {'variant','problem','M','D','runs','pf_points','mean_nd_size', ...
     'paper_igd','mean_igd','sample_std','signed_diff','abs_diff', ...
     'relative_diff_percent','mean_std','max_run_full_nd_abs_diff'});

writetable(detail,fullfile(outputRoot,'per_run_igd.csv'));
writetable(summary,fullfile(outputRoot,'summary.csv'));

ranking = groupsummary(summary,'variant',{'mean','median'}, ...
    'relative_diff_percent');
ranking = sortrows(ranking,'mean_relative_diff_percent');
writetable(ranking,fullfile(outputRoot,'ranking.csv'));

old = readtable(fullfile(root,'nsga2_outputs','v290_pf_sources_t1_t8','summary.csv'));
T1 = old(strcmp(old.source,'T1_v290_PF'), ...
    {'problem','mean_igd','sample_std','relative_diff_percent'});
T1.Properties.VariableNames(2:end) = ...
    {'T1_mean_igd','T1_sample_std','T1_relative_diff_percent'};
PF10a = summary(strcmp(summary.variant,'PF10a_native_full'), ...
    {'problem','mean_igd','sample_std','relative_diff_percent'});
PF10a.Properties.VariableNames(2:end) = ...
    {'PF10a_mean_igd','PF10a_sample_std','PF10a_relative_diff_percent'};
PF10b = summary(strcmp(summary.variant,'PF10b_GLOBAL_Metric_ND'), ...
    {'problem','mean_igd','sample_std','relative_diff_percent','mean_nd_size'});
PF10b.Properties.VariableNames(2:end) = ...
    {'PF10b_mean_igd','PF10b_sample_std','PF10b_relative_diff_percent','mean_nd_size'};
comparison = join(join(T1,PF10a,'Keys','problem'),PF10b,'Keys','problem');
comparison.T1_PF10a_mean_abs_diff = ...
    abs(comparison.T1_mean_igd-comparison.PF10a_mean_igd);
comparison.PF10b_minus_PF10a = ...
    comparison.PF10b_mean_igd-comparison.PF10a_mean_igd;
writetable(comparison,fullfile(outputRoot,'comparison_with_T1.csv'));

disp(summary);
disp(ranking);
disp(comparison);
