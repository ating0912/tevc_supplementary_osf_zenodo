"""Package the PDF-aligned without-elite-injection ablation tables.

This script extracts the elite-injection family from the completed direct
ablation run and writes a focused, report-ready data package.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT / "p0_lite_outputs" / "tevc_pdf_direct_ablation_full_20260717"
SOURCE_SUMMARY = SOURCE_ROOT / "pdf_direct_ablation_summary"
OUT_DIR = ROOT / "outputs" / "tevc_without_elite_injection_20260720"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    overall = read_csv(SOURCE_SUMMARY / "pdf_direct_ablation_overall.csv")
    instance_ranked = read_csv(SOURCE_SUMMARY / "pdf_direct_ablation_instance_ranked.csv")
    win_loss = read_csv(SOURCE_SUMMARY / "pdf_direct_ablation_pairwise_win_loss.csv")
    completion = read_csv(SOURCE_SUMMARY / "pdf_direct_ablation_completion_status.csv")

    overall_elite = overall[overall["ablation_family"] == "elite_injection"].copy()
    instance_elite = instance_ranked[instance_ranked["ablation_family"] == "elite_injection"].copy()
    win_loss_elite = win_loss[win_loss["ablation_family"] == "elite_injection"].copy()
    completion_elite = completion[completion["ablation_family"] == "elite_injection"].copy()

    no_elite_vs_others = win_loss_elite[
        win_loss_elite["method_a"].eq("PDF_Abl_Elite_0pct")
        | win_loss_elite["method_b"].eq("PDF_Abl_Elite_0pct")
    ].copy()

    overall_elite.to_csv(OUT_DIR / "without_elite_injection_overall.csv", index=False, encoding="utf-8-sig")
    instance_elite.to_csv(
        OUT_DIR / "without_elite_injection_instance_ranked.csv", index=False, encoding="utf-8-sig"
    )
    win_loss_elite.to_csv(
        OUT_DIR / "without_elite_injection_pairwise_win_loss.csv", index=False, encoding="utf-8-sig"
    )
    no_elite_vs_others.to_csv(
        OUT_DIR / "without_elite_0pct_vs_elite_ratios_win_loss.csv", index=False, encoding="utf-8-sig"
    )
    completion_elite.to_csv(
        OUT_DIR / "without_elite_injection_completion_status.csv", index=False, encoding="utf-8-sig"
    )

    readme = {
        "purpose": "PDF-aligned Without Elite Injection ablation package",
        "source_root": str(SOURCE_ROOT),
        "source_summary": str(SOURCE_SUMMARY),
        "output_dir": str(OUT_DIR),
        "variants": {
            "PDF_Abl_Elite_0pct": "without elite injection; eliteRatio=0",
            "PDF_Abl_Elite_1pct": "elite injection ratio 1%",
            "PDF_Abl_Elite_5pct": "elite injection ratio 5%",
            "PDF_Abl_Elite_10pct": "elite injection ratio 10%",
        },
        "controlled_settings": {
            "subpops": 3,
            "operator": "DE/rand",
            "migration": "fixed",
            "stagnation_threshold": 10,
            "population_size": 100,
            "maxFE": 10000,
            "runs_per_instance": 30,
            "test_instances": 32,
        },
        "implementation_note": (
            "ECMADE_MOO_KB treats eliteRatio<=0 as no elite copy. This avoids the "
            "previous max(1, ceil(eliteRatio*N)) behavior and makes eliteRatio=0 "
            "a true without-elite-injection condition."
        ),
    }
    (OUT_DIR / "README.json").write_text(json.dumps(readme, indent=2), encoding="utf-8")

    print(f"Wrote {OUT_DIR}")
    print(overall_elite[[
        "ablation_level",
        "instances",
        "mean_HV",
        "mean_IGD",
        "mean_PF_Overlap",
        "mean_PF_Drift",
        "mean_Runtime",
        "overall_RankScore",
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
