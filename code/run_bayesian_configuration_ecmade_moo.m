function run_bayesian_configuration_ecmade_moo()
% Bayesian configuration ECMADE-MOO baseline for TEVC Experiment B.
%
% This runner performs discrete Bayesian optimization over the approved
% L24 theta library. It first searches for a single globally good theta on
% validation instances, then evaluates that selected theta on unseen test
% instances.
%
% Default workflow:
%   configuration phase:
%     validation split, 8 instances, 3 runs per theta, 12-theta BO budget
%   final test phase:
%     test split, all instances, 30 runs using the selected theta
%
% Optional base-workspace overrides:
%   BAYES_CONFIG_THETA_PATH, BAYES_CONFIG_MANIFEST, BAYES_CONFIG_OUT_ROOT
%   BAYES_CONFIG_SPLITS, BAYES_CONFIG_FINAL_SPLITS
%   BAYES_CONFIG_CONFIG_RUNS, BAYES_CONFIG_FINAL_RUNS
%   BAYES_CONFIG_CONFIG_MAX_INSTANCES, BAYES_CONFIG_FINAL_MAX_INSTANCES
%   BAYES_CONFIG_N, BAYES_CONFIG_CONFIG_MAXFE, BAYES_CONFIG_FINAL_MAXFE
%   BAYES_CONFIG_BUDGET, BAYES_CONFIG_INITIAL_POINTS, BAYES_CONFIG_SEED
%   BAYES_CONFIG_FORCE_RERUN

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');

cfg = struct();
cfg.method = 'BayesianConfig_ECMADE_MOO';
cfg.thetaPath = defaultThetaPath();
cfg.thetaSheet = 'L24_Theta_Config';
cfg.manifestPath = fullfile(scriptDir,'data','synthetic_constrained_portfolio','manifest.csv');
cfg.outRoot = fullfile(scriptDir,'p0_lite_outputs', ...
    ['bayesian_config_ecmade_moo_' datestr(now,'yyyymmdd_HHMMSS')]);
cfg.configSplits = {'validation'};
cfg.finalSplits = {'test'};
cfg.configRuns = 3;
cfg.finalRuns = 30;
cfg.N = 100;
cfg.configMaxFE = 5000;
cfg.finalMaxFE = 10000;
cfg.configMaxInstances = 8;
cfg.finalMaxInstances = inf;
cfg.instanceNames = {};
cfg.budget = 12;
cfg.initialPoints = 5;
cfg.seed = 20260712;
cfg.rngType = 'mcg16807';
cfg.forceRerun = false;
cfg.riskPenalty = 1.0;
cfg.feasibleBonus = 0.01;
cfg.pfSizeWeight = 1e-4;
cfg.runtimePenalty = 1e-4;

cfg = applyWorkspaceOverrides(cfg);
cfg.configSaveGenerations = max(1,cfg.configMaxFE / cfg.N);
cfg.finalSaveGenerations = max(1,cfg.finalMaxFE / cfg.N);

validateInputs(cfg,platemoRoot);

restoredefaultpath;
addpath(genpath(platemoRoot));
addpath(scriptDir);

if ~exist(cfg.outRoot,'dir')
    mkdir(cfg.outRoot);
end

candidates = readL24Candidates(cfg.thetaPath,cfg.thetaSheet);
manifest = loadManifest(cfg.manifestPath,scriptDir);
configManifest = filterManifest(manifest,cfg.configSplits,cfg.instanceNames,cfg.configMaxInstances);
finalManifest = filterManifest(manifest,cfg.finalSplits,cfg.instanceNames,cfg.finalMaxInstances);

writetable(struct2table(candidates),fullfile(cfg.outRoot,'l24_theta_candidates.csv'));
writetable(configManifest,fullfile(cfg.outRoot,'configuration_instances.csv'));
writetable(finalManifest,fullfile(cfg.outRoot,'final_test_instances.csv'));
writeProtocol(cfg,numel(candidates),height(configManifest),height(finalManifest));

fprintf('Bayesian configuration ECMADE-MOO baseline\n');
fprintf('Theta Excel: %s\n',cfg.thetaPath);
fprintf('Config instances: %d, runs=%d, maxFE=%d, budget=%d\n', ...
    height(configManifest),cfg.configRuns,cfg.configMaxFE,cfg.budget);
fprintf('Final test instances: %d, runs=%d, maxFE=%d\n', ...
    height(finalManifest),cfg.finalRuns,cfg.finalMaxFE);
fprintf('Output: %s\n',cfg.outRoot);

cleanup = onCleanup(@() evalin('base','clear ECMADE_MOO_KB_THETA'));

evalTable = runBayesianSearch(candidates,configManifest,cfg);
writetable(evalTable,fullfile(cfg.outRoot,'bayesian_configuration_evaluations.csv'));

best = sortrows(evalTable,{'J','iteration'},{'descend','ascend'});
bestThetaId = best.theta_id{1};
bestIndex = best.theta_index(1);
bestTheta = candidates(bestIndex);
writetable(best(1,:),fullfile(cfg.outRoot,'bayesian_selected_theta.csv'));

fprintf('Selected theta: %s, J=%.8g\n',bestThetaId,best.J(1));
runFinalTest(bestTheta,bestIndex,finalManifest,cfg);

configSummary = rebuildSummary(fullfile(cfg.outRoot,'configuration'),[]);
if ~isempty(configSummary)
    writetable(configSummary,fullfile(cfg.outRoot,'configuration_run_summary.csv'));
end
finalSummary = rebuildSummary(fullfile(cfg.outRoot,'final_test'),cfg.method);
if ~isempty(finalSummary)
    writetable(finalSummary,fullfile(cfg.outRoot,'bayesian_config_final_test_summary.csv'));
    writeAggregateSummary(finalSummary,fullfile(cfg.outRoot,'bayesian_config_summary_by_instance.csv'));
end
runRanker(scriptDir,cfg.outRoot);

fprintf('Done. Selected theta: %s\n',bestThetaId);
fprintf('Final summary: %s\n',fullfile(cfg.outRoot,'bayesian_config_final_test_summary.csv'));
end

function thetaPath = defaultThetaPath()
repoRoot = fileparts(fileparts(mfilename('fullpath')));
candidates = {fullfile(repoRoot,'external_data','TEVC_P0_L24_Orthogonal_Theta_Configurations.xlsx')};
thetaPath = candidates{1};
for i = 1:numel(candidates)
    if exist(candidates{i},'file')
        thetaPath = candidates{i};
        return;
    end
end
end

function cfg = applyWorkspaceOverrides(cfg)
cfg = overrideValue(cfg,'BAYES_CONFIG_THETA_PATH','thetaPath');
cfg = overrideValue(cfg,'BAYES_CONFIG_MANIFEST','manifestPath');
cfg = overrideValue(cfg,'BAYES_CONFIG_OUT_ROOT','outRoot');
cfg = overrideValue(cfg,'BAYES_CONFIG_SPLITS','configSplits');
cfg = overrideValue(cfg,'BAYES_CONFIG_FINAL_SPLITS','finalSplits');
cfg = overrideValue(cfg,'BAYES_CONFIG_CONFIG_RUNS','configRuns');
cfg = overrideValue(cfg,'BAYES_CONFIG_FINAL_RUNS','finalRuns');
cfg = overrideValue(cfg,'BAYES_CONFIG_N','N');
cfg = overrideValue(cfg,'BAYES_CONFIG_CONFIG_MAXFE','configMaxFE');
cfg = overrideValue(cfg,'BAYES_CONFIG_FINAL_MAXFE','finalMaxFE');
cfg = overrideValue(cfg,'BAYES_CONFIG_CONFIG_MAX_INSTANCES','configMaxInstances');
cfg = overrideValue(cfg,'BAYES_CONFIG_FINAL_MAX_INSTANCES','finalMaxInstances');
cfg = overrideValue(cfg,'BAYES_CONFIG_INSTANCE_NAMES','instanceNames');
cfg = overrideValue(cfg,'BAYES_CONFIG_BUDGET','budget');
cfg = overrideValue(cfg,'BAYES_CONFIG_INITIAL_POINTS','initialPoints');
cfg = overrideValue(cfg,'BAYES_CONFIG_SEED','seed');
cfg = overrideValue(cfg,'BAYES_CONFIG_FORCE_RERUN','forceRerun');
end

function cfg = overrideValue(cfg,varName,fieldName)
if evalin('base',sprintf('exist(''%s'',''var'')',varName))
    cfg.(fieldName) = evalin('base',varName);
end
end

function validateInputs(cfg,platemoRoot)
if ~exist(cfg.thetaPath,'file')
    error('BayesConfig:MissingThetaFile','Theta Excel file not found: %s',cfg.thetaPath);
end
if ~exist(cfg.manifestPath,'file')
    error('BayesConfig:MissingManifest','Manifest file not found: %s',cfg.manifestPath);
end
if ~exist(platemoRoot,'dir')
    error('BayesConfig:MissingPlatEMO','PlatEMO root not found: %s',platemoRoot);
end
end

function evalTable = runBayesianSearch(candidates,configManifest,cfg)
budget = min(cfg.budget,numel(candidates));
initialPoints = min(cfg.initialPoints,budget);
rng(cfg.seed,'twister');
order = randperm(numel(candidates));
observed = [];
rows = {};

for iteration = 1:budget
    if iteration <= initialPoints
        thetaIndex = order(iteration);
        acquisition = 'initial_random';
        acquisitionValue = NaN;
    else
        [thetaIndex,acquisitionValue] = proposeExpectedImprovement(candidates,observed);
        acquisition = 'expected_improvement';
    end

    thetaCfg = candidates(thetaIndex);
    fprintf('BO iteration %02d/%02d: evaluating %s (%s)\n', ...
        iteration,budget,thetaCfg.source_theta_id,acquisition);
    stats = evaluateTheta(thetaCfg,thetaIndex,configManifest,cfg,iteration);

    observed(end+1,:) = [thetaIndex,stats.J]; %#ok<AGROW>
    rows(end+1,:) = { ...
        iteration,thetaIndex,thetaCfg.source_theta_id,acquisition,acquisitionValue, ...
        stats.J,stats.mean_return,stats.mean_risk,stats.mean_pf_size, ...
        stats.mean_runtime_sec,stats.mean_pf_feasible_rate,stats.completed_runs, ...
        thetaCfg.subpops,thetaCfg.source_operator,thetaCfg.source_migration, ...
        thetaCfg.eliteRatio,thetaCfg.stagnationThreshold}; %#ok<AGROW>
end

evalTable = cell2table(rows,'VariableNames',{ ...
    'iteration','theta_index','theta_id','acquisition','acquisition_value', ...
    'J','mean_return','mean_risk','mean_pf_size','mean_runtime_sec', ...
    'mean_pf_feasible_rate','completed_runs','S','operator','migration', ...
    'elite_ratio','stagnation_threshold'});
end

function [thetaIndex,eiValue] = proposeExpectedImprovement(candidates,observed)
observedIdx = observed(:,1);
y = observed(:,2);
allIdx = (1:numel(candidates))';
remaining = setdiff(allIdx,observedIdx,'stable');
if isempty(remaining)
    thetaIndex = observedIdx(end);
    eiValue = 0;
    return;
end

X = candidateFeatures(candidates,observedIdx);
Xstar = candidateFeatures(candidates,remaining);
yStd = std(y);
if yStd < 1e-12 || size(X,1) < 2
    thetaIndex = remaining(1);
    eiValue = 0;
    return;
end
yn = (y - mean(y)) / yStd;

ell = 1.25;
noise = 1e-6;
K = rbfKernel(X,X,ell) + noise*eye(size(X,1));
Ks = rbfKernel(X,Xstar,ell);
Kss = ones(numel(remaining),1);

alpha = K \ yn;
mu = Ks' * alpha;
v = K \ Ks;
sigma2 = max(Kss - sum(Ks .* v,1)',1e-12);
sigma = sqrt(sigma2);

bestY = max(yn);
improvement = mu - bestY;
z = improvement ./ sigma;
ei = improvement .* normalCdf(z) + sigma .* normalPdf(z);
[eiValue,pos] = max(ei);
thetaIndex = remaining(pos);
end

function X = candidateFeatures(candidates,indices)
X = zeros(numel(indices),5);
for r = 1:numel(indices)
    c = candidates(indices(r));
    X(r,:) = [c.S_level,c.operator_level,c.migration_level,c.elite_level,c.tau_level];
end
end

function K = rbfKernel(A,B,ell)
D = zeros(size(A,1),size(B,1));
for j = 1:size(A,2)
    diff = A(:,j) - B(:,j)';
    D = D + diff.^2;
end
K = exp(-0.5 * D / (ell^2));
end

function y = normalPdf(x)
y = exp(-0.5*x.^2) / sqrt(2*pi);
end

function y = normalCdf(x)
y = 0.5 * (1 + erf(x ./ sqrt(2)));
end

function stats = evaluateTheta(thetaCfg,thetaIndex,manifest,cfg,iteration)
assignin('base','ECMADE_MOO_KB_THETA',thetaCfg);
runRows = {};
for ii = 1:height(manifest)
    row = manifest(ii,:);
    instance = scalarText(row.instance);
    splitName = scalarText(row.split);
    dataPath = scalarText(row.path);
    K = row.K;
    nAssets = row.assets;
    method = sprintf('BayesEval_%s',thetaCfg.source_theta_id);

    for run = 1:cfg.configRuns
        runDir = fullfile(cfg.outRoot,'configuration',splitName,instance, ...
            sprintf('K_%02d',K),method,sprintf('run_%03d',run));
        if ~cfg.forceRerun && hasCompleteRun(runDir)
            [pfObj,runtime,feasibleRate] = readRunOutputs(runDir);
        else
            if ~exist(runDir,'dir')
                mkdir(runDir);
            end
            writeRunMetadata(runDir,row,thetaCfg,cfg.method,thetaIndex,iteration, ...
                cfg.N,cfg.configMaxFE,cfg.configRuns,dataPath);
            fprintf('%s %s Run %03d/%03d\n',method,instance,run,cfg.configRuns);
            rng(run,cfg.rngType);
            t = tic;
            G = GLOBAL('-algorithm',@ECMADE_MOO_KB, ...
                '-problem',{@PortfolioORLIB,dataPath,K}, ...
                '-N',cfg.N,'-M',2,'-D',nAssets, ...
                '-evaluation',cfg.configMaxFE,'-run',run, ...
                '-save',cfg.configSaveGenerations,'-outputFcn',@(varargin)[]);
            G.Start();
            runtime = toc(t);
            Pop = G.result{end,2};
            Obj = Pop.objs;
            Dec = Pop.decs;
            [pfDec,pfObj] = P0LiteUtils.firstFrontDecObj(Dec,Obj);
            P0LiteUtils.saveRun(runDir,Dec,Obj,pfDec,pfObj,runtime,K);
            P0LiteUtils.saveGenerationSnapshots(runDir,G.result,K,cfg.N);
            feasibleRate = readFeasibleRate(runDir);
        end
        runRows(end+1,:) = runStatsRow(pfObj,runtime,feasibleRate); %#ok<AGROW>
    end
end
stats = scoreRunRows(runRows,cfg);
end

function row = runStatsRow(pfObj,runtime,feasibleRate)
if isempty(pfObj)
    pfSize = 0;
    meanRisk = NaN;
    meanReturn = NaN;
else
    pfSize = size(pfObj,1);
    meanRisk = mean(pfObj(:,1));
    meanReturn = mean(-pfObj(:,2));
end
row = {pfSize,runtime,meanRisk,meanReturn,feasibleRate};
end

function stats = scoreRunRows(runRows,cfg)
T = cell2table(runRows,'VariableNames',{ ...
    'pf_size','runtime_sec','mean_risk','mean_return','pf_feasible_rate'});
stats = struct();
stats.completed_runs = height(T);
stats.mean_pf_size = nanmeanLocal(T.pf_size);
stats.mean_runtime_sec = nanmeanLocal(T.runtime_sec);
stats.mean_risk = nanmeanLocal(T.mean_risk);
stats.mean_return = nanmeanLocal(T.mean_return);
stats.mean_pf_feasible_rate = nanmeanLocal(T.pf_feasible_rate);
stats.J = stats.mean_return ...
    - cfg.riskPenalty * stats.mean_risk ...
    + cfg.feasibleBonus * stats.mean_pf_feasible_rate ...
    + cfg.pfSizeWeight * log1p(stats.mean_pf_size) ...
    - cfg.runtimePenalty * stats.mean_runtime_sec;
end

function runFinalTest(thetaCfg,thetaIndex,manifest,cfg)
assignin('base','ECMADE_MOO_KB_THETA',thetaCfg);
for ii = 1:height(manifest)
    row = manifest(ii,:);
    instance = scalarText(row.instance);
    splitName = scalarText(row.split);
    dataPath = scalarText(row.path);
    K = row.K;
    nAssets = row.assets;
    fprintf('Final test %s | %s | K=%d | %s\n',splitName,instance,K,thetaCfg.source_theta_id);

    for run = 1:cfg.finalRuns
        runDir = fullfile(cfg.outRoot,'final_test',splitName,instance, ...
            sprintf('K_%02d',K),cfg.method,sprintf('run_%03d',run));
        if ~cfg.forceRerun && hasCompleteRun(runDir)
            continue;
        end
        if ~exist(runDir,'dir')
            mkdir(runDir);
        end
        writeRunMetadata(runDir,row,thetaCfg,cfg.method,thetaIndex,NaN, ...
            cfg.N,cfg.finalMaxFE,cfg.finalRuns,dataPath);
        fprintf('%s %s Run %03d/%03d\n',cfg.method,instance,run,cfg.finalRuns);
        rng(run,cfg.rngType);
        t = tic;
        G = GLOBAL('-algorithm',@ECMADE_MOO_KB, ...
            '-problem',{@PortfolioORLIB,dataPath,K}, ...
            '-N',cfg.N,'-M',2,'-D',nAssets, ...
            '-evaluation',cfg.finalMaxFE,'-run',run, ...
            '-save',cfg.finalSaveGenerations,'-outputFcn',@(varargin)[]);
        G.Start();
        runtime = toc(t);
        Pop = G.result{end,2};
        Obj = Pop.objs;
        Dec = Pop.decs;
        [pfDec,pfObj] = P0LiteUtils.firstFrontDecObj(Dec,Obj);
        P0LiteUtils.saveRun(runDir,Dec,Obj,pfDec,pfObj,runtime,K);
        P0LiteUtils.saveGenerationSnapshots(runDir,G.result,K,cfg.N);
    end
end
end

function [pfObj,runtime,feasibleRate] = readRunOutputs(runDir)
pfObj = readmatrix(fullfile(runDir,'pf_obj.csv'));
rt = readtable(fullfile(runDir,'runtime.csv'));
runtime = rt.runtime_sec(1);
feasibleRate = readFeasibleRate(runDir);
end

function feasibleRate = readFeasibleRate(runDir)
feasibleRate = NaN;
feasibleFile = fullfile(runDir,'feasible_rate.csv');
if exist(feasibleFile,'file')
    feas = readtable(feasibleFile);
    feasibleRate = feas.PF_Feasible_Rate(1);
end
end

function writeRunMetadata(runDir,row,thetaCfg,method,thetaIndex,iteration,N,maxFE,runs,dataPath)
T = table();
T.method = {method};
T.theta_index = thetaIndex;
T.theta_id = {thetaCfg.source_theta_id};
T.bo_iteration = iteration;
T.S = thetaCfg.subpops;
T.operator = {thetaCfg.source_operator};
T.operatorMode = {thetaCfg.operatorMode};
T.migration = {thetaCfg.source_migration};
T.exchangeMode = {thetaCfg.exchangeMode};
T.elite_ratio = thetaCfg.eliteRatio;
T.source_elite_ratio = {thetaCfg.source_elite_ratio};
T.stagnation_threshold = thetaCfg.stagnationThreshold;
T.archive_strategy = {thetaCfg.source_archive_strategy};
T.constraint_handling = {thetaCfg.source_constraint_handling};
T.instance = row.instance;
T.split = row.split;
T.assets = row.assets;
T.K = row.K;
T.k_ratio = row.k_ratio;
T.corr_structure = row.corr_structure;
T.return_distribution = row.return_distribution;
T.risk_structure = row.risk_structure;
T.N = N;
T.maxFE = maxFE;
T.runs = runs;
T.dataPath = {dataPath};
writetable(T,fullfile(runDir,'theta_metadata.csv'));
end

function candidates = readL24Candidates(thetaPath,sheetName)
raw = readcell(thetaPath,'Sheet',sheetName);
headers = raw(4,:);
data = raw(5:28,:);

idx.theta_id = findHeader(headers,'theta_id');
idx.S_level = findHeader(headers,'S_level');
idx.operator_level = findHeader(headers,'operator_level');
idx.migration_level = findHeader(headers,'migration_level');
idx.elite_level = findHeader(headers,'elite_level');
idx.tau_level = findHeader(headers,'tau_level');
idx.S = findHeader(headers,'S');
idx.operator = findHeader(headers,'operator');
idx.migration = findHeader(headers,'migration');
idx.elite_ratio = findHeader(headers,'elite_ratio');
idx.stagnation_threshold = findHeader(headers,'stagnation_threshold');
idx.archive_strategy = findHeader(headers,'archive_strategy');
idx.constraint_handling = findHeader(headers,'constraint_handling');

candidates = struct('method',{},'source_theta_id',{},'source_operator',{}, ...
    'source_migration',{},'source_elite_ratio',{},'source_archive_strategy',{}, ...
    'source_constraint_handling',{},'subpops',{},'operatorMode',{}, ...
    'exchangeMode',{},'eliteRatio',{},'stagnationThreshold',{},'theta',{}, ...
    'archiveLimitFactor',{},'consensusArchive',{},'archiveConsWeight',{}, ...
    'bestGuide',{},'minSubpopSize',{},'S_level',{},'operator_level',{}, ...
    'migration_level',{},'elite_level',{},'tau_level',{});

for i = 1:size(data,1)
    rawThetaId = scalarText(data{i,idx.theta_id});
    if isempty(rawThetaId)
        continue;
    end
    thetaId = normalizeThetaId(rawThetaId,i);
    op = scalarText(data{i,idx.operator});
    mig = scalarText(data{i,idx.migration});
    elite = scalarText(data{i,idx.elite_ratio});

    c = struct();
    c.method = thetaId;
    c.source_theta_id = thetaId;
    c.source_operator = op;
    c.source_migration = mig;
    c.source_elite_ratio = elite;
    c.source_archive_strategy = scalarText(data{i,idx.archive_strategy});
    c.source_constraint_handling = scalarText(data{i,idx.constraint_handling});
    c.subpops = numericValue(data{i,idx.S});
    c.operatorMode = mapOperator(op);
    c.exchangeMode = mapMigration(mig);
    c.eliteRatio = parseEliteRatio(elite);
    c.stagnationThreshold = numericValue(data{i,idx.stagnation_threshold});
    c.theta = 1/13;
    c.archiveLimitFactor = 5;
    c.consensusArchive = false;
    c.archiveConsWeight = 0.0;
    c.bestGuide = 'rank';
    c.minSubpopSize = 1;
    c.S_level = numericValue(data{i,idx.S_level});
    c.operator_level = numericValue(data{i,idx.operator_level});
    c.migration_level = numericValue(data{i,idx.migration_level});
    c.elite_level = numericValue(data{i,idx.elite_level});
    c.tau_level = numericValue(data{i,idx.tau_level});
    candidates(end+1,1) = c; %#ok<AGROW>
end
end

function idx = findHeader(headers,name)
labels = cellfun(@scalarText,headers,'UniformOutput',false);
idx = find(strcmp(labels,name),1);
if isempty(idx)
    error('BayesConfig:MissingHeader','Missing header in L24 sheet: %s',name);
end
end

function thetaId = normalizeThetaId(rawThetaId,rowIndex)
tokens = regexp(rawThetaId,'(\d+)','tokens','once');
if isempty(tokens)
    number = rowIndex;
else
    number = str2double(tokens{1});
    if isnan(number)
        number = rowIndex;
    end
end
thetaId = sprintf('theta_%02d',number);
end

function manifest = loadManifest(manifestPath,scriptDir)
manifest = readtable(manifestPath);
for ii = 1:height(manifest)
    p = scalarText(manifest.path(ii));
    if isempty(regexp(p,'^[A-Za-z]:[\\/]', 'once'))
        p = fullfile(scriptDir,p);
    end
    manifest.path(ii) = {p};
end
end

function manifest = filterManifest(manifest,splits,instanceNames,maxInstances)
splitMask = false(height(manifest),1);
splitList = asCellstr(splits);
for si = 1:numel(splitList)
    splitMask = splitMask | strcmp(manifest.split,splitList{si});
end
manifest = manifest(splitMask,:);

names = asCellstr(instanceNames);
if ~isempty(names)
    nameMask = false(height(manifest),1);
    for ni = 1:numel(names)
        nameMask = nameMask | strcmp(manifest.instance,names{ni});
    end
    manifest = manifest(nameMask,:);
end

if isfinite(maxInstances)
    manifest = manifest(1:min(height(manifest),maxInstances),:);
end
end

function summary = rebuildSummary(root,methodFilter)
files = dir(fullfile(root,'**','runtime.csv'));
rows = {};
for fi = 1:numel(files)
    runDir = files(fi).folder;
    pfFile = fullfile(runDir,'pf_obj.csv');
    metaFile = fullfile(runDir,'theta_metadata.csv');
    if ~exist(pfFile,'file') || ~exist(metaFile,'file')
        continue;
    end
    meta = readtable(metaFile);
    method = scalarText(meta.method(1));
    if ~isempty(methodFilter) && ~strcmp(method,methodFilter)
        continue;
    end
    rt = readtable(fullfile(runDir,'runtime.csv'));
    pfObj = readmatrix(pfFile);
    feasibleRate = readFeasibleRate(runDir);
    runToken = regexp(runDir,[regexptranslate('escape',filesep) 'run_(\d+)$'],'tokens','once');
    if isempty(runToken)
        run = NaN;
    else
        run = str2double(runToken{1});
    end
    rows(end+1,:) = { ...
        method,scalarText(meta.split(1)),scalarText(meta.instance(1)), ...
        meta.assets(1),meta.K(1),meta.k_ratio(1), ...
        scalarText(meta.corr_structure(1)),scalarText(meta.return_distribution(1)), ...
        scalarText(meta.risk_structure(1)),meta.theta_index(1),scalarText(meta.theta_id(1)), ...
        meta.S(1),scalarText(meta.operator(1)),scalarText(meta.migration(1)), ...
        meta.elite_ratio(1),meta.stagnation_threshold(1), ...
        run,size(pfObj,1),rt.runtime_sec(1),mean(pfObj(:,1)),mean(-pfObj(:,2)), ...
        feasibleRate}; %#ok<AGROW>
end
if isempty(rows)
    summary = table();
else
    summary = cell2table(rows,'VariableNames',{ ...
        'method','split','instance','assets','K','k_ratio', ...
        'corr_structure','return_distribution','risk_structure', ...
        'theta_index','theta_id','S','operator','migration','elite_ratio', ...
        'stagnation_threshold','run','pf_size','runtime_sec','mean_risk', ...
        'mean_return','pf_feasible_rate'});
end
end

function writeAggregateSummary(summary,outPath)
if isempty(summary)
    return;
end
[keys,~,g] = unique(summary(:,{'method','split','instance','assets','K','theta_id','S','operator','migration','elite_ratio','stagnation_threshold'}),'rows','stable');
rows = {};
for i = 1:height(keys)
    mask = g == i;
    part = summary(mask,:);
    rows(end+1,:) = { ...
        keys.method{i},keys.split{i},keys.instance{i},keys.assets(i),keys.K(i), ...
        keys.theta_id{i},keys.S(i),keys.operator{i},keys.migration{i}, ...
        keys.elite_ratio(i),keys.stagnation_threshold(i),height(part), ...
        mean(part.pf_size),std(part.pf_size), ...
        mean(part.runtime_sec),std(part.runtime_sec), ...
        mean(part.mean_risk),std(part.mean_risk), ...
        mean(part.mean_return),std(part.mean_return), ...
        mean(part.pf_feasible_rate),std(part.pf_feasible_rate)}; %#ok<AGROW>
end
T = cell2table(rows,'VariableNames',{ ...
    'method','split','instance','assets','K','theta_id','S','operator','migration', ...
    'elite_ratio','stagnation_threshold','runs','mean_pf_size','std_pf_size', ...
    'mean_runtime_sec','std_runtime_sec','mean_risk','std_risk', ...
    'mean_return','std_return','mean_pf_feasible_rate','std_pf_feasible_rate'});
writetable(T,outPath);
end

function runRanker(scriptDir,outRoot)
ranker = fullfile(scriptDir,'rank_knowledge_base_parameter_search.py');
if exist(ranker,'file')
    cmd = sprintf('python "%s" --root "%s"',ranker,outRoot);
    status = system(cmd);
    if status ~= 0
        warning('BayesConfig:RankerFailed','Ranker command failed: %s',cmd);
    end
end
end

function writeProtocol(cfg,nCandidates,nConfigInstances,nFinalInstances)
fid = fopen(fullfile(cfg.outRoot,'bayesian_configuration_protocol.txt'),'w');
fprintf(fid,'purpose=Bayesian configuration ECMADE-MOO baseline for Experiment B\n');
fprintf(fid,'theta_excel=%s\n',cfg.thetaPath);
fprintf(fid,'theta_sheet=%s\n',cfg.thetaSheet);
fprintf(fid,'theta_candidates=%d\n',nCandidates);
fprintf(fid,'optimizer=discrete Gaussian-process surrogate with expected improvement\n');
fprintf(fid,'seed=%d\n',cfg.seed);
fprintf(fid,'config_splits=%s\n',strjoin(asCellstr(cfg.configSplits),','));
fprintf(fid,'config_instances=%d\n',nConfigInstances);
fprintf(fid,'config_runs=%d\n',cfg.configRuns);
fprintf(fid,'config_maxFE=%d\n',cfg.configMaxFE);
fprintf(fid,'budget=%d\n',cfg.budget);
fprintf(fid,'initial_random_points=%d\n',cfg.initialPoints);
fprintf(fid,'objective=mean_return - riskPenalty*mean_risk + feasibleBonus*feasibleRate + pfSizeWeight*log1p(pfSize) - runtimePenalty*runtime\n');
fprintf(fid,'riskPenalty=%.12g\n',cfg.riskPenalty);
fprintf(fid,'feasibleBonus=%.12g\n',cfg.feasibleBonus);
fprintf(fid,'pfSizeWeight=%.12g\n',cfg.pfSizeWeight);
fprintf(fid,'runtimePenalty=%.12g\n',cfg.runtimePenalty);
fprintf(fid,'final_splits=%s\n',strjoin(asCellstr(cfg.finalSplits),','));
fprintf(fid,'final_instances=%d\n',nFinalInstances);
fprintf(fid,'final_runs=%d\n',cfg.finalRuns);
fprintf(fid,'final_maxFE=%d\n',cfg.finalMaxFE);
fclose(fid);
end

function ok = hasCompleteRun(runDir)
ok = exist(fullfile(runDir,'pf_obj.csv'),'file') && ...
    exist(fullfile(runDir,'runtime.csv'),'file') && ...
    exist(fullfile(runDir,'generation_pf_points.csv'),'file') && ...
    exist(fullfile(runDir,'generation_population_log.csv'),'file') && ...
    exist(fullfile(runDir,'theta_metadata.csv'),'file');
end

function out = mapOperator(text)
text = lower(strtrim(text));
switch text
    case 'de/rand'
        out = 'rand2';
    case 'de/best'
        out = 'best2';
    case 'mixed'
        out = 'mixed';
    otherwise
        error('BayesConfig:UnknownOperator','Unknown operator: %s',text);
end
end

function out = mapMigration(text)
text = lower(strtrim(text));
switch text
    case 'none'
        out = 'none';
    case 'fixed'
        out = 'paper';
    case 'adaptive'
        out = 'stable';
    otherwise
        error('BayesConfig:UnknownMigration','Unknown migration: %s',text);
end
end

function value = parseEliteRatio(text)
hasPercent = contains(text,'%');
text = strrep(strtrim(text),'%','');
value = str2double(text);
if isnan(value)
    error('BayesConfig:BadEliteRatio','Cannot parse elite ratio: %s',text);
end
if hasPercent || value > 1
    value = value / 100;
end
end

function value = numericValue(x)
if isnumeric(x)
    value = x;
else
    value = str2double(scalarText(x));
end
if isnan(value)
    error('BayesConfig:BadNumber','Cannot parse numeric value: %s',scalarText(x));
end
end

function value = nanmeanLocal(x)
x = x(~isnan(x));
if isempty(x)
    value = NaN;
else
    value = mean(x);
end
end

function out = scalarText(x)
if iscell(x)
    if isempty(x)
        out = '';
    else
        out = scalarText(x{1});
    end
elseif isstring(x)
    if ismissing(x(1))
        out = '';
    else
        out = char(x(1));
    end
elseif isnumeric(x)
    if isempty(x) || any(isnan(x))
        out = '';
    else
        out = num2str(x);
    end
else
    out = char(x);
end
end

function out = asCellstr(x)
if isempty(x)
    out = {};
elseif iscell(x)
    out = x;
elseif isstring(x)
    out = cellstr(x);
else
    out = {x};
end
end
