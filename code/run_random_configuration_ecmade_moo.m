function run_random_configuration_ecmade_moo()
% Random configuration ECMADE-MOO baseline for TEVC Experiment B.
%
% Default protocol:
%   1. Read the TEVC P0 L24 theta library from the approved Excel file.
%   2. For each unseen test instance, sample one theta uniformly at random.
%   3. Run ECMADE_MOO_KB with the sampled theta for 30 independent runs.
%   4. Save the random assignment log, per-run theta metadata, PF outputs,
%      feasibility logs, and an aggregate summary.
%
% Optional base-workspace overrides:
%   RANDOM_CONFIG_THETA_PATH, RANDOM_CONFIG_MANIFEST, RANDOM_CONFIG_OUT_ROOT
%   RANDOM_CONFIG_SPLITS, RANDOM_CONFIG_RUNS, RANDOM_CONFIG_N
%   RANDOM_CONFIG_MAXFE, RANDOM_CONFIG_MAX_INSTANCES
%   RANDOM_CONFIG_INSTANCE_NAMES, RANDOM_CONFIG_ASSIGNMENT_SEED
%   RANDOM_CONFIG_FORCE_RERUN

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');

cfg = struct();
cfg.method = 'RandomConfig_ECMADE_MOO';
cfg.thetaPath = fullfile(fileparts(scriptDir),'external_data','TEVC_P0_L24_Orthogonal_Theta_Configurations.xlsx');
cfg.thetaSheet = 'L24_Theta_Config';
cfg.manifestPath = fullfile(scriptDir,'data','synthetic_constrained_portfolio','manifest.csv');
cfg.outRoot = fullfile(scriptDir,'p0_lite_outputs', ...
    ['random_config_ecmade_moo_' datestr(now,'yyyymmdd_HHMMSS')]);
cfg.splits = {'test'};
cfg.runs = 30;
cfg.N = 100;
cfg.maxFE = 10000;
cfg.saveGenerations = cfg.maxFE / cfg.N;
cfg.rngType = 'mcg16807';
cfg.maxInstances = inf;
cfg.instanceNames = {};
cfg.assignmentSeed = 20260709;
cfg.forceRerun = false;

cfg = applyWorkspaceOverrides(cfg);
cfg.saveGenerations = max(1,cfg.maxFE / cfg.N);

if ~exist(cfg.thetaPath,'file')
    error('RandomConfig:MissingThetaFile','Theta Excel file not found: %s',cfg.thetaPath);
end
if ~exist(cfg.manifestPath,'file')
    error('RandomConfig:MissingManifest','Manifest file not found: %s',cfg.manifestPath);
end
if ~exist(platemoRoot,'dir')
    error('RandomConfig:MissingPlatEMO','PlatEMO root not found: %s',platemoRoot);
end
if ~exist(cfg.outRoot,'dir')
    mkdir(cfg.outRoot);
end

restoredefaultpath;
addpath(genpath(platemoRoot));
addpath(scriptDir);

candidates = readL24Candidates(cfg.thetaPath,cfg.thetaSheet);
manifest = loadManifest(cfg.manifestPath,scriptDir);
manifest = filterManifest(manifest,cfg);
assignments = sampleRandomThetaAssignments(manifest,candidates,cfg.assignmentSeed);

writetable(struct2table(candidates),fullfile(cfg.outRoot,'l24_theta_candidates.csv'));
writetable(assignments,fullfile(cfg.outRoot,'random_config_assignment.csv'));
writeProtocol(cfg,height(manifest),numel(candidates));

cleanup = onCleanup(@() evalin('base','clear ECMADE_MOO_KB_THETA'));

fprintf('Random configuration ECMADE-MOO baseline\n');
fprintf('Theta Excel: %s\n',cfg.thetaPath);
fprintf('Manifest: %s\n',cfg.manifestPath);
fprintf('Selected instances: %d, splits=%s\n',height(manifest),strjoin(asCellstr(cfg.splits),','));
fprintf('Runs per instance: %d, N=%d, maxFE=%d\n',cfg.runs,cfg.N,cfg.maxFE);
fprintf('Assignment seed: %d\n',cfg.assignmentSeed);
fprintf('Output: %s\n',cfg.outRoot);

for ii = 1:height(manifest)
    row = manifest(ii,:);
    instance = scalarText(row.instance);
    splitName = scalarText(row.split);
    dataPath = scalarText(row.path);
    K = row.K;
    nAssets = row.assets;

    thetaCfg = candidates(assignments.theta_index(ii));
    assignin('base','ECMADE_MOO_KB_THETA',thetaCfg);

    fprintf('=== %s | %s | K=%d | %s sampled %s ===\n', ...
        splitName,instance,K,cfg.method,thetaCfg.source_theta_id);
    fprintf('    S=%d operator=%s migration=%s elite=%.3g tau=%d\n', ...
        thetaCfg.subpops,thetaCfg.operatorMode,thetaCfg.exchangeMode, ...
        thetaCfg.eliteRatio,thetaCfg.stagnationThreshold);

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

        writeRunMetadata(runDir,row,thetaCfg,cfg,ii,assignments.theta_index(ii));

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

summary = rebuildRandomConfigSummary(cfg.outRoot,cfg.method);
if ~isempty(summary)
    writetable(summary,fullfile(cfg.outRoot,'random_config_run_summary.csv'));
    writeAggregateSummary(summary,fullfile(cfg.outRoot,'random_config_summary_by_instance.csv'));
end

fprintf('Done. Assignment log: %s\n',fullfile(cfg.outRoot,'random_config_assignment.csv'));
fprintf('Done. Summary: %s\n',fullfile(cfg.outRoot,'random_config_run_summary.csv'));
end

function cfg = applyWorkspaceOverrides(cfg)
cfg = overrideValue(cfg,'RANDOM_CONFIG_THETA_PATH','thetaPath');
cfg = overrideValue(cfg,'RANDOM_CONFIG_MANIFEST','manifestPath');
cfg = overrideValue(cfg,'RANDOM_CONFIG_OUT_ROOT','outRoot');
cfg = overrideValue(cfg,'RANDOM_CONFIG_SPLITS','splits');
cfg = overrideValue(cfg,'RANDOM_CONFIG_RUNS','runs');
cfg = overrideValue(cfg,'RANDOM_CONFIG_N','N');
cfg = overrideValue(cfg,'RANDOM_CONFIG_MAXFE','maxFE');
cfg = overrideValue(cfg,'RANDOM_CONFIG_MAX_INSTANCES','maxInstances');
cfg = overrideValue(cfg,'RANDOM_CONFIG_INSTANCE_NAMES','instanceNames');
cfg = overrideValue(cfg,'RANDOM_CONFIG_ASSIGNMENT_SEED','assignmentSeed');
cfg = overrideValue(cfg,'RANDOM_CONFIG_FORCE_RERUN','forceRerun');
end

function cfg = overrideValue(cfg,varName,fieldName)
if evalin('base',sprintf('exist(''%s'',''var'')',varName))
    cfg.(fieldName) = evalin('base',varName);
end
end

function candidates = readL24Candidates(thetaPath,sheetName)
raw = readcell(thetaPath,'Sheet',sheetName);
headers = raw(4,:);
data = raw(5:28,:);

idx.theta_id = findHeader(headers,'theta_id');
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
    'bestGuide',{},'minSubpopSize',{});

for i = 1:size(data,1)
    rawThetaId = scalarText(data{i,idx.theta_id});
    if isempty(rawThetaId) || all(ismissingString(rawThetaId))
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
    candidates(end+1,1) = c; %#ok<AGROW>
end

if numel(candidates) ~= 24
    warning('RandomConfig:ThetaCount','Expected 24 theta rows, found %d.',numel(candidates));
end
end

function idx = findHeader(headers,name)
labels = cellfun(@scalarText,headers,'UniformOutput',false);
idx = find(strcmp(labels,name),1);
if isempty(idx)
    error('RandomConfig:MissingHeader','Missing header in L24 sheet: %s',name);
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

function manifest = filterManifest(manifest,cfg)
splits = asCellstr(cfg.splits);
splitMask = false(height(manifest),1);
for si = 1:numel(splits)
    splitMask = splitMask | strcmp(manifest.split,splits{si});
end
manifest = manifest(splitMask,:);

names = asCellstr(cfg.instanceNames);
if ~isempty(names)
    nameMask = false(height(manifest),1);
    for ni = 1:numel(names)
        nameMask = nameMask | strcmp(manifest.instance,names{ni});
    end
    manifest = manifest(nameMask,:);
end

if isfinite(cfg.maxInstances)
    manifest = manifest(1:min(height(manifest),cfg.maxInstances),:);
end
end

function assignments = sampleRandomThetaAssignments(manifest,candidates,assignmentSeed)
rng(assignmentSeed,'twister');
n = height(manifest);
thetaIndex = randi(numel(candidates),n,1);
rows = cell(n,14);
for i = 1:n
    c = candidates(thetaIndex(i));
    rows(i,:) = { ...
        i,scalarText(manifest.split(i)),scalarText(manifest.instance(i)), ...
        manifest.assets(i),manifest.K(i),thetaIndex(i),c.source_theta_id, ...
        c.subpops,c.source_operator,c.source_migration,c.source_elite_ratio, ...
        c.stagnationThreshold,c.source_archive_strategy,c.source_constraint_handling};
end
assignments = cell2table(rows,'VariableNames',{ ...
    'manifest_row','split','instance','assets','K','theta_index','theta_id', ...
    'S','operator','migration','elite_ratio','stagnation_threshold', ...
    'archive_strategy','constraint_handling'});
end

function writeProtocol(cfg,nInstances,nCandidates)
fid = fopen(fullfile(cfg.outRoot,'random_config_protocol.txt'),'w');
fprintf(fid,'purpose=Random configuration ECMADE-MOO baseline for Experiment B\n');
fprintf(fid,'theta_excel=%s\n',cfg.thetaPath);
fprintf(fid,'theta_sheet=%s\n',cfg.thetaSheet);
fprintf(fid,'theta_candidates=%d\n',nCandidates);
fprintf(fid,'selection_rule=sample one theta uniformly at random per selected instance\n');
fprintf(fid,'assignment_seed=%d\n',cfg.assignmentSeed);
fprintf(fid,'manifest=%s\n',cfg.manifestPath);
fprintf(fid,'splits=%s\n',strjoin(asCellstr(cfg.splits),','));
fprintf(fid,'selected_instances=%d\n',nInstances);
fprintf(fid,'runs=%d\n',cfg.runs);
fprintf(fid,'N=%d\n',cfg.N);
fprintf(fid,'maxFE=%d\n',cfg.maxFE);
fprintf(fid,'rng=%s\n',cfg.rngType);
fprintf(fid,'seed_rule=optimization seed equals run index\n');
fprintf(fid,'test_leakage_rule=random theta selection does not inspect test performance\n');
fclose(fid);
end

function writeRunMetadata(runDir,row,thetaCfg,cfg,manifestRow,thetaIndex)
T = table();
T.method = {cfg.method};
T.random_config_protocol = {'one uniform random theta per instance'};
T.assignment_seed = cfg.assignmentSeed;
T.manifest_row = manifestRow;
T.theta_index = thetaIndex;
T.theta_id = {thetaCfg.source_theta_id};
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
T.N = cfg.N;
T.maxFE = cfg.maxFE;
T.runs = cfg.runs;
T.dataPath = row.path;
writetable(T,fullfile(runDir,'theta_metadata.csv'));
end

function summary = rebuildRandomConfigSummary(outRoot,method)
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
        error('RandomConfig:UnknownOperator','Unknown operator: %s',text);
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
        error('RandomConfig:UnknownMigration','Unknown migration: %s',text);
end
end

function value = parseEliteRatio(text)
hasPercent = contains(text,'%');
text = strrep(strtrim(text),'%','');
value = str2double(text);
if isnan(value)
    error('RandomConfig:BadEliteRatio','Cannot parse elite ratio: %s',text);
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
    error('RandomConfig:BadNumber','Cannot parse numeric value: %s',scalarText(x));
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

function tf = ismissingString(text)
tf = isempty(strtrim(text)) || strcmpi(strtrim(text),'missing');
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
