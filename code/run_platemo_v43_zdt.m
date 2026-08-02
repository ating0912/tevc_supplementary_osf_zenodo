% Run PlatEMO v4.3 NSGA-II on the five paper ZDT problems.
clear; clc;
scriptDir=fileparts(mfilename('fullpath'));
root=fullfile(scriptDir,'PlatEMO_v4.3','PlatEMO');
out=fullfile(scriptDir,'nsga2_outputs','platemo_v43_zdt_seeded_r2026a');
pfRoot=fullfile(scriptDir,'zdt_reference_v43');
if ~exist(out,'dir'); mkdir(out); end
if ~exist(pfRoot,'dir'); mkdir(pfRoot); end
restoredefaultpath; addpath(genpath(root)); addpath(fullfile(scriptDir,'platemo_v43_compat'));
P={'ZDT1',@ZDT1,30,.14621;'ZDT2',@ZDT2,30,.50813;'ZDT3',@ZDT3,30,.17787; ...
   'ZDT4',@ZDT4,10,.53146;'ZDT6',@ZDT6,10,.07429};
rows={};
for p=1:size(P,1)
 name=P{p,1}; f=P{p,2}; D=P{p,3}; paper=P{p,4}; dir=fullfile(out,name);
 if ~exist(dir,'dir'); mkdir(dir); end
 pr=f('N',100,'M',2,'D',D,'maxFE',10000); PF=pr.GetOptimum(10000);
 writematrix(PF,fullfile(pfRoot,[name,'.csv'])); v=nan(30,1); e=nan(30,1);
 for run=1:30
  rd=fullfile(dir,sprintf('run_%03d',run)); file=fullfile(rd,'igd.csv');
  if exist(file,'file'); t=readtable(file); v(run)=t.igd(1); e(run)=t.elapsed_seconds(1); continue; end
  if ~exist(rd,'dir'); mkdir(rd); end
  rng(run,'twister'); tic; [Dec,Obj,~]=platemo('algorithm',@NSGAII,'problem',f,'N',100,'M',2,'D',D,'maxFE',10000); e(run)=toc;
  v(run)=igd(Obj,PF); writematrix(Dec,fullfile(rd,'dec.csv')); writematrix(Obj,fullfile(rd,'obj.csv'));
  writetable(table(run,v(run),e(run),'VariableNames',{'seed','igd','elapsed_seconds'}),file);
 end
 writetable(table((1:30)',v,e,'VariableNames',{'seed','igd','elapsed_seconds'}),fullfile(dir,'igd_runs.csv'));
 m=mean(v); s=std(v); rows(end+1,:)={name,2,D,100,10000,30,size(PF,1),paper,m,s,m-paper,abs(m-paper),abs(m-paper)/paper*100}; %#ok<SAGROW>
end
T=cell2table(rows,'VariableNames',{'problem','M','D','N','maxFE','runs','pf_points','paper_igd','mean_igd','sample_std','signed_diff','abs_diff','relative_diff_percent'});
writetable(T,fullfile(out,'summary.csv')); disp(T);
function z=igd(A,R), d=inf(size(R,1),1); for i=1:size(A,1), q=R-A(i,:); d=min(d,sqrt(sum(q.*q,2))); end, z=mean(d); end
