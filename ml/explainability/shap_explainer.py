"""
SHAP explanations (Milestone 7 + 19).

Uses shap.Explainer wrapping the full sklearn pipeline's predict_proba,
so it works regardless of whether the final model is Logistic Regression,
XGBoost, or RandomForest -- no per-model-type branching needed, and no
hardcoded contribution values (spec section 18/45).
"""

import os
import sys

import numpy as np
import pandas as pd
import shap

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from preprocessing.feature_config import NUMERIC_FEATURES  # noqa: E402
from preprocessing.feature_config import CATEGORICAL_FEATURES  # noqa: E402
from preprocessing.feature_config import label_for  # noqa: E402

FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def _raw_feature_name(
    transformed_name: str, feature_columns: list[str]
) -> str:
    """Map a preprocessor output column (including one-hot columns) to its form
    field."""
    for column in feature_columns:
        if (
            transformed_name == f"numeric__{column}"
            or transformed_name == column
        ):
            return column
    for column in CATEGORICAL_FEATURES:
        if transformed_name.startswith(f"categorical__{column}_"):
            return column
    return transformed_name


def _positive_class_values(values: np.ndarray) -> np.ndarray:
    """Normalise SHAP output from binary tree and linear classifiers to class
    1."""
    if values.ndim == 3:
        return values[..., 1] if values.shape[-1] == 2 else values[:, 1, :]
    return values


def _raw_contributions(
    pipeline,
    raw_df: pd.DataFrame,
    background_df: pd.DataFrame,
    feature_columns: list[str],
) -> dict[str, float]:
    """Explain the fitted estimator on numeric preprocessor output, then
    regroup one-hot columns.

    This intentionally explains the classifier after its fitted preprocessing.
    It avoids SHAP's slow generic permutation masker (and its mixed-dtype
    failure) while retaining an exact correspondence to the saved pipeline.
    """
    preprocessor = pipeline.named_steps["preprocessor"]
    classifier = pipeline.named_steps["classifier"]
    background = preprocessor.transform(
        _background_sample(background_df[feature_columns])
    )
    applicant = preprocessor.transform(raw_df[feature_columns])
    if hasattr(background, "toarray"):
        background = background.toarray()
        applicant = applicant.toarray()

    explanation = shap.Explainer(classifier, background)(applicant)
    values = _positive_class_values(explanation.values)[0]
    grouped = {column: 0.0 for column in feature_columns}
    for name, value in zip(preprocessor.get_feature_names_out(), values):
        raw_name = _raw_feature_name(name, feature_columns)
        if raw_name in grouped:
            grouped[raw_name] += float(value)
    return grouped


def _background_sample(
    background_df: pd.DataFrame, n: int = 20
) -> pd.DataFrame:
    if len(background_df) <= n:
        return background_df
    return background_df.sample(n=n, random_state=42)


def local_shap_explanation(
    pipeline,
    applicant_df: pd.DataFrame,
    background_df: pd.DataFrame,
    feature_columns: list[str] | None = None,
    label_for_fn=None,
) -> list[dict]:
    """
    Returns a per-feature contribution list for ONE applicant, sorted by
    absolute contribution descending:
        [{"feature": ..., "label": ..., "value": ..., "contribution": float,
        "direction": "positive"|"negative"}]
    "positive" contribution pushes toward APPROVAL; "negative" pushes toward
    REJECTION.
    """
    feature_columns = feature_columns or FEATURE_COLUMNS
    label_for_fn = label_for_fn or label_for
    contributions = _raw_contributions(
        pipeline, applicant_df, background_df, feature_columns
    )
    results = []
    for col in feature_columns:
        contribution = contributions[col]
        results.append(
            {
                "feature": col,
                "label": label_for_fn(col),
                "value": applicant_df.iloc[0][col],
                "contribution": round(contribution, 4),
                "direction": "positive" if contribution >= 0 else "negative",
            }
        )
    results.sort(key=lambda r: abs(r["contribution"]), reverse=True)
    return results


def global_shap_importance(
    pipeline,
    sample_df: pd.DataFrame,
    max_samples: int = 100,
    feature_columns: list[str] | None = None,
    label_for_fn=None,
) -> list[dict]:
    """
    Mean |SHAP value| per feature across a sample of applicants --
    answers "what generally influences the model?" for the admin dashboard.
    """
    feature_columns = feature_columns or FEATURE_COLUMNS
    label_for_fn = label_for_fn or label_for
    sample = _background_sample(sample_df, n=max_samples)
    per_row = [
        _raw_contributions(
            pipeline, sample.iloc[[index]], sample_df, feature_columns
        )
        for index in range(len(sample))
    ]
    mean_abs = {
        column: float(np.mean([abs(row[column]) for row in per_row]))
        for column in feature_columns
    }
    results = [
        {
            "feature": col,
            "label": label_for_fn(col),
            "mean_abs_shap": round(mean_abs[col], 4),
        }
        for col in feature_columns
    ]
    results.sort(key=lambda r: r["mean_abs_shap"], reverse=True)
    return results
