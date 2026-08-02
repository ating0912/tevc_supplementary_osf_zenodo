% Verify that NSGA-II configuration A is exactly reproducible with a seed.

clear; clc;

N = 100;
M = 2;
D = 30;
maxFE = 10000;
seed = 1;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir, 'PlatEMO', 'PlatEMO');
outDir = fullfile(scriptDir, 'nsga2_outputs', 'a_seed_repro_validation');
if ~exist(outDir, 'dir')
    mkdir(outDir);
end
addpath(genpath(platemoRoot));

[Dec1,Obj1,Con1] = platemo( ...
    'algorithm', @NSGAII, 'problem', @ZDT1, ...
    'N', N, 'M', M, 'D', D, 'maxFE', maxFE, ...
    'run', 1, 'seed', seed);
[Dec2,Obj2,Con2] = platemo( ...
    'algorithm', @NSGAII, 'problem', @ZDT1, ...
    'N', N, 'M', M, 'D', D, 'maxFE', maxFE, ...
    'run', 1, 'seed', seed);

problem = ZDT1('N', N, 'M', M, 'D', D, 'maxFE', maxFE);
PF = problem.GetOptimum(10000);
igd1 = MatrixIGD(Obj1, PF);
igd2 = MatrixIGD(Obj2, PF);

sameDec = isequaln(Dec1, Dec2);
sameObj = isequaln(Obj1, Obj2);
sameCon = isequaln(Con1, Con2);
sameIGD = isequaln(igd1, igd2);
passed = sameDec && sameObj && sameCon && sameIGD;

writematrix(Dec1, fullfile(outDir, 'repeat_1_dec.csv'));
writematrix(Obj1, fullfile(outDir, 'repeat_1_obj.csv'));
writematrix(Dec2, fullfile(outDir, 'repeat_2_dec.csv'));
writematrix(Obj2, fullfile(outDir, 'repeat_2_obj.csv'));

result = table(seed, N, M, D, maxFE, igd1, igd2, sameDec, sameObj, ...
    sameCon, sameIGD, passed);
writetable(result, fullfile(outDir, 'validation_summary.csv'));
disp(result);

if ~passed
    error('Seed reproducibility validation failed.');
end
fprintf('PASS: configuration A is exactly reproducible with seed %d.\n', seed);

function score = MatrixIGD(PopObj, PF)
    minDistances = inf(size(PF,1), 1);
    for i = 1 : size(PopObj,1)
        diff = PF - PopObj(i,:);
        distances = sqrt(sum(diff.*diff, 2));
        minDistances = min(minDistances, distances);
    end
    score = mean(minDistances);
end
