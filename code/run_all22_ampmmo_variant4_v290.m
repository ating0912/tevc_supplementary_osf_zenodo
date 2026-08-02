% Full A-MPMO V4 all-22 run under unified baseline settings.
%
% Fixed baseline settings:
% N=100, maxFE=10000, seeds=1:30, PlatEMO v2.9 PF(10000), raw IGD.
%
% A-MPMO fixed paper settings:
% k=3, beta=0.2, delta/gamma=0.05,
% parameter groups [proC,proM] = [1,0.5], [1,1], [0.5,1].
%
% Variant 4:
% Later global survival, next contribution from offspring survivor count.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');
compatRoot = fullfile(scriptDir,'platemo_v43_compat');
metricCompatRoot = fullfile(scriptDir,'v290_metric_compat');
out = fullfile(scriptDir,'ampmmo_outputs','all22_v4_v290_fe10000_seed1_30');
if ~exist(out,'dir'); mkdir(out); end
progressFile = fullfile(out,'progress.log');

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

N = 100;
maxFE = 10000;
mode = 2;
variant = 4;
seeds = 1:30;
rows = {};

for p = 1:size(problems,1)
    name = problems{p,1};
    problemFcn = problems{p,2};
    M = problems{p,3};
    D = problems{p,4};
    paperMean = problems{p,5};
    problemDir = fullfile(out,name);
    if ~exist(problemDir,'dir'); mkdir(problemDir); end

    referenceGlobal = GLOBAL( ...
        '-algorithm', @NSGAII, '-problem', problemFcn, '-N', N, ...
        '-M', M, '-D', D, '-evaluation', maxFE, '-outputFcn', @(varargin)[] ...
    );
    PF = referenceGlobal.problem.PF(10000);

    igdValues = nan(numel(seeds),1);
    ndSizes = nan(numel(seeds),1);
    for r = 1:numel(seeds)
        seed = seeds(r);
        resultFile = fullfile(problemDir,sprintf('seed_%04d_igd.csv',seed));
        if exist(resultFile,'file')
            old = readtable(resultFile);
            igdValues(r) = old.igd(1);
            ndSizes(r) = old.feasible_nd_size(1);
            continue;
        end

        RandStream.setGlobalStream(RandStream('mcg16807','Seed',seed));
        Global = GLOBAL( ...
            '-algorithm', {@A_MPMO_NSGAII_v290,3,0.2,0.05,mode,variant}, ...
            '-problem', problemFcn, '-N', N, '-M', M, '-D', D, ...
            '-evaluation', maxFE, '-run', seed, '-outputFcn', @(varargin)[] ...
        );
        Global.Start();

        Population = Global.result{end,2};
        Obj = Population.objs;
        Obj = Obj(all(Population.cons <= 0,2),:);
        Obj = Obj(NDSort(Obj,1) == 1,:);
        igdValues(r) = IGD(Obj,PF);
        ndSizes(r) = size(Obj,1);
        writetable(table(seed,igdValues(r),ndSizes(r), ...
            'VariableNames',{'seed','igd','feasible_nd_size'}),resultFile);
        append_progress(progressFile,sprintf( ...
            'done %s seed %04d IGD %.12g ND %d', ...
            name,seed,igdValues(r),ndSizes(r)));
    end

    writetable(table(seeds',igdValues,ndSizes, ...
        'VariableNames',{'seed','igd','feasible_nd_size'}), ...
        fullfile(problemDir,'igd_runs.csv'));

    meanIgd = mean(igdValues);
    rows(end+1,:) = {name,M,D,N,maxFE,numel(seeds),seeds(1),seeds(end), ...
        paperMean,meanIgd,std(igdValues),meanIgd-paperMean, ...
        abs(meanIgd-paperMean),abs(meanIgd-paperMean)/abs(paperMean)*100, ...
        mean(ndSizes)}; %#ok<SAGROW>
    write_outputs(out,rows);
end

write_outputs(out,rows);
diary off;

function write_outputs(out,rows)
    T = cell2table(rows,'VariableNames',{ ...
        'problem','M','D','N','maxFE','runs','first_seed','last_seed', ...
        'paper_ampmmo_mean_igd','reproduced_mean_igd','reproduced_std_igd', ...
        'mean_signed_diff','mean_abs_diff','mean_relative_diff_percent', ...
        'mean_feasible_nd_size'});
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
    append_progress(fullfile(out,'progress.log'),sprintf( ...
        'summary problems=%d all_mean_rel=%.12g all_median_rel=%.12g', ...
        height(T),S.mean_relative_diff_percent(end), ...
        S.median_relative_diff_percent(end)));
end

function append_progress(progressFile,message)
    fid = fopen(progressFile,'a');
    fprintf(fid,'%s %s\n',datestr(now,'yyyy-mm-dd HH:MM:SS'),message);
    fclose(fid);
end
