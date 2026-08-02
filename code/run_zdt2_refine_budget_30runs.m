% Refined 30-run ZDT2 budget sweep around the paper NSGA-II IGD value.

clear; clc;

N = 100;
M = 2;
D = 30;
Runs = 30;
targetIGD = 0.50813;
maxFEs = [3500 4000 4500 5000];

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir, 'PlatEMO', 'PlatEMO');
outRoot = fullfile(scriptDir, 'nsga2_outputs', 'zdt2_refine_budget_30runs');

if ~exist(outRoot, 'dir')
    mkdir(outRoot);
end

addpath(genpath(platemoRoot));

PFX = linspace(0, 1, 10000)';
PF = [PFX, 1 - PFX.^2];

summary = cell(numel(maxFEs), 7);

for b = 1 : numel(maxFEs)
    maxFE = maxFEs(b);
    values = zeros(Runs, 1);
    fprintf('\n=== paper_style_proM maxFE=%d ===\n', maxFE);
    for run = 1 : Runs
        rng(run);
        evalc("[~,Obj,~] = platemo('algorithm', @NSGAII_PaperMutation, 'problem', @ZDT2, 'N', N, 'M', M, 'D', D, 'maxFE', maxFE, 'run', run);");
        values(run) = MatrixIGD(Obj, PF);
        fprintf('maxFE=%d run=%02d IGD=%.12g\n', maxFE, run, values(run));
    end

    perRunTable = table((1:Runs)', values, 'VariableNames', {'run','igd'});
    writetable(perRunTable, fullfile(outRoot, sprintf('paper_style_maxFE_%05d_runs.csv', maxFE)));

    summary(b,:) = {'paper_style_proM', maxFE, Runs, mean(values), std(values), ...
        abs(mean(values)-targetIGD), sprintf('%.12g; ', values)};
end

summaryTable = cell2table(summary, 'VariableNames', ...
    {'config','maxFE','runs','mean_igd','sample_std','abs_diff_to_paper','run_values'});
writetable(summaryTable, fullfile(outRoot, 'zdt2_refine_budget_30runs_summary.csv'));
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
