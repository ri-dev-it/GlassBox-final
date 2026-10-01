"""Manual document-value consistency checks for demo purposes.

This module does not perform OCR or authenticate documents. It compares
declared numbers with actual platform transaction values supplied by the
backend from persisted merchant transaction data.
"""


def _discrepancy_pct(declared: float, expected: float) -> float:
    if expected == 0:
        return 0.0 if declared == 0 else 100.0
    return round(abs(declared - expected) / abs(expected) * 100, 2)


def check_document_consistency(
    declared: dict, actual_transaction_data: dict, threshold: float = 0.20
) -> dict:
    """Compare manual declarations with persisted transaction values."""
    comparisons = [
        (
            "gst_reported_monthly_revenue",
            "actual_monthly_gmv",
            "Declared GST revenue",
            "actual platform transaction volume",
        ),
        (
            "bank_statement_monthly_inflow",
            "actual_monthly_inflow",
            "Declared bank inflow",
            "actual platform transaction inflow",
        ),
    ]
    mismatches = []
    for declared_field, expected_field, label, expected_label in comparisons:
        declared_value = float(declared.get(declared_field, 0))
        expected_value = float(actual_transaction_data.get(expected_field, 0))
        discrepancy_pct = _discrepancy_pct(declared_value, expected_value)
        if discrepancy_pct / 100 > threshold:
            direction = (
                "lower" if declared_value < expected_value else "higher"
            )
            mismatches.append(
                {
                    "field": declared_field,
                    "declared_value": declared_value,
                    "expected_value": expected_value,
                    "discrepancy_pct": discrepancy_pct,
                    "message": (
                        f"{label} is"
                        f" {discrepancy_pct:.0f}%"
                        f" {direction} than {expected_label} — possible"
                        " under-reporting or documentation mismatch."
                    ),
                }
            )
    return {"consistent": not mismatches, "mismatches": mismatches}
