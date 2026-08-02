% Compare four tournament implementations while keeping the closest v2.9
% PF10b configuration unchanged.

clear; clc;

root = fileparts(mfilename('fullpath'));
outputRoot = fullfile(root,'nsga2_outputs','v290_tournament_diagnostic');
if ~exist(outputRoot,'dir'); mkdir(outputRoot); end

restoredefaultpath;
addpath(fullfile(root,'v290_metric_compat'));
addpath(genpath(fullfile(root,'PlatEMO_v2.9.0','PlatEMO')));
addpath(fullfile(root,'platemo_v43_compat'));
addpath(root);

problems = {
    'ZDT2', @ZDT2, 2,30,0.50813;
    'ZDT4', @ZDT4, 2,10,0.53146;
    'DTLZ1',@DTLZ1,3, 7,0.23828;
    'DTLZ4',@DTLZ4,3,12,0.40388;
    'UF6',  @UF6,  2,30,0.5948;
    'UF10', @UF10, 3,30,0.74415;
};
variants = {
    'X1_platemo_native',          @NSGAII;
    'X2_random_exact_tie',        @NSGAII_RandomTie_v290;
    'X3_dual_permutation_rank',   @NSGAII_DualPermutationRank_v290;
    'X4_deb_dominance_tournament',@NSGAII_DebTournament_v290;
};

rows = {};
for v = 1:size(variants,1)
    variant = variants{v,1};
    algorithm = variants{v,2};
    for p = 1:size(problems,1)
        name = problems{p,1};
        problemFcn = problems{p,2};
        M = problems{p,3};
        D = problems{p,4};
        paperIGD = problems{p,5};
        problemDir = fullfile(outputRoot,variant,name);
        if ~exist(problemDir,'dir'); mkdir(problemDir); end

        referenceGlobal = GLOBAL('-algorithm',@NSGAII,'-problem',problemFcn, ...
            '-N',100,'-M',M,'-D',D,'-evaluation',10000, ...
            '-outputFcn',@(varargin)[]);
        PF = referenceGlobal.problem.PF(10000);
        values = nan(30,1);

        for run = 1:30
            runDir = fullfile(problemDir,sprintf('run_%03d',run));
            resultFile = fullfile(runDir,'igd.csv');
            if exist(resultFile,'file')
                old = readtable(resultFile);
                values(run) = old.igd(1);
                continue;
            end
            if ~exist(runDir,'dir'); mkdir(runDir); end

            rng(run,'twister');
            Global = GLOBAL('-algorithm',algorithm,'-problem',problemFcn, ...
                '-N',100,'-M',M,'-D',D,'-evaluation',10000, ...
                '-run',run,'-outputFcn',@(varargin)[]);
            Global.Start();
            Population = Global.result{end,2};
            Obj = Population.objs;
            Dec = Population.decs;
            feasible = all(Population.cons<=0,2);
            feasibleObj = Obj(feasible,:);
            nonDominated = NDSort(feasibleObj,1)==1;
            values(run) = IGD(feasibleObj(nonDominated,:),PF);

            writematrix(Obj,fullfile(runDir,'obj.csv'));
            writematrix(Dec,fullfile(runDir,'dec.csv'));
            writetable(table(run,values(run),'VariableNames',{'seed','igd'}), ...
                resultFile);
            fprintf('%s %s run=%02d IGD=%.12g\n', ...
                variant,name,run,values(run));
        end

        meanIGD = mean(values);
        sampleStd = std(values);
        relativeDiff = abs(meanIGD-paperIGD)/paperIGD*100;
        writetable(table((1:30)',values,'VariableNames',{'seed','igd'}), ...
            fullfile(problemDir,'igd_runs.csv'));
        rows(end+1,:) = {variant,name,M,D,100,10000,30,paperIGD, ...
            meanIGD,sampleStd,meanIGD-paperIGD,abs(meanIGD-paperIGD), ...
            relativeDiff,sprintf('%.4e (%.4e)',meanIGD,sampleStd)}; %#ok<SAGROW>
        writeSummary(outputRoot,rows);
    end
end

summary = cell2table(rows,'VariableNames',summaryNames());
writetable(summary,fullfile(outputRoot,'summary.csv'));
ranking = groupsummary(summary,'variant',{'mean','median'}, ...
    'relative_diff_percent');
ranking = sortrows(ranking,'mean_relative_diff_percent');
writetable(ranking,fullfile(outputRoot,'ranking.csv'));

bestRows = {};
names = unique(summary.problem,'stable');
for p = 1:numel(names)
    subset = summary(strcmp(summary.problem,names{p}),:);
    [~,best] = min(subset.relative_diff_percent);
    bestRows(end+1,:) = {names{p},subset.variant{best}, ...
        subset.mean_igd(best),subset.sample_std(best), ...
        subset.paper_igd(best),subset.relative_diff_percent(best)}; %#ok<SAGROW>
end
best = cell2table(bestRows,'VariableNames', ...
    {'problem','closest_variant','mean_igd','sample_std','paper_igd', ...
     'relative_diff_percent'});
writetable(best,fullfile(outputRoot,'best_by_problem.csv'));
disp(summary);
disp(ranking);
disp(best);

function writeSummary(outputRoot,rows)
    summary = cell2table(rows,'VariableNames',summaryNames());
    writetable(summary,fullfile(outputRoot,'summary_partial.csv'));
end

function names = summaryNames()
    names = {'variant','problem','M','D','N','maxFE','runs','paper_igd', ...
        'mean_igd','sample_std','signed_diff','abs_diff', ...
        'relative_diff_percent','mean_std'};
end
