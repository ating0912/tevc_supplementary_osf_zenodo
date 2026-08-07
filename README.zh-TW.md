# TEVC 完整補充資料與可重現性套件（No-Replicate）

[English](README.md)

本 repository 是 TEVC 投資組合最佳化研究的完整 supplementary/reproducibility package，將實驗設定、可執行研究程式、run-level 輸出、指標表格、統計檢定、論文圖表與原始 Pareto front（PF）CSV 串接在同一份可稽核套件中。

## 專案用意

本研究檢驗 meta-designed、stability-aware 的 ECMADE-MOO 組態協定，是否能在合成限制型投資組合問題與真實市場 rolling windows 中提升穩定性及 Pareto-front 品質。正式 selector 採用 **no-replicate** 版本：`replicate` 僅保留作為合成 instance 的來源識別，不會作為 selector 輸入特徵。

## 主要結論

- 正式合成資料切分為 112 個 training、48 個 validation、32 個 held-out test instances。
- 在 held-out synthetic comparison 中，`ExperimentC_NoReplicate_ECMADE_MOO` 在五種組態協定中得到最佳平均 stability-weighted rank（`2.375`），並列最佳平均 rank-based composite rank（`2.46875`）。
- 合成 no-replicate 比較包含 `ExperimentC_NoReplicate_ECMADE_MOO` 的 960 次 runs；test instance 的 theta 預測與最終選擇均放在 `selector/`。
- 真實市場 RankScore 的協定差異達統計顯著（`Friedman chi-square = 24.6966`、`p = 1.7868e-05`、`n = 33`）。但 stability-aware 協定並非 overall real-market RankScore 的最佳方法，因此此結果應解讀為外部穩健性證據，而不是全面優越性主張。

## 套件內容

| Reviewer 要求 | 套件位置 |
| --- | --- |
| 研究程式碼 | `code/`、`manifest/code_inventory.csv` |
| 中英文 README | `README.md`、`README.zh-TW.md` |
| Python 環境 | `environment.yml`、`requirements.txt` |
| MATLAB、PlatEMO、CPU、GPU、OS | `system/software_environment.md` |
| 實驗設定 | `configs/` |
| 正式 split 與 selector 輸入 | `data/synthetic/`、`selector/`、`labels/` |
| 完整 run-level tables | `labels/`、`experiments/`、`real_market/` |
| 執行 logs | `logs/full_run_logs.zip` |
| 論文表格與統計檢定 | `paper_outputs/`、`experiments/`、`real_market/` |
| 論文 figures | `figures/`、`figures/paper_figures.zip` |
| 原始 PF/objective/archive CSV | `raw_pf/raw_pf_csv_part*.zip` |
| 完整性雜湊 | `manifest/artifact_checksums.sha256` |

ZIP archives 與 frozen selector 使用 Git LFS 儲存。raw PF 資料拆成數個可獨立驗證的 ZIP parts，以避免超過通用單一 LFS object 限制。下載前請先安裝 Git LFS：

```bash
git lfs install
git clone https://github.com/ating0912/tevc_supplementary_osf_zenodo.git
cd tevc_supplementary_osf_zenodo
git lfs pull
```

## 建立環境

```bash
conda env create -f environment.yml
conda activate tevc-reproducibility
```

記錄的 MATLAB 環境為 MATLAB 9.9.0.2037887（R2020b）Update 8。PlatEMO v2.9.0 是 R2020b baseline 實作；PlatEMO v4.3 用於相容性及 reference-PF 檢查。完整軟硬體資訊請見 `system/software_environment.md`。

## 驗證套件

```bash
python scripts/fetch_artifacts.py
python scripts/check_github_package.py
python scripts/check_github_package.py --full-zip-test
```

驗證器會檢查必要檔案、artifact 大小與 SHA-256、ZIP 可讀性、112/48/32 split、no-replicate 特徵政策及主要 CSV 形狀。`--full-zip-test` 會額外對 archive 中每個成員執行 CRC 檢查，可能需要數分鐘。

## 可重現流程

1. `configs/` 固定實驗設定，`manifest/rng_policy.md` 記錄 RNG 政策。
2. `data/synthetic/split_manifest.csv` 記錄正式資料切分；`code/generate_synthetic_portfolio_instances.py` 提供確定性的合成 instance 產生程式。
3. MATLAB/Python runners 位於 `code/`；`manifest/source_file_map.csv` 對應各輸出與產生程式。
4. `labels/`、`experiments/`、`real_market/` 收錄 run-level metrics，原始執行記錄封存在 `logs/`。
5. 各實驗資料夾包含 Friedman、Wilcoxon-Holm 等統計檢定輸出。
6. `paper_outputs/` 收錄論文表格，`figures/` 與 `raw_pf/` 收錄圖檔及原始 PF CSV archive。

套件中的 precomputed outputs 是論文結果的固定快照。完整重新執行 optimizer 需要 MATLAB R2020b 與上述 PlatEMO 版本，執行時間會依硬體能力而異，且可能相當長。

## 資料使用說明

合成 instances、衍生指標與原始最佳化 fronts 可供研究驗證使用。由於資料供應商條款可能限制再散布，本套件不直接提供原始市場價格；套件已提供 `code/download_market_universe_prices.py`、市場設定、run archive 中的 ticker/universe metadata 與衍生結果，讓具有合法存取權限的使用者重建市場輸入。

## 引用與版本

引用本套件時請使用 `CITATION.cff`。`v1.0.0` 是預定對應 TEVC supplementary submission 的固定版本；完成 Zenodo 封存後，可再將 DOI 補入 citation 與 README。
