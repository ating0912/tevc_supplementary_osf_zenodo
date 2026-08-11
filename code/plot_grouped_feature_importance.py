from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "selector" / "figure_data"
DEFAULT_OUTPUT_DIR = ROOT / "figures"

PERMUTATION_COLUMNS = {
    "feature",
    "permutation_importance_mean_r2_drop",
    "permutation_importance_std",
}
IMPURITY_COLUMNS = {"base_feature", "impurity_importance_sum"}
SHAP_COLUMNS = {"base_feature", "mean_abs_shap_sum"}


def read_table(path: Path, required: set[str]) -> pd.DataFrame:
    frame = pd.read_csv(path, encoding="utf-8-sig")
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(missing)}")
    return frame


def save_figure(fig: plt.Figure, output_dir: Path, stem: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [output_dir / f"{stem}.png", output_dir / f"{stem}.svg"]
    fig.savefig(outputs[0], dpi=200, bbox_inches="tight", facecolor="white")
    fig.savefig(outputs[1], bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return outputs


def plot_feature_importance(
    permutation: pd.DataFrame,
    impurity: pd.DataFrame,
    output_dir: Path,
) -> list[Path]:
    selected = permutation.loc[
        permutation["permutation_importance_mean_r2_drop"].ne(0)
    ].copy()
    selected = selected.sort_values(
        "permutation_importance_mean_r2_drop", ascending=False
    ).reset_index(drop=True)
    impurity_values = impurity.set_index("base_feature")["impurity_importance_sum"]
    missing = sorted(set(selected["feature"]) - set(impurity_values.index))
    if missing:
        raise ValueError("Impurity table lacks selected features: " + ", ".join(missing))

    y = np.arange(len(selected))
    fig, axes = plt.subplots(1, 2, figsize=(16, 8), sharey=True)
    fig.suptitle(
        "No-replicate selector grouped feature importance",
        fontsize=18,
        fontweight="bold",
    )

    axes[0].barh(
        y,
        selected["permutation_importance_mean_r2_drop"],
        xerr=selected["permutation_importance_std"],
        color="#3f7fa6",
        edgecolor="none",
        ecolor="black",
        capsize=0,
    )
    axes[0].axvline(0, color="#333333", linewidth=1)
    axes[0].set_yticks(y, selected["feature"])
    axes[0].set_xlabel("R2 drop")
    axes[0].set_title("Permutation importance")

    axes[1].barh(
        y,
        [impurity_values[feature] for feature in selected["feature"]],
        color="#1b9e77",
        edgecolor="none",
    )
    axes[1].set_xlabel("Importance sum")
    axes[1].set_title("RF impurity importance")

    axes[0].invert_yaxis()
    for axis in axes:
        axis.grid(axis="x", color="#dfe3e8", linewidth=1)
        axis.set_axisbelow(True)
        axis.tick_params(labelsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94), w_pad=5)
    return save_figure(fig, output_dir, "fig_feature_importance_no_replicate")


def plot_grouped_shap(shap: pd.DataFrame, output_dir: Path) -> list[Path]:
    ordered = shap.sort_values("mean_abs_shap_sum", ascending=False).reset_index(drop=True)
    y = np.arange(len(ordered))
    fig, axis = plt.subplots(figsize=(12, 8))
    axis.barh(y, ordered["mean_abs_shap_sum"], color="#7a3fe4", edgecolor="none")
    axis.set_yticks(y, ordered["base_feature"])
    axis.invert_yaxis()
    axis.set_xlabel("Mean absolute SHAP")
    axis.set_title("Grouped SHAP global importance", fontsize=18)
    axis.grid(axis="x", color="#dfe3e8", linewidth=1)
    axis.set_axisbelow(True)
    axis.tick_params(labelsize=11)
    fig.tight_layout()
    return save_figure(fig, output_dir, "fig_shap_global_importance_grouped")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild formal TEVC Fig. S2 and Fig. S3 from grouped selector importance CSVs."
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    permutation = read_table(
        args.data_dir / "corrected_grouped_permutation_importance.csv",
        PERMUTATION_COLUMNS,
    )
    impurity = read_table(
        args.data_dir / "corrected_grouped_impurity_importance.csv",
        IMPURITY_COLUMNS,
    )
    shap = read_table(
        args.data_dir / "corrected_grouped_shap_importance.csv",
        SHAP_COLUMNS,
    )

    outputs = plot_feature_importance(permutation, impurity, args.output_dir)
    outputs.extend(plot_grouped_shap(shap, args.output_dir))
    for output in outputs:
        print(output.resolve())


if __name__ == "__main__":
    main()
