"""
Model evaluation utilities shared by train.py and standalone re-evaluation.
"""

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)


def evaluate_model(model, X_test, y_test) -> dict:
    """
    Compute the full metric set on a held-out test set. Every number
    here comes from actual sklearn computation against real held-out
    data -- nothing is hardcoded (see project principle: no fake metrics).
    """
    y_pred = model.predict(X_test)
    y_proba = (
        model.predict_proba(X_test)[:, 1]
        if hasattr(model, "predict_proba")
        else None
    )

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
    }

    if y_proba is not None:
        metrics["roc_auc"] = float(roc_auc_score(y_test, y_proba))

    cm = confusion_matrix(y_test, y_pred).tolist()
    metrics["confusion_matrix"] = cm  # [[TN, FP], [FN, TP]]

    return metrics


def print_metrics(name: str, metrics: dict) -> None:
    print(f"\n--- {name} ---")
    for key in ("accuracy", "precision", "recall", "f1", "roc_auc"):
        if key in metrics:
            print(f"  {key:10s}: {metrics[key]:.4f}")
    print(
        f"  confusion_matrix (TN, FP / FN, TP): {metrics['confusion_matrix']}"
    )
