"""
Standalone re-comparison of candidate models against the current dataset,
without overwriting the saved production model. Useful for experimenting.

    cd ml
    python training/compare_models.py
"""

from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from training.train import load_data, HAS_XGBOOST  # noqa: E402
from preprocessing.preprocessing import build_preprocessor  # noqa: E402
from preprocessing.feature_config import NUMERIC_FEATURES  # noqa: E402
from preprocessing.feature_config import CATEGORICAL_FEATURES  # noqa: E402
from config import TARGET_COLUMN, RANDOM_STATE, TEST_SIZE  # noqa: E402
from training.evaluate import evaluate_model  # noqa: E402

if HAS_XGBOOST:
    from xgboost import XGBClassifier
else:
    from sklearn.ensemble import RandomForestClassifier


def main():
    df = load_data()
    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    X, y = df[feature_cols], df[TARGET_COLUMN]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    models = {
        "logistic_regression": LogisticRegression(
            max_iter=1000, random_state=RANDOM_STATE
        ),
        "xgboost" if HAS_XGBOOST else "random_forest": (
            XGBClassifier(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.05,
                random_state=RANDOM_STATE,
                eval_metric="logloss",
            )
            if HAS_XGBOOST
            else RandomForestClassifier(
                n_estimators=300, max_depth=8, random_state=RANDOM_STATE
            )
        ),
    }

    print(
        f"{'Model':<22}{'Accuracy':>10}{'Precision':>11}"
        f"{'Recall':>9}{'F1':>8}{'ROC-AUC':>10}"
    )
    for name, clf in models.items():
        pipe = Pipeline(
            [("preprocessor", build_preprocessor()), ("classifier", clf)]
        )
        pipe.fit(X_train, y_train)
        m = evaluate_model(pipe, X_test, y_test)
        print(
            f"{name:<22}{m['accuracy']:>10.4f}{m['precision']:>11.4f}"
            f"{m['recall']:>9.4f}{m['f1']:>8.4f}{m.get(
                                'roc_auc',
                                float('nan')):>10.4f}"
        )


if __name__ == "__main__":
    main()
