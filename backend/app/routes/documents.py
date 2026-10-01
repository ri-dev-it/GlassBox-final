import os
import datetime
import uuid
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, request, send_file
from werkzeug.utils import secure_filename

from app.extensions import db
from app.middleware.auth_middleware import roles_required
from app.models import Application, Document, User
from app.services.document_verification_service import verify_document

documents_bp = Blueprint("documents", __name__)
ALLOWED_TYPES = {
    "PAN_CARD",
    "AADHAAR_CARD",
    "SALARY_SLIP",
    "BANK_STATEMENT",
    "ADDRESS_PROOF",
}
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
ALLOWED_MIMES = {"application/pdf", "image/jpeg", "image/png"}
@documents_bp.post("/documents")
@roles_required("applicant", "loan_officer", "admin")
def upload_document():
    from app.services.document_pipeline import SLOTS, upload, ExtractionError

    slot = request.form.get("slot") or next(
        (k for k, v in SLOTS.items() if v == request.form.get("documentType")),
        None,
    )
    if slot:
        file = request.files.get("file")
        if not file or not file.filename:
            return (
                jsonify(
                    {"success": False, "message": "Please select a document."}
                ),
                400,
            )
        try:
            document, checks = upload(g.current_user, file, slot)
        except ExtractionError as error:
            return jsonify({"success": False, "message": str(error)}), 400
        rejected = document.status == "REJECTED"
        return jsonify(
            {
                "success": not rejected,
                "document": document.to_dict(),
                "checks": checks,
                "message": (
                    "Document rejected; see checks."
                    if rejected
                    else "Document uploaded."
                ),
            }
        ), (422 if rejected else 201)
    document_type = request.form.get("documentType", "")
    file = request.files.get("file")
    confirmed = request.form.get("confirmedDocumentType") == "true"
    if document_type not in ALLOWED_TYPES:
        return (
            jsonify(
                {"success": False, "message": "Unsupported document type."}
            ),
            400,
        )
    if not file or not file.filename:
        return (
            jsonify(
                {"success": False, "message": "Please select a document."}
            ),
            400,
        )
    if not confirmed:
        return (
            jsonify(
                {
                    "success": False,
                    "message": (
                        "Confirm that this file matches the selected document"
                        " type before uploading."
                    ),
                }
            ),
            400,
        )
    filename = secure_filename(file.filename)
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if (
        extension not in ALLOWED_EXTENSIONS
        or file.mimetype not in ALLOWED_MIMES
    ):
        return (
            jsonify(
                {
                    "success": False,
                    "message": (
                        "Only PDF, JPG, JPEG, and PNG files are supported."
                    ),
                }
            ),
            400,
        )
    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    if size <= 0 or size > current_app.config["MAX_DOCUMENT_SIZE_BYTES"]:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "File size exceeds the allowed 10 MB limit.",
                }
            ),
            400,
        )
    from app.services.document_pipeline import (
        detect_type,
        extract,
        ExtractionError,
        AADHAAR,
        mask_identifiers,
    )

    try:
        payload = file.stream.read()
        detected_mime, extension = detect_type(payload)
        legacy_text, _, _ = extract(payload, detected_mime)
        if not legacy_text.strip():
            raise ExtractionError(
                "Readable text could not be extracted. Upload a clearer"
                " document."
            )
        if AADHAAR.search(legacy_text):
            raise ExtractionError(
                "Upload identity documents in the Aadhaar slot; raw identity"
                " files are not retained."
            )
        file.stream.seek(0)
        filename = mask_identifiers(filename)
    except ExtractionError as error:
        return jsonify({"success": False, "message": str(error)}), 400
    directory = Path(current_app.config["DOCUMENT_UPLOAD_DIR"]) / str(
        g.current_user.id
    )
    directory.mkdir(parents=True, exist_ok=True)
    stored = directory / f"{uuid.uuid4().hex}.{extension}"
    try:
        file.save(stored)
        existing = Document.query.filter_by(
            user_id=g.current_user.id,
            application_id=None,
            document_type=document_type,
        ).first()
        if existing:
            old_path = existing.storage_reference
            db.session.delete(existing)
            db.session.flush()
            try:
                os.remove(old_path)
            except OSError:
                pass
        document = Document(
            user_id=g.current_user.id,
            document_type=document_type,
            storage_reference=str(stored),
            original_filename=filename,
            mime_type=detected_mime,
            file_size=size,
            status="VERIFYING",
        )
        db.session.add(document)
        db.session.flush()
        verification = verify_document(document, g.current_user.full_name)
        db.session.add(verification)
        db.session.commit()
    except OSError:
        db.session.rollback()
        try:
            os.remove(stored)
        except OSError:
            pass
        current_app.logger.exception(
            "Document storage failed for user id %s", g.current_user.id
        )
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Document storage failed. Please try again.",
                }
            ),
            500,
        )
    except Exception:
        db.session.rollback()
        try:
            os.remove(stored)
        except OSError:
            pass
        current_app.logger.exception(
            "Document upload record failed for user id %s", g.current_user.id
        )
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Document upload failed. Please try again.",
                }
            ),
            500,
        )
    return (
        jsonify(
            {
                "success": True,
                "message": (
                    "Document uploaded successfully. AI-assisted verification"
                    " is complete or pending review."
                ),
                "document": document.to_dict(),
            }
        ),
        201,
    )


@documents_bp.get("/documents/pending")
@roles_required("applicant", "loan_officer", "admin")
def list_pending_documents():
    from app.services.document_pipeline import RETIRED_DOCUMENT_TYPES

    if g.current_user.role == "admin":
        rows = (
            Document.query.join(User, User.id == Document.user_id)
            .filter(
                Document.application_id.isnot(None),
                Document.document_type.notin_(RETIRED_DOCUMENT_TYPES),
            )
            .order_by(Document.uploaded_at.desc())
            .with_entities(Document, User)
            .all()
        )
        documents = []
        for document, user in rows:
            application = Application.query.get(document.application_id)
            documents.append(
                {
                    **document.to_dict(),
                    "applicant": {
                        "id": (
                            application.applicant_id if application else None
                        ),
                        "full_name": user.full_name,
                        "email": user.email,
                    },
                    "application": (
                        application.to_dict()
                        | {
                            "decision": (
                                application.prediction.decision
                                if application.prediction
                                else None
                            )
                        }
                        if application
                        else None
                    ),
                }
            )
        return jsonify({"documents": documents}), 200
    docs = (
        Document.query.filter_by(
            user_id=g.current_user.id, application_id=None
        )
        .filter(Document.document_type.notin_(RETIRED_DOCUMENT_TYPES))
        .order_by(Document.id)
        .all()
    )
    return (
        jsonify({"documents": [document.to_dict() for document in docs]}),
        200,
    )


@documents_bp.delete("/documents/<int:document_id>")
@roles_required("applicant")
def delete_document(document_id):
    from app.services.document_pipeline import (
        remove_document,
        DocumentPolicyError,
    )

    try:
        report = remove_document(g.current_user, document_id)
    except DocumentPolicyError as error:
        db.session.rollback()
        return jsonify({"error": str(error)}), error.status_code
    return jsonify({"success": True, "report": report}), 200


@documents_bp.get("/documents/<int:document_id>/bank-statement")
@roles_required("applicant", "loan_officer", "admin")
def bank_statement_details(document_id):
    from app.services.document_pipeline import bank_statement_detail

    document = Document.query.get_or_404(document_id)
    if (
        g.current_user.role in {"client", "applicant"}
        and document.user_id != g.current_user.id
    ) or document.document_type != "BANK_STATEMENT":
        return jsonify({"error": "Document not found."}), 404
    return jsonify(bank_statement_detail(document)), 200


@documents_bp.post("/admin/documents/<int:document_id>/review")
@roles_required("admin")
def review_document(document_id: int):
    document = Document.query.get_or_404(document_id)
    decision = str(
        (request.get_json(silent=True) or {}).get("documentStatus", "")
    ).lower()
    if decision not in {"approved", "rejected"}:
        return (
            jsonify({"error": "documentStatus must be approved or rejected."}),
            400,
        )
    document.document_status, document.reviewed_by, document.reviewed_at = (
        decision,
        g.current_user.id,
        datetime.datetime.utcnow(),
    )
    db.session.commit()
    return jsonify({"document": document.to_dict()}), 200


@documents_bp.get("/documents/report")
@roles_required("applicant", "loan_officer", "admin")
def own_verification_report():
    from app.services.document_pipeline import stored_report

    return jsonify(stored_report(g.current_user.id)), 200


@documents_bp.get("/documents/applications/<int:application_id>/report")
@roles_required("applicant", "loan_officer", "admin")
def application_verification_report(application_id):
    from app.services.document_pipeline import stored_report

    application = Application.query.get_or_404(application_id)
    owner_id = application.applicant.user_id
    if (
        g.current_user.role in {"client", "applicant"}
        and owner_id != g.current_user.id
    ):
        return jsonify({"error": "Document report not found."}), 404
    return jsonify(stored_report(owner_id, application_id)), 200


@documents_bp.get("/documents/<int:document_id>/file")
@roles_required("applicant", "loan_officer", "admin")
def view_document(document_id: int):
    document = Document.query.get_or_404(document_id)
    if (
        g.current_user.role in {"applicant", "client"}
        and document.user_id != g.current_user.id
    ):
        return jsonify({"error": "Document not found."}), 404
    if document.document_type == "AADHAAR_CARD" and not document.audits:
        return (
            jsonify(
                {
                    "error": (
                        "Legacy identity preview is disabled. Upload through"
                        " the masked identity pipeline."
                    )
                }
            ),
            410,
        )
    if document.file_size == 0:
        return jsonify({"error": "Rejected original was not retained."}), 410
    return send_file(
        document.storage_reference,
        mimetype=document.mime_type,
        download_name=document.original_filename,
        as_attachment=False,
    )
