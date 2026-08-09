# TEVC 可重現性套件稽核報告

- Package: TEVC supplementary artifact package, no-replicate release
- Generated: `2026-08-09T21:59:15+08:00`
- Generation-time base revision: `1ff354d`
- Scope: 預先計算結果的封存、追溯與完整性稽核；**不宣稱 fully automated end-to-end reproduction**

## 1. 專案用意

本套件的目的，是讓第三方能沿著「實驗設定 -> 程式與執行紀錄 -> 指標表 -> 統計檢定 -> 論文數值」逐項追溯 TEVC 研究結果。套件收錄 no-replicate 正式 selector、Python/MATLAB 程式、環境資訊、run logs、表格、統計檢定、圖檔及 raw PF CSV。

本套件目前定位為 **artifact archive and audit package**。`audit_all_artifacts.py` 稽核預先計算產物，不會從零重新執行所有 MATLAB/PlatEMO 最佳化工作，因此 README 與本文均不得寫成 fully automated end-to-end reproduction。

## 2. 整體判定

| 檢查面向 | 狀態 | 判定 |
|---|---:|---|
| 投稿要求的套件內容 | **PASS** | 9/9 項投稿要求皆已收錄。 |
| 程式、資料與封存檔完整性 | **PASS** | 可用 SHA-256、ZIP CRC、CSV 結構及清單進行稽核。 |
| No-replicate selector 政策 | **PASS** | `selector/feature_columns_no_replicate.json` 排除 `replicate`。 |
| 套件內數值交叉核對 | **PASS** | 17 項關鍵數值皆具有對應來源並完成套件內核對。 |
| 最終正文/附錄同步 | **PENDING** | 17/17 項仍待與最終稿逐項確認。 |
| 消融實驗定量結果 | **NOT INCLUDED** | 僅有 protocol 與 assignment manifest；不可宣稱已有最終消融結果表。 |
| GitHub `v1.0.0` 標籤 | **ACTION REQUIRED** | `v1.0.0` 仍指向 `5e31996`，報告產生時的基準修訂為 `1ff354d`；建立正式 Release 前須同步。 |
| Zenodo DOI | **PENDING** | 尚未建立 Zenodo DOI。 |

**結論：**目前套件符合「可檢查預先計算研究產物」的要求，且 code、README、environment、版本/硬體、logs、tables、figures 與 raw PF CSV 均已收錄。正式投稿前仍須完成正文數值同步、處理 `v1.0.0` 標籤、建立 GitHub Release/Zenodo archive，並回填 DOI。

## 3. 研究結果核對

### Synthetic Experiment C

- 正式方法：`ExperimentC_NoReplicate_ECMADE_MOO`，32 個 test instances x 30 runs = 960 runs。
- Mean StabilityWeightedRank = **2.375**；MetaDesigned = 2.4375；Holm-adjusted p = **0.909122**，差異不顯著。
- Mean RankBasedCompositeRank = **2.46875**；MetaDesigned 同為 2.46875；Holm-adjusted p = **1**。
- 五方法整體 Friedman 檢定顯著：StabilityWeightedRank p = **0.000505106**；RankBasedCompositeRank p = **0.00443926**。
- 因此可陳述「五方法整體存在差異」，但現有成對檢定**不支持**主要方法相對 MetaDesigned 具有顯著優勢。

### Real-market Experiment

- 33 個 rolling windows 中，Experiment C mean RankScore = **2.56887**；HandCrafted = 2.205234。
- 四方法整體 Friedman p = **1.78684e-05**。
- 主要方法的 Holm-adjusted pairwise p-values：vs Bayesian = **1**、vs HandCrafted = **1**、vs MetaDesigned = **0.512578**。
- 整體檢定顯著，但上述主要方法對基準的校正後成對比較均不顯著；正文不得改寫為顯著優於所有基準。

### Transaction-cost Results

- Experiment C mean annual net return：10 bps = **0.321943**、20 bps = **0.320709**、50 bps = **0.317013**。
- 三個成本情境的 annual-return rank 皆為 3；這些結果應作描述性穩健度資訊，不應延伸成最佳方法結論。

### Ablation Boundary

- `final_result_table_present = false`。
- `experiments/ablation/` 只提供 protocol 與 assignment manifest。若正文包含消融定量結論，必須補入實際結果表與統計檢定，否則應刪除該定量主張。

完整來源、row key、樣本數與 p-value 位於 `manifest/paper_value_crosscheck.csv`。

## 4. 可追溯鏈

| 階段 | 主要產物 | 可核對內容 |
|---|---|---|
| 實驗設定 | `configs/`, `manifest/rng_policy.md`, `data/synthetic/split_manifest.csv` | L24 theta、seed、112/48/32 split、no-replicate 政策 |
| 執行與程式 | `code/`, `manifest/code_inventory.csv`, `logs/full_run_logs.zip` | Python/MATLAB runners、來源清單、實際 run logs |
| 指標計算 | `labels/`, `experiments/`, `real_market/` | run-level HV、IGD、PF overlap/drift、rank/composite metrics |
| 統計檢定 | experiment/market CSV tables | Friedman 與 Wilcoxon-Holm 輸入及輸出 |
| 論文輸出 | `paper_outputs/`, `figures/`, `manifest/paper_value_crosscheck.csv` | tables、figures 與正文關鍵數值交叉核對 |
| 完整性 | `manifest/artifact_checksums.sha256`, `scripts/check_github_package.py` | SHA-256、ZIP CRC、必要檔案及 CSV 結構 |

## 5. 套件內容

- Code inventory: **363** entries (140 Python, 181 MATLAB source files under `code/`).
- Synthetic split manifest: **192** rows (`train=112`, `validation=48`, `test=32`).
- Run logs: `logs/full_run_logs.zip`，**5738** files，15.19 MB。
- Figures: `figures/paper_figures.zip`，**64** files，12.07 MB。
- Raw PF CSV: **6** ZIP parts，**68832** files，832.34 MB。
- SHA-256 manifest: **25** artifacts。

### Reviewer-requested Items

| 項目 | 狀態 | 位置 |
|---|---:|---|
| `code` | complete | `code/ and manifest/code_inventory.csv` |
| `README` | complete | `README.md and README.zh-TW.md` |
| `environment.yml` | complete | `environment.yml and requirements.txt` |
| `MATLAB/PlatEMO version` | complete | `system/software_environment.md` |
| `CPU/GPU/OS` | complete | `system/software_environment.md` |
| `run logs` | complete | `logs/full_run_logs.zip` |
| `tables` | complete | `labels/ experiments/ real_market/ and paper_outputs/` |
| `figures` | complete | `figures/ and figures/paper_figures.zip` |
| `raw PF csv` | complete | `raw_pf/raw_pf_csv_part*.zip` |

### Detailed Reproducibility Checklist

| 項目 | 狀態 | 備註 |
|---|---:|---|
| `source_code` | complete | Research sources are in code/; third-party PlatEMO releases are identified but not relicensed. |
| `environment` | complete | See environment.yml requirements.txt system/software_environment.md and LICENSES_THIRD_PARTY.md. |
| `synthetic_instances` | complete_by_generation | Split manifest and deterministic generator are included. |
| `split_manifest` | complete | data/synthetic/split_manifest.csv contains 112/48/32 instances. |
| `theta_L24` | complete | configs/theta_L24.csv |
| `rng_policy` | complete | manifest/rng_policy.md and split manifest seed fields |
| `no_replicate_features` | complete | selector/feature_columns_no_replicate.json excludes replicate. |
| `labels` | complete | Formal and retained legacy label tables are included in labels/. |
| `frozen_selector` | complete | selector/selector_no_replicate.joblib is stored with Git LFS. |
| `test_predictions` | complete | selector/test_theta_predictions.csv and selector/test_selected_theta.csv |
| `run_level_metrics` | complete | Run-level CSV files are included under experiments/ labels/ and real_market/. |
| `statistical_tests` | complete | Friedman and Wilcoxon-Holm outputs are included beside experiment summaries. |
| `real_market` | complete_with_data_rights_note | Derived results and download code are included; raw provider prices are excluded under DATA_USE_STATEMENT.md. |
| `paper_outputs` | complete | Paper tables figures archives and plotting code are included. |
| `integrity` | complete | manifest/artifact_checksums.sha256 and scripts/check_github_package.py |
| `readme_license` | complete | README files, CITATION.cff, LICENSE, DATA_USE_STATEMENT.md, and LICENSES_THIRD_PARTY.md |

## 6. 軟硬體環境

- OS: Microsoft Windows NT 10.0.26200.0 (Windows 11 generation), 64-bit
- CPU: Intel64 Family 6 Model 186 Stepping 2, GenuineIntel (20 logical processors)
- RAM: 15.65 GB
- GPU: NVIDIA GeForce RTX 4050 Laptop GPU and Intel Iris Xe Graphics；套件稽核與統計程式不要求 GPU。
- MATLAB: 9.9.0.2037887 (R2020b) Update 8
- Formal baseline: PlatEMO v2.9.0
- Compatibility/reference: PlatEMO v4.3
- Python: 3.13.12；主要套件版本記錄於 `environment.yml`, `requirements.txt` 與 `system/software_environment.md`。

Packaging machine hostname 不屬於重現研究所需資訊，已從公開環境紀錄移除；OS、CPU、RAM、GPU 與軟體版本仍完整保留於 `system/software_environment.md`。

## 7. 已知限制與投稿前工作

1. 本套件稽核預先計算結果，不是 fully automated end-to-end rerun。
2. 所有 17 項 paper-value rows 仍標記 `pending_final_manuscript_confirmation`；須與最終正文及附錄逐項比對。
3. 消融實驗沒有最終定量結果表，只能主張 protocol/assignment 可稽核。
4. Raw provider market prices 因資料權利未重新散布；套件提供衍生結果與下載程式，詳見 `DATA_USE_STATEMENT.md`。
5. 部分歷史 Excel inputs 預期由使用者放入 `external_data/`；這不影響已封存產物稽核，但會影響完整歷史流程重跑。
6. `v1.0.0` 目前未對齊最新修訂；正式 Release 前需重新建立或改用新版本號，並確認 Git LFS 檔案進入 release archive。
7. Zenodo DOI 尚未建立；建立 archive 後須同步更新 README、`CITATION.cff`、`.zenodo.json` 與論文。

## 8. 驗證指令

```powershell
python scripts/check_github_package.py --full-zip-test
python scripts/check_paper_values.py
python scripts/check_no_personal_paths.py
python audit_all_artifacts.py
git lfs fsck
```

## 9. 本次重新整理的更新

1. 將單一 **PASS** 改為「套件完整性、正文同步、消融結果、Release/DOI」分層狀態，避免過度宣稱。
2. 新增專案用意、可主張的結論，以及 synthetic、real-market、cost 的精確數值與統計解讀。
3. 明確標示 `audit_all_artifacts.py` 只稽核預先計算結果。
4. 新增從實驗設定到論文輸出的可追溯鏈與必要套件逐項位置。
5. 把消融定量表缺漏、外部資料權利、歷史 Excel inputs、正文同步列為已知限制。
6. 自動比較目前 Git revision 與 `v1.0.0`，並檢查 Zenodo DOI 是否已回填。
7. 報告不顯示個人電腦 hostname；公開 producer paths 維持 repository-relative。

## English Summary

This package is a **precomputed-artifact archive and audit package**, not a fully automated end-to-end reproduction. It contains the requested code, bilingual READMEs, environment specifications, MATLAB/PlatEMO and hardware records, run logs, tables, figures, and raw PF CSV archives. Artifact completeness and package-internal numerical cross-checks pass.

The current evidence supports significant omnibus differences among methods, but the reported Holm-adjusted pairwise tests do not establish that the primary Experiment C method significantly outperforms the named baselines. Quantitative ablation results are not included. Before formal submission, the authors must confirm all paper values against the final manuscript, align the release tag with the audited revision, create the GitHub/Zenodo release, and add the DOI to all citation metadata.
