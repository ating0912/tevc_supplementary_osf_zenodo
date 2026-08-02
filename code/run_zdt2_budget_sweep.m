% Quick ZDT2 budget sweep for NSGA-II reproduction checks.

clear; clc;

N = 100;
M = 2;
D = 30;
Runs = 10;
targetIGD = 0.50813;
maxFEs = [200 300 500 800 1000 1500 2000 3000 5000 8000 10000];

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir, 'PlatEMO', 'PlatEMO');
outRoot = fullfile(scriptDir, 'nsga2_outputs', 'zdt2_budget_sweep');

if ~exist(outRoot, 'dir')
    mkdir(outRoot);
end

addpath(genpath(platemoRoot));

configs = {
    'platemo_proM_over_D', @NSGAII;
    'paper_style_proM', @NSGAII_PaperMutation;
};

PFX = linspace(0, 1, 10000)';
PF = [PFX, 1 - PFX.^2];
summary = cell(numel(maxFEs)*size(configs,1), 7);
row = 0;

for c = 1 : size(configs,1)
    configName = configs{c,1};
    algorithmFcn = configs{c,2};
    for b = 1 : numel(maxFEs)
        maxFE = maxFEs(b);
        values = zeros(Runs, 1);
        fprintf('\n=== %s maxFE=%d ===\n', configName, maxFE);
        for run = 1 : Runs
            rng(run);
            [~,Obj,~] = platemo( ...
                'algorithm', algorithmFcn, ...
                'problem', @ZDT2, ...
                'N', N, ...
                'M', M, ...
                'D', D, ...
                'maxFE', maxFE, ...
                'run', run);
            values(run) = MatrixIGD(Obj, PF);
            fprintf('%s maxFE=%d run=%02d IGD=%.12g\n', configName, maxFE, run, values(run));
        end
        row = row + 1;
        summary(row,:) = {configName, maxFE, Runs, mean(values), std(values), ...
            abs(mean(values)-targetIGD), sprintf('%.12g; ', values)};
    end
end

summaryTable = cell2table(summary, 'VariableNames', ...
    {'config','maxFE','runs','mean_igd','sample_std','abs_diff_to_paper','run_values'});
writetable(summaryTable, fullfile(outRoot, 'zdt2_budget_sweep_summary.csv'));
disp(sortrows(summaryTable, 'abs_diff_to_paper'));

function score = MatrixIGD(PopObj, PF)
    minDistances = inf(size(PF,1), 1);
    for i = 1 : size(PopObj,1)
        diff = PF - PopObj(i,:);
        distances = sqrt(sum(diff.*diff, 2));
        minDistances = min(minDistances, distances);
    end
    score = mean(minDistances);
end
