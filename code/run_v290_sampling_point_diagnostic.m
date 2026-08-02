% Test which final sampling point may have been used for reported IGD.

clear; clc;
global NSGAII_SAMPLING_TRACE

root=fileparts(mfilename('fullpath'));
outputRoot=fullfile(root,'nsga2_outputs','v290_sampling_point_diagnostic');
if ~exist(outputRoot,'dir'); mkdir(outputRoot); end
restoredefaultpath;
addpath(fullfile(root,'v290_metric_compat'));
addpath(genpath(fullfile(root,'PlatEMO_v2.9.0','PlatEMO')));
addpath(fullfile(root,'platemo_v43_compat'));
addpath(root);

problems={
    'ZDT2',@ZDT2,2,30,0.50813; 'ZDT4',@ZDT4,2,10,0.53146;
    'DTLZ1',@DTLZ1,3,7,0.23828; 'DTLZ4',@DTLZ4,3,12,0.40388;
    'UF6',@UF6,2,30,0.5948; 'UF10',@UF10,3,30,0.74415;
};
variants={'previous_parent_9900FE','last_offspring_100', ...
    'preselection_mixed_200','final_population_100','history_archive'};
rows={};

for p=1:size(problems,1)
    name=problems{p,1}; f=problems{p,2}; M=problems{p,3};
    D=problems{p,4}; paper=problems{p,5};
    ref=GLOBAL('-algorithm',@NSGAII,'-problem',f,'-N',100,'-M',M,'-D',D, ...
        '-evaluation',10000,'-outputFcn',@(varargin)[]);
    PF=ref.problem.PF(10000);
    values=nan(30,numel(variants));

    for run=1:30
        runDir=fullfile(outputRoot,name,sprintf('run_%03d',run));
        resultFile=fullfile(runDir,'igd.csv');
        if exist(resultFile,'file')
            old=readtable(resultFile);
            for v=1:numel(variants)
                values(run,v)=old.(variants{v})(1);
            end
            continue;
        end
        if ~exist(runDir,'dir'); mkdir(runDir); end
        rng(run,'twister');
        G=GLOBAL('-algorithm',@NSGAII_SamplingDiagnostic_v290,'-problem',f, ...
            '-N',100,'-M',M,'-D',D,'-evaluation',10000,'-run',run, ...
            '-outputFcn',@(varargin)[]);
        G.Start();

        sets={NSGAII_SAMPLING_TRACE.previous.objs, ...
            NSGAII_SAMPLING_TRACE.offspring.objs, ...
            NSGAII_SAMPLING_TRACE.mixed.objs, ...
            NSGAII_SAMPLING_TRACE.final.objs, ...
            NSGAII_SAMPLING_TRACE.archive};
        for v=1:numel(sets)
            Obj=sets{v};
            Obj=Obj(NDSort(Obj,1)==1,:);
            values(run,v)=IGD(Obj,PF);
        end
        result=array2table(values(run,:),'VariableNames',variants);
        result.seed=run;
        result=movevars(result,'seed','Before',1);
        writetable(result,resultFile);
        fprintf('%s run=%02d final=%.12g archive=%.12g\n', ...
            name,run,values(run,4),values(run,5));
    end

    for v=1:numel(variants)
        m=mean(values(:,v)); s=std(values(:,v));
        rows(end+1,:)={variants{v},name,M,D,30,paper,m,s,m-paper, ...
            abs(m-paper),abs(m-paper)/paper*100, ...
            sprintf('%.4e (%.4e)',m,s)}; %#ok<SAGROW>
    end
    writetable(array2table([(1:30)',values],'VariableNames', ...
        [{'seed'},variants]),fullfile(outputRoot,name,'igd_runs.csv'));
    writeSummary(outputRoot,rows);
end

summary=cell2table(rows,'VariableNames',summaryNames());
writetable(summary,fullfile(outputRoot,'summary.csv'));
ranking=groupsummary(summary,'variant',{'mean','median'}, ...
    'relative_diff_percent');
ranking=sortrows(ranking,'mean_relative_diff_percent');
writetable(ranking,fullfile(outputRoot,'ranking.csv'));
disp(summary); disp(ranking);

function writeSummary(outputRoot,rows)
    T=cell2table(rows,'VariableNames',summaryNames());
    writetable(T,fullfile(outputRoot,'summary_partial.csv'));
end
function n=summaryNames()
    n={'variant','problem','M','D','runs','paper_igd','mean_igd', ...
       'sample_std','signed_diff','abs_diff','relative_diff_percent','mean_std'};
end
