function run_tevc_pdf_direct_ablation()
% Direct PDF-aligned ablation raw runner.
%
% This runner performs one-factor-at-a-time ECMADE-MOO_KB variants for:
%   1) subpopulation number S = 2,3,5
%   2) migration = none,fixed,adaptive
%   3) elite injection ratio = 0,1%,5%,10%
%
% Optional base-workspace overrides:
%   TEVC_ABLATION_OUT_ROOT, TEVC_ABLATION_RUNS, TEVC_ABLATION_N
%   TEVC_ABLATION_MAXFE, TEVC_ABLATION_MAX_INSTANCES
%   TEVC_ABLATION_INSTANCE_NAMES, TEVC_ABLATION_VARIANTS
%   TEVC_ABLATION_FORCE_RERUN

scriptDir = fileparts(mfilename('fullpath'));

cfg = struct();
cfg.outRoot = fullfile(scriptDir,'p0_lite_outputs', ...
    ['tevc_pdf_direct_ablation_' datestr(now,'yyyymmdd_HHMMSS')]);
cfg.runs = 30;
cfg.N = 100;
cfg.maxFE = 10000;
cfg.maxInstances = inf;
cfg.instanceNames = {};
cfg.forceRerun = false;
cfg.variantFilter = {};

cfg = applyWorkspaceOverrides(cfg);

if ~exist(cfg.outRoot,'dir')
    mkdir(cfg.outRoot);
end

variants = buildVariants();
variants = filterVariants(variants,cfg.variantFilter);
if isempty(variants)
    error('TEVCAblation:NoVariants','No variants selected.');
end

writetable(struct2table(variants),fullfile(cfg.outRoot,'kb_theta_candidates.csv'));
writeProtocol(cfg,variants);

assignin('base','SYNTHETIC_OUT_ROOT',cfg.outRoot);
assignin('base','SYNTHETIC_SPLITS',{'test'});
assignin('base','SYNTHETIC_RUNS',cfg.runs);
assignin('base','SYNTHETIC_N',cfg.N);
assignin('base','SYNTHETIC_MAXFE',cfg.maxFE);
assignin('base','SYNTHETIC_MAX_INSTANCES',cfg.maxInstances);
assignin('base','SYNTHETIC_INSTANCE_NAMES',cfg.instanceNames);
assignin('base','SYNTHETIC_SKIP_SUMMARY',true);
assignin('base','SYNTHETIC_FORCE_RERUN',cfg.forceRerun);
assignin('base','SYNTHETIC_EXPERIMENT_NAME','tevc_pdf_direct_ablation');
assignin('base','SYNTHETIC_DATASET_LABEL','TEVC PDF direct ablation');

cleanup = onCleanup(@() clearWorkspaceVars());

fprintf('TEVC PDF direct ablation\n');
fprintf('Output: %s\n',cfg.outRoot);
fprintf('Variants: %d\n',numel(variants));
fprintf('Runs per instance: %d, N=%d, maxFE=%d\n',cfg.runs,cfg.N,cfg.maxFE);

for vi = 1:numel(variants)
    thetaCfg = variantToTheta(variants(vi));
    assignin('base','ECMADE_MOO_KB_THETA',thetaCfg);
    fprintf('=== Variant %d/%d: %s | family=%s | S=%d op=%s migration=%s elite=%.3g tau=%d ===\n', ...
        vi,numel(variants),thetaCfg.method,variants(vi).ablation_family, ...
        thetaCfg.subpops,thetaCfg.operatorMode,thetaCfg.exchangeMode, ...
        thetaCfg.eliteRatio,thetaCfg.stagnationThreshold);
    SyntheticRunner.runAlgorithm(@ECMADE_MOO_KB,thetaCfg.method);
end

evalin('base','clear ECMADE_MOO_KB_THETA');
runRanker(scriptDir,cfg.outRoot);
fprintf('Done. Output: %s\n',cfg.outRoot);
end

function cfg = applyWorkspaceOverrides(cfg)
cfg = overrideValue(cfg,'TEVC_ABLATION_OUT_ROOT','outRoot');
cfg = overrideValue(cfg,'TEVC_ABLATION_RUNS','runs');
cfg = overrideValue(cfg,'TEVC_ABLATION_N','N');
cfg = overrideValue(cfg,'TEVC_ABLATION_MAXFE','maxFE');
cfg = overrideValue(cfg,'TEVC_ABLATION_MAX_INSTANCES','maxInstances');
cfg = overrideValue(cfg,'TEVC_ABLATION_INSTANCE_NAMES','instanceNames');
cfg = overrideValue(cfg,'TEVC_ABLATION_FORCE_RERUN','forceRerun');
cfg = overrideValue(cfg,'TEVC_ABLATION_VARIANTS','variantFilter');
end

function cfg = overrideValue(cfg,varName,fieldName)
if evalin('base',sprintf('exist(''%s'',''var'')',varName))
    cfg.(fieldName) = evalin('base',varName);
end
end

function variants = buildVariants()
base = struct();
base.source_operator = 'DE/rand';
base.operatorMode = 'rand2';
base.source_archive_strategy = 'crowding-pruned';
base.source_constraint_handling = 'repair+feasible-first';
base.theta = 1/13;
base.archiveLimitFactor = 5;
base.consensusArchive = false;
base.archiveConsWeight = 0.0;
base.bestGuide = 'rank';
base.minSubpopSize = 1;

variants = struct('method',{},'source_theta_id',{},'ablation_family',{}, ...
    'ablation_level',{},'source_operator',{},'source_migration',{}, ...
    'source_elite_ratio',{},'source_archive_strategy',{}, ...
    'source_constraint_handling',{},'subpops',{},'operatorMode',{}, ...
    'exchangeMode',{},'eliteRatio',{},'stagnationThreshold',{}, ...
    'theta',{},'archiveLimitFactor',{},'consensusArchive',{}, ...
    'archiveConsWeight',{},'bestGuide',{},'minSubpopSize',{});

% S ablation: isolate S with migration disabled.
sValues = [2 3 5];
for i = 1:numel(sValues)
    v = base;
    v.method = sprintf('PDF_Abl_S_%d',sValues(i));
    v.source_theta_id = v.method;
    v.ablation_family = 'subpopulation_number';
    v.ablation_level = sprintf('S=%d',sValues(i));
    v.source_migration = 'none';
    v.exchangeMode = 'none';
    v.source_elite_ratio = '5%';
    v.eliteRatio = 0.05;
    v.subpops = sValues(i);
    v.stagnationThreshold = 10;
    variants(end+1,1) = v; %#ok<AGROW>
end

% Migration ablation: isolate exchange mode with S=3 and elite=5%.
migrations = {'none','fixed','adaptive'};
exchangeModes = {'none','paper','stable'};
for i = 1:numel(migrations)
    v = base;
    v.method = sprintf('PDF_Abl_Migration_%s',migrations{i});
    v.source_theta_id = v.method;
    v.ablation_family = 'migration';
    v.ablation_level = migrations{i};
    v.source_migration = migrations{i};
    v.exchangeMode = exchangeModes{i};
    v.source_elite_ratio = '5%';
    v.eliteRatio = 0.05;
    v.subpops = 3;
    v.stagnationThreshold = 10;
    variants(end+1,1) = v; %#ok<AGROW>
end

% Elite injection ablation: keep fixed migration active, vary copied elite ratio.
eliteLabels = {'0%','1%','5%','10%'};
eliteValues = [0 0.01 0.05 0.10];
for i = 1:numel(eliteValues)
    v = base;
    v.method = sprintf('PDF_Abl_Elite_%s',strrep(eliteLabels{i},'%','pct'));
    v.source_theta_id = v.method;
    v.ablation_family = 'elite_injection';
    v.ablation_level = eliteLabels{i};
    v.source_migration = 'fixed';
    v.exchangeMode = 'paper';
    v.source_elite_ratio = eliteLabels{i};
    v.eliteRatio = eliteValues(i);
    v.subpops = 3;
    v.stagnationThreshold = 10;
    variants(end+1,1) = v; %#ok<AGROW>
end
end

function variants = filterVariants(variants,variantFilter)
filters = asCellstr(variantFilter);
if isempty(filters)
    return;
end
keep = false(numel(variants),1);
for i = 1:numel(variants)
    keep(i) = any(strcmp(variants(i).method,filters)) || ...
        any(strcmp(variants(i).ablation_family,filters));
end
variants = variants(keep);
end

function thetaCfg = variantToTheta(v)
thetaCfg = v;
thetaCfg = rmfield(thetaCfg,{'ablation_family','ablation_level'});
end

function writeProtocol(cfg,variants)
fid = fopen(fullfile(cfg.outRoot,'tevc_pdf_direct_ablation_protocol.txt'),'w');
fprintf(fid,'purpose=PDF-aligned direct mechanism ablation\n');
fprintf(fid,'one_factor_at_a_time=true\n');
fprintf(fid,'splits=test\n');
fprintf(fid,'runs=%d\n',cfg.runs);
fprintf(fid,'N=%d\n',cfg.N);
fprintf(fid,'maxFE=%d\n',cfg.maxFE);
fprintf(fid,'maxInstances=%g\n',cfg.maxInstances);
fprintf(fid,'forceRerun=%d\n',cfg.forceRerun);
fprintf(fid,'variant_count=%d\n',numel(variants));
fprintf(fid,'base_for_S=operator DE/rand, migration none, elite 5%%, tau 10\n');
fprintf(fid,'base_for_migration=S 3, operator DE/rand, elite 5%%, tau 10\n');
fprintf(fid,'base_for_elite=S 3, operator DE/rand, fixed migration, tau 10\n');
fclose(fid);
end

function runRanker(scriptDir,outRoot)
ranker = fullfile(scriptDir,'rank_knowledge_base_parameter_search.py');
if exist(ranker,'file')
    cmd = sprintf('python "%s" --root "%s"',ranker,outRoot);
    status = system(cmd);
    if status ~= 0
        warning('TEVCAblation:RankerFailed','Ranker command failed: %s',cmd);
    end
end
end

function clearWorkspaceVars()
evalin('base','clear ECMADE_MOO_KB_THETA');
evalin('base','clear SYNTHETIC_OUT_ROOT SYNTHETIC_SPLITS SYNTHETIC_RUNS SYNTHETIC_N');
evalin('base','clear SYNTHETIC_MAXFE SYNTHETIC_MAX_INSTANCES SYNTHETIC_INSTANCE_NAMES');
evalin('base','clear SYNTHETIC_SKIP_SUMMARY SYNTHETIC_FORCE_RERUN');
evalin('base','clear SYNTHETIC_EXPERIMENT_NAME SYNTHETIC_DATASET_LABEL');
end

function values = asCellstr(x)
if isempty(x)
    values = {};
elseif ischar(x)
    values = {x};
elseif isstring(x)
    values = cellstr(x);
elseif iscell(x)
    values = x;
else
    error('TEVCAblation:InvalidCellstr','Expected char, string, or cell array.');
end
end
