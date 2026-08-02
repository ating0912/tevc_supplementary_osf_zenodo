% P0-lite SPEA2 only: OR-Library port1, K={5,10,15,20,25,30}, 30 runs.

if evalin('base','exist(''P0_LITE_SMOKE'',''var'')')
    p0LiteSmoke = evalin('base','P0_LITE_SMOKE');
else
    p0LiteSmoke = false;
end
clearvars -except p0LiteSmoke; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');
outRoot = fullfile(scriptDir,'p0_lite_outputs','port1_nsga2_spea2_logged');
if p0LiteSmoke
    outRoot = fullfile(scriptDir,'p0_lite_outputs','smoke_port1_spea2_only');
end
if ~exist(outRoot,'dir'); mkdir(outRoot); end

restoredefaultpath;
addpath(genpath(platemoRoot));
addpath(scriptDir);

cfg = P0LiteUtils.baseConfig(scriptDir,p0LiteSmoke);
[mu,~] = P0LiteUtils.loadORLibraryPortfile(cfg.dataPath);
P0LiteUtils.writeConfig(outRoot,cfg,numel(mu),'SPEA2');

for kk = 1:numel(cfg.KValues)
    K = cfg.KValues(kk);
    fprintf('=== SPEA2 K=%d ===\n',K);
    for run = 1:cfg.runs
        fprintf('SPEA2 K=%d Run %03d/%03d\n',K,run,cfg.runs);
        runDir = fullfile(outRoot,sprintf('K_%02d',K),'SPEA2',sprintf('run_%03d',run));
        if exist(fullfile(runDir,'pf_obj.csv'),'file') && ...
                exist(fullfile(runDir,'runtime.csv'),'file') && ...
                exist(fullfile(runDir,'generation_pf_points.csv'),'file') && ...
                exist(fullfile(runDir,'generation_population_log.csv'),'file')
            continue;
        end
        if ~exist(runDir,'dir'); mkdir(runDir); end

        t = tic;
        rng(run,cfg.rngType);
        G = GLOBAL('-algorithm',@SPEA2,'-problem',{@PortfolioORLIB,cfg.dataPath,K}, ...
            '-N',cfg.N,'-M',2,'-D',numel(mu),'-evaluation',cfg.maxFE, ...
            '-run',run,'-save',cfg.saveGenerations,'-outputFcn',@(varargin)[]);
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

P0LiteUtils.rebuildSummary(outRoot,{'NSGAII','SPEA2','MOEAD','GDE3','ECMADE_MOO'});
fprintf('SPEA2 outputs: %s\n',outRoot);
