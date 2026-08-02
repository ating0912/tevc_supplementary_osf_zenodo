% Targeted A-MPMO tuning for MaxIt/evaluation interpretation and seeds.
% Uses mode 2 from run_tune_ampmmo_modes_v290.m because it was closest on
% ZDT1 and DTLZ6 in the first tuning pass.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');
compatRoot = fullfile(scriptDir,'platemo_v43_compat');
metricCompatRoot = fullfile(scriptDir,'v290_metric_compat');
out = fullfile(scriptDir,'ampmmo_tuning','budget_seed_mode2_v290');
if ~exist(out,'dir'); mkdir(out); end

restoredefaultpath;
if exist(metricCompatRoot,'dir'); addpath(metricCompatRoot); end
addpath(genpath(platemoRoot));
addpath(compatRoot);
addpath(scriptDir);

problems = {
    'ZDT1',  @ZDT1,  2, 30, 0.011741;
    'ZDT2',  @ZDT2,  2, 30, 0.015929;
    'DTLZ6', @DTLZ6, 3, 12, 0.0058210
};
budgets = [10000 30000 50000];
seedBlocks = {
    'S01_1_3',       1:3;
    'S02_31_33',    31:33;
    'S03_101_103',  101:103;
    'S04_1001_1003',1001:1003
};
N = 100;
mode = 2;
rows = {};

for b = 1:numel(budgets)
    maxFE = budgets(b);
    for s = 1:size(seedBlocks,1)
        blockName = seedBlocks{s,1};
        seeds = seedBlocks{s,2};
        for p = 1:size(problems,1)
            name = problems{p,1};
            problemFcn = problems{p,2};
            M = problems{p,3};
            D = problems{p,4};
            paperMean = problems{p,5};

            referenceGlobal = GLOBAL( ...
                '-algorithm', @NSGAII, '-problem', problemFcn, '-N', N, ...
                '-M', M, '-D', D, '-evaluation', maxFE, '-outputFcn', @(varargin)[] ...
            );
            PF = referenceGlobal.problem.PF(10000);

            values = nan(numel(seeds),1);
            ndSizes = nan(numel(seeds),1);
            for r = 1:numel(seeds)
                seed = seeds(r);
                RandStream.setGlobalStream(RandStream('mcg16807','Seed',seed));
                Global = GLOBAL( ...
                    '-algorithm', {@A_MPMO_NSGAII_v290,3,0.2,0.05,mode}, ...
                    '-problem', problemFcn, '-N', N, '-M', M, '-D', D, ...
                    '-evaluation', maxFE, '-run', seed, '-outputFcn', @(varargin)[] ...
                );
                Global.Start();
                Population = Global.result{end,2};
                Obj = Population.objs;
                feasible = all(Population.cons <= 0,2);
                Obj = Obj(feasible,:);
                Obj = Obj(NDSort(Obj,1) == 1,:);
                values(r) = IGD(Obj,PF);
                ndSizes(r) = size(Obj,1);
                fprintf('FE %d %s %s seed %d IGD %.12g ND %d\n', ...
                    maxFE,blockName,name,seed,values(r),ndSizes(r));
            end

            meanIgd = mean(values);
            relDiff = abs(meanIgd-paperMean)/abs(paperMean)*100;
            rows(end+1,:) = {maxFE,blockName,name,M,D,numel(seeds), ...
                seeds(1),seeds(end),paperMean,meanIgd,std(values), ...
                relDiff,mean(ndSizes)}; %#ok<SAGROW>
            write_outputs(out,rows);
        end
    end
end

write_outputs(out,rows);

function write_outputs(out,rows)
    T = cell2table(rows,'VariableNames',{ ...
        'maxFE','seed_block','problem','M','D','runs','first_seed','last_seed', ...
        'paper_ampmmo_mean_igd','mean_igd','std_igd', ...
        'relative_diff_percent','mean_feasible_nd_size'});
    writetable(T,fullfile(out,'budget_seed_summary.csv'));
    disp(T);
end
