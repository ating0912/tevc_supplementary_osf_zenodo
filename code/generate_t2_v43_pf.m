% Generate T2 reference PFs in a clean MATLAB session using PlatEMO v4.3.

clear; clc;
root = fileparts(mfilename('fullpath'));
target = fullfile(root,'nsga2_outputs','v290_pf_sources_t1_t2_t3', ...
    'reference_pf','T2_v43');
if ~exist(target,'dir'); mkdir(target); end

restoredefaultpath;
addpath(genpath(fullfile(root,'PlatEMO_v4.3','PlatEMO')));

problems = {
    'DTLZ1', 3,  7; 'DTLZ2', 3, 12; 'DTLZ3', 3, 12;
    'DTLZ4', 3, 12; 'DTLZ5', 3, 12; 'DTLZ6', 3, 12;
    'DTLZ7', 3, 22; 'ZDT1',  2, 30; 'ZDT2',  2, 30;
    'ZDT3',  2, 30; 'ZDT4',  2, 10; 'ZDT6',  2, 10;
    'UF1',   2, 30; 'UF2',   2, 30; 'UF3',   2, 30;
    'UF4',   2, 30; 'UF5',   2, 30; 'UF6',   2, 30;
    'UF7',   2, 30; 'UF8',   3, 30; 'UF9',   3, 30;
    'UF10',  3, 30;
};

for p = 1:size(problems,1)
    name = problems{p,1};
    problemFcn = str2func(name);
    problem = problemFcn('N',100,'M',problems{p,2},'D',problems{p,3}, ...
        'maxFE',10000);
    PF = problem.GetOptimum(10000);
    writematrix(PF,fullfile(target,[name,'.csv']));
    fprintf('%s: %d points\n',name,size(PF,1));
end
