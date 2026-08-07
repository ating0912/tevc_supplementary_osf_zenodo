function run_theta24_192instance_label_full()
% Full meta-learning label generation for the 70/15/15 Training split.

scriptDir = fileparts(mfilename('fullpath'));
thetaPath = fullfile(fileparts(scriptDir),'external_data','TEVC_P0_Selected_Theta_fractional_24.xlsx');
manifestPath = fullfile(scriptDir,'data','synthetic_constrained_portfolio','manifest_70_15_15.csv');
instanceRoot = fullfile(scriptDir,'data','synthetic_constrained_portfolio','instances_70_15_15','Training');

cfg = struct();
cfg.outRoot = fullfile(scriptDir,'p0_lite_outputs', ...
    ['theta24_70_15_15_training_label_full_' datestr(now,'yyyymmdd_HHMMSS')]);
cfg.runs = 30;
cfg.N = 100;
cfg.maxFE = 10000;
cfg.splits = {'Training'};
cfg.maxInstances = 192;

if evalin('base','exist(''THETA24_FULL_OUT_ROOT'',''var'')')
    cfg.outRoot = evalin('base','THETA24_FULL_OUT_ROOT');
end
if evalin('base','exist(''THETA24_FULL_RUNS'',''var'')')
    cfg.runs = evalin('base','THETA24_FULL_RUNS');
end
if evalin('base','exist(''THETA24_FULL_MAX_INSTANCES'',''var'')')
    cfg.maxInstances = evalin('base','THETA24_FULL_MAX_INSTANCES');
end
if evalin('base','exist(''THETA24_FULL_SPLITS'',''var'')')
    cfg.splits = evalin('base','THETA24_FULL_SPLITS');
end

if ~exist(thetaPath,'file')
    error('Theta Excel file not found: %s',thetaPath);
end
if ~exist(manifestPath,'file')
    error('Synthetic manifest not found: %s',manifestPath);
end
if ~exist(instanceRoot,'dir')
    error('Training instance folder not found: %s',instanceRoot);
end
if ~exist(cfg.outRoot,'dir')
    mkdir(cfg.outRoot);
end

thetaTable = readtable(thetaPath,'Sheet','Selected_Theta');
thetaTable = thetaTable(~cellfun(@isempty,tableCellstr(thetaTable.theta_id)),:);
candidates = tableToCandidates(thetaTable);
allCandidates = candidates;
if evalin('base','exist(''THETA24_FULL_METHODS'',''var'')')
    methodFilter = asCellstr(evalin('base','THETA24_FULL_METHODS'));
    keep = false(numel(candidates),1);
    for ci = 1:numel(candidates)
        keep(ci) = any(strcmp(candidates(ci).method,methodFilter));
    end
    candidates = candidates(keep);
    if isempty(candidates)
        error('Theta24Full:NoCandidates','No theta candidates matched THETA24_FULL_METHODS.');
    end
end
writetable(struct2table(allCandidates),fullfile(cfg.outRoot,'kb_theta_candidates.csv'));
selectedCount = writeSelectedInstances(scriptDir,manifestPath,cfg);
writeProtocol(cfg,thetaPath,manifestPath,instanceRoot,numel(candidates),selectedCount);

assignin('base','SYNTHETIC_OUT_ROOT',cfg.outRoot);
assignin('base','SYNTHETIC_MANIFEST',manifestPath);
assignin('base','SYNTHETIC_SPLITS',cfg.splits);
assignin('base','SYNTHETIC_RUNS',cfg.runs);
assignin('base','SYNTHETIC_N',cfg.N);
assignin('base','SYNTHETIC_MAXFE',cfg.maxFE);
assignin('base','SYNTHETIC_MAX_INSTANCES',cfg.maxInstances);
assignin('base','SYNTHETIC_SKIP_SUMMARY',true);
assignin('base','SYNTHETIC_FORCE_RERUN',false);

cleanup = onCleanup(@() clearFullWorkspaceVars());

fprintf('Theta24 70/15/15 Training label full run\n');
fprintf('Splits: %s\n',strjoin(cfg.splits,','));
fprintf('Instances: first %d selected rows from manifest; selected %d rows\n', ...
    cfg.maxInstances,selectedCount);
fprintf('Theta candidates: %d, runs per instance-theta: %d, N=%d, maxFE=%d\n', ...
    numel(candidates),cfg.runs,cfg.N,cfg.maxFE);
fprintf('Expected runs: %d\n',selectedCount*numel(candidates)*cfg.runs);
fprintf('Output: %s\n',cfg.outRoot);

for ci = 1:numel(candidates)
    assignin('base','ECMADE_MOO_KB_THETA',candidates(ci));
    fprintf('=== %s | S=%d | operator=%s | migration=%s | rho=%.3g | tau=%d ===\n', ...
        candidates(ci).method,candidates(ci).subpops,candidates(ci).operatorMode, ...
        candidates(ci).exchangeMode,candidates(ci).eliteRatio,candidates(ci).stagnationThreshold);
    SyntheticRunner.runAlgorithm(@ECMADE_MOO_KB,candidates(ci).method);
end

evalin('base','clear ECMADE_MOO_KB_THETA');
runRanker(scriptDir,cfg.outRoot);

fprintf('Done. Report folder: %s\n',fullfile(cfg.outRoot,'knowledge_base_parameter_report'));
end

function candidates = tableToCandidates(T)
candidates = struct('method',{},'source_theta_id',{},'source_operator',{}, ...
    'source_migration',{},'source_elite_ratio',{},'source_archive_strategy',{}, ...
    'source_constraint_handling',{},'subpops',{},'operatorMode',{}, ...
    'exchangeMode',{},'eliteRatio',{},'stagnationThreshold',{},'theta',{}, ...
    'archiveLimitFactor',{},'consensusArchive',{},'archiveConsWeight',{}, ...
    'bestGuide',{},'minSubpopSize',{});

for i = 1:height(T)
    thetaId = scalarText(T.theta_id(i));
    op = scalarText(T.operator(i));
    mig = scalarText(T.migration(i));
    elite = scalarText(T.elite_ratio(i));
    c = struct();
    c.method = thetaId;
    c.source_theta_id = thetaId;
    c.source_operator = op;
    c.source_migration = mig;
    c.source_elite_ratio = elite;
    c.source_archive_strategy = scalarText(T.archive_strategy(i));
    c.source_constraint_handling = scalarText(T.constraint_handling(i));
    c.subpops = T.S(i);
    c.operatorMode = mapOperator(op);
    c.exchangeMode = mapMigration(mig);
    c.eliteRatio = parseEliteRatio(elite);
    c.stagnationThreshold = T.stagnation_threshold(i);
    c.theta = 1/13;
    c.archiveLimitFactor = 5;
    c.consensusArchive = false;
    c.archiveConsWeight = 0.0;
    c.bestGuide = 'rank';
    c.minSubpopSize = 1;
    candidates(end+1,1) = c; %#ok<AGROW>
end
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
        error('Unknown operator: %s',text);
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
        error('Unknown migration: %s',text);
end
end

function value = parseEliteRatio(text)
hasPercent = contains(text,'%');
text = strrep(strtrim(text),'%','');
value = str2double(text);
if isnan(value)
    error('Cannot parse elite ratio: %s',text);
end
if hasPercent || value > 1
    value = value / 100;
end
end

function out = scalarText(x)
if iscell(x)
    out = x{1};
elseif isstring(x)
    out = char(x(1));
elseif isnumeric(x)
    out = num2str(x);
else
    out = char(x);
end
end

function out = tableCellstr(x)
out = cell(size(x));
for i = 1:numel(x)
    out{i} = scalarText(x(i));
end
end

function writeProtocol(cfg,thetaPath,manifestPath,instanceRoot,nCandidates,selectedCount)
fid = fopen(fullfile(cfg.outRoot,'theta24_70_15_15_training_label_protocol.txt'),'w');
fprintf(fid,'purpose=full meta-learning label generation\n');
fprintf(fid,'label_protocol=%d selected instances x %d theta x %d independent runs\n', ...
    selectedCount,nCandidates,cfg.runs);
fprintf(fid,'theta_excel=%s\n',thetaPath);
fprintf(fid,'manifest=%s\n',manifestPath);
fprintf(fid,'instance_root=%s\n',instanceRoot);
fprintf(fid,'splits=%s\n',strjoin(cfg.splits,','));
fprintf(fid,'max_instances=%d\n',cfg.maxInstances);
fprintf(fid,'selected_instances=%d\n',selectedCount);
fprintf(fid,'theta_candidates=%d\n',nCandidates);
fprintf(fid,'runs=%d\n',cfg.runs);
fprintf(fid,'N=%d\n',cfg.N);
fprintf(fid,'maxFE=%d\n',cfg.maxFE);
fprintf(fid,'score=rank average over HV(max), IGD(min), PF_Overlap(max), PF_Drift(min), Runtime(min)\n');
fprintf(fid,'labels=top1_classification_labels.csv, theta_ranking_labels.csv, regression_score_labels.csv\n');
fclose(fid);
end

function selectedCount = writeSelectedInstances(scriptDir,manifestPath,cfg)
manifest = readtable(manifestPath);
mask = false(height(manifest),1);
splits = asCellstr(cfg.splits);
for si = 1:numel(splits)
    mask = mask | strcmp(manifest.split,splits{si});
end
selected = manifest(mask,:);
selected = selected(1:min(cfg.maxInstances,height(selected)),:);
for i = 1:height(selected)
    p = scalarText(selected.path(i));
    if isempty(regexp(p,'^[A-Za-z]:[\\/]', 'once'))
        p = fullfile(scriptDir,p);
    end
    selected.path(i) = {p};
end
selectedCount = height(selected);
writetable(selected,fullfile(cfg.outRoot,'selected_70_15_15_training_instances.csv'));
end

function out = asCellstr(x)
if ischar(x)
    out = {x};
elseif isstring(x)
    out = cellstr(x);
elseif iscell(x)
    out = x;
else
    error('Expected char, string, or cell array.');
end
end

function runRanker(scriptDir,outRoot)
ranker = fullfile(scriptDir,'rank_knowledge_base_parameter_search.py');
if exist(ranker,'file')
    cmd = sprintf('python "%s" --root "%s"',ranker,outRoot);
    status = system(cmd);
    if status ~= 0
        warning('Theta24Full:RankerFailed','Ranker command failed: %s',cmd);
    end
end
end

function clearFullWorkspaceVars()
evalin('base',['clear ECMADE_MOO_KB_THETA SYNTHETIC_OUT_ROOT SYNTHETIC_MANIFEST ' ...
    'SYNTHETIC_SPLITS SYNTHETIC_RUNS SYNTHETIC_N SYNTHETIC_MAXFE ' ...
    'SYNTHETIC_MAX_INSTANCES SYNTHETIC_SKIP_SUMMARY SYNTHETIC_FORCE_RERUN']);
end
