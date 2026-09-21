import os
import uuid
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.utils import secure_filename

from app.extensions import db
from app.middleware.auth_middleware import roles_required
from app.models import Document, User
from app.services.document_verification_service import verify_document

documents_bp = Blueprint("documents", __name__)
ALLOWED_TYPES = {"PAN_CARD", "AADHAAR_CARD", "SALARY_SLIP", "BANK_STATEMENT", "ADDRESS_PROOF", "EMPLOYMENT_INCOME_PROOF"}
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
ALLOWED_MIMES = {"application/pdf", "image/jpeg", "image/png"}

@documents_bp.post("/documents")
@roles_required("applicant", "loan_officer", "admin")
def upload_document():
    document_type = request.form.get("documentType", "")
    file = request.files.get("file")
    if document_type not in ALLOWED_TYPES:
        return jsonify({"success": False, "message": "Unsupported document type."}), 400
    if not file or not file.filename:
        return jsonify({"success": False, "message": "Please select a document."}), 400
    filename = secure_filename(file.filename)
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS or file.mimetype not in ALLOWED_MIMES:
        return jsonify({"success": False, "message": "Only PDF, JPG, JPEG, and PNG files are supported."}), 400
    file.stream.seek(0, os.SEEK_END); size = file.stream.tell(); file.stream.seek(0)
    if size <= 0 or size > current_app.config["MAX_DOCUMENT_SIZE_BYTES"]:
        return jsonify({"success": False, "message": "File size exceeds the allowed 10 MB limit."}), 400
    directory = Path(current_app.config["DOCUMENT_UPLOAD_DIR"]) / str(g.current_user.id)
    directory.mkdir(parents=True, exist_ok=True)
    stored = directory / f"{uuid.uuid4().hex}.{extension}"
    try:
        file.save(stored)
        existing = Document.query.filter_by(user_id=g.current_user.id, application_id=None, document_type=document_type).first()
        if existing:
            old_path = existing.storage_reference
            db.session.delete(existing); db.session.flush()
            try: os.remove(old_path)
            except OSError: pass
        document = Document(user_id=g.current_user.id, document_type=document_type, storage_reference=str(stored), original_filename=filename, mime_type=file.mimetype, file_size=size, status="VERIFYING")
        db.session.add(document); db.session.flush()
        verification = verify_document(document, g.current_user.full_name)
        db.session.add(verification); db.session.commit()
    except OSError:
        db.session.rollback()
        try: os.remove(stored)
        except OSError: pass
        current_app.logger.exception("Document storage failed for user id %s", g.current_user.id)
        return jsonify({"success": False, "message": "Document storage failed. Please try again."}), 500
    except Exception:
        db.session.rollback()
        try: os.remove(stored)
        except OSError: pass
        current_app.logger.exception("Document upload record failed for user id %s", g.current_user.id)
        return jsonify({"success": False, "message": "Document upload failed. Please try again."}), 500
    return jsonify({"success": True, "message": "Document uploaded successfully. AI-assisted verification is complete or pending review.", "document": document.to_dict()}), 201

@documents_bp.get("/documents/pending")
@roles_required("applicant", "loan_officer", "admin")
def list_pending_documents():
    if g.current_user.role == "admin":
        rows = (Document.query.join(User, User.id == Document.user_id)
            .filter(Document.application_id.isnot(None))
            .order_by(Document.uploaded_at.desc()).with_entities(Document, User).all())
        return jsonify({"documents": [{**document.to_dict(), "applicant": {"full_name": user.full_name, "email": user.email}} for document, user in rows]}), 200
    docs = Document.query.filter_by(user_id=g.current_user.id, application_id=None).all()
    return jsonify({"documents": [document.to_dict() for document in docs]}), 200
