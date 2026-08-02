% Diagnose IGD reference-set and reported-population conventions on the
% existing PlatEMO v2.9 / MATLAB R2020b NSGA-II runs.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');
compatRoot = fullfile(scriptDir,'platemo_v43_compat');
outputRoot = fullfile(scriptDir,'nsga2_outputs','v290_all22_diagnostics');
if ~exist(outputRoot,'dir'); mkdir(outputRoot); end

restoredefaultpath;
addpath(genpath(platemoRoot));
addpath(compatRoot);

problems = {
    'ZDT1', @ZDT1, 2, 30, 0.14621, 'platemo_v290_zdt_seeded_r2020b';
    'ZDT2', @ZDT2, 2, 30, 0.50813, 'platemo_v290_zdt_seeded_r2020b';
    'ZDT3', @ZDT3, 2, 30, 0.17787, 'platemo_v290_zdt_seeded_r2020b';
    'ZDT4', @ZDT4, 2, 10, 0.53146, 'platemo_v290_zdt_seeded_r2020b';
    'ZDT6', @ZDT6, 2, 10, 0.07429, 'platemo_v290_zdt_seeded_r2020b';
    'DTLZ1',@DTLZ1,3, 7, 0.23828, 'platemo_v290_dtlz1_7_seeded_r2020b';
    'DTLZ2',@DTLZ2,3,12, 0.054881,'platemo_v290_dtlz1_7_seeded_r2020b';
    'DTLZ3',@DTLZ3,3,12,13.357,  'platemo_v290_dtlz1_7_seeded_r2020b';
    'DTLZ4',@DTLZ4,3,12, 0.40388, 'platemo_v290_dtlz1_7_seeded_r2020b';
    'DTLZ5',@DTLZ5,3,12, 0.032473,'platemo_v290_dtlz1_7_seeded_r2020b';
    'DTLZ6',@DTLZ6,3,12, 0.11635, 'platemo_v290_dtlz1_7_seeded_r2020b';
    'DTLZ7',@DTLZ7,3,22, 0.1708,  'platemo_v290_dtlz1_7_seeded_r2020b';
    'UF1',  @UF1,  2,30, 0.31352, 'platemo_v290_uf1_5_seeded_r2020b';
    'UF2',  @UF2,  2,30, 0.21196, 'platemo_v290_uf1_5_seeded_r2020b';
    'UF3',  @UF3,  2,30, 0.33463, 'platemo_v290_uf1_5_seeded_r2020b';
    'UF4',  @UF4,  2,30, 0.12713, 'platemo_v290_uf1_5_seeded_r2020b';
    'UF5',  @UF5,  2,30, 1.3074,  'platemo_v290_uf1_5_seeded_r2020b';
    'UF6',  @UF6,  2,30, 0.5948,  'platemo_v290_uf6_10_seeded_r2020b';
    'UF7',  @UF7,  2,30, 0.43887, 'platemo_v290_uf6_10_seeded_r2020b';
    'UF8',  @UF8,  3,30, 0.58545, 'platemo_v290_uf6_10_seeded_r2020b';
    'UF9',  @UF9,  3,30, 0.52501, 'platemo_v290_uf6_10_seeded_r2020b';
    'UF10', @UF10, 3,30, 0.74415, 'platemo_v290_uf6_10_seeded_r2020b';
};

pointCounts = [100,1000,10000];
summaryRows = {};
runRows = {};

for p = 1:size(problems,1)
    name = problems{p,1};
    problemFcn = problems{p,2};
    M = problems{p,3};
    D = problems{p,4};
    paper = problems{p,5};
    inputRoot = fullfile(scriptDir,'nsga2_outputs',problems{p,6},name);
    Global = GLOBAL('-algorithm',@NSGAII,'-problem',problemFcn, ...
        '-N',100,'-M',M,'-D',D,'-evaluation',10000, ...
        '-outputFcn',@(varargin)[]);

    PFs = cell(1,length(pointCounts));
    actualPoints = zeros(1,length(pointCounts));
    for q = 1:length(pointCounts)
        PFs{q} = Global.problem.PF(pointCounts(q));
        actualPoints(q) = size(PFs{q},1);
    end

    variants = {};
    for q = 1:length(pointCounts)
        variants(end+1,:) = {sprintf('nativePF_%d_full',pointCounts(q)),q,'full','igd'}; %#ok<SAGROW>
        variants(end+1,:) = {sprintf('nativePF_%d_nd',pointCounts(q)),q,'nd','igd'}; %#ok<SAGROW>
    end
    variants(end+1,:) = {'nativePF_10000_swapped',3,'nd','swapped'}; %#ok<SAGROW>

    values = nan(30,size(variants,1));
    ndSizes = nan(30,1);
    for run = 1:30
        objFile = fullfile(inputRoot,sprintf('run_%03d',run),'obj.csv');
        if ~exist(objFile,'file')
            error('Missing saved population: %s',objFile);
        end
        Obj = readmatrix(objFile);
        FrontNo = NDSort(Obj,1);
        NDObj = Obj(FrontNo==1,:);
        ndSizes(run) = size(NDObj,1);

        for v = 1:size(variants,1)
            pfIndex = variants{v,2};
            if strcmp(variants{v,3},'nd')
                reported = NDObj;
            else
                reported = Obj;
            end
            if strcmp(variants{v,4},'swapped')
                score = directedMeanDistance(PFs{pfIndex},reported);
            else
                score = directedMeanDistance(reported,PFs{pfIndex});
            end
            values(run,v) = score;
            runRows(end+1,:) = {name,run,variants{v,1},actualPoints(pfIndex), ...
                size(reported,1),score}; %#ok<SAGROW>
        end
    end

    for v = 1:size(variants,1)
        meanValue = mean(values(:,v));
        stdValue = std(values(:,v));
        summaryRows(end+1,:) = {name,M,D,paper,variants{v,1}, ...
            actualPoints(variants{v,2}),mean(ndSizes),30,meanValue,stdValue, ...
            meanValue-paper,abs(meanValue-paper),abs(meanValue-paper)/paper*100}; %#ok<SAGROW>
    end
    fprintf('%s diagnostics complete\n',name);
end

runTable = cell2table(runRows,'VariableNames', ...
    {'problem','seed','variant','pf_points','reported_points','igd'});
writetable(runTable,fullfile(outputRoot,'runs.csv'));

summary = cell2table(summaryRows,'VariableNames', ...
    {'problem','M','D','paper_igd','variant','pf_points','mean_nd_size', ...
     'runs','mean_igd','sample_std','signed_diff','abs_diff','relative_diff_percent'});
writetable(summary,fullfile(outputRoot,'summary.csv'));

variants = unique(summary.variant,'stable');
rankRows = {};
for v = 1:length(variants)
    selected = summary(strcmp(summary.variant,variants{v}),:);
    rankRows(end+1,:) = {variants{v},height(selected), ...
        mean(selected.relative_diff_percent),median(selected.relative_diff_percent), ...
        sum(isClosest(summary,variants{v}))}; %#ok<SAGROW>
end
ranking = cell2table(rankRows,'VariableNames', ...
    {'variant','problems','mean_relative_diff_percent', ...
     'median_relative_diff_percent','closest_wins'});
ranking = sortrows(ranking,'mean_relative_diff_percent');
writetable(ranking,fullfile(outputRoot,'ranking.csv'));

winnerRows = {};
problemNames = unique(summary.problem,'stable');
for i = 1:length(problemNames)
    selected = summary(strcmp(summary.problem,problemNames{i}),:);
    [~,best] = min(selected.abs_diff);
    winnerRows(end+1,:) = {problemNames{i},selected.paper_igd(best), ...
        selected.variant{best},selected.mean_igd(best),selected.sample_std(best), ...
        selected.abs_diff(best),selected.relative_diff_percent(best)}; %#ok<SAGROW>
end
winners = cell2table(winnerRows,'VariableNames', ...
    {'problem','paper_igd','closest_variant','mean_igd','sample_std', ...
     'abs_diff','relative_diff_percent'});
writetable(winners,fullfile(outputRoot,'problem_winners.csv'));

disp(ranking);
disp(winners);

function score = directedMeanDistance(approximation,reference)
    distances = inf(size(reference,1),1);
    for i = 1:size(approximation,1)
        delta = reference-approximation(i,:);
        distances = min(distances,sqrt(sum(delta.*delta,2)));
    end
    score = mean(distances);
end

function flags = isClosest(summary,variant)
    flags = false(height(summary),1);
    problemNames = unique(summary.problem,'stable');
    for i = 1:length(problemNames)
        indices = find(strcmp(summary.problem,problemNames{i}));
        [~,best] = min(summary.abs_diff(indices));
        winner = indices(best);
        flags(winner) = strcmp(summary.variant{winner},variant);
    end
end
