from flask import Blueprint, g, jsonify, request

from app.middleware.auth_middleware import roles_required
from app.schemas.application_schema import validate_application_payload
from app.services import ml_service
from app.services.ml_service import MLServiceError

explanations_bp = Blueprint("explanations", __name__)


@explanations_bp.get("/explain/<int:application_id>")
@roles_required("applicant", "loan_officer", "admin")
def grounded_application_explanation(application_id):
    try:
        result = ml_service.get_grounded_application_explanation(application_id, g.current_user)
    except MLServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    if result is None:
        return jsonify({"error": "Application or SHAP explanation not found."}), 404
    return jsonify(result), 200


@explanations_bp.get("/explain/merchant/<merchant_id>")
@roles_required("applicant", "loan_officer", "admin")
def grounded_merchant_explanation(merchant_id):
    try:
        result = ml_service.get_grounded_merchant_explanation(merchant_id)
    except MLServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    if result is None:
        return jsonify({"error": "Merchant explanation not found."}), 404
    return jsonify(result), 200


def _predict_and_validate(data: dict):
    errors = validate_application_payload(data)
    if errors:
        return None, (jsonify({"errors": errors}), 400)
    result = ml_service.predict_application(data)
    return result, None


@explanations_bp.post("/explain/shap")
@roles_required("applicant", "loan_officer", "admin")
def explain_shap():
    """Computes a fresh local SHAP explanation for the given applicant data."""
    data = request.get_json(silent=True) or {}
    result, error_response = _predict_and_validate(data)
    if error_response:
        return error_response
    try:
        shap_result = ml_service.get_shap_explanation(data, result["prediction"], result["probability"])
    except MLServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify({"prediction": result, **shap_result}), 200


@explanations_bp.post("/explain/lime")
@roles_required("applicant", "loan_officer", "admin")
def explain_lime():
    """Computes a fresh local LIME explanation for the given applicant data."""
    data = request.get_json(silent=True) or {}
    result, error_response = _predict_and_validate(data)
    if error_response:
        return error_response
    try:
        lime_result = ml_service.get_lime_explanation(data, result["prediction"], result["probability"])
    except MLServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify({"prediction": result, **lime_result}), 200


@explanations_bp.get("/explain/partial-dependence")
@roles_required("applicant", "loan_officer", "admin")
def partial_dependence():
    try:
        curves = ml_service.get_partial_dependence()
    except MLServiceError as error:
        return jsonify({"error": error.message}), error.status_code
    return jsonify({"curves": curves}), 200
