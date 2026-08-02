clear; clc;
base=fileparts(mfilename('fullpath')); input=fullfile(base,'nsga2_outputs','deb_c_zdt_maxfe10000'); pfRoot=fullfile(base,'zdt_reference_v43');
P={'ZDT1',30,.14621;'ZDT2',30,.50813;'ZDT3',30,.17787;'ZDT4',10,.53146;'ZDT6',10,.07429}; rows={}; details={};
for p=1:size(P,1)
 name=P{p,1}; D=P{p,2}; paper=P{p,3}; PF=readmatrix(fullfile(pfRoot,[name,'.csv'])); vf=nan(30,1); vb=nan(30,1);
 for run=1:30
  rd=fullfile(input,name,sprintf('run_%03d',run)); F=readmatrix(fullfile(rd,'final_pop.out'),'FileType','text','CommentStyle','#'); B=readmatrix(fullfile(rd,'best_pop.out'),'FileType','text','CommentStyle','#');
  vf(run)=igd(F(:,1:2),PF); vb(run)=igd(B(:,1:2),PF); details(end+1,:)={name,run,vf(run),vb(run),size(B,1)}; %#ok<SAGROW>
 end
 for s=1:2, V={vf,vb}; labels={'final_population','best_nondominated'}; m=mean(V{s}); rows(end+1,:)={name,2,D,labels{s},30,size(PF,1),paper,m,std(V{s}),m-paper,abs(m-paper),abs(m-paper)/paper*100}; end %#ok<SAGROW>
end
T=cell2table(rows,'VariableNames',{'problem','M','D','solution_set','runs','pf_points','paper_igd','mean_igd','sample_std','signed_diff','abs_diff','relative_diff_percent'});
R=cell2table(details,'VariableNames',{'problem','seed','final_population_igd','best_nondominated_igd','best_population_size'});
writetable(T,fullfile(input,'summary.csv')); writetable(R,fullfile(input,'igd_runs.csv')); disp(T);
function z=igd(A,R), d=inf(size(R,1),1); for i=1:size(A,1), q=R-A(i,:); d=min(d,sqrt(sum(q.*q,2))); end, z=mean(d); end
