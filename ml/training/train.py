"""
Reproducible training pipeline (Milestone 5).

    cd ml
    python data/download_dataset.py      # once, needs internet
    python training/train.py

Steps (per project spec section 10):
  load -> inspect -> clean -> split features/target -> train/test split
  -> train baseline (Logistic Regression) -> train stronger model (XGBoost,
  falls back to RandomForest if xgboost isn't installed) -> compare on
  real held-out metrics -> select the actual winner -> save pipeline + metadata.

The saved artifact is a single sklearn Pipeline containing BOTH the
fitted preprocessor and the fitted classifier, so prediction time reuses
the exact training-time preprocessing (see preprocessing/preprocessing.py).
"""

import json
import os
import sys
import time

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RAW_DATA_FILE, MODEL_FILE, METADATA_FILE, TARGET_COLUMN, RANDOM_STATE, TEST_SIZE, TEST_SET_WITH_PREDICTIONS  # noqa: E402
from preprocessing.preprocessing import build_preprocessor  # noqa: E402
from preprocessing.feature_config import NUMERIC_FEATURES, CATEGORICAL_FEATURES, PROTECTED_ATTRIBUTE_COLUMN  # noqa: E402
from training.evaluate import evaluate_model, print_metrics  # noqa: E402
from fairness.fairness_analyzer import run_fairness_analysis  # noqa: E402
from fairness.governance_gate import check_governance  # noqa: E402
from versioning.registry import register_model_version  # noqa: E402

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    from sklearn.ensemble import RandomForestClassifier
    HAS_XGBOOST = False


def load_data() -> pd.DataFrame:
    if not os.path.exists(RAW_DATA_FILE):
        raise FileNotFoundError(
            f"{RAW_DATA_FILE} not found. Run `python data/download_dataset.py` "
            "first (requires internet access to fetch the UCI dataset)."
        )
    df = pd.read_csv(RAW_DATA_FILE)
    print(f"Loaded {len(df)} rows, {df.shape[1]} columns")
    print(f"Missing values total: {df.isna().sum().sum()}")
    print(f"Class distribution:\n{df[TARGET_COLUMN].value_counts(normalize=True)}")
    return df


def main():
    df = load_data()

    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    X = df[feature_cols]
    y = df[TARGET_COLUMN]
    protected = df[PROTECTED_ATTRIBUTE_COLUMN]

    X_train, X_test, y_train, y_test, protected_train, protected_test = train_test_split(
        X, y, protected, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y,
    )
    print(f"\nTrain size: {len(X_train)}  Test size: {len(X_test)}")

    candidates = {}

    # --- Baseline: Logistic Regression ---
    baseline_pipeline = Pipeline(steps=[
        ("preprocessor", build_preprocessor()),
        ("classifier", LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)),
    ])
    baseline_pipeline.fit(X_train, y_train)
    candidates["logistic_regression"] = baseline_pipeline

    # --- Stronger model: XGBoost (or RandomForest fallback) ---
    if HAS_XGBOOST:
        strong_model = XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            random_state=RANDOM_STATE, eval_metric="logloss",
        )
        strong_name = "xgboost"
    else:
        strong_model = RandomForestClassifier(n_estimators=300, max_depth=8, random_state=RANDOM_STATE)
        strong_name = "random_forest"
        print("\n[warning] xgboost not installed -- falling back to RandomForest. "
              "Install xgboost for the intended stronger model.")

    strong_pipeline = Pipeline(steps=[
        ("preprocessor", build_preprocessor()),
        ("classifier", strong_model),
    ])
    strong_pipeline.fit(X_train, y_train)
    candidates[strong_name] = strong_pipeline

    # --- Evaluate both on the SAME held-out test set ---
    results = {}
    for name, pipeline in candidates.items():
        metrics = evaluate_model(pipeline, X_test, y_test)
        results[name] = metrics
        print_metrics(name, metrics)

    # --- Select winner by F1 (imbalanced classes -- accuracy alone is misleading) ---
    winner_name = max(results, key=lambda n: results[n]["f1"])
    winner_pipeline = candidates[winner_name]
    print(f"\nSelected final model: {winner_name} (highest F1 = {results[winner_name]['f1']:.4f})")

    # --- Save a labeled copy of the test set + predictions, for the fairness dashboard ---
    test_out = X_test.copy()
    test_out[TARGET_COLUMN] = y_test.values
    test_out[PROTECTED_ATTRIBUTE_COLUMN] = protected_test.values
    test_out["prediction"] = winner_pipeline.predict(X_test)
    test_out.to_csv(TEST_SET_WITH_PREDICTIONS, index=False)
    print(f"Saved labeled test set + predictions to {TEST_SET_WITH_PREDICTIONS}")

    fairness_metrics = run_fairness_analysis()
    governance = check_governance(fairness_metrics)
    if not governance["passed"]:
        print(f"[governance] Income model was not saved because fairness checks failed: {governance['failed_checks']}")
        return

    # --- Save model only after governance passes ---
    joblib.dump(winner_pipeline, MODEL_FILE)
    print(f"Saved model pipeline to {MODEL_FILE}")

    # --- Save metadata ---
    metadata = {
        "final_model": winner_name,
        "precision": results[winner_name]["precision"],
        "recall": results[winner_name]["recall"],
        "f1": results[winner_name]["f1"],
        "roc_auc": results[winner_name]["roc_auc"],
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset_size": len(df),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "feature_columns": feature_cols,
        "target_column": TARGET_COLUMN,
        "protected_attribute": PROTECTED_ATTRIBUTE_COLUMN,
        "model_comparison": results,
        "xgboost_available": HAS_XGBOOST,
        "governance": {
            **governance,
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata to {METADATA_FILE}")
    version = register_model_version("credit_history", MODEL_FILE, metadata)
    print(f"Registered credit_history version {version['version_number']} ({'active' if version['is_active'] else 'rejected'})")


if __name__ == "__main__":
    main()
