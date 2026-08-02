% Quick smoke test for A_MPMO_NSGAII_v290 on the local PlatEMO v2.9 setup.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');
compatRoot = fullfile(scriptDir,'platemo_v43_compat');
metricCompatRoot = fullfile(scriptDir,'v290_metric_compat');
out = fullfile(scriptDir,'ampmmo_smoke_matlab_v290');
if ~exist(out,'dir'); mkdir(out); end

restoredefaultpath;
if exist(metricCompatRoot,'dir'); addpath(metricCompatRoot); end
addpath(genpath(platemoRoot));
addpath(compatRoot);
addpath(scriptDir);

problems = {
    'ZDT1', @ZDT1, 2, 30;
    'DTLZ2', @DTLZ2, 3, 12
};

rows = {};
for p = 1:size(problems,1)
    name = problems{p,1};
    problemFcn = problems{p,2};
    M = problems{p,3};
    D = problems{p,4};

    referenceGlobal = GLOBAL( ...
        '-algorithm', @NSGAII, '-problem', problemFcn, '-N', 100, ...
        '-M', M, '-D', D, '-evaluation', 1000, '-outputFcn', @(varargin)[] ...
    );
    PF = referenceGlobal.problem.PF(10000);

    for run = 1:2
        RandStream.setGlobalStream(RandStream('mcg16807','Seed',run));
        Global = GLOBAL( ...
            '-algorithm', @A_MPMO_NSGAII_v290, ...
            '-problem', problemFcn, '-N', 100, '-M', M, '-D', D, ...
            '-evaluation', 1000, '-run', run, '-outputFcn', @(varargin)[] ...
        );
        Global.Start();

        Population = Global.result{end,2};
        Obj = Population.objs;
        feasible = all(Population.cons <= 0,2);
        Obj = Obj(feasible,:);
        Obj = Obj(NDSort(Obj,1) == 1,:);
        value = IGD(Obj,PF);
        rows(end+1,:) = {name,M,D,run,value,size(Obj,1)}; %#ok<SAGROW>
        fprintf('%s run %02d IGD %.12g ND %d\n',name,run,value,size(Obj,1));
    end
end

T = cell2table(rows,'VariableNames',{'problem','M','D','seed','igd','feasible_nd_size'});
writetable(T,fullfile(out,'smoke_igd.csv'));
disp(T);
