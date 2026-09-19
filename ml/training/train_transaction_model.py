"""Train the additive transaction-behavior model on synthetic demo data.

The generated merchant data is simulated and is not real Razorpay data.
The original income-based loan model and training script are independent.
"""

import json
import os
import sys
import time

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (  # noqa: E402
    RANDOM_STATE,
    TEST_SIZE,
    TRANSACTION_METADATA_FILE,
    TRANSACTION_MODEL_FILE,
    TRANSACTION_REFERENCE_FILE,
)
from data.synthetic_transactions import TRANSACTION_FEATURES, generate_synthetic_transactions  # noqa: E402
from training.evaluate import evaluate_model, print_metrics  # noqa: E402
from fairness.fairness_analyzer import run_fairness_analysis_for_data  # noqa: E402
from fairness.governance_gate import check_governance  # noqa: E402
from versioning.registry import register_model_version  # noqa: E402

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    from sklearn.ensemble import RandomForestClassifier
    HAS_XGBOOST = False


TARGET_COLUMN = "defaulted"


def _build_pipeline(classifier) -> Pipeline:
    preprocessor = ColumnTransformer([
        ("numeric", StandardScaler(), TRANSACTION_FEATURES),
    ])
    return Pipeline(steps=[("preprocessor", preprocessor), ("classifier", classifier)])


def main() -> None:
    # Synthetic data only: this is a demo model, not a Razorpay underwriting model.
    df = generate_synthetic_transactions()
    df.to_csv(TRANSACTION_REFERENCE_FILE, index=False)
    X = df[TRANSACTION_FEATURES]
    y = df[TARGET_COLUMN]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y,
    )

    candidates = {
        "logistic_regression": _build_pipeline(
            LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)
        ),
    }
    if HAS_XGBOOST:
        candidates["xgboost"] = _build_pipeline(XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            random_state=RANDOM_STATE, eval_metric="logloss",
        ))
    else:
        candidates["random_forest"] = _build_pipeline(
            RandomForestClassifier(n_estimators=300, max_depth=8, random_state=RANDOM_STATE)
        )

    results = {}
    for name, pipeline in candidates.items():
        pipeline.fit(X_train, y_train)
        results[name] = evaluate_model(pipeline, X_test, y_test)
        print_metrics(name, results[name])

    winner_name = max(results, key=lambda name: (results[name]["f1"], results[name].get("roc_auc", 0)))
    winner_pipeline = candidates[winner_name]
    fairness_metrics = run_fairness_analysis_for_data(
        y_test, winner_pipeline.predict(X_test),
        X_test["account_age_days"] >= X_test["account_age_days"].median(),
        "account_age_band",
    )
    governance = check_governance(fairness_metrics)
    if not governance["passed"]:
        print(f"[governance] Transaction model was not saved because fairness checks failed: {governance['failed_checks']}")
        return
    joblib.dump(winner_pipeline, TRANSACTION_MODEL_FILE)

    metadata = {
        "synthetic_data": True,
        "data_disclaimer": "Simulated merchant transactions for demo purposes; not real Razorpay data.",
        "final_model": winner_name,
        "precision": results[winner_name]["precision"],
        "recall": results[winner_name]["recall"],
        "f1": results[winner_name]["f1"],
        "roc_auc": results[winner_name]["roc_auc"],
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset_size": len(df),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "feature_columns": TRANSACTION_FEATURES,
        "target_column": TARGET_COLUMN,
        "model_comparison": results,
        "xgboost_available": HAS_XGBOOST,
        "governance": {
            **governance,
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }
    with open(TRANSACTION_METADATA_FILE, "w") as file:
        json.dump(metadata, file, indent=2)
    print(f"Saved synthetic transaction model to {TRANSACTION_MODEL_FILE}")
    print(f"Saved transaction metadata to {TRANSACTION_METADATA_FILE}")
    version = register_model_version("transaction", TRANSACTION_MODEL_FILE, metadata)
    print(f"Registered transaction version {version['version_number']} ({'active' if version['is_active'] else 'rejected'})")


if __name__ == "__main__":
    main()