% Test two common objective-normalization conventions for IGD.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v4.3','PlatEMO');
inputRoot = fullfile(scriptDir,'nsga2_outputs','platemo_v43_uf1_5_seeded');
restoredefaultpath;
addpath(genpath(platemoRoot));

problems = {
    'UF1', @UF1, 3.1352e-1;
    'UF2', @UF2, 2.1196e-1;
    'UF3', @UF3, 3.3463e-1;
    'UF4', @UF4, 1.2713e-1;
    'UF5', @UF5, 1.3074e0;
};
rows = {};

for p = 1:size(problems,1)
    name = problems{p,1};
    problemFcn = problems{p,2};
    paper = problems{p,3};
    problem = problemFcn('N',100,'M',2,'D',30,'maxFE',10000);
    PF = problem.GetOptimum(10000);
    raw = nan(30,1);
    pfNorm = nan(30,1);
    jointNorm = nan(30,1);

    pfLower = min(PF,[],1);
    pfSpan = max(PF,[],1)-pfLower;
    pfSpan(pfSpan==0) = 1;
    normalizedPF = (PF-pfLower)./pfSpan;

    for run = 1:30
        Obj = readmatrix(fullfile(inputRoot,name,sprintf('run_%03d',run),'obj.csv'));
        FrontNo = NDSort(Obj,1);
        NDObj = Obj(FrontNo==1,:);
        raw(run) = MatrixIGD(NDObj,PF);
        pfNorm(run) = MatrixIGD((NDObj-pfLower)./pfSpan,normalizedPF);

        allObj = [PF;NDObj];
        jointLower = min(allObj,[],1);
        jointSpan = max(allObj,[],1)-jointLower;
        jointSpan(jointSpan==0) = 1;
        jointNorm(run) = MatrixIGD((NDObj-jointLower)./jointSpan, ...
            (PF-jointLower)./jointSpan);
    end

    methods = {'raw';'pf_range_normalized';'joint_range_normalized'};
    values = {raw;pfNorm;jointNorm};
    for m = 1:numel(methods)
        meanIGD = mean(values{m});
        sampleStd = std(values{m});
        rows(end+1,:) = {name,methods{m},paper,meanIGD,sampleStd, ...
            abs(meanIGD-paper)/paper*100}; %#ok<SAGROW>
    end
end

detail = cell2table(rows,'VariableNames', ...
    {'problem','normalization','paper_igd','mean_igd','sample_std', ...
    'relative_diff_percent'});
writetable(detail,fullfile(inputRoot,'comparison_normalization_detail.csv'));

methods = unique(detail.normalization,'stable');
summaryRows = {};
for m = 1:numel(methods)
    subset = detail(strcmp(detail.normalization,methods{m}),:);
    summaryRows(end+1,:) = {methods{m},mean(subset.relative_diff_percent), ...
        median(subset.relative_diff_percent)}; %#ok<SAGROW>
end
summary = cell2table(summaryRows,'VariableNames', ...
    {'normalization','mean_relative_diff_percent','median_relative_diff_percent'});
writetable(summary,fullfile(inputRoot,'comparison_normalization_summary.csv'));
disp(detail);
disp(summary);

function score = MatrixIGD(PopObj,PF)
    minDistances = inf(size(PF,1),1);
    for i = 1:size(PopObj,1)
        diff = PF-PopObj(i,:);
        distances = sqrt(sum(diff.*diff,2));
        minDistances = min(minDistances,distances);
    end
    score = mean(minDistances);
end
