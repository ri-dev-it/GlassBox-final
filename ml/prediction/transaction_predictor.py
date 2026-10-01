"""Prediction helpers for the separate synthetic merchant-risk model."""

import json
import os
from functools import lru_cache

import joblib
import pandas as pd

from config import (
    TRANSACTION_METADATA_FILE,
    TRANSACTION_MODEL_FILE,
    TRANSACTION_REFERENCE_FILE,
)
from data.synthetic_transactions import TRANSACTION_FEATURES
from decisioning.bands import decide


class TransactionModelNotTrainedError(RuntimeError):
    """Raised when the synthetic transaction model has not been trained."""


@lru_cache(maxsize=1)
def load_transaction_pipeline():
    if not os.path.exists(TRANSACTION_MODEL_FILE):
        raise TransactionModelNotTrainedError(
            f"No transaction model found at {TRANSACTION_MODEL_FILE}. "
            "Run `python training/train_transaction_model.py` inside ml/."
        )
    metadata = load_transaction_metadata()
    governance = metadata.get("governance")
    if governance is not None and not governance.get("passed", False):
        raise TransactionModelNotTrainedError(
            "Transaction model is blocked from serving because fairness"
            f" governance failed: {governance.get('failed_checks', [])}"
        )
    return joblib.load(TRANSACTION_MODEL_FILE)


@lru_cache(maxsize=1)
def load_transaction_metadata() -> dict:
    if not os.path.exists(TRANSACTION_METADATA_FILE):
        raise TransactionModelNotTrainedError(
            "No transaction model metadata found. Train the transaction model"
            " first."
        )
    with open(TRANSACTION_METADATA_FILE) as file:
        return json.load(file)


@lru_cache(maxsize=1)
def load_transaction_reference() -> pd.DataFrame:
    if not os.path.exists(TRANSACTION_REFERENCE_FILE):
        raise TransactionModelNotTrainedError(
            "Synthetic transaction reference data not found. Train the"
            " transaction model first."
        )
    return pd.read_csv(TRANSACTION_REFERENCE_FILE)


def transaction_to_dataframe(features: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [{column: features.get(column) for column in TRANSACTION_FEATURES}],
        columns=TRANSACTION_FEATURES,
    )


def predict_transaction(features: dict) -> dict:
    pipeline = load_transaction_pipeline()
    probability = float(
        pipeline.predict_proba(transaction_to_dataframe(features))[0][1]
    )
    return {
        "prediction": decide(probability),
        "probability": round(probability, 4),
    }
