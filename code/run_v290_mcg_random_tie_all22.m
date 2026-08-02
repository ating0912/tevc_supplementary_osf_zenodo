% Full 22-problem validation of mcg16807 plus random exact tournament ties.

clear; clc;
root = fileparts(mfilename('fullpath'));
outputRoot = fullfile(root,'nsga2_outputs','v290_mcg_random_tie_all22');
if ~exist(outputRoot,'dir'); mkdir(outputRoot); end

restoredefaultpath;
addpath(fullfile(root,'v290_metric_compat'));
addpath(genpath(fullfile(root,'PlatEMO_v2.9.0','PlatEMO')));
addpath(fullfile(root,'platemo_v43_compat'));
addpath(root);

problems = {
    'DTLZ1',@DTLZ1,3, 7,0.23828;
    'DTLZ2',@DTLZ2,3,12,0.054881;
    'DTLZ3',@DTLZ3,3,12,13.357;
    'DTLZ4',@DTLZ4,3,12,0.40388;
    'DTLZ5',@DTLZ5,3,12,0.032473;
    'DTLZ6',@DTLZ6,3,12,0.11635;
    'DTLZ7',@DTLZ7,3,22,0.1708;
    'ZDT1', @ZDT1, 2,30,0.14621;
    'ZDT2', @ZDT2, 2,30,0.50813;
    'ZDT3', @ZDT3, 2,30,0.17787;
    'ZDT4', @ZDT4, 2,10,0.53146;
    'ZDT6', @ZDT6, 2,10,0.07429;
    'UF1',  @UF1,  2,30,0.31352;
    'UF2',  @UF2,  2,30,0.21196;
    'UF3',  @UF3,  2,30,0.33463;
    'UF4',  @UF4,  2,30,0.12713;
    'UF5',  @UF5,  2,30,1.3074;
    'UF6',  @UF6,  2,30,0.5948;
    'UF7',  @UF7,  2,30,0.43887;
    'UF8',  @UF8,  3,30,0.58545;
    'UF9',  @UF9,  3,30,0.52501;
    'UF10', @UF10, 3,30,0.74415;
};

rows = {};
for p = 1:size(problems,1)
    name = problems{p,1};
    problemFcn = problems{p,2};
    M = problems{p,3};
    D = problems{p,4};
    paperIGD = problems{p,5};
    problemDir = fullfile(outputRoot,name);
    if ~exist(problemDir,'dir'); mkdir(problemDir); end

    referenceGlobal = GLOBAL('-algorithm',@NSGAII,'-problem',problemFcn, ...
        '-N',100,'-M',M,'-D',D,'-evaluation',10000, ...
        '-outputFcn',@(varargin)[]);
    PF = referenceGlobal.problem.PF(10000);
    values = nan(30,1);
    for run = 1:30
        resultFile = fullfile(problemDir,sprintf('run_%03d.csv',run));
        if exist(resultFile,'file')
            old = readtable(resultFile);
            values(run) = old.igd(1);
            continue;
        end
        RandStream.setGlobalStream(RandStream('mcg16807','Seed',run));
        Global = GLOBAL('-algorithm',@NSGAII_RandomTie_v290, ...
            '-problem',problemFcn,'-N',100,'-M',M,'-D',D, ...
            '-evaluation',10000,'-run',run,'-outputFcn',@(varargin)[]);
        Global.Start();
        Population = Global.result{end,2};
        Obj = Population.objs;
        feasible = all(Population.cons<=0,2);
        Obj = Obj(feasible,:);
        Obj = Obj(NDSort(Obj,1)==1,:);
        values(run) = IGD(Obj,PF);
        writetable(table(run,values(run),'VariableNames',{'seed','igd'}), ...
            resultFile);
        fprintf('%s run=%02d IGD=%.12g\n',name,run,values(run));
    end

    meanIGD = mean(values);
    sampleStd = std(values);
    relativeDiff = abs(meanIGD-paperIGD)/paperIGD*100;
    rows(end+1,:) = {name,M,D,100,10000,30,paperIGD,meanIGD,sampleStd, ...
        meanIGD-paperIGD,abs(meanIGD-paperIGD),relativeDiff, ...
        sprintf('%.4e (%.4e)',meanIGD,sampleStd)}; %#ok<SAGROW>
    writetable(table((1:30)',values,'VariableNames',{'seed','igd'}), ...
        fullfile(problemDir,'igd_runs.csv'));
    writeSummary(outputRoot,rows);
end
writeSummary(outputRoot,rows);

T = cell2table(rows,'VariableNames',summaryNames());
familyRows = {};
families = {'DTLZ','ZDT','UF'};
for i = 1:numel(families)
    mask = startsWith(T.problem,families{i});
    familyRows(end+1,:) = {families{i},sum(mask), ...
        mean(T.relative_diff_percent(mask)), ...
        median(T.relative_diff_percent(mask))}; %#ok<SAGROW>
end
familyRows(end+1,:) = {'ALL',height(T),mean(T.relative_diff_percent), ...
    median(T.relative_diff_percent)};
family = cell2table(familyRows,'VariableNames', ...
    {'family','problem_count','mean_relative_diff_percent', ...
     'median_relative_diff_percent'});
writetable(family,fullfile(outputRoot,'family_ranking.csv'));
disp(T);
disp(family);

function writeSummary(outputRoot,rows)
    T = cell2table(rows,'VariableNames',summaryNames());
    writetable(T,fullfile(outputRoot,'summary.csv'));
end

function names = summaryNames()
    names = {'problem','M','D','N','maxFE','runs','paper_igd','mean_igd', ...
        'sample_std','signed_diff','abs_diff','relative_diff_percent', ...
        'mean_std'};
end
