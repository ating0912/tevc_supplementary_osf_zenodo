from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs" / "tevc_adaptive_exchange_significance_20260722"
C_DETAIL = ROOT / "outputs" / "tevc_ablation_6_20260717" / "theta_factor_group_detail.csv"
C_EAF = ROOT / "outputs" / "tevc_ablation_6_20260717" / "theta_factor_group_eaf_detail.csv"
DIRECT = (
    ROOT
    / "p0_lite_outputs"
    / "tevc_pdf_direct_ablation_full_20260717"
    / "pdf_direct_ablation_summary"
    / "pdf_direct_ablation_instance_ranked.csv"
)
DIRECT_EAF = (
    ROOT
    / "p0_lite_outputs"
    / "tevc_p0_requirement_tables_20260717"
    / "tevc_p0_instance_eaf_band_width.csv"
)


def average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    pos = 0
    while pos < len(values):
        end = pos + 1
        while end < len(values) and values[order[end]] == values[order[pos]]:
            end += 1
        avg = (pos + 1 + end) / 2.0
        ranks[order[pos:end]] = avg
        pos = end
    return ranks


def wilcoxon_exact_paired(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    diff = np.asarray(x, dtype=float) - np.asarray(y, dtype=float)
    diff = diff[np.isfinite(diff)]
    diff = diff[diff != 0]
    n = len(diff)
    if n == 0:
        return 0.0, 1.0
    ranks = average_ranks(np.abs(diff))
    w_plus = float(ranks[diff > 0].sum())
    total = float(ranks.sum())
    obs = min(w_plus, total - w_plus)
    scaled = np.rint(ranks * 2).astype(int)
    total_scaled = int(np.rint(total * 2))
    obs_scaled = int(np.floor(obs * 2 + 1e-9))
    counts = np.zeros(total_scaled + 1, dtype=object)
    counts[0] = 1
    for rank in scaled:
        counts[rank:] += counts[:-rank]
    lower = sum(counts[: obs_scaled + 1])
    upper = sum(counts[total_scaled - obs_scaled :])
    p_value = min(1.0, float((lower + upper) / (2**n)))
    return w_plus, p_value


def holm_adjust(p_values: list[float]) -> list[float]:
    m = len(p_values)
    order = sorted(range(m), key=lambda idx: p_values[idx])
    adjusted = [1.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        value = min(1.0, (m - rank) * p_values[idx])
        running = max(running, value)
        adjusted[idx] = running
    return adjusted


def paired_rows(frame: pd.DataFrame, metrics: list[tuple[str, str]], context: str) -> pd.DataFrame:
    rows = []
    for metric, direction in metrics:
        pivot = frame.pivot_table(index=["instance", "K"], columns="level", values=metric, aggfunc="mean")
        pivot = pivot.dropna(subset=["none", "adaptive"])
        none = pivot["none"].astype(float).to_numpy()
        adaptive = pivot["adaptive"].astype(float).to_numpy()
        diff = none - adaptive
        if direction == "min":
            none_better = diff < -1e-12
            adaptive_better = diff > 1e-12
        else:
            none_better = diff > 1e-12
            adaptive_better = diff < -1e-12
        _, p_value = wilcoxon_exact_paired(none, adaptive)
        rows.append(
            {
                "context": context,
                "metric": metric,
                "direction": direction,
                "n_pairs": int(len(pivot)),
                "none_mean": float(np.nanmean(none)),
                "adaptive_mean": float(np.nanmean(adaptive)),
                "median_none_minus_adaptive": float(np.nanmedian(diff)),
                "none_better": int(none_better.sum()),
                "ties": int((np.abs(diff) <= 1e-12).sum()),
                "adaptive_better": int(adaptive_better.sum()),
                "wilcoxon_p_two_sided": float(p_value),
            }
        )
    out = pd.DataFrame(rows)
    out["holm_p"] = holm_adjust(out["wilcoxon_p_two_sided"].tolist())
    out["significant_0_05_holm"] = out["holm_p"] < 0.05
    return out


def c_label_frame() -> pd.DataFrame:
    detail = pd.read_csv(C_DETAIL, encoding="utf-8-sig")
    detail = detail[
        detail["objective"].eq("stability_label")
        & detail["source"].eq("Validation")
        & detail["factor"].eq("migration")
        & detail["level"].isin(["none", "adaptive"])
    ].copy()
    eaf = pd.read_csv(C_EAF, encoding="utf-8-sig")
    detail = detail.merge(
        eaf[["instance", "K", "level", "EAF_Band_Width_IQR", "EAF_Band_Width_80pct"]],
        on=["instance", "K", "level"],
        how="left",
    )
    return detail


def direct_frame() -> pd.DataFrame:
    direct = pd.read_csv(DIRECT, encoding="utf-8-sig")
    direct = direct[
        direct["ablation_family"].eq("migration") & direct["ablation_level"].isin(["none", "adaptive"])
    ].copy()
    direct = direct.rename(columns={"ablation_level": "level"})
    eaf = pd.read_csv(DIRECT_EAF, encoding="utf-8-sig")
    eaf = eaf[eaf["experiment"].eq("TEVC_PDF_Direct_Ablation")].copy()
    direct = direct.merge(
        eaf[["instance", "K", "method", "EAF_Band_Width_IQR", "EAF_Band_Width_80pct"]],
        on=["instance", "K", "method"],
        how="left",
    )
    return direct


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    c_metrics = [
        ("objective_loss", "min"),
        ("objective_rank", "min"),
        ("top3_share", "max"),
        ("PF_Overlap", "max"),
        ("PF_Drift", "min"),
        ("EAF_Band_Width_IQR", "min"),
        ("Runtime", "min"),
    ]
    direct_metrics = [
        ("RankScore", "min"),
        ("FamilyInstanceRank", "min"),
        ("HV", "max"),
        ("IGD", "min"),
        ("PF_Overlap", "max"),
        ("PF_Drift", "min"),
        ("EAF_Band_Width_IQR", "min"),
        ("Runtime", "min"),
    ]
    c_stats = paired_rows(c_label_frame(), c_metrics, "Validation C-label main effect")
    direct_stats = paired_rows(direct_frame(), direct_metrics, "Direct test ablation")
    c_stats.to_csv(OUT_DIR / "adaptive_none_vs_adaptive_c_label_wilcoxon.csv", index=False, encoding="utf-8-sig")
    direct_stats.to_csv(OUT_DIR / "adaptive_none_vs_adaptive_direct_wilcoxon.csv", index=False, encoding="utf-8-sig")
    all_stats = pd.concat([c_stats, direct_stats], ignore_index=True)
    all_stats.to_csv(OUT_DIR / "adaptive_none_vs_adaptive_wilcoxon_all.csv", index=False, encoding="utf-8-sig")
    print(all_stats.to_string(index=False))


if __name__ == "__main__":
    main()
