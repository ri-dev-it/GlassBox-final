"""Small dependency rules applied to DiCE candidate profiles."""


CONSTRAINT_NOTE = (
    "Alternatives are filtered through dependency checks for loan amount and duration, "
    "employment and job category, housing and property, and high installment burden."
)


def violates_dependency_constraints(profile: dict) -> bool:
    """Return whether a candidate profile contains an implausible dependency."""
    if profile.get("credit_amount", 0) > 10000 and profile.get("duration_months", 0) < 12:
        return True
    if profile.get("employment_since") == "unemployed" and profile.get("job") != "unemployed/unskilled non-resident":
        return True
    if profile.get("housing") == "own" and profile.get("property") == "unknown/no property":
        return True
    if profile.get("installment_rate_percent", 0) >= 4 and profile.get("credit_amount", 0) > 10000:
        return True
    return False