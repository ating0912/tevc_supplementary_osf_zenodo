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
