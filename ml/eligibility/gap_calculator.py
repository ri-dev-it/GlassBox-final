"""Illustrative Razorpay Capital tier-gap calculator.

Thresholds and exposure amounts using this module are simulated demo values,
not real Razorpay Capital policy. The gap normalization deliberately follows
the supplied calculator's original naive unit normalization.
"""

from dataclasses import dataclass, field
from typing import Dict, List

TRANSACTION_GAP_FEATURES = {
    "gmv_trend_30d": ("increase", "percentage points"),
    "gmv_trend_90d": ("increase", "percentage points"),
    "payment_success_rate": ("increase", "percentage points"),
    "refund_rate": ("decrease", "percentage points"),
    "chargeback_rate": ("decrease", "percentage points"),
    "customer_concentration": ("decrease", "percentage points"),
    "order_volume_volatility": ("decrease", "points"),
    "account_age_days": ("increase", "days"),
}


CAPITAL_TIER_CRITERIA = [
    {
        "name": "Starter Advance",
        "min_gmv_trend_30d": -0.20,
        "min_gmv_trend_90d": -0.25,
        "min_payment_success_rate": 0.90,
        "max_refund_rate": 0.12,
        "max_chargeback_rate": 0.04,
        "max_customer_concentration": 0.65,
        "max_order_volume_volatility": 1.20,
        "min_account_age_days": 60,
        "estimated_exposure": 50000,
    },
    {
        "name": "Growth Capital",
        "min_gmv_trend_30d": -0.05,
        "min_gmv_trend_90d": 0.00,
        "min_payment_success_rate": 0.94,
        "max_refund_rate": 0.08,
        "max_chargeback_rate": 0.025,
        "max_customer_concentration": 0.50,
        "max_order_volume_volatility": 0.85,
        "min_account_age_days": 180,
        "estimated_exposure": 150000,
    },
    {
        "name": "Scale Capital",
        "min_gmv_trend_30d": 0.10,
        "min_gmv_trend_90d": 0.15,
        "min_payment_success_rate": 0.97,
        "max_refund_rate": 0.05,
        "max_chargeback_rate": 0.01,
        "max_customer_concentration": 0.35,
        "max_order_volume_volatility": 0.55,
        "min_account_age_days": 365,
        "estimated_exposure": 500000,
    },
]


@dataclass
class Gap:
    feature: str
    current_value: float
    required_value: float
    delta: float
    direction: str
    human_message: str


@dataclass
class BankEligibilityResult:
    """Original result shape retained; ``bank`` contains a Capital tier
    name."""

    bank: str
    eligible: bool
    gaps: List[Gap] = field(default_factory=list)
    overall_message: str = ""

    @property
    def tier(self) -> str:
        return self.bank


def _format_gap_message(
    feature: str, delta: float, current: float, required: float, direction: str
) -> str:
    labels = {
        "gmv_trend_30d": "30-day GMV trend",
        "gmv_trend_90d": "90-day GMV trend",
        "payment_success_rate": "payment success rate",
        "refund_rate": "refund rate",
        "chargeback_rate": "chargeback rate",
        "customer_concentration": "customer concentration",
        "order_volume_volatility": "order volume volatility",
        "account_age_days": "account age",
    }
    unit = (
        "percentage points"
        if feature not in {"account_age_days", "order_volume_volatility"}
        else "days" if feature == "account_age_days" else "points"
    )
    action = "increase" if direction == "increase" else "decrease"
    if unit == "days":
        return (
            f"{labels[feature]} needs to {action} by {delta:,.0f} days"
            f" (currently {current:,.0f}, needs {required:,.0f})."
        )
    return (
        f"{labels[feature]} needs to {action} by {delta * 100:.1f}"
        f" percentage points (currently {current * 100:.1f}%,"
        f" needs {required * 100:.1f}%)."
    )


def compute_gaps(
    applicant: Dict, tier_criteria: Dict
) -> BankEligibilityResult:
    gaps = []
    higher_is_better = [
        "gmv_trend_30d",
        "gmv_trend_90d",
        "payment_success_rate",
        "account_age_days",
    ]
    for feature in higher_is_better:
        required = tier_criteria.get(f"min_{feature}")
        current = float(applicant.get(feature, 0))
        if required is not None and current < required:
            delta = round(required - current, 4)
            gaps.append(
                Gap(
                    feature,
                    current,
                    required,
                    delta,
                    "increase",
                    _format_gap_message(
                        feature, delta, current, required, "increase"
                    ),
                )
            )

    lower_is_better = [
        "refund_rate",
        "chargeback_rate",
        "customer_concentration",
        "order_volume_volatility",
    ]
    for feature in lower_is_better:
        required = tier_criteria.get(f"max_{feature}")
        current = float(applicant.get(feature, 0))
        if required is not None and current > required:
            delta = round(current - required, 4)
            gaps.append(
                Gap(
                    feature,
                    current,
                    required,
                    delta,
                    "decrease",
                    _format_gap_message(
                        feature, delta, current, required, "decrease"
                    ),
                )
            )

    eligible = not gaps
    if eligible:
        message = "Eligible — meets all illustrative tier criteria."
    else:
        closeness = sum(_normalized_gap(gap, tier_criteria) for gap in gaps)
        message = (
            f"Not yet eligible — {len(gaps)} criteria unmet. Relative distance"
            f" score: {closeness:.2f} (lower = closer to qualifying)."
        )
    return BankEligibilityResult(
        tier_criteria.get("name", "Unknown Capital Tier"),
        eligible,
        gaps,
        message,
    )


def _normalized_gap(gap: Gap, bank_criteria: Dict) -> float:
    """Original normalization logic, adapted only for transaction feature
    names."""
    if gap.feature in {"gmv_trend_30d", "gmv_trend_90d"}:
        return gap.delta / max(
            abs(bank_criteria.get(f"min_{gap.feature}", 1)), 1
        )
    if gap.feature == "payment_success_rate":
        return gap.delta / 0.10
    if gap.feature in {
        "refund_rate",
        "chargeback_rate",
        "customer_concentration",
    }:
        return gap.delta / 0.10
    if gap.feature == "order_volume_volatility":
        return gap.delta / 0.10
    if gap.feature == "account_age_days":
        return gap.delta / 365
    return 0.0


def rank_all_banks(
    applicant: Dict, all_bank_criteria: List[Dict]
) -> List[BankEligibilityResult]:
    """Original API name retained for compatibility with the supplied
    module."""
    results = [compute_gaps(applicant, tier) for tier in all_bank_criteria]

    def sort_key(result: BankEligibilityResult):
        if result.eligible:
            return (0, 0)
        criteria = next(
            tier
            for tier in all_bank_criteria
            if tier.get("name") == result.bank
        )
        distance = sum(_normalized_gap(gap, criteria) for gap in result.gaps)
        return (1, distance)

    return sorted(results, key=sort_key)


def rank_all_tiers(applicant: Dict) -> List[BankEligibilityResult]:
    return rank_all_banks(applicant, CAPITAL_TIER_CRITERIA)
