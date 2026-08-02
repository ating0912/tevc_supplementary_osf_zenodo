% Reproduce configuration A on the 22 paper benchmark problems.
% A: PlatEMO v4.3, N=100, maxFE=10000, proC=1, etaC=20,
%    proM=1 interpreted by OperatorGA as proM/D, etaM=20,
%    final population, native GetOptimum(10000), raw IGD, rng(run).

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
workspaceRoot = fileparts(fileparts(scriptDir));
platemoRoot = fullfile(workspaceRoot,'PlatEMO_v4.3','PlatEMO');
outputRoot = fullfile(workspaceRoot,'nsga2_outputs','A_group_v43_extracted');

restoredefaultpath;
addpath(genpath(platemoRoot));
if ~exist(outputRoot,'dir'); mkdir(outputRoot); end

N = 100;
maxFE = 10000;
runs = 30;
pfPoints = 10000;

problems = {
    'DTLZ1', @DTLZ1, 3,  7, 0.23828;
    'DTLZ2', @DTLZ2, 3, 12, 0.054881;
    'DTLZ3', @DTLZ3, 3, 12, 13.357;
    'DTLZ4', @DTLZ4, 3, 12, 0.40388;
    'DTLZ5', @DTLZ5, 3, 12, 0.032473;
    'DTLZ6', @DTLZ6, 3, 12, 0.11635;
    'DTLZ7', @DTLZ7, 3, 22, 0.1708;
    'ZDT1',  @ZDT1,  2, 30, 0.14621;
    'ZDT2',  @ZDT2,  2, 30, 0.50813;
    'ZDT3',  @ZDT3,  2, 30, 0.17787;
    'ZDT4',  @ZDT4,  2, 10, 0.53146;
    'ZDT6',  @ZDT6,  2, 10, 0.07429;
    'UF1',   @UF1,   2, 30, 0.31352;
    'UF2',   @UF2,   2, 30, 0.21196;
    'UF3',   @UF3,   2, 30, 0.33463;
    'UF4',   @UF4,   2, 30, 0.12713;
    'UF5',   @UF5,   2, 30, 1.3074;
    'UF6',   @UF6,   2, 30, 0.59480;
    'UF7',   @UF7,   2, 30, 0.43887;
    'UF8',   @UF8,   3, 30, 0.58545;
    'UF9',   @UF9,   3, 30, 0.52501;
    'UF10',  @UF10,  3, 30, 0.74415;
};

rows = cell(size(problems,1),13);
for p = 1:size(problems,1)
    name = problems{p,1};
    problemFcn = problems{p,2};
    M = problems{p,3};
    D = problems{p,4};
    paperIGD = problems{p,5};
    problemDir = fullfile(outputRoot,name);
    if ~exist(problemDir,'dir'); mkdir(problemDir); end

    referenceProblem = problemFcn('N',N,'M',M,'D',D,'maxFE',maxFE);
    PF = referenceProblem.GetOptimum(pfPoints);
    values = nan(runs,1);

    for run = 1:runs
        runDir = fullfile(problemDir,sprintf('run_%03d',run));
        igdFile = fullfile(runDir,'igd.csv');
        if exist(igdFile,'file')
            previous = readmatrix(igdFile);
            values(run) = previous(1,2);
            continue;
        end
        if ~exist(runDir,'dir'); mkdir(runDir); end

        rng(run,'twister');
        [Dec,Obj,~] = platemo('algorithm',@NSGAII,'problem',problemFcn, ...
            'N',N,'M',M,'D',D,'maxFE',maxFE,'run',run);
        values(run) = MatrixIGD(Obj,PF);

        writematrix(Obj,fullfile(runDir,'obj.csv'));
        writematrix(Dec,fullfile(runDir,'dec.csv'));
        writetable(table(run,values(run),'VariableNames',{'seed','igd'}),igdFile);
        fprintf('%s run %02d IGD %.12g\n',name,run,values(run));
    end

    writetable(table((1:runs)',values,'VariableNames',{'seed','igd'}), ...
        fullfile(problemDir,'igd_runs.csv'));
    meanIGD = mean(values);
    sampleStd = std(values);
    signedDiff = meanIGD-paperIGD;
    rows(p,:) = {name,M,D,N,maxFE,runs,pfPoints,paperIGD,meanIGD, ...
        sampleStd,signedDiff,abs(signedDiff),abs(signedDiff)/paperIGD*100};
end

summary = cell2table(rows,'VariableNames', ...
    {'problem','M','D','N','maxFE','runs','pf_points','paper_igd', ...
     'mean_igd','sample_std','signed_diff','abs_diff','relative_diff_percent'});
writetable(summary,fullfile(outputRoot,'summary.csv'));
disp(summary);

function score = MatrixIGD(PopObj,PF)
    minimumDistances = inf(size(PF,1),1);
    for i = 1:size(PopObj,1)
        difference = PF-PopObj(i,:);
        minimumDistances = min(minimumDistances,sqrt(sum(difference.^2,2)));
    end
    score = mean(minimumDistances);
end
