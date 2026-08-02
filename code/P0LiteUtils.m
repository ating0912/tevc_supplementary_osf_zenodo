classdef P0LiteUtils
% Shared utilities for P0-lite portfolio experiments.
% This file contains no algorithm-specific launch list.

    methods(Static)
        function cfg = baseConfig(scriptDir, smoke)
            cfg = struct();
            cfg.instance = 'port1';
            cfg.dataPath = fullfile(scriptDir,'data','orlib','port1.txt');
            cfg.KValues = [5 10 15 20 25 30];
            cfg.runs = 30;
            cfg.N = 100;
            cfg.maxFE = 10000;
            cfg.saveGenerations = cfg.maxFE / cfg.N;
            cfg.rngType = 'mcg16807';
            cfg.smoke = smoke;
            if cfg.smoke
                cfg.KValues = 5;
                cfg.runs = 1;
                cfg.maxFE = 1000;
                cfg.saveGenerations = cfg.maxFE / cfg.N;
            end
        end

        function [mu,Sigma] = loadORLibraryPortfile(filePath)
            txt = fileread(filePath);
            nums = sscanf(txt,'%f');
            idx = 1;
            n = round(nums(idx));
            idx = idx + 1;
            mu = zeros(n,1);
            stdv = zeros(n,1);
            for i = 1:n
                mu(i) = nums(idx);
                stdv(i) = nums(idx+1);
                idx = idx + 2;
            end
            corr = eye(n);
            while idx + 2 <= numel(nums)
                i = round(nums(idx));
                j = round(nums(idx+1));
                rij = nums(idx+2);
                if i >= 1 && i <= n && j >= 1 && j <= n
                    corr(i,j) = rij;
                    corr(j,i) = rij;
                end
                idx = idx + 3;
            end
            Sigma = (stdv*stdv') .* corr;
            Sigma = 0.5*(Sigma+Sigma');
        end

        function writeConfig(outRoot,cfg,nAssets,method)
            fid = fopen(fullfile(outRoot,sprintf('config_%s.txt',method)),'w');
            fprintf(fid,'instance=%s\n',cfg.instance);
            fprintf(fid,'dataPath=%s\n',cfg.dataPath);
            fprintf(fid,'assets=%d\n',nAssets);
            fprintf(fid,'KValues=%s\n',mat2str(cfg.KValues));
            fprintf(fid,'runs=%d\n',cfg.runs);
            fprintf(fid,'algorithm=%s\n',method);
            fprintf(fid,'N=%d\n',cfg.N);
            fprintf(fid,'maxFE=%d\n',cfg.maxFE);
            fprintf(fid,'rng=%s\n',cfg.rngType);
            fprintf(fid,'seed=run index\n');
            fclose(fid);
        end

        function saveRun(outDir,Dec,Obj,pfDec,pfObj,runtime,K)
            writematrix(Dec,fullfile(outDir,'population_dec.csv'));
            writematrix(Obj,fullfile(outDir,'population_obj.csv'));
            writematrix(pfDec,fullfile(outDir,'pf_dec.csv'));
            writematrix(pfObj,fullfile(outDir,'pf_obj.csv'));
            writematrix(pfDec,fullfile(outDir,'final_archive_dec.csv'));
            writematrix(pfObj,fullfile(outDir,'final_archive_obj.csv'));
            writematrix(pfObj,fullfile(outDir,'pf_points.csv'));
            writetable(table(runtime,'VariableNames',{'runtime_sec'}),fullfile(outDir,'runtime.csv'));
            if nargin >= 7
                pfFeasible = P0LiteUtils.feasibleRateFromDec(pfDec,K);
                popFeasible = P0LiteUtils.feasibleRateFromDec(Dec,K);
                T = table(pfFeasible,popFeasible,'VariableNames',{'PF_Feasible_Rate','Population_Feasible_Rate'});
                writetable(T,fullfile(outDir,'feasible_rate.csv'));

                pfViolation = P0LiteUtils.constraintViolationFromDec(pfDec,K);
                popViolation = P0LiteUtils.constraintViolationFromDec(Dec,K);
                C = table( ...
                    P0LiteUtils.nanMean(pfViolation),P0LiteUtils.nanMax(pfViolation), ...
                    P0LiteUtils.nanMean(popViolation),P0LiteUtils.nanMax(popViolation), ...
                    pfFeasible,popFeasible, ...
                    'VariableNames',{'PF_Mean_Violation','PF_Max_Violation', ...
                    'Population_Mean_Violation','Population_Max_Violation', ...
                    'PF_Feasible_Rate','Population_Feasible_Rate'});
                writetable(C,fullfile(outDir,'constraint_metrics.csv'));

                archiveSize = size(pfObj,1);
                archiveDiversity = P0LiteUtils.objectiveSpread(pfObj);
                archiveSpacing = P0LiteUtils.objectiveSpacing(pfObj);
                A = table(archiveSize,archiveDiversity,archiveSpacing, ...
                    'VariableNames',{'Archive_Size','Archive_Diversity','Archive_Spacing'});
                writetable(A,fullfile(outDir,'archive_metrics.csv'));
            end
        end

        function saveGenerationSnapshots(outDir,result,K,N)
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
                Con = Pop.cons;
                feasible = all(Con <= 0,2);
                feasibleRate = mean(feasible);
                if any(feasible)
                    [~,pfObj] = P0LiteUtils.firstFrontDecObj(Dec(feasible,:),Obj(feasible,:));
                else
                    pfObj = [];
                end
                pfSize = size(pfObj,1);
                popRows(end+1,:) = [generation,evaluated,size(Obj,1),sum(feasible),feasibleRate,pfSize]; %#ok<AGROW>
                if pfSize > 0
                    pointIndex = (1:pfSize)';
                    pointRows = [pointRows; ...
                        [repmat([generation,evaluated],pfSize,1),pointIndex,pfObj(:,1),pfObj(:,2),-pfObj(:,2)]]; %#ok<AGROW>
                end
            end
            pointHeader = {'generation','evaluations','point_index','risk','minus_return','return'};
            popHeader = {'generation','evaluations','population_size','feasible_count','feasible_rate','pf_size'};
            writetable(array2table(pointRows,'VariableNames',pointHeader),fullfile(outDir,'generation_pf_points.csv'));
            writetable(array2table(popRows,'VariableNames',popHeader),fullfile(outDir,'generation_population_log.csv'));
        end

        function rate = feasibleRateFromDec(Dec,K)
            if isempty(Dec)
                rate = NaN;
                return;
            end
            tol = 1e-8;
            card = sum(Dec > tol,2);
            sumOk = abs(sum(Dec,2)-1) <= 1e-6;
            boundsOk = all(Dec >= -tol,2) & all(Dec <= 1+tol,2);
            rate = mean(card <= K & sumOk & boundsOk);
        end

        function violation = constraintViolationFromDec(Dec,K)
            if isempty(Dec)
                violation = NaN;
                return;
            end
            tol = 1e-8;
            cardViolation = max(sum(Dec > tol,2) - K,0);
            sumViolation = abs(sum(Dec,2)-1);
            lowerViolation = sum(max(-Dec,0),2);
            upperViolation = sum(max(Dec-1,0),2);
            violation = cardViolation + sumViolation + lowerViolation + upperViolation;
        end

        function value = objectiveSpread(Obj)
            if size(Obj,1) <= 1
                value = 0;
                return;
            end
            span = max(Obj,[],1) - min(Obj,[],1);
            value = sqrt(sum(span.^2));
        end

        function value = objectiveSpacing(Obj)
            if size(Obj,1) <= 2
                value = 0;
                return;
            end
            n = size(Obj,1);
            D = inf(n,n);
            for i = 1:n
                diff = Obj - Obj(i,:);
                D(:,i) = sqrt(sum(diff.^2,2));
            end
            D(1:n+1:end) = inf;
            nearest = min(D,[],2);
            nearest = nearest(~isnan(nearest) & isfinite(nearest));
            if isempty(nearest)
                value = 0;
            else
                value = std(nearest);
            end
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

        function [pfDec,pfObj] = firstFrontDecObj(Dec,Obj)
            n = size(Obj,1);
            dominated = false(n,1);
            for i = 1:n
                if dominated(i)
                    continue;
                end
                for j = 1:n
                    if i == j
                        continue;
                    end
                    if all(Obj(j,:) <= Obj(i,:)) && any(Obj(j,:) < Obj(i,:))
                        dominated(i) = true;
                        break;
                    end
                end
            end
            pfDec = Dec(~dominated,:);
            pfObj = Obj(~dominated,:);
            [~,ord] = sort(pfObj(:,1),'ascend');
            pfDec = pfDec(ord,:);
            pfObj = pfObj(ord,:);
        end

        function rebuildSummary(outRoot,methods)
            rows = {};
            for K = [5 10 15 20 25 30]
                for mi = 1:numel(methods)
                    method = methods{mi};
                    for run = 1:30
                        runDir = fullfile(outRoot,sprintf('K_%02d',K),method,sprintf('run_%03d',run));
                        pfFile = fullfile(runDir,'pf_obj.csv');
                        rtFile = fullfile(runDir,'runtime.csv');
                        if ~exist(pfFile,'file') || ~exist(rtFile,'file')
                            continue;
                        end
                        pfObj = readmatrix(pfFile);
                        rt = readtable(rtFile);
                        rows(end+1,:) = {method,K,run,size(pfObj,1),rt.runtime_sec(1),mean(pfObj(:,1)),mean(-pfObj(:,2))}; %#ok<AGROW>
                    end
                end
            end
            T = cell2table(rows,'VariableNames',{'method','K','run','pf_size','runtime_sec','mean_risk','mean_return'});
            writetable(T,fullfile(outRoot,'run_summary.csv'));
            if ~isempty(T)
                S = groupsummary(T,{'method','K'},{'mean','std'},{'pf_size','runtime_sec','mean_risk','mean_return'});
                writetable(S,fullfile(outRoot,'summary_by_method_k.csv'));
                disp(S);
            end
        end
    end
end
