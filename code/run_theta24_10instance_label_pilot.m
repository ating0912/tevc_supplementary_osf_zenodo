function run_theta24_10instance_label_pilot()
% Pilot meta-learning label generation: 10 training instances x 24 theta x 30 runs.

scriptDir = fileparts(mfilename('fullpath'));
thetaPath = 'C:\Users\yiting\Desktop\NCHU\lab\TEVC\TEVC_P0_Selected_Theta_fractional_24.xlsx';
manifestPath = fullfile(scriptDir,'data','synthetic_constrained_portfolio','manifest.csv');

cfg = struct();
cfg.outRoot = fullfile(scriptDir,'p0_lite_outputs', ...
    ['theta24_10instance_label_pilot_' datestr(now,'yyyymmdd_HHMMSS')]);
cfg.runs = 30;
cfg.N = 100;
cfg.maxFE = 10000;
cfg.splits = {'train'};
cfg.maxInstances = 10;

if evalin('base','exist(''THETA24_PILOT_OUT_ROOT'',''var'')')
    cfg.outRoot = evalin('base','THETA24_PILOT_OUT_ROOT');
end
if evalin('base','exist(''THETA24_PILOT_RUNS'',''var'')')
    cfg.runs = evalin('base','THETA24_PILOT_RUNS');
end
if evalin('base','exist(''THETA24_PILOT_MAX_INSTANCES'',''var'')')
    cfg.maxInstances = evalin('base','THETA24_PILOT_MAX_INSTANCES');
end

if ~exist(thetaPath,'file')
    error('Theta Excel file not found: %s',thetaPath);
end
if ~exist(manifestPath,'file')
    error('Synthetic manifest not found: %s',manifestPath);
end
if ~exist(cfg.outRoot,'dir')
    mkdir(cfg.outRoot);
end

thetaTable = readtable(thetaPath,'Sheet','Selected_Theta');
thetaTable = thetaTable(~cellfun(@isempty,tableCellstr(thetaTable.theta_id)),:);
candidates = tableToCandidates(thetaTable);
writetable(struct2table(candidates),fullfile(cfg.outRoot,'kb_theta_candidates.csv'));
writeProtocol(cfg,thetaPath,manifestPath,numel(candidates));
writeSelectedInstances(scriptDir,manifestPath,cfg);

assignin('base','SYNTHETIC_OUT_ROOT',cfg.outRoot);
assignin('base','SYNTHETIC_MANIFEST',manifestPath);
assignin('base','SYNTHETIC_SPLITS',cfg.splits);
assignin('base','SYNTHETIC_RUNS',cfg.runs);
assignin('base','SYNTHETIC_N',cfg.N);
assignin('base','SYNTHETIC_MAXFE',cfg.maxFE);
assignin('base','SYNTHETIC_MAX_INSTANCES',cfg.maxInstances);
assignin('base','SYNTHETIC_SKIP_SUMMARY',true);
assignin('base','SYNTHETIC_FORCE_RERUN',false);

cleanup = onCleanup(@() clearPilotWorkspaceVars());

fprintf('Theta24 10-instance label pilot\n');
fprintf('Instances: first %d train rows from manifest\n',cfg.maxInstances);
fprintf('Theta candidates: %d, runs per instance-theta: %d, N=%d, maxFE=%d\n', ...
    numel(candidates),cfg.runs,cfg.N,cfg.maxFE);
fprintf('Expected runs: %d\n',cfg.maxInstances*numel(candidates)*cfg.runs);
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

function writeProtocol(cfg,thetaPath,manifestPath,nCandidates)
fid = fopen(fullfile(cfg.outRoot,'theta24_10instance_label_protocol.txt'),'w');
fprintf(fid,'purpose=pilot meta-learning label generation\n');
fprintf(fid,'label_protocol=10 train instances x 24 theta x 30 independent runs\n');
fprintf(fid,'theta_excel=%s\n',thetaPath);
fprintf(fid,'manifest=%s\n',manifestPath);
fprintf(fid,'splits=%s\n',strjoin(cfg.splits,','));
fprintf(fid,'max_instances=%d\n',cfg.maxInstances);
fprintf(fid,'theta_candidates=%d\n',nCandidates);
fprintf(fid,'runs=%d\n',cfg.runs);
fprintf(fid,'N=%d\n',cfg.N);
fprintf(fid,'maxFE=%d\n',cfg.maxFE);
fprintf(fid,'score=rank average over HV(max), IGD(min), PF_Overlap(max), PF_Drift(min), Runtime(min)\n');
fprintf(fid,'labels=top1_classification_labels.csv, theta_ranking_labels.csv, regression_score_labels.csv\n');
fclose(fid);
end

function writeSelectedInstances(scriptDir,manifestPath,cfg)
manifest = readtable(manifestPath);
mask = strcmp(manifest.split,cfg.splits{1});
selected = manifest(mask,:);
selected = selected(1:min(cfg.maxInstances,height(selected)),:);
for i = 1:height(selected)
    p = scalarText(selected.path(i));
    if isempty(regexp(p,'^[A-Za-z]:[\\/]', 'once'))
        p = fullfile(scriptDir,p);
    end
    selected.path(i) = {p};
end
writetable(selected,fullfile(cfg.outRoot,'selected_10_train_instances.csv'));
end

function runRanker(scriptDir,outRoot)
ranker = fullfile(scriptDir,'rank_knowledge_base_parameter_search.py');
if exist(ranker,'file')
    cmd = sprintf('python "%s" --root "%s"',ranker,outRoot);
    status = system(cmd);
    if status ~= 0
        warning('Theta24Pilot:RankerFailed','Ranker command failed: %s',cmd);
    end
end
end

function clearPilotWorkspaceVars()
evalin('base',['clear ECMADE_MOO_KB_THETA SYNTHETIC_OUT_ROOT SYNTHETIC_MANIFEST ' ...
    'SYNTHETIC_SPLITS SYNTHETIC_RUNS SYNTHETIC_N SYNTHETIC_MAXFE ' ...
    'SYNTHETIC_MAX_INSTANCES SYNTHETIC_SKIP_SUMMARY SYNTHETIC_FORCE_RERUN']);
end
