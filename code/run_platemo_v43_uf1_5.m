% Run NSGA-II on UF1-UF5 using the official PlatEMO v4.3 snapshot.

clear; clc;

N = 100;
M = 2;
D = 30;
maxFE = 10000;
runs = 1:30;
pfPoints = 10000;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir, 'PlatEMO_v4.3', 'PlatEMO');
releaseName = version('-release');
outRoot = fullfile(scriptDir, 'nsga2_outputs', ...
    ['platemo_v43_uf1_5_seeded_', lower(releaseName)]);
if ~exist(outRoot, 'dir')
    mkdir(outRoot);
end

restoredefaultpath;
addpath(genpath(platemoRoot));
addpath(fullfile(scriptDir, 'platemo_v43_compat'));

problems = {
    'UF1', @UF1, 3.1352e-1;
    'UF2', @UF2, 2.1196e-1;
    'UF3', @UF3, 3.3463e-1;
    'UF4', @UF4, 1.2713e-1;
    'UF5', @UF5, 1.3074e0;
};

metadata = table( ...
    {'v4.3'}, {'29156d4dfaceb319903020d202bd214a3d3aafe3'}, ...
    {'2023-09-20'}, {releaseName}, {version}, N, M, D, maxFE, numel(runs), pfPoints, ...
    {'NSGA-II'}, 1, 20, 1, 20, {'PlatEMO proM/D'}, ...
    {'final population'}, {'raw IGD'}, {'rng(run,''twister'')'}, ...
    'VariableNames', {'platemo_version','commit','release_date','matlab_release', ...
    'matlab_version','N','M','D', ...
    'maxFE','runs','pf_points','algorithm','proC','etaC','proM','etaM', ...
    'mutation_interpretation','evaluated_set','igd_type','seed_policy'});
writetable(metadata, fullfile(outRoot, 'configuration.csv'));

summaryRows = {};
for p = 1:size(problems,1)
    problemName = problems{p,1};
    problemFcn = problems{p,2};
    paperIGD = problems{p,3};
    problemDir = fullfile(outRoot, problemName);
    if ~exist(problemDir, 'dir')
        mkdir(problemDir);
    end

    referenceProblem = problemFcn('N', N, 'M', M, 'D', D, 'maxFE', maxFE);
    PF = referenceProblem.GetOptimum(pfPoints);
    values = nan(numel(runs),1);
    elapsed = nan(numel(runs),1);

    fprintf('\n=== PlatEMO v4.3 | %s M=%d D=%d maxFE=%d ===\n', ...
        problemName, M, D, maxFE);
    for i = 1:numel(runs)
        run = runs(i);
        runDir = fullfile(problemDir, sprintf('run_%03d', run));
        objPath = fullfile(runDir, 'obj.csv');
        decPath = fullfile(runDir, 'dec.csv');
        igdPath = fullfile(runDir, 'igd.csv');

        if exist(objPath, 'file') && exist(igdPath, 'file')
            result = readtable(igdPath);
            values(i) = result.igd(1);
            elapsed(i) = result.elapsed_seconds(1);
            fprintf('%s seed=%02d already complete, IGD=%.12g\n', ...
                problemName, run, values(i));
            continue;
        end
        if ~exist(runDir, 'dir')
            mkdir(runDir);
        end

        rng(run, 'twister');
        started = tic;
        [Dec, Obj, ~] = platemo( ...
            'algorithm', @NSGAII, 'problem', problemFcn, ...
            'N', N, 'M', M, 'D', D, 'maxFE', maxFE);
        elapsed(i) = toc(started);
        values(i) = MatrixIGD(Obj, PF);

        writematrix(Dec, decPath);
        writematrix(Obj, objPath);
        result = table(run, values(i), elapsed(i), ...
            'VariableNames', {'seed','igd','elapsed_seconds'});
        writetable(result, igdPath);
        fprintf('%s seed=%02d IGD=%.12g time=%.1fs\n', ...
            problemName, run, values(i), elapsed(i));
    end

    runsTable = table(runs(:), values, elapsed, ...
        'VariableNames', {'seed','igd','elapsed_seconds'});
    writetable(runsTable, fullfile(problemDir, 'igd_runs.csv'));

    meanIGD = mean(values);
    sampleStd = std(values);
    signedDiff = meanIGD - paperIGD;
    summaryRows(end+1,:) = {problemName, M, D, N, maxFE, numel(runs), ...
        paperIGD, meanIGD, sampleStd, signedDiff, abs(signedDiff), ...
        abs(signedDiff)/paperIGD*100}; %#ok<SAGROW>
    summary = cell2table(summaryRows, 'VariableNames', ...
        {'problem','M','D','N','maxFE','completed_runs','paper_nsga2_igd', ...
        'mean_igd','sample_std','ours_minus_paper','abs_diff', ...
        'relative_diff_percent'});
    writetable(summary, fullfile(outRoot, 'summary.csv'));
end

disp(summary);

function score = MatrixIGD(PopObj, PF)
    minDistances = inf(size(PF,1),1);
    for i = 1:size(PopObj,1)
        diff = PF - PopObj(i,:);
        distances = sqrt(sum(diff.*diff,2));
        minDistances = min(minDistances,distances);
    end
    score = mean(minDistances);
end
