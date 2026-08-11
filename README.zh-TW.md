# TEVC 補充資料套件（No-Replicate）

[English](README.md)

本 repository 是 TEVC 投資組合最佳化研究的 GitHub 預發行補充資料套件，並預定於內容凍結後封存至 OSF 與 Zenodo。套件保存實驗設定、完整研究程式、預先計算的 run-level 輸出、統計檢定、論文表格、圖、執行紀錄與原始 Pareto front（PF）CSV，供第三方核對研究證據。

## 1. 專案用意與主要結論

本研究評估 meta-designed 與 stability-aware ECMADE-MOO 設定流程在合成限制式投資組合、rolling real-market windows 與 MOKP transfer tests 上的表現。正式合成 selector 為 **no-replicate** 版本；`replicate` 只保留作為來源追蹤欄位，不作為 selector 輸入。

以 `20260811` 正文及附錄正式表格為最高判定依據，結果顯示部分 omnibus endpoints 存在方法差異，但不能概括宣稱 stability-aware 方法在所有指標都較佳。Experiment C 的 StabilityWeightedRank 兩兩比較經 Holm 校正後皆不顯著。四設定 real-market protocol 中，其年化淨報酬顯著優於 MetaDesigned、年化波動顯著劣於 HandCrafted、runtime 較快，但多項 PF 品質指標較差。由 rank 推導的分數僅作描述性使用。

## 2. 套件範圍與用途

本 repository 支援 artifact inspection 與 targeted reruns，**不是 fully automated end-to-end reproduction pipeline**。`audit_all_artifacts.py` 以 `--audit-only` 呼叫各階段驗證器，不會啟動所有 optimizer、重新產生 labels、重訓 selector、重建全部表格或自動產生論文。現行與歷史 producer 的角色見 `manifest/code_authority.csv`。

`code/` 包含可用於指定實驗的 MATLAB/Python runners。完整 optimizer 重跑需要 MATLAB R2020b、記錄的 PlatEMO 版本、合法取得的原始資料與大量運算時間。現行 CSV 構成本預發行版本的證據快照；正式投稿版本將於 `v1.0.0` release 時凍結。producer/provenance 路徑見 `manifest/source_file_map.csv`；正式與 audit-only 檔案的界線見 `manifest/artifact_authority.csv`。

## 3. 資料切分與正式 Selector

- 合成資料切分：112 training、48 validation、32 held-out test instances。
- 正式模型：`selector/selector_no_replicate.joblib`。
- 特徵政策：`selector/feature_columns_no_replicate.json` 不含 `replicate` 輸入。
- 正式 test predictions 與 theta assignments 位於 `selector/`。

## 4. Experiment A

Experiment A 的 run-level metrics、instance-method summaries 與 statistical tests 位於 `experiments/experiment_a/`；論文表位於 `paper_outputs/table_experiment_a.csv`。這些是正式 artifact inventory 的一部分，不以 RankScore-only 推論取代。

## 5. Experiments B 與 C

修正後五方法 Experiment C 使用 32 個 test groups，每個方法 960 runs。MetaDesigned 的平均 J-stability 為 `0.6963`、平均 StabilityWeightedRank 為 `2.1875`；stability-aware ECMADE-MOO 的平均 J-stability 為 `0.6211`、平均 StabilityWeightedRank 為 `2.7813`、平均 Diversity 為 `0.8299`。

J-stability/StabilityWeightedRank 的 Friedman 結果為 `chi-square = 18.8000`、`p = 0.000860`。stability-aware ECMADE-MOO 對 HandCrafted、RandomConfig、BayesianConfig、MetaDesigned 的 Holm-adjusted p-value 分別為 `0.8086`、`0.1205`、`1.0000`、`0.2750`，皆未達 0.05 顯著水準。正式表位於 `experiments/experiment_bc/`。

## 6. Selector Final-Test Ablation

四個 variants 為 FullSelector、NoInstanceFeatures、NoThetaFeatures、RandomizedLabels；每個 variant 使用 32 groups、960 runs。其 mean RankScore 分別為 `2.6042`、`2.8125`、`2.3854`、`2.1979`。NoThetaFeatures 的 overall RankScore 為 `2.1667`，FullSelector 為 `3.0000`。

RankScore Friedman 結果為 `chi-square = 19.3956`、`p = 0.000226`。FullSelector 對 NoInstanceFeatures、NoThetaFeatures、RandomizedLabels 的 Holm-adjusted p-value 分別為 `0.1918`、`1.0000`、`1.0000`，皆不顯著。assignments、run completeness、run metrics 與統計表位於 `experiments/selector_ablation/`。

## 7. Validation Feature 與 Label Ablations

Feature-group 與 label-objective validation ablation 程式收錄於 `code/`。其封存輸出屬支援性分析；第 6 節的 final-test selector ablation 才是 `20260811` cross-check 採用的正式 held-out selector 比較。

## 8. Mechanism 與 Parameter Ablations

機制與參數消融的產生程式及封存輸出位於 `code/`、`experiments/` 與 `artifacts/`。歷史 RankScore 推論只保留在 `artifacts/deprecated_or_audit_only/`，不作為正式論文證據。

## 9. 六演算法 Real-Market 比較

六演算法研究含 33 個 rolling windows。10 bps 下，MOEAD mean annual net return 為 `34.81%`；GDE3 mean Sharpe 為 `1.286`、Sortino 為 `2.122`；ECMADE-MOO mean annual volatility 為 `26.11%`、CVaR95 loss 為 `3.38%`。NSGA-II 的 CrossWindowOverallRank `2.167` 僅為描述值。

原始財務 endpoints 的 Friedman p-value 範圍為 `0.1112` 至 `0.8115`，皆未達 0.05。`RankScore`、`WindowRank` 與 `CrossWindowOverallRank` 不作推論。正式 endpoint tests 位於 `real_market/six_algorithm_endpoint_*.csv`。

## 10. 四設定 Real-Market Protocol

在 33 個 paired windows 中，stability-aware ECMADE-MOO 的年化淨報酬顯著高於 MetaDesigned（`26/0/7`，Holm `p = 0.034893`），年化波動顯著劣於 HandCrafted（`12/0/21`，Holm `p = 0.022167`）。Sharpe、Sortino、maximum drawdown、CVaR95、turnover 與其他原始財務比較經 Holm 校正後皆不顯著。

stability-aware 方法比三個 baselines 快；正式 endpoint 表亦記錄其 PF size、HV、IGD 與 PF overlap 的劣勢。16 個 endpoints 與 multiplicity scope 詳見 `real_market/configuration_protocol_endpoint_pairwise_wilcoxon_holm.csv`。

## 11. Transaction-Cost Sensitivity

成本敏感度分析是在固定 portfolio paths 上重新計價，不會重跑 optimizer，也不是 cost-aware reoptimization。交易成本由 10 提高至 50 bps，mean annual net return 約下降 0.48 至 0.49 個百分點：MOEAD `0.3481 -> 0.3432`、NSGA-II `0.3369 -> 0.3320`、ECMADE-MOO `0.3271 -> 0.3222`。所有 scenarios 的順序皆為 MOEAD、NSGA-II、GDE3、A-MPMO、ECMADE-MOO、SPEA2。此結果僅為描述性敏感度證據。

## 12. MOKP Transfer Validation

MOKP 正式推論只使用 HV、IGD、PF overlap、PF drift、Diversity 與 Runtime。MOKP rank-derived scores 僅為描述值。正式 Friedman 與 Wilcoxon-Holm 檔案位於 `experiments/mokp/`。

## 13. 套件清單與稽核

| 要求 | 位置 |
| --- | --- |
| 完整研究程式 | `code/`、`manifest/code_inventory.csv` |
| 中英文說明 | `README.md`、`README.zh-TW.md` |
| Python 環境 | `environment.yml`、`requirements.txt` |
| MATLAB/PlatEMO/CPU/GPU/OS | `system/software_environment.md` |
| 設定與 RNG policy | `configs/`、`manifest/rng_policy.md` |
| Run-level 輸出與統計 | `labels/`、`experiments/`、`real_market/` |
| Run logs | `logs/full_run_logs.zip` |
| Tables 與 figures | `paper_outputs/`、`figures/` |
| Raw PF CSV archives | `raw_pf/raw_pf_csv_part*.zip` |
| Provenance、authority 與 checksums | `manifest/` |

大型 archives 與 frozen selector 使用 Git LFS。clone 後執行：

```bash
git lfs install
git lfs pull
conda env create -f environment.yml
conda activate tevc-reproducibility
python scripts/check_github_package.py
python scripts/check_paper_values.py
python scripts/check_no_personal_paths.py
python audit_all_artifacts.py
```

以上命令只稽核封存快照，不是 end-to-end experimental rerun。`--full-zip-test` 會額外執行所有 ZIP members 的 CRC 檢查。

## 資料使用與發行狀態

合成 instances、derived metrics 與 raw optimization fronts 可供研究核對。若 market price provider 條款限制再散布，原始價格不納入套件；詳見 `DATA_USE_STATEMENT.md`。

目前 metadata 為 `0.9.0-pre-release`，尚未建立 Zenodo DOI 或最終 `v1.0.0` archive。待正文、CSV cross-check 與 Git LFS release archive 凍結後，再建立 GitHub release 並透過 Zenodo 封存，最後同步更新兩份 README、`CITATION.cff`、`.zenodo.json` 與論文 DOI。
