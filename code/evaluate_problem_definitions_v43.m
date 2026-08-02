% Evaluate the v2.9 decision points with PlatEMO v4.3 problem code.

clear; clc;
root = fileparts(mfilename('fullpath'));
out = fullfile(root,'nsga2_outputs','problem_definition_diagnostic');
restoredefaultpath;
addpath(genpath(fullfile(root,'PlatEMO_v4.3','PlatEMO')));

problems = {
    'ZDT2',@ZDT2,2,30; 'ZDT4',@ZDT4,2,10;
    'DTLZ1',@DTLZ1,3,7; 'DTLZ4',@DTLZ4,3,12;
    'UF6',@UF6,2,30; 'UF10',@UF10,3,30;
};
for p = 1:size(problems,1)
    name=problems{p,1}; f=problems{p,2}; M=problems{p,3}; D=problems{p,4};
    P=f('N',100,'M',M,'D',D,'maxFE',10000);
    X=readmatrix(fullfile(out,[name '_dec.csv']));
    F=P.CalObj(X);
    writematrix(F,fullfile(out,[name '_v43_obj.csv']));
end
