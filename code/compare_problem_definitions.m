% Compare v2.9, v4.3, and official CEC 2009 objective implementations.

clear; clc;
root = fileparts(mfilename('fullpath'));
out = fullfile(root,'nsga2_outputs','problem_definition_diagnostic');
officialRoot = fullfile(root,'cec2009_reference','official_database', ...
    'CEC2009_MultiObjectiveEA_Database');
addpath(officialRoot);

names={'ZDT2','ZDT4','DTLZ1','DTLZ4','UF6','UF10'};
rows={};
for i=1:numel(names)
    name=names{i};
    X=readmatrix(fullfile(out,[name '_dec.csv']));
    A=readmatrix(fullfile(out,[name '_v290_obj.csv']));
    B=readmatrix(fullfile(out,[name '_v43_obj.csv']));
    d=abs(A-B);
    officialMax=NaN; officialMean=NaN;
    if startsWith(name,'UF')
        official=cec09(name);
        C=official(X')';
        od=abs(A-C);
        officialMax=max(od,[],'all');
        officialMean=mean(od,'all');
        writematrix(C,fullfile(out,[name '_cec2009_obj.csv']));
    end
    rows(end+1,:)={name,size(X,1),max(d,[],'all'),mean(d,'all'), ...
        sum(d(:)>1e-12),officialMax,officialMean}; %#ok<SAGROW>
end
summary=cell2table(rows,'VariableNames', ...
    {'problem','points','v290_v43_max_abs_diff','v290_v43_mean_abs_diff', ...
     'v290_v43_values_above_1e12','v290_official_max_abs_diff', ...
     'v290_official_mean_abs_diff'});
writetable(summary,fullfile(out,'summary.csv'));
disp(summary);
