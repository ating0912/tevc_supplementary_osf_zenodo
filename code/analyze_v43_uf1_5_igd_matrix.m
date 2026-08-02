% Compare IGD evaluation conventions on fixed PlatEMO v4.3 UF1-UF5 runs.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v4.3','PlatEMO');
inputRoot = fullfile(scriptDir,'nsga2_outputs','platemo_v43_uf1_5_seeded');
cecRoot = fullfile(scriptDir,'cec2009_reference');
outputRoot = fullfile(inputRoot,'igd_evaluation_matrix');
if ~exist(outputRoot,'dir')
    mkdir(outputRoot);
end

restoredefaultpath;
addpath(genpath(platemoRoot));

problems = {
    'UF1', @UF1, 3.1352e-1;
    'UF2', @UF2, 2.1196e-1;
    'UF3', @UF3, 3.3463e-1;
    'UF4', @UF4, 1.2713e-1;
    'UF5', @UF5, 1.3074e0;
};
pfSources = {'cec2009_jmetal','platemo_getoptimum'};
setTypes = {'full_population','nondominated'};
normalizations = {'raw','pf_range','joint_range'};
metrics = {'igd','igd_plus','rms_min_distance','mean_min_squared_distance'};

runRows = {};
summaryRows = {};

for p = 1:size(problems,1)
    name = problems{p,1};
    problemFcn = problems{p,2};
    paper = problems{p,3};
    problem = problemFcn('N',100,'M',2,'D',30,'maxFE',10000);

    cecPF = readmatrix(fullfile(cecRoot,[name,'.pf']),'FileType','text');
    platemoPF = problem.GetOptimum(10000);
    pfSets = {cecPF,platemoPF};

    for ps = 1:numel(pfSources)
        PF = pfSets{ps};
        for st = 1:numel(setTypes)
            for nz = 1:numel(normalizations)
                values = nan(30,numel(metrics));
                pointCounts = nan(30,1);
                for run = 1:30
                    Obj = readmatrix(fullfile(inputRoot,name, ...
                        sprintf('run_%03d',run),'obj.csv'));
                    if strcmp(setTypes{st},'nondominated')
                        frontNo = NDSort(Obj,1);
                        Obj = Obj(frontNo==1,:);
                    end
                    pointCounts(run) = size(Obj,1);
                    [evalObj,evalPF] = NormalizeSets(Obj,PF,normalizations{nz});
                    values(run,:) = EvaluateMetrics(evalObj,evalPF);
                    for mt = 1:numel(metrics)
                        runRows(end+1,:) = {name,run,pfSources{ps},size(PF,1), ...
                            setTypes{st},pointCounts(run),normalizations{nz}, ...
                            metrics{mt},values(run,mt)}; %#ok<SAGROW>
                    end
                end

                for mt = 1:numel(metrics)
                    metricValues = values(:,mt);
                    meanValue = mean(metricValues);
                    stdValue = std(metricValues);
                    summaryRows(end+1,:) = {name,paper,pfSources{ps}, ...
                        size(PF,1),setTypes{st},mean(pointCounts), ...
                        normalizations{nz},metrics{mt},meanValue,stdValue, ...
                        meanValue-paper,abs(meanValue-paper), ...
                        abs(meanValue-paper)/paper*100}; %#ok<SAGROW>
                end
            end
        end
    end
end

runDetail = cell2table(runRows,'VariableNames', ...
    {'problem','seed','pf_source','pf_points','solution_set', ...
    'solution_points','normalization','metric','value'});
summary = cell2table(summaryRows,'VariableNames', ...
    {'problem','paper_igd','pf_source','pf_points','solution_set', ...
    'mean_solution_points','normalization','metric','mean_value', ...
    'sample_std','signed_diff','abs_diff','relative_diff_percent'});
summary = sortrows(summary,{'problem','relative_diff_percent'});

writetable(runDetail,fullfile(outputRoot,'run_detail.csv'));
writetable(summary,fullfile(outputRoot,'summary_all.csv'));

bestPerProblem = summary([],:);
for p = 1:size(problems,1)
    subset = summary(strcmp(summary.problem,problems{p,1}),:);
    bestPerProblem = [bestPerProblem;subset(1,:)]; %#ok<AGROW>
end
writetable(bestPerProblem,fullfile(outputRoot,'best_per_problem.csv'));

configs = unique(summary(:,{'pf_source','solution_set','normalization','metric'}),'stable');
rankRows = {};
for c = 1:height(configs)
    mask = strcmp(summary.pf_source,configs.pf_source{c}) & ...
        strcmp(summary.solution_set,configs.solution_set{c}) & ...
        strcmp(summary.normalization,configs.normalization{c}) & ...
        strcmp(summary.metric,configs.metric{c});
    subset = summary(mask,:);
    rankRows(end+1,:) = {configs.pf_source{c},configs.solution_set{c}, ...
        configs.normalization{c},configs.metric{c}, ...
        mean(subset.relative_diff_percent), ...
        median(subset.relative_diff_percent), ...
        sum(subset.relative_diff_percent<20)}; %#ok<SAGROW>
end
ranking = cell2table(rankRows,'VariableNames', ...
    {'pf_source','solution_set','normalization','metric', ...
    'mean_relative_diff_percent','median_relative_diff_percent', ...
    'problems_within_20_percent'});
ranking = sortrows(ranking,'mean_relative_diff_percent');
writetable(ranking,fullfile(outputRoot,'configuration_ranking.csv'));

disp(bestPerProblem);
disp(ranking(1:min(10,height(ranking)),:));

function [normalizedObj,normalizedPF] = NormalizeSets(Obj,PF,method)
    switch method
        case 'raw'
            normalizedObj = Obj;
            normalizedPF = PF;
        case 'pf_range'
            lower = min(PF,[],1);
            span = max(PF,[],1)-lower;
            span(span==0) = 1;
            normalizedObj = (Obj-lower)./span;
            normalizedPF = (PF-lower)./span;
        case 'joint_range'
            combined = [Obj;PF];
            lower = min(combined,[],1);
            span = max(combined,[],1)-lower;
            span(span==0) = 1;
            normalizedObj = (Obj-lower)./span;
            normalizedPF = (PF-lower)./span;
    end
end

function scores = EvaluateMetrics(Obj,PF)
    minSquared = inf(size(PF,1),1);
    minPlusSquared = inf(size(PF,1),1);
    for i = 1:size(Obj,1)
        delta = PF-Obj(i,:);
        squared = sum(delta.*delta,2);
        minSquared = min(minSquared,squared);

        plusDelta = max(Obj(i,:)-PF,0);
        plusSquared = sum(plusDelta.*plusDelta,2);
        minPlusSquared = min(minPlusSquared,plusSquared);
    end

    scores = [mean(sqrt(minSquared)), ...
        mean(sqrt(minPlusSquared)), ...
        sqrt(mean(minSquared)), ...
        mean(minSquared)];
end
