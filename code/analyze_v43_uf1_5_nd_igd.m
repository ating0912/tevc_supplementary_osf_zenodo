% Recalculate PlatEMO v4.3 UF1-UF5 IGD using nondominated solutions only.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir, 'PlatEMO_v4.3', 'PlatEMO');
inputRoot = fullfile(scriptDir, 'nsga2_outputs', 'platemo_v43_uf1_5_seeded');
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
    fullValues = nan(30,1);
    ndValues = nan(30,1);
    ndCounts = nan(30,1);

    for run = 1:30
        objPath = fullfile(inputRoot,name,sprintf('run_%03d',run),'obj.csv');
        Obj = readmatrix(objPath);
        FrontNo = NDSort(Obj,1);
        NDObj = Obj(FrontNo == 1,:);
        fullValues(run) = MatrixIGD(Obj,PF);
        ndValues(run) = MatrixIGD(NDObj,PF);
        ndCounts(run) = size(NDObj,1);
    end

    fullMean = mean(fullValues);
    fullStd = std(fullValues);
    ndMean = mean(ndValues);
    ndStd = std(ndValues);
    fullRel = abs(fullMean-paper)/paper*100;
    ndRel = abs(ndMean-paper)/paper*100;
    rows(end+1,:) = {name,paper,fullMean,fullStd,fullRel,ndMean,ndStd,ndRel, ...
        ndRel-fullRel,mean(ndCounts),min(ndCounts),max(ndCounts)}; %#ok<SAGROW>

    runTable = table((1:30)',fullValues,ndValues,ndCounts, ...
        'VariableNames',{'seed','full_population_igd','nondominated_igd','nondominated_count'});
    writetable(runTable,fullfile(inputRoot,name,'igd_full_vs_nd.csv'));
end

summary = cell2table(rows,'VariableNames', ...
    {'problem','paper_igd','full_mean','full_std','full_relative_diff_percent', ...
    'nd_mean','nd_std','nd_relative_diff_percent','nd_minus_full_diff_points', ...
    'mean_nd_count','min_nd_count','max_nd_count'});
writetable(summary,fullfile(inputRoot,'comparison_full_vs_nondominated.csv'));
disp(summary);
fprintf('Average relative difference, full population: %.6f%%\n',mean(summary.full_relative_diff_percent));
fprintf('Average relative difference, nondominated only: %.6f%%\n',mean(summary.nd_relative_diff_percent));

function score = MatrixIGD(PopObj,PF)
    minDistances = inf(size(PF,1),1);
    for i = 1:size(PopObj,1)
        diff = PF-PopObj(i,:);
        distances = sqrt(sum(diff.*diff,2));
        minDistances = min(minDistances,distances);
    end
    score = mean(minDistances);
end
