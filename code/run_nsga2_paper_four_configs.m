function run_nsga2_paper_four_configs(configId, runs, problemFilter)
% Run one of the four NSGA-II interpretations of the paper settings.
%
% P1: maxFE=10000,   PlatEMO mutation probability 1/D
% P2: maxFE=1000000, PlatEMO mutation probability 1/D
% P3: maxFE=10000,   per-variable mutation probability 1
% P4: maxFE=1000000, per-variable mutation probability 1

    if nargin < 1 || isempty(configId)
        error('Specify one configuration: P1, P2, P3, or P4.');
    end
    if nargin < 2 || isempty(runs)
        runs = 1:30;
    end
    if nargin < 3
        problemFilter = '';
    end

    N = 100;
    configId = upper(char(configId));
    switch configId
        case 'P1'
            algorithmFcn = @NSGAII;
            maxFE = 10000;
            mutationInterpretation = 'PlatEMO proM/D';
        case 'P2'
            algorithmFcn = @NSGAII;
            maxFE = N * 10000;
            mutationInterpretation = 'PlatEMO proM/D';
        case 'P3'
            algorithmFcn = @NSGAII_PaperMutation;
            maxFE = 10000;
            mutationInterpretation = 'per-variable proM=1';
        case 'P4'
            algorithmFcn = @NSGAII_PaperMutation;
            maxFE = N * 10000;
            mutationInterpretation = 'per-variable proM=1';
        otherwise
            error('Unknown configuration "%s". Use P1, P2, P3, or P4.', configId);
    end

    scriptDir = fileparts(mfilename('fullpath'));
    platemoRoot = fullfile(scriptDir, 'PlatEMO', 'PlatEMO');
    outRoot = fullfile(scriptDir, 'nsga2_outputs', 'paper_four_seeded');
    configDir = fullfile(outRoot, configId);
    if ~exist(configDir, 'dir')
        mkdir(configDir);
    end
    addpath(genpath(platemoRoot));

    benchmarks = {
        'DTLZ1', @DTLZ1, 3,  7, 2.3828e-1;
        'DTLZ2', @DTLZ2, 3, 12, 5.4881e-2;
        'DTLZ3', @DTLZ3, 3, 12, 1.3357e1;
        'DTLZ4', @DTLZ4, 3, 12, 4.0388e-1;
        'DTLZ5', @DTLZ5, 3, 12, 3.2473e-2;
        'DTLZ6', @DTLZ6, 3, 12, 1.1635e-1;
        'DTLZ7', @DTLZ7, 3, 22, 1.7080e-1;
        'ZDT1',  @ZDT1,  2, 30, 1.4621e-1;
        'ZDT2',  @ZDT2,  2, 30, 5.0813e-1;
        'ZDT3',  @ZDT3,  2, 30, 1.7787e-1;
        'ZDT4',  @ZDT4,  2, 10, 5.3146e-1;
        'ZDT6',  @ZDT6,  2, 10, 7.4290e-2;
        'UF1',   @UF1,   2, 30, 3.1352e-1;
        'UF2',   @UF2,   2, 30, 2.1196e-1;
        'UF3',   @UF3,   2, 30, 3.3463e-1;
        'UF4',   @UF4,   2, 30, 1.2713e-1;
        'UF5',   @UF5,   2, 30, 1.3074e0;
        'UF6',   @UF6,   2, 30, 5.9480e-1;
        'UF7',   @UF7,   2, 30, 4.3887e-1;
        'UF8',   @UF8,   3, 30, 5.8545e-1;
        'UF9',   @UF9,   3, 30, 5.2501e-1;
        'UF10',  @UF10,  3, 30, 7.4415e-1;
    };
    if ~isempty(problemFilter)
        benchmarks = benchmarks(strcmp(benchmarks(:,1), char(problemFilter)), :);
        if isempty(benchmarks)
            error('Unknown problem filter "%s".', char(problemFilter));
        end
    end

    metadata = table({configId}, N, maxFE, 1, 20, 1, 20, ...
        {mutationInterpretation}, {'final population'}, 10000, {'raw IGD'}, ...
        {'seed=run; twister'}, ...
        'VariableNames', {'config','N','maxFE','proC','etaC','proM','etaM', ...
        'mutation_interpretation','evaluated_set','pf_points','igd_type','seed_policy'});
    writetable(metadata, fullfile(configDir, 'configuration.csv'));

    for p = 1:size(benchmarks,1)
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
        PF = tempProblem.GetOptimum(10000);
        fprintf('\n=== %s | %s M=%d D=%d maxFE=%d ===\n', ...
            configId, problemName, M, D, maxFE);

        for run = runs(:)'
            runDir = fullfile(problemDir, sprintf('run_%03d', run));
            objPath = fullfile(runDir, 'obj.csv');
            decPath = fullfile(runDir, 'dec.csv');
            igdPath = fullfile(runDir, 'igd.csv');
            if exist(objPath, 'file') && exist(igdPath, 'file')
                fprintf('%s %s seed=%02d already complete\n', configId, problemName, run);
                continue;
            end
            if ~exist(runDir, 'dir')
                mkdir(runDir);
            end

            started = tic;
            try
                [Dec, Obj, ~] = platemo( ...
                    'algorithm', algorithmFcn, 'problem', problemFcn, ...
                    'N', N, 'M', M, 'D', D, 'maxFE', maxFE, ...
                    'run', run, 'seed', run);
                score = MatrixIGD(Obj, PF);
                elapsed = toc(started);
                writematrix(Dec, decPath);
                writematrix(Obj, objPath);
                runResult = table(run, score, elapsed, ...
                    'VariableNames', {'seed','igd','elapsed_seconds'});
                writetable(runResult, igdPath);
                fprintf('%s %s seed=%02d IGD=%.12g time=%.1fs\n', ...
                    configId, problemName, run, score, elapsed);
            catch err
                fid = fopen(fullfile(runDir, 'error.txt'), 'w');
                if fid >= 0
                    fprintf(fid, '%s\n', getReport(err, 'extended', 'hyperlinks', 'off'));
                    fclose(fid);
                end
                rethrow(err);
            end
        end
        UpdateProblemSummary(problemDir, configId, problemName, M, D, N, ...
            maxFE, paperIGD);
        UpdateConfigSummary(configDir);
    end
end

function UpdateProblemSummary(problemDir, configId, problemName, M, D, N, maxFE, paperIGD)
    files = dir(fullfile(problemDir, 'run_*', 'igd.csv'));
    seeds = nan(numel(files),1);
    values = nan(numel(files),1);
    elapsed = nan(numel(files),1);
    for i = 1:numel(files)
        result = readtable(fullfile(files(i).folder, files(i).name));
        seeds(i) = result.seed(1);
        values(i) = result.igd(1);
        elapsed(i) = result.elapsed_seconds(1);
    end
    [seeds, order] = sort(seeds);
    values = values(order);
    elapsed = elapsed(order);
    runsTable = table(seeds, values, elapsed, ...
        'VariableNames', {'seed','igd','elapsed_seconds'});
    writetable(runsTable, fullfile(problemDir, 'igd_runs.csv'));

    completedRuns = numel(values);
    meanIGD = mean(values);
    sampleStd = std(values);
    summary = table({configId}, {problemName}, M, D, N, maxFE, completedRuns, ...
        paperIGD, meanIGD, sampleStd, meanIGD-paperIGD, abs(meanIGD-paperIGD), ...
        'VariableNames', {'config','problem','M','D','N','maxFE','completed_runs', ...
        'paper_nsga2_igd','mean_igd','sample_std','ours_minus_paper','abs_diff'});
    writetable(summary, fullfile(problemDir, 'summary.csv'));
end

function UpdateConfigSummary(configDir)
    files = dir(fullfile(configDir, '*', 'summary.csv'));
    rows = cell(numel(files),1);
    for i = 1:numel(files)
        rows{i} = readtable(fullfile(files(i).folder, files(i).name));
    end
    if ~isempty(rows)
        summary = vertcat(rows{:});
        writetable(summary, fullfile(configDir, 'summary.csv'));
    end
end

function score = MatrixIGD(PopObj, PF)
    minDistances = inf(size(PF,1), 1);
    for i = 1:size(PopObj,1)
        diff = PF - PopObj(i,:);
        distances = sqrt(sum(diff.*diff, 2));
        minDistances = min(minDistances, distances);
    end
    score = mean(minDistances);
end
