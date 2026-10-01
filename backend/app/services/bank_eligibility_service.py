"""Transparent bank-profile eligibility layer over the existing general ML
model.
It does not claim that any bank trained or supplied the underlying model.
"""

from app.models import BankEligibilityResult

BANK_PROFILES = (
    ("HDFC Bank", 0.70),
    ("ICICI Bank", 0.64),
    ("Axis Bank", 0.58),
    ("SBI", 0.52),
)


def create_bank_eligibilities(
    application_id: int, probability: float, features: dict
) -> list[BankEligibilityResult]:
    employment = features.get("employment_since", "")
    stable = employment in {"4-7 years", ">= 7 years"}
    existing_credits = float(features.get("existing_credits_count", 0))
    installment = float(features.get("installment_rate_percent", 0))
    records = []
    for bank_name, threshold in BANK_PROFILES:
        if probability >= threshold:
            decision = "APPROVED"
        elif probability >= threshold - 0.10:
            decision = "NEEDS_REVIEW"
        else:
            decision = "NOT_ELIGIBLE"
        reasons = (
            [
                "General ML approval probability meets this educational"
                " profile's threshold."
            ]
            if probability >= threshold
            else [
                "General ML approval probability is below this educational"
                " profile's threshold."
            ]
        )
        if stable:
            reasons.append("Stable employment duration indicated.")
        conditions = ["Subject to bank KYC, affordability and policy checks."]
        risks = []
        if existing_credits > 1:
            risks.append("Existing credit obligations indicated.")
        if installment >= 3:
            risks.append("Higher installment-to-income band indicated.")
        if not risks:
            risks.append("No additional rule-based risk indicator identified.")
        record = BankEligibilityResult(
            application_id=application_id,
            bank_name=bank_name,
            decision=decision,
            probability=probability,
        )
        record.set_lists(reasons, conditions, risks)
        records.append(record)
    return records
