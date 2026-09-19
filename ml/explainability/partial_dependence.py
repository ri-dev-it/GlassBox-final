"""Partial-dependence curves for the fitted loan model."""

import numpy as np

from preprocessing.feature_config import NUMERIC_FEATURES, label_for


def global_partial_dependence(pipeline, reference_df, feature_columns=None,
                              grid_resolution: int = 20) -> list[dict]:
    """Return average approval-probability curves for numeric features."""
    from sklearn.inspection import partial_dependence

    features = feature_columns or NUMERIC_FEATURES
    curves = []
    for feature in features:
        result = partial_dependence(
            pipeline,
            reference_df,
            features=[feature],
            response_method="predict_proba",
            kind="average",
            grid_resolution=grid_resolution,
        )
        values = result.get("grid_values", result.get("values"))[0]
        average_values = np.asarray(result["average"])
        average = average_values[1 if average_values.shape[0] > 1 else 0]
        curves.append({
            "feature": feature,
            "label": label_for(feature),
            "points": [
                {"value": float(value), "approval_probability": round(float(probability), 4)}
                for value, probability in zip(values, average)
            ],
        })
    return curves