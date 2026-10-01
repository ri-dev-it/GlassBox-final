"""Explainable fraud-pattern detection for daily merchant transactions.

This is a defensive rules engine, not a model for evading fraud controls.
Each signal is derived from auditable rolling statistics and contributes to a
bounded score in the range 0.0 to 1.0.
"""

from __future__ import annotations

from datetime import date
from statistics import mean, pstdev

FRAUD_SCORE_THRESHOLD = 0.5


def _number(record: dict, field: str) -> float:
    try:
        return max(0.0, float(record.get(field, 0)))
    except (TypeError, ValueError):
        return 0.0


def _day(record: dict) -> str:
    value = record.get("date")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def detect_fraud_signals(transaction_history: list[dict]) -> dict:
    """Detect suspicious daily behavior with transparent rolling rules.

    ``transaction_history`` is expected to be chronological daily records with
    ``date``, ``gmv``, ``refund_count``, ``chargeback_count``, and
    ``order_count`` fields. The score is additive by rule and capped at 1.0;
    it is not a probability or a finding of fraud.
    """
    records = sorted(transaction_history, key=_day)
    flags: list[str] = []
    flagged_days: set[str] = set()
    score = 0.0

    # Refund spikes compare each day with the preceding 30 days only.
    refund_spike_days: set[str] = set()
    for index, record in enumerate(records):
        trailing = [
            _number(item, "refund_count")
            for item in records[max(0, index - 30): index]
        ]
        if len(trailing) < 7:
            continue
        current = _number(record, "refund_count")
        threshold = mean(trailing) + 3 * pstdev(trailing)
        if current > threshold and current > mean(trailing):
            day = _day(record)
            refund_spike_days.add(day)
            flags.append(
                f"Refund spike on {day}: {current:.0f}"
                " refunds exceeded the trailing 30-day baseline."
            )
            flagged_days.add(day)
    if refund_spike_days:
        score += 0.25

    # Chargeback clusters mark every day inside a rolling seven-day cluster.
    cluster_days: set[str] = set()
    for end in range(len(records)):
        start = max(0, end - 6)
        window = records[start: end + 1]
        total = sum(_number(item, "chargeback_count") for item in window)
        if total >= 3:
            cluster_days.update(
                _day(item)
                for item in window
                if _number(item, "chargeback_count") > 0
            )
    if cluster_days:
        flags.append(
            f"Chargeback cluster: {len(cluster_days)} flagged"
            " day(s) contained 3 or more chargebacks in a rolling 7-day"
            " window."
        )
        flagged_days.update(cluster_days)
        score += 0.25

    # Velocity compares order volume with the preceding seven days.
    velocity_days: set[str] = set()
    for index, record in enumerate(records):
        trailing = [
            _number(item, "order_count")
            for item in records[max(0, index - 7): index]
        ]
        if len(trailing) < 3:
            continue
        baseline = mean(trailing)
        current = _number(record, "order_count")
        if current > 4 * baseline and current > baseline:
            day = _day(record)
            velocity_days.add(day)
            flags.append(
                f"Velocity anomaly on {day}:"
                f" {current:.0f} orders exceeded four"
                " times the trailing 7-day average."
            )
            flagged_days.add(day)
    if velocity_days:
        score += 0.25

    # A sharp GMV jump followed by elevated refunds within the next three days.
    mismatch_days: set[str] = set()
    for index, record in enumerate(records[:-1]):
        prior_gmv = [
            _number(item, "gmv") for item in records[max(0, index - 7): index]
        ]
        current_gmv = _number(record, "gmv")
        if len(prior_gmv) < 3 or current_gmv <= 1.5 * mean(prior_gmv):
            continue
        follow_up = records[index + 1: min(len(records), index + 4)]
        if any(
            _number(item, "refund_count")
            / max(_number(item, "order_count"), 1)
            >= 0.15
            for item in follow_up
        ):
            day = _day(record)
            mismatch_days.add(day)
            mismatch_days.update(_day(item) for item in follow_up)
            flags.append(
                f"GMV-refund mismatch near {day}: a sharp GMV increase was"
                " followed by an elevated refund rate."
            )
            flagged_days.update(mismatch_days)
    if mismatch_days:
        score += 0.25

    return {
        "fraud_score": round(min(score, 1.0), 4),
        "flags": flags,
        "flagged_days": sorted(flagged_days),
    }
