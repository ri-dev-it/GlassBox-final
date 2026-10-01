"""
Plain-English explanation engine (Milestone 22).

Dynamically converts SHAP/LIME feature contributions into readable
sentences. Nothing here is applicant-specific hardcoding -- every
sentence is generated from the actual (feature, value, contribution)
tuples passed in.
"""


def _magnitude_word(abs_contribution: float) -> str:
    if abs_contribution >= 0.08:
        return "strongly"
    if abs_contribution >= 0.03:
        return "moderately"
    return "slightly"


def explain_feature(
    feature_label: str,
    value,
    contribution: float,
    prediction: str,
    positive_direction: str = "toward approval",
    negative_direction: str = "toward rejection",
) -> str:
    """One sentence for one feature's contribution."""
    magnitude = _magnitude_word(abs(contribution))
    direction = positive_direction if contribution >= 0 else negative_direction
    return (
        f"{feature_label} (value: {value}) contributed {magnitude}"
        f" {direction}."
    )


def generate_summary(
    contributions: list[dict],
    prediction: str,
    probability: float,
    top_n: int = 5,
    positive_direction: str = "toward approval",
    negative_direction: str = "toward rejection",
    positive_prediction: str = "APPROVE",
) -> str:
    """
    contributions: sorted list of {"label", "value", "contribution", ...}
    (as returned by shap_explainer.local_shap_explanation).
    """
    top = contributions[:top_n]
    sentences = [
        explain_feature(
            c["label"],
            c["value"],
            c["contribution"],
            prediction,
            positive_direction,
            negative_direction,
        )
        for c in top
    ]

    confidence_pct = round(
        (
            probability * 100
            if prediction == positive_prediction
            else (1 - probability) * 100
        ),
        1,
    )
    intro = (
        f"The model predicted {prediction} with {confidence_pct}% confidence"
        " in that outcome. This is a model-generated statistical estimate,"
        " not a guarantee. The most influential factors were:"
    )
    return intro + "\n" + "\n".join(f"- {s}" for s in sentences)
