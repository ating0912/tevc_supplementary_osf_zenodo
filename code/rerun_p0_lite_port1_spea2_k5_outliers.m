% Rerun runtime-contaminated SPEA2 K=5 runs for P0-lite port1.

clear; clc;
scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');
dataPath = fullfile(scriptDir,'data','orlib','port1.txt');
outRoot = fullfile(scriptDir,'p0_lite_outputs','port1_nsga2_spea2');

restoredefaultpath;
addpath(genpath(platemoRoot));
addpath(scriptDir);

[mu,~] = load_orlibrary_portfile(dataPath);
K = 5;
runs = [26 27];
for run = runs
    fprintf('Rerun SPEA2 K=%d run_%03d\n',K,run);
    runDir = fullfile(outRoot,sprintf('K_%02d',K),'SPEA2',sprintf('run_%03d',run));
    if ~exist(runDir,'dir'); mkdir(runDir); end
    t = tic;
    rng(run,'mcg16807');
    G = GLOBAL('-algorithm',@SPEA2,'-problem',{@PortfolioORLIB,dataPath,K}, ...
        '-N',100,'-M',2,'-D',numel(mu),'-evaluation',10000, ...
        '-run',run,'-outputFcn',@(varargin)[]);
    G.Start();
    runtime = toc(t);
    Pop = G.result{end,2};
    Obj = Pop.objs;
    Dec = Pop.decs;
    [pfDec,pfObj] = first_front_dec_obj(Dec,Obj);
    save_run(runDir,Dec,Obj,pfDec,pfObj,runtime);
end

rebuild_summary(outRoot);
fprintf('Rebuilt summary at %s\n',outRoot);

function save_run(outDir,Dec,Obj,pfDec,pfObj,runtime)
    writematrix(Dec,fullfile(outDir,'population_dec.csv'));
    writematrix(Obj,fullfile(outDir,'population_obj.csv'));
    writematrix(pfDec,fullfile(outDir,'pf_dec.csv'));
    writematrix(pfObj,fullfile(outDir,'pf_obj.csv'));
    writetable(table(runtime,'VariableNames',{'runtime_sec'}),fullfile(outDir,'runtime.csv'));
end

function rebuild_summary(outRoot)
    rows = {};
    for K = [5 10]
        for methodCell = {'NSGAII','SPEA2'}
            method = methodCell{1};
            for run = 1:30
                runDir = fullfile(outRoot,sprintf('K_%02d',K),method,sprintf('run_%03d',run));
                pfObj = readmatrix(fullfile(runDir,'pf_obj.csv'));
                rt = readtable(fullfile(runDir,'runtime.csv'));
                rows(end+1,:) = {method,K,run,size(pfObj,1),rt.runtime_sec(1),mean(pfObj(:,1)),mean(-pfObj(:,2))}; %#ok<AGROW>
            end
        end
    end
    T = cell2table(rows,'VariableNames',{'method','K','run','pf_size','runtime_sec','mean_risk','mean_return'});
    writetable(T,fullfile(outRoot,'run_summary.csv'));
    S = groupsummary(T,{'method','K'},{'mean','std'},{'pf_size','runtime_sec','mean_risk','mean_return'});
    writetable(S,fullfile(outRoot,'summary_by_method_k.csv'));
    disp(S);
end

function [mu,Sigma] = load_orlibrary_portfile(filePath)
    txt = fileread(filePath);
    nums = sscanf(txt,'%f');
    idx = 1;
    n = round(nums(idx)); idx = idx + 1;
    mu = zeros(n,1); stdv = zeros(n,1);
    for i = 1:n
        mu(i) = nums(idx);
        stdv(i) = nums(idx+1);
        idx = idx + 2;
    end
    corr = eye(n);
    while idx + 2 <= numel(nums)
        i = round(nums(idx)); j = round(nums(idx+1)); rij = nums(idx+2);
        if i >= 1 && i <= n && j >= 1 && j <= n
            corr(i,j) = rij; corr(j,i) = rij;
        end
        idx = idx + 3;
    end
    Sigma = (stdv*stdv') .* corr;
    Sigma = 0.5*(Sigma+Sigma');
end

function [pfDec,pfObj] = first_front_dec_obj(Dec,Obj)
    n = size(Obj,1);
    dominated = false(n,1);
    for i = 1:n
        if dominated(i); continue; end
        for j = 1:n
            if i == j; continue; end
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
