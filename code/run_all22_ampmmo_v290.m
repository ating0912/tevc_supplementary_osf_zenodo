% Reproduce A-MPMO on the 22 benchmark problems from Zhao et al. (2025).
%
% Settings are aligned with NSGAII_baseline_reproduction_parameters.docx:
% MATLAB R2020b, PlatEMO v2.9, N=100, maxFE=10000, 30 runs, mcg16807,
% feasible non-dominated final set, PlatEMO native PF(10000), raw IGD.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');
compatRoot = fullfile(scriptDir,'platemo_v43_compat');
metricCompatRoot = fullfile(scriptDir,'v290_metric_compat');

baseOut = fullfile(scriptDir,'ampmmo_outputs','all22_v290_mcg_randomtie');
out = baseOut;
suffix = 1;
while exist(out,'dir')
    suffix = suffix + 1;
    out = sprintf('%s_%02d',baseOut,suffix);
end
mkdir(out);

diary(fullfile(out,'run.log'));
fprintf('MATLAB version: %s\n',version);
fprintf('MATLAB release: %s\n',version('-release'));
fprintf('Output workspace: %s\n',out);

restoredefaultpath;
if exist(metricCompatRoot,'dir'); addpath(metricCompatRoot); end
addpath(genpath(platemoRoot));
addpath(compatRoot);
addpath(scriptDir);

problems = {
    'DTLZ1', @DTLZ1, 3,  7, 0.10161;
    'DTLZ2', @DTLZ2, 3, 12, 0.067842;
    'DTLZ3', @DTLZ3, 3, 12, 9.0840;
    'DTLZ4', @DTLZ4, 3, 12, 0.083231;
    'DTLZ5', @DTLZ5, 3, 12, 0.0057991;
    'DTLZ6', @DTLZ6, 3, 12, 0.0058210;
    'DTLZ7', @DTLZ7, 3, 22, 0.11112;
    'ZDT1',  @ZDT1,  2, 30, 0.011741;
    'ZDT2',  @ZDT2,  2, 30, 0.015929;
    'ZDT3',  @ZDT3,  2, 30, 0.020728;
    'ZDT4',  @ZDT4,  2, 10, 0.14880;
    'ZDT6',  @ZDT6,  2, 10, 0.032087;
    'UF1',   @UF1,   2, 30, 0.10239;
    'UF2',   @UF2,   2, 30, 0.057116;
    'UF3',   @UF3,   2, 30, 0.30983;
    'UF4',   @UF4,   2, 30, 0.075443;
    'UF5',   @UF5,   2, 30, 0.73566;
    'UF6',   @UF6,   2, 30, 0.33528;
    'UF7',   @UF7,   2, 30, 0.078538;
    'UF8',   @UF8,   3, 30, 0.27935;
    'UF9',   @UF9,   3, 30, 0.38723;
    'UF10',  @UF10,  3, 30, 1.3364
};

rows = {};
for p = 1:size(problems,1)
    name = problems{p,1};
    problemFcn = problems{p,2};
    M = problems{p,3};
    D = problems{p,4};
    paperMean = problems{p,5};

    problemDir = fullfile(out,name);
    mkdir(problemDir);

    referenceGlobal = GLOBAL( ...
        '-algorithm', @NSGAII, '-problem', problemFcn, '-N', 100, ...
        '-M', M, '-D', D, '-evaluation', 10000, '-outputFcn', @(varargin)[] ...
    );
    PF = referenceGlobal.problem.PF(10000);

    igdValues = nan(30,1);
    ndSizes = nan(30,1);
    for run = 1:30
        RandStream.setGlobalStream(RandStream('mcg16807','Seed',run));
        Global = GLOBAL( ...
            '-algorithm', @A_MPMO_NSGAII_v290, ...
            '-problem', problemFcn, '-N', 100, '-M', M, '-D', D, ...
            '-evaluation', 10000, '-run', run, '-outputFcn', @(varargin)[] ...
        );
        Global.Start();

        Population = Global.result{end,2};
        Obj = Population.objs;
        Dec = Population.decs;
        feasible = all(Population.cons <= 0,2);
        ObjFeasible = Obj(feasible,:);
        nd = NDSort(ObjFeasible,1) == 1;
        ObjReported = ObjFeasible(nd,:);

        igdValues(run) = IGD(ObjReported,PF);
        ndSizes(run) = size(ObjReported,1);

        runDir = fullfile(problemDir,sprintf('run_%03d',run));
        mkdir(runDir);
        writematrix(Obj,fullfile(runDir,'obj_final_population.csv'));
        writematrix(Dec,fullfile(runDir,'dec_final_population.csv'));
        writematrix(ObjReported,fullfile(runDir,'obj_feasible_nd.csv'));
        writetable(table(run,igdValues(run),ndSizes(run), ...
            'VariableNames',{'seed','igd','feasible_nd_size'}), ...
            fullfile(runDir,'igd.csv'));

        fprintf('%s run %02d IGD %.12g ND %d\n', ...
            name,run,igdValues(run),ndSizes(run));
    end

    writetable(table((1:30)',igdValues,ndSizes, ...
        'VariableNames',{'seed','igd','feasible_nd_size'}), ...
        fullfile(problemDir,'igd_runs.csv'));

    meanIgd = mean(igdValues);
    stdIgd = std(igdValues);
    rows(end+1,:) = {name,M,D,100,10000,30,paperMean,meanIgd,stdIgd, ...
        meanIgd-paperMean,abs(meanIgd-paperMean), ...
        abs(meanIgd-paperMean)/abs(paperMean)*100,mean(ndSizes)}; %#ok<SAGROW>
    write_outputs(out,rows);
end

write_outputs(out,rows);
diary off;

function write_outputs(out,rows)
    T = cell2table(rows,'VariableNames',{ ...
        'problem','M','D','N','maxFE','runs','paper_ampmmo_mean_igd', ...
        'reproduced_mean_igd','reproduced_std_igd','mean_signed_diff', ...
        'mean_abs_diff','mean_relative_diff_percent','mean_feasible_nd_size'});
    writetable(T,fullfile(out,'comparison_table.csv'));

    familyRows = {};
    families = {'DTLZ','ZDT','UF'};
    for i = 1:numel(families)
        mask = startsWith(T.problem,families{i});
        familyRows(end+1,:) = {families{i},sum(mask), ...
            mean(T.mean_relative_diff_percent(mask)), ...
            median(T.mean_relative_diff_percent(mask))}; %#ok<AGROW>
    end
    familyRows(end+1,:) = {'ALL',height(T), ...
        mean(T.mean_relative_diff_percent), ...
        median(T.mean_relative_diff_percent)}; %#ok<AGROW>
    S = cell2table(familyRows,'VariableNames', ...
        {'family','problem_count','mean_relative_diff_percent', ...
         'median_relative_diff_percent'});
    writetable(S,fullfile(out,'relative_diff_summary.csv'));
    disp(T);
    disp(S);
end
