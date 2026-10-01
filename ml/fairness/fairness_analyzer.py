"""
Fairlearn fairness audit (Milestone 11 / spec sections 26-28).

Operates on the labeled test set + predictions saved by train.py
(ml/data/processed/test_with_predictions.csv), grouped by the
'sex' proxy attribute (see docs/fairness/README.md for the caveat
about this being a derived proxy, not a clean self-reported field).

Every number here is computed from real stored predictions -- never
hardcoded, never simulated (spec section 45/47).
"""

import os
import sys

import pandas as pd
from fairlearn.metrics import (
    MetricFrame,
    selection_rate,
    true_positive_rate,
    false_positive_rate,
    false_negative_rate,
    demographic_parity_difference,
    equalized_odds_difference,
)
from sklearn.metrics import accuracy_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_WITH_PREDICTIONS  # noqa: E402
from config import TARGET_COLUMN  # noqa: E402
from config import PROTECTED_ATTRIBUTE  # noqa: E402

# Disparity threshold above which we flag "potential disparity" -- documented,
# not an absolute fairness verdict (spec section 28: never claim "the
# model is fair").
DISPARITY_FLAG_THRESHOLD = 0.10


def run_fairness_analysis() -> dict:
    if not os.path.exists(TEST_SET_WITH_PREDICTIONS):
        raise FileNotFoundError(
            f"{TEST_SET_WITH_PREDICTIONS} not found. Run training/train.py"
            " first -- it saves the labeled test set + predictions this"
            " analysis needs."
        )

    df = pd.read_csv(TEST_SET_WITH_PREDICTIONS)
    y_true = df[TARGET_COLUMN]
    y_pred = df["prediction"]
    groups = df[PROTECTED_ATTRIBUTE]

    return run_fairness_analysis_for_data(
        y_true, y_pred, groups, PROTECTED_ATTRIBUTE
    )


def run_fairness_analysis_for_data(
    y_true, y_pred, groups, protected_attribute: str
) -> dict:
    """Run the existing Fairlearn audit over supplied held-out predictions."""

    metric_frame = MetricFrame(
        metrics={
            "accuracy": accuracy_score,
            "selection_rate": selection_rate,  # == approval rate here
            "true_positive_rate": true_positive_rate,
            "false_positive_rate": false_positive_rate,
            "false_negative_rate": false_negative_rate,
        },
        y_true=y_true,
        y_pred=y_pred,
        sensitive_features=groups,
    )

    by_group = metric_frame.by_group.round(4).to_dict(orient="index")

    dp_diff = float(
        demographic_parity_difference(
            y_true, y_pred, sensitive_features=groups
        )
    )
    eo_diff = float(
        equalized_odds_difference(y_true, y_pred, sensitive_features=groups)
    )

    def interpret(name: str, value: float) -> str:
        if abs(value) >= DISPARITY_FLAG_THRESHOLD:
            return (
                f"Potential disparity detected on {name} (difference ="
                f" {value:.3f}, exceeds the"
                f" {DISPARITY_FLAG_THRESHOLD} documented threshold)."
            )
        return (
            f"No substantial disparity detected on {name} under this metric"
            f" (difference = {value:.3f})."
        )

    return {
        "protected_attribute": protected_attribute,
        "protected_attribute_caveat": (
            f"Fairness was audited across the supplied '{protected_attribute}'"
            " groups. This grouping is a governance signal, not a legal or"
            " absolute fairness verdict."
        ),
        "group_metrics": by_group,
        "overall_metrics": {
            "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
            "selection_rate": round(float(selection_rate(y_true, y_pred)), 4),
        },
        "disparity_metrics": {
            "demographic_parity_difference": round(dp_diff, 4),
            "equalized_odds_difference": round(eo_diff, 4),
        },
        "interpretation": [
            interpret("demographic parity (selection/approval rate)", dp_diff),
            interpret("equalized odds (TPR/FPR balance)", eo_diff),
        ],
        "sample_size": len(y_true),
        "disclaimer": (
            "Fairness is context-dependent. These metrics describe statistical"
            " patterns in this model's outcomes on this test set -- they are"
            " not a legal or absolute determination of fairness."
        ),
    }
