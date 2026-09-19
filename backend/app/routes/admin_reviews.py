from flask import Blueprint, g, jsonify, request

from app.middleware.auth_middleware import roles_required
from app.services import application_service

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