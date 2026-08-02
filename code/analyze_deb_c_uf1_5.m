% Calculate official CEC 2009 IGD for Deb NSGA-II C UF1-UF5 runs.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
inputRoot = fullfile(scriptDir,'nsga2_outputs','deb_c_uf1_5_maxfe10000');
pfRoot = fullfile(scriptDir,'cec2009_reference','official_database', ...
    'CEC2009_MultiObjectiveEA_Database','pf_data');

paperValues = [0.31352,0.21196,0.33463,0.12713,1.3074];
runRows = {};
summaryRows = {};

for p = 1:5
    name = sprintf('UF%d',p);
    PF = readmatrix(fullfile(pfRoot,[name,'.dat']),'FileType','text');
    fullValues = nan(30,1);
    bestValues = nan(30,1);
    for run = 1:30
        runDir = fullfile(inputRoot,name,sprintf('run_%03d',run));
        finalData = readmatrix(fullfile(runDir,'final_pop.out'), ...
            'FileType','text','CommentStyle','#');
        bestData = readmatrix(fullfile(runDir,'best_pop.out'), ...
            'FileType','text','CommentStyle','#');
        finalObj = finalData(:,1:2);
        bestObj = bestData(:,1:2);
        fullValues(run) = MatrixIGD(finalObj,PF);
        bestValues(run) = MatrixIGD(bestObj,PF);
        runRows(end+1,:) = {name,run,fullValues(run),bestValues(run), ...
            size(finalObj,1),size(bestObj,1)}; %#ok<SAGROW>
    end

    sets = {'final_population','best_nondominated'};
    values = {fullValues,bestValues};
    for s = 1:2
        meanValue = mean(values{s});
        stdValue = std(values{s});
        paper = paperValues(p);
        summaryRows(end+1,:) = {name,sets{s},30,paper,meanValue,stdValue, ...
            meanValue-paper,abs(meanValue-paper), ...
            abs(meanValue-paper)/paper*100}; %#ok<SAGROW>
    end
end

detail = cell2table(runRows,'VariableNames', ...
    {'problem','seed','final_population_igd','best_nondominated_igd', ...
    'final_population_size','best_population_size'});
summary = cell2table(summaryRows,'VariableNames', ...
    {'problem','solution_set','runs','paper_igd','mean_igd','sample_std', ...
    'signed_diff','abs_diff','relative_diff_percent'});
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
