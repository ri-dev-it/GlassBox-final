"""
Validates a loan application payload against ml/preprocessing/feature_config.py
-- the single source of truth for what fields the model expects, so the
backend never drifts out of sync with the model (spec section 15: never
trust frontend validation alone).
"""

import os
import sys

_ML_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml")
)
if _ML_ROOT not in sys.path:
    sys.path.insert(0, _ML_ROOT)

from preprocessing.feature_config import FEATURES  # noqa: E402


def validate_application_payload(data: dict) -> list[str]:
    errors = []

    for field, cfg in FEATURES.items():
        if field not in data or data[field] in (None, ""):
            errors.append(f"'{field}' is required.")
            continue

        value = data[field]

        if cfg["category"] == "numeric":
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                errors.append(f"'{field}' must be a number.")
                continue
            if "min" in cfg and numeric_value < cfg["min"]:
                errors.append(f"'{field}' must be >= {cfg['min']}.")
            if "max" in cfg and numeric_value > cfg["max"]:
                errors.append(f"'{field}' must be <= {cfg['max']}.")

        elif cfg["category"] == "categorical":
            if value not in cfg["options"]:
                errors.append(f"'{field}' must be one of {cfg['options']}.")

    return errors
