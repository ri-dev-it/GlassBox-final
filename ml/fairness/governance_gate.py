"""Fairness governance gate applied before a model can be served."""

# These limits require review against applicable regulation and lending policy
# before production use; they are illustrative governance defaults only.
MAX_DEMOGRAPHIC_PARITY_DIFF = 0.10
MAX_EQUALIZED_ODDS_DIFF = 0.10
DEFAULT_GOVERNANCE_THRESHOLDS = {
    "max_demographic_parity_difference": MAX_DEMOGRAPHIC_PARITY_DIFF,
    "max_equalized_odds_difference": MAX_EQUALIZED_ODDS_DIFF,
}


def check_governance(
    fairness_metrics: dict, thresholds: dict | None = None
) -> dict:
    """Return whether disparity metrics remain within configured limits."""
    limits = {**DEFAULT_GOVERNANCE_THRESHOLDS, **(thresholds or {})}
    disparity = fairness_metrics.get("disparity_metrics", fairness_metrics)
    checks = [
        (
            "demographic parity difference",
            "demographic_parity_difference",
            limits["max_demographic_parity_difference"],
        ),
        (
            "equalized odds difference",
            "equalized_odds_difference",
            limits["max_equalized_odds_difference"],
        ),
    ]
    failed_checks = []
    for label, metric, maximum in checks:
        value = abs(float(disparity.get(metric, 0)))
        if value > maximum:
            failed_checks.append(
                f"{label} {value:.4f} exceeds maximum allowed {maximum:.4f}."
            )
    return {"passed": not failed_checks, "failed_checks": failed_checks}
