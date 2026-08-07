import os


ROOT = r"."
os.environ.setdefault("EXPERIMENT_A_ROOT", ROOT)
os.environ.setdefault("EXPERIMENT_A_OUT_ROOT", os.path.join(ROOT, "p0_lite_outputs", "orlib_constrained_portfolio"))
os.environ.setdefault("EXPERIMENT_A_MANIFEST", os.path.join(ROOT, "data", "orlib_constrained_portfolio", "manifest.csv"))
os.environ.setdefault("EXPERIMENT_A_REPORT_PREFIX", "experiment_A_orlib_report")
os.environ.setdefault("EXPERIMENT_A_DOCX_NAME", "Experiment_A_OR-Library_results_report.docx")
os.environ.setdefault("EXPERIMENT_A_DATASET_LABEL", "OR-Library")
os.environ.setdefault("EXPERIMENT_A_REPORT_TITLE", "Experiment A OR-Library Results Report")
os.environ.setdefault(
    "EXPERIMENT_A_REPORT_SUBTITLE",
    "ECMADE-MOO and Baseline Comparison on Formal OR-Library Portfolio Instances",
)

from build_synthetic_experiment_a_report import main


if __name__ == "__main__":
    main()
