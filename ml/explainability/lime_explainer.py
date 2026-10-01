"""
LIME local explanations (Milestone 8).

LIME operates in the RAW feature space (before the pipeline's internal
one-hot/scaling), with the pipeline's predict_proba as the black-box
function -- so the pipeline handles preprocessing consistently, exactly
as it does for SHAP and for real predictions.
"""

import os
import sys

import numpy as np
import pandas as pd
from lime.lime_tabular import LimeTabularExplainer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from preprocessing.feature_config import NUMERIC_FEATURES  # noqa: E402
from preprocessing.feature_config import CATEGORICAL_FEATURES  # noqa: E402
from preprocessing.feature_config import label_for  # noqa: E402

FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def _build_explainer(
    training_df: pd.DataFrame,
    feature_columns: list[str],
    categorical_features: list[str],
    class_names: list[str],
):
    df = training_df[feature_columns].copy()

    # LIME needs categorical columns as integer-coded with a category map.
    categorical_indices = []
    category_maps = {}
    encoded = df.copy()
    for i, col in enumerate(feature_columns):
        if col in categorical_features:
            categories = sorted(df[col].astype(str).unique())
            category_maps[i] = categories
            categorical_indices.append(i)
            encoded[col] = df[col].astype(str).apply(categories.index)

    explainer = LimeTabularExplainer(
        training_data=encoded.values,
        feature_names=feature_columns,
        categorical_features=categorical_indices,
        categorical_names=category_maps,
        class_names=class_names,
        mode="classification",
        discretize_continuous=True,
    )
    return explainer, category_maps


def local_lime_explanation(
    pipeline,
    applicant_df: pd.DataFrame,
    training_df: pd.DataFrame,
    num_features: int = 10,
    feature_columns: list[str] | None = None,
    categorical_features: list[str] | None = None,
    label_for_fn=None,
    class_names: list[str] | None = None,
) -> list[dict]:
    """
    Returns per-feature contributions for ONE applicant in the same shape
    as local_shap_explanation, so the frontend/comparison module can
    treat them uniformly.
    """
    feature_columns = feature_columns or FEATURE_COLUMNS
    categorical_features = categorical_features or CATEGORICAL_FEATURES
    label_for_fn = label_for_fn or label_for
    explainer, category_maps = _build_explainer(
        training_df,
        feature_columns,
        categorical_features,
        class_names or ["REJECTED", "APPROVED"],
    )

    def predict_fn(encoded_rows: np.ndarray) -> np.ndarray:
        decoded = pd.DataFrame(encoded_rows, columns=feature_columns)
        for i, col in enumerate(feature_columns):
            if col in categorical_features:
                categories = category_maps[i]
                decoded[col] = (
                    decoded[col]
                    .round()
                    .astype(int)
                    .clip(0, len(categories) - 1)
                    .apply(lambda idx: categories[idx])
                )
            else:
                decoded[col] = decoded[col].astype(float)
        return pipeline.predict_proba(decoded)

    # Encode the single applicant row the same way as the training data.
    row = applicant_df[feature_columns].iloc[0].copy()
    encoded_row = []
    for i, col in enumerate(feature_columns):
        if col in categorical_features:
            categories = category_maps[i]
            value = str(row[col])
            encoded_row.append(
                categories.index(value) if value in categories else 0
            )
        else:
            encoded_row.append(float(row[col]))
    encoded_row = np.array(encoded_row)

    explanation = explainer.explain_instance(
        encoded_row,
        predict_fn,
        num_features=num_features,
        labels=(1,),
    )

    # as_list() keys look like "feature_name <= value" strings -- map back
    # to our feature columns by matching the LIME-generated feature index map.
    results = []
    for feature_idx, weight in explanation.local_exp[1]:
        col = feature_columns[feature_idx]
        results.append(
            {
                "feature": col,
                "label": label_for_fn(col),
                "value": applicant_df.iloc[0][col],
                "contribution": round(float(weight), 4),
                "direction": "positive" if weight >= 0 else "negative",
            }
        )
    results.sort(key=lambda r: abs(r["contribution"]), reverse=True)
    return results
