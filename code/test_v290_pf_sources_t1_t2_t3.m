% Recalculate IGD for saved PlatEMO v2.9 final populations using:
% T1 - PlatEMO v2.9 problem.PF(10000)
% T2 - PlatEMO v4.3 problem.GetOptimum(10000)
% T3 - the reference files used by the completed v2.9 experiments

clear; clc;

root = fileparts(mfilename('fullpath'));
outRoot = fullfile(root,'nsga2_outputs','v290_pf_sources_t1_t2_t3');
pfRoot = fullfile(outRoot,'reference_pf');
if ~exist(outRoot,'dir'); mkdir(outRoot); end
if ~exist(pfRoot,'dir'); mkdir(pfRoot); end

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

if numel(dir(fullfile(pfRoot,'T1_v290','*.csv'))) ~= size(problems,1)
    error('T1 PF files are incomplete. Run generate_t1_v290_pf.m first.');
end
if numel(dir(fullfile(pfRoot,'T2_v43','*.csv'))) ~= size(problems,1)
    error('T2 PF files are incomplete. Run generate_t2_v43_pf.m first.');
end

detailRows = {};
summaryRows = {};
pfRows = {};
detailIndex = 0;
summaryIndex = 0;
pfIndex = 0;

for p = 1:size(problems,1)
    name = problems{p,1};
    M = problems{p,2};
    D = problems{p,3};
    paperIGD = problems{p,4};
    populationBatch = problems{p,5};

    T1 = readmatrix(fullfile(pfRoot,'T1_v290',[name,'.csv']));
    T2 = readmatrix(fullfile(pfRoot,'T2_v43',[name,'.csv']));
    T3 = readT3(root,name);
    sources = {T1,T2,T3};
    labels = {'T1_v290_PF','T2_v43_GetOptimum','T3_experiment_file'};

    pfIndex = pfIndex + 1;
    pfRows(pfIndex,:) = {name,size(T1,1),size(T2,1),size(T3,1), ...
        sameMatrix(T1,T2),sameMatrix(T1,T3),sameMatrix(T2,T3), ...
        matrixDifference(T1,T2),matrixDifference(T1,T3),matrixDifference(T2,T3)};

    values = nan(30,3);
    for run = 1:30
        objFile = fullfile(root,'nsga2_outputs',populationBatch,name, ...
            sprintf('run_%03d',run),'obj.csv');
        Obj = readmatrix(objFile);
        for source = 1:3
            duplicate = find(cellfun(@(x)sameMatrix(x,sources{source}), ...
                sources(1:source-1)),1);
            if isempty(duplicate)
                values(run,source) = MatrixIGD(Obj,sources{source});
            else
                values(run,source) = values(run,duplicate);
            end
            detailIndex = detailIndex + 1;
            detailRows(detailIndex,:) = {labels{source},name,M,D,run, ...
                size(sources{source},1),values(run,source)};
        end
    end

    for source = 1:3
        meanIGD = mean(values(:,source));
        sampleStd = std(values(:,source));
        signedDiff = meanIGD-paperIGD;
        summaryIndex = summaryIndex + 1;
        summaryRows(summaryIndex,:) = {labels{source},name,M,D,30, ...
            size(sources{source},1),paperIGD,meanIGD,sampleStd, ...
            signedDiff,abs(signedDiff),abs(signedDiff)/paperIGD*100, ...
            sprintf('%.4e (%.4e)',meanIGD,sampleStd)};
    end
    fprintf('%s complete: T1 %.12g, T2 %.12g, T3 %.12g\n', ...
        name,mean(values(:,1)),mean(values(:,2)),mean(values(:,3)));
end

detail = cell2table(detailRows,'VariableNames', ...
    {'source','problem','M','D','run','pf_points','igd'});
summary = cell2table(summaryRows,'VariableNames', ...
    {'source','problem','M','D','runs','pf_points','paper_igd','mean_igd', ...
     'sample_std','signed_diff','abs_diff','relative_diff_percent','mean_std'});
pfComparison = cell2table(pfRows,'VariableNames', ...
    {'problem','T1_points','T2_points','T3_points','T1_eq_T2','T1_eq_T3', ...
     'T2_eq_T3','T1_T2_max_abs_diff','T1_T3_max_abs_diff','T2_T3_max_abs_diff'});

writetable(detail,fullfile(outRoot,'per_run_igd.csv'));
writetable(summary,fullfile(outRoot,'summary.csv'));
writetable(pfComparison,fullfile(outRoot,'pf_source_comparison.csv'));

sourceRanking = groupsummary(summary,'source',{'mean','median'},'relative_diff_percent');
sourceRanking = sortrows(sourceRanking,'mean_relative_diff_percent');
writetable(sourceRanking,fullfile(outRoot,'source_ranking.csv'));

bestRows = cell(size(problems,1),5);
for p = 1:size(problems,1)
    name = problems{p,1};
    subset = summary(strcmp(summary.problem,name),:);
    [~,index] = min(subset.abs_diff);
    bestRows(p,:) = {name,subset.source{index},subset.mean_igd(index), ...
        subset.sample_std(index),subset.relative_diff_percent(index)};
end
best = cell2table(bestRows,'VariableNames', ...
    {'problem','closest_source','mean_igd','sample_std','relative_diff_percent'});
writetable(best,fullfile(outRoot,'best_source_per_problem.csv'));

disp(summary);
disp(sourceRanking);
disp(pfComparison);

function PF = readT3(root,name)
    if startsWith(name,'ZDT')
        PF = readmatrix(fullfile(root,'zdt_reference_v43',[name,'.csv']));
    elseif startsWith(name,'DTLZ')
        PF = readmatrix(fullfile(root,'dtlz_reference_v43',[name,'.csv']));
    else
        PF = readmatrix(fullfile(root,'cec2009_reference','official_database', ...
            'CEC2009_MultiObjectiveEA_Database','pf_data',[name,'.dat']), ...
            'FileType','text');
    end
end

function value = MatrixIGD(PopObj,PF)
    minimumDistances = inf(size(PF,1),1);
    for i = 1:size(PopObj,1)
        difference = PF-PopObj(i,:);
        minimumDistances = min(minimumDistances,sqrt(sum(difference.^2,2)));
    end
    value = mean(minimumDistances);
end

function result = sameMatrix(A,B)
    result = isequal(size(A),size(B)) && all(A(:)==B(:));
end

function value = matrixDifference(A,B)
    if ~isequal(size(A),size(B))
        value = NaN;
    else
        value = max(abs(A(:)-B(:)));
    end
end
