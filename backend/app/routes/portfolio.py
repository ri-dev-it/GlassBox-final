from flask import Blueprint, jsonify

from app.middleware.auth_middleware import roles_required
from app.services import ml_service
from app.services.ml_service import MLServiceError

portfolio_bp = Blueprint("portfolio", __name__)


@portfolio_bp.get("/portfolio/exposure")
@roles_required("loan_officer", "admin")
def exposure():
    try:
        return jsonify(ml_service.get_portfolio_exposure()), 200
    except MLServiceError as error:
        return jsonify({"error": error.message}), error.status_code
