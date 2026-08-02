% Test interactions between RNG generators and tournament implementations.

clear; clc;
root = fileparts(mfilename('fullpath'));
outputRoot = fullfile(root,'nsga2_outputs','v290_rng_tournament_interaction');
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
    'I1_twister_native',       @NSGAII,                         'twister';
    'I2_mcg_dual_rank',        @NSGAII_DualPermutationRank_v290,'mcg16807';
    'I3_mcg_random_tie',       @NSGAII_RandomTie_v290,          'mcg16807';
    'I4_dsfmt_dual_rank',      @NSGAII_DualPermutationRank_v290,'dsfmt19937';
};

rows = {};
for v = 1:size(variants,1)
    variant = variants{v,1};
    algorithm = variants{v,2};
    generator = variants{v,3};
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
            resultFile = fullfile(problemDir,sprintf('run_%03d.csv',run));
            if exist(resultFile,'file')
                old = readtable(resultFile);
                values(run) = old.igd(1);
                continue;
            end
            setGenerator(generator,run);
            Global = GLOBAL('-algorithm',algorithm,'-problem',problemFcn, ...
                '-N',100,'-M',M,'-D',D,'-evaluation',10000, ...
                '-run',run,'-outputFcn',@(varargin)[]);
            Global.Start();
            Population = Global.result{end,2};
            Obj = Population.objs;
            feasible = all(Population.cons<=0,2);
            Obj = Obj(feasible,:);
            Obj = Obj(NDSort(Obj,1)==1,:);
            values(run) = IGD(Obj,PF);
            writetable(table(run,values(run),'VariableNames',{'seed','igd'}), ...
                resultFile);
            fprintf('%s %s run=%02d IGD=%.12g\n', ...
                variant,name,run,values(run));
        end
        meanIGD = mean(values);
        sampleStd = std(values);
        relativeDiff = abs(meanIGD-paperIGD)/paperIGD*100;
        rows(end+1,:) = {variant,generator,name,M,D,30,paperIGD,meanIGD, ...
            sampleStd,meanIGD-paperIGD,abs(meanIGD-paperIGD),relativeDiff, ...
            sprintf('%.4e (%.4e)',meanIGD,sampleStd)}; %#ok<SAGROW>
        writetable(table((1:30)',values,'VariableNames',{'seed','igd'}), ...
            fullfile(problemDir,'igd_runs.csv'));
        writeOutputs(outputRoot,rows);
    end
end
writeOutputs(outputRoot,rows);

function setGenerator(name,seed)
    if strcmp(name,'twister')
        rng(seed,'twister');
    else
        RandStream.setGlobalStream(RandStream(name,'Seed',seed));
    end
end

function writeOutputs(outputRoot,rows)
    names = {'variant','generator','problem','M','D','runs','paper_igd', ...
        'mean_igd','sample_std','signed_diff','abs_diff', ...
        'relative_diff_percent','mean_std'};
    T = cell2table(rows,'VariableNames',names);
    writetable(T,fullfile(outputRoot,'summary.csv'));
    R = groupsummary(T,'variant',{'mean','median'}, ...
        'relative_diff_percent');
    R = sortrows(R,'mean_relative_diff_percent');
    writetable(R,fullfile(outputRoot,'ranking.csv'));
end
