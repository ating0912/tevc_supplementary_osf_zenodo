% Rerun NSGA-II V1-V10 and V14-V15 diagnostic versions.
% Paper-mentioned numeric parameters are kept unchanged.

clear; clc;

N = 100;
Runs = 30;
shortMaxFE = 10000;
longMaxFE = N * 10000;
scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir, 'PlatEMO', 'PlatEMO');
outRoot = fullfile(scriptDir, 'nsga2_outputs', 'version_matrix_rerun');

if ~exist(outRoot, 'dir')
    mkdir(outRoot);
end

addpath(genpath(platemoRoot));

benchmarks = {
    'DTLZ1',  @DTLZ1,  3,  7,  2.3828e1;
    'DTLZ2',  @DTLZ2,  3, 12,  5.4881e-2;
    'DTLZ3',  @DTLZ3,  3, 12,  1.3357e1;
    'DTLZ4',  @DTLZ4,  3, 12,  4.0388e-2;
    'DTLZ5',  @DTLZ5,  3, 12,  3.2473e-2;
    'DTLZ6',  @DTLZ6,  3, 12,  1.1635e-1;
    'DTLZ7',  @DTLZ7,  3, 22,  1.7080e-1;
    'ZDT1',   @ZDT1,   2, 30,  1.4621e-1;
    'ZDT2',   @ZDT2,   2, 30,  5.0813e-1;
    'ZDT3',   @ZDT3,   2, 30,  1.7787e-1;
    'ZDT4',   @ZDT4,   2, 10,  5.3146e-1;
    'ZDT6',   @ZDT6,   2, 10,  7.4290e-2;
    'UF1',    @UF1,    2, 30,  3.1352e-1;
    'UF2',    @UF2,    2, 30,  2.1196e-1;
    'UF3',    @UF3,    2, 30,  3.3463e-1;
    'UF4',    @UF4,    2, 30,  1.2713e-1;
    'UF5',    @UF5,    2, 30,  1.3074e0;
    'UF6',    @UF6,    2, 30,  5.9480e-1;
    'UF7',    @UF7,    2, 30,  4.3887e-1;
    'UF8',    @UF8,    3, 30,  5.8545e-1;
    'UF9',    @UF9,    3, 30,  5.2501e-1;
    'UF10',   @UF10,   3, 30,  7.4415e-1;
};

configs = {
    'V1',  'PlatEMO; maxFE=10000; proM/D; final; raw analytic PF; rng(run)',      @NSGAII,               shortMaxFE, 10000, false, false, true;
    'V2',  'PlatEMO; maxFE=10000; proM/D; nondominated; raw analytic PF; rng(run)', @NSGAII,             shortMaxFE, 10000, false, true,  true;
    'V3',  'PlatEMO; maxFE=10000; proM/D; final; normalized IGD; rng(run)',       @NSGAII,               shortMaxFE, 10000, true,  false, true;
    'V4',  'PlatEMO; maxFE=10000; proM/D; nondominated; normalized IGD; rng(run)', @NSGAII,              shortMaxFE, 10000, true,  true,  true;
    'V5',  'PlatEMO; maxFE=10000; proM/D; final; GetOptimum(100); rng(run)',      @NSGAII,               shortMaxFE,   100, false, false, true;
    'V6',  'PlatEMO; maxFE=10000; proM/D; final; GetOptimum(10000); rng(run)',    @NSGAII,               shortMaxFE, 10000, false, false, true;
    'V7',  'PlatEMO; maxFE=10000; proM/D; final; raw analytic PF; default seed',  @NSGAII,               shortMaxFE, 10000, false, false, false;
    'V8',  'PlatEMO; maxFE=10000; per-variable proM; final; raw analytic PF; rng(run)', @NSGAII_PaperMutation, shortMaxFE, 10000, false, false, true;
    'V9',  'PlatEMO; maxFE=10000; per-variable proM; nondominated; raw analytic PF; rng(run)', @NSGAII_PaperMutation, shortMaxFE, 10000, false, true, true;
    'V10', 'PlatEMO; maxFE=10000; per-variable proM; final; normalized IGD; rng(run)', @NSGAII_PaperMutation, shortMaxFE, 10000, true, false, true;
    'V14', 'PlatEMO; maxFE=N*10000; proM/D; final; raw analytic PF; rng(run)',    @NSGAII,               longMaxFE,  10000, false, false, true;
    'V15', 'PlatEMO; maxFE=N*10000; per-variable proM; final; raw analytic PF; rng(run)', @NSGAII_PaperMutation, longMaxFE, 10000, false, false, true;
};

summaryRows = {};
partialPath = fullfile(outRoot, 'version_matrix_matlab_partial_summary.csv');
row = 0;
if exist(partialPath, 'file')
    previous = readtable(partialPath);
    summaryRows = table2cell(previous);
    row = size(summaryRows, 1);
end

for c = 1 : size(configs,1)
    configId = configs{c,1};
    configDesc = configs{c,2};
    algorithmFcn = configs{c,3};
    maxFE = configs{c,4};
    pfPoints = configs{c,5};
    normalizeObj = configs{c,6};
    useND = configs{c,7};
    setSeed = configs{c,8};

    for p = 1 : size(benchmarks,1)
        problemName = benchmarks{p,1};
        if AlreadySummarized(summaryRows, configId, problemName)
            continue;
        end

        problemFcn = benchmarks{p,2};
        M = benchmarks{p,3};
        D = benchmarks{p,4};
        paperIGD = benchmarks{p,5};
        problemDir = fullfile(outRoot, configId, problemName);
        if ~exist(problemDir, 'dir')
            mkdir(problemDir);
        end

        tempProblem = problemFcn('N', N, 'M', M, 'D', D, 'maxFE', maxFE);
        PF = tempProblem.GetOptimum(pfPoints);
        values = nan(Runs, 1);

        fprintf('\n=== %s | %s M=%d D=%d maxFE=%d ===\n', configId, problemName, M, D, maxFE);
        for run = 1 : Runs
            runDir = fullfile(problemDir, sprintf('run_%03d', run));
            objPath = fullfile(runDir, 'obj.csv');
            if exist(objPath, 'file')
                Obj = readmatrix(objPath);
            else
                if ~exist(runDir, 'dir')
                    mkdir(runDir);
                end
                if setSeed
                    rng(run);
                end
                evalc("[~,Obj,~] = platemo('algorithm', algorithmFcn, 'problem', problemFcn, 'N', N, 'M', M, 'D', D, 'maxFE', maxFE, 'run', run);");
                writematrix(Obj, objPath);
            end
            EvalObj = ObjForMetric(Obj, useND);
            if normalizeObj
                values(run) = NormalizedMatrixIGD(EvalObj, PF);
            else
                values(run) = MatrixIGD(EvalObj, PF);
            end
            fprintf('%s %s run=%02d IGD=%.12g\n', configId, problemName, run, values(run));
        end

        perRunTable = table((1:Runs)', values, 'VariableNames', {'run','igd'});
        writetable(perRunTable, fullfile(problemDir, sprintf('%s_%s_igd_runs.csv', configId, problemName)));

        meanIGD = mean(values);
        stdIGD = std(values);
        signedDiff = meanIGD - paperIGD;
        row = row + 1;
        summaryRows(row,:) = {configId, configDesc, problemName, M, D, N, maxFE, Runs, pfPoints, ...
            normalizeObj, useND, setSeed, paperIGD, meanIGD, stdIGD, signedDiff, abs(signedDiff), abs(signedDiff)/paperIGD*100};

        summaryTable = cell2table(summaryRows, 'VariableNames', ...
            {'config','description','problem','M','D','N','maxFE','runs','pf_points','normalized_igd', ...
             'nondominated_only','seed_fixed','paper_nsga2_igd','mean_igd','sample_std', ...
             'ours_minus_paper','abs_diff','relative_diff_percent'});
        writetable(summaryTable, partialPath);
    end
end

summaryTable = cell2table(summaryRows, 'VariableNames', ...
    {'config','description','problem','M','D','N','maxFE','runs','pf_points','normalized_igd', ...
     'nondominated_only','seed_fixed','paper_nsga2_igd','mean_igd','sample_std', ...
     'ours_minus_paper','abs_diff','relative_diff_percent'});
writetable(summaryTable, fullfile(outRoot, 'version_matrix_matlab_summary.csv'));
disp(summaryTable);

function tf = AlreadySummarized(rows, configId, problemName)
    tf = false;
    for i = 1 : size(rows,1)
        if strcmp(rows{i,1}, configId) && strcmp(rows{i,3}, problemName)
            tf = true;
            return;
        end
    end
end

function EvalObj = ObjForMetric(Obj, useND)
    if ~useND
        EvalObj = Obj;
    else
        FrontNo = NDSort(Obj, 1);
        EvalObj = Obj(FrontNo == 1, :);
    end
end

function score = MatrixIGD(PopObj, PF)
    minDistances = inf(size(PF,1), 1);
    for i = 1 : size(PopObj,1)
        diff = PF - PopObj(i,:);
        distances = sqrt(sum(diff.*diff, 2));
        minDistances = min(minDistances, distances);
    end
    score = mean(minDistances);
end

function score = NormalizedMatrixIGD(PopObj, PF)
    allObj = [PopObj; PF];
    lower = min(allObj, [], 1);
    upper = max(allObj, [], 1);
    span = upper - lower;
    span(span == 0) = 1;
    score = MatrixIGD((PopObj - lower)./span, (PF - lower)./span);
end
