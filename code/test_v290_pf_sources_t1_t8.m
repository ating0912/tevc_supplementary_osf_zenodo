% Compare T1-T8 reference PF definitions on saved PlatEMO v2.9 populations.
%
% T1 v2.9 PF(10000)
% T2 v4.3 GetOptimum(10000)
% T3 reference files used by the completed v2.9 experiments
% T4 official CEC2009 PF files (UF only)
% T5 independently generated analytic PF, nominally 10000 points
%    (ZDT and DTLZ only)
% T6 high-density analytic PF, nominally 100000 points
%    (ZDT and DTLZ only)
% T7 union of T1-T5 followed by duplicate and non-dominated filtering
% T8 empirical union PF from v4.3, v2.9, and Deb C final populations
%
% T8 includes the evaluated v2.9 populations and is therefore diagnostic
% and optimistically biased. It must not be used as an independent metric.

clear; clc;

root = fileparts(mfilename('fullpath'));
outRoot = fullfile(root,'nsga2_outputs','v290_pf_sources_t1_t8');
pfRoot = fullfile(outRoot,'reference_pf');
if ~exist(outRoot,'dir'); mkdir(outRoot); end
if ~exist(pfRoot,'dir'); mkdir(pfRoot); end

restoredefaultpath;
addpath(genpath(fullfile(root,'PlatEMO_v4.3','PlatEMO')));

problems = {
    'DTLZ1', 3,  7, 0.23828, 'platemo_v290_dtlz1_7_seeded_r2020b', 'platemo_v43_dtlz1_7_seeded_r2026a', 'deb_c_dtlz1_7_maxfe10000';
    'DTLZ2', 3, 12, 0.054881,'platemo_v290_dtlz1_7_seeded_r2020b', 'platemo_v43_dtlz1_7_seeded_r2026a', 'deb_c_dtlz1_7_maxfe10000';
    'DTLZ3', 3, 12, 13.357,  'platemo_v290_dtlz1_7_seeded_r2020b', 'platemo_v43_dtlz1_7_seeded_r2026a', 'deb_c_dtlz1_7_maxfe10000';
    'DTLZ4', 3, 12, 0.40388, 'platemo_v290_dtlz1_7_seeded_r2020b', 'platemo_v43_dtlz1_7_seeded_r2026a', 'deb_c_dtlz1_7_maxfe10000';
    'DTLZ5', 3, 12, 0.032473,'platemo_v290_dtlz1_7_seeded_r2020b', 'platemo_v43_dtlz1_7_seeded_r2026a', 'deb_c_dtlz1_7_maxfe10000';
    'DTLZ6', 3, 12, 0.11635, 'platemo_v290_dtlz1_7_seeded_r2020b', 'platemo_v43_dtlz1_7_seeded_r2026a', 'deb_c_dtlz1_7_maxfe10000';
    'DTLZ7', 3, 22, 0.1708,  'platemo_v290_dtlz1_7_seeded_r2020b', 'platemo_v43_dtlz1_7_seeded_r2026a', 'deb_c_dtlz1_7_maxfe10000';
    'ZDT1',  2, 30, 0.14621, 'platemo_v290_zdt_seeded_r2020b', 'platemo_v43_zdt_seeded_r2026a', 'deb_c_zdt_maxfe10000';
    'ZDT2',  2, 30, 0.50813, 'platemo_v290_zdt_seeded_r2020b', 'platemo_v43_zdt_seeded_r2026a', 'deb_c_zdt_maxfe10000';
    'ZDT3',  2, 30, 0.17787, 'platemo_v290_zdt_seeded_r2020b', 'platemo_v43_zdt_seeded_r2026a', 'deb_c_zdt_maxfe10000';
    'ZDT4',  2, 10, 0.53146, 'platemo_v290_zdt_seeded_r2020b', 'platemo_v43_zdt_seeded_r2026a', 'deb_c_zdt_maxfe10000';
    'ZDT6',  2, 10, 0.07429, 'platemo_v290_zdt_seeded_r2020b', 'platemo_v43_zdt_seeded_r2026a', 'deb_c_zdt_maxfe10000';
    'UF1',   2, 30, 0.31352, 'platemo_v290_uf1_5_seeded_r2020b', 'platemo_v43_uf1_5_seeded', 'deb_c_uf1_5_maxfe10000';
    'UF2',   2, 30, 0.21196, 'platemo_v290_uf1_5_seeded_r2020b', 'platemo_v43_uf1_5_seeded', 'deb_c_uf1_5_maxfe10000';
    'UF3',   2, 30, 0.33463, 'platemo_v290_uf1_5_seeded_r2020b', 'platemo_v43_uf1_5_seeded', 'deb_c_uf1_5_maxfe10000';
    'UF4',   2, 30, 0.12713, 'platemo_v290_uf1_5_seeded_r2020b', 'platemo_v43_uf1_5_seeded', 'deb_c_uf1_5_maxfe10000';
    'UF5',   2, 30, 1.3074,  'platemo_v290_uf1_5_seeded_r2020b', 'platemo_v43_uf1_5_seeded', 'deb_c_uf1_5_maxfe10000';
    'UF6',   2, 30, 0.59480, 'platemo_v290_uf6_10_seeded_r2020b', 'platemo_v43_uf6_10_seeded_r2026a', 'deb_c_uf6_10_maxfe10000';
    'UF7',   2, 30, 0.43887, 'platemo_v290_uf6_10_seeded_r2020b', 'platemo_v43_uf6_10_seeded_r2026a', 'deb_c_uf6_10_maxfe10000';
    'UF8',   3, 30, 0.58545, 'platemo_v290_uf6_10_seeded_r2020b', 'platemo_v43_uf6_10_seeded_r2026a', 'deb_c_uf6_10_maxfe10000';
    'UF9',   3, 30, 0.52501, 'platemo_v290_uf6_10_seeded_r2020b', 'platemo_v43_uf6_10_seeded_r2026a', 'deb_c_uf6_10_maxfe10000';
    'UF10',  3, 30, 0.74415, 'platemo_v290_uf6_10_seeded_r2020b', 'platemo_v43_uf6_10_seeded_r2026a', 'deb_c_uf6_10_maxfe10000';
};

oldPFRoot = fullfile(root,'nsga2_outputs','v290_pf_sources_t1_t2_t3','reference_pf');
generateReferences(root,pfRoot,oldPFRoot,problems);

labels = {'T1_v290_PF','T2_v43_GetOptimum','T3_experiment_file', ...
    'T4_CEC2009_official','T5_analytic_10000','T6_analytic_100000', ...
    'T7_merged_reference','T8_empirical_union'};

detailRows = {};
summaryRows = {};
pfRows = {};
detailIndex = 0;
summaryIndex = 0;

for p = 1:size(problems,1)
    name = problems{p,1}; M = problems{p,2}; D = problems{p,3};
    paperIGD = problems{p,4}; populationBatch = problems{p,5};
    sources = cell(1,8);
    for source = 1:8
        file = fullfile(pfRoot,labels{source},[name,'.csv']);
        if exist(file,'file')
            sources{source} = readmatrix(file);
        else
            sources{source} = [];
        end
    end

    pfRows(end+1,:) = {name,M,D, ...
        size(sources{1},1),size(sources{2},1),size(sources{3},1), ...
        size(sources{4},1),size(sources{5},1),size(sources{6},1), ...
        size(sources{7},1),size(sources{8},1)}; %#ok<SAGROW>

    values = nan(30,8);
    for run = 1:30
        Obj = readmatrix(fullfile(root,'nsga2_outputs',populationBatch,name, ...
            sprintf('run_%03d',run),'obj.csv'));
        for source = 1:8
            if isempty(sources{source}); continue; end
            duplicate = find(cellfun(@(x)~isempty(x) && sameMatrix(x,sources{source}), ...
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

    for source = 1:8
        if all(isnan(values(:,source))); continue; end
        meanIGD = mean(values(:,source));
        sampleStd = std(values(:,source));
        signedDiff = meanIGD-paperIGD;
        summaryIndex = summaryIndex + 1;
        summaryRows(summaryIndex,:) = {labels{source},name,M,D,30, ...
            size(sources{source},1),paperIGD,meanIGD,sampleStd,signedDiff, ...
            abs(signedDiff),abs(signedDiff)/paperIGD*100, ...
            sprintf('%.4e (%.4e)',meanIGD,sampleStd)};
    end
    fprintf('%s complete\n',name);
end

detail = cell2table(detailRows,'VariableNames', ...
    {'source','problem','M','D','run','pf_points','igd'});
summary = cell2table(summaryRows,'VariableNames', ...
    {'source','problem','M','D','runs','pf_points','paper_igd','mean_igd', ...
     'sample_std','signed_diff','abs_diff','relative_diff_percent','mean_std'});
pfSummary = cell2table(pfRows,'VariableNames', ...
    {'problem','M','D','T1_points','T2_points','T3_points','T4_points', ...
     'T5_points','T6_points','T7_points','T8_points'});

writetable(detail,fullfile(outRoot,'per_run_igd.csv'));
writetable(summary,fullfile(outRoot,'summary.csv'));
writetable(pfSummary,fullfile(outRoot,'pf_point_counts.csv'));

sourceRanking = groupsummary(summary,'source',{'mean','median'},'relative_diff_percent');
sourceRanking = sortrows(sourceRanking,'mean_relative_diff_percent');
writetable(sourceRanking,fullfile(outRoot,'source_ranking.csv'));

dataset = strings(height(summary),1);
dataset(startsWith(summary.problem,'ZDT')) = "ZDT";
dataset(startsWith(summary.problem,'DTLZ')) = "DTLZ";
dataset(startsWith(summary.problem,'UF')) = "UF";
summaryWithDataset = addvars(summary,dataset,'After','problem');
datasetRanking = groupsummary(summaryWithDataset,{'source','dataset'}, ...
    {'mean','median'},'relative_diff_percent');
writetable(datasetRanking,fullfile(outRoot,'ranking_by_dataset.csv'));

bestRows = {};
for p = 1:size(problems,1)
    subset = summary(strcmp(summary.problem,problems{p,1}),:);
    [~,index] = min(subset.abs_diff);
    bestRows(end+1,:) = {problems{p,1},subset.source{index}, ...
        subset.mean_igd(index),subset.sample_std(index), ...
        subset.relative_diff_percent(index)}; %#ok<SAGROW>
end
best = cell2table(bestRows,'VariableNames', ...
    {'problem','closest_source','mean_igd','sample_std','relative_diff_percent'});
writetable(best,fullfile(outRoot,'best_source_per_problem.csv'));

disp(sourceRanking);
disp(datasetRanking);
disp(best);

function generateReferences(root,pfRoot,oldPFRoot,problems)
    labels = {'T1_v290_PF','T2_v43_GetOptimum','T3_experiment_file', ...
        'T4_CEC2009_official','T5_analytic_10000','T6_analytic_100000', ...
        'T7_merged_reference','T8_empirical_union'};
    for i = 1:numel(labels)
        folder = fullfile(pfRoot,labels{i});
        if ~exist(folder,'dir'); mkdir(folder); end
    end

    for p = 1:size(problems,1)
        name = problems{p,1}; M = problems{p,2};
        copyfile(fullfile(oldPFRoot,'T1_v290',[name,'.csv']), ...
            fullfile(pfRoot,labels{1},[name,'.csv']));
        copyfile(fullfile(oldPFRoot,'T2_v43',[name,'.csv']), ...
            fullfile(pfRoot,labels{2},[name,'.csv']));
        T3 = readT3(root,name);
        writematrix(T3,fullfile(pfRoot,labels{3},[name,'.csv']));

        official = [];
        if startsWith(name,'UF')
            official = readmatrix(fullfile(root,'cec2009_reference','official_database', ...
                'CEC2009_MultiObjectiveEA_Database','pf_data',[name,'.dat']), ...
                'FileType','text');
            writematrix(official,fullfile(pfRoot,labels{4},[name,'.csv']));
        end

        analytic10k = [];
        analytic100k = [];
        if startsWith(name,'ZDT') || startsWith(name,'DTLZ')
            analytic10k = analyticPF(name,M,10000);
            analytic100k = analyticPF(name,M,100000);
            writematrix(analytic10k,fullfile(pfRoot,labels{5},[name,'.csv']));
            writematrix(analytic100k,fullfile(pfRoot,labels{6},[name,'.csv']));
        end

        T1 = readmatrix(fullfile(pfRoot,labels{1},[name,'.csv']));
        T2 = readmatrix(fullfile(pfRoot,labels{2},[name,'.csv']));
        merged = unique([T1;T2;T3;official;analytic10k],'rows','stable');
        merged = merged(NDSort(merged,1)==1,:);
        writematrix(merged,fullfile(pfRoot,labels{7},[name,'.csv']));

        empirical = empiricalUnion(root,name,M,problems{p,5}, ...
            problems{p,6},problems{p,7});
        empirical = unique(empirical,'rows','stable');
        empirical = empirical(NDSort(empirical,1)==1,:);
        writematrix(empirical,fullfile(pfRoot,labels{8},[name,'.csv']));
        fprintf('PF %s: T7=%d T8=%d\n',name,size(merged,1),size(empirical,1));
    end
end

function PF = analyticPF(name,M,N)
    if strcmp(name,'ZDT1') || strcmp(name,'ZDT4')
        x = linspace(0,1,N)'; PF = [x,1-sqrt(x)];
    elseif strcmp(name,'ZDT2')
        x = linspace(0,1,N)'; PF = [x,1-x.^2];
    elseif strcmp(name,'ZDT3')
        x = linspace(0,1,N)';
        allPoints = [x,1-sqrt(x)-x.*sin(10*pi*x)];
        PF = allPoints(NDSort(allPoints,1)==1,:);
    elseif strcmp(name,'ZDT6')
        x = linspace(0.280775,1,N)'; PF = [x,1-x.^2];
    elseif strcmp(name,'DTLZ1')
        PF = UniformPoint(N,M)/2;
    elseif any(strcmp(name,{'DTLZ2','DTLZ3','DTLZ4'}))
        PF = UniformPoint(N,M);
        PF = PF./sqrt(sum(PF.^2,2));
    elseif any(strcmp(name,{'DTLZ5','DTLZ6'}))
        x = linspace(0,1,N)';
        curve = [x,1-x];
        curve = curve./sqrt(sum(curve.^2,2));
        PF = [curve(:,ones(1,M-2)),curve];
        PF = PF./sqrt(2).^repmat([M-2,M-2:-1:0],size(PF,1),1);
    elseif strcmp(name,'DTLZ7')
        interval = [0,0.251412,0.631627,0.859401];
        median = (interval(2)-interval(1))/ ...
            (interval(4)-interval(3)+interval(2)-interval(1));
        X = UniformPoint(N,M-1,'grid');
        X(X<=median) = X(X<=median)*(interval(2)-interval(1))/median;
        X(X>median) = (X(X>median)-median)* ...
            (interval(4)-interval(3))/(1-median)+interval(3);
        PF = [X,2*(M-sum(X/2.*(1+sin(3*pi.*X)),2))];
    else
        PF = [];
    end
end

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

function points = empiricalUnion(root,name,M,v290Batch,v43Batch,debBatch)
    points = [];
    for run = 1:30
        points = [points;readmatrix(fullfile(root,'nsga2_outputs',v290Batch, ...
            name,sprintf('run_%03d',run),'obj.csv'))]; %#ok<AGROW>
        points = [points;readmatrix(fullfile(root,'nsga2_outputs',v43Batch, ...
            name,sprintf('run_%03d',run),'obj.csv'))]; %#ok<AGROW>
        deb = readmatrix(fullfile(root,'nsga2_outputs',debBatch,name, ...
            sprintf('run_%03d',run),'final_pop.out'),'FileType','text', ...
            'CommentStyle','#');
        points = [points;deb(:,1:M)]; %#ok<AGROW>
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
