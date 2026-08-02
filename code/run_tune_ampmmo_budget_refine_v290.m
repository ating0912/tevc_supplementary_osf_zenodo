% Refined budget sweep for A-MPMO mode 2.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');
compatRoot = fullfile(scriptDir,'platemo_v43_compat');
metricCompatRoot = fullfile(scriptDir,'v290_metric_compat');
out = fullfile(scriptDir,'ampmmo_tuning','budget_refine_mode2_v290');
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
budgets = [12000 15000 20000];
seedBlocks = {
    'S01_1_3',    1:3;
    'S02_31_33', 31:33
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
                Obj = Obj(all(Population.cons <= 0,2),:);
                Obj = Obj(NDSort(Obj,1) == 1,:);
                values(r) = IGD(Obj,PF);
                fprintf('FE %d %s %s seed %d IGD %.12g\n', ...
                    maxFE,blockName,name,seed,values(r));
            end
            meanIgd = mean(values);
            rows(end+1,:) = {maxFE,blockName,name,M,D,numel(seeds), ...
                paperMean,meanIgd,std(values), ...
                abs(meanIgd-paperMean)/abs(paperMean)*100}; %#ok<SAGROW>
            write_outputs(out,rows);
        end
    end
end

write_outputs(out,rows);

function write_outputs(out,rows)
    T = cell2table(rows,'VariableNames',{ ...
        'maxFE','seed_block','problem','M','D','runs','paper_ampmmo_mean_igd', ...
        'mean_igd','std_igd','relative_diff_percent'});
    writetable(T,fullfile(out,'budget_refine_summary.csv'));
    disp(T);
end
