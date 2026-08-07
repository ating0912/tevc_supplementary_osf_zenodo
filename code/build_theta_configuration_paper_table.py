from __future__ import annotations

import os
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "p0_lite_outputs" / "theta_configuration_paper_table_20260723"
SELECTED_THETA = Path(os.environ.get("TEVC_THETA_WORKBOOK", ROOT.parent / "external_data" / "TEVC_P0_Selected_Theta_fractional_24.xlsx"))
ASSIGNMENT = ROOT / "p0_lite_outputs" / "experiment_c_stability_selector_training" / "experiment_c_stability_theta_assignment.csv"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    theta = pd.read_excel(SELECTED_THETA, sheet_name="Selected_Theta")
    theta = theta.rename(
        columns={
            "theta_id": "source_theta_id",
            "S": "subpops",
            "elite_ratio": "elite_ratio",
            "stagnation_threshold": "stagnation_threshold",
        }
    )
    theta.insert(0, "L24_row", [f"L24-{i:02d}" for i in range(1, len(theta) + 1)])
    theta.insert(1, "paper_theta_id", [f"theta_{i:02d}" for i in range(1, len(theta) + 1)])

    if ASSIGNMENT.exists():
        assignment = pd.read_csv(ASSIGNMENT, encoding="utf-8-sig")
        counts = (
            assignment["theta_id"]
            .value_counts()
            .rename_axis("source_theta_id")
            .reset_index(name="experiment_c_test_assignment_count")
        )
        theta = theta.merge(counts, on="source_theta_id", how="left")
    else:
        theta["experiment_c_test_assignment_count"] = 0
    theta["experiment_c_test_assignment_count"] = (
        theta["experiment_c_test_assignment_count"].fillna(0).astype(int)
    )

    columns = [
        "L24_row",
        "paper_theta_id",
        "source_theta_id",
        "subpops",
        "operator",
        "migration",
        "elite_ratio",
        "stagnation_threshold",
        "archive_strategy",
        "constraint_handling",
        "experiment_c_test_assignment_count",
    ]
    table = theta[columns].copy()
    table.to_csv(OUT_DIR / "theta_configuration_table_for_paper.csv", index=False, encoding="utf-8-sig")

    validation = pd.read_excel(SELECTED_THETA, sheet_name="DOE_Validation")
    validation.to_csv(OUT_DIR / "theta_l24_balance_validation.csv", index=False, encoding="utf-8-sig")

    high = table.sort_values(
        ["experiment_c_test_assignment_count", "source_theta_id"], ascending=[False, True]
    ).head(8)
    lines = [
        "# Theta Configuration Table for Paper",
        "",
        "The 24 configurations are a fractional subset of the 3^5 full factorial theta space.",
        "Archive strategy and constraint handling are fixed for P0.",
        "",
        "## L24 Theta Configurations",
        "",
        table.to_markdown(index=False),
        "",
        "## Most Frequently Assigned in Experiment C Test Split",
        "",
        high.to_markdown(index=False),
        "",
        "## L24 Balance Validation",
        "",
        validation.to_markdown(index=False),
        "",
    ]
    (OUT_DIR / "README_theta_configuration_table.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"OUT_DIR={OUT_DIR}")
    print(table.to_string(index=False))
    print("High-frequency theta:")
    print(high.to_string(index=False))


if __name__ == "__main__":
    main()
