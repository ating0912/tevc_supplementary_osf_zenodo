% Run the user-defined A-G NSGA-II diagnostic matrix in MATLAB/PlatEMO.
% Matrix:
% A maxFE=10000, PlatEMO proM/D, analytic PF
% B maxFE=10000, per-variable proM, analytic PF
% C maxFE=10000, per-variable proM, PlatEMO GetOptimum(100)
% D maxFE=10000, per-variable proM, PlatEMO GetOptimum(10000)
% E maxFE=N*10000, PlatEMO proM/D, analytic PF
% F maxFE=N*10000, per-variable proM, analytic PF
% G maxFE=10000, per-variable proM, analytic PF + objective normalization

clear; clc;

N = 100;
Runs = 30;
MaxIt = 10000;
longMaxFE = N * MaxIt;
shortMaxFE = 10000;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir, 'PlatEMO', 'PlatEMO');
oldRoot = fullfile(scriptDir, 'nsga2_outputs', 'all_nsga2_test_matrix');
outRoot = fullfile(scriptDir, 'nsga2_outputs', 'paper_matrix_nsga2');

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
    'A', 'maxFE=10000; PlatEMO proM/D; analytic PF',            @NSGAII,               shortMaxFE, 10000, false, 'C_platemo_maxFE10000';
    'B', 'maxFE=10000; per-variable proM; analytic PF',         @NSGAII_PaperMutation, shortMaxFE, 10000, false, 'D_paper_maxFE10000';
    'C', 'maxFE=10000; per-variable proM; GetOptimum(100)',     @NSGAII_PaperMutation, shortMaxFE,   100, false, 'D_paper_maxFE10000';
    'D', 'maxFE=10000; per-variable proM; GetOptimum(10000)',   @NSGAII_PaperMutation, shortMaxFE, 10000, false, 'D_paper_maxFE10000';
    'G', 'maxFE=10000; per-variable proM; analytic PF; norm',   @NSGAII_PaperMutation, shortMaxFE, 10000, true,  'D_paper_maxFE10000';
    'E', 'maxFE=N*10000; PlatEMO proM/D; analytic PF',          @NSGAII,               longMaxFE,  10000, false, '';
    'F', 'maxFE=N*10000; per-variable proM; analytic PF',       @NSGAII_PaperMutation, longMaxFE,  10000, false, '';
};

summaryRows = {};
row = 0;

for c = 1 : size(configs,1)
    configId = configs{c,1};
    configDesc = configs{c,2};
    algorithmFcn = configs{c,3};
    maxFE = configs{c,4};
    pfPoints = configs{c,5};
    normalizeObj = configs{c,6};
    reuseConfig = configs{c,7};
    configDir = fullfile(outRoot, configId);
    if ~exist(configDir, 'dir')
        mkdir(configDir);
    end

    for p = 1 : size(benchmarks,1)
        problemName = benchmarks{p,1};
        problemFcn = benchmarks{p,2};
        M = benchmarks{p,3};
        D = benchmarks{p,4};
        paperIGD = benchmarks{p,5};
        problemDir = fullfile(configDir, problemName);
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
                oldObjPath = '';
                if ~isempty(reuseConfig)
                    oldObjPath = fullfile(oldRoot, reuseConfig, problemName, sprintf('run_%03d', run), 'obj.csv');
                end
                if ~isempty(oldObjPath) && exist(oldObjPath, 'file')
                    Obj = readmatrix(oldObjPath);
                    if ~exist(runDir, 'dir')
                        mkdir(runDir);
                    end
                    writematrix(Obj, objPath);
                else
                    if ~exist(runDir, 'dir')
                        mkdir(runDir);
                    end
                    rng(run);
                    evalc("[~,Obj,~] = platemo('algorithm', algorithmFcn, 'problem', problemFcn, 'N', N, 'M', M, 'D', D, 'maxFE', maxFE, 'run', run);");
                    writematrix(Obj, objPath);
                end
            end

            if normalizeObj
                values(run) = NormalizedMatrixIGD(Obj, PF);
            else
                values(run) = MatrixIGD(Obj, PF);
            end
            fprintf('%s %s run=%02d IGD=%.12g\n', configId, problemName, run, values(run));
        end

        perRunTable = table((1:Runs)', values, 'VariableNames', {'run','igd'});
        writetable(perRunTable, fullfile(problemDir, sprintf('%s_%s_igd_runs.csv', configId, problemName)));

        meanIGD = mean(values);
        stdIGD = std(values);
        signedDiff = meanIGD - paperIGD;
        row = row + 1;
        summaryRows(row,:) = {configId, configDesc, problemName, M, D, N, maxFE, Runs, pfPoints, normalizeObj, ...
            paperIGD, meanIGD, stdIGD, signedDiff, abs(signedDiff), abs(signedDiff)/paperIGD*100};

        partialTable = cell2table(summaryRows, 'VariableNames', ...
            {'config','description','problem','M','D','N','maxFE','runs','pf_points','normalized_igd', ...
             'paper_nsga2_igd','mean_igd','sample_std','ours_minus_paper','abs_diff','relative_diff_percent'});
        writetable(partialTable, fullfile(outRoot, 'paper_matrix_matlab_partial_summary.csv'));
    end
end

summaryTable = cell2table(summaryRows, 'VariableNames', ...
    {'config','description','problem','M','D','N','maxFE','runs','pf_points','normalized_igd', ...
     'paper_nsga2_igd','mean_igd','sample_std','ours_minus_paper','abs_diff','relative_diff_percent'});
writetable(summaryTable, fullfile(outRoot, 'paper_matrix_matlab_summary.csv'));

bestRows = {};
for p = 1 : size(benchmarks,1)
    problemName = benchmarks{p,1};
    idx = strcmp(summaryTable.problem, problemName);
    sub = summaryTable(idx,:);
    [~,bestIdx] = min(sub.abs_diff);
    bestRows(end+1,:) = table2cell(sub(bestIdx,:)); %#ok<AGROW>
end
bestTable = cell2table(bestRows, 'VariableNames', summaryTable.Properties.VariableNames);
writetable(bestTable, fullfile(outRoot, 'paper_matrix_matlab_best_config_per_problem.csv'));

disp(summaryTable);
disp(bestTable);

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
