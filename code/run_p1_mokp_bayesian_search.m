function run_p1_mokp_bayesian_search()
% Discrete Bayesian configuration search for ECMADE-MOO on P1 MOKP.

scriptDir = fileparts(mfilename('fullpath'));
cfg = defaultConfig(scriptDir);
cfg = applyOverrides(cfg);

P1MOKPConfigRunner.setupPaths(scriptDir,cfg.outRoot);
theta = P1MOKPConfigRunner.readL24Candidates(cfg.thetaPath,cfg.thetaSheet);
manifest = P1MOKPConfigRunner.defaultManifest();
configManifest = limitRows(manifest,cfg.configMaxInstances,cfg.configInstanceNames);
finalManifest = limitRows(manifest,cfg.finalMaxInstances,cfg.finalInstanceNames);

if ~exist(cfg.outRoot,'dir'); mkdir(cfg.outRoot); end
writetable(struct2table(theta),fullfile(cfg.outRoot,'l24_theta_candidates.csv'));
writetable(configManifest,fullfile(cfg.outRoot,'configuration_instances.csv'));
writetable(finalManifest,fullfile(cfg.outRoot,'final_test_instances.csv'));
writeProtocol(cfg,numel(theta),height(configManifest),height(finalManifest));

fprintf('P1 MOKP Bayesian configuration search\n');
fprintf('Config instances=%d, runs=%d, maxFE=%d, budget=%d\n',height(configManifest),cfg.configRuns,cfg.configMaxFE,cfg.budget);
fprintf('Final instances=%d, runs=%d, maxFE=%d\n',height(finalManifest),cfg.finalRuns,cfg.finalMaxFE);
fprintf('Output: %s\n',cfg.outRoot);

evalTable = runSearch(theta,configManifest,cfg,scriptDir);
writetable(evalTable,fullfile(cfg.outRoot,'bayesian_configuration_evaluations.csv'));
ranked = sortrows(evalTable,{'J','iteration'},{'descend','ascend'});
writetable(ranked(1,:),fullfile(cfg.outRoot,'bayesian_selected_theta.csv'));

bestIndex = ranked.theta_index(1);
bestTheta = theta(bestIndex);
fprintf('Selected theta: %s, J=%.8g\n',bestTheta.source_theta_id,ranked.J(1));

finalRoot = fullfile(cfg.outRoot,'final_test');
finalCfg = runnerConfig(scriptDir,cfg.method,finalRoot,cfg.finalRuns,cfg.N,cfg.finalMaxFE,cfg.forceRerun);
assignments = makeAssignments(finalManifest,bestTheta,bestIndex,ranked.J(1));
writetable(assignments,fullfile(cfg.outRoot,'bayesian_final_assignment.csv'));
P1MOKPConfigRunner.runRows(assignments,finalCfg);
P1MOKPConfigRunner.rebuildSummary(finalRoot,cfg.method);

fprintf('Done. Final outputs: %s\n',finalRoot);
end

function cfg = defaultConfig(scriptDir)
cfg = struct();
cfg.method = 'BayesianConfig_ECMADE_MOO';
cfg.thetaPath = P1MOKPConfigRunner.defaultThetaPath();
cfg.thetaSheet = 'L24_Theta_Config';
cfg.outRoot = fullfile(scriptDir,'p0_lite_outputs',['p1_mokp_bayesian_config_' datestr(now,'yyyymmdd_HHMMSS')]);
cfg.configRuns = 3;
cfg.finalRuns = 30;
cfg.N = 100;
cfg.configMaxFE = 5000;
cfg.finalMaxFE = 10000;
cfg.configMaxInstances = 8;
cfg.finalMaxInstances = inf;
cfg.configInstanceNames = {};
cfg.finalInstanceNames = {};
cfg.budget = 12;
cfg.initialPoints = 5;
cfg.seed = 20260719;
cfg.forceRerun = false;
cfg.feasibleBonus = 0.01;
cfg.pfSizeWeight = 1e-4;
cfg.runtimePenalty = 1e-4;
end

function cfg = applyOverrides(cfg)
names = {'OUT_ROOT','CONFIG_RUNS','FINAL_RUNS','N','CONFIG_MAXFE','FINAL_MAXFE', ...
    'CONFIG_MAX_INSTANCES','FINAL_MAX_INSTANCES','CONFIG_INSTANCE_NAMES', ...
    'FINAL_INSTANCE_NAMES','BUDGET','INITIAL_POINTS','SEED','FORCE_RERUN'};
fields = {'outRoot','configRuns','finalRuns','N','configMaxFE','finalMaxFE', ...
    'configMaxInstances','finalMaxInstances','configInstanceNames', ...
    'finalInstanceNames','budget','initialPoints','seed','forceRerun'};
for i = 1:numel(names)
    varName = ['P1_MOKP_BAYES_' names{i}];
    if evalin('base',sprintf('exist(''%s'',''var'')',varName))
        cfg.(fields{i}) = evalin('base',varName);
    end
end
end

function evalTable = runSearch(theta,manifest,cfg,scriptDir)
budget = min(cfg.budget,numel(theta));
initialPoints = min(cfg.initialPoints,budget);
rng(cfg.seed,'twister');
order = randperm(numel(theta));
observed = [];
rows = {};
configRoot = fullfile(cfg.outRoot,'configuration');

for iteration = 1:budget
    if iteration <= initialPoints
        thetaIndex = order(iteration);
        acquisition = 'initial_random';
        acquisitionValue = NaN;
    else
        [thetaIndex,acquisitionValue] = proposeExpectedImprovement(theta,observed);
        acquisition = 'expected_improvement';
    end
    thetaCfg = theta(thetaIndex);
    method = ['BayesEval_' thetaCfg.source_theta_id];
    fprintf('BO iteration %02d/%02d: %s (%s)\n',iteration,budget,thetaCfg.source_theta_id,acquisition);

    runCfg = runnerConfig(scriptDir,method,configRoot,cfg.configRuns,cfg.N,cfg.configMaxFE,cfg.forceRerun);
    assignments = makeAssignments(manifest,thetaCfg,thetaIndex,NaN);
    P1MOKPConfigRunner.runRows(assignments,runCfg);
    stats = scoreTheta(configRoot,manifest,method,cfg.configRuns,cfg);

    observed(end+1,:) = [thetaIndex,stats.J]; %#ok<AGROW>
    rows(end+1,:) = {iteration,thetaIndex,thetaCfg.source_theta_id,acquisition,acquisitionValue, ...
        stats.J,stats.mean_loss_fraction,stats.mean_pf_size,stats.mean_runtime_sec, ...
        stats.mean_pf_feasible_rate,stats.completed_runs,thetaCfg.subpops, ...
        thetaCfg.source_operator,thetaCfg.source_migration,thetaCfg.eliteRatio, ...
        thetaCfg.stagnationThreshold}; %#ok<AGROW>
end

evalTable = cell2table(rows,'VariableNames',{'iteration','theta_index','theta_id', ...
    'acquisition','acquisition_value','J','mean_loss_fraction','mean_pf_size', ...
    'mean_runtime_sec','mean_pf_feasible_rate','completed_runs','S','operator', ...
    'migration','elite_ratio','stagnation_threshold'});
end

function cfg = runnerConfig(scriptDir,method,outRoot,runs,N,maxFE,forceRerun)
cfg = P1MOKPConfigRunner.baseConfig(scriptDir,method,outRoot);
cfg.runs = runs;
cfg.N = N;
cfg.maxFE = maxFE;
cfg.saveGenerations = max(1,maxFE / N);
cfg.forceRerun = forceRerun;
end

function assignments = makeAssignments(manifest,thetaCfg,thetaIndex,predictedScore)
rows = {};
for ii = 1:height(manifest)
    rows(end+1,:) = P1MOKPConfigRunner.assignmentRow(manifest(ii,:),thetaCfg,thetaIndex,predictedScore); %#ok<AGROW>
end
assignments = cell2table(rows,'VariableNames',P1MOKPConfigRunner.assignmentColumns());
end

function stats = scoreTheta(root,manifest,method,runs,cfg)
losses = [];
pfSizes = [];
runtimes = [];
feasibleRates = [];
for ii = 1:height(manifest)
    row = manifest(ii,:);
    totalProfit = P1KnapsackRunner.totalProfit(row);
    for run = 1:runs
        runDir = fullfile(root,P1MOKPConfigRunner.cellValue(row.split), ...
            P1MOKPConfigRunner.cellValue(row.instance),method,sprintf('run_%03d',run));
        pfFile = fullfile(runDir,'pf_obj.csv');
        rtFile = fullfile(runDir,'runtime.csv');
        if ~exist(pfFile,'file') || ~exist(rtFile,'file')
            continue;
        end
        pfObj = readmatrix(pfFile);
        rt = readtable(rtFile);
        losses(end+1,1) = mean(pfObj ./ totalProfit,'all'); %#ok<AGROW>
        pfSizes(end+1,1) = size(pfObj,1); %#ok<AGROW>
        runtimes(end+1,1) = rt.runtime_sec(1); %#ok<AGROW>
        feasibleRates(end+1,1) = readFeasibleRate(runDir); %#ok<AGROW>
    end
end
stats = struct();
stats.completed_runs = numel(losses);
stats.mean_loss_fraction = nanmeanLocal(losses);
stats.mean_pf_size = nanmeanLocal(pfSizes);
stats.mean_runtime_sec = nanmeanLocal(runtimes);
stats.mean_pf_feasible_rate = nanmeanLocal(feasibleRates);
stats.J = -stats.mean_loss_fraction ...
    + cfg.feasibleBonus * stats.mean_pf_feasible_rate ...
    + cfg.pfSizeWeight * log1p(stats.mean_pf_size) ...
    - cfg.runtimePenalty * stats.mean_runtime_sec;
end

function value = readFeasibleRate(runDir)
value = NaN;
path = fullfile(runDir,'feasible_rate.csv');
if exist(path,'file')
    T = readtable(path);
    value = T.PF_Feasible_Rate(1);
end
end

function [thetaIndex,eiValue] = proposeExpectedImprovement(theta,observed)
observedIdx = observed(:,1);
y = observed(:,2);
remaining = setdiff((1:numel(theta))',observedIdx,'stable');
if isempty(remaining)
    thetaIndex = observedIdx(end);
    eiValue = 0;
    return;
end
if numel(y) < 2 || std(y) < 1e-12
    thetaIndex = remaining(1);
    eiValue = 0;
    return;
end
X = thetaFeatures(theta,observedIdx);
Xstar = thetaFeatures(theta,remaining);
yn = (y - mean(y)) / std(y);
ell = 1.25;
K = rbfKernel(X,X,ell) + 1e-6*eye(size(X,1));
Ks = rbfKernel(X,Xstar,ell);
alpha = K \ yn;
mu = Ks' * alpha;
v = K \ Ks;
sigma2 = max(1 - sum(Ks .* v,1)',1e-12);
sigma = sqrt(sigma2);
bestY = max(yn);
z = (mu - bestY) ./ sigma;
ei = (mu - bestY) .* normalCdf(z) + sigma .* normalPdf(z);
[eiValue,pos] = max(ei);
thetaIndex = remaining(pos);
end

function X = thetaFeatures(theta,indices)
X = zeros(numel(indices),5);
for r = 1:numel(indices)
    c = theta(indices(r));
    X(r,:) = [c.subpops/8,operatorLevel(c.source_operator), ...
        migrationLevel(c.source_migration),c.eliteRatio,c.stagnationThreshold/50];
end
end

function value = operatorLevel(op)
if strcmp(op,'DE/rand'); value = 1;
elseif strcmp(op,'DE/best'); value = 2;
else; value = 3; end
end

function value = migrationLevel(mig)
if strcmp(mig,'none'); value = 1;
elseif strcmp(mig,'fixed'); value = 2;
else; value = 3; end
end

function K = rbfKernel(A,B,ell)
D = zeros(size(A,1),size(B,1));
for j = 1:size(A,2)
    D = D + (A(:,j) - B(:,j)').^2;
end
K = exp(-0.5 * D / (ell^2));
end

function y = normalPdf(x)
y = exp(-0.5*x.^2) / sqrt(2*pi);
end

function y = normalCdf(x)
y = 0.5 * (1 + erf(x ./ sqrt(2)));
end

function rows = limitRows(rows,maxRows,names)
names = P1MOKPConfigRunner.asCellstr(names);
if ~isempty(names)
    mask = false(height(rows),1);
    for i = 1:numel(names)
        mask = mask | strcmp(rows.instance,names{i});
    end
    rows = rows(mask,:);
end
if isfinite(maxRows)
    rows = rows(1:min(height(rows),maxRows),:);
end
end

function value = nanmeanLocal(x)
x = x(~isnan(x));
if isempty(x); value = NaN; else; value = mean(x); end
end

function writeProtocol(cfg,nTheta,nConfig,nFinal)
fid = fopen(fullfile(cfg.outRoot,'bayesian_configuration_protocol.txt'),'w');
fprintf(fid,'purpose=P1 MOKP Bayesian configuration search for ECMADE-MOO\n');
fprintf(fid,'theta_candidates=%d\n',nTheta);
fprintf(fid,'optimizer=discrete Gaussian-process surrogate with expected improvement\n');
fprintf(fid,'seed=%d\n',cfg.seed);
fprintf(fid,'config_instances=%d\n',nConfig);
fprintf(fid,'config_runs=%d\n',cfg.configRuns);
fprintf(fid,'config_maxFE=%d\n',cfg.configMaxFE);
fprintf(fid,'budget=%d\n',cfg.budget);
fprintf(fid,'initial_random_points=%d\n',cfg.initialPoints);
fprintf(fid,'score=-mean_loss_fraction + feasibleBonus*feasibleRate + pfSizeWeight*log1p(pfSize) - runtimePenalty*runtime\n');
fprintf(fid,'final_instances=%d\n',nFinal);
fprintf(fid,'final_runs=%d\n',cfg.finalRuns);
fprintf(fid,'final_maxFE=%d\n',cfg.finalMaxFE);
fclose(fid);
end
