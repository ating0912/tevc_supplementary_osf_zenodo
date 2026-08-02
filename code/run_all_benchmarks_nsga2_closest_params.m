% Run NSGA-II on all paper-listed benchmarks using the closest inferred settings.

clear; clc;

N = 100;
maxFE = 3500;
Runs = 30;
pfPoints = 10000;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir, 'PlatEMO', 'PlatEMO');
outRoot = fullfile(scriptDir, 'nsga2_outputs', 'all_benchmarks_nsga2_closest_params');

if ~exist(outRoot, 'dir')
    mkdir(outRoot);
end

addpath(genpath(platemoRoot));

benchmarks = {
    'DTLZ1',  @DTLZ1,  3,  7;
    'DTLZ2',  @DTLZ2,  3, 12;
    'DTLZ3',  @DTLZ3,  3, 12;
    'DTLZ4',  @DTLZ4,  3, 12;
    'DTLZ5',  @DTLZ5,  3, 12;
    'DTLZ6',  @DTLZ6,  3, 12;
    'DTLZ7',  @DTLZ7,  3, 22;
    'ZDT1',   @ZDT1,   2, 30;
    'ZDT2',   @ZDT2,   2, 30;
    'ZDT3',   @ZDT3,   2, 30;
    'ZDT4',   @ZDT4,   2, 10;
    'ZDT6',   @ZDT6,   2, 10;
    'UF1',    @UF1,    2, 30;
    'UF2',    @UF2,    2, 30;
    'UF3',    @UF3,    2, 30;
    'UF4',    @UF4,    2, 30;
    'UF5',    @UF5,    2, 30;
    'UF6',    @UF6,    2, 30;
    'UF7',    @UF7,    2, 30;
    'UF8',    @UF8,    3, 30;
    'UF9',    @UF9,    3, 30;
    'UF10',   @UF10,   3, 30;
};

summary = cell(size(benchmarks,1), 10);

for p = 1 : size(benchmarks,1)
    problemName = benchmarks{p,1};
    problemFcn  = benchmarks{p,2};
    M           = benchmarks{p,3};
    D           = benchmarks{p,4};
    outDir      = fullfile(outRoot, problemName);
    if ~exist(outDir, 'dir')
        mkdir(outDir);
    end

    tempProblem = problemFcn('N', N, 'M', M, 'D', D, 'maxFE', maxFE);
    PF = tempProblem.GetOptimum(pfPoints);

    values = zeros(Runs, 1);
    fprintf('\n=== %s M=%d D=%d N=%d maxFE=%d ===\n', problemName, M, D, N, maxFE);

    for run = 1 : Runs
        rng(run);
        evalc("[~,Obj,~] = platemo('algorithm', @NSGAII_PaperMutation, 'problem', problemFcn, 'N', N, 'M', M, 'D', D, 'maxFE', maxFE, 'run', run);");
        values(run) = MatrixIGD(Obj, PF);

        runDir = fullfile(outDir, sprintf('run_%03d', run));
        if ~exist(runDir, 'dir')
            mkdir(runDir);
        end
        writematrix(Obj, fullfile(runDir, 'obj.csv'));
        fprintf('%s run=%02d IGD=%.12g\n', problemName, run, values(run));
    end

    perRunTable = table((1:Runs)', values, 'VariableNames', {'run','igd'});
    perRunFile = fullfile(outDir, sprintf('%s_igd_runs.csv', problemName));
    writetable(perRunTable, perRunFile);

    summary(p,:) = {problemName, M, D, N, maxFE, Runs, mean(values), std(values), min(values), max(values)};
end

summaryTable = cell2table(summary, 'VariableNames', ...
    {'problem','M','D','N','maxFE','runs','mean_igd','sample_std','min_igd','max_igd'});
writetable(summaryTable, fullfile(outRoot, 'all_benchmarks_nsga2_closest_params_summary.csv'));
disp(summaryTable);

function score = MatrixIGD(PopObj, PF)
    minDistances = inf(size(PF,1), 1);
    for i = 1 : size(PopObj,1)
        diff = PF - PopObj(i,:);
        distances = sqrt(sum(diff.*diff, 2));
        minDistances = min(minDistances, distances);
    end
    score = mean(minDistances);
end
