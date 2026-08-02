% Calculate official CEC 2009 IGD for Deb NSGA-II C UF6-UF10 runs.

clear; clc;
scriptDir = fileparts(mfilename('fullpath'));
inputRoot = fullfile(scriptDir,'nsga2_outputs','deb_c_uf6_10_maxfe10000');
pfRoot = fullfile(scriptDir,'cec2009_reference','official_database', ...
    'CEC2009_MultiObjectiveEA_Database','pf_data');
addpath(fileparts(pfRoot));
papers = [0.5948,0.43887,0.58545,0.52501,0.74415];
summaryRows = {};
runRows = {};

for p = 6:10
    name = sprintf('UF%d',p);
    M = 2 + (p>=8);
    PF = readmatrix(fullfile(pfRoot,[name,'.dat']),'FileType','text');
    fullValues = nan(30,1);
    bestValues = nan(30,1);
    maxObjectiveDiff = nan(30,1);
    officialFcn = cec09(name);

    for run = 1:30
        runDir = fullfile(inputRoot,name,sprintf('run_%03d',run));
        finalData = readmatrix(fullfile(runDir,'final_pop.out'), ...
            'FileType','text','CommentStyle','#');
        bestData = readmatrix(fullfile(runDir,'best_pop.out'), ...
            'FileType','text','CommentStyle','#');
        finalObj = finalData(:,1:M);
        bestObj = bestData(:,1:M);
        finalDec = finalData(:,M+1:M+30);
        officialObj = officialFcn(finalDec')';
        maxObjectiveDiff(run) = max(abs(officialObj-finalObj),[],'all');
        fullValues(run) = MatrixIGD(finalObj,PF);
        bestValues(run) = MatrixIGD(bestObj,PF);
        runRows(end+1,:) = {name,run,fullValues(run),bestValues(run), ...
            maxObjectiveDiff(run),size(bestObj,1)}; %#ok<SAGROW>
    end

    sets = {'final_population','best_nondominated'};
    values = {fullValues,bestValues};
    for s = 1:2
        meanValue = mean(values{s});
        paper = papers(p-5);
        summaryRows(end+1,:) = {name,M,sets{s},30,paper,meanValue, ...
            std(values{s}),meanValue-paper,abs(meanValue-paper), ...
            abs(meanValue-paper)/paper*100,max(maxObjectiveDiff)}; %#ok<SAGROW>
    end
end

detail = cell2table(runRows,'VariableNames', ...
    {'problem','seed','final_population_igd','best_nondominated_igd', ...
    'max_official_objective_abs_diff','best_population_size'});
summary = cell2table(summaryRows,'VariableNames', ...
    {'problem','M','solution_set','runs','paper_igd','mean_igd','sample_std', ...
    'signed_diff','abs_diff','relative_diff_percent', ...
    'max_official_objective_abs_diff'});
writetable(detail,fullfile(inputRoot,'igd_runs.csv'));
writetable(summary,fullfile(inputRoot,'summary.csv'));
disp(summary);

function score = MatrixIGD(PopObj,PF)
    minDistances = inf(size(PF,1),1);
    for i = 1:size(PopObj,1)
        delta = PF-PopObj(i,:);
        minDistances = min(minDistances,sqrt(sum(delta.*delta,2)));
    end
    score = mean(minDistances);
end
