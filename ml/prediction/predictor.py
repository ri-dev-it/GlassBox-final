"""
Loads the saved model pipeline ONCE and serves predictions.
The backend must not retrain or reimplement preprocessing -- it just
calls predict() from here (see backend/app/services/ml_service.py).
"""

import json
import os
import sys
from functools import lru_cache

import joblib
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODEL_FILE, METADATA_FILE  # noqa: E402
from decisioning.bands import decide  # noqa: E402
from preprocessing.feature_config import NUMERIC_FEATURES, CATEGORICAL_FEATURES  # noqa: E402

FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES


class ModelNotTrainedError(RuntimeError):
    """Raised when a prediction is requested before train.py has been run."""


@lru_cache(maxsize=1)
def load_pipeline():
    if not os.path.exists(MODEL_FILE):
        raise ModelNotTrainedError(
            f"No trained model found at {MODEL_FILE}. Run "
            "`python data/download_dataset.py && python training/train.py` inside ml/ first."
        )
    metadata = load_metadata()
    governance = metadata.get("governance")
    if governance is not None and not governance.get("passed", False):
        raise ModelNotTrainedError(
            "Income model is blocked from serving because fairness governance failed: "
            f"{governance.get('failed_checks', [])}"
        )
    return joblib.load(MODEL_FILE)


@lru_cache(maxsize=1)
def load_metadata() -> dict:
    if not os.path.exists(METADATA_FILE):
        raise ModelNotTrainedError(f"No metadata found at {METADATA_FILE}. Train the model first.")
    with open(METADATA_FILE) as f:
        return json.load(f)


def applicant_to_dataframe(applicant: dict) -> pd.DataFrame:
    """Build a single-row DataFrame in the exact column order the model expects."""
    row = {col: applicant.get(col) for col in FEATURE_COLUMNS}
    return pd.DataFrame([row], columns=FEATURE_COLUMNS)


def predict(applicant: dict) -> dict:
    """
    applicant: dict of raw feature_name -> value (matching feature_config.FEATURES).
    Returns: {"prediction": "APPROVED"|"REJECTED", "probability": float}
    """
    pipeline = load_pipeline()
    if set(getattr(pipeline, "feature_names_in_", FEATURE_COLUMNS)) != set(FEATURE_COLUMNS):
        raise ModelNotTrainedError("Model schema does not match BANK_DOCUMENT_FEATURES. Retrain the matching model before serving.")
    X = applicant_to_dataframe(applicant)

    proba = pipeline.predict_proba(X)[0]
    approved_probability = float(proba[1])  # class 1 = good credit / approve
    decision = decide(1 - approved_probability)

    return {
        "prediction": decision,
        "probability": round(approved_probability, 4),
    }
