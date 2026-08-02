% Smoke-test PlatEMO v2.9 algorithms on PortfolioORLIB.
% This only checks whether each algorithm can start and finish a tiny run.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');
restoredefaultpath;
addpath(genpath(platemoRoot));
addpath(scriptDir);

dataPath = fullfile(scriptDir,'data','orlib','port1.txt');
[mu,~] = P0LiteUtils.loadORLibraryPortfile(dataPath);
K = 5;
N = 50;
maxFE = 500;

algorithms = {
    'MOEAD',   @MOEAD
    'GDE3',    @GDE3
    'IBEA',    @IBEA
    'SMSEMOA', @SMSEMOA
    'MOCell',  @MOCell
    'PESAII',  @PESAII
    'HypE',    @HypE
    'GrEA',    @GrEA
    'MOPSO',   @MOPSO
    'SMPSO',   @SMPSO
    };

rows = {};
for i = 1:size(algorithms,1)
    name = algorithms{i,1};
    alg = algorithms{i,2};
    fprintf('Testing %s...\n',name);
    try
        rng(1,'mcg16807');
        t = tic;
        G = GLOBAL('-algorithm',alg,'-problem',{@PortfolioORLIB,dataPath,K}, ...
            '-N',N,'-M',2,'-D',numel(mu),'-evaluation',maxFE, ...
            '-run',1,'-outputFcn',@(varargin)[]);
        G.Start();
        runtime = toc(t);
        Pop = G.result{end,2};
        rows(end+1,:) = {name,true,'',numel(Pop),runtime}; %#ok<SAGROW>
    catch err
        rows(end+1,:) = {name,false,err.message,NaN,NaN}; %#ok<SAGROW>
    end
end

T = cell2table(rows,'VariableNames',{'algorithm','ok','message','population_size','runtime_sec'});
outFile = fullfile(scriptDir,'p0_lite_outputs','portfolio_baseline_compatibility.csv');
if ~exist(fileparts(outFile),'dir')
    mkdir(fileparts(outFile));
end
writetable(T,outFile);
disp(T);
fprintf('Compatibility table: %s\n',outFile);
