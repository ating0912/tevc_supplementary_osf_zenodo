function run_experiment_c_no_replicate_changed_final_test()
% Re-run only test instances whose selected theta changed after removing
% the synthetic replicate feature from the Experiment C selector.

scriptDir = fileparts(mfilename('fullpath'));

changedInstances = {
    'syn_n100_k05_low_corr_skewed_extreme_events_r02_s20260686'
    'syn_n100_k10_high_corr_normal_low_vol_r03_s20260698'
    'syn_n100_k30_high_corr_heavy_tail_extreme_events_r01_s20260722'
    'syn_n200_k10_high_corr_heavy_tail_extreme_events_r01_s20260746'
    'syn_n200_k30_high_corr_normal_low_vol_r03_s20260769'
    'syn_n500_k20_cluster_corr_skewed_high_vol_r01_s20260805'
    'syn_n500_k20_pathological_cov_mixed_low_vol_r01_s20260806'
    'syn_n50_k30_cluster_corr_heavy_tail_low_vol_r02_s20260673'
    'syn_n50_k30_low_corr_heavy_tail_high_vol_r03_s20260674'
};

assignin('base','META_DESIGNED_METHOD','ExperimentC_StabilityAware_ECMADE_MOO');
assignin('base','META_DESIGNED_ASSIGNMENT_PATH',fullfile(scriptDir, ...
    'outputs','experiment_c_replicate_audit_20260730','full_selector_no_replicate', ...
    'experiment_c_stability_theta_assignment.csv'));
assignin('base','META_DESIGNED_OUT_ROOT',fullfile(scriptDir, ...
    'p0_lite_outputs','experiment_c_stability_ecmade_moo_no_replicate_20260730'));
assignin('base','META_DESIGNED_RUNS',30);
assignin('base','META_DESIGNED_N',100);
assignin('base','META_DESIGNED_MAXFE',10000);
assignin('base','META_DESIGNED_MAX_INSTANCES',inf);
assignin('base','META_DESIGNED_INSTANCE_NAMES',changedInstances);
assignin('base','META_DESIGNED_FORCE_RERUN',true);

run_meta_designed_ecmade_moo();

evalin('base',[
    'clear META_DESIGNED_METHOD META_DESIGNED_ASSIGNMENT_PATH META_DESIGNED_OUT_ROOT ' ...
    'META_DESIGNED_RUNS META_DESIGNED_N META_DESIGNED_MAXFE META_DESIGNED_MAX_INSTANCES ' ...
    'META_DESIGNED_INSTANCE_NAMES META_DESIGNED_FORCE_RERUN']);
end
