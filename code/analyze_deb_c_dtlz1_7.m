% Calculate common-reference IGD for Deb NSGA-II C DTLZ1-DTLZ7 runs.

clear; clc;
scriptDir = fileparts(mfilename('fullpath'));
inputRoot = fullfile(scriptDir,'nsga2_outputs','deb_c_dtlz1_7_maxfe10000');
pfRoot = fullfile(scriptDir,'dtlz_reference_v43');
papers = [0.23828,0.054881,13.357,0.40388,0.032473,0.11635,0.1708];
dims = [7,12,12,12,12,12,22];
summaryRows = {}; runRows = {};

restoredefaultpath;
addpath(genpath(fullfile(scriptDir,'PlatEMO_v4.3','PlatEMO')));
for p = 1:7
    name = sprintf('DTLZ%d',p); D = dims(p);
    PF = readmatrix(fullfile(pfRoot,[name,'.csv']));
    fullValues = nan(30,1); bestValues = nan(30,1);
    objectiveDiff = nan(30,1);
    problemFcn = str2func(name);
    problem = problemFcn('N',100,'M',3,'D',D,'maxFE',10000);
    for run = 1:30
        runDir = fullfile(inputRoot,name,sprintf('run_%03d',run));
        finalData = readmatrix(fullfile(runDir,'final_pop.out'), ...
            'FileType','text','CommentStyle','#');
        bestData = readmatrix(fullfile(runDir,'best_pop.out'), ...
            'FileType','text','CommentStyle','#');
        finalObj = finalData(:,1:3); bestObj = bestData(:,1:3);
        finalDec = finalData(:,4:3+D);
        officialObj = problem.CalObj(finalDec);
        objectiveDiff(run) = max(abs(officialObj-finalObj),[],'all');
        fullValues(run) = MatrixIGD(finalObj,PF);
        bestValues(run) = MatrixIGD(bestObj,PF);
        runRows(end+1,:) = {name,run,fullValues(run),bestValues(run), ...
            objectiveDiff(run),size(bestObj,1)}; %#ok<SAGROW>
    end
    sets = {'final_population','best_nondominated'};
    values = {fullValues,bestValues};
    for s = 1:2
        meanValue = mean(values{s}); paper = papers(p);
        summaryRows(end+1,:) = {name,3,D,sets{s},30,size(PF,1),paper, ...
            meanValue,std(values{s}),meanValue-paper,abs(meanValue-paper), ...
            abs(meanValue-paper)/paper*100,max(objectiveDiff)}; %#ok<SAGROW>
    end
end
detail = cell2table(runRows,'VariableNames', ...
    {'problem','seed','final_population_igd','best_nondominated_igd', ...
    'max_objective_abs_diff','best_population_size'});
summary = cell2table(summaryRows,'VariableNames', ...
    {'problem','M','D','solution_set','runs','pf_points','paper_igd','mean_igd', ...
    'sample_std','signed_diff','abs_diff','relative_diff_percent', ...
    'max_objective_abs_diff'});
writetable(detail,fullfile(inputRoot,'igd_runs.csv'));
writetable(summary,fullfile(inputRoot,'summary.csv')); disp(summary);

function score = MatrixIGD(PopObj,PF)
    minDistances = inf(size(PF,1),1);
    for i = 1:size(PopObj,1)
        delta = PF-PopObj(i,:);
        minDistances = min(minDistances,sqrt(sum(delta.*delta,2)));
    end
    score = mean(minDistances);
end
