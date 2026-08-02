% Run the algorithm-level diagnostics that cannot be derived from saved
% populations. Each case is resumable and uses the common 10000-point PF.

clear; clc;

scriptDir = fileparts(mfilename('fullpath'));
platemoRoot = fullfile(scriptDir,'PlatEMO_v2.9.0','PlatEMO');
compatRoot = fullfile(scriptDir,'platemo_v43_compat');
outputRoot = fullfile(scriptDir,'nsga2_outputs','v290_all22_algorithm_diagnostics');
if ~exist(outputRoot,'dir'); mkdir(outputRoot); end

restoredefaultpath;
addpath(genpath(platemoRoot));
addpath(compatRoot);
addpath(scriptDir);

problems = {
    'ZDT1', @ZDT1, 2,30,0.14621; 'ZDT2',@ZDT2,2,30,0.50813;
    'ZDT3', @ZDT3, 2,30,0.17787; 'ZDT4',@ZDT4,2,10,0.53146;
    'ZDT6', @ZDT6, 2,10,0.07429;
    'DTLZ1',@DTLZ1,3, 7,0.23828; 'DTLZ2',@DTLZ2,3,12,0.054881;
    'DTLZ3',@DTLZ3,3,12,13.357;  'DTLZ4',@DTLZ4,3,12,0.40388;
    'DTLZ5',@DTLZ5,3,12,0.032473;'DTLZ6',@DTLZ6,3,12,0.11635;
    'DTLZ7',@DTLZ7,3,22,0.1708;
    'UF1',@UF1,2,30,0.31352; 'UF2',@UF2,2,30,0.21196;
    'UF3',@UF3,2,30,0.33463; 'UF4',@UF4,2,30,0.12713;
    'UF5',@UF5,2,30,1.3074;  'UF6',@UF6,2,30,0.5948;
    'UF7',@UF7,2,30,0.43887; 'UF8',@UF8,3,30,0.58545;
    'UF9',@UF9,3,30,0.52501;'UF10',@UF10,3,30,0.74415;
};

cases = {
    'proM_per_variable', @NSGAII_ProMPerVariable_v290, 10000;
    'exact_100_offspring_generations', @NSGAII, 10100;
};

summaryRows = {};
for c = 1:size(cases,1)
    caseName = cases{c,1};
    algorithm = cases{c,2};
    evaluation = cases{c,3};
    for p = 1:size(problems,1)
        name = problems{p,1};
        problemFcn = problems{p,2};
        M = problems{p,3};
        D = problems{p,4};
        paper = problems{p,5};
        problemDir = fullfile(outputRoot,caseName,name);
        if ~exist(problemDir,'dir'); mkdir(problemDir); end

        referenceGlobal = GLOBAL('-algorithm',@NSGAII,'-problem',problemFcn, ...
            '-N',100,'-M',M,'-D',D,'-evaluation',10000, ...
            '-outputFcn',@(varargin)[]);
        PF = referenceGlobal.problem.PF(10000);
        values = nan(30,1);

        for run = 1:30
            runDir = fullfile(problemDir,sprintf('run_%03d',run));
            resultFile = fullfile(runDir,'igd.csv');
            if exist(resultFile,'file')
                old = readtable(resultFile);
                values(run) = old.igd(1);
                continue;
            end
            if ~exist(runDir,'dir'); mkdir(runDir); end

            rng(run,'twister');
            Global = GLOBAL('-algorithm',algorithm,'-problem',problemFcn, ...
                '-N',100,'-M',M,'-D',D,'-evaluation',evaluation, ...
                '-run',run,'-outputFcn',@(varargin)[]);
            Global.Start();
            Population = Global.result{end,2};
            Obj = Population.objs;
            Dec = Population.decs;
            value = directedMeanDistance(Obj,PF);
            values(run) = value;

            writematrix(Obj,fullfile(runDir,'obj.csv'));
            writematrix(Dec,fullfile(runDir,'dec.csv'));
            writetable(table(run,value,evaluation,'VariableNames', ...
                {'seed','igd','evaluation_budget'}),resultFile);
            fprintf('%s %s run %02d IGD %.12g\n',caseName,name,run,value);
        end

        meanValue = mean(values);
        stdValue = std(values);
        writetable(table((1:30)',values,'VariableNames',{'seed','igd'}), ...
            fullfile(problemDir,'igd_runs.csv'));
        summaryRows(end+1,:) = {caseName,name,M,D,100,evaluation,30,paper, ...
            meanValue,stdValue,meanValue-paper,abs(meanValue-paper), ...
            abs(meanValue-paper)/paper*100}; %#ok<SAGROW>
        writetable(cell2table(summaryRows,'VariableNames',summaryNames()), ...
            fullfile(outputRoot,'summary_partial.csv'));
    end
end

summary = cell2table(summaryRows,'VariableNames',summaryNames());
writetable(summary,fullfile(outputRoot,'summary.csv'));
disp(summary);

function names = summaryNames()
    names = {'case_name','problem','M','D','N','evaluation_budget','runs', ...
        'paper_igd','mean_igd','sample_std','signed_diff','abs_diff', ...
        'relative_diff_percent'};
end

function score = directedMeanDistance(approximation,reference)
    distances = inf(size(reference,1),1);
    for i = 1:size(approximation,1)
        delta = reference-approximation(i,:);
        distances = min(distances,sqrt(sum(delta.*delta,2)));
    end
    score = mean(distances);
end
