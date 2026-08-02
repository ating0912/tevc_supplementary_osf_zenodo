classdef P1KnapsackRunner
% Shared launcher for the TEVC P1 multi-objective knapsack test bed.

    methods(Static)
        function runAlgorithm(algorithmHandle, method)
            scriptDir = fileparts(mfilename('fullpath'));
            platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');
            outRoot = fullfile(scriptDir,'p0_lite_outputs','p1_multi_objective_knapsack');

            restoredefaultpath;
            addpath(genpath(platemoRoot));
            addpath(scriptDir);

            cfg = P1KnapsackRunner.baseConfig(scriptDir,outRoot);
            cfg = P1KnapsackRunner.applyWorkspaceOverrides(cfg);
            if ~exist(cfg.outRoot,'dir'); mkdir(cfg.outRoot); end

            manifest = P1KnapsackRunner.defaultManifest(cfg);
            manifest = P1KnapsackRunner.filterManifest(manifest,cfg);
            writetable(manifest,fullfile(cfg.outRoot,'manifest_selected.csv'));
            P1KnapsackRunner.writeConfig(cfg,method,height(manifest));

            fprintf('P1 multi-objective knapsack runner\n');
            fprintf('Method: %s\n',method);
            fprintf('Manifest rows: %d\n',height(manifest));
            fprintf('Runs per instance: %d, N=%d, maxFE=%d\n',cfg.runs,cfg.N,cfg.maxFE);

            for ii = 1:height(manifest)
                row = manifest(ii,:);
                instance = P1KnapsackRunner.cellValue(row.instance);
                splitName = P1KnapsackRunner.cellValue(row.split);
                D = row.items;
                M = row.objectives;
                seed = row.seed;
                capacityRatio = row.capacity_ratio;
                profitMode = P1KnapsackRunner.cellValue(row.profit_mode);
                fprintf('=== %s | %s | D=%d | %s ===\n',splitName,instance,D,method);

                for run = 1:cfg.runs
                    fprintf('%s %s Run %03d/%03d\n',method,instance,run,cfg.runs);
                    runDir = fullfile(cfg.outRoot,splitName,instance,method,sprintf('run_%03d',run));
                    if ~cfg.forceRerun && P1KnapsackRunner.hasCompleteRun(runDir)
                        continue;
                    end
                    if ~exist(runDir,'dir'); mkdir(runDir); end
                    P1KnapsackRunner.writeInstanceMetadata(runDir,row,method,cfg);

                    t = tic;
                    rng(run,cfg.rngType);
                    G = GLOBAL('-algorithm',algorithmHandle, ...
                        '-problem',{@P1MOKP,D,M,seed,capacityRatio,profitMode}, ...
                        '-N',cfg.N,'-M',M,'-D',D, ...
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

            if ~cfg.skipSummary
                P1KnapsackRunner.rebuildSummary(cfg.outRoot,{'NSGAII','SPEA2','MOEAD','GDE3','ECMADE_MOO','A_MPMO'});
            else
                fprintf('P1 MOKP summary rebuild skipped.\n');
            end
            fprintf('%s outputs: %s\n',method,cfg.outRoot);
        end

        function cfg = baseConfig(scriptDir,outRoot)
            cfg = struct();
            cfg.experiment = 'p1_multi_objective_knapsack';
            cfg.outRoot = outRoot;
            cfg.splits = {'test'};
            cfg.runs = 30;
            cfg.N = 100;
            cfg.maxFE = 10000;
            cfg.saveGenerations = cfg.maxFE / cfg.N;
            cfg.rngType = 'mcg16807';
            cfg.maxInstances = inf;
            cfg.instanceNames = {};
            cfg.skipSummary = false;
            cfg.forceRerun = false;
            cfg.scriptDir = scriptDir;
            cfg.items = [100 250 500];
            cfg.objectives = 2;
            cfg.capacityRatios = [0.35 0.50 0.65];
            cfg.profitModes = {'independent','conflicting'};
            cfg.replicates = 1;
            if P1KnapsackRunner.baseExists('P1_MOKP_SMOKE') && evalin('base','P1_MOKP_SMOKE')
                cfg.runs = 1;
                cfg.maxFE = 1000;
                cfg.saveGenerations = cfg.maxFE / cfg.N;
                cfg.maxInstances = 1;
                cfg.skipSummary = true;
            end
        end

        function cfg = applyWorkspaceOverrides(cfg)
            cfg = P1KnapsackRunner.overrideValue(cfg,'P1_MOKP_OUT_ROOT','outRoot');
            cfg = P1KnapsackRunner.overrideValue(cfg,'P1_MOKP_RUNS','runs');
            cfg = P1KnapsackRunner.overrideValue(cfg,'P1_MOKP_N','N');
            cfg = P1KnapsackRunner.overrideValue(cfg,'P1_MOKP_MAXFE','maxFE');
            cfg = P1KnapsackRunner.overrideValue(cfg,'P1_MOKP_MAX_INSTANCES','maxInstances');
            cfg = P1KnapsackRunner.overrideValue(cfg,'P1_MOKP_SPLITS','splits');
            cfg = P1KnapsackRunner.overrideValue(cfg,'P1_MOKP_INSTANCE_NAMES','instanceNames');
            cfg = P1KnapsackRunner.overrideValue(cfg,'P1_MOKP_SKIP_SUMMARY','skipSummary');
            cfg = P1KnapsackRunner.overrideValue(cfg,'P1_MOKP_FORCE_RERUN','forceRerun');
            cfg.saveGenerations = max(1,cfg.maxFE / cfg.N);
        end

        function cfg = overrideValue(cfg,varName,fieldName)
            if P1KnapsackRunner.baseExists(varName)
                cfg.(fieldName) = evalin('base',varName);
            end
        end

        function tf = baseExists(varName)
            tf = evalin('base',sprintf('exist(''%s'',''var'')',varName)) ~= 0;
        end

        function manifest = defaultManifest(cfg)
            rows = {};
            modes = cfg.profitModes;
            for di = 1:numel(cfg.items)
                for ci = 1:numel(cfg.capacityRatios)
                    for mi = 1:numel(modes)
                        for ri = 1:cfg.replicates
                            D = cfg.items(di);
                            cr = cfg.capacityRatios(ci);
                            mode = modes{mi};
                            seed = 20260718 + 10000*di + 1000*ci + 100*mi + ri;
                            instance = sprintf('mokp_m%02d_d%03d_c%02d_%s_r%02d_s%d', ...
                                cfg.objectives,D,round(100*cr),mode,ri,seed);
                            rows(end+1,:) = {'test',instance,D,cfg.objectives,cr,mode,ri,seed}; %#ok<AGROW>
                        end
                    end
                end
            end
            manifest = cell2table(rows,'VariableNames', ...
                {'split','instance','items','objectives','capacity_ratio','profit_mode','replicate','seed'});
        end

        function manifest = filterManifest(manifest,cfg)
            splitMask = false(height(manifest),1);
            splits = P1KnapsackRunner.asCellstr(cfg.splits);
            for si = 1:numel(splits)
                splitMask = splitMask | strcmp(manifest.split,splits{si});
            end
            manifest = manifest(splitMask,:);

            names = P1KnapsackRunner.asCellstr(cfg.instanceNames);
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
            fprintf(fid,'selectedManifestRows=%d\n',nRows);
            fprintf(fid,'splits=%s\n',strjoin(P1KnapsackRunner.asCellstr(cfg.splits),','));
            fprintf(fid,'runs=%d\n',cfg.runs);
            fprintf(fid,'algorithm=%s\n',method);
            fprintf(fid,'N=%d\n',cfg.N);
            fprintf(fid,'maxFE=%d\n',cfg.maxFE);
            fprintf(fid,'rng=%s\n',cfg.rngType);
            fprintf(fid,'seed=run index\n');
            fprintf(fid,'items=%s\n',mat2str(cfg.items));
            fprintf(fid,'objectives=%d\n',cfg.objectives);
            fprintf(fid,'capacityRatios=%s\n',mat2str(cfg.capacityRatios));
            fprintf(fid,'profitModes=%s\n',strjoin(cfg.profitModes,','));
            fclose(fid);
        end

        function writeInstanceMetadata(runDir,row,method,cfg)
            T = table();
            T.method = {method};
            T.instance = row.instance;
            T.split = row.split;
            T.items = row.items;
            T.objectives = row.objectives;
            T.capacity_ratio = row.capacity_ratio;
            T.profit_mode = row.profit_mode;
            T.replicate = row.replicate;
            T.seed = row.seed;
            T.N = cfg.N;
            T.maxFE = cfg.maxFE;
            T.runs = cfg.runs;
            writetable(T,fullfile(runDir,'instance_metadata.csv'));
        end

        function saveRun(outDir,Dec,Obj,pfDec,pfObj,runtime,row)
            writematrix(Dec,fullfile(outDir,'population_dec.csv'));
            writematrix(Obj,fullfile(outDir,'population_obj.csv'));
            writematrix(pfDec,fullfile(outDir,'pf_dec.csv'));
            writematrix(pfObj,fullfile(outDir,'pf_obj.csv'));
            writematrix(pfDec,fullfile(outDir,'final_archive_dec.csv'));
            writematrix(pfObj,fullfile(outDir,'final_archive_obj.csv'));
            writematrix(pfObj,fullfile(outDir,'pf_points.csv'));
            writetable(table(runtime,'VariableNames',{'runtime_sec'}),fullfile(outDir,'runtime.csv'));

            [pfFeasible,pfViolation] = P1KnapsackRunner.feasibility(pfDec,row);
            [popFeasible,popViolation] = P1KnapsackRunner.feasibility(Dec,row);
            writetable(table(pfFeasible,popFeasible, ...
                'VariableNames',{'PF_Feasible_Rate','Population_Feasible_Rate'}), ...
                fullfile(outDir,'feasible_rate.csv'));
            writetable(table(P1KnapsackRunner.nanMean(pfViolation),P1KnapsackRunner.nanMax(pfViolation), ...
                P1KnapsackRunner.nanMean(popViolation),P1KnapsackRunner.nanMax(popViolation), ...
                pfFeasible,popFeasible, ...
                'VariableNames',{'PF_Mean_Violation','PF_Max_Violation', ...
                'Population_Mean_Violation','Population_Max_Violation', ...
                'PF_Feasible_Rate','Population_Feasible_Rate'}), ...
                fullfile(outDir,'constraint_metrics.csv'));
            writetable(table(size(pfObj,1),P0LiteUtils.objectiveSpread(pfObj),P0LiteUtils.objectiveSpacing(pfObj), ...
                'VariableNames',{'Archive_Size','Archive_Diversity','Archive_Spacing'}), ...
                fullfile(outDir,'archive_metrics.csv'));
        end

        function saveGenerationSnapshots(outDir,result,row,N)
            pointRows = [];
            popRows = [];
            for gi = 1:size(result,1)
                if isempty(result{gi,1}) || isempty(result{gi,2})
                    continue;
                end
                evaluated = result{gi,1};
                generation = max(1,ceil(evaluated/N));
                Pop = result{gi,2};
                Obj = Pop.objs;
                Dec = Pop.decs;
                [feasibleRate,~] = P1KnapsackRunner.feasibility(Dec,row);
                [~,pfObj] = P0LiteUtils.firstFrontDecObj(Dec,Obj);
                pfSize = size(pfObj,1);
                popRows(end+1,:) = [generation,evaluated,size(Obj,1),round(feasibleRate*size(Obj,1)),feasibleRate,pfSize]; %#ok<AGROW>
                if pfSize > 0
                    pointIndex = (1:pfSize)';
                    totalProfit = repmat(P1KnapsackRunner.totalProfit(row),pfSize,1);
                    profit = totalProfit - pfObj;
                    pointRows = [pointRows; ...
                        [repmat([generation,evaluated],pfSize,1),pointIndex,pfObj(:,1),pfObj(:,2),profit(:,1),profit(:,2)]]; %#ok<AGROW>
                end
            end
            writetable(array2table(pointRows,'VariableNames', ...
                {'generation','evaluations','point_index','objective_1_loss','objective_2_loss','profit_1','profit_2'}), ...
                fullfile(outDir,'generation_pf_points.csv'));
            writetable(array2table(popRows,'VariableNames', ...
                {'generation','evaluations','population_size','feasible_count','feasible_rate','pf_size'}), ...
                fullfile(outDir,'generation_population_log.csv'));
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
                method = P1KnapsackRunner.cellValue(meta{1,1});
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
                rows(end+1,:) = {method, ...
                    P1KnapsackRunner.cellValue(meta{1,3}),P1KnapsackRunner.cellValue(meta{1,2}), ...
                    meta{1,4},meta{1,5},meta{1,6},P1KnapsackRunner.cellValue(meta{1,7}), ...
                    meta{1,8},meta{1,9},run,size(pfObj,1),rt{1,1},mean(pfObj(:,1)),mean(pfObj(:,2))}; %#ok<AGROW>
            end
            if isempty(rows)
                return;
            end
            T = cell2table(rows,'VariableNames', ...
                {'method','split','instance','items','objectives','capacity_ratio','profit_mode', ...
                'replicate','seed','run','pf_size','runtime_sec','mean_obj1_loss','mean_obj2_loss'});
            writetable(T,fullfile(outRoot,'run_summary.csv'));
            S = groupsummary(T,{'method','items','capacity_ratio','profit_mode'},{'mean','std'}, ...
                {'pf_size','runtime_sec','mean_obj1_loss','mean_obj2_loss'});
            writetable(S,fullfile(outRoot,'summary_by_method_instance_type.csv'));
            disp(S);
        end

        function [rate,violation] = feasibility(Dec,row)
            if isempty(Dec)
                rate = NaN;
                violation = NaN;
                return;
            end
            [~,W,C] = P1MOKP.makeData(row.objectives,row.items,row.seed,row.capacity_ratio, ...
                P1KnapsackRunner.cellValue(row.profit_mode));
            X = Dec > 0.5;
            loads = X * W';
            violation = sum(max(loads - repmat(C',size(X,1),1),0),2);
            rate = mean(violation <= 1e-8);
        end

        function total = totalProfit(row)
            [P,~,~] = P1MOKP.makeData(row.objectives,row.items,row.seed,row.capacity_ratio, ...
                P1KnapsackRunner.cellValue(row.profit_mode));
            total = sum(P,2)';
        end

        function value = nanMean(x)
            x = x(~isnan(x));
            if isempty(x)
                value = NaN;
            else
                value = mean(x);
            end
        end

        function value = nanMax(x)
            x = x(~isnan(x));
            if isempty(x)
                value = NaN;
            else
                value = max(x);
            end
        end

        function values = asCellstr(value)
            if isempty(value)
                values = {};
            elseif ischar(value)
                values = {value};
            elseif isstring(value)
                values = cellstr(value);
            else
                values = value;
            end
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
    end
end
