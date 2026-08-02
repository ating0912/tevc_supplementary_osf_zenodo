% Postprocess P0-lite port1 results.
% Reads existing PF/runtime files and writes metrics plus PF figures.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
outRoot = fullfile(scriptDir,'p0_lite_outputs','port1_nsga2_spea2_logged');
metricsDir = fullfile(outRoot,'postprocess_metrics');
if ~exist(metricsDir,'dir')
    mkdir(metricsDir);
end

methods = {'NSGAII','SPEA2','MOEAD','GDE3','ECMADE_MOO'};
KValues = [5 10 15 20 25 30];
runs = 30;
epsilonOverlap = 0.03;
tol = 1e-8;

allRows = {};
eafRows = {};
generationLog = table();

for ki = 1:numel(KValues)
    K = KValues(ki);
    runData = loadRunData(outRoot,methods,K,runs);
    if isempty(runData)
        warning('No data found for K=%d',K);
        continue;
    end

    allObj = vertcat(runData.obj);
    refObj = firstFront(allObj);
    refObj = sortrows(refObj,1);
    writematrix(refObj,fullfile(metricsDir,sprintf('reference_pf_K_%02d.csv',K)));

    fmin = min(allObj,[],1);
    fmax = max(allObj,[],1);
    scale = max(fmax-fmin,eps);
    refNorm = normalizeObj(refObj,fmin,scale);

    for i = 1:numel(runData)
        obj = runData(i).obj;
        dec = runData(i).dec;
        popDec = runData(i).popDec;
        normObj = normalizeObj(obj,fmin,scale);
        normObj = firstFront(normObj);

        hv = hv2d(normObj,[1.1 1.1]);
        igd = mean(minDistances(refNorm,normObj));
        overlap = mean(minDistances(refNorm,normObj) <= epsilonOverlap);
        [diversityExtent,spacingStd] = diversityMetrics(normObj);
        pfFeasibleRate = feasibleRate(dec,K,tol);
        popFeasibleRate = feasibleRate(popDec,K,tol);

        allRows(end+1,:) = {runData(i).method,K,runData(i).run,size(obj,1), ...
            runData(i).runtime,hv,igd,overlap,diversityExtent,spacingStd, ...
            pfFeasibleRate,popFeasibleRate,mean(obj(:,1)),mean(-obj(:,2))}; %#ok<SAGROW>

        genT = generationMetrics(runData(i),K,fmin,scale,refNorm);
        if ~isempty(genT)
            writetable(genT,fullfile(runData(i).runDir,'generation_log.csv'));
            generationLog = [generationLog; genT]; %#ok<AGROW>
        end
    end

    for mi = 1:numel(methods)
        method = methods{mi};
        idx = strcmp({runData.method},method);
        methodData = runData(idx);
        if isempty(methodData)
            continue;
        end
        [bandWidth,gridX,q25,q50,q75] = eafBandWidth(methodData,fmin,scale);
        eafRows(end+1,:) = {method,K,bandWidth,nnz(~isnan(q50)),numel(gridX)}; %#ok<SAGROW>
        eafTable = table(gridX(:),q25(:),q50(:),q75(:), ...
            'VariableNames',{'risk_grid_norm','q25_obj2_norm','median_obj2_norm','q75_obj2_norm'});
        writetable(eafTable,fullfile(metricsDir,sprintf('eaf_curve_%s_K_%02d.csv',method,K)));
    end

    makeOverlayFigure(metricsDir,runData,methods,K,refObj);
    makeHeatmapFigure(metricsDir,runData,methods,K);
    makeEafFigure(metricsDir,runData,methods,K,fmin,scale);
end

metrics = cell2table(allRows,'VariableNames',{'method','K','run','pf_size', ...
    'runtime_sec','HV','IGD','PF_Overlap','Diversity','SpacingStd', ...
    'PF_Feasible_Rate','Population_Feasible_Rate','mean_risk','mean_return'});
writetable(metrics,fullfile(metricsDir,'run_metrics.csv'));

summary = summarizeMetrics(metrics);
writetable(summary,fullfile(metricsDir,'summary_metrics_by_method_k.csv'));

eafSummary = cell2table(eafRows,'VariableNames',{'method','K','EAF_Band_Width','valid_grid_points','total_grid_points'});
writetable(eafSummary,fullfile(metricsDir,'eaf_band_width.csv'));

if ~isempty(generationLog)
    writetable(generationLog,fullfile(metricsDir,'generation_log.csv'));
    genSummary = groupsummary(generationLog,{'method','K','generation'},{'mean','std'}, ...
        {'HV','IGD','feasible_rate','pf_size'});
    writetable(genSummary,fullfile(metricsDir,'generation_summary_by_method_k.csv'));
end

disp(summary);
disp(eafSummary);
fprintf('Postprocess outputs: %s\n',metricsDir);

function runData = loadRunData(outRoot,methods,K,runs)
runData = struct('method',{},'run',{},'runDir',{},'obj',{},'dec',{},'popDec',{},'runtime',{});
for mi = 1:numel(methods)
    method = methods{mi};
    for run = 1:runs
        runDir = fullfile(outRoot,sprintf('K_%02d',K),method,sprintf('run_%03d',run));
        objFile = fullfile(runDir,'pf_obj.csv');
        decFile = fullfile(runDir,'pf_dec.csv');
        popDecFile = fullfile(runDir,'population_dec.csv');
        rtFile = fullfile(runDir,'runtime.csv');
        if ~exist(objFile,'file') || ~exist(decFile,'file') || ~exist(popDecFile,'file') || ~exist(rtFile,'file')
            continue;
        end
        rt = readtable(rtFile);
        item.method = method;
        item.run = run;
        item.runDir = runDir;
        item.obj = ensureTwoColumn(readmatrix(objFile));
        item.dec = readmatrix(decFile);
        item.popDec = readmatrix(popDecFile);
        item.runtime = rt.runtime_sec(1);
        runData(end+1) = item; %#ok<AGROW>
    end
end
end

function T = generationMetrics(item,K,fmin,scale,refNorm)
pfFile = fullfile(item.runDir,'generation_pf_points.csv');
popFile = fullfile(item.runDir,'generation_population_log.csv');
if ~exist(pfFile,'file') || ~exist(popFile,'file')
    T = table();
    return;
end
pf = readtable(pfFile);
pop = readtable(popFile);
rows = {};
for i = 1:height(pop)
    generation = pop.generation(i);
    idx = pf.generation == generation;
    if any(idx)
        F = [pf.risk(idx),pf.minus_return(idx)];
        F = normalizeObj(F,fmin,scale);
        F = firstFront(F);
        hv = hv2d(F,[1.1 1.1]);
        igd = mean(minDistances(refNorm,F));
    else
        hv = 0;
        igd = NaN;
    end
    rows(end+1,:) = {item.method,K,item.run,generation,pop.evaluations(i), ...
        hv,igd,pop.feasible_rate(i),pop.pf_size(i)}; %#ok<AGROW>
end
T = cell2table(rows,'VariableNames',{'method','K','run','generation','evaluations', ...
    'HV','IGD','feasible_rate','pf_size'});
end

function X = ensureTwoColumn(X)
if size(X,2) ~= 2 && size(X,1) == 2
    X = X';
end
end

function F = normalizeObj(F,fmin,scale)
F = (F - fmin) ./ scale;
F = max(min(F,1),0);
end

function front = firstFront(F)
if isempty(F)
    front = F;
    return;
end
F = unique(F,'rows','stable');
n = size(F,1);
dominated = false(n,1);
for i = 1:n
    if dominated(i)
        continue;
    end
    for j = 1:n
        if i == j
            continue;
        end
        if all(F(j,:) <= F(i,:)) && any(F(j,:) < F(i,:))
            dominated(i) = true;
            break;
        end
    end
end
front = sortrows(F(~dominated,:),1);
end

function hv = hv2d(F,ref)
F = firstFront(F);
F = F(all(F < ref,2),:);
if isempty(F)
    hv = 0;
    return;
end
F = sortrows(F,1);
hv = 0;
for i = 1:size(F,1)
    if i < size(F,1)
        width = max(F(i+1,1) - F(i,1),0);
    else
        width = max(ref(1) - F(i,1),0);
    end
    height = max(ref(2) - F(i,2),0);
    hv = hv + width*height;
end
end

function d = minDistances(A,B)
if isempty(A) || isempty(B)
    d = inf(size(A,1),1);
    return;
end
d = inf(size(A,1),1);
for i = 1:size(A,1)
    diff = B - A(i,:);
    d(i) = sqrt(min(sum(diff.^2,2)));
end
end

function [extent,spacingStd] = diversityMetrics(F)
if isempty(F)
    extent = NaN;
    spacingStd = NaN;
    return;
end
extent = norm(max(F,[],1)-min(F,[],1));
if size(F,1) < 3
    spacingStd = 0;
    return;
end
F = sortrows(F,1);
gap = sqrt(sum(diff(F,1,1).^2,2));
spacingStd = std(gap);
end

function rate = feasibleRate(Dec,K,tol)
if isempty(Dec)
    rate = NaN;
    return;
end
card = sum(Dec > tol,2);
sumOk = abs(sum(Dec,2)-1) <= 1e-6;
boundsOk = all(Dec >= -tol,2) & all(Dec <= 1+tol,2);
rate = mean(card <= K & sumOk & boundsOk);
end

function [bandWidth,gridX,q25,q50,q75] = eafBandWidth(methodData,fmin,scale)
gridX = linspace(0,1,101);
curves = nan(numel(methodData),numel(gridX));
for i = 1:numel(methodData)
    F = normalizeObj(methodData(i).obj,fmin,scale);
    F = firstFront(F);
    for gi = 1:numel(gridX)
        eligible = F(F(:,1) <= gridX(gi),2);
        if ~isempty(eligible)
            curves(i,gi) = min(eligible);
        end
    end
end
q25 = rowQuantile(curves,0.25);
q50 = rowQuantile(curves,0.50);
q75 = rowQuantile(curves,0.75);
width = q75 - q25;
bandWidth = mean(width(~isnan(width)));
end

function q = rowQuantile(X,p)
q = nan(1,size(X,2));
for j = 1:size(X,2)
    v = sort(X(~isnan(X(:,j)),j));
    if isempty(v)
        continue;
    end
    pos = 1 + (numel(v)-1)*p;
    lo = floor(pos);
    hi = ceil(pos);
    if lo == hi
        q(j) = v(lo);
    else
        q(j) = v(lo) + (v(hi)-v(lo))*(pos-lo);
    end
end
end

function T = summarizeMetrics(metrics)
vars = {'pf_size','runtime_sec','HV','IGD','PF_Overlap','Diversity','SpacingStd', ...
    'PF_Feasible_Rate','Population_Feasible_Rate','mean_risk','mean_return'};
rows = {};
methods = unique(metrics.method,'stable');
KValues = unique(metrics.K,'stable');
for mi = 1:numel(methods)
    for ki = 1:numel(KValues)
        idx = strcmp(metrics.method,methods{mi}) & metrics.K == KValues(ki);
        if ~any(idx)
            continue;
        end
        row = {methods{mi},KValues(ki),sum(idx)};
        for vi = 1:numel(vars)
            x = metrics{idx,vars{vi}};
            row = [row,{mean(x,'omitnan'),std(x,'omitnan')}]; %#ok<AGROW>
        end
        rows(end+1,:) = row; %#ok<AGROW>
    end
end
names = {'method','K','runs'};
for vi = 1:numel(vars)
    names{end+1} = ['mean_' vars{vi}]; %#ok<AGROW>
    names{end+1} = ['std_' vars{vi}]; %#ok<AGROW>
end
T = cell2table(rows,'VariableNames',names);
end

function makeOverlayFigure(metricsDir,runData,methods,K,refObj)
fig = figure('Visible','off','Color','w','Position',[100 100 900 620]);
colors = methodColors(numel(methods));
markers = {'o','^','s','d','v','p','h'};
hold on;
handles = gobjects(1,numel(methods)+1);
for mi = 1:numel(methods)
    method = methods{mi};
    idx = strcmp({runData.method},method);
    allObj = vertcat(runData(idx).obj);
    if ~isempty(allObj)
        handles(mi) = scatter(allObj(:,1),-allObj(:,2),18,colors(mi,:),markers{mi}, ...
            'filled','MarkerFaceAlpha',0.34,'MarkerEdgeAlpha',0.34);
    end
end
handles(end) = plot(refObj(:,1),-refObj(:,2),'k-','LineWidth',2.2);
xlabel('Risk');
ylabel('Return');
title(sprintf('PF Overlay, port1, K=%d',K));
legend(handles,[methods,{'Empirical reference PF'}],'Location','best');
grid on; box on;
saveFigure(fig,metricsDir,sprintf('pf_overlay_K_%02d',K));
close(fig);
end

function makeHeatmapFigure(metricsDir,runData,methods,K)
fig = figure('Visible','off','Color','w','Position',[100 100 max(980,420*numel(methods)) 430]);
colors = methodColors(numel(methods));
for mi = 1:numel(methods)
    subplot(1,numel(methods),mi);
    idx = strcmp({runData.method},methods{mi});
    allObj = vertcat(runData(idx).obj);
    x = allObj(:,1);
    y = -allObj(:,2);
    xb = linspace(min(x),max(x),45);
    yb = linspace(min(y),max(y),45);
    counts = histcounts2(x,y,xb,yb);
    imagesc(xb,yb,counts');
    set(gca,'YDir','normal');
    xlabel('Risk');
    ylabel('Return');
    title(sprintf('%s, K=%d',methods{mi},K));
    colorbar;
    colormap(gca,methodColormap(colors(mi,:)));
    grid on; box on;
end
saveFigure(fig,metricsDir,sprintf('pf_heatmap_K_%02d',K));
close(fig);
end

function makeEafFigure(metricsDir,runData,methods,K,fmin,scale)
fig = figure('Visible','off','Color','w','Position',[100 100 900 620]);
colors = methodColors(numel(methods));
hold on;
handles = gobjects(1,numel(methods));
for mi = 1:numel(methods)
    idx = strcmp({runData.method},methods{mi});
    methodData = runData(idx);
    if isempty(methodData)
        continue;
    end
    [~,gridX,q25,q50,q75] = eafBandWidth(methodData,fmin,scale);
    fill([gridX fliplr(gridX)],[q25 fliplr(q75)],colors(mi,:), ...
        'FaceAlpha',0.18,'EdgeColor','none');
    handles(mi) = plot(gridX,q50,'Color',colors(mi,:),'LineWidth',2.2);
end
xlabel('Normalized risk');
ylabel('Normalized objective 2 (-return)');
title(sprintf('EAF Band, port1, K=%d',K));
legend(handles,methods,'Location','best');
grid on; box on;
saveFigure(fig,metricsDir,sprintf('eaf_band_K_%02d',K));
close(fig);
end

function colors = methodColors(n)
base = [0.0000 0.2784 0.6706;   % blue
        0.8353 0.2431 0.0196;   % orange-red
        0.0000 0.4980 0.0000;   % green
        0.4941 0.1843 0.5569;   % purple
        0.0000 0.5804 0.6500];  % teal
colors = base(1:n,:);
end

function cmap = methodColormap(color)
white = [1 1 1];
dark = max(color*0.55,0);
mid = color;
light = 0.75*white + 0.25*color;
x = [0;0.35;0.75;1];
c = [white;light;mid;dark];
xi = linspace(0,1,256)';
cmap = [interp1(x,c(:,1),xi),interp1(x,c(:,2),xi),interp1(x,c(:,3),xi)];
end

function saveFigure(fig,outDir,baseName)
pngFile = fullfile(outDir,[baseName '.png']);
svgFile = fullfile(outDir,[baseName '.svg']);
print(fig,pngFile,'-dpng','-r220');
print(fig,svgFile,'-dsvg');
end
