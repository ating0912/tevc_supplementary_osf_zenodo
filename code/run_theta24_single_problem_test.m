function run_theta24_single_problem_test()
% Run one OR-Library problem with the 24 theta configurations from Excel.

scriptDir = fileparts(mfilename('fullpath'));
thetaPath = fullfile(fileparts(scriptDir),'external_data','TEVC_P0_Selected_Theta_fractional_24.xlsx');
dataPath = fullfile(scriptDir,'data','orlib','port1.txt');
platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');

cfg = struct();
cfg.instance = 'orlib_port1';
cfg.K = 10;
cfg.runs = 5;
cfg.N = 100;
cfg.maxFE = 10000;
cfg.saveGenerations = max(1,cfg.maxFE / cfg.N);
cfg.rngType = 'mcg16807';
cfg.outRoot = fullfile(scriptDir,'p0_lite_outputs', ...
    ['theta24_single_problem_test_' datestr(now,'yyyymmdd_HHMMSS')]);
if evalin('base','exist(''THETA24_OUT_ROOT'',''var'')')
    cfg.outRoot = evalin('base','THETA24_OUT_ROOT');
end
if evalin('base','exist(''THETA24_RUNS'',''var'')')
    cfg.runs = evalin('base','THETA24_RUNS');
end

if ~exist(thetaPath,'file')
    error('Theta Excel file not found: %s',thetaPath);
end
if ~exist(dataPath,'file')
    error('Problem file not found: %s',dataPath);
end
if ~exist(cfg.outRoot,'dir')
    mkdir(cfg.outRoot);
end

restoredefaultpath;
addpath(genpath(platemoRoot));
addpath(scriptDir);

thetaTable = readtable(thetaPath,'Sheet','Selected_Theta');
thetaTable = thetaTable(~cellfun(@isempty,tableCellstr(thetaTable.theta_id)),:);
candidates = tableToCandidates(thetaTable);
writetable(struct2table(candidates),fullfile(cfg.outRoot,'theta24_config.csv'));
writeProtocol(cfg,thetaPath,dataPath,numel(candidates));

[mu,~] = P0LiteUtils.loadORLibraryPortfile(dataPath);
nAssets = numel(mu);
summaryRows = {};

fprintf('Theta24 single-problem test\n');
fprintf('Problem: %s, K=%d, theta=%d, runs=%d, N=%d, maxFE=%d\n', ...
    cfg.instance,cfg.K,numel(candidates),cfg.runs,cfg.N,cfg.maxFE);
fprintf('Output: %s\n',cfg.outRoot);

for ci = 1:numel(candidates)
    thetaCfg = candidates(ci);
    assignin('base','ECMADE_MOO_KB_THETA',thetaCfg);
    method = thetaCfg.method;
    fprintf('=== %s | S=%d | operator=%s | migration=%s | rho=%.3g | tau=%d ===\n', ...
        method,thetaCfg.subpops,thetaCfg.operatorMode,thetaCfg.exchangeMode, ...
        thetaCfg.eliteRatio,thetaCfg.stagnationThreshold);

    for run = 1:cfg.runs
        runDir = fullfile(cfg.outRoot,sprintf('K_%02d',cfg.K),method,sprintf('run_%03d',run));
        if hasCompleteRun(runDir)
            fprintf('%s run %03d already complete; skipping.\n',method,run);
        else
            if ~exist(runDir,'dir')
                mkdir(runDir);
            end
            writeThetaMetadata(runDir,thetaCfg,cfg,dataPath);
            rng(run,cfg.rngType);
            t = tic;
            G = GLOBAL('-algorithm',@ECMADE_MOO_KB, ...
                '-problem',{@PortfolioORLIB,dataPath,cfg.K}, ...
                '-N',cfg.N,'-M',2,'-D',nAssets, ...
                '-evaluation',cfg.maxFE,'-run',run, ...
                '-save',cfg.saveGenerations,'-outputFcn',@(varargin)[]);
            G.Start();
            runtime = toc(t);

            Pop = G.result{end,2};
            Obj = Pop.objs;
            Dec = Pop.decs;
            [pfDec,pfObj] = P0LiteUtils.firstFrontDecObj(Dec,Obj);
            P0LiteUtils.saveRun(runDir,Dec,Obj,pfDec,pfObj,runtime,cfg.K);
            P0LiteUtils.saveGenerationSnapshots(runDir,G.result,cfg.K,cfg.N);
        end

        rt = readtable(fullfile(runDir,'runtime.csv'));
        pfObj = readmatrix(fullfile(runDir,'pf_obj.csv'));
        feasibleFile = fullfile(runDir,'feasible_rate.csv');
        feasibleRate = NaN;
        if exist(feasibleFile,'file')
            feas = readtable(feasibleFile);
            feasibleRate = feas.PF_Feasible_Rate(1);
        end
        summaryRows(end+1,:) = { ...
            method,thetaCfg.source_theta_id,thetaCfg.source_operator,thetaCfg.source_migration, ...
            thetaCfg.subpops,thetaCfg.operatorMode,thetaCfg.exchangeMode,thetaCfg.eliteRatio, ...
            thetaCfg.stagnationThreshold,cfg.K,run,size(pfObj,1),rt.runtime_sec(1), ...
            mean(pfObj(:,1)),mean(-pfObj(:,2)),feasibleRate}; %#ok<AGROW>
    end
end

evalin('base','clear ECMADE_MOO_KB_THETA');
summary = cell2table(summaryRows,'VariableNames',{ ...
    'method','theta_id','source_operator','source_migration','subpops','operatorMode', ...
    'exchangeMode','eliteRatio','stagnationThreshold','K','run','pf_size', ...
    'runtime_sec','mean_risk','mean_return','pf_feasible_rate'});
writetable(summary,fullfile(cfg.outRoot,'theta24_run_summary.csv'));
writeSimpleRank(summary,fullfile(cfg.outRoot,'theta24_rank_by_mean_return.csv'));
writeThetaAggregate(summary,fullfile(cfg.outRoot,'theta24_theta_summary.csv'), ...
    fullfile(cfg.outRoot,'theta24_theta_rank.csv'));

fprintf('Done. Summary: %s\n',fullfile(cfg.outRoot,'theta24_run_summary.csv'));
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

function ok = hasCompleteRun(runDir)
ok = exist(fullfile(runDir,'pf_obj.csv'),'file') && ...
    exist(fullfile(runDir,'runtime.csv'),'file') && ...
    exist(fullfile(runDir,'generation_pf_points.csv'),'file') && ...
    exist(fullfile(runDir,'generation_population_log.csv'),'file');
end

function writeThetaMetadata(runDir,thetaCfg,cfg,dataPath)
T = struct2table(thetaCfg);
T.problem = {cfg.instance};
T.dataPath = {dataPath};
T.K = cfg.K;
T.N = cfg.N;
T.maxFE = cfg.maxFE;
T.runs = cfg.runs;
T.rng = {cfg.rngType};
T.seed_rule = {'seed = run index'};
writetable(T,fullfile(runDir,'theta_metadata.csv'));
end

function writeProtocol(cfg,thetaPath,dataPath,nCandidates)
fid = fopen(fullfile(cfg.outRoot,'theta24_single_problem_protocol.txt'),'w');
fprintf(fid,'purpose=single problem theta24 smoke test\n');
fprintf(fid,'theta_excel=%s\n',thetaPath);
fprintf(fid,'problem=%s\n',cfg.instance);
fprintf(fid,'dataPath=%s\n',dataPath);
fprintf(fid,'K=%d\n',cfg.K);
fprintf(fid,'theta_candidates=%d\n',nCandidates);
fprintf(fid,'runs=%d\n',cfg.runs);
fprintf(fid,'N=%d\n',cfg.N);
fprintf(fid,'maxFE=%d\n',cfg.maxFE);
fprintf(fid,'rng=%s\n',cfg.rngType);
fprintf(fid,'seed_rule=seed equals run index\n');
fclose(fid);
end

function writeSimpleRank(summary,outPath)
rankTable = sortrows(summary,{'mean_return','mean_risk'},{'descend','ascend'});
rankTable.rank_by_mean_return = (1:height(rankTable))';
writetable(rankTable,outPath);
end

function writeThetaAggregate(summary,summaryPath,rankPath)
[thetaIds,~,groupIndex] = unique(summary.theta_id,'stable');
rows = {};
for i = 1:numel(thetaIds)
    mask = groupIndex == i;
    g = summary(mask,:);
    rows(end+1,:) = { ...
        g.theta_id{1},g.subpops(1),g.source_operator{1},g.source_migration{1}, ...
        g.eliteRatio(1),g.stagnationThreshold(1),height(g), ...
        mean(g.pf_size),mean(g.runtime_sec),mean(g.mean_risk), ...
        mean(g.mean_return),mean(g.pf_feasible_rate)}; %#ok<AGROW>
end
thetaSummary = cell2table(rows,'VariableNames',{ ...
    'theta_id','subpops','source_operator','source_migration','eliteRatio', ...
    'stagnationThreshold','runs','mean_pf_size','mean_runtime_sec', ...
    'mean_risk','mean_return','mean_pf_feasible_rate'});
writetable(thetaSummary,summaryPath);
thetaRank = sortrows(thetaSummary,{'mean_return','mean_risk'},{'descend','ascend'});
thetaRank.rank_by_avg_return = (1:height(thetaRank))';
thetaRank.is_best_theta = thetaRank.rank_by_avg_return == 1;
thetaRank.best_reason = repmat({''},height(thetaRank),1);
if height(thetaRank) > 0
    thetaRank.best_reason{1} = 'Highest 5-run average mean_return; ties broken by lower mean_risk.';
end
writetable(thetaRank,rankPath);
[rankFolder,~,~] = fileparts(rankPath);
writetable(thetaRank(1,:),fullfile(rankFolder,'best_theta_single_problem.csv'));
end
