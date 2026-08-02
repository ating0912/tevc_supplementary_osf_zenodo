% Test initialization + exactly 100 offspring generations (maxFE=10100).

clear; clc;

N = 100;
M = 2;
D = 30;
maxFE = 10100;
runs = 1:30;
scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v4.3','PlatEMO');
outRoot = fullfile(scriptDir,'nsga2_outputs','platemo_v43_uf1_5_exact_100gen');
if ~exist(outRoot,'dir'); mkdir(outRoot); end
restoredefaultpath;
addpath(genpath(platemoRoot));
addpath(fullfile(scriptDir,'platemo_v43_compat'));

problems = {
    'UF1',@UF1,3.1352e-1;
    'UF2',@UF2,2.1196e-1;
    'UF3',@UF3,3.3463e-1;
    'UF4',@UF4,1.2713e-1;
    'UF5',@UF5,1.3074e0;
};
rows = {};

for p = 1:size(problems,1)
    name = problems{p,1};
    problemFcn = problems{p,2};
    paper = problems{p,3};
    problemDir = fullfile(outRoot,name);
    if ~exist(problemDir,'dir'); mkdir(problemDir); end
    referenceProblem = problemFcn('N',N,'M',M,'D',D,'maxFE',maxFE);
    PF = referenceProblem.GetOptimum(10000);
    values = nan(30,1);

    fprintf('=== %s exact 100 generations ===\n',name);
    for run = runs
        objPath = fullfile(problemDir,sprintf('run_%03d_obj.csv',run));
        if exist(objPath,'file')
            Obj = readmatrix(objPath);
        else
            rng(run,'twister');
            evalc("[~,Obj,~]=platemo('algorithm',@NSGAII,'problem',problemFcn," + ...
                "'N',N,'M',M,'D',D,'maxFE',maxFE);");
            writematrix(Obj,objPath);
        end
        FrontNo = NDSort(Obj,1);
        values(run) = MatrixIGD(Obj(FrontNo==1,:),PF);
        fprintf('%s seed=%02d IGD=%.12g\n',name,run,values(run));
    end

    meanIGD = mean(values);
    sampleStd = std(values);
    relativeDiff = abs(meanIGD-paper)/paper*100;
    rows(end+1,:) = {name,paper,meanIGD,sampleStd,relativeDiff}; %#ok<SAGROW>
    writetable(table(runs(:),values,'VariableNames',{'seed','igd'}), ...
        fullfile(problemDir,'igd_runs.csv'));
end

summary = cell2table(rows,'VariableNames', ...
    {'problem','paper_igd','mean_igd','sample_std','relative_diff_percent'});
writetable(summary,fullfile(outRoot,'summary.csv'));
disp(summary);
fprintf('Average relative difference: %.6f%%\n',mean(summary.relative_diff_percent));

function score = MatrixIGD(PopObj,PF)
    minDistances = inf(size(PF,1),1);
    for i = 1:size(PopObj,1)
        diff = PF-PopObj(i,:);
        distances = sqrt(sum(diff.*diff,2));
        minDistances = min(minDistances,distances);
    end
    score = mean(minDistances);
end
