% Compare fixed-per-run P1 with three continuous batch RNG workflows.

clear; clc;
root = fileparts(mfilename('fullpath'));
outputRoot = fullfile(root,'nsga2_outputs','v290_sequential_rng_diagnostic');
if ~exist(outputRoot,'dir'); mkdir(outputRoot); end

restoredefaultpath;
addpath(fullfile(root,'v290_metric_compat'));
addpath(genpath(fullfile(root,'PlatEMO_v2.9.0','PlatEMO')));
addpath(fullfile(root,'platemo_v43_compat'));
addpath(root);

problems = {
    'DTLZ1',@DTLZ1,3, 7,0.23828,0.443;
    'DTLZ4',@DTLZ4,3,12,0.40388,0.313;
    'ZDT2', @ZDT2, 2,30,0.50813,0.0879;
    'ZDT4', @ZDT4, 2,10,0.53146,0.251;
    'UF6',  @UF6,  2,30,0.5948,0.270;
    'UF10', @UF10, 3,30,0.74415,0.0993;
};
variants = {
    'S3_native_inherited', 'inherited_whole_batch';
    'S0_fixed_run_twister','fixed';
    'S1_default_once',     'default_each_problem';
    'S2_shuffle_once',     'shuffle_each_problem';
};

rows = {};
for v = 1:size(variants,1)
    variant = variants{v,1};
    mode = variants{v,2};
    variantDir = fullfile(outputRoot,variant);
    if ~exist(variantDir,'dir'); mkdir(variantDir); end

    if strcmp(mode,'inherited_whole_batch')
        initialState = rng;
        save(fullfile(variantDir,'initial_rng_state.mat'),'initialState');
    end

    for p = 1:size(problems,1)
        name = problems{p,1};
        problemFcn = problems{p,2};
        M = problems{p,3};
        D = problems{p,4};
        paperMean = problems{p,5};
        paperStd = problems{p,6};
        problemDir = fullfile(variantDir,name);
        if ~exist(problemDir,'dir'); mkdir(problemDir); end

        referenceGlobal = GLOBAL('-algorithm',@NSGAII,'-problem',problemFcn, ...
            '-N',100,'-M',M,'-D',D,'-evaluation',10000, ...
            '-outputFcn',@(varargin)[]);
        PF = referenceGlobal.problem.PF(10000);

        if strcmp(mode,'default_each_problem')
            rng('default');
            initialState = rng;
            save(fullfile(problemDir,'initial_rng_state.mat'),'initialState');
        elseif strcmp(mode,'shuffle_each_problem')
            rng('shuffle');
            initialState = rng;
            save(fullfile(problemDir,'initial_rng_state.mat'),'initialState');
        end

        values = nan(30,1);
        for run = 1:30
            resultFile = fullfile(problemDir,sprintf('run_%03d.csv',run));
            if strcmp(mode,'fixed') && exist(resultFile,'file')
                old = readtable(resultFile);
                values(run) = old.igd(1);
                continue;
            end

            if strcmp(mode,'fixed')
                baseline = fullfile(root,'nsga2_outputs','paper_four_seeded', ...
                    'P1',name,sprintf('run_%03d',run),'igd.csv');
                old = readtable(baseline);
                values(run) = old.igd(1);
            else
                Global = GLOBAL('-algorithm',@NSGAII,'-problem',problemFcn, ...
                    '-N',100,'-M',M,'-D',D,'-evaluation',10000, ...
                    '-run',run,'-outputFcn',@(varargin)[]);
                Global.Start();
                Population = Global.result{end,2};
                Obj = Population.objs;
                feasible = all(Population.cons<=0,2);
                Obj = Obj(feasible,:);
                Obj = Obj(NDSort(Obj,1)==1,:);
                values(run) = IGD(Obj,PF);
                stateAfterRun = rng;
                save(fullfile(problemDir,sprintf('rng_after_run_%03d.mat',run)), ...
                    'stateAfterRun');
            end
            writetable(table(run,values(run),'VariableNames',{'run','igd'}), ...
                resultFile);
            fprintf('%s %s run=%02d IGD=%.12g\n', ...
                variant,name,run,values(run));
        end

        meanIGD = mean(values);
        sampleStd = std(values);
        meanRelativeDiff = abs(meanIGD-paperMean)/paperMean*100;
        stdRelativeDiff = abs(sampleStd-paperStd)/paperStd*100;
        rows(end+1,:) = {variant,mode,name,M,D,30,paperMean,paperStd, ...
            meanIGD,sampleStd,meanIGD-paperMean,sampleStd-paperStd, ...
            meanRelativeDiff,stdRelativeDiff, ...
            sprintf('%.4e (%.4e)',meanIGD,sampleStd)}; %#ok<SAGROW>
        writetable(table((1:30)',values,'VariableNames',{'run','igd'}), ...
            fullfile(problemDir,'igd_runs.csv'));
        writeOutputs(outputRoot,rows);
    end
end
writeOutputs(outputRoot,rows);

function writeOutputs(outputRoot,rows)
    names = {'variant','rng_mode','problem','M','D','runs','paper_mean', ...
        'paper_std','mean_igd','sample_std','mean_signed_diff', ...
        'std_signed_diff','mean_relative_diff_percent', ...
        'std_relative_diff_percent','mean_std'};
    T = cell2table(rows,'VariableNames',names);
    writetable(T,fullfile(outputRoot,'summary.csv'));
    R = groupsummary(T,'variant',{'mean','median'}, ...
        {'mean_relative_diff_percent','std_relative_diff_percent'});
    R = sortrows(R,'mean_mean_relative_diff_percent');
    writetable(R,fullfile(outputRoot,'ranking.csv'));
end
