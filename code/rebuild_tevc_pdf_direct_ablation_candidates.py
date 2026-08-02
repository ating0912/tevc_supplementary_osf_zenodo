"""Rebuild the full candidate metadata table for TEVC PDF direct ablation.

The MATLAB runner can be executed by ablation family. Each partial execution
rewrites kb_theta_candidates.csv with only the selected family, while the raw
output root may contain all families after resumed chunked runs. This utility
restores the full 10-variant metadata table expected by the ranker/summarizer.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


COLUMNS = [
    "method",
    "source_theta_id",
    "ablation_family",
    "ablation_level",
    "source_operator",
    "source_migration",
    "source_elite_ratio",
    "source_archive_strategy",
    "source_constraint_handling",
    "subpops",
    "operatorMode",
    "exchangeMode",
    "eliteRatio",
    "stagnationThreshold",
    "theta",
    "archiveLimitFactor",
    "consensusArchive",
    "archiveConsWeight",
    "bestGuide",
    "minSubpopSize",
]


def base_row() -> dict[str, object]:
    return {
        "source_operator": "DE/rand",
        "operatorMode": "rand2",
        "source_archive_strategy": "crowding-pruned",
        "source_constraint_handling": "repair+feasible-first",
        "theta": 1 / 13,
        "archiveLimitFactor": 5,
        "consensusArchive": 0,
        "archiveConsWeight": 0.0,
        "bestGuide": "rank",
        "minSubpopSize": 1,
        "stagnationThreshold": 10,
    }


def make_row(method: str, family: str, level: str, **overrides: object) -> dict[str, object]:
    row = base_row()
    row.update(
        {
            "method": method,
            "source_theta_id": method,
            "ablation_family": family,
            "ablation_level": level,
        }
    )
    row.update(overrides)
    return row


def build_candidates() -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for s_value in [2, 3, 5]:
        rows.append(
            make_row(
                f"PDF_Abl_S_{s_value}",
                "subpopulation_number",
                f"S={s_value}",
                source_migration="none",
                exchangeMode="none",
                source_elite_ratio="5%",
                eliteRatio=0.05,
                subpops=s_value,
            )
        )

    for migration, exchange_mode in [
        ("none", "none"),
        ("fixed", "paper"),
        ("adaptive", "stable"),
    ]:
        rows.append(
            make_row(
                f"PDF_Abl_Migration_{migration}",
                "migration",
                migration,
                source_migration=migration,
                exchangeMode=exchange_mode,
                source_elite_ratio="5%",
                eliteRatio=0.05,
                subpops=3,
            )
        )

    for label, value in [("0%", 0.0), ("1%", 0.01), ("5%", 0.05), ("10%", 0.10)]:
        rows.append(
            make_row(
                f"PDF_Abl_Elite_{label.replace('%', 'pct')}",
                "elite_injection",
                label,
                source_migration="fixed",
                exchangeMode="paper",
                source_elite_ratio=label,
                eliteRatio=value,
                subpops=3,
            )
        )

    return pd.DataFrame(rows, columns=COLUMNS)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()

    root = args.root
    root.mkdir(parents=True, exist_ok=True)
    out_path = root / "kb_theta_candidates.csv"
    candidates = build_candidates()
    candidates.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(candidates)} candidates to {out_path}")


if __name__ == "__main__":
    main()
