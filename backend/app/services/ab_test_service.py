import datetime
import random

from app.extensions import db
from app.models import ABTest, ABTestResult, ModelVersion


def canonical_model_name(model_name: str) -> str | None:
    return {
        "credit_history": "credit_history",
        "income_model": "credit_history",
        "transaction": "transaction",
        "transaction_model": "transaction",
    }.get(model_name)


def start_test(model_name: str, payload: dict) -> ABTest:
    canonical = canonical_model_name(model_name)
    if not canonical:
        raise ValueError("Unknown model name.")
    try:
        control_id = int(payload.get("control_version_id", payload.get("control_model_version_id")))
        treatment_id = int(payload.get("treatment_version_id", payload.get("treatment_model_version_id")))
        traffic = float(payload.get("traffic_percentage", payload.get("traffic_split", 50)))
    except (KeyError, TypeError, ValueError):
        raise ValueError("control_version_id, treatment_version_id, and traffic_percentage are required.")
    if control_id == treatment_id or not 0 <= traffic <= 100:
        raise ValueError("Versions must differ and traffic_percentage must be between 0 and 100.")
    control = ModelVersion.query.filter_by(id=control_id, model_name=canonical).first()
    treatment = ModelVersion.query.filter_by(id=treatment_id, model_name=canonical).first()
    if not control or not treatment:
        raise ValueError("Both model versions must exist for the requested model.")
    if not control.governance_passed or not treatment.governance_passed:
        raise ValueError("Only model versions that passed governance can be tested.")
    if ABTest.query.filter_by(model_name=canonical, status="active").first():
        raise ValueError("An active A/B test already exists for this model.")
    test = ABTest(
        model_name=canonical,
        name=str(payload.get("name") or f"{canonical} A/B test"),
        control_version_id=control.id,
        treatment_version_id=treatment.id,
        traffic_percentage=traffic,
    )
    db.session.add(test)
    db.session.commit()
    return test


def get_assignment(model_name: str) -> dict | None:
    canonical = canonical_model_name(model_name)
    test = ABTest.query.filter_by(model_name=canonical, status="active").first() if canonical else None
    if not test:
        return None
    treatment = random.random() * 100 < test.traffic_percentage
    variant = "treatment" if treatment else "control"
    version = test.treatment_version if treatment else test.control_version
    return {"test": test, "variant": variant, "version": version}


def record_result(assignment: dict, prediction, decision: str, probability: float) -> ABTestResult:
    result = ABTestResult(
        ab_test_id=assignment["test"].id,
        prediction_id=prediction.id if prediction is not None else None,
        variant=assignment["variant"],
        model_version_id=assignment["version"].id,
        decision=decision,
        probability=probability,
    )
    db.session.add(result)
    return result


def get_results(model_name: str, test_id: int) -> dict | None:
    canonical = canonical_model_name(model_name)
    test = ABTest.query.filter_by(id=test_id, model_name=canonical).first() if canonical else None
    if not test:
        return None
    results = ABTestResult.query.filter_by(ab_test_id=test.id).order_by(ABTestResult.created_at.asc()).all()
    by_variant = {}
    for variant in ("control", "treatment"):
        rows = [row for row in results if row.variant == variant]
        approved = sum(row.decision in {"APPROVE", "APPROVED"} for row in rows)
        by_variant[variant] = {
            "count": len(rows),
            "approved": approved,
            "approval_rate": approved / len(rows) if rows else None,
            "average_probability": sum(row.probability for row in rows) / len(rows) if rows else None,
        }
    return {"test": test.to_dict(), "summary": by_variant, "results": [row.to_dict() for row in results]}


def list_tests(model_name: str) -> list[ABTest]:
    canonical = canonical_model_name(model_name)
    return ABTest.query.filter_by(model_name=canonical).order_by(ABTest.started_at.desc()).all() if canonical else []


def end_test(model_name: str, test_id: int) -> ABTest | None:
    canonical = canonical_model_name(model_name)
    test = ABTest.query.filter_by(id=test_id, model_name=canonical, status="active").first() if canonical else None
    if not test:
        return None
    test.status = "ended"
    test.ended_at = datetime.datetime.utcnow()
    db.session.commit()
    return test