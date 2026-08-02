% Diagnostic 8: IGD precision, normalization, and distance conventions.

clear; clc;
root=fileparts(mfilename('fullpath'));
inputRoot=fullfile(root,'nsga2_outputs','v290_sampling_point_diagnostic');
outputRoot=fullfile(root,'nsga2_outputs','v290_diagnostic_8_metric');
if ~exist(outputRoot,'dir'); mkdir(outputRoot); end
restoredefaultpath;
addpath(fullfile(root,'v290_metric_compat'));
addpath(genpath(fullfile(root,'PlatEMO_v2.9.0','PlatEMO')));

problems={
 'ZDT2',@ZDT2,2,30,0.50813; 'ZDT4',@ZDT4,2,10,0.53146;
 'DTLZ1',@DTLZ1,3,7,0.23828; 'DTLZ4',@DTLZ4,3,12,0.40388;
 'UF6',@UF6,2,30,0.5948; 'UF10',@UF10,3,30,0.74415;
};
variants={'M1_native_double_raw','M2_manual_double_raw', ...
    'M3_single_precision_raw','M4_pf_range_normalized', ...
    'M5_joint_range_normalized','M6_squared_distance'};
rows={};
for p=1:size(problems,1)
    name=problems{p,1}; f=problems{p,2}; M=problems{p,3};
    D=problems{p,4}; paper=problems{p,5};
    G=GLOBAL('-algorithm',@NSGAII,'-problem',f,'-N',100,'-M',M,'-D',D, ...
        '-evaluation',10000,'-outputFcn',@(varargin)[]);
    PF=G.problem.PF(10000);
    values=nan(30,numel(variants));
    for run=1:30
        source=fullfile(root,'nsga2_outputs','v290_seed_sensitivity_all22_rerun2', ...
            'S01_seed_1_30',name,sprintf('seed_%04d',run),'obj.csv');
        Obj=readmatrix(source);
        Obj=Obj(NDSort(Obj,1)==1,:);
        values(run,1)=IGD(Obj,PF);
        values(run,2)=manualIGD(Obj,PF,false);
        values(run,3)=double(manualIGD(single(Obj),single(PF),false));
        lo=min(PF,[],1); span=max(PF,[],1)-lo; span(span==0)=1;
        values(run,4)=manualIGD((Obj-lo)./span,(PF-lo)./span,false);
        allObj=[Obj;PF]; lo=min(allObj,[],1);
        span=max(allObj,[],1)-lo; span(span==0)=1;
        values(run,5)=manualIGD((Obj-lo)./span,(PF-lo)./span,false);
        values(run,6)=manualIGD(Obj,PF,true);
    end
    for v=1:numel(variants)
        m=mean(values(:,v)); s=std(values(:,v));
        rows(end+1,:)={variants{v},name,M,D,30,paper,m,s,m-paper, ...
            abs(m-paper),abs(m-paper)/paper*100, ...
            sprintf('%.4e (%.4e)',m,s)}; %#ok<SAGROW>
    end
    writetable(array2table([(1:30)',values],'VariableNames', ...
        [{'seed'},variants]),fullfile(outputRoot,[name '_runs.csv']));
end
T=cell2table(rows,'VariableNames',names());
writetable(T,fullfile(outputRoot,'summary.csv'));
R=groupsummary(T,'variant',{'mean','median'},'relative_diff_percent');
R=sortrows(R,'mean_relative_diff_percent');
writetable(R,fullfile(outputRoot,'ranking.csv'));
disp(T); disp(R);

function score=manualIGD(A,R,squared)
    d=inf(size(R,1),1);
    for i=1:size(A,1)
        q=R-A(i,:);
        q=sum(q.*q,2);
        if ~squared; q=sqrt(q); end
        d=min(d,q);
    end
    score=mean(d);
end
function n=names()
    n={'variant','problem','M','D','runs','paper_igd','mean_igd', ...
       'sample_std','signed_diff','abs_diff','relative_diff_percent','mean_std'};
end
