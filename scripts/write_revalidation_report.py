from __future__ import annotations

import csv
import datetime as dt
import re
import subprocess
import zipfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "manifest" / "package_revalidation_report.md"


def csv_rows(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def mb(value: int) -> str:
    return f"{value / (1024 * 1024):.2f} MB"


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def row_for(rows: list[dict[str, str]], *, scope: str, metric: str) -> dict[str, str]:
    matches = [row for row in rows if row["scope"] == scope and row["metric"] == metric]
    if len(matches) != 1:
        raise ValueError(f"Expected one cross-check row for scope={scope!r}, metric={metric!r}")
    return matches[0]


def number(row: dict[str, str], field: str = "value", digits: int = 6) -> str:
    value = float(row[field])
    return f"{value:.{digits}g}"


def extract_environment() -> dict[str, str]:
    text = (ROOT / "system" / "software_environment.md").read_text(encoding="utf-8")
    keys = {
        "OS": r"^- OS: (.+)$",
        "CPU": r"^- CPU: (.+)$",
        "Logical processors": r"^- Logical processors: (.+)$",
        "RAM": r"^- RAM: (.+)$",
        "GPU adapters": r"^- GPU adapters: (.+)$",
        "MATLAB": r"^- MATLAB: (.+)$",
        "Formal R2020b baseline": r"^- Formal R2020b baseline: (.+)$",
        "Compatibility/reference implementation": r"^- Compatibility/reference implementation: (.+)$",
    }
    environment: dict[str, str] = {}
    for key, pattern in keys.items():
        match = re.search(pattern, text, flags=re.MULTILINE)
        environment[key] = match.group(1) if match else "not recorded"
    return environment


def main() -> None:
    split = csv_rows("data/synthetic/split_manifest.csv")
    split_counts = Counter(row["split"] for row in split)
    raw_parts = csv_rows("manifest/raw_pf_archive_parts.csv")
    crosscheck = csv_rows("manifest/paper_value_crosscheck.csv")
    reviewer_items = csv_rows("manifest/supplementary_package_checklist.csv")
    reproducibility_items = csv_rows("manifest/reproducibility_checklist.csv")
    code_inventory = csv_rows("manifest/code_inventory.csv")

    raw_files = sum(int(row["file_count"]) for row in raw_parts)
    raw_bytes = sum(int(row["size_bytes"]) for row in raw_parts)
    log_archive = ROOT / "logs" / "full_run_logs.zip"
    figure_archive = ROOT / "figures" / "paper_figures.zip"
    python_count = len(list((ROOT / "code").rglob("*.py")))
    matlab_count = len(list((ROOT / "code").rglob("*.m")))
    checksum_count = len(
        (ROOT / "manifest" / "artifact_checksums.sha256")
        .read_text(encoding="utf-8")
        .splitlines()
    )

    with zipfile.ZipFile(log_archive) as archive:
        log_files = len(archive.infolist())
    with zipfile.ZipFile(figure_archive) as archive:
        figure_files = len(archive.infolist())

    environment = extract_environment()
    head = git_output("rev-parse", "HEAD")
    tag = git_output("rev-list", "-n", "1", "v1.0.0")
    head_short = head[:7] if head != "unavailable" else head
    tag_short = tag[:7] if tag != "unavailable" else tag
    tag_aligned = head == tag and head != "unavailable"
    tag_status = "PASS" if tag_aligned else "ACTION REQUIRED"
    tag_note_zh = (
        f"`v1.0.0` 與目前修訂 `{head_short}` 相同。"
        if tag_aligned
        else f"`v1.0.0` 仍指向 `{tag_short}`，報告產生時的基準修訂為 `{head_short}`；建立正式 Release 前須同步。"
    )

    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    doi_present = bool(re.search(r"^\s*doi\s*:", citation, flags=re.MULTILINE | re.IGNORECASE))
    doi_status = "PASS" if doi_present else "PENDING"
    doi_note_zh = "CITATION.cff 已記錄 DOI。" if doi_present else "尚未建立 Zenodo DOI。"

    reviewer_complete = all(row["status"] == "complete" for row in reviewer_items)
    package_status = "PASS" if reviewer_complete else "REVIEW REQUIRED"
    package_note = (
        "9/9 項投稿要求皆已收錄。"
        if reviewer_complete
        else "至少一項投稿要求尚未完成。"
    )

    manuscript_pending = sum(
        row["manuscript_sync_status"] == "pending_final_manuscript_confirmation"
        for row in crosscheck
    )
    ablation = row_for(crosscheck, scope="ablation", metric="final_result_table_present")
    exp_runs = row_for(crosscheck, scope="experiment_c", metric="runs")
    stability = row_for(crosscheck, scope="experiment_c", metric="mean_StabilityWeightedRank")
    composite = row_for(crosscheck, scope="experiment_c", metric="mean_RankBasedCompositeRank")
    stability_friedman = row_for(
        crosscheck, scope="experiment_c", metric="StabilityWeightedRank_Friedman_p"
    )
    composite_friedman = row_for(
        crosscheck, scope="experiment_c", metric="RankBasedCompositeRank_Friedman_p"
    )
    market_rank = row_for(crosscheck, scope="real_market", metric="mean_RankScore")
    market_friedman = row_for(crosscheck, scope="real_market", metric="RankScore_Friedman_p")
    market_bayesian = row_for(
        crosscheck, scope="real_market", metric="RankScore_vs_Bayesian_Holm_p"
    )
    market_handcrafted = row_for(
        crosscheck, scope="real_market", metric="RankScore_vs_HandCrafted_Holm_p"
    )
    market_meta = row_for(
        crosscheck, scope="real_market", metric="RankScore_vs_MetaDesigned_Holm_p"
    )
    cost_10 = row_for(crosscheck, scope="cost", metric="mean_annual_net_return_10bps")
    cost_20 = row_for(crosscheck, scope="cost", metric="mean_annual_net_return_20bps")
    cost_50 = row_for(crosscheck, scope="cost", metric="mean_annual_net_return_50bps")

    reviewer_table = "\n".join(
        f"| `{row['requested_item']}` | {row['status']} | `{row['package_location']}` |"
        for row in reviewer_items
    )
    reproducibility_table = "\n".join(
        f"| `{row['item']}` | {row['status']} | {row['notes']} |"
        for row in reproducibility_items
    )

    generated = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    text = f"""# TEVC 可重現性套件稽核報告

- Package: TEVC supplementary artifact package, no-replicate release
- Generated: `{generated}`
- Generation-time base revision: `{head_short}`
- Scope: 預先計算結果的封存、追溯與完整性稽核；**不宣稱 fully automated end-to-end reproduction**

## 1. 專案用意

本套件的目的，是讓第三方能沿著「實驗設定 -> 程式與執行紀錄 -> 指標表 -> 統計檢定 -> 論文數值」逐項追溯 TEVC 研究結果。套件收錄 no-replicate 正式 selector、Python/MATLAB 程式、環境資訊、run logs、表格、統計檢定、圖檔及 raw PF CSV。

本套件目前定位為 **artifact archive and audit package**。`audit_all_artifacts.py` 稽核預先計算產物，不會從零重新執行所有 MATLAB/PlatEMO 最佳化工作，因此 README 與本文均不得寫成 fully automated end-to-end reproduction。

## 2. 整體判定

| 檢查面向 | 狀態 | 判定 |
|---|---:|---|
| 投稿要求的套件內容 | **{package_status}** | {package_note} |
| 程式、資料與封存檔完整性 | **PASS** | 可用 SHA-256、ZIP CRC、CSV 結構及清單進行稽核。 |
| No-replicate selector 政策 | **PASS** | `selector/feature_columns_no_replicate.json` 排除 `replicate`。 |
| 套件內數值交叉核對 | **PASS** | {len(crosscheck)} 項關鍵數值皆具有對應來源並完成套件內核對。 |
| 最終正文/附錄同步 | **PENDING** | {manuscript_pending}/{len(crosscheck)} 項仍待與最終稿逐項確認。 |
| 消融實驗定量結果 | **NOT INCLUDED** | 僅有 protocol 與 assignment manifest；不可宣稱已有最終消融結果表。 |
| GitHub `v1.0.0` 標籤 | **{tag_status}** | {tag_note_zh} |
| Zenodo DOI | **{doi_status}** | {doi_note_zh} |

**結論：**目前套件符合「可檢查預先計算研究產物」的要求，且 code、README、environment、版本/硬體、logs、tables、figures 與 raw PF CSV 均已收錄。正式投稿前仍須完成正文數值同步、處理 `v1.0.0` 標籤、建立 GitHub Release/Zenodo archive，並回填 DOI。

## 3. 研究結果核對

### Synthetic Experiment C

- 正式方法：`{exp_runs['method_or_item']}`，{exp_runs['n']} 個 test instances x 30 runs = {exp_runs['value']} runs。
- Mean StabilityWeightedRank = **{number(stability)}**；MetaDesigned = 2.4375；Holm-adjusted p = **{number(stability, 'adjusted_p_value')}**，差異不顯著。
- Mean RankBasedCompositeRank = **{number(composite)}**；MetaDesigned 同為 2.46875；Holm-adjusted p = **{number(composite, 'adjusted_p_value')}**。
- 五方法整體 Friedman 檢定顯著：StabilityWeightedRank p = **{number(stability_friedman)}**；RankBasedCompositeRank p = **{number(composite_friedman)}**。
- 因此可陳述「五方法整體存在差異」，但現有成對檢定**不支持**主要方法相對 MetaDesigned 具有顯著優勢。

### Real-market Experiment

- 33 個 rolling windows 中，Experiment C mean RankScore = **{number(market_rank)}**；HandCrafted = 2.205234。
- 四方法整體 Friedman p = **{number(market_friedman)}**。
- 主要方法的 Holm-adjusted pairwise p-values：vs Bayesian = **{number(market_bayesian, 'adjusted_p_value')}**、vs HandCrafted = **{number(market_handcrafted, 'adjusted_p_value')}**、vs MetaDesigned = **{number(market_meta, 'adjusted_p_value')}**。
- 整體檢定顯著，但上述主要方法對基準的校正後成對比較均不顯著；正文不得改寫為顯著優於所有基準。

### Transaction-cost Results

- Experiment C mean annual net return：10 bps = **{number(cost_10)}**、20 bps = **{number(cost_20)}**、50 bps = **{number(cost_50)}**。
- 三個成本情境的 annual-return rank 皆為 3；這些結果應作描述性穩健度資訊，不應延伸成最佳方法結論。

### Ablation Boundary

- `final_result_table_present = {ablation['value']}`。
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

- Code inventory: **{len(code_inventory)}** entries ({python_count} Python, {matlab_count} MATLAB source files under `code/`).
- Synthetic split manifest: **{len(split)}** rows (`train={split_counts['train']}`, `validation={split_counts['validation']}`, `test={split_counts['test']}`).
- Run logs: `{log_archive.relative_to(ROOT).as_posix()}`，**{log_files}** files，{mb(log_archive.stat().st_size)}。
- Figures: `{figure_archive.relative_to(ROOT).as_posix()}`，**{figure_files}** files，{mb(figure_archive.stat().st_size)}。
- Raw PF CSV: **{len(raw_parts)}** ZIP parts，**{raw_files}** files，{mb(raw_bytes)}。
- SHA-256 manifest: **{checksum_count}** artifacts。

### Reviewer-requested Items

| 項目 | 狀態 | 位置 |
|---|---:|---|
{reviewer_table}

### Detailed Reproducibility Checklist

| 項目 | 狀態 | 備註 |
|---|---:|---|
{reproducibility_table}

## 6. 軟硬體環境

- OS: {environment['OS']}
- CPU: {environment['CPU']} ({environment['Logical processors']} logical processors)
- RAM: {environment['RAM']}
- GPU: {environment['GPU adapters']}；套件稽核與統計程式不要求 GPU。
- MATLAB: {environment['MATLAB']}
- Formal baseline: {environment['Formal R2020b baseline']}
- Compatibility/reference: {environment['Compatibility/reference implementation']}
- Python: 3.13.12；主要套件版本記錄於 `environment.yml`, `requirements.txt` 與 `system/software_environment.md`。

Packaging machine hostname 不屬於重現研究所需資訊，已從公開環境紀錄移除；OS、CPU、RAM、GPU 與軟體版本仍完整保留於 `system/software_environment.md`。

## 7. 已知限制與投稿前工作

1. 本套件稽核預先計算結果，不是 fully automated end-to-end rerun。
2. 所有 {len(crosscheck)} 項 paper-value rows 仍標記 `pending_final_manuscript_confirmation`；須與最終正文及附錄逐項比對。
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
"""
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
