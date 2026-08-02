from __future__ import annotations

import json
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "p0_lite_outputs" / "experiment_c_stability_selector_training"
OUT = ROOT / "outputs" / "experiment_c_feature_importance_20260725"
MODEL_PATH = SRC / "experiment_c_stability_random_forest.joblib"
VAL_PATH = SRC / "validation_predictions.csv"
FEATURE_COLUMNS_PATH = SRC / "feature_columns.json"


def main() -> None:
    import shap  # type: ignore

    OUT.mkdir(parents=True, exist_ok=True)
    with FEATURE_COLUMNS_PATH.open("r", encoding="utf-8") as fh:
        feature_config = json.load(fh)
    raw_features = feature_config["numeric"] + feature_config["categorical"]
    model = joblib.load(MODEL_PATH)
    validation = pd.read_csv(VAL_PATH)
    x_val = validation[raw_features]
    x_shap = x_val.iloc[: min(200, len(x_val))].copy()

    preprocess = model.named_steps["preprocess"]
    forest = model.named_steps["model"]
    transformed = preprocess.transform(x_shap)
    transformed_features = list(preprocess.get_feature_names_out())
    if hasattr(transformed, "toarray"):
        transformed = transformed.toarray()

    explainer = shap.TreeExplainer(forest)
    shap_values = explainer.shap_values(transformed)
    if isinstance(shap_values, list):
        shap_values = shap_values[0]
    shap_values = np.asarray(shap_values)

    plt.figure()
    shap.summary_plot(shap_values, transformed, feature_names=transformed_features, show=False, max_display=20)
    plt.tight_layout()
    plt.savefig(OUT / "shap_summary_beeswarm_no_replicate.png", dpi=220, bbox_inches="tight")
    plt.close()

    plt.figure()
    shap.summary_plot(shap_values, transformed, feature_names=transformed_features, show=False, plot_type="bar", max_display=20)
    plt.tight_layout()
    plt.savefig(OUT / "shap_summary_bar_no_replicate.png", dpi=220, bbox_inches="tight")
    plt.close()

    order = np.argsort(np.mean(np.abs(shap_values), axis=0))[::-1][:5]
    rows = []
    for rank, idx in enumerate(order, start=1):
        feature = transformed_features[idx]
        plt.figure()
        shap.dependence_plot(idx, shap_values, transformed, feature_names=transformed_features, show=False, interaction_index=None)
        plt.tight_layout()
        out_path = OUT / f"shap_dependence_top{rank}_{feature.replace('__', '_').replace('/', '_')}.png"
        plt.savefig(out_path, dpi=220, bbox_inches="tight")
        plt.close()
        rows.append({"rank": rank, "feature": feature, "path": str(out_path)})
    pd.DataFrame(rows).to_csv(OUT / "shap_dependence_plot_inventory.csv", index=False, encoding="utf-8-sig")
    print(f"WROTE_SHAP_PLOTS={OUT}")


if __name__ == "__main__":
    main()
