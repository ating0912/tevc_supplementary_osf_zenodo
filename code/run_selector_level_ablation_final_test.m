function run_selector_level_ablation_final_test()
% Formal selector-level final-test ablation for TEVC Experiment C.
%
% This wrapper reuses run_meta_designed_ecmade_moo.m with four assignment
% files produced by build_selector_level_ablation_assignments.py.
%
% Optional base-workspace overrides:
%   SELECTOR_ABLATION_RUNS, SELECTOR_ABLATION_N, SELECTOR_ABLATION_MAXFE
%   SELECTOR_ABLATION_MAX_INSTANCES, SELECTOR_ABLATION_FORCE_RERUN

scriptDir = fileparts(mfilename('fullpath'));
assignmentRoot = fullfile(scriptDir,'outputs','selector_level_ablation_20260728');
rawRoot = fullfile(assignmentRoot,'raw_final_test');

runs = getBaseValue('SELECTOR_ABLATION_RUNS',10);
N = getBaseValue('SELECTOR_ABLATION_N',100);
maxFE = getBaseValue('SELECTOR_ABLATION_MAXFE',10000);
maxInstances = getBaseValue('SELECTOR_ABLATION_MAX_INSTANCES',inf);
forceRerun = getBaseValue('SELECTOR_ABLATION_FORCE_RERUN',false);

variants = {
    'FullSelector',       'SelectorAblation_FullSelector_ECMADE_MOO';
    'NoInstanceFeatures', 'SelectorAblation_NoInstanceFeatures_ECMADE_MOO';
    'NoThetaFeatures',    'SelectorAblation_NoThetaFeatures_ECMADE_MOO';
    'RandomizedLabels',   'SelectorAblation_RandomizedLabels_ECMADE_MOO';
};

if ~exist(rawRoot,'dir')
    mkdir(rawRoot);
end

fprintf('Selector-level ablation final test\n');
fprintf('assignmentRoot=%s\n',assignmentRoot);
fprintf('rawRoot=%s\n',rawRoot);
fprintf('runs=%d, N=%d, maxFE=%d, maxInstances=%g\n',runs,N,maxFE,maxInstances);

for i = 1:size(variants,1)
    variant = variants{i,1};
    method = variants{i,2};
    assignmentPath = fullfile(assignmentRoot,[variant '_theta_assignment.csv']);
    outRoot = fullfile(rawRoot,variant);

    if ~exist(assignmentPath,'file')
        error('SelectorAblation:MissingAssignment','Missing assignment: %s',assignmentPath);
    end
    if ~exist(outRoot,'dir')
        mkdir(outRoot);
    end

    assignin('base','META_DESIGNED_METHOD',method);
    assignin('base','META_DESIGNED_ASSIGNMENT_PATH',assignmentPath);
    assignin('base','META_DESIGNED_OUT_ROOT',outRoot);
    assignin('base','META_DESIGNED_RUNS',runs);
    assignin('base','META_DESIGNED_N',N);
    assignin('base','META_DESIGNED_MAXFE',maxFE);
    assignin('base','META_DESIGNED_MAX_INSTANCES',maxInstances);
    assignin('base','META_DESIGNED_INSTANCE_NAMES',{});
    assignin('base','META_DESIGNED_FORCE_RERUN',forceRerun);

    fprintf('\n=== Variant %d/%d: %s ===\n',i,size(variants,1),variant);
    run_meta_designed_ecmade_moo();
end

evalin('base','clear META_DESIGNED_METHOD META_DESIGNED_ASSIGNMENT_PATH META_DESIGNED_OUT_ROOT META_DESIGNED_RUNS META_DESIGNED_N META_DESIGNED_MAXFE META_DESIGNED_MAX_INSTANCES META_DESIGNED_INSTANCE_NAMES META_DESIGNED_FORCE_RERUN');
fprintf('Selector-level ablation final test complete: %s\n',rawRoot);
end

function value = getBaseValue(name,defaultValue)
if evalin('base',sprintf('exist(''%s'',''var'')',name))
    value = evalin('base',name);
else
    value = defaultValue;
end
end
