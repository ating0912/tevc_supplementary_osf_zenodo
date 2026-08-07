from __future__ import annotations

import csv
import os
import platform
import shutil
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GITHUB = ROOT / "tevc_reproducibility_github"
OUT = ROOT / "tevc_supplementary_osf_zenodo"

EXCLUDE_DIRS = {
    ".git",
    ".agents",
    ".codex",
    "__pycache__",
    "node_modules",
    "tevc_reproducibility_package",
    "tevc_reproducibility_github",
    "tevc_reproducibility_github_replicate",
    "tevc_supplementary_osf_zenodo",
    "PlatEMO",
    "PlatEMO_v2.9.0",
    "PlatEMO_v4.3",
    "PEATSD",
    "PEATSD_upstream",
}

LOG_EXTENSIONS = {".log", ".out", ".err"}
LOG_NAME_PATTERNS = ("log", "stdout", "stderr", "progress", "status")
FIGURE_EXTENSIONS = {".png", ".svg", ".pdf", ".jpg", ".jpeg"}
RAW_PF_PATTERNS = ("pf", "front", "archive", "obj")
RAW_PF_EXTENSIONS = {".csv"}
ARTIFACT_ROOTS = [
    ROOT / "p0_lite_outputs/p1_mokp_experiment_c_no_replicate_full_20260731",
    ROOT / "p0_lite_outputs/experiment_c_stability_ecmade_moo_no_replicate_20260730",
    ROOT / "p0_lite_outputs/experiment_c_formal_five_method_no_replicate_20260731",
    ROOT / "p0_lite_outputs/p1_mokp_config_comparison_no_replicate_audit_20260731",
    ROOT / "p0_lite_outputs/p1_rolling_window_market_validation_20260719",
    ROOT / "outputs/experiment_A_stats_delivery_20260706",
    ROOT / "outputs/experiment_c_replicate_audit_20260730",
    ROOT / "outputs/selector_level_ablation_20260728",
    ROOT / "outputs/real_market_config_protocol_section_20260730",
    ROOT / "outputs/experiment_c_feature_importance_20260725",
    ROOT / "outputs/experiment_c_report_20260717",
]


def should_exclude(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    return any(part in EXCLUDE_DIRS for part in rel.parts)


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


def zip_files(files: list[Path], zip_path: Path) -> list[dict[str, object]]:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
        for src in sorted(files, key=lambda p: str(p.relative_to(ROOT)).lower()):
            if not src.exists() or not src.is_file():
                continue
            arcname = str(src.relative_to(ROOT)).replace("\\", "/")
            zf.write(src, arcname)
            rows.append({"archive": str(zip_path.relative_to(OUT)).replace("\\", "/"), "file": arcname, "size_bytes": src.stat().st_size})
    return rows


def collect_logs() -> list[Path]:
    files: list[Path] = []
    bases = [base for base in ARTIFACT_ROOTS if base.exists()]
    for base in bases:
        for path in base.rglob("*") if base.is_dir() else []:
            if not path.is_file() or should_exclude(path):
                continue
            name = path.name.lower()
            if path.suffix.lower() in LOG_EXTENSIONS or any(pattern in name for pattern in LOG_NAME_PATTERNS):
                if path.suffix.lower() in {".log", ".out", ".err", ".txt"} or any(pattern in name for pattern in LOG_NAME_PATTERNS):
                    files.append(path)
    for path in ROOT.iterdir():
        if path.is_file() and (path.suffix.lower() in LOG_EXTENSIONS or any(pattern in path.name.lower() for pattern in LOG_NAME_PATTERNS)):
            files.append(path)
    return sorted(set(files), key=lambda p: str(p.relative_to(ROOT)).lower())


def collect_figures() -> list[Path]:
    files: list[Path] = []
    bases = [base for base in ARTIFACT_ROOTS if base.exists()]
    for base in bases:
        for path in base.rglob("*"):
            if not path.is_file() or should_exclude(path):
                continue
            if path.suffix.lower() in FIGURE_EXTENSIONS:
                files.append(path)
    for path in ROOT.iterdir():
        if path.is_file() and path.suffix.lower() in FIGURE_EXTENSIONS:
            files.append(path)
    return sorted(set(files), key=lambda p: str(p.relative_to(ROOT)).lower())


def collect_raw_pf_csv() -> list[Path]:
    roots = [base for base in ARTIFACT_ROOTS if base.exists()]
    seen: set[Path] = set()
    files: list[Path] = []
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*.csv"):
            if not path.is_file() or path in seen or should_exclude(path):
                continue
            name = path.name.lower()
            if any(pattern in name for pattern in RAW_PF_PATTERNS):
                seen.add(path)
                files.append(path)
    return files


def matlab_version() -> str:
    try:
        completed = subprocess.run(
            ["matlab", "-batch", "disp(version);"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception as exc:
        return f"not detected automatically ({exc})"
    text = (completed.stdout + "\n" + completed.stderr).strip()
    if completed.returncode != 0:
        return f"matlab -batch failed with exit code {completed.returncode}: {text[:500]}"
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else "matlab command returned no version text"


def ram_gb() -> str:
    if platform.system().lower() != "windows":
        return "not detected automatically"
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        return f"{status.ullTotalPhys / (1024 ** 3):.2f} GB"
    except Exception as exc:
        return f"not detected automatically ({exc})"


def write_system_environment() -> None:
    matlab = matlab_version()
    platemo_versions = []
    for candidate in ["PlatEMO_v2.9.0", "PlatEMO_v4.3", "PlatEMO"]:
        path = ROOT / candidate
        if path.exists():
            platemo_versions.append(candidate)
    text = f"""
# Software and Hardware Environment

## Operating System

- OS: {platform.platform()}
- Machine: {platform.machine()}

## CPU / RAM / GPU

- CPU: {platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "not detected automatically")}
- RAM: {ram_gb()}
- GPU: not detected automatically in this restricted session; fill from the run machine if GPU was used.
- GPU usage: not required for the packaged validation scripts unless a separate runner states otherwise.

## MATLAB / PlatEMO

- MATLAB version detected by `matlab -batch "disp(version);"`: {matlab}
- PlatEMO folders present in workspace: {", ".join(platemo_versions) if platemo_versions else "not found"}
- Final paper package note: record the exact PlatEMO folder/version used for each experiment block if multiple versions were used.

## Python

- Python: {platform.python_version()}
- Environment file: `environment.yml`
- Requirements file: `requirements.txt`
"""
    write_text(OUT / "system/software_environment.md", text)


def main() -> None:
    if not GITHUB.exists():
        raise SystemExit("Build tevc_reproducibility_github first.")
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(GITHUB, OUT)

    log_rows = zip_files(collect_logs(), OUT / "logs/full_run_logs.zip")
    figure_rows = zip_files(collect_figures(), OUT / "figures/paper_figures.zip")
    raw_pf_rows = zip_files(collect_raw_pf_csv(), OUT / "raw_pf/raw_pf_csv.zip")

    write_csv(OUT / "manifest/run_logs_inventory.csv", log_rows)
    write_csv(OUT / "manifest/figures_inventory.csv", figure_rows)
    write_csv(OUT / "manifest/raw_pf_inventory.csv", raw_pf_rows)
    write_system_environment()
    write_csv(
        OUT / "manifest/osf_zenodo_completion_summary.csv",
        [
            {"item": "run_logs", "archive": "logs/full_run_logs.zip", "files": len(log_rows), "status": "included"},
            {"item": "figures", "archive": "figures/paper_figures.zip", "files": len(figure_rows), "status": "included"},
            {"item": "raw_pf_csv", "archive": "raw_pf/raw_pf_csv.zip", "files": len(raw_pf_rows), "status": "included"},
            {"item": "software_hardware_environment", "archive": "system/software_environment.md", "files": 1, "status": "included"},
        ],
    )
    print(f"OSF/Zenodo package built at: {OUT}")
    print(f"run logs: {len(log_rows)} files")
    print(f"figures: {len(figure_rows)} files")
    print(f"raw PF CSV: {len(raw_pf_rows)} files")


if __name__ == "__main__":
    main()
