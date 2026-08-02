% Diagnose whether paper MaxIt=10000 means 10000 generations.
% Only maxFE changes from 10000 to N*10000=1000000. All other settings
% follow the closest PlatEMO v2.9 GLOBAL.Metric/PF10b configuration.

clear; clc;

root = fileparts(mfilename('fullpath'));
outputRoot = fullfile(root,'nsga2_outputs','v290_maxit10000_diagnostic');
baselineRoot = fullfile(root,'nsga2_outputs','v290_seed_sensitivity_all22_rerun2');
if ~exist(outputRoot,'dir'); mkdir(outputRoot); end

restoredefaultpath;
addpath(fullfile(root,'v290_metric_compat'));
addpath(genpath(fullfile(root,'PlatEMO_v2.9.0','PlatEMO')));
addpath(fullfile(root,'platemo_v43_compat'));

N = 100;
maxFE = N*10000;
runs = 30;
problems = {
    'ZDT2', @ZDT2, 2,30,0.50813;
    'ZDT4', @ZDT4, 2,10,0.53146;
    'DTLZ1',@DTLZ1,3, 7,0.23828;
    'DTLZ4',@DTLZ4,3,12,0.40388;
    'UF6',  @UF6,  2,30,0.5948;
    'UF10', @UF10, 3,30,0.74415;
};

summaryRows = {};
for p = 1:size(problems,1)
    name = problems{p,1};
    problemFcn = problems{p,2};
    M = problems{p,3};
    D = problems{p,4};
    paperIGD = problems{p,5};
    problemDir = fullfile(outputRoot,name);
    if ~exist(problemDir,'dir'); mkdir(problemDir); end

    referenceGlobal = GLOBAL('-algorithm',@NSGAII,'-problem',problemFcn, ...
        '-N',N,'-M',M,'-D',D,'-evaluation',10000, ...
        '-outputFcn',@(varargin)[]);
    PF = referenceGlobal.problem.PF(10000);
    values = nan(runs,1);
    elapsed = nan(runs,1);

    for run = 1:runs
        runDir = fullfile(problemDir,sprintf('run_%03d',run));
        resultFile = fullfile(runDir,'igd.csv');
        if exist(resultFile,'file')
            old = readtable(resultFile);
            values(run) = old.igd(1);
            elapsed(run) = old.elapsed_seconds(1);
            continue;
        end
        if ~exist(runDir,'dir'); mkdir(runDir); end

        rng(run,'twister');
        timer = tic;
        Global = GLOBAL('-algorithm',@NSGAII,'-problem',problemFcn, ...
            '-N',N,'-M',M,'-D',D,'-evaluation',maxFE, ...
            '-run',run,'-outputFcn',@(varargin)[]);
        Global.Start();
        elapsed(run) = toc(timer);
        Population = Global.result{end,2};
        Obj = Population.objs;
        Dec = Population.decs;
        feasible = all(Population.cons<=0,2);
        feasibleObj = Obj(feasible,:);
        nonDominated = NDSort(feasibleObj,1)==1;
        value = IGD(feasibleObj(nonDominated,:),PF);
        values(run) = value;

        writematrix(Obj,fullfile(runDir,'obj.csv'));
        writematrix(Dec,fullfile(runDir,'dec.csv'));
        writetable(table(run,value,elapsed(run),maxFE,'VariableNames', ...
            {'seed','igd','elapsed_seconds','maxFE'}),resultFile);
        fprintf('%s run=%02d IGD=%.12g time=%.1fs\n', ...
            name,run,value,elapsed(run));
    end

    baselineFile = fullfile(baselineRoot,'S01_seed_1_30',name,'igd_runs.csv');
    baseline = readtable(baselineFile);
    baselineMean = mean(baseline.igd);
    longMean = mean(values);
    longStd = std(values);
    relativeDiff = abs(longMean-paperIGD)/paperIGD*100;
    baselineRelativeDiff = abs(baselineMean-paperIGD)/paperIGD*100;

    writetable(table((1:runs)',values,elapsed,'VariableNames', ...
        {'seed','igd','elapsed_seconds'}),fullfile(problemDir,'igd_runs.csv'));
    summaryRows(end+1,:) = {name,M,D,N,maxFE,runs,paperIGD, ...
        baselineMean,longMean,longStd,longMean-baselineMean, ...
        (longMean-baselineMean)/baselineMean*100,baselineRelativeDiff, ...
        relativeDiff,relativeDiff-baselineRelativeDiff,sum(elapsed)}; %#ok<SAGROW>
    writeSummary(outputRoot,summaryRows);
end

summary = cell2table(summaryRows,'VariableNames',summaryNames());
writetable(summary,fullfile(outputRoot,'summary.csv'));
disp(summary);

function writeSummary(outputRoot,rows)
    summary = cell2table(rows,'VariableNames',summaryNames());
    writetable(summary,fullfile(outputRoot,'summary_partial.csv'));
end

function names = summaryNames()
    names = {'problem','M','D','N','maxFE','runs','paper_igd', ...
        'baseline_10000_mean','maxit10000_mean','maxit10000_std', ...
        'mean_change','mean_change_percent','baseline_relative_diff_percent', ...
        'maxit10000_relative_diff_percent','relative_diff_change_points', ...
        'total_elapsed_seconds'};
end
