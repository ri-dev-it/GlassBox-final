from flask import Blueprint, g, jsonify, send_file

from app.middleware.auth_middleware import roles_required
from app.services import application_service
from app.services import report_service

applicants_bp = Blueprint("applicants", __name__)


@applicants_bp.get("/applications")
@roles_required("applicant", "loan_officer", "admin")
def list_applications():
    if g.current_user.role in {"applicant", "client"}:
        applications = application_service.get_applications_for_user(g.current_user)
    else:
        applications = application_service.get_all_applications()
    return jsonify({"applications": applications}), 200


@applicants_bp.get("/applications/<int:application_id>")
@roles_required("applicant", "loan_officer", "admin")
def get_application(application_id: int):
    detail = application_service.get_application_detail(application_id, g.current_user)
    if detail is None:
        return jsonify({"error": "Application not found."}), 404
    return jsonify(detail), 200


@applicants_bp.get("/applications/<int:application_id>/report")
@roles_required("applicant", "loan_officer", "admin")
def get_application_report(application_id: int):
    result = report_service.get_report(application_id, g.current_user)
    if result is None:
        return jsonify({"error": "Application not found."}), 404
    if result["report"] is None:
        return jsonify({"error": "A complete stored analysis is not available for this application."}), 409
    return jsonify(result), 200


@applicants_bp.get("/applications/<int:application_id>/report.pdf")
@roles_required("applicant", "loan_officer", "admin")
def download_application_report(application_id: int):
    result = report_service.get_report(application_id, g.current_user)
    if result is None:
        return jsonify({"error": "Application not found."}), 404
    if result["report"] is None:
        return jsonify({"error": "A complete stored analysis is not available for this application."}), 409
    try:
        pdf = report_service.create_pdf(result["report"])
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 503
    return send_file(pdf, mimetype="application/pdf", as_attachment=True, download_name=f"{result['report']['application_id']}-assessment.pdf")
