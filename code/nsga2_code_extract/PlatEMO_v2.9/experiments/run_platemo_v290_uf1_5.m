% Run PlatEMO v2.9.0 NSGA-II on UF1-UF5 with fixed seeds.

clear; clc;

scriptDir = fileparts(fileparts(fileparts(mfilename('fullpath'))));
platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');
compatRoot = fullfile(scriptDir,'platemo_v43_compat');
pfRoot = fullfile(scriptDir,'cec2009_reference','official_database', ...
    'CEC2009_MultiObjectiveEA_Database','pf_data');
outputRoot = fullfile(scriptDir,'nsga2_outputs','platemo_v290_uf1_5_seeded_r2020b');
if ~exist(outputRoot,'dir')
    mkdir(outputRoot);
end

restoredefaultpath;
addpath(genpath(platemoRoot));
addpath(compatRoot);

problems = {
    'UF1', @UF1, 0.31352;
    'UF2', @UF2, 0.21196;
    'UF3', @UF3, 0.33463;
    'UF4', @UF4, 0.12713;
    'UF5', @UF5, 1.3074;
};
summaryRows = {};

for p = 1:size(problems,1)
    name = problems{p,1};
    problemFcn = problems{p,2};
    paper = problems{p,3};
    problemDir = fullfile(outputRoot,name);
    if ~exist(problemDir,'dir')
        mkdir(problemDir);
    end
    PF = readmatrix(fullfile(pfRoot,[name,'.dat']),'FileType','text');
    values = nan(30,1);

    for run = 1:30
        runDir = fullfile(problemDir,sprintf('run_%03d',run));
        igdFile = fullfile(runDir,'igd.csv');
        if exist(igdFile,'file')
            old = readmatrix(igdFile);
            values(run) = old(1,2);
            continue;
        end
        if ~exist(runDir,'dir')
            mkdir(runDir);
        end

        rng(run,'twister');
        Global = GLOBAL('-algorithm',@NSGAII,'-problem',problemFcn, ...
            '-N',100,'-M',2,'-D',30,'-evaluation',10000, ...
            '-run',run,'-outputFcn',@(varargin)[]);
        Global.Start();
        Population = Global.result{end,2};
        Obj = Population.objs;
        Dec = Population.decs;
        value = MatrixIGD(Obj,PF);
        values(run) = value;

        writematrix(Obj,fullfile(runDir,'obj.csv'));
        writematrix(Dec,fullfile(runDir,'dec.csv'));
        writetable(table(run,value,'VariableNames',{'seed','igd'}),igdFile);
        fprintf('%s run %02d IGD %.12g\n',name,run,value);
    end

    runTable = table((1:30)',values,'VariableNames',{'seed','igd'});
    writetable(runTable,fullfile(problemDir,'igd_runs.csv'));
    meanValue = mean(values);
    stdValue = std(values);
    summaryRows(end+1,:) = {name,2,30,100,10000,30,paper, ...
        meanValue,stdValue,meanValue-paper,abs(meanValue-paper), ...
        abs(meanValue-paper)/paper*100}; %#ok<SAGROW>
end

summary = cell2table(summaryRows,'VariableNames', ...
    {'problem','M','D','N','maxFE','runs','paper_igd','mean_igd', ...
    'sample_std','signed_diff','abs_diff','relative_diff_percent'});
writetable(summary,fullfile(outputRoot,'summary.csv'));
disp(summary);

function score = MatrixIGD(PopObj,PF)
    minDistances = inf(size(PF,1),1);
    for i = 1:size(PopObj,1)
        delta = PF-PopObj(i,:);
        minDistances = min(minDistances,sqrt(sum(delta.*delta,2)));
    end
    score = mean(minDistances);
end
