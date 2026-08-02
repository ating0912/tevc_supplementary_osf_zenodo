% Compare saved PlatEMO objectives with the official CEC 2009 MATLAB code.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
officialRoot = fullfile(scriptDir,'cec2009_reference','official_database', ...
    'CEC2009_MultiObjectiveEA_Database');
inputRoot = fullfile(scriptDir,'nsga2_outputs','platemo_v43_uf1_5_seeded');
outputFile = fullfile(inputRoot,'cec2009_official_uf_validation.csv');
restoredefaultpath;
addpath(officialRoot);

rows = {};
summaryRows = {};
for p = 1:5
    name = sprintf('UF%d',p);
    officialFcn = cec09(name);
    allDiffs = [];
    for run = 1:30
        runDir = fullfile(inputRoot,name,sprintf('run_%03d',run));
        Dec = readmatrix(fullfile(runDir,'dec.csv'));
        savedObj = readmatrix(fullfile(runDir,'obj.csv'));
        officialObj = officialFcn(Dec')';
        absDiff = abs(officialObj-savedObj);
        allDiffs = [allDiffs;absDiff(:)]; %#ok<AGROW>
        rows(end+1,:) = {name,run,max(absDiff,[],'all'), ...
            mean(absDiff,'all')}; %#ok<SAGROW>
    end
    summaryRows(end+1,:) = {name,30,max(allDiffs),mean(allDiffs), ...
        sum(allDiffs>1e-12)}; %#ok<SAGROW>
end

detail = cell2table(rows,'VariableNames', ...
    {'problem','seed','max_objective_abs_diff','mean_objective_abs_diff'});
summary = cell2table(summaryRows,'VariableNames', ...
    {'problem','runs','max_objective_abs_diff','mean_objective_abs_diff', ...
    'values_different_above_1e_12'});
writetable(detail,outputFile);
writetable(summary,fullfile(inputRoot,'cec2009_official_uf_validation_summary.csv'));
disp(summary);
