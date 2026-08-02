function run_knowledge_base_parameter_search(dataInput,algorithmInput)
% Two-input meta-learning label generator.
% Input 1: dataInput      -> 'synthetic', 'orlib_port1', manifest csv, or OR-Library txt.
% Input 2: algorithmInput -> 'ECMADE_MOO', 'NSGAII', 'SPEA2', 'MOEAD', 'GDE3', 'A_MPMO', or comma list.

if nargin < 1 || isempty(dataInput)
    dataInput = input('資料: ','s');
end
if nargin < 2 || isempty(algorithmInput)
    algorithmInput = input('演算法: ','s');
end
if isempty(strtrim(dataInput)); dataInput = 'synthetic'; end
if isempty(strtrim(algorithmInput)); algorithmInput = 'ECMADE_MOO'; end

scriptDir = fileparts(mfilename('fullpath'));
outRoot = fullfile(scriptDir,'p0_lite_outputs', ...
    ['kb_label_generation_' datestr(now,'yyyymmdd_HHMMSS')]);
if ~exist(outRoot,'dir'); mkdir(outRoot); end

cfg = fixedLabelConfig(scriptDir,outRoot);
cfg = resolveDataInput(cfg,dataInput);
algorithms = parseList(algorithmInput);

if strcmpi(cfg.dataMode,'orlib_port1')
    runORLibrarySearch(scriptDir,cfg,algorithms);
else
    runSyntheticSearch(scriptDir,cfg,algorithms);
end

ranker = fullfile(scriptDir,'rank_knowledge_base_parameter_search.py');
if exist(ranker,'file')
    system(sprintf('python "%s" --root "%s"',ranker,cfg.outRoot));
end
fprintf('Output: %s\n',cfg.outRoot);
end

function cfg = fixedLabelConfig(scriptDir,outRoot)
cfg = struct();
cfg.outRoot = outRoot;
cfg.runs = 10;
cfg.N = 100;
cfg.maxFE = 10000;
cfg.maxCandidates = 24;
cfg.splits = {'train','validation','test'};
cfg.instances = {};
cfg.manifestPath = fullfile(scriptDir,'data','synthetic_constrained_portfolio','manifest.csv');
cfg.orlibPath = fullfile(scriptDir,'data','orlib','port1.txt');
cfg.KValues = [5 10 15 20 25 30];
cfg.dataMode = 'synthetic';
end

function cfg = resolveDataInput(cfg,dataInput)
dataInput = strtrim(dataInput);
if strcmpi(dataInput,'synthetic')
    cfg.dataMode = 'synthetic';
elseif strcmpi(dataInput,'orlib_port1')
    cfg.dataMode = 'orlib_port1';
elseif exist(dataInput,'file')
    [~,~,ext] = fileparts(dataInput);
    if strcmpi(ext,'.csv')
        cfg.dataMode = 'synthetic';
        cfg.manifestPath = dataInput;
    else
        cfg.dataMode = 'orlib_port1';
        cfg.orlibPath = dataInput;
    end
else
    error('Data not found: %s',dataInput);
end
end

function runSyntheticSearch(scriptDir,cfg,algorithms)
assignin('base','SYNTHETIC_OUT_ROOT',cfg.outRoot);
assignin('base','SYNTHETIC_MANIFEST',cfg.manifestPath);
assignin('base','SYNTHETIC_SPLITS',cfg.splits);
assignin('base','SYNTHETIC_INSTANCE_NAMES',cfg.instances);
assignin('base','SYNTHETIC_RUNS',cfg.runs);
assignin('base','SYNTHETIC_N',cfg.N);
assignin('base','SYNTHETIC_MAXFE',cfg.maxFE);
assignin('base','SYNTHETIC_SKIP_SUMMARY',true);
assignin('base','SYNTHETIC_FORCE_RERUN',false);

restoredefaultpath;
addpath(genpath(fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO')));
addpath(scriptDir);
writeProtocol(cfg);

for ai = 1:numel(algorithms)
    alg = algorithms{ai};
    if strcmpi(alg,'ECMADE_MOO')
        candidates = knowledgeBaseThetaCandidates(cfg.maxCandidates);
        writetable(struct2table(candidates),fullfile(cfg.outRoot,'kb_theta_candidates.csv'));
        for ci = 1:numel(candidates)
            assignin('base','ECMADE_MOO_KB_THETA',candidates(ci));
            SyntheticRunner.runAlgorithm(@ECMADE_MOO_KB,candidates(ci).method);
        end
        evalin('base','clear ECMADE_MOO_KB_THETA');
    else
        [handle,method] = algorithmHandle(alg);
        SyntheticRunner.runAlgorithm(handle,method);
    end
end

evalin('base',['clear SYNTHETIC_OUT_ROOT SYNTHETIC_MANIFEST SYNTHETIC_SPLITS ' ...
    'SYNTHETIC_INSTANCE_NAMES SYNTHETIC_RUNS SYNTHETIC_N SYNTHETIC_MAXFE ' ...
    'SYNTHETIC_SKIP_SUMMARY SYNTHETIC_FORCE_RERUN']);
end

function runORLibrarySearch(scriptDir,cfg,algorithms)
restoredefaultpath;
addpath(genpath(fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO')));
addpath(scriptDir);
writeProtocol(cfg);

for ai = 1:numel(algorithms)
    alg = algorithms{ai};
    if strcmpi(alg,'ECMADE_MOO')
        candidates = knowledgeBaseThetaCandidates(cfg.maxCandidates);
        writetable(struct2table(candidates),fullfile(cfg.outRoot,'kb_theta_candidates.csv'));
        for ci = 1:numel(candidates)
            assignin('base','ECMADE_MOO_KB_THETA',candidates(ci));
            runORLibraryOne(cfg,@ECMADE_MOO_KB,candidates(ci).method);
        end
        evalin('base','clear ECMADE_MOO_KB_THETA');
    else
        [handle,method] = algorithmHandle(alg);
        runORLibraryOne(cfg,handle,method);
    end
end
end

function runORLibraryOne(cfg,algorithmHandle,method)
[mu,~] = P0LiteUtils.loadORLibraryPortfile(cfg.orlibPath);
for kk = 1:numel(cfg.KValues)
    K = cfg.KValues(kk);
    fprintf('=== %s | K=%d ===\n',method,K);
    for run = 1:cfg.runs
        runDir = fullfile(cfg.outRoot,sprintf('K_%02d',K),method,sprintf('run_%03d',run));
        if exist(fullfile(runDir,'pf_obj.csv'),'file') && exist(fullfile(runDir,'runtime.csv'),'file')
            continue;
        end
        if ~exist(runDir,'dir'); mkdir(runDir); end
        t = tic;
        rng(run,'mcg16807');
        G = GLOBAL('-algorithm',algorithmHandle,'-problem',{@PortfolioORLIB,cfg.orlibPath,K}, ...
            '-N',cfg.N,'-M',2,'-D',numel(mu),'-evaluation',cfg.maxFE, ...
            '-run',run,'-save',max(1,cfg.maxFE/cfg.N),'-outputFcn',@(varargin)[]);
        G.Start();
        runtime = toc(t);
        Pop = G.result{end,2};
        [pfDec,pfObj] = P0LiteUtils.firstFrontDecObj(Pop.decs,Pop.objs);
        P0LiteUtils.saveRun(runDir,Pop.decs,Pop.objs,pfDec,pfObj,runtime,K);
        P0LiteUtils.saveGenerationSnapshots(runDir,G.result,K,cfg.N);
    end
end
end

function writeProtocol(cfg)
fid = fopen(fullfile(cfg.outRoot,'meta_learning_label_protocol.txt'),'w');
fprintf(fid,'input_data=%s\n',cfg.dataMode);
fprintf(fid,'runs_for_label=%d\n',cfg.runs);
fprintf(fid,'same_budget_N=%d\n',cfg.N);
fprintf(fid,'same_budget_maxFE=%d\n',cfg.maxFE);
fprintf(fid,'theta_candidates=%d\n',cfg.maxCandidates);
fprintf(fid,'output_labels=top1_classification_labels.csv, theta_ranking_labels.csv, regression_score_labels.csv\n');
fprintf(fid,'test_rule=test split is report-only; do not use it for theta selection or meta-learner tuning.\n');
fclose(fid);
end

function candidates = knowledgeBaseThetaCandidates(maxCandidates)
subpops = [2 3 5];
operators = {'mixed','rand2','best2'};
exchangeModes = {'none','stable','paper'};
eliteRatios = [0.01 0.05 0.10];
taus = [5 10 20];
thetas = [0.05 1/13 0.10 0.20];
archiveFactors = [1 5 inf];
consensusFlags = [false true];

candidates = struct('method',{},'subpops',{},'operatorMode',{},'exchangeMode',{}, ...
    'eliteRatio',{},'stagnationThreshold',{},'theta',{},'archiveLimitFactor',{}, ...
    'consensusArchive',{},'archiveConsWeight',{},'bestGuide',{},'minSubpopSize',{});
for i = 1:maxCandidates
    c = struct();
    c.method = sprintf('KB_T%03d',i);
    c.subpops = subpops(mod(i-1,numel(subpops))+1);
    c.operatorMode = operators{mod(2*i-2,numel(operators))+1};
    c.exchangeMode = exchangeModes{mod(3*i-3,numel(exchangeModes))+1};
    c.eliteRatio = eliteRatios(mod(5*i-5,numel(eliteRatios))+1);
    c.stagnationThreshold = taus(mod(7*i-7,numel(taus))+1);
    c.theta = thetas(mod(11*i-11,numel(thetas))+1);
    c.archiveLimitFactor = archiveFactors(mod(13*i-13,numel(archiveFactors))+1);
    c.consensusArchive = consensusFlags(mod(17*i-17,numel(consensusFlags))+1);
    c.archiveConsWeight = 0.10 * double(c.consensusArchive);
    c.bestGuide = ternary(c.consensusArchive,'consensus','rank');
    c.minSubpopSize = 1;
    candidates(end+1,1) = c; %#ok<AGROW>
end
end

function [handle,method] = algorithmHandle(name)
name = upper(strtrim(name));
switch name
    case 'NSGAII'
        handle = @NSGAII; method = 'NSGAII';
    case 'SPEA2'
        handle = @SPEA2; method = 'SPEA2';
    case 'MOEAD'
        handle = @MOEAD; method = 'MOEAD';
    case 'GDE3'
        handle = @GDE3; method = 'GDE3';
    case 'A_MPMO'
        handle = @A_MPMO_NSGAII_v290; method = 'A_MPMO';
    otherwise
        error('Unknown algorithm: %s',name);
end
end

function items = parseList(text)
parts = regexp(text,',','split');
items = {};
for i = 1:numel(parts)
    item = strtrim(parts{i});
    if ~isempty(item)
        items{end+1} = item; %#ok<AGROW>
    end
end
end

function out = ternary(cond,a,b)
if cond
    out = a;
else
    out = b;
end
end
