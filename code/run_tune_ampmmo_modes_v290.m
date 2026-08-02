% Targeted A-MPMO tuning for unspecified implementation choices.
%
% Paper-fixed settings are kept unchanged:
% N=100, maxFE=10000, k=3, beta=0.2, delta/gamma=0.05,
% parameter groups [proC,proM] = [1,0.5], [1,1], [0.5,1],
% etaC=20, etaM=20.
%
% Tested choice:
% mode 1 = later global environmental selection with skill floor
% mode 2 = later global environmental selection without forced skill floor
% mode 3 = later subpopulation-local environmental selection

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');
compatRoot = fullfile(scriptDir,'platemo_v43_compat');
metricCompatRoot = fullfile(scriptDir,'v290_metric_compat');
out = fullfile(scriptDir,'ampmmo_tuning','modes_v290_3runs');
if ~exist(out,'dir'); mkdir(out); end

restoredefaultpath;
if exist(metricCompatRoot,'dir'); addpath(metricCompatRoot); end
addpath(genpath(platemoRoot));
addpath(compatRoot);
addpath(scriptDir);

problems = {
    'ZDT1',  @ZDT1,  2, 30, 0.011741;
    'ZDT2',  @ZDT2,  2, 30, 0.015929;
    'DTLZ6', @DTLZ6, 3, 12, 0.0058210;
    'UF1',   @UF1,   2, 30, 0.10239;
    'UF10',  @UF10,  3, 30, 1.3364
};
modes = [1 2 3];
runs = 1:3;
N = 100;
maxFE = 10000;

rows = {};
for m = 1:numel(modes)
    mode = modes(m);
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

        values = nan(numel(runs),1);
        ndSizes = nan(numel(runs),1);
        for r = 1:numel(runs)
            seed = runs(r);
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
            fprintf('mode %d %s seed %d IGD %.12g ND %d\n', ...
                mode,name,seed,values(r),ndSizes(r));
        end

        meanIgd = mean(values);
        relDiff = abs(meanIgd-paperMean)/abs(paperMean)*100;
        rows(end+1,:) = {mode,name,M,D,numel(runs),paperMean,meanIgd, ...
            std(values),relDiff,mean(ndSizes)}; %#ok<SAGROW>
        write_outputs(out,rows);
    end
end

write_outputs(out,rows);

function write_outputs(out,rows)
    T = cell2table(rows,'VariableNames',{ ...
        'mode','problem','M','D','runs','paper_ampmmo_mean_igd', ...
        'mean_igd','std_igd','relative_diff_percent','mean_feasible_nd_size'});
    writetable(T,fullfile(out,'mode_tuning_summary.csv'));
    disp(T);
end
