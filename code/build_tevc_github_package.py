from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FULL = ROOT / "tevc_reproducibility_package"
OUT = ROOT / "tevc_reproducibility_github"
MAX_FULL_COPY_BYTES = 2_000_000
SAMPLE_ROWS = 200


TEXT_FILES = [
    "DATA_USE_STATEMENT.md",
    "LICENSES_THIRD_PARTY.md",
    "environment.yml",
    "requirements.txt",
    "configs/common_experiment_config.yaml",
    "configs/algorithm_parameters.yaml",
    "configs/handcrafted_theta.yaml",
    "configs/bayesian_search_space.yaml",
    "configs/ablation_configs.yaml",
    "configs/real_market_config.yaml",
    "labels/label_formula.md",
    "manifest/rng_policy.md",
    "manifest/run_metric_schema.csv",
    "manifest/meta_feature_schema.csv",
    "manifest/table_figure_map.csv",
    "selector/feature_columns_no_replicate.json",
    "selector/test_selected_theta.csv",
    "selector/test_theta_predictions.csv",
    "selector/selector_performance.csv",
    "selector/validation_theta_predictions.csv",
    "configs/theta_L24.csv",
    "data/synthetic/split_manifest.csv",
    "paper_outputs/table_experiment_a.csv",
    "paper_outputs/table_experiment_c.csv",
    "paper_outputs/table_real_market.csv",
    "real_market/configured_overall_summary.csv",
    "real_market/configured_friedman_tests.csv",
    "real_market/configured_pairwise_wilcoxon_holm.csv",
    "experiments/experiment_bc/formal_five_overall_summary.csv",
    "experiments/experiment_bc/formal_five_friedman_tests.csv",
    "experiments/experiment_bc/formal_five_primary_method_wilcoxon_holm.csv",
    "experiments/experiment_a/experiment_A_statistical_tests.csv",
]


HEAVY_ARTIFACTS = [
    "selector/selector_no_replicate.joblib",
    "labels/train_raw_run_metrics.csv",
    "labels/validation_raw_run_metrics.csv",
    "labels/train_theta_summary.csv",
    "labels/validation_theta_summary.csv",
    "labels/train_theta_ranking_labels.csv",
    "labels/validation_theta_ranking_labels.csv",
    "experiments/experiment_a/experiment_A_run_metrics.csv",
    "experiments/experiment_a/experiment_A_instance_method_summary.csv",
    "experiments/experiment_bc/formal_five_run_metrics.csv",
    "experiments/experiment_bc/formal_five_instance_method_metrics_raw.csv",
    "experiments/experiment_bc/formal_five_instance_method_endpoints_ranked.csv",
    "experiments/experiment_bc/formal_five_pairwise_wilcoxon_holm.csv",
    "real_market/configured_run_metrics_with_pf_stability.csv",
    "real_market/configured_window_method_summary.csv",
    "real_market/configured_window_method_ranked.csv",
    "real_market/configured_transaction_cost_overall.csv",
    "logs/full_run_logs.zip",
    "figures/paper_figures.zip",
    "raw_pf/raw_pf_csv.zip",
]


CODE_EXTENSIONS = {".py", ".m", ".mjs", ".js", ".ps1", ".bat", ".json", ".yaml", ".yml"}
CODE_EXCLUDE_DIRS = {
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
CODE_INCLUDE_DIRS = {
    "tevc_scripts",
    "p0_pf_plot_tools",
    "orlib_pf_plot_tools",
    "nsga2_sources",
    "nsga2_code_extract",
}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def copy_file(rel: str) -> None:
    src = FULL / rel
    dst = OUT / rel
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def sample_csv(src: Path, dst: Path, rows: int = SAMPLE_ROWS) -> int:
    dst.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with src.open("r", newline="", encoding="utf-8-sig") as f_in, dst.open(
        "w", newline="", encoding="utf-8-sig"
    ) as f_out:
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)
        for idx, row in enumerate(reader):
            if idx > rows:
                break
            writer.writerow(row)
            if idx > 0:
                written += 1
    return written


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def artifact_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for rel in HEAVY_ARTIFACTS:
        src = FULL / rel
        if not src.exists():
            rows.append(
                {
                    "package_path": rel,
                    "size_bytes": "",
                    "included_in_github": "no",
                    "sample_path": "",
                    "restore_to": rel,
                    "external_url": "TODO",
                    "notes": "Missing from local full package; add rebuild instructions or artifact URL.",
                }
            )
            continue
        sample_path = ""
        if src.suffix.lower() == ".csv":
            sample_rel = f"samples/{rel}.sample.csv"
            sample_csv(src, OUT / sample_rel)
            sample_path = sample_rel
        rows.append(
            {
                "package_path": rel,
                "size_bytes": src.stat().st_size,
                "included_in_github": "no",
                "sample_path": sample_path,
                "restore_to": rel,
                "external_url": "TODO",
                "notes": "Store in Zenodo/OSF/GitHub Release/Git LFS, then fill external_url.",
            }
        )
    return rows


def iter_code_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.iterdir():
        if path.is_file() and path.suffix.lower() in CODE_EXTENSIONS:
            files.append(path)
    for dirname in CODE_INCLUDE_DIRS:
        base = ROOT / dirname
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in CODE_EXTENSIONS:
                continue
            rel = path.relative_to(ROOT)
            if any(part in CODE_EXCLUDE_DIRS for part in rel.parts):
                continue
            files.append(path)
    return sorted(files, key=lambda p: str(p.relative_to(ROOT)).lower())


def copy_code_files() -> None:
    rows: list[dict[str, object]] = []
    for src in iter_code_files():
        rel = src.relative_to(ROOT)
        dst = OUT / "code" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        rows.append(
            {
                "code_path": str((Path("code") / rel).as_posix()),
                "source_path": str(src),
                "size_bytes": src.stat().st_size,
            }
        )
    write_csv(OUT / "manifest/code_inventory.csv", rows)


def software_environment_text() -> str:
    return """
# Software and Hardware Environment

This file records the environment fields requested for the GitHub/OSF/Zenodo supplementary package.

## Python

- Environment file: `environment.yml`
- Requirements file: `requirements.txt`
- Main Python packages: numpy, pandas, scipy, scikit-learn, joblib, matplotlib, seaborn, openpyxl, PyYAML, statsmodels.

## MATLAB and PlatEMO

- MATLAB version used for MATLAB/PlatEMO experiments: **to be verified before archival release**.
- Workspace evidence indicates MATLAB R2020b compatibility scripts/logs were used during development, but the final supplementary package should record the exact MATLAB release used for the reported runs.
- PlatEMO version: **to be verified before archival release**.
- Workspace contains PlatEMO v2.9.0 and v4.3-related compatibility folders/scripts; the final release should state which version was used for each experiment block.

## Hardware

Fill these fields before the OSF/Zenodo archival release:

- OS:
- CPU:
- RAM:
- GPU:
- GPU driver:
- Notes on whether GPU was used:

The current GitHub package does not require GPU execution for the packaged validation scripts.
"""


def supplementary_checklist_rows() -> list[dict[str, str]]:
    return [
        {
            "requested_item": "code",
            "status": "complete_for_workspace_research_code",
            "package_location": "code/ and manifest/code_inventory.csv",
            "notes": "All source-like research scripts from the workspace root are copied, excluding generated packages, git metadata, node_modules, and third-party dependency folders such as PlatEMO/PEATSD.",
        },
        {
            "requested_item": "README",
            "status": "complete",
            "package_location": "README.md and README.zh-TW.md",
            "notes": "Both English and Traditional Chinese README files include project purpose, conclusions, and no-replicate version definition.",
        },
        {
            "requested_item": "environment.yml",
            "status": "complete",
            "package_location": "environment.yml",
            "notes": "Python environment is included.",
        },
        {
            "requested_item": "MATLAB/PlatEMO version",
            "status": "partial_needs_final_value",
            "package_location": "system/software_environment.md",
            "notes": "Fields are present, but exact final MATLAB and PlatEMO versions must be verified and filled before archival release.",
        },
        {
            "requested_item": "CPU/GPU/OS",
            "status": "partial_needs_final_value",
            "package_location": "system/software_environment.md",
            "notes": "Fields are present. Automatic hardware query was not available in the current restricted session, so values must be filled manually or from the run machine.",
        },
        {
            "requested_item": "run logs",
            "status": "external_artifact_needed",
            "package_location": "logs/README.md and manifest/external_artifacts.csv",
            "notes": "GitHub package has a restoration location and artifact manifest entry; upload full logs to OSF/Zenodo/GitHub Release.",
        },
        {
            "requested_item": "tables",
            "status": "complete_for_summary_tables",
            "package_location": "paper_outputs/ and experiments/",
            "notes": "Paper summary tables and small statistical-test tables are included. Large run-level tables are listed as external artifacts with samples.",
        },
        {
            "requested_item": "figures",
            "status": "external_artifact_needed",
            "package_location": "figures/README.md and manifest/external_artifacts.csv",
            "notes": "No final paper figure files are currently included in the lightweight GitHub package; add figure archive or individual files before OSF/Zenodo release.",
        },
        {
            "requested_item": "raw PF csv",
            "status": "external_artifact_needed",
            "package_location": "raw_pf/README.md and manifest/external_artifacts.csv",
            "notes": "Raw Pareto-front CSV files are not in the lightweight GitHub package; add raw PF archive before OSF/Zenodo release.",
        },
    ]


def github_readme() -> str:
    return """
# TEVC Reproducibility Package - GitHub Version

This repository contains the GitHub-ready **no-replicate** reproducibility package for the TEVC portfolio-optimization study. It provides the code-facing, reviewer-readable control layer for tracing the reported results from experimental settings to selector inputs, metrics, statistical tests, and paper-ready summary tables.

This lightweight GitHub version intentionally excludes heavyweight artifacts such as frozen model binaries, full run-level CSVs, raw Pareto-front archives, and market-price files. Those files are listed in `manifest/external_artifacts.csv`.

## Project Purpose

The purpose of this project is to make the TEVC study reproducible and auditable. The package records the experimental protocol for synthetic portfolio instances, ECMADE-MOO theta selection, no-replicate selector training, final synthetic comparisons, ablation checks, and real-market rolling-window validation.

The central methodological question is whether a meta-designed, stability-aware ECMADE-MOO configuration protocol can improve robustness and Pareto-front quality without relying on the synthetic `replicate` identifier as a selector input.

## Main Conclusions

- The formal GitHub package is the **no-replicate** version: the selector feature list excludes `replicate`, while the official synthetic split remains 112 train / 48 validation / 32 test instances.
- In the 32-instance synthetic final comparison, `ExperimentC_NoReplicate_ECMADE_MOO` achieves the best mean stability-weighted rank among the five ECMADE-MOO configuration protocols (`mean_StabilityWeightedRank = 2.375`) and ties the best mean rank-based composite rank (`mean_RankBasedCompositeRank = 2.46875`).
- The synthetic no-replicate comparison is based on 960 runs for `ExperimentC_NoReplicate_ECMADE_MOO`, with all test-instance theta predictions and selections included in `selector/`.
- In the real-market configured ECMADE-MOO validation, protocol differences are statistically detectable for RankScore (`Friedman chi-square = 24.6966`, `p = 1.7868e-05`, `n = 33` universe-window units). However, the stability-aware protocol is not the best real-market protocol by overall RankScore in the included summary; this result should be interpreted as external robustness evidence rather than a dominance claim.

## Version

- Selector version: **no-replicate**
- Formal selector input policy: the `replicate` field is **not** used as a selector feature.
- Official split authority: `data/synthetic/split_manifest.csv`
- Synthetic split: 112 train / 48 validation / 32 test instances.

The `replicate` column may still appear in the synthetic instance manifest as a data-generation identifier. In this package, it must not appear in `selector/feature_columns_no_replicate.json`.

## Included Files

- Experiment configuration files in `configs/`.
- Official synthetic split manifest in `data/synthetic/split_manifest.csv`.
- L24 theta candidate table in `configs/theta_L24.csv`.
- Formal no-replicate selector feature columns and prediction tables in `selector/`.
- Label formula and RNG policy.
- Paper-ready summary tables.
- Statistical-test outputs that are small enough for GitHub.
- Small CSV samples under `samples/` for large artifacts.
- `manifest/external_artifacts.csv`, which lists every omitted large artifact and where it should be restored.

## Excluded Large Artifacts

Large artifacts are excluded from git and listed in:

```text
manifest/external_artifacts.csv
```

Before a full archival release, upload those files to Zenodo, OSF, GitHub Releases, or Git LFS and fill the `external_url` column.

## Quick Validation

```bash
python scripts/check_github_package.py
```

This script checks the GitHub package structure, confirms the official 112/48/32 split, and verifies that the formal selector feature list excludes `replicate`.

## Full Reproduction

The complete local package can be rebuilt from the parent workspace with:

```bash
python build_tevc_reproducibility_package.py
python build_tevc_github_package.py
```

For full reruns, restore external artifacts first, then use the stage wrappers copied from the full package or connect the original MATLAB/Python runners listed in `manifest/source_file_map.csv`.

## Recommended GitHub Workflow

1. Commit this folder as the public repository root.
2. Keep large outputs out of git.
3. Upload large artifacts separately and update `manifest/external_artifacts.csv`.
4. Add a release tag that matches the paper submission version.
"""


def github_readme_zh_tw() -> str:
    return """
# TEVC 可重現性套件 - GitHub 版本

這個資料夾是 TEVC 投資組合最佳化研究的 GitHub 友善版 **no-replicate** 可重現性套件。它提供審稿者可閱讀、可檢查的控制層，讓第三方能追蹤論文結果如何由實驗設定、selector 輸入、指標計算、統計檢定與論文表格產生。

這是輕量 GitHub 版本，因此不直接放入大型檔案，例如 frozen model binary、完整 run-level CSV、原始 Pareto front/archive 檔案與市場價格資料。這些大型檔案統一列在 `manifest/external_artifacts.csv`。

## 專案用意

本專案的目的，是讓 TEVC 研究的主要結果可以被第三方檢查與重現。套件整理了 synthetic portfolio instances、ECMADE-MOO theta 選擇、no-replicate selector 訓練、最終 synthetic comparison、消融檢查，以及真實市場 rolling-window validation 的實驗協定與輸出位置。

核心研究問題是：在不把 synthetic `replicate` 識別欄位作為 selector input 的前提下，meta-designed、stability-aware 的 ECMADE-MOO configuration protocol 是否仍能改善穩定性與 Pareto front 品質。

## 主要結論

- 這份 GitHub package 是正式 **no-replicate** 版本：selector feature list 不包含 `replicate`，而 synthetic 官方切分維持 112 train / 48 validation / 32 test instances。
- 在 32 個 test synthetic instances 的 final comparison 中，`ExperimentC_NoReplicate_ECMADE_MOO` 在五種 ECMADE-MOO configuration protocols 中取得最佳 mean stability-weighted rank（`mean_StabilityWeightedRank = 2.375`），並並列最佳 mean rank-based composite rank（`mean_RankBasedCompositeRank = 2.46875`）。
- synthetic no-replicate comparison 中，`ExperimentC_NoReplicate_ECMADE_MOO` 對應 960 runs；test instances 的 theta predictions 與 selected theta 已放在 `selector/`。
- 在 real-market configured ECMADE-MOO validation 中，不同 protocol 的 RankScore 差異具有統計顯著性（`Friedman chi-square = 24.6966`，`p = 1.7868e-05`，`n = 33` universe-window units）。但依目前 summary，stability-aware protocol 不是 real-market overall RankScore 最佳者，因此這部分應解讀為外部 robustness evidence，而不是全面優勢宣稱。

## 版本定義

- Selector 版本：**no-replicate**
- 正式 selector 輸入規則：`replicate` 欄位 **不作為 selector feature**
- 官方資料切分依據：`data/synthetic/split_manifest.csv`
- Synthetic split：112 train / 48 validation / 32 test instances

注意：`replicate` 欄位仍可出現在 synthetic instance manifest 中，因為它是資料生成與識別資訊；但在這個 no-replicate 版本中，它不可出現在 `selector/feature_columns_no_replicate.json`。

## 內含內容

- `configs/`：實驗設定檔
- `data/synthetic/split_manifest.csv`：官方 synthetic split manifest
- `configs/theta_L24.csv`：L24 的 24 組 theta candidate
- `selector/`：正式 no-replicate selector 的 feature columns 與 prediction tables
- label formula 與 RNG policy
- 論文用 summary tables
- 可放入 GitHub 的小型統計檢定結果
- `samples/`：大型 CSV 的小樣本
- `manifest/external_artifacts.csv`：列出未放入 GitHub 的大型檔案與還原位置

## 未放入 GitHub 的大型檔案

大型 artifacts 已排除於 git 之外，並列於：

```text
manifest/external_artifacts.csv
```

正式封存前，請將這些檔案上傳至 Zenodo、OSF、GitHub Releases 或 Git LFS，並補上 `external_url` 欄位。

## 快速檢查

```bash
python scripts/check_github_package.py
```

這支程式會檢查 GitHub 套件結構、確認官方 split 為 112/48/32，並確認正式 no-replicate selector feature list 不包含 `replicate`。

## 完整重現

完整本地 package 可由上層 workspace 重新建立：

```bash
python build_tevc_reproducibility_package.py
python build_tevc_github_package.py
```

若要執行完整重跑，請先還原 `manifest/external_artifacts.csv` 中列出的外部大型檔案，再使用完整 package 的 stage wrappers，或連接 `manifest/source_file_map.csv` 中列出的原始 MATLAB/Python runner。

## 建議 GitHub 使用流程

1. 將此資料夾內容作為 GitHub repository root。
2. 大型輸出檔不要放入 git。
3. 將大型 artifacts 另外上傳，並更新 `manifest/external_artifacts.csv`。
4. 依論文投稿版本建立 release tag。
"""


def gitignore_text() -> str:
    return """
# Python
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/

# Environments
.venv/
venv/
env/
.conda/

# Heavy reproducibility artifacts restored externally
artifacts/
raw/
raw_outputs/
**/*.joblib
**/*.pkl
**/*.mat
**/*.fig
**/*run_metrics.csv
**/*raw*.csv
**/*wealth_curve_run_level.csv

# Local/editor files
.DS_Store
Thumbs.db
.vscode/
.idea/
"""


def gitattributes_text() -> str:
    return """
* text=auto
*.md text eol=lf
*.py text eol=lf
*.yaml text eol=lf
*.yml text eol=lf
*.csv text eol=lf
*.json text eol=lf
"""


def license_text() -> str:
    return """
MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Note: this license applies to code in this GitHub package. Market data and
third-party software remain subject to their original licenses and terms.
"""


def citation_text() -> str:
    return """
cff-version: 1.2.0
title: TEVC Reproducibility Package
message: If you use this package, please cite the associated TEVC paper.
type: software
authors:
  - family-names: Chen
    given-names: Yi-Ting
date-released: 2026-07-31
license: MIT
"""


def check_script() -> str:
    return """
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED = [
    "README.md",
    "LICENSE",
    "environment.yml",
    "configs/common_experiment_config.yaml",
    "configs/algorithm_parameters.yaml",
    "configs/theta_L24.csv",
    "data/synthetic/split_manifest.csv",
    "labels/label_formula.md",
    "manifest/external_artifacts.csv",
    "manifest/supplementary_package_checklist.csv",
    "manifest/run_metric_schema.csv",
    "manifest/meta_feature_schema.csv",
    "system/software_environment.md",
    "selector/feature_columns_no_replicate.json",
    "selector/test_theta_predictions.csv",
    "selector/test_selected_theta.csv",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main() -> None:
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    if missing:
        fail("missing required GitHub files: " + ", ".join(missing))
    rows = read_csv(ROOT / "data/synthetic/split_manifest.csv")
    counts = Counter(row.get("split", "") for row in rows)
    expected = {"train": 112, "validation": 48, "test": 32}
    if counts != expected:
        fail(f"split mismatch: observed={dict(counts)}, expected={expected}")
    feature_columns = json.loads((ROOT / "selector/feature_columns_no_replicate.json").read_text(encoding="utf-8"))
    if "replicate" in json.dumps(feature_columns):
        fail("replicate appears in formal no-replicate feature columns")
    artifacts = read_csv(ROOT / "manifest/external_artifacts.csv")
    if not artifacts:
        fail("external artifact manifest is empty")
    checklist = read_csv(ROOT / "manifest/supplementary_package_checklist.csv")
    if not checklist:
        fail("supplementary package checklist is empty")
    print("OK: GitHub package structure is valid")
    print("OK: split manifest has 112/48/32 instances")
    print("OK: no-replicate selector feature list excludes replicate")
    print(f"OK: external artifacts listed: {len(artifacts)}")
    print(f"OK: supplementary checklist items listed: {len(checklist)}")


if __name__ == "__main__":
    main()
"""


def fetch_artifacts_script() -> str:
    return """
from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest" / "external_artifacts.csv"


def main() -> None:
    with MANIFEST.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    missing_urls = [row["package_path"] for row in rows if row.get("external_url", "TODO") in {"", "TODO"}]
    if missing_urls:
        print("External artifact URLs are not filled yet. Update manifest/external_artifacts.csv first.")
        for item in missing_urls[:20]:
            print(f"- {item}")
        raise SystemExit(1)
    print("Download implementation placeholder: use urllib/request or your preferred artifact manager after URLs are finalized.")


if __name__ == "__main__":
    main()
"""


def main() -> None:
    raise SystemExit(
        "DEPRECATED: this historical builder embeds superseded pre-20260811 tables. "
        "Use the repository package in place and run scripts/check_github_package.py."
    )
    if not FULL.exists():
        raise SystemExit("Build tevc_reproducibility_package first.")
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    write_text(OUT / "README.md", github_readme())
    write_text(OUT / "README.zh-TW.md", github_readme_zh_tw())
    write_text(OUT / ".gitignore", gitignore_text())
    write_text(OUT / ".gitattributes", gitattributes_text())
    write_text(OUT / "LICENSE", license_text())
    write_text(OUT / "CITATION.cff", citation_text())
    for rel in TEXT_FILES:
        src = FULL / rel
        if src.exists() and src.stat().st_size <= MAX_FULL_COPY_BYTES:
            copy_file(rel)
        elif src.exists() and src.suffix.lower() == ".csv":
            sample_csv(src, OUT / f"samples/{rel}.sample.csv")
    copy_code_files()
    write_csv(OUT / "manifest/external_artifacts.csv", artifact_rows())
    write_csv(OUT / "manifest/supplementary_package_checklist.csv", supplementary_checklist_rows())
    copy_file("manifest/source_file_map.csv")
    copy_file("manifest/reproducibility_checklist.csv")
    write_text(OUT / "system/software_environment.md", software_environment_text())
    write_text(OUT / "scripts/check_github_package.py", check_script())
    write_text(OUT / "scripts/fetch_artifacts.py", fetch_artifacts_script())
    write_text(
        OUT / "artifacts/README.md",
        "Place externally downloaded heavyweight artifacts here or restore them to the paths listed in manifest/external_artifacts.csv.",
    )
    write_text(
        OUT / "logs/README.md",
        "Place full run logs here for the OSF/Zenodo archival package. The lightweight GitHub package tracks them in manifest/external_artifacts.csv.",
    )
    write_text(
        OUT / "figures/README.md",
        "Place final paper figures here, or restore figures/paper_figures.zip from the URL recorded in manifest/external_artifacts.csv.",
    )
    write_text(
        OUT / "raw_pf/README.md",
        "Place raw Pareto-front CSV files here, or restore raw_pf/raw_pf_csv.zip from the URL recorded in manifest/external_artifacts.csv.",
    )
    print(f"GitHub package built at: {OUT}")


if __name__ == "__main__":
    main()
