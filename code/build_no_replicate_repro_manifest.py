from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "no_replicate_reproducibility_manifest_20260731.json"


def run(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, cwd=ROOT, text=True, stderr=subprocess.STDOUT, timeout=30).strip()
    except Exception as exc:
        return f"unavailable: {type(exc).__name__}: {exc}"


def package_version(name: str) -> str:
    try:
        import importlib.metadata as metadata

        return metadata.version(name)
    except Exception:
        return "unavailable"


def main() -> None:
    manifest = {
        "created": "2026-07-31",
        "workspace": str(ROOT),
        "os": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
        },
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "packages": {
                "numpy": package_version("numpy"),
                "pandas": package_version("pandas"),
                "scipy": package_version("scipy"),
                "scikit-learn": package_version("scikit-learn"),
                "joblib": package_version("joblib"),
                "shap": package_version("shap"),
                "matplotlib": package_version("matplotlib"),
            },
        },
        "matlab": {
            "version_command": run(["matlab", "-batch", "disp(version); exit"]),
            "platemo_roots": [
                str(ROOT / "PlatEMO_v2.9.0" / "PlatEMO"),
                str(ROOT / "PlatEMO_v4.3"),
            ],
        },
        "experiment_outputs": {
            "selector_training": str(ROOT / "p0_lite_outputs" / "experiment_c_stability_selector_training"),
            "feature_importance": str(ROOT / "outputs" / "experiment_c_feature_importance_20260725"),
            "replicate_audit": str(ROOT / "outputs" / "experiment_c_replicate_audit_20260730"),
            "formal_five_method": str(ROOT / "p0_lite_outputs" / "experiment_c_formal_five_method_no_replicate_20260731"),
            "six_method_audit": str(ROOT / "p0_lite_outputs" / "experiment_c_replicate_audit_final_test_20260730"),
            "real_market": str(
                ROOT
                / "p0_lite_outputs"
                / "p1_rolling_window_market_validation_20260719"
                / "configured_ecmade_no_replicate_audit_summary_20260731"
            ),
            "mokp": str(ROOT / "p0_lite_outputs" / "p1_mokp_config_comparison_no_replicate_audit_20260731"),
            "selector_level_ablation": str(ROOT / "outputs" / "selector_level_ablation_20260728"),
        },
        "primary_commands": [
            "python train_experiment_c_stability_selector.py",
            "python outputs/experiment_c_feature_importance_20260725/compute_selector_importance.py",
            "python plot_no_replicate_shap_diagnostics.py",
            "python summarize_experiment_c_formal_five_method.py",
            "python summarize_experiment_c_replicate_audit_final_test.py",
            "python analyze_experiment_c_replicate_audit_statistics.py",
            "python analyze_stability_weighted_rank_no_replicate_audit.py",
            "python analyze_real_market_ecmade_no_replicate_audit.py",
            "python analyze_p1_mokp_config_comparison_no_replicate_audit.py",
            "matlab -batch \"SELECTOR_ABLATION_RUNS=30; SELECTOR_ABLATION_FORCE_RERUN=false; run_selector_level_ablation_final_test\"",
            "python analyze_selector_level_ablation_final_test.py",
        ],
    }
    OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"WROTE={OUT}")


if __name__ == "__main__":
    main()
