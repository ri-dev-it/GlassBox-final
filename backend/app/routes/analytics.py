import json
from collections import Counter
from flask import Blueprint, g, jsonify

from app.middleware.auth_middleware import roles_required
from app.models import MerchantFraudCheck
from app.services import ml_service, application_service
from app.services.ml_service import MLServiceError

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.get("/analytics/model")
@roles_required("loan_officer", "admin")
def model_analytics():
    try:
        metadata = ml_service.get_model_metadata()
    except MLServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(metadata), 200


@analytics_bp.get("/analytics/models")
@roles_required("loan_officer", "admin")
def models_analytics():
    try:
        metrics = ml_service.get_models_metrics()
    except MLServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(metrics), 200


@analytics_bp.get("/analytics/shap")
@roles_required("loan_officer", "admin")
def global_shap():
    try:
        importance = ml_service.get_global_shap()
    except MLServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify({"global_importance": importance}), 200


@analytics_bp.get("/analytics/applications-summary")
@roles_required("loan_officer", "admin")
def applications_summary():
    applications = application_service.get_all_applications()
    total = len(applications)
    approved = sum(1 for a in applications if a.get("prediction") and a["prediction"]["decision"] in {"APPROVE", "APPROVED"})
    rejected = sum(1 for a in applications if a.get("prediction") and a["prediction"]["decision"] in {"DECLINE", "REJECTED"})
    review = sum(1 for a in applications if a.get("prediction") and a["prediction"]["decision"] == "REVIEW")
    return jsonify({
        "total": total,
        "approved": approved,
        "rejected": rejected,
        "review": review,
        "approval_rate": round(approved / total, 4) if total else None,
    }), 200


@analytics_bp.get("/dashboard/stats")
@roles_required("applicant", "loan_officer", "admin")
def dashboard_stats():
    applications = (application_service.get_applications_for_user(g.current_user)
                    if g.current_user.role in {"applicant", "client"} else application_service.get_all_applications())
    decisions = Counter(a["prediction"]["decision"] for a in applications if a.get("prediction"))
    risks = Counter(a["prediction"].get("risk_level", "MEDIUM") for a in applications if a.get("prediction"))
    fraud_flags = Counter()
    for fraud_check in MerchantFraudCheck.query.all():
        fraud_flags.update(json.loads(fraud_check.flags_json or "[]"))
    return jsonify({
        "total": len(applications),
        "approved": decisions["APPROVE"] + decisions["APPROVED"],
        "rejected": decisions["DECLINE"] + decisions["REJECTED"],
        "under_review": decisions["REVIEW"] + sum(1 for a in applications if not a.get("prediction")),
        "approval_rate": round(decisions["APPROVE"] / len(applications) * 100, 1) if applications else None,
        "risk_distribution": {"low": risks["LOW"], "medium": risks["MEDIUM"], "high": risks["HIGH"]},
        "fraud_flag_summary": [{"flag": flag, "count": count} for flag, count in fraud_flags.most_common()],
        "recent_applications": applications[:5],
    }), 200
