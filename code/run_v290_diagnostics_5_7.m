% Run diagnostics 5-7: RNG, boundary repair, and crowding tie handling.

clear; clc;
root=fileparts(mfilename('fullpath'));
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
families={
 'D5_rng','R1_twister_native',@NSGAII,'twister';
 'D5_rng','R2_dsfmt_native',@NSGAII,'dsfmt19937';
 'D5_rng','R3_mcg16807_native',@NSGAII,'mcg16807';
 'D5_rng','R4_twister_extra_per_generation',@NSGAII_ExtraRand_v290,'twister';
 'D6_boundary','B1_native_clip',@NSGAII_BoundaryClip_v290,'twister';
 'D6_boundary','B2_reflect',@NSGAII_BoundaryReflect_v290,'twister';
 'D6_boundary','B3_random_reset',@NSGAII_BoundaryRandom_v290,'twister';
 'D7_crowding_tie','C1_stable',@NSGAII_CrowdingStable_v290,'twister';
 'D7_crowding_tie','C2_random',@NSGAII_CrowdingRandom_v290,'twister';
 'D7_crowding_tie','C3_reverse_index',@NSGAII_CrowdingReverse_v290,'twister';
};

rows={};
for c=1:size(families,1)
    family=families{c,1}; variant=families{c,2};
    algorithm=families{c,3}; generator=families{c,4};
    outputRoot=fullfile(root,'nsga2_outputs','v290_diagnostics_5_7',family);
    if ~exist(outputRoot,'dir'); mkdir(outputRoot); end
    for p=1:size(problems,1)
        name=problems{p,1}; f=problems{p,2}; M=problems{p,3};
        D=problems{p,4}; paper=problems{p,5};
        problemDir=fullfile(outputRoot,variant,name);
        if ~exist(problemDir,'dir'); mkdir(problemDir); end
        ref=GLOBAL('-algorithm',@NSGAII,'-problem',f,'-N',100,'-M',M, ...
            '-D',D,'-evaluation',10000,'-outputFcn',@(varargin)[]);
        PF=ref.problem.PF(10000);
        values=nan(30,1);
        for run=1:30
            resultFile=fullfile(problemDir,sprintf('run_%03d.csv',run));
            if exist(resultFile,'file')
                old=readtable(resultFile); values(run)=old.igd(1); continue;
            end
            setGenerator(generator,run);
            G=GLOBAL('-algorithm',algorithm,'-problem',f,'-N',100,'-M',M, ...
                '-D',D,'-evaluation',10000,'-run',run, ...
                '-outputFcn',@(varargin)[]);
            G.Start();
            Population=G.result{end,2};
            Obj=Population.objs;
            feasible=all(Population.cons<=0,2);
            Obj=Obj(feasible,:);
            Obj=Obj(NDSort(Obj,1)==1,:);
            values(run)=IGD(Obj,PF);
            writetable(table(run,values(run),'VariableNames',{'seed','igd'}), ...
                resultFile);
            fprintf('%s %s %s run=%02d IGD=%.12g\n', ...
                family,variant,name,run,values(run));
        end
        m=mean(values); s=std(values);
        rows(end+1,:)={family,variant,name,M,D,30,paper,m,s,m-paper, ...
            abs(m-paper),abs(m-paper)/paper*100, ...
            sprintf('%.4e (%.4e)',m,s)}; %#ok<SAGROW>
        writetable(table((1:30)',values,'VariableNames',{'seed','igd'}), ...
            fullfile(problemDir,'igd_runs.csv'));
        writeOutputs(root,rows);
    end
end
writeOutputs(root,rows);

function setGenerator(name,seed)
    if strcmp(name,'twister')
        rng(seed,'twister');
    else
        RandStream.setGlobalStream(RandStream(name,'Seed',seed));
    end
end
function writeOutputs(root,rows)
    out=fullfile(root,'nsga2_outputs','v290_diagnostics_5_7');
    T=cell2table(rows,'VariableNames',names());
    writetable(T,fullfile(out,'summary.csv'));
    if isempty(T); return; end
    R=groupsummary(T,{'family','variant'},{'mean','median'}, ...
        'relative_diff_percent');
    R=sortrows(R,{'family','mean_relative_diff_percent'});
    writetable(R,fullfile(out,'ranking.csv'));
end
function n=names()
    n={'family','variant','problem','M','D','runs','paper_igd','mean_igd', ...
       'sample_std','signed_diff','abs_diff','relative_diff_percent','mean_std'};
end
