# TEVC 補充資料套件（No-Replicate）

[English](README.md)

本 repository 是 TEVC 投資組合最佳化研究的封存補充資料套件，提供實驗設定、研究程式、預先計算的 run-level 輸出、指標表、統計檢定、圖表、執行紀錄與原始 Pareto-front（PF）CSV，供第三方檢查論文結果。

## 套件範圍與用途

本 repository 支援 artifact 稽核與指定實驗重跑，**不是 fully automated end-to-end reproduction pipeline**。`audit_all_artifacts.py` 只會使用 `--audit-only` 逐階段呼叫套件驗證器；它不會啟動最佳化器、不會重新產生 labels、不會重新訓練 selector，也不會從零重建全部表格或論文。

預先計算的輸出是本套件的正式結果快照。完整重跑需要 MATLAB R2020b、指定 PlatEMO 版本、`code/` 中對應的 producer scripts，以及相當長的計算時間。部分歷史 runner 仍需要放在 repository-relative `external_data/` 下、保留原 worksheet 格式的 theta workbooks；供結果檢查使用的 frozen configuration 已包含於 `configs/theta_L24.csv`。各 artifact 的 repository-relative producer/provenance paths 記錄於 `manifest/source_file_map.csv`。

## 專案目的

本研究評估 meta-designed、stability-aware 的 ECMADE-MOO 組態協定，是否能在合成限制型投資組合問題與真實市場 rolling windows 中改善穩定性及 Pareto-front 品質。正式 synthetic selector 採 **no-replicate** 設定：`replicate` 僅保留為 instance provenance，不作為 selector 輸入特徵。

## 結果快照

下列數值皆連結至 `manifest/paper_value_crosscheck.csv` 所列的封存 CSV。正式投稿前，必須再與最終正文及附錄逐項同步。

- **Synthetic split：**112 個 training、48 個 validation、32 個 held-out test instances。
- **Experiment C synthetic comparison：**`ExperimentC_NoReplicate_ECMADE_MOO` 在 32 個 test instances 上共有 960 runs。其 mean stability-weighted rank 為 `2.375`，`MetaDesigned_ECMADE_MOO` 為 `2.4375`；兩者 Holm-adjusted pairwise p-value 為 `0.9091220347`，因此此 pairwise 差異不顯著。兩者的 mean rank-based composite rank 同為 `2.46875`，adjusted pairwise p-value 為 `1.0`。
- **Selector ablation：**套件目前包含 ablation protocol 與 assignment manifest，但沒有最終 ablation 結果或統計表，因此 README 不提出量化的 ablation 結論。
- **Real market：**封存表使用的方法 ID 為 `ExperimentC_StabilityAware_ECMADE_MOO`。在 33 個 universe-window units 上，RankScore Friedman test 為 `chi-square = 24.6965944272`、`p = 1.7868365549e-05`。Experiment C 的 mean RankScore 為 `2.5688705234`；最低的 mean RankScore 是 `HandCrafted_ECMADE_MOO` 的 `2.2052341598`。Experiment C 對 Bayesian、HandCrafted、MetaDesigned 的 RankScore Holm-adjusted p-values 依序為 `1.0`、`1.0`、`0.5125780637`。
- **Transaction-cost sensitivity：**在 10、20、50 bps 下，Experiment C 的 mean annual net return 分別為 `0.3219427032`、`0.3207092913`、`0.3170134141`，三種情境的 annual-return rank 都是第三。這些是描述性敏感度結果，不是 adjusted significance 結論。

## 套件內容

| 要求 | 位置 |
| --- | --- |
| 研究程式 | `code/`、`manifest/code_inventory.csv` |
| 中英文 README | `README.md`、`README.zh-TW.md` |
| Python 環境 | `environment.yml`、`requirements.txt` |
| MATLAB、PlatEMO、CPU、GPU、OS | `system/software_environment.md` |
| 實驗設定 | `configs/` |
| 正式 split 與 selector artifacts | `data/synthetic/`、`selector/`、`labels/` |
| Run-level tables | `labels/`、`experiments/`、`real_market/` |
| Run logs | `logs/full_run_logs.zip` |
| Tables 與統計檢定 | `paper_outputs/`、`experiments/`、`real_market/` |
| Figures | `figures/`、`figures/paper_figures.zip` |
| Raw PF/objective/archive CSV | `raw_pf/raw_pf_csv_part*.zip` |
| 完整性雜湊 | `manifest/artifact_checksums.sha256` |
| 論文數值核對表 | `manifest/paper_value_crosscheck.csv` |

ZIP archives 與 frozen selector 使用 Git LFS 儲存。Clone 前請先安裝 Git LFS：

```bash
git lfs install
git clone https://github.com/ating0912/tevc_supplementary_osf_zenodo.git
cd tevc_supplementary_osf_zenodo
git lfs pull
```

## 執行環境

```bash
conda env create -f environment.yml
conda activate tevc-reproducibility
```

封存環境為 MATLAB 9.9.0.2037887（R2020b）Update 8。PlatEMO v2.9.0 是 R2020b baseline implementation；PlatEMO v4.3 用於 compatibility 與 reference-PF checks。完整軟硬體資訊請見 `system/software_environment.md`。

## 稽核封存 Artifacts

```bash
python scripts/fetch_artifacts.py
python scripts/check_github_package.py
python scripts/check_github_package.py --full-zip-test
python scripts/check_paper_values.py
python scripts/check_no_personal_paths.py
python audit_all_artifacts.py
```

以上指令只驗證封存套件，不代表 end-to-end experimental rerun。驗證器會檢查必要檔案、artifact 大小、SHA-256、ZIP 可讀性、112/48/32 split、no-replicate feature policy 與主要 CSV 形狀；`--full-zip-test` 會額外執行完整 archive CRC 檢查。

## 可重現性追溯

1. 實驗設定在 `configs/`，RNG policy 在 `manifest/rng_policy.md`。
2. 正式資料分割在 `data/synthetic/split_manifest.csv`。
3. Producer scripts 在 `code/`，repository-relative provenance 在 `manifest/source_file_map.csv`。
4. 預先計算的 metrics 在 `labels/`、`experiments/`、`real_market/`，logs 在 `logs/`。
5. Friedman 與 Wilcoxon-Holm 等統計表放在各實驗輸出旁。
6. 論文表格、figures 與 raw PF 分別在 `paper_outputs/`、`figures/`、`raw_pf/`。

## 資料使用

Synthetic instances、derived metrics 與 raw optimization fronts 可供研究驗證。Raw market prices 因資料供應條款可能受限，未直接重新散布；套件包含市場下載程式、設定、run archive 中的 ticker/universe metadata 與 derived results，讓有資料使用權限者重建輸入。

## 引用與封存發布

本 repository 尚未取得 Zenodo DOI。DOI 正式產生前，請引用 `CITATION.cff` 所記錄的 GitHub 版本或 tag，不要使用假的 placeholder DOI。正式投稿時，應建立 GitHub `v1.0.0` release、由 Zenodo 封存該 release，再把取得的 DOI 同步更新到 `README.md`、`README.zh-TW.md`、`CITATION.cff` 與論文。詳細步驟見 `docs/zenodo_release_checklist.md`。
