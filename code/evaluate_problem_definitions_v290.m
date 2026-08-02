% Evaluate deterministic decision points with PlatEMO v2.9 problem code.

clear; clc;
root = fileparts(mfilename('fullpath'));
out = fullfile(root,'nsga2_outputs','problem_definition_diagnostic');
if ~exist(out,'dir'); mkdir(out); end
restoredefaultpath;
addpath(genpath(fullfile(root,'PlatEMO_v2.9.0','PlatEMO')));

problems = {
    'ZDT2',@ZDT2,2,30; 'ZDT4',@ZDT4,2,10;
    'DTLZ1',@DTLZ1,3,7; 'DTLZ4',@DTLZ4,3,12;
    'UF6',@UF6,2,30; 'UF10',@UF10,3,30;
};
for p = 1:size(problems,1)
    name=problems{p,1}; f=problems{p,2}; M=problems{p,3}; D=problems{p,4};
    G=GLOBAL('-algorithm',@NSGAII,'-problem',f,'-N',100,'-M',M,'-D',D, ...
        '-evaluation',10000,'-outputFcn',@(varargin)[]);
    rng(20250611,'twister');
    X=repmat(G.lower,1000,1)+rand(1000,D).*repmat(G.upper-G.lower,1000,1);
    F=G.problem.CalObj(X);
    writematrix(X,fullfile(out,[name '_dec.csv']));
    writematrix(F,fullfile(out,[name '_v290_obj.csv']));
end
