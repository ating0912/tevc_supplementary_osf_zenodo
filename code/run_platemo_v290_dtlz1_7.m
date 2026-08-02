% Run PlatEMO v2.9.0 NSGA-II on DTLZ1-DTLZ7 with fixed seeds.

clear; clc;
scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');
outputRoot = fullfile(scriptDir,'nsga2_outputs','platemo_v290_dtlz1_7_seeded_r2020b');
pfRoot = fullfile(scriptDir,'dtlz_reference_v43');
if ~exist(outputRoot,'dir'); mkdir(outputRoot); end
restoredefaultpath;
addpath(genpath(platemoRoot));
addpath(fullfile(scriptDir,'platemo_v43_compat'));

problems = {
    'DTLZ1', @DTLZ1, 7,  0.23828;
    'DTLZ2', @DTLZ2, 12, 0.054881;
    'DTLZ3', @DTLZ3, 12, 13.357;
    'DTLZ4', @DTLZ4, 12, 0.40388;
    'DTLZ5', @DTLZ5, 12, 0.032473;
    'DTLZ6', @DTLZ6, 12, 0.11635;
    'DTLZ7', @DTLZ7, 22, 0.1708;
};
summaryRows = {};

for p = 1:size(problems,1)
    name = problems{p,1}; problemFcn = problems{p,2};
    D = problems{p,3}; paper = problems{p,4};
    problemDir = fullfile(outputRoot,name);
    if ~exist(problemDir,'dir'); mkdir(problemDir); end
    PF = readmatrix(fullfile(pfRoot,[name,'.csv']));
    values = nan(30,1);
    for run = 1:30
        runDir = fullfile(problemDir,sprintf('run_%03d',run));
        igdFile = fullfile(runDir,'igd.csv');
        if exist(igdFile,'file')
            old = readmatrix(igdFile); values(run) = old(1,2); continue;
        end
        if ~exist(runDir,'dir'); mkdir(runDir); end
        rng(run,'twister');
        Global = GLOBAL('-algorithm',@NSGAII,'-problem',problemFcn, ...
            '-N',100,'-M',3,'-D',D,'-evaluation',10000, ...
            '-run',run,'-outputFcn',@(varargin)[]);
        Global.Start();
        Population = Global.result{end,2};
        Obj = Population.objs; Dec = Population.decs;
        values(run) = MatrixIGD(Obj,PF);
        writematrix(Obj,fullfile(runDir,'obj.csv'));
        writematrix(Dec,fullfile(runDir,'dec.csv'));
        writetable(table(run,values(run),'VariableNames',{'seed','igd'}),igdFile);
        fprintf('%s run %02d IGD %.12g\n',name,run,values(run));
    end
    writetable(table((1:30)',values,'VariableNames',{'seed','igd'}), ...
        fullfile(problemDir,'igd_runs.csv'));
    meanValue = mean(values); stdValue = std(values);
    summaryRows(end+1,:) = {name,3,D,100,10000,30,size(PF,1),paper, ...
        meanValue,stdValue,meanValue-paper,abs(meanValue-paper), ...
        abs(meanValue-paper)/paper*100}; %#ok<SAGROW>
end
summary = cell2table(summaryRows,'VariableNames', ...
    {'problem','M','D','N','maxFE','runs','pf_points','paper_igd','mean_igd', ...
    'sample_std','signed_diff','abs_diff','relative_diff_percent'});
writetable(summary,fullfile(outputRoot,'summary.csv')); disp(summary);

function score = MatrixIGD(PopObj,PF)
    minDistances = inf(size(PF,1),1);
    for i = 1:size(PopObj,1)
        delta = PF-PopObj(i,:);
        minDistances = min(minDistances,sqrt(sum(delta.*delta,2)));
    end
    score = mean(minDistances);
end
