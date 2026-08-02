% P1 MOKP global-theta diagnostic for Experiment C selected theta values.

assignmentRoot = fullfile(pwd,'p0_lite_outputs','p1_mokp_experiment_c_global_theta_assignments_20260729');
outputRoot = fullfile(pwd,'p0_lite_outputs','p1_mokp_experiment_c_global_theta_diagnostic_20260729');

P1MOKPConfigRunner.runAssignment('ExperimentC_GlobalTheta034_ECMADE_MOO', ...
    fullfile(assignmentRoot,'p1_mokp_global_theta_034_assignment.csv'), outputRoot);

P1MOKPConfigRunner.runAssignment('ExperimentC_GlobalTheta037_ECMADE_MOO', ...
    fullfile(assignmentRoot,'p1_mokp_global_theta_037_assignment.csv'), outputRoot);
