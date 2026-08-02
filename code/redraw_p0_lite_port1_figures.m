% Redraw P0-lite figures from existing logged outputs.
% This does not rerun algorithms or recompute per-generation metrics.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
outRoot = fullfile(scriptDir,'p0_lite_outputs','port1_nsga2_spea2_logged');
metricsDir = fullfile(outRoot,'postprocess_metrics');
methods = {'NSGAII','SPEA2','MOEAD','GDE3','ECMADE_MOO'};
KValues = [5 10 15 20 25 30];

for ki = 1:numel(KValues)
    K = KValues(ki);
    refObj = readmatrix(fullfile(metricsDir,sprintf('reference_pf_K_%02d.csv',K)));
    makeOverlayFigure(outRoot,metricsDir,methods,K,refObj);
    makeHeatmapFigure(outRoot,metricsDir,methods,K);
    makeEafFigure(metricsDir,methods,K);
end

fprintf('Redrawn figures: %s\n',metricsDir);

function makeOverlayFigure(outRoot,metricsDir,methods,K,refObj)
fig = figure('Visible','off','Color','w','Position',[100 100 900 620]);
colors = methodColors(numel(methods));
markers = {'o','^','s','d','v','p','h'};
handles = gobjects(1,numel(methods)+1);
hold on;
for mi = 1:numel(methods)
    allObj = loadAllPf(outRoot,methods{mi},K);
    handles(mi) = scatter(allObj(:,1),-allObj(:,2),18,colors(mi,:),markers{mi}, ...
        'filled','MarkerFaceAlpha',0.34,'MarkerEdgeAlpha',0.34);
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

function makeHeatmapFigure(outRoot,metricsDir,methods,K)
fig = figure('Visible','off','Color','w','Position',[100 100 max(980,420*numel(methods)) 430]);
colors = methodColors(numel(methods));
for mi = 1:numel(methods)
    subplot(1,numel(methods),mi);
    allObj = loadAllPf(outRoot,methods{mi},K);
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

function makeEafFigure(metricsDir,methods,K)
fig = figure('Visible','off','Color','w','Position',[100 100 900 620]);
colors = methodColors(numel(methods));
handles = gobjects(1,numel(methods));
hold on;
for mi = 1:numel(methods)
    curveFile = fullfile(metricsDir,sprintf('eaf_curve_%s_K_%02d.csv',methods{mi},K));
    T = readtable(curveFile);
    x = T.risk_grid_norm;
    q25 = T.q25_obj2_norm;
    q50 = T.median_obj2_norm;
    q75 = T.q75_obj2_norm;
    fill([x;flipud(x)],[q25;flipud(q75)],colors(mi,:), ...
        'FaceAlpha',0.18,'EdgeColor','none');
    handles(mi) = plot(x,q50,'Color',colors(mi,:),'LineWidth',2.2);
end
xlabel('Normalized risk');
ylabel('Normalized objective 2 (-return)');
title(sprintf('EAF Band, port1, K=%d',K));
legend(handles,methods,'Location','best');
grid on; box on;
saveFigure(fig,metricsDir,sprintf('eaf_band_K_%02d',K));
close(fig);
end

function allObj = loadAllPf(outRoot,method,K)
allObj = [];
for run = 1:30
    pfFile = fullfile(outRoot,sprintf('K_%02d',K),method,sprintf('run_%03d',run),'pf_obj.csv');
    allObj = [allObj; readmatrix(pfFile)]; %#ok<AGROW>
end
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
