from flask import Blueprint, jsonify, request

from app.extensions import db
from app.middleware.auth_middleware import roles_required
from app.models import ModelVersion
from app.services import ab_test_service


models_bp = Blueprint("models", __name__)


def _canonical_name(model_name: str) -> str | None:
    return {"credit_history": "credit_history", "income_model": "credit_history", "transaction": "transaction", "transaction_model": "transaction"}.get(model_name)


@models_bp.get("/models/<string:model_name>/versions")
@roles_required("admin", "loan_officer")
def list_versions(model_name: str):
    canonical = _canonical_name(model_name)
    if not canonical:
        return jsonify({"error": "Unknown model name."}), 404
    versions = ModelVersion.query.filter_by(model_name=canonical).order_by(ModelVersion.version_number.desc()).all()
    return jsonify({"model_name": canonical, "versions": [version.to_dict() for version in versions]}), 200


@models_bp.post("/models/<string:model_name>/versions/<int:version_id>/activate")
@roles_required("admin", "loan_officer")
def activate_version(model_name: str, version_id: int):
    canonical = _canonical_name(model_name)
    version = ModelVersion.query.filter_by(id=version_id, model_name=canonical).first() if canonical else None
    if not version:
        return jsonify({"error": "Model version not found."}), 404
    if not version.governance_passed:
        return jsonify({"error": "Only versions that passed governance can be activated."}), 409
    ModelVersion.query.filter_by(model_name=canonical).update({"is_active": False})
    version.is_active = True
    db.session.commit()
    return jsonify({"version": version.to_dict()}), 200


@models_bp.get("/models/<string:model_name>/ab-tests")
@roles_required("admin", "loan_officer")
def list_ab_tests(model_name: str):
    if not ab_test_service.canonical_model_name(model_name):
        return jsonify({"error": "Unknown model name."}), 404
    return jsonify({"tests": [test.to_dict() for test in ab_test_service.list_tests(model_name)]}), 200


@models_bp.post("/models/<string:model_name>/ab-tests")
@roles_required("admin", "loan_officer")
def start_ab_test(model_name: str):
    try:
        test = ab_test_service.start_test(model_name, request.get_json(silent=True) or {})
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"test": test.to_dict()}), 201


@models_bp.get("/models/<string:model_name>/ab-tests/<int:test_id>")
@models_bp.get("/models/<string:model_name>/ab-tests/<int:test_id>/results")
@roles_required("admin", "loan_officer")
def ab_test_results(model_name: str, test_id: int):
    results = ab_test_service.get_results(model_name, test_id)
    if results is None:
        return jsonify({"error": "A/B test not found."}), 404
    return jsonify(results), 200


@models_bp.post("/models/<string:model_name>/ab-tests/<int:test_id>/end")
@roles_required("admin", "loan_officer")
def end_ab_test(model_name: str, test_id: int):
    test = ab_test_service.end_test(model_name, test_id)
    if test is None:
        return jsonify({"error": "Active A/B test not found."}), 404
    return jsonify({"test": test.to_dict()}), 200