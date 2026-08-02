classdef P1MOKPConfigRunner
% Shared P1 runner for ECMADE-MOO configuration baselines on MOKP.

    methods(Static)
        function runAssignment(method,assignmentPath,outRoot)
            scriptDir = fileparts(mfilename('fullpath'));
            cfg = P1MOKPConfigRunner.baseConfig(scriptDir,method,outRoot);
            cfg = P1MOKPConfigRunner.applyOverrides(cfg,'P1_MOKP_CONFIG');
            P1MOKPConfigRunner.setupPaths(scriptDir,cfg.outRoot);
            assignments = readtable(assignmentPath);
            assignments = P1MOKPConfigRunner.filterRows(assignments,cfg);
            writetable(assignments,fullfile(cfg.outRoot,[method '_assignment_used.csv']));
            P1MOKPConfigRunner.runRows(assignments,cfg);
            P1MOKPConfigRunner.rebuildSummary(cfg.outRoot,method);
        end

        function runRandom(outRoot)
            scriptDir = fileparts(mfilename('fullpath'));
            cfg = P1MOKPConfigRunner.baseConfig(scriptDir,'RandomConfig_ECMADE_MOO',outRoot);
            cfg = P1MOKPConfigRunner.applyOverrides(cfg,'P1_MOKP_RANDOM');
            P1MOKPConfigRunner.setupPaths(scriptDir,cfg.outRoot);
            theta = P1MOKPConfigRunner.readL24Candidates(cfg.thetaPath,cfg.thetaSheet);
            manifest = P1MOKPConfigRunner.defaultManifest();
            manifest = P1MOKPConfigRunner.filterRows(manifest,cfg);
            rng(cfg.assignmentSeed,'twister');
            rows = {};
            for ii = 1:height(manifest)
                thetaIndex = randi(numel(theta));
                rows(end+1,:) = P1MOKPConfigRunner.assignmentRow(manifest(ii,:),theta(thetaIndex),thetaIndex,NaN); %#ok<AGROW>
            end
            assignments = cell2table(rows,'VariableNames',P1MOKPConfigRunner.assignmentColumns());
            writetable(struct2table(theta),fullfile(cfg.outRoot,'l24_theta_candidates.csv'));
            writetable(assignments,fullfile(cfg.outRoot,'random_config_assignment.csv'));
            P1MOKPConfigRunner.runRows(assignments,cfg);
            P1MOKPConfigRunner.rebuildSummary(cfg.outRoot,cfg.method);
        end

        function runGlobalTheta(method,thetaIndex,outRoot)
            scriptDir = fileparts(mfilename('fullpath'));
            cfg = P1MOKPConfigRunner.baseConfig(scriptDir,method,outRoot);
            cfg = P1MOKPConfigRunner.applyOverrides(cfg,'P1_MOKP_GLOBAL_THETA');
            P1MOKPConfigRunner.setupPaths(scriptDir,cfg.outRoot);
            theta = P1MOKPConfigRunner.readL24Candidates(cfg.thetaPath,cfg.thetaSheet);
            manifest = P1MOKPConfigRunner.defaultManifest();
            manifest = P1MOKPConfigRunner.filterRows(manifest,cfg);
            thetaIndex = min(max(1,thetaIndex),numel(theta));
            rows = {};
            for ii = 1:height(manifest)
                rows(end+1,:) = P1MOKPConfigRunner.assignmentRow(manifest(ii,:),theta(thetaIndex),thetaIndex,NaN); %#ok<AGROW>
            end
            assignments = cell2table(rows,'VariableNames',P1MOKPConfigRunner.assignmentColumns());
            writetable(struct2table(theta),fullfile(cfg.outRoot,'l24_theta_candidates.csv'));
            writetable(assignments,fullfile(cfg.outRoot,[method '_assignment.csv']));
            P1MOKPConfigRunner.runRows(assignments,cfg);
            P1MOKPConfigRunner.rebuildSummary(cfg.outRoot,cfg.method);
        end

        function cfg = baseConfig(scriptDir,method,outRoot)
            cfg = struct();
            cfg.method = method;
            cfg.thetaPath = P1MOKPConfigRunner.defaultThetaPath();
            cfg.thetaSheet = 'L24_Theta_Config';
            cfg.outRoot = outRoot;
            cfg.runs = 30;
            cfg.N = 100;
            cfg.maxFE = 10000;
            cfg.saveGenerations = cfg.maxFE / cfg.N;
            cfg.rngType = 'mcg16807';
            cfg.maxInstances = inf;
            cfg.instanceNames = {};
            cfg.forceRerun = false;
            cfg.assignmentSeed = 20260719;
            cfg.scriptDir = scriptDir;
        end

        function cfg = applyOverrides(cfg,prefix)
            cfg = P1MOKPConfigRunner.overrideValue(cfg,[prefix '_RUNS'],'runs');
            cfg = P1MOKPConfigRunner.overrideValue(cfg,[prefix '_N'],'N');
            cfg = P1MOKPConfigRunner.overrideValue(cfg,[prefix '_MAXFE'],'maxFE');
            cfg = P1MOKPConfigRunner.overrideValue(cfg,[prefix '_MAX_INSTANCES'],'maxInstances');
            cfg = P1MOKPConfigRunner.overrideValue(cfg,[prefix '_INSTANCE_NAMES'],'instanceNames');
            cfg = P1MOKPConfigRunner.overrideValue(cfg,[prefix '_FORCE_RERUN'],'forceRerun');
            cfg = P1MOKPConfigRunner.overrideValue(cfg,[prefix '_ASSIGNMENT_SEED'],'assignmentSeed');
            cfg.saveGenerations = max(1,cfg.maxFE / cfg.N);
        end

        function cfg = overrideValue(cfg,varName,fieldName)
            if evalin('base',sprintf('exist(''%s'',''var'')',varName))
                cfg.(fieldName) = evalin('base',varName);
            end
        end

        function setupPaths(scriptDir,outRoot)
            platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');
            restoredefaultpath;
            addpath(genpath(platemoRoot));
            addpath(scriptDir);
            if ~exist(outRoot,'dir'); mkdir(outRoot); end
        end

        function manifest = defaultManifest()
            rows = {};
            for di = 1:numel([100 250 500])
                itemsList = [100 250 500];
                items = itemsList(di);
                for ci = 1:numel([0.35 0.50 0.65])
                    ratios = [0.35 0.50 0.65];
                    cr = ratios(ci);
                    for mi = 1:numel({'independent','conflicting'})
                        modes = {'independent','conflicting'};
                        mode = modes{mi};
                        seed = 20260718 + 10000*di + 1000*ci + 100*mi + 1;
                        instance = sprintf('mokp_m02_d%03d_c%02d_%s_r01_s%d',items,round(100*cr),mode,seed);
                        rows(end+1,:) = {'test',instance,items,2,cr,mode,1,seed}; %#ok<AGROW>
                    end
                end
            end
            manifest = cell2table(rows,'VariableNames',{'split','instance','items','objectives','capacity_ratio','profit_mode','replicate','seed'});
        end

        function rows = filterRows(rows,cfg)
            names = P1MOKPConfigRunner.asCellstr(cfg.instanceNames);
            if ~isempty(names)
                mask = false(height(rows),1);
                for i = 1:numel(names)
                    mask = mask | strcmp(rows.instance,names{i});
                end
                rows = rows(mask,:);
            end
            if isfinite(cfg.maxInstances)
                rows = rows(1:min(height(rows),cfg.maxInstances),:);
            end
        end

        function runRows(assignments,cfg)
            cleanup = onCleanup(@() evalin('base','clear ECMADE_MOO_KB_THETA'));
            fprintf('%s on P1 MOKP\n',cfg.method);
            fprintf('Assignments: %d, runs=%d, N=%d, maxFE=%d\n',height(assignments),cfg.runs,cfg.N,cfg.maxFE);
            fprintf('Output: %s\n',cfg.outRoot);
            for ii = 1:height(assignments)
                row = assignments(ii,:);
                thetaCfg = P1MOKPConfigRunner.rowToTheta(row);
                assignin('base','ECMADE_MOO_KB_THETA',thetaCfg);
                instance = P1MOKPConfigRunner.cellValue(row.instance);
                splitName = P1MOKPConfigRunner.cellValue(row.split);
                fprintf('=== %s | %s | %s selected %s ===\n',splitName,instance,cfg.method,thetaCfg.source_theta_id);
                for run = 1:cfg.runs
                    runDir = fullfile(cfg.outRoot,splitName,instance,cfg.method,sprintf('run_%03d',run));
                    if ~cfg.forceRerun && P1MOKPConfigRunner.hasCompleteRun(runDir)
                        continue;
                    end
                    if ~exist(runDir,'dir'); mkdir(runDir); end
                    P1MOKPConfigRunner.writeThetaMetadata(runDir,row,thetaCfg,cfg,ii);
                    fprintf('%s %s Run %03d/%03d\n',cfg.method,instance,run,cfg.runs);
                    rng(run,cfg.rngType);
                    t = tic;
                    G = GLOBAL('-algorithm',@ECMADE_MOO_KB, ...
                        '-problem',{@P1MOKP,row.items,row.objectives,row.seed,row.capacity_ratio,P1MOKPConfigRunner.cellValue(row.profit_mode)}, ...
                        '-N',cfg.N,'-M',row.objectives,'-D',row.items, ...
                        '-evaluation',cfg.maxFE,'-run',run, ...
                        '-save',cfg.saveGenerations,'-outputFcn',@(varargin)[]);
                    G.Start();
                    runtime = toc(t);
                    Pop = G.result{end,2};
                    Obj = Pop.objs;
                    Dec = Pop.decs;
                    [pfDec,pfObj] = P0LiteUtils.firstFrontDecObj(Dec,Obj);
                    P1KnapsackRunner.saveRun(runDir,Dec,Obj,pfDec,pfObj,runtime,row);
                    P1KnapsackRunner.saveGenerationSnapshots(runDir,G.result,row,cfg.N);
                end
            end
        end

        function ok = hasCompleteRun(runDir)
            ok = exist(fullfile(runDir,'pf_obj.csv'),'file') && ...
                exist(fullfile(runDir,'runtime.csv'),'file') && ...
                exist(fullfile(runDir,'generation_pf_points.csv'),'file') && ...
                exist(fullfile(runDir,'theta_metadata.csv'),'file');
        end

        function writeThetaMetadata(runDir,row,thetaCfg,cfg,assignmentRow)
            T = table();
            T.method = {cfg.method};
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
            T.instance = row.instance;
            T.split = row.split;
            T.items = row.items;
            T.objectives = row.objectives;
            T.capacity_ratio = row.capacity_ratio;
            T.profit_mode = row.profit_mode;
            T.seed = row.seed;
            T.N = cfg.N;
            T.maxFE = cfg.maxFE;
            T.runs = cfg.runs;
            writetable(T,fullfile(runDir,'theta_metadata.csv'));
        end

        function rebuildSummary(outRoot,method)
            files = dir(fullfile(outRoot,'**','runtime.csv'));
            rows = {};
            for fi = 1:numel(files)
                runDir = files(fi).folder;
                pfFile = fullfile(runDir,'pf_obj.csv');
                metaFile = fullfile(runDir,'theta_metadata.csv');
                if ~exist(pfFile,'file') || ~exist(metaFile,'file'); continue; end
                meta = readtable(metaFile);
                if ~strcmp(P1MOKPConfigRunner.cellValue(meta.method(1)),method); continue; end
                rt = readtable(fullfile(runDir,'runtime.csv'));
                pfObj = readmatrix(pfFile);
                runToken = regexp(runDir,[regexptranslate('escape',filesep) 'run_(\d+)$'],'tokens','once');
                if isempty(runToken); run = NaN; else; run = str2double(runToken{1}); end
                rows(end+1,:) = {method,P1MOKPConfigRunner.cellValue(meta.split(1)),P1MOKPConfigRunner.cellValue(meta.instance(1)), ...
                    meta.items(1),meta.objectives(1),meta.capacity_ratio(1),P1MOKPConfigRunner.cellValue(meta.profit_mode(1)),meta.seed(1), ...
                    meta.theta_index(1),P1MOKPConfigRunner.cellValue(meta.theta_id(1)),meta.predicted_score(1), ...
                    meta.S(1),P1MOKPConfigRunner.cellValue(meta.operator(1)),P1MOKPConfigRunner.cellValue(meta.migration(1)), ...
                    meta.elite_ratio(1),meta.stagnation_threshold(1),run,size(pfObj,1),rt.runtime_sec(1),mean(pfObj(:,1)),mean(pfObj(:,2))}; %#ok<AGROW>
            end
            if isempty(rows); return; end
            T = cell2table(rows,'VariableNames',{'method','split','instance','items','objectives','capacity_ratio','profit_mode','seed', ...
                'theta_index','theta_id','predicted_score','S','operator','migration','elite_ratio','stagnation_threshold', ...
                'run','pf_size','runtime_sec','mean_obj1_loss','mean_obj2_loss'});
            writetable(T,fullfile(outRoot,[method '_run_summary.csv']));
        end

        function thetaCfg = rowToTheta(row)
            op = P1MOKPConfigRunner.cellValue(row.operator);
            mig = P1MOKPConfigRunner.cellValue(row.migration);
            thetaCfg = struct();
            thetaCfg.method = P1MOKPConfigRunner.cellValue(row.theta_id);
            thetaCfg.source_theta_id = P1MOKPConfigRunner.cellValue(row.theta_id);
            thetaCfg.source_operator = op;
            thetaCfg.source_migration = mig;
            thetaCfg.source_elite_ratio = num2str(row.elite_ratio);
            thetaCfg.source_archive_strategy = 'crowding-pruned';
            thetaCfg.source_constraint_handling = 'repair+feasible-first';
            thetaCfg.subpops = row.S;
            thetaCfg.operatorMode = P1MOKPConfigRunner.mapOperator(op);
            thetaCfg.exchangeMode = P1MOKPConfigRunner.mapMigration(mig);
            thetaCfg.eliteRatio = row.elite_ratio;
            thetaCfg.stagnationThreshold = row.stagnation_threshold;
            thetaCfg.theta = 1/13;
            thetaCfg.archiveLimitFactor = 5;
            thetaCfg.consensusArchive = false;
            thetaCfg.archiveConsWeight = 0.0;
            thetaCfg.bestGuide = 'rank';
            thetaCfg.minSubpopSize = 1;
        end

        function cols = assignmentColumns()
            cols = {'split','instance','items','objectives','capacity_ratio','profit_mode','replicate','seed', ...
                'theta_index','theta_id','predicted_score','S','operator','migration','elite_ratio','stagnation_threshold'};
        end

        function row = assignmentRow(manifestRow,thetaCfg,thetaIndex,predictedScore)
            row = {P1MOKPConfigRunner.cellValue(manifestRow.split),P1MOKPConfigRunner.cellValue(manifestRow.instance), ...
                manifestRow.items,manifestRow.objectives,manifestRow.capacity_ratio,P1MOKPConfigRunner.cellValue(manifestRow.profit_mode), ...
                manifestRow.replicate,manifestRow.seed,thetaIndex,thetaCfg.source_theta_id,predictedScore, ...
                thetaCfg.subpops,thetaCfg.source_operator,thetaCfg.source_migration,thetaCfg.eliteRatio,thetaCfg.stagnationThreshold};
        end

        function candidates = readL24Candidates(thetaPath,sheetName)
            raw = readcell(thetaPath,'Sheet',sheetName);
            headers = raw(4,:);
            data = raw(5:28,:);
            labels = cellfun(@P1MOKPConfigRunner.cellValue,headers,'UniformOutput',false);
            idx = @(name) find(strcmp(labels,name),1);
            candidates = struct('source_theta_id',{},'source_operator',{},'source_migration',{}, ...
                'subpops',{},'eliteRatio',{},'stagnationThreshold',{});
            for i = 1:size(data,1)
                thetaId = sprintf('theta_%02d',i);
                op = P1MOKPConfigRunner.cellValue(data{i,idx('operator')});
                mig = P1MOKPConfigRunner.cellValue(data{i,idx('migration')});
                elite = P1MOKPConfigRunner.cellValue(data{i,idx('elite_ratio')});
                c = struct();
                c.source_theta_id = thetaId;
                c.source_operator = op;
                c.source_migration = mig;
                c.subpops = P1MOKPConfigRunner.numericValue(data{i,idx('S')});
                c.eliteRatio = P1MOKPConfigRunner.parseEliteRatio(elite);
                c.stagnationThreshold = P1MOKPConfigRunner.numericValue(data{i,idx('stagnation_threshold')});
                candidates(end+1,1) = c; %#ok<AGROW>
            end
        end

        function path = defaultThetaPath()
            candidates = {'C:\Users\yiting\Desktop\NCHU\lab\TEVC\excel\TEVC_P0_L24_Orthogonal_Theta_Configurations.xlsx', ...
                'C:\Users\yiting\Desktop\NCHU\lab\TEVC\data\TEVC_P0_L24_Orthogonal_Theta_Configurations.xlsx'};
            path = candidates{1};
            for i = 1:numel(candidates)
                if exist(candidates{i},'file'); path = candidates{i}; return; end
            end
        end

        function mode = mapOperator(op)
            if strcmp(op,'DE/rand'); mode = 'rand2';
            elseif strcmp(op,'DE/best'); mode = 'best2';
            else; mode = 'mixed'; end
        end

        function mode = mapMigration(mig)
            if strcmp(mig,'none'); mode = 'none';
            elseif strcmp(mig,'fixed'); mode = 'paper';
            else; mode = 'stable'; end
        end

        function value = parseEliteRatio(text)
            s = strrep(char(text),'%','');
            value = str2double(s);
            if value > 1; value = value / 100; end
        end

        function value = numericValue(x)
            if isnumeric(x); value = x; else; value = str2double(char(x)); end
        end

        function values = asCellstr(value)
            if isempty(value); values = {};
            elseif ischar(value); values = {value};
            elseif isstring(value); values = cellstr(value);
            else; values = value; end
        end

        function value = cellValue(x)
            if iscell(x); value = x{1};
            elseif isstring(x); value = char(x(1));
            else; value = x; end
        end
    end
end
