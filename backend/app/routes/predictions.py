from flask import Blueprint, current_app, g, jsonify, request

from app.middleware.auth_middleware import roles_required
from app.schemas.application_schema import validate_application_payload
from app.services import application_service
from app.services.indian_feature_mapper import map_indian_ui_to_model
from app.services.ml_service import MLServiceError

predictions_bp = Blueprint("predictions", __name__)


@predictions_bp.post("/predict")
@roles_required("applicant", "loan_officer", "admin")
def predict():
    data = request.get_json(silent=True) or {}
    loan_type = str(data.pop("loan_type", "PERSONAL_LOAN")).upper()
    submission_details = data.pop("submission_details", {})
    if not isinstance(submission_details, dict):
        return jsonify({"error": "submission_details must be an object."}), 400
    allowed_loan_types = {"PERSONAL_LOAN", "CAR_LOAN", "BIKE_LOAN", "HOME_LOAN", "BUSINESS_CAPITAL", "EDUCATION_LOAN"}
    if loan_type not in allowed_loan_types:
        return jsonify({"error": "Unsupported loan type."}), 400
    model_features = map_indian_ui_to_model(data)
    errors = validate_application_payload(model_features)
    if errors:
        return jsonify({"errors": errors}), 400

    try:
        result = application_service.submit_application(g.current_user, model_features, loan_type, submission_details)
    except MLServiceError as e:
        from app.extensions import db
        db.session.rollback()
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        # Do not turn an ML/explainer failure into an empty or misleading
        # response.  Keep the full traceback in the Flask log and provide a
        # useful development response to the React error handler.
        current_app.logger.exception("Loan analysis generation failed")
        from app.extensions import db
        db.session.rollback()
        response = {"error": "Analysis generation failed."}
        if current_app.debug:
            response["details"] = str(e)
        return jsonify(response), 500

    return jsonify(result), 201
