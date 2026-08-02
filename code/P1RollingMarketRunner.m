classdef P1RollingMarketRunner
% Shared runner for P1 rolling-window real-market validation.

    methods(Static)
        function runAlgorithm(algorithmHandle,method)
            scriptDir = fileparts(mfilename('fullpath'));
            platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');
            restoredefaultpath;
            addpath(genpath(platemoRoot));
            addpath(scriptDir);

            cfg = P1RollingMarketRunner.baseConfig(scriptDir);
            cfg = P1RollingMarketRunner.applyOverrides(cfg);
            cfg = P1RollingMarketRunner.loadThetaAssignments(cfg);
            if ~exist(cfg.outRoot,'dir'); mkdir(cfg.outRoot); end

            manifest = readtable(cfg.manifestPath);
            manifest = P1RollingMarketRunner.filterManifest(manifest,cfg);
            writetable(manifest,fullfile(cfg.outRoot,'rolling_manifest_used.csv'));
            fprintf('P1 rolling-window market validation | %s\n',method);
            fprintf('Windows=%d, runs=%d, N=%d, maxFE=%d\n',height(manifest),cfg.runs,cfg.N,cfg.maxFE);
            fprintf('Output: %s\n',cfg.outRoot);

            for wi = 1:height(manifest)
                row = manifest(wi,:);
                universe = P1RollingMarketRunner.text(row.universe);
                windowId = P1RollingMarketRunner.text(row.window_id);
                dataPath = P1RollingMarketRunner.text(row.data_path);
                K = row.K;
                D = row.assets;
                fprintf('=== %s | %s | D=%d K=%d | %s ===\n',universe,windowId,D,K,method);
                for run = 1:cfg.runs
                    runDir = fullfile(cfg.outRoot,universe,windowId,method,sprintf('run_%03d',run));
                    if ~cfg.forceRerun && P1RollingMarketRunner.hasCompleteRun(runDir)
                        continue;
                    end
                    if ~exist(runDir,'dir'); mkdir(runDir); end
                    thetaCfg = P1RollingMarketRunner.thetaConfigFor(cfg,row,method);
                    if isempty(fieldnames(thetaCfg))
                        evalin('base','clear(''ECMADE_MOO_KB_THETA'')');
                    else
                        assignin('base','ECMADE_MOO_KB_THETA',thetaCfg);
                    end
                    P1RollingMarketRunner.writeMetadata(runDir,row,method,cfg,thetaCfg);
                    fprintf('%s %s %s Run %03d/%03d\n',method,universe,windowId,run,cfg.runs);
                    rng(run,cfg.rngType);
                    t = tic;
                    G = GLOBAL('-algorithm',algorithmHandle, ...
                        '-problem',{@PortfolioMarketWindow,dataPath,K}, ...
                        '-N',cfg.N,'-M',2,'-D',D, ...
                        '-evaluation',cfg.maxFE,'-run',run, ...
                        '-save',cfg.saveGenerations,'-outputFcn',@(varargin)[]);
                    G.Start();
                    runtime = toc(t);
                    Pop = G.result{end,2};
                    Dec = Pop.decs;
                    Obj = Pop.objs;
                    [pfDec,pfObj] = P0LiteUtils.firstFrontDecObj(Dec,Obj);
                    P0LiteUtils.saveRun(runDir,Dec,Obj,pfDec,pfObj,runtime,K);
                    P0LiteUtils.saveGenerationSnapshots(runDir,G.result,K,cfg.N);
                    P1RollingMarketRunner.saveSelectedBacktest(runDir,pfDec,pfObj,dataPath,cfg.transactionCost);
                end
            end
            P1RollingMarketRunner.rebuildSummary(cfg.outRoot);
        end

        function cfg = baseConfig(scriptDir)
            cfg = struct();
            cfg.manifestPath = fullfile(scriptDir,'p0_lite_outputs','p1_rolling_window_market_validation_20260719','windows','rolling_window_manifest.csv');
            cfg.outRoot = fullfile(scriptDir,'p0_lite_outputs','p1_rolling_window_market_validation_20260719','raw');
            cfg.universes = {};
            cfg.windowIds = {};
            cfg.maxWindows = inf;
            cfg.runs = 10;
            cfg.N = 100;
            cfg.maxFE = 10000;
            cfg.saveGenerations = cfg.maxFE / cfg.N;
            cfg.rngType = 'mcg16807';
            cfg.forceRerun = false;
            cfg.transactionCost = 0.001;
            cfg.thetaAssignmentPath = '';
            cfg.thetaAssignments = table();
        end

        function cfg = applyOverrides(cfg)
            cfg = P1RollingMarketRunner.override(cfg,'P1_ROLLING_MANIFEST','manifestPath');
            cfg = P1RollingMarketRunner.override(cfg,'P1_ROLLING_OUT_ROOT','outRoot');
            cfg = P1RollingMarketRunner.override(cfg,'P1_ROLLING_UNIVERSES','universes');
            cfg = P1RollingMarketRunner.override(cfg,'P1_ROLLING_WINDOW_IDS','windowIds');
            cfg = P1RollingMarketRunner.override(cfg,'P1_ROLLING_MAX_WINDOWS','maxWindows');
            cfg = P1RollingMarketRunner.override(cfg,'P1_ROLLING_RUNS','runs');
            cfg = P1RollingMarketRunner.override(cfg,'P1_ROLLING_N','N');
            cfg = P1RollingMarketRunner.override(cfg,'P1_ROLLING_MAXFE','maxFE');
            cfg = P1RollingMarketRunner.override(cfg,'P1_ROLLING_FORCE_RERUN','forceRerun');
            cfg = P1RollingMarketRunner.override(cfg,'P1_ROLLING_TRANSACTION_COST','transactionCost');
            cfg = P1RollingMarketRunner.override(cfg,'P1_ROLLING_THETA_ASSIGNMENT','thetaAssignmentPath');
            cfg.saveGenerations = max(1,cfg.maxFE / cfg.N);
        end

        function cfg = override(cfg,varName,field)
            if evalin('base',sprintf('exist(''%s'',''var'')',varName))
                cfg.(field) = evalin('base',varName);
            end
        end

        function cfg = loadThetaAssignments(cfg)
            if ischar(cfg.thetaAssignmentPath) || isstring(cfg.thetaAssignmentPath)
                path = char(cfg.thetaAssignmentPath);
            else
                path = '';
            end
            if ~isempty(path)
                cfg.thetaAssignments = readtable(path);
            end
        end

        function manifest = filterManifest(manifest,cfg)
            universes = P1RollingMarketRunner.asCell(cfg.universes);
            if ~isempty(universes)
                mask = false(height(manifest),1);
                for i = 1:numel(universes)
                    mask = mask | strcmp(manifest.universe,universes{i});
                end
                manifest = manifest(mask,:);
            end
            windowIds = P1RollingMarketRunner.asCell(cfg.windowIds);
            if ~isempty(windowIds)
                mask = false(height(manifest),1);
                for i = 1:numel(windowIds)
                    mask = mask | strcmp(manifest.window_id,windowIds{i});
                end
                manifest = manifest(mask,:);
            end
            if isfinite(cfg.maxWindows)
                manifest = manifest(1:min(height(manifest),cfg.maxWindows),:);
            end
        end

        function ok = hasCompleteRun(runDir)
            ok = exist(fullfile(runDir,'pf_obj.csv'),'file') && ...
                exist(fullfile(runDir,'selected_portfolio.csv'),'file') && ...
                exist(fullfile(runDir,'backtest_metrics.csv'),'file') && ...
                exist(fullfile(runDir,'runtime.csv'),'file');
        end

        function thetaCfg = thetaConfigFor(cfg,row,method)
            thetaCfg = struct();
            if isempty(cfg.thetaAssignments) || height(cfg.thetaAssignments) == 0
                return;
            end
            A = cfg.thetaAssignments;
            universe = P1RollingMarketRunner.text(row.universe);
            windowId = P1RollingMarketRunner.text(row.window_id);
            methodText = char(method);
            mask = strcmp(cellstr(string(A.method)),methodText) & ...
                strcmp(cellstr(string(A.universe)),universe) & ...
                strcmp(cellstr(string(A.window_id)),windowId);
            idx = find(mask,1,'first');
            if isempty(idx)
                warning('No theta assignment found for %s %s %s. Using default config.',methodText,universe,windowId);
                return;
            end
            rec = A(idx,:);
            numericFields = {'subpops','archiveSize','theta','stagnationThreshold', ...
                'exploitationAlpha','fScale','crScale','fMax','consensusBins', ...
                'archiveConsWeight','bestConsWeight','bestCentralWeight', ...
                'minSubpopSize','eliteRatio','archiveLimitFactor'};
            textFields = {'exchangeMode','bestGuide','operatorMode'};
            logicalFields = {'consensusArchive'};
            for i = 1:numel(numericFields)
                name = numericFields{i};
                if ismember(name,A.Properties.VariableNames)
                    value = rec.(name);
                    if iscell(value); value = value{1}; end
                    if isstring(value) || ischar(value)
                        value = str2double(value);
                    end
                    if ~isnan(value)
                        thetaCfg.(name) = value;
                    end
                end
            end
            for i = 1:numel(textFields)
                name = textFields{i};
                if ismember(name,A.Properties.VariableNames)
                    thetaCfg.(name) = P1RollingMarketRunner.text(rec.(name));
                end
            end
            for i = 1:numel(logicalFields)
                name = logicalFields{i};
                if ismember(name,A.Properties.VariableNames)
                    value = rec.(name);
                    if iscell(value); value = value{1}; end
                    if isstring(value) || ischar(value)
                        value = str2double(value);
                    end
                    thetaCfg.(name) = logical(value);
                end
            end
        end

        function writeMetadata(runDir,row,method,cfg,thetaCfg)
            T = table();
            T.method = {method};
            T.universe = row.universe;
            T.window_id = row.window_id;
            T.data_path = row.data_path;
            T.train_start = row.train_start;
            T.train_end = row.train_end;
            T.test_start = row.test_start;
            T.test_end = row.test_end;
            T.assets = row.assets;
            T.K = row.K;
            T.train_days = row.train_days;
            T.test_days = row.test_days;
            T.N = cfg.N;
            T.maxFE = cfg.maxFE;
            T.runs = cfg.runs;
            T.transaction_cost = cfg.transactionCost;
            if nargin >= 5 && ~isempty(fieldnames(thetaCfg))
                names = fieldnames(thetaCfg);
                for i = 1:numel(names)
                    value = thetaCfg.(names{i});
                    if ischar(value) || isstring(value)
                        T.(names{i}) = {char(value)};
                    else
                        T.(names{i}) = value;
                    end
                end
            end
            writetable(T,fullfile(runDir,'window_metadata.csv'));
        end

        function saveSelectedBacktest(runDir,pfDec,pfObj,dataPath,transactionCost)
            data = load(dataPath,'testReturns','mu','Sigma','tickers');
            if isempty(pfDec)
                return;
            end
            trainReturn = -pfObj(:,2);
            trainRisk = sqrt(max(pfObj(:,1),0));
            sharpe = trainReturn ./ max(trainRisk,1e-12);
            [~,idx] = max(sharpe);
            w = pfDec(idx,:);
            w = w ./ max(sum(w),1e-12);
            tickers = cellstr(data.tickers);
            selected = w(:) > 1e-8;
            portfolio = table(tickers(:),w(:),selected(:),'VariableNames',{'ticker','weight','selected'});
            writetable(portfolio,fullfile(runDir,'selected_portfolio.csv'));

            r = data.testReturns * w(:);
            r = r(:);
            grossReturn = prod(1+r) - 1;
            annReturn = (1 + grossReturn)^(252/max(numel(r),1)) - 1;
            annVol = std(r) * sqrt(252);
            sharpeOos = mean(r) / max(std(r),1e-12) * sqrt(252);
            downside = r(r < 0);
            if isempty(downside); sortino = Inf; else; sortino = mean(r) / max(std(downside),1e-12) * sqrt(252); end
            equity = cumprod(1+r);
            peak = cummax(equity);
            mdd = min(equity ./ peak - 1);
            turnover = sum(abs(w(:)));
            tcCost = transactionCost * turnover;
            netReturn = grossReturn - tcCost;
            annNetReturn = (1 + netReturn)^(252/max(numel(r),1)) - 1;
            T = table(grossReturn,netReturn,annReturn,annNetReturn,annVol,sharpeOos,sortino,mdd,turnover,tcCost, ...
                'VariableNames',{'gross_return','net_return','annual_return','annual_net_return','annual_volatility','sharpe','sortino','max_drawdown','turnover','transaction_cost'});
            writetable(T,fullfile(runDir,'backtest_metrics.csv'));
            writematrix(r,fullfile(runDir,'test_daily_returns.csv'));
        end

        function rebuildSummary(outRoot)
            files = dir(fullfile(outRoot,'**','backtest_metrics.csv'));
            rows = {};
            for fi = 1:numel(files)
                runDir = files(fi).folder;
                metaFile = fullfile(runDir,'window_metadata.csv');
                if ~exist(metaFile,'file'); continue; end
                meta = readtable(metaFile);
                bt = readtable(fullfile(runDir,'backtest_metrics.csv'));
                rt = readtable(fullfile(runDir,'runtime.csv'));
                runToken = regexp(runDir,[regexptranslate('escape',filesep) 'run_(\d+)$'],'tokens','once');
                if isempty(runToken); run = NaN; else; run = str2double(runToken{1}); end
                rows(end+1,:) = {P1RollingMarketRunner.text(meta.method),P1RollingMarketRunner.text(meta.universe), ...
                    P1RollingMarketRunner.text(meta.window_id),run,meta.assets(1),meta.K(1),meta.train_days(1),meta.test_days(1), ...
                    bt.gross_return(1),bt.net_return(1),bt.annual_return(1),bt.annual_net_return(1),bt.annual_volatility(1), ...
                    bt.sharpe(1),bt.sortino(1),bt.max_drawdown(1),bt.turnover(1),bt.transaction_cost(1),rt.runtime_sec(1)}; %#ok<AGROW>
            end
            if isempty(rows); return; end
            T = cell2table(rows,'VariableNames',{'method','universe','window_id','run','assets','K','train_days','test_days', ...
                'gross_return','net_return','annual_return','annual_net_return','annual_volatility','sharpe','sortino','max_drawdown','turnover','transaction_cost','runtime_sec'});
            writetable(T,fullfile(outRoot,'rolling_backtest_run_summary.csv'));
        end

        function value = text(x)
            if iscell(x); value = x{1};
            elseif isstring(x); value = char(x(1));
            else; value = char(x); end
        end

        function out = asCell(x)
            if isempty(x); out = {};
            elseif ischar(x); out = {x};
            elseif isstring(x); out = cellstr(x);
            else; out = x; end
        end
    end
end
