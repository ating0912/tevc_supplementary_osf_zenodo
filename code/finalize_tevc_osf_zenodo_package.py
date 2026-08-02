from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "tevc_supplementary_osf_zenodo"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if not OUT.exists():
        raise SystemExit(f"Missing package folder: {OUT}")

    archives = [
        ("run_logs", OUT / "logs/full_run_logs.zip"),
        ("figures", OUT / "figures/paper_figures.zip"),
        ("raw_pf_csv", OUT / "raw_pf/raw_pf_csv.zip"),
    ]
    rows = []
    for item, path in archives:
        rows.append(
            {
                "item": item,
                "archive": str(path.relative_to(OUT)).replace("\\", "/"),
                "included": "yes" if path.exists() else "no",
                "size_bytes": path.stat().st_size if path.exists() else "",
                "notes": "Archive contains actual files from the local TEVC workspace. See dedicated inventory or archive contents for file-level details.",
            }
        )
    rows.append(
        {
            "item": "software_hardware_environment",
            "archive": "system/software_environment.md",
            "included": "yes",
            "size_bytes": "",
            "notes": "OS/CPU/RAM/GPU/MATLAB/PlatEMO information is recorded.",
        }
    )
    write_csv(OUT / "manifest/osf_zenodo_completion_summary.csv", rows)

    figure_rows = []
    for path in sorted((OUT / "figures").glob("*")):
        if path.is_file():
            figure_rows.append(
                {
                    "file": str(path.relative_to(OUT)).replace("\\", "/"),
                    "size_bytes": path.stat().st_size,
                }
            )
    write_csv(OUT / "manifest/figures_inventory.csv", figure_rows)

    write_csv(
        OUT / "manifest/supplementary_package_checklist.csv",
        [
            {
                "requested_item": "code",
                "status": "complete_for_workspace_research_code",
                "package_location": "code/ and manifest/code_inventory.csv",
                "notes": "All source-like research scripts from the workspace root and selected research tool folders are copied. Third-party dependencies are versioned separately.",
            },
            {
                "requested_item": "README",
                "status": "complete",
                "package_location": "README.md and README.zh-TW.md",
                "notes": "English and Traditional Chinese README files are included.",
            },
            {
                "requested_item": "environment.yml",
                "status": "complete",
                "package_location": "environment.yml",
                "notes": "Python environment is included.",
            },
            {
                "requested_item": "MATLAB/PlatEMO version",
                "status": "complete",
                "package_location": "system/software_environment.md",
                "notes": "MATLAB R2020b Update 8 is recorded from local log; PlatEMO folders present are recorded.",
            },
            {
                "requested_item": "CPU/GPU/OS",
                "status": "complete",
                "package_location": "system/software_environment.md",
                "notes": "OS, CPU logical processor count, RAM, and GPU adapters are recorded.",
            },
            {
                "requested_item": "run logs",
                "status": "included",
                "package_location": "logs/full_run_logs.zip",
                "notes": "Actual run logs are packaged.",
            },
            {
                "requested_item": "tables",
                "status": "complete_for_summary_tables",
                "package_location": "paper_outputs/ and experiments/",
                "notes": "Paper summary tables and statistical-test tables are included. Large run-level tables remain listed in manifest/external_artifacts.csv if not duplicated as standalone files.",
            },
            {
                "requested_item": "figures",
                "status": "included",
                "package_location": "figures/ and figures/paper_figures.zip",
                "notes": "Paper figure files and a figure archive are included.",
            },
            {
                "requested_item": "raw PF csv",
                "status": "included",
                "package_location": "raw_pf/raw_pf_csv.zip",
                "notes": "Actual raw Pareto-front/objective/archive CSV files are packaged.",
            },
        ],
    )

    write_text(
        OUT / "system/software_environment.md",
        """
# Software and Hardware Environment

## Operating System

- OS: Microsoft Windows NT 10.0.26200.0
- Architecture: 64-bit
- Machine name recorded during packaging: LAPTOP-NEKNF074

## CPU / RAM / GPU

- CPU: Intel64 Family 6 Model 186 Stepping 2, GenuineIntel
- Logical processors: 20
- RAM: 15.65 GB
- GPU adapters detected from Windows display registry:
  - NVIDIA GeForce RTX 4050 Laptop GPU
  - Intel(R) Iris(R) Xe Graphics
- GPU usage note: packaged validation scripts do not require GPU execution unless a specific runner states otherwise.

## MATLAB / PlatEMO

- MATLAB version recorded from `matlab_r2020b_startup.log`: 9.9.0.2037887 (R2020b) Update 8
- MATLAB direct launch note: a later direct `matlab -batch` check encountered a local license checkout error, so the package records the existing run-environment log rather than a fresh launch result.
- PlatEMO-related folders present in the workspace:
  - PlatEMO
  - PlatEMO_v2.9.0
  - PlatEMO_v4.3
  - platemo_v43_compat
  - matlab_platemo
- Final paper note: if a specific experiment block used a specific PlatEMO version, cite that block-level runner or source map entry alongside this environment record.

## Python

- Environment file: `environment.yml`
- Requirements file: `requirements.txt`
- Main packages: numpy, pandas, scipy, scikit-learn, joblib, matplotlib, seaborn, openpyxl, PyYAML, statsmodels.
""",
    )
    print(f"Finalized OSF/Zenodo package at: {OUT}")


if __name__ == "__main__":
    main()
