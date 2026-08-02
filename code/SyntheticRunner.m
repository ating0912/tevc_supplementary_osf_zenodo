classdef SyntheticRunner
% Shared launcher for synthetic constrained portfolio experiments.
% Algorithm-specific scripts should call runAlgorithm with a single handle.

    methods(Static)
        function runAlgorithm(algorithmHandle, method)
            if evalin('base','exist(''SYNTHETIC_SMOKE'',''var'')')
                smoke = evalin('base','SYNTHETIC_SMOKE');
            else
                smoke = false;
            end

            scriptDir = fileparts(mfilename('fullpath'));
            platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');
            outRoot = fullfile(scriptDir,'p0_lite_outputs','synthetic_constrained_portfolio');
            manifestPath = fullfile(scriptDir,'data','synthetic_constrained_portfolio','manifest.csv');

            restoredefaultpath;
            addpath(genpath(platemoRoot));
            addpath(scriptDir);

            cfg = SyntheticRunner.baseConfig(scriptDir,manifestPath,outRoot,smoke);
            cfg = SyntheticRunner.applyWorkspaceOverrides(cfg);
            if ~exist(cfg.outRoot,'dir'); mkdir(cfg.outRoot); end

            manifest = SyntheticRunner.loadManifest(cfg.manifestPath,scriptDir);
            manifest = SyntheticRunner.filterManifest(manifest,cfg);
            SyntheticRunner.writeConfig(cfg,method,height(manifest));

            fprintf('%s runner\n',cfg.datasetLabel);
            fprintf('Method: %s\n',method);
            fprintf('Manifest rows: %d\n',height(manifest));
            fprintf('Runs per instance: %d, N=%d, maxFE=%d\n',cfg.runs,cfg.N,cfg.maxFE);

            for ii = 1:height(manifest)
                row = manifest(ii,:);
                instance = SyntheticRunner.cellValue(row.instance);
                splitName = SyntheticRunner.cellValue(row.split);
                dataPath = SyntheticRunner.cellValue(row.path);
                K = row.K;
                nAssets = row.assets;
                fprintf('=== %s | %s | K=%d | %s ===\n',splitName,instance,K,method);

                for run = 1:cfg.runs
                    fprintf('%s %s Run %03d/%03d\n',method,instance,run,cfg.runs);
                    runDir = fullfile(cfg.outRoot,splitName,instance,sprintf('K_%02d',K),method,sprintf('run_%03d',run));
                    if ~cfg.forceRerun && SyntheticRunner.hasCompleteRun(runDir)
                        continue;
                    end
                    if ~exist(runDir,'dir'); mkdir(runDir); end
                    SyntheticRunner.writeInstanceMetadata(runDir,row,method,cfg);

                    t = tic;
                    rng(run,cfg.rngType);
                    G = GLOBAL('-algorithm',algorithmHandle, ...
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

            if ~cfg.skipSummary
                SyntheticRunner.rebuildSummary(cfg.outRoot,{'NSGAII','SPEA2','MOEAD','GDE3','ECMADE_MOO','A_MPMO'});
            else
                fprintf('%s summary rebuild skipped.\n',cfg.datasetLabel);
            end
            fprintf('%s outputs: %s\n',method,cfg.outRoot);
        end

        function cfg = baseConfig(scriptDir,manifestPath,outRoot,smoke)
            cfg = struct();
            cfg.experiment = 'synthetic_constrained_portfolio';
            cfg.datasetLabel = 'Synthetic constrained portfolio';
            cfg.manifestPath = manifestPath;
            cfg.outRoot = outRoot;
            cfg.splits = {'train','validation','test'};
            cfg.runs = 30;
            cfg.N = 100;
            cfg.maxFE = 10000;
            cfg.saveGenerations = cfg.maxFE / cfg.N;
            cfg.rngType = 'mcg16807';
            cfg.smoke = smoke;
            cfg.maxInstances = inf;
            cfg.instanceNames = {};
            cfg.skipSummary = false;
            cfg.forceRerun = false;
            cfg.scriptDir = scriptDir;
            if cfg.smoke
                cfg.splits = {'train'};
                cfg.runs = 1;
                cfg.maxFE = 1000;
                cfg.saveGenerations = cfg.maxFE / cfg.N;
                cfg.maxInstances = 1;
            end
        end

        function cfg = applyWorkspaceOverrides(cfg)
            cfg = SyntheticRunner.overrideValue(cfg,'SYNTHETIC_MANIFEST','manifestPath');
            cfg = SyntheticRunner.overrideValue(cfg,'SYNTHETIC_OUT_ROOT','outRoot');
            cfg = SyntheticRunner.overrideValue(cfg,'SYNTHETIC_RUNS','runs');
            cfg = SyntheticRunner.overrideValue(cfg,'SYNTHETIC_N','N');
            cfg = SyntheticRunner.overrideValue(cfg,'SYNTHETIC_MAXFE','maxFE');
            cfg = SyntheticRunner.overrideValue(cfg,'SYNTHETIC_MAX_INSTANCES','maxInstances');
            cfg = SyntheticRunner.overrideValue(cfg,'SYNTHETIC_SPLITS','splits');
            cfg = SyntheticRunner.overrideValue(cfg,'SYNTHETIC_INSTANCE_NAMES','instanceNames');
            cfg = SyntheticRunner.overrideValue(cfg,'SYNTHETIC_SKIP_SUMMARY','skipSummary');
            cfg = SyntheticRunner.overrideValue(cfg,'SYNTHETIC_FORCE_RERUN','forceRerun');
            cfg = SyntheticRunner.overrideValue(cfg,'SYNTHETIC_EXPERIMENT_NAME','experiment');
            cfg = SyntheticRunner.overrideValue(cfg,'SYNTHETIC_DATASET_LABEL','datasetLabel');
            cfg.saveGenerations = max(1,cfg.maxFE / cfg.N);
        end

        function cfg = overrideValue(cfg,varName,fieldName)
            if evalin('base',sprintf('exist(''%s'',''var'')',varName))
                cfg.(fieldName) = evalin('base',varName);
            end
        end

        function manifest = loadManifest(manifestPath,scriptDir)
            if ~exist(manifestPath,'file')
                error('SyntheticRunner:MissingManifest','Manifest not found: %s',manifestPath);
            end
            manifest = readtable(manifestPath);
            for ii = 1:height(manifest)
                p = SyntheticRunner.cellValue(manifest.path(ii));
                if isempty(regexp(p,'^[A-Za-z]:[\\/]', 'once'))
                    p = fullfile(scriptDir,p);
                end
                manifest.path(ii) = {p};
            end
        end

        function manifest = filterManifest(manifest,cfg)
            splitMask = false(height(manifest),1);
            splits = SyntheticRunner.asCellstr(cfg.splits);
            for si = 1:numel(splits)
                splitMask = splitMask | strcmp(manifest.split,splits{si});
            end
            manifest = manifest(splitMask,:);

            names = SyntheticRunner.asCellstr(cfg.instanceNames);
            if ~isempty(names)
                nameMask = false(height(manifest),1);
                for ni = 1:numel(names)
                    nameMask = nameMask | strcmp(manifest.instance,names{ni});
                end
                manifest = manifest(nameMask,:);
            end

            if isfinite(cfg.maxInstances)
                keep = min(height(manifest),cfg.maxInstances);
                manifest = manifest(1:keep,:);
            end
        end

        function ok = hasCompleteRun(runDir)
            ok = exist(fullfile(runDir,'pf_obj.csv'),'file') && ...
                exist(fullfile(runDir,'runtime.csv'),'file') && ...
                exist(fullfile(runDir,'generation_pf_points.csv'),'file') && ...
                exist(fullfile(runDir,'generation_population_log.csv'),'file');
        end

        function writeConfig(cfg,method,nRows)
            fid = fopen(fullfile(cfg.outRoot,sprintf('config_%s.txt',method)),'w');
            fprintf(fid,'experiment=%s\n',cfg.experiment);
            fprintf(fid,'manifestPath=%s\n',cfg.manifestPath);
            fprintf(fid,'selectedManifestRows=%d\n',nRows);
            fprintf(fid,'splits=%s\n',strjoin(SyntheticRunner.asCellstr(cfg.splits),','));
            fprintf(fid,'runs=%d\n',cfg.runs);
            fprintf(fid,'algorithm=%s\n',method);
            fprintf(fid,'N=%d\n',cfg.N);
            fprintf(fid,'maxFE=%d\n',cfg.maxFE);
            fprintf(fid,'rng=%s\n',cfg.rngType);
            fprintf(fid,'seed=run index\n');
            fclose(fid);
        end

        function writeInstanceMetadata(runDir,row,method,cfg)
            T = table();
            T.method = {method};
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
            writetable(T,fullfile(runDir,'instance_metadata.csv'));
        end

        function rebuildSummary(outRoot,methods)
            files = dir(fullfile(outRoot,'**','runtime.csv'));
            rows = {};
            for fi = 1:numel(files)
                runDir = files(fi).folder;
                pfFile = fullfile(runDir,'pf_obj.csv');
                metaFile = fullfile(runDir,'instance_metadata.csv');
                if ~exist(pfFile,'file') || ~exist(metaFile,'file')
                    continue;
                end
                meta = readtable(metaFile);
                method = SyntheticRunner.cellValue(meta{1,1});
                if ~any(strcmp(method,methods))
                    continue;
                end
                rt = readtable(fullfile(runDir,'runtime.csv'));
                pfObj = readmatrix(pfFile);
                runToken = regexp(runDir,[regexptranslate('escape',filesep) 'run_(\d+)$'],'tokens','once');
                if isempty(runToken)
                    run = NaN;
                else
                    run = str2double(runToken{1});
                end
                rows(end+1,:) = { ...
                    method, ...
                    SyntheticRunner.cellValue(meta{1,3}), ...
                    SyntheticRunner.cellValue(meta{1,2}), ...
                    meta{1,4},meta{1,5},meta{1,6}, ...
                    SyntheticRunner.cellValue(meta{1,7}), ...
                    SyntheticRunner.cellValue(meta{1,8}), ...
                    SyntheticRunner.cellValue(meta{1,9}), ...
                    run,size(pfObj,1),rt{1,1}, ...
                    mean(pfObj(:,1)),mean(-pfObj(:,2))}; %#ok<AGROW>
            end
            if isempty(rows)
                return;
            end
            T = cell2table(rows,'VariableNames',{ ...
                'method','split','instance','assets','K','k_ratio', ...
                'corr_structure','return_distribution','risk_structure', ...
                'run','pf_size','runtime_sec','mean_risk','mean_return'});
            writetable(T,fullfile(outRoot,'run_summary.csv'));
            S = groupsummary(T,{'method','split','assets','K'},{'mean','std'}, ...
                {'pf_size','runtime_sec','mean_risk','mean_return'});
            writetable(S,fullfile(outRoot,'summary_by_method_split_assets_k.csv'));
            disp(S);
        end

        function value = cellValue(x)
            if iscell(x)
                value = x{1};
            elseif isstring(x)
                value = char(x(1));
            else
                value = x;
            end
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
                error('SyntheticRunner:InvalidCellstr','Expected char, string, or cell array.');
            end
        end
    end
end
