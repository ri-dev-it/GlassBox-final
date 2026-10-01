"""
SHAP vs LIME comparison (Milestone 9 / spec section 21).

Compares the top-N features each method flags as important for the
SAME applicant, and reports agreement/disagreement WITHOUT forcing
artificial alignment -- the two methods use different methodologies
(SHAP: game-theoretic attribution; LIME: local linear surrogate model)
and legitimately can disagree on ranking or even direction.
"""


def compare_explanations(
    shap_results: list[dict], lime_results: list[dict], top_n: int = 5
) -> dict:
    shap_top = {r["feature"]: r for r in shap_results[:top_n]}
    lime_top = {r["feature"]: r for r in lime_results[:top_n]}

    agreement = []
    disagreement = []

    common_features = set(shap_top) & set(lime_top)
    for feature in common_features:
        shap_dir = shap_top[feature]["direction"]
        lime_dir = lime_top[feature]["direction"]
        entry = {
            "feature": feature,
            "label": shap_top[feature]["label"],
            "shap_contribution": shap_top[feature]["contribution"],
            "lime_contribution": lime_top[feature]["contribution"],
            "shap_direction": shap_dir,
            "lime_direction": lime_dir,
        }
        if shap_dir == lime_dir:
            agreement.append(entry)
        else:
            disagreement.append(entry)

    shap_only = [f for f in shap_top if f not in lime_top]
    lime_only = [f for f in lime_top if f not in shap_top]

    return {
        "agreement": agreement,
        "direction_disagreement": disagreement,
        "shap_only_top_features": [shap_top[f]["label"] for f in shap_only],
        "lime_only_top_features": [lime_top[f]["label"] for f in lime_only],
        "note": (
            "SHAP and LIME use different methodologies (game-theoretic "
            "attribution vs. local linear surrogate models). Disagreement "
            "in ranking or direction is expected and does not mean either "
            "method is wrong."
        ),
    }
