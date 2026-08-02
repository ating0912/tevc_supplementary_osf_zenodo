% Run NSGA-II on UF1-UF10 with the paper-level common parameters.

clear; clc;

N = 100;
D = 30;
maxFE = 10000;
Runs = 30;
pfPoints = 10000;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir, 'PlatEMO', 'PlatEMO');
outRoot = fullfile(scriptDir, 'nsga2_outputs', 'uf_series_nsga2_paper_params');

if ~exist(outRoot, 'dir')
    mkdir(outRoot);
end

addpath(genpath(platemoRoot));

problems = {
    'UF1',  @UF1,  2;
    'UF2',  @UF2,  2;
    'UF3',  @UF3,  2;
    'UF4',  @UF4,  2;
    'UF5',  @UF5,  2;
    'UF6',  @UF6,  2;
    'UF7',  @UF7,  2;
    'UF8',  @UF8,  3;
    'UF9',  @UF9,  3;
    'UF10', @UF10, 3;
};

summary = cell(size(problems,1), 9);

for p = 1 : size(problems,1)
    problemName = problems{p,1};
    problemFcn  = problems{p,2};
    M           = problems{p,3};
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

    summary(p,:) = {problemName, M, D, N, maxFE, Runs, mean(values), std(values), perRunFile};
end

summaryTable = cell2table(summary, 'VariableNames', ...
    {'problem','M','D','N','maxFE','runs','mean_igd','sample_std','per_run_file'});
writetable(summaryTable, fullfile(outRoot, 'uf_series_nsga2_paper_params_summary.csv'));
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
