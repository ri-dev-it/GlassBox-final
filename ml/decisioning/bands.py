"""Convert probability of default into an approve/review/decline band."""

import os
from typing import Literal

DecisionBand = Literal["APPROVE", "REVIEW", "DECLINE"]

APPROVE_BELOW = float(os.environ.get("APPROVE_BELOW", "0.15"))
DECLINE_AT_OR_ABOVE = float(os.environ.get("DECLINE_AT_OR_ABOVE", "0.55"))


def decide(
    probability_of_default: float,
    approve_below: float = APPROVE_BELOW,
    decline_at_or_above: float = DECLINE_AT_OR_ABOVE,
) -> DecisionBand:
    """Return APPROVE, REVIEW, or DECLINE for a default probability."""
    if not 0 <= probability_of_default <= 1:
        raise ValueError("probability_of_default must be between 0 and 1")
    if not 0 <= approve_below < decline_at_or_above <= 1:
        raise ValueError(
            "decision thresholds must satisfy 0 <= approve_below <"
            " decline_at_or_above <= 1"
        )
    if probability_of_default < approve_below:
        return "APPROVE"
    if probability_of_default >= decline_at_or_above:
        return "DECLINE"
    return "REVIEW"
