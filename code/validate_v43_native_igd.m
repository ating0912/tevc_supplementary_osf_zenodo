% Validate PlatEMO v4.3 GUI/experiment metric path against saved IGD values.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v4.3','PlatEMO');
inputRoot = fullfile(scriptDir,'nsga2_outputs','platemo_v43_uf1_5_seeded');
outputFile = fullfile(inputRoot,'platemo_native_igd_validation.csv');
restoredefaultpath;
addpath(genpath(platemoRoot));
addpath(fullfile(scriptDir,'platemo_v43_compat'));

problems = {
    'UF1', @UF1;
    'UF2', @UF2;
    'UF3', @UF3;
    'UF4', @UF4;
    'UF5', @UF5;
};
rows = {};

for p = 1:size(problems,1)
    name = problems{p,1};
    problemFcn = problems{p,2};
    problem = problemFcn('N',100,'M',2,'D',30,'maxFE',10000);
    for run = 1:30
        runDir = fullfile(inputRoot,name,sprintf('run_%03d',run));
        Obj = readmatrix(fullfile(runDir,'obj.csv'));
        savedRow = readmatrix(fullfile(runDir,'igd.csv'));
        savedFullIGD = savedRow(1,2);
        Population = SOLUTION(zeros(size(Obj,1),1),Obj,zeros(size(Obj,1),1));
        nativeIGD = problem.CalMetric('IGD',Population);
        frontNo = NDSort(Obj,1);
        manualNativeIGD = MatrixIGD(Obj(frontNo==1,:),problem.optimum);
        rows(end+1,:) = {name,run,savedFullIGD,nativeIGD,manualNativeIGD, ...
            nativeIGD-savedFullIGD,abs(nativeIGD-savedFullIGD), ...
            abs(nativeIGD-manualNativeIGD)}; %#ok<SAGROW>
    end
end

result = cell2table(rows,'VariableNames', ...
    {'problem','seed','saved_full_population_igd','platemo_native_igd', ...
    'manual_nondominated_igd','native_minus_saved','native_vs_saved_abs_diff', ...
    'native_vs_manual_abs_diff'});
writetable(result,outputFile);

fprintf('Validated runs: %d\n',height(result));
fprintf('Maximum native-vs-manual difference: %.17g\n', ...
    max(result.native_vs_manual_abs_diff));
fprintf('Mean native-vs-saved full-population difference: %.17g\n', ...
    mean(result.native_minus_saved));

function score = MatrixIGD(PopObj,PF)
    minDistances = inf(size(PF,1),1);
    for i = 1:size(PopObj,1)
        delta = PF-PopObj(i,:);
        minDistances = min(minDistances,sqrt(sum(delta.*delta,2)));
    end
    score = mean(minDistances);
end
