from __future__ import annotations

from pathlib import Path

import analyze_p1_mokp_config_comparison as base


ROOT = Path(__file__).resolve().parent

base.OUT_DIR = ROOT / "p0_lite_outputs" / "p1_mokp_config_comparison_no_replicate_audit_20260731"
base.SOURCES = [
    ROOT / "p0_lite_outputs" / "p1_multi_objective_knapsack_full_independent_20260719",
    ROOT / "p0_lite_outputs" / "p1_mokp_random_config_full_20260719",
    ROOT / "p0_lite_outputs" / "p1_mokp_meta_transfer_full_20260719",
    ROOT / "p0_lite_outputs" / "p1_mokp_bayesian_config_full_20260719" / "final_test",
    ROOT / "p0_lite_outputs" / "p1_mokp_experiment_c_stability_full_20260729",
    ROOT / "p0_lite_outputs" / "p1_mokp_experiment_c_no_replicate_full_20260731",
    ROOT / "p0_lite_outputs" / "p1_mokp_experiment_c_global_theta_diagnostic_20260729",
]
base.METHODS = [
    "NSGAII",
    "SPEA2",
    "MOEAD",
    "GDE3",
    "A_MPMO",
    "RandomConfig_ECMADE_MOO",
    "MetaTransfer_ECMADE_MOO",
    "BayesianConfig_ECMADE_MOO",
    "ExperimentC_StabilityAware_ECMADE_MOO",
    "ExperimentC_NoReplicate_ECMADE_MOO",
    "ExperimentC_GlobalTheta034_ECMADE_MOO",
    "ExperimentC_GlobalTheta037_ECMADE_MOO",
    "ECMADE_MOO",
]


if __name__ == "__main__":
    base.main()
