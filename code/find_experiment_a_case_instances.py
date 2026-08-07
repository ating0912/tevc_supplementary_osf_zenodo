import os

import numpy as np
import pandas as pd


ROOT = r"."
SYN_DIR = os.path.join(
    ROOT,
    "p0_lite_outputs",
    "synthetic_constrained_portfolio",
    "experiment_A_report_20260705_094925",
)
OR_DIR = os.path.join(
    ROOT,
    "p0_lite_outputs",
    "orlib_constrained_portfolio",
    "experiment_A_orlib_report_20260705_235837",
)
OUT_DIR = os.path.join(ROOT, "docx_outputs")
OUT_CSV = os.path.join(OUT_DIR, "Experiment_A_case_instance_selection.csv")
OUT_MD = os.path.join(OUT_DIR, "Experiment_A_case_instance_selection.md")

QUALITY_METRICS = ["HV", "IGD"]
TYPICAL_METRICS = ["HV", "IGD", "PF_Overlap", "EAF_Band_Width"]
STABILITY_METRICS = ["PF_Overlap", "EAF_Band_Width", "PF_Drift"]
BASELINES = ["NSGAII", "SPEA2", "MOEAD", "GDE3", "A_MPMO"]


def zscore(s):
    s = pd.Series(s, dtype=float)
    sd = s.std(ddof=0)
    if sd == 0 or np.isnan(sd):
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - s.mean()) / sd


def fmt(x, digits=4):
    if pd.isna(x):
        return ""
    return f"{float(x):.{digits}f}"


def load_dataset(label, path):
    df = pd.read_csv(os.path.join(path, "instance_method_metrics.csv"))
    df.insert(0, "Dataset", label)
    return df


def typical_case(df):
    e = df[df["method"].eq("ECMADE_MOO")].copy().reset_index(drop=True)
    zcols = {}
    for metric in TYPICAL_METRICS:
        zcols[metric] = zscore(e[metric])
        median_z = (e[metric].median() - e[metric].mean()) / e[metric].std(ddof=0)
        e[f"abs_zdist_{metric}"] = (zcols[metric] - median_z).abs()
    e["TypicalDistance"] = e[[f"abs_zdist_{m}" for m in TYPICAL_METRICS]].sum(axis=1)
    row = e.sort_values("TypicalDistance", ascending=True).iloc[0].to_dict()
    row["CaseType"] = "Typical"
    return row, e.sort_values("TypicalDistance").head(10)


def quality_advantage_table(df):
    pivot = df.pivot_table(index="instance", columns="method", values=["HV", "IGD", "PF_Overlap", "EAF_Band_Width", "PF_Drift"], aggfunc="mean")
    meta = df[df["method"].eq("ECMADE_MOO")].set_index("instance")
    rows = []
    for instance in pivot.index:
        rec = {"instance": instance}
        for col in ["split", "assets", "K", "k_ratio"]:
            if col in meta.columns:
                rec[col] = meta.loc[instance, col]
        rec["DeltaHV"] = pivot.loc[instance, ("HV", "ECMADE_MOO")] - pivot.loc[instance, ("HV", BASELINES)].max()
        rec["DeltaIGD"] = pivot.loc[instance, ("IGD", BASELINES)].min() - pivot.loc[instance, ("IGD", "ECMADE_MOO")]
        rec["DeltaOverlap"] = pivot.loc[instance, ("PF_Overlap", "ECMADE_MOO")] - pivot.loc[instance, ("PF_Overlap", BASELINES)].max()
        rec["DeltaEAF"] = pivot.loc[instance, ("EAF_Band_Width", BASELINES)].min() - pivot.loc[instance, ("EAF_Band_Width", "ECMADE_MOO")]
        rec["ECMADE_HV"] = pivot.loc[instance, ("HV", "ECMADE_MOO")]
        rec["ECMADE_IGD"] = pivot.loc[instance, ("IGD", "ECMADE_MOO")]
        rec["ECMADE_PF_Overlap"] = pivot.loc[instance, ("PF_Overlap", "ECMADE_MOO")]
        rec["ECMADE_EAF_Band_Width"] = pivot.loc[instance, ("EAF_Band_Width", "ECMADE_MOO")]
        rec["ECMADE_PF_Drift"] = pivot.loc[instance, ("PF_Drift", "ECMADE_MOO")]
        rows.append(rec)
    out = pd.DataFrame(rows)
    out["GoodScore"] = zscore(out["DeltaHV"]) + zscore(out["DeltaIGD"])
    out["GoodScore_All4_NotUsed"] = (
        zscore(out["DeltaHV"]) + zscore(out["DeltaIGD"]) + zscore(out["DeltaOverlap"]) + zscore(out["DeltaEAF"])
    )
    return out


def good_case(df):
    adv = quality_advantage_table(df)
    row = adv.sort_values("GoodScore", ascending=False).iloc[0].to_dict()
    row["CaseType"] = "Good"
    return row, adv.sort_values("GoodScore", ascending=False).head(10)


def unstable_case(df):
    e = df[df["method"].eq("ECMADE_MOO")].copy().reset_index(drop=True)
    hv_q75 = e["HV"].quantile(0.75)
    igd_q25 = e["IGD"].quantile(0.25)
    e["z_PF_Overlap"] = zscore(e["PF_Overlap"])
    e["z_EAF_Band_Width"] = zscore(e["EAF_Band_Width"])
    e["z_PF_Drift"] = zscore(e["PF_Drift"])
    candidates = e[(e["HV"] >= hv_q75) & (e["IGD"] <= igd_q25)].copy()
    if candidates.empty:
        candidates = e[(e["HV"] >= hv_q75) | (e["IGD"] <= igd_q25)].copy()
    candidates["UnstableScore"] = (
        -candidates["z_PF_Overlap"] + candidates["z_EAF_Band_Width"] + candidates["z_PF_Drift"]
    )
    candidates["HV_Q75"] = hv_q75
    candidates["IGD_Q25"] = igd_q25
    row = candidates.sort_values("UnstableScore", ascending=False).iloc[0].to_dict()
    row["CaseType"] = "High-quality but unstable"
    return row, candidates.sort_values("UnstableScore", ascending=False).head(10)


def summarize_row(dataset, row):
    return {
        "Dataset": dataset,
        "CaseType": row["CaseType"],
        "instance": row["instance"],
        "split": row.get("split", ""),
        "assets": row.get("assets", ""),
        "K": row.get("K", ""),
        "HV": row.get("HV", row.get("ECMADE_HV", "")),
        "IGD": row.get("IGD", row.get("ECMADE_IGD", "")),
        "PF_Overlap": row.get("PF_Overlap", row.get("ECMADE_PF_Overlap", "")),
        "EAF_Band_Width": row.get("EAF_Band_Width", row.get("ECMADE_EAF_Band_Width", "")),
        "PF_Drift": row.get("PF_Drift", row.get("ECMADE_PF_Drift", "")),
        "TypicalDistance": row.get("TypicalDistance", ""),
        "GoodScore": row.get("GoodScore", ""),
        "DeltaHV": row.get("DeltaHV", ""),
        "DeltaIGD": row.get("DeltaIGD", ""),
        "UnstableScore": row.get("UnstableScore", ""),
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    datasets = [
        ("Synthetic", load_dataset("Synthetic", SYN_DIR)),
        ("OR-Library", load_dataset("OR-Library", OR_DIR)),
    ]
    summary_rows = []
    detail_tables = {}
    for label, df in datasets:
        typical, typical_top = typical_case(df)
        good, good_top = good_case(df)
        unstable, unstable_top = unstable_case(df)
        summary_rows.extend([
            summarize_row(label, typical),
            summarize_row(label, good),
            summarize_row(label, unstable),
        ])
        detail_tables[f"{label}_typical_top10"] = typical_top
        detail_tables[f"{label}_good_top10"] = good_top
        detail_tables[f"{label}_unstable_top10"] = unstable_top

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    lines = ["# Experiment A Case Instance Selection", ""]
    lines.append("Selection rules follow the requested definitions. Scores are normalized within each dataset to avoid mixing Synthetic and OR-Library scales.")
    lines.append("")
    lines.append("## Selected Instances")
    lines.append("")
    cols = ["Dataset", "CaseType", "instance", "assets", "K", "HV", "IGD", "PF_Overlap", "EAF_Band_Width", "PF_Drift", "TypicalDistance", "GoodScore", "DeltaHV", "DeltaIGD", "UnstableScore"]
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, r in summary.iterrows():
        values = []
        for c in cols:
            v = r[c]
            values.append(fmt(v) if isinstance(v, (int, float, np.floating)) and c not in ["assets", "K"] else str(v))
        lines.append("| " + " | ".join(values) + " |")
    lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    lines.append("- Use the OR-Library Good Case to highlight ECMADE-MOO's portfolio-specific solution-quality advantage.")
    lines.append("- Use the Synthetic High-quality but unstable case to motivate Experiment B/C, because it shows that quality can be high while stability remains weak on heterogeneous instances.")
    lines.append("- Use the Typical Case only as a neutral representative for method behavior plots.")
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    for name, table in detail_tables.items():
        table.to_csv(os.path.join(OUT_DIR, f"Experiment_A_case_{name}.csv"), index=False, encoding="utf-8-sig")

    print(f"SUMMARY_CSV={OUT_CSV}")
    print(f"SUMMARY_MD={OUT_MD}")
    print(summary[cols].to_string(index=False))


if __name__ == "__main__":
    main()
