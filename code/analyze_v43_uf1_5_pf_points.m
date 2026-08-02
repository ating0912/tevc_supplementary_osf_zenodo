% Test IGD reference-set sizes on saved PlatEMO v4.3 UF1-UF5 populations.

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
pointCounts = [100,500,1000,10000];
rows = {};

for p = 1:size(problems,1)
    name = problems{p,1};
    problemFcn = problems{p,2};
    paper = problems{p,3};
    problem = problemFcn('N',100,'M',2,'D',30,'maxFE',10000);

    for pc = pointCounts
        PF = problem.GetOptimum(pc);
        values = nan(30,1);
        for run = 1:30
            Obj = readmatrix(fullfile(inputRoot,name,sprintf('run_%03d',run),'obj.csv'));
            FrontNo = NDSort(Obj,1);
            values(run) = MatrixIGD(Obj(FrontNo==1,:),PF);
        end
        meanIGD = mean(values);
        sampleStd = std(values);
        relativeDiff = abs(meanIGD-paper)/paper*100;
        rows(end+1,:) = {name,pc,size(PF,1),paper,meanIGD,sampleStd,relativeDiff}; %#ok<SAGROW>
    end
end

detail = cell2table(rows,'VariableNames', ...
    {'problem','requested_pf_points','actual_pf_points','paper_igd','mean_igd', ...
    'sample_std','relative_diff_percent'});
writetable(detail,fullfile(inputRoot,'comparison_pf_point_counts_detail.csv'));

summaryRows = {};
for pc = pointCounts
    subset = detail(detail.requested_pf_points==pc,:);
    summaryRows(end+1,:) = {pc,mean(subset.relative_diff_percent), ...
        median(subset.relative_diff_percent),sum(subset.relative_diff_percent<20)}; %#ok<SAGROW>
end
summary = cell2table(summaryRows,'VariableNames', ...
    {'requested_pf_points','mean_relative_diff_percent', ...
    'median_relative_diff_percent','problems_within_20_percent'});
writetable(summary,fullfile(inputRoot,'comparison_pf_point_counts_summary.csv'));
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
