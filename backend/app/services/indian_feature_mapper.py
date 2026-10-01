"""Maps Indian-facing loan form values to the unchanged German Credit model.

The trained model and its preprocessing pipeline use legacy German Credit
categories.  This adapter is the single compatibility boundary: UI labels and
amounts may be Indianized without altering the model's expected schema.
"""

from copy import deepcopy

# UI rupee amount ÷ 100 = model's legacy numeric amount.  This is an
# interface normalization scale, not a currency conversion or a claim that
# the German Credit dataset represents Indian borrowers.
INR_TO_MODEL_AMOUNT_SCALE = 100

UI_CATEGORY_MAP = {
    "checking_account_status": {
        "no_account": "no checking account",
        "below_10000": "< 0 DM",
        "10000_50000": "0-200 DM",
        "above_50000": ">= 200 DM",
    },
    "savings_account": {
        "below_10000": "< 100 DM",
        "10000_50000": "100-500 DM",
        "50000_100000": "500-1000 DM",
        "above_100000": ">= 1000 DM",
        "unknown": "unknown/no savings account",
    },
    "purpose": {
        "home_loan": "furniture/equipment",
        "car_loan": "new car",
        "two_wheeler": "used car",
        "education": "education",
        "personal_loan": "radio/television",
        "medical": "repairs",
        "business": "business",
        "home_renovation": "repairs",
        "consumer_purchase": "radio/television",
        "other": "other",
    },
}


def model_value_to_indian_display(feature: str, value):
    """Presentation-only reverse mapping for explanations and reports."""
    if feature == "credit_amount":
        try:
            return f"₹{round(float(value) * INR_TO_MODEL_AMOUNT_SCALE):,}"
        except (TypeError, ValueError):
            return value
    labels = {
        "checking_account_status": {
            "no checking account": "No active current account",
            "< 0 DM": "Below ₹10,000",
            "0-200 DM": "₹10,000 – ₹50,000",
            ">= 200 DM": "Above ₹50,000",
        },
        "savings_account": {
            "< 100 DM": "Below ₹10,000",
            "100-500 DM": "₹10,000 – ₹50,000",
            "500-1000 DM": "₹50,000 – ₹1,00,000",
            ">= 1000 DM": "Above ₹1,00,000",
            "unknown/no savings account": "Not available",
        },
    }
    return labels.get(feature, {}).get(value, value)


def map_indian_ui_to_model(payload: dict) -> dict:
    """Return a model-compatible feature dict, accepting legacy API values
    too."""
    mapped = deepcopy(payload)
    legacy_payload = payload.get("model_input") or any(
        "DM" in str(payload.get(feature, ""))
        for feature in ("checking_account_status", "savings_account")
    )
    for feature, options in UI_CATEGORY_MAP.items():
        value = mapped.get(feature)
        if value in options:
            mapped[feature] = options[value]

    if "credit_amount" in mapped:
        try:
            amount = float(mapped["credit_amount"])
            # Indian UI requests are sent in rupees; legacy API callers can
            # explicitly set `model_input` to bypass this presentation adapter.
            if not legacy_payload:
                mapped["credit_amount"] = amount / INR_TO_MODEL_AMOUNT_SCALE
        except (TypeError, ValueError):
            pass
    mapped.pop("model_input", None)
    return mapped


def risk_level(decision: str, approval_probability: float) -> str:
    """A transparent model-derived risk band, not an official credit score."""
    risk_probability = 1 - approval_probability
    if risk_probability < 0.30:
        return "LOW"
    if risk_probability < 0.60:
        return "MEDIUM"
    return "HIGH"
