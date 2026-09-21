import datetime

from flask import Blueprint, g, jsonify, request

from app.middleware.auth_middleware import roles_required
from app.models import Application, ModelVersion
from app.services import application_service
from app.services import ml_service

admin_reviews_bp = Blueprint("admin_reviews", __name__)


@admin_reviews_bp.get("/admin/applications/review")
@roles_required("admin")
def pending_reviews():
    return jsonify({"applications": application_service.get_pending_admin_reviews()}), 200


@admin_reviews_bp.post("/admin/applications/<int:application_id>/review")
@roles_required("admin")
def decide_review(application_id: int):
    data = request.get_json(silent=True) or {}
    decision = str(data.get("decision", "")).upper()
    if decision not in {"APPROVE", "REJECT"}:
        return jsonify({"error": "Decision must be APPROVE or REJECT."}), 400

    application = application_service.decide_admin_review(application_id, decision, g.current_user.id)
    if application is None:
        return jsonify({"error": "This application is not awaiting admin review."}), 409
    return jsonify({"application": application}), 200


@admin_reviews_bp.get("/admin/overview")
@roles_required("admin")
def overview():
    today = datetime.datetime.utcnow().date()
    applications = Application.query.all()
    pending = sum(1 for application in applications if application.prediction and application.prediction.decision == "REVIEW" and application.admin_decision is None)
    approved_today = sum(1 for application in applications if application.admin_decision == "APPROVE" and application.admin_decided_at and application.admin_decided_at.date() == today)
    rejected_today = sum(1 for application in applications if application.admin_decision == "REJECT" and application.admin_decided_at and application.admin_decided_at.date() == today)
    versions = ModelVersion.query.all()
    governed = [version for version in versions if version.governance_passed]
    governance_passed = all(version.governance_passed for version in versions) if versions else False
    try:
        metrics = ml_service.get_models_metrics()
        governance_passed = all(item.get("governance", {}).get("passed", False) for item in metrics.get("latest", {}).values())
    except Exception:
        pass
    return jsonify({
        "pending_review": pending,
        "approved_today": approved_today,
        "rejected_today": rejected_today,
        "active_models": sum(1 for version in versions if version.is_active),
        "governed_models": len(governed),
        "governance_passed": governance_passed,
    }), 200