function run_meta_designed_ecmade_moo()
% Meta-designed ECMADE-MOO runner for TEVC Experiment B.
%
% This script reads per-instance theta assignments produced by
% train_meta_designed_ecmade_moo.py and evaluates ECMADE_MOO_KB on the
% assigned theta for each unseen test instance.
%
% Optional base-workspace overrides:
%   META_DESIGNED_METHOD, META_DESIGNED_ASSIGNMENT_PATH, META_DESIGNED_OUT_ROOT
%   META_DESIGNED_RUNS, META_DESIGNED_N, META_DESIGNED_MAXFE
%   META_DESIGNED_MAX_INSTANCES, META_DESIGNED_INSTANCE_NAMES
%   META_DESIGNED_FORCE_RERUN

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');

cfg = struct();
cfg.method = 'MetaDesigned_ECMADE_MOO';
cfg.assignmentPath = fullfile(scriptDir,'p0_lite_outputs', ...
    'meta_designed_ecmade_moo_training','meta_designed_theta_assignment.csv');
cfg.outRoot = fullfile(scriptDir,'p0_lite_outputs', ...
    ['meta_designed_ecmade_moo_' datestr(now,'yyyymmdd_HHMMSS')]);
cfg.runs = 30;
cfg.N = 100;
cfg.maxFE = 10000;
cfg.saveGenerations = cfg.maxFE / cfg.N;
cfg.rngType = 'mcg16807';
cfg.maxInstances = inf;
cfg.instanceNames = {};
cfg.forceRerun = false;

cfg = applyWorkspaceOverrides(cfg);
cfg.saveGenerations = max(1,cfg.maxFE / cfg.N);

if ~exist(cfg.assignmentPath,'file')
    error('MetaDesigned:MissingAssignment','Assignment file not found: %s',cfg.assignmentPath);
end
if ~exist(platemoRoot,'dir')
    error('MetaDesigned:MissingPlatEMO','PlatEMO root not found: %s',platemoRoot);
end
if ~exist(cfg.outRoot,'dir')
    mkdir(cfg.outRoot);
end

restoredefaultpath;
addpath(genpath(platemoRoot));
addpath(scriptDir);

assignments = readtable(cfg.assignmentPath);
assignments = filterAssignments(assignments,cfg);
writetable(assignments,fullfile(cfg.outRoot,'meta_designed_theta_assignment_used.csv'));
writeProtocol(cfg,height(assignments));

cleanup = onCleanup(@() evalin('base','clear ECMADE_MOO_KB_THETA'));

fprintf('Meta-designed ECMADE-MOO evaluation\n');
fprintf('Assignment: %s\n',cfg.assignmentPath);
fprintf('Selected instances: %d\n',height(assignments));
fprintf('Runs per instance: %d, N=%d, maxFE=%d\n',cfg.runs,cfg.N,cfg.maxFE);
fprintf('Output: %s\n',cfg.outRoot);

for ii = 1:height(assignments)
    row = assignments(ii,:);
    instance = scalarText(row.instance);
    splitName = scalarText(row.split);
    dataPath = scalarText(row.path);
    if isempty(regexp(dataPath,'^[A-Za-z]:[\\/]', 'once'))
        dataPath = fullfile(scriptDir,dataPath);
    end
    K = row.K;
    nAssets = row.assets;
    thetaCfg = assignmentToTheta(row);
    assignin('base','ECMADE_MOO_KB_THETA',thetaCfg);

    fprintf('=== %s | %s | K=%d | %s selected %s ===\n', ...
        splitName,instance,K,cfg.method,thetaCfg.source_theta_id);
    fprintf('    predicted_score=%.8g | S=%d operator=%s migration=%s elite=%.3g tau=%d\n', ...
        row.predicted_score,thetaCfg.subpops,thetaCfg.operatorMode, ...
        thetaCfg.exchangeMode,thetaCfg.eliteRatio,thetaCfg.stagnationThreshold);

    for run = 1:cfg.runs
        runDir = fullfile(cfg.outRoot,splitName,instance, ...
            sprintf('K_%02d',K),cfg.method,sprintf('run_%03d',run));

        if ~cfg.forceRerun && hasCompleteRun(runDir)
            fprintf('%s %s run %03d already complete; skipping.\n',cfg.method,instance,run);
            continue;
        end
        if ~exist(runDir,'dir')
            mkdir(runDir);
        end

        writeRunMetadata(runDir,row,thetaCfg,cfg,ii,dataPath);

        fprintf('%s %s Run %03d/%03d\n',cfg.method,instance,run,cfg.runs);
        rng(run,cfg.rngType);
        t = tic;
        G = GLOBAL('-algorithm',@ECMADE_MOO_KB, ...
            '-problem',{@PortfolioORLIB,dataPath,K}, ...
            '-N',cfg.N,'-M',2,'-D',nAssets, ...
            '-evaluation',cfg.maxFE,'-run',run, ...
            '-save',cfg.saveGenerations,'-outputFcn',@(varargin)[]);
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

summary = rebuildSummary(cfg.outRoot,cfg.method);
if ~isempty(summary)
    writetable(summary,fullfile(cfg.outRoot,'meta_designed_run_summary.csv'));
    writeAggregateSummary(summary,fullfile(cfg.outRoot,'meta_designed_summary_by_instance.csv'));
end

runRanker(scriptDir,cfg.outRoot);

fprintf('Done. Assignment used: %s\n',fullfile(cfg.outRoot,'meta_designed_theta_assignment_used.csv'));
fprintf('Done. Summary: %s\n',fullfile(cfg.outRoot,'meta_designed_run_summary.csv'));
end

function cfg = applyWorkspaceOverrides(cfg)
cfg = overrideValue(cfg,'META_DESIGNED_METHOD','method');
cfg = overrideValue(cfg,'META_DESIGNED_ASSIGNMENT_PATH','assignmentPath');
cfg = overrideValue(cfg,'META_DESIGNED_OUT_ROOT','outRoot');
cfg = overrideValue(cfg,'META_DESIGNED_RUNS','runs');
cfg = overrideValue(cfg,'META_DESIGNED_N','N');
cfg = overrideValue(cfg,'META_DESIGNED_MAXFE','maxFE');
cfg = overrideValue(cfg,'META_DESIGNED_MAX_INSTANCES','maxInstances');
cfg = overrideValue(cfg,'META_DESIGNED_INSTANCE_NAMES','instanceNames');
cfg = overrideValue(cfg,'META_DESIGNED_FORCE_RERUN','forceRerun');
end

function cfg = overrideValue(cfg,varName,fieldName)
if evalin('base',sprintf('exist(''%s'',''var'')',varName))
    cfg.(fieldName) = evalin('base',varName);
end
end

function assignments = filterAssignments(assignments,cfg)
names = asCellstr(cfg.instanceNames);
if ~isempty(names)
    mask = false(height(assignments),1);
    for i = 1:numel(names)
        mask = mask | strcmp(assignments.instance,names{i});
    end
    assignments = assignments(mask,:);
end
if isfinite(cfg.maxInstances)
    assignments = assignments(1:min(height(assignments),cfg.maxInstances),:);
end
end

function thetaCfg = assignmentToTheta(row)
thetaId = scalarText(row.theta_id);
op = scalarText(row.operator);
mig = scalarText(row.migration);
thetaCfg = struct();
thetaCfg.method = thetaId;
thetaCfg.source_theta_id = thetaId;
thetaCfg.source_operator = op;
thetaCfg.source_migration = mig;
thetaCfg.source_elite_ratio = num2str(row.elite_ratio);
thetaCfg.source_archive_strategy = 'crowding-pruned';
thetaCfg.source_constraint_handling = 'repair+feasible-first';
thetaCfg.subpops = row.S;
thetaCfg.operatorMode = mapOperator(op);
thetaCfg.exchangeMode = mapMigration(mig);
thetaCfg.eliteRatio = row.elite_ratio;
thetaCfg.stagnationThreshold = row.stagnation_threshold;
thetaCfg.theta = 1/13;
thetaCfg.archiveLimitFactor = 5;
thetaCfg.consensusArchive = false;
thetaCfg.archiveConsWeight = 0.0;
thetaCfg.bestGuide = 'rank';
thetaCfg.minSubpopSize = 1;
end

function writeProtocol(cfg,nInstances)
fid = fopen(fullfile(cfg.outRoot,'meta_designed_protocol.txt'),'w');
fprintf(fid,'purpose=Meta-designed ECMADE-MOO evaluation for Experiment B\n');
fprintf(fid,'assignment=%s\n',cfg.assignmentPath);
fprintf(fid,'selection_rule=theta predicted by trained meta-learner per unseen test instance\n');
fprintf(fid,'selected_instances=%d\n',nInstances);
fprintf(fid,'runs=%d\n',cfg.runs);
fprintf(fid,'N=%d\n',cfg.N);
fprintf(fid,'maxFE=%d\n',cfg.maxFE);
fprintf(fid,'rng=%s\n',cfg.rngType);
fprintf(fid,'seed_rule=optimization seed equals run index\n');
fclose(fid);
end

function writeRunMetadata(runDir,row,thetaCfg,cfg,assignmentRow,dataPath)
T = table();
T.method = {cfg.method};
T.meta_designed_protocol = {'trained meta-learner selected theta per instance'};
T.assignment_row = assignmentRow;
T.theta_index = row.theta_index;
T.theta_id = {thetaCfg.source_theta_id};
T.predicted_score = row.predicted_score;
T.S = thetaCfg.subpops;
T.operator = {thetaCfg.source_operator};
T.operatorMode = {thetaCfg.operatorMode};
T.migration = {thetaCfg.source_migration};
T.exchangeMode = {thetaCfg.exchangeMode};
T.elite_ratio = thetaCfg.eliteRatio;
T.stagnation_threshold = thetaCfg.stagnationThreshold;
T.archive_strategy = {thetaCfg.source_archive_strategy};
T.constraint_handling = {thetaCfg.source_constraint_handling};
T.instance = row.instance;
T.split = row.split;
T.assets = row.assets;
T.K = row.K;
T.k_ratio = row.k_ratio;
T.N = cfg.N;
T.maxFE = cfg.maxFE;
T.runs = cfg.runs;
T.dataPath = {dataPath};
writetable(T,fullfile(runDir,'theta_metadata.csv'));
end

function summary = rebuildSummary(outRoot,method)
files = dir(fullfile(outRoot,'**','runtime.csv'));
rows = {};
for fi = 1:numel(files)
    runDir = files(fi).folder;
    pfFile = fullfile(runDir,'pf_obj.csv');
    metaFile = fullfile(runDir,'theta_metadata.csv');
    if ~exist(pfFile,'file') || ~exist(metaFile,'file')
        continue;
    end
    meta = readtable(metaFile);
    if ~strcmp(scalarText(meta.method(1)),method)
        continue;
    end
    rt = readtable(fullfile(runDir,'runtime.csv'));
    pfObj = readmatrix(pfFile);
    feasibleRate = NaN;
    feasibleFile = fullfile(runDir,'feasible_rate.csv');
    if exist(feasibleFile,'file')
        feas = readtable(feasibleFile);
        feasibleRate = feas.PF_Feasible_Rate(1);
    end
    runToken = regexp(runDir,[regexptranslate('escape',filesep) 'run_(\d+)$'],'tokens','once');
    if isempty(runToken)
        run = NaN;
    else
        run = str2double(runToken{1});
    end
    rows(end+1,:) = { ...
        method,scalarText(meta.split(1)),scalarText(meta.instance(1)), ...
        meta.assets(1),meta.K(1),meta.k_ratio(1), ...
        meta.theta_index(1),scalarText(meta.theta_id(1)),meta.predicted_score(1), ...
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
        'theta_index','theta_id','predicted_score','S','operator','migration', ...
        'elite_ratio','stagnation_threshold','run','pf_size','runtime_sec', ...
        'mean_risk','mean_return','pf_feasible_rate'});
end
end

function writeAggregateSummary(summary,outPath)
if isempty(summary)
    return;
end
[keys,~,g] = unique(summary(:,{'method','split','instance','assets','K','theta_id','predicted_score','S','operator','migration','elite_ratio','stagnation_threshold'}),'rows','stable');
rows = {};
for i = 1:height(keys)
    mask = g == i;
    part = summary(mask,:);
    rows(end+1,:) = { ...
        keys.method{i},keys.split{i},keys.instance{i},keys.assets(i),keys.K(i), ...
        keys.theta_id{i},keys.predicted_score(i),keys.S(i),keys.operator{i},keys.migration{i}, ...
        keys.elite_ratio(i),keys.stagnation_threshold(i),height(part), ...
        mean(part.pf_size),std(part.pf_size), ...
        mean(part.runtime_sec),std(part.runtime_sec), ...
        mean(part.mean_risk),std(part.mean_risk), ...
        mean(part.mean_return),std(part.mean_return), ...
        mean(part.pf_feasible_rate),std(part.pf_feasible_rate)}; %#ok<AGROW>
end
T = cell2table(rows,'VariableNames',{ ...
    'method','split','instance','assets','K','theta_id','predicted_score','S','operator','migration', ...
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
        warning('MetaDesigned:RankerFailed','Ranker command failed: %s',cmd);
    end
end
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
        error('MetaDesigned:UnknownOperator','Unknown operator: %s',text);
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
        error('MetaDesigned:UnknownMigration','Unknown migration: %s',text);
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
