% Tune only A-MPMO internal interpretation variants.
%
% Fixed baseline parameters:
% N=100, maxFE=10000, seeds=1:5, PlatEMO v2.9 PF(10000), raw IGD.
%
% Variant definitions in A_MPMO_NSGAII_v290:
% V1 = later global survival, no forced skill floor
% V2 = later local survival, offspring count follows NP_i
% V3 = later local survival, offspring count follows current subpopulation size
% V4 = later global survival, next contribution from offspring survivor count

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');
compatRoot = fullfile(scriptDir,'platemo_v43_compat');
metricCompatRoot = fullfile(scriptDir,'v290_metric_compat');
out = fullfile(scriptDir,'ampmmo_tuning','internal_variants_v290_fe10000_5runs');
if ~exist(out,'dir'); mkdir(out); end

progressFile = fullfile(out,'progress.log');
restoredefaultpath;
if exist(metricCompatRoot,'dir'); addpath(metricCompatRoot); end
addpath(genpath(platemoRoot));
addpath(compatRoot);
addpath(scriptDir);

problems = {
    'DTLZ1', @DTLZ1, 3,  7, 0.10161;
    'DTLZ6', @DTLZ6, 3, 12, 0.0058210;
    'ZDT1',  @ZDT1,  2, 30, 0.011741;
    'ZDT2',  @ZDT2,  2, 30, 0.015929;
    'UF7',   @UF7,   2, 30, 0.078538;
    'UF10',  @UF10,  3, 30, 1.3364
};

variants = 1:4;
seeds = 1:5;
N = 100;
maxFE = 10000;
mode = 2;
rows = {};

for v = variants
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
            resultDir = fullfile(out,sprintf('V%d',v),name,sprintf('seed_%04d',seed));
            resultFile = fullfile(resultDir,'igd.csv');
            if exist(resultFile,'file')
                old = readtable(resultFile);
                values(r) = old.igd(1);
                ndSizes(r) = old.feasible_nd_size(1);
                continue;
            end
            if ~exist(resultDir,'dir'); mkdir(resultDir); end

            RandStream.setGlobalStream(RandStream('mcg16807','Seed',seed));
            Global = GLOBAL( ...
                '-algorithm', {@A_MPMO_NSGAII_v290,3,0.2,0.05,mode,v}, ...
                '-problem', problemFcn, '-N', N, '-M', M, '-D', D, ...
                '-evaluation', maxFE, '-run', seed, '-outputFcn', @(varargin)[] ...
            );
            Global.Start();

            Population = Global.result{end,2};
            Obj = Population.objs;
            Obj = Obj(all(Population.cons <= 0,2),:);
            Obj = Obj(NDSort(Obj,1) == 1,:);
            values(r) = IGD(Obj,PF);
            ndSizes(r) = size(Obj,1);
            writetable(table(seed,values(r),ndSizes(r), ...
                'VariableNames',{'seed','igd','feasible_nd_size'}),resultFile);
            append_progress(progressFile,sprintf( ...
                'done V%d %s seed %04d IGD %.12g ND %d', ...
                v,name,seed,values(r),ndSizes(r)));
        end

        meanIgd = mean(values);
        rows(end+1,:) = {v,name,M,D,N,maxFE,numel(seeds), ...
            paperMean,meanIgd,std(values), ...
            abs(meanIgd-paperMean)/abs(paperMean)*100,mean(ndSizes)}; %#ok<SAGROW>
        write_outputs(out,rows);
    end
end

write_outputs(out,rows);

function write_outputs(out,rows)
    T = cell2table(rows,'VariableNames',{ ...
        'variant','problem','M','D','N','maxFE','runs', ...
        'paper_ampmmo_mean_igd','mean_igd','std_igd', ...
        'relative_diff_percent','mean_feasible_nd_size'});
    writetable(T,fullfile(out,'variant_summary.csv'));

    variants = unique(T.variant);
    rankRows = {};
    for i = 1:numel(variants)
        mask = T.variant == variants(i);
        rankRows(end+1,:) = {variants(i),sum(mask), ...
            mean(T.relative_diff_percent(mask)), ...
            median(T.relative_diff_percent(mask))}; %#ok<AGROW>
    end
    R = cell2table(rankRows,'VariableNames', ...
        {'variant','problem_count','mean_relative_diff_percent', ...
         'median_relative_diff_percent'});
    R = sortrows(R,'mean_relative_diff_percent');
    writetable(R,fullfile(out,'variant_ranking.csv'));
end

function append_progress(progressFile,message)
    fid = fopen(progressFile,'a');
    fprintf(fid,'%s %s\n',datestr(now,'yyyy-mm-dd HH:MM:SS'),message);
    fclose(fid);
end
