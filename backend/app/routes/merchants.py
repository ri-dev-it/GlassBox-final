from flask import Blueprint, jsonify, request

from app.middleware.auth_middleware import roles_required
from app.services import ml_service
from app.services.ml_service import MLServiceError

merchants_bp = Blueprint("merchants", __name__)


@merchants_bp.post("/merchants/assess")
@roles_required("applicant", "loan_officer", "admin")
def assess_merchant():
    data = request.get_json(silent=True) or {}
    try:
        result = ml_service.assess_merchant(data)
    except MLServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    return jsonify(result), 200


@merchants_bp.post("/merchants/fraud-check")
@roles_required("applicant", "loan_officer", "admin")
def fraud_check():
    data = request.get_json(silent=True) or {}
    try:
        result = ml_service.check_merchant_fraud(
            data.get("merchant_id"), data.get("transaction_history")
        )
    except MLServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    return jsonify(result), 200


@merchants_bp.get("/merchants/<merchant_id>/tier-gaps")
@roles_required("applicant", "loan_officer", "admin")
def tier_gaps(merchant_id):
    try:
        supplied_features = request.args.to_dict()
        return (
            jsonify(
                ml_service.get_merchant_tier_gaps(
                    merchant_id, supplied_features or None
                )
            ),
            200,
        )
    except MLServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@merchants_bp.post("/merchants/<merchant_id>/verify-documents")
@roles_required("applicant", "loan_officer", "admin")
def verify_documents(merchant_id):
    data = request.get_json(silent=True) or {}
    try:
        return (
            jsonify(ml_service.verify_merchant_documents(merchant_id, data)),
            200,
        )
    except MLServiceError as error:
        return jsonify({"error": error.message}), error.status_code


@merchants_bp.get("/merchants/<merchant_id>/verify-documents")
@roles_required("applicant", "loan_officer", "admin")
def get_verified_documents(merchant_id):
    try:
        result = ml_service.get_merchant_document_verification(merchant_id)
        return (
            jsonify(
                result or {"merchant_id": merchant_id, "verification": None}
            ),
            200,
        )
    except MLServiceError as error:
        return jsonify({"error": error.message}), error.status_code
