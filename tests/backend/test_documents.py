from io import BytesIO
from pathlib import Path

FIXTURES = Path(__file__).parents[1] / "fixtures/documents"

from app.extensions import db
from app.models import Applicant, Application, Document, DocumentVerification, User
from app.services.auth_service import issue_token


def _token(client, full_name="Document Test"):
    response = client.post("/api/auth/register", json={
        "full_name": full_name, "email": "document@example.com", "password": "strong-password-123",
    })
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


def test_authenticated_document_upload_persists_record(client, app, tmp_path):
    app.config["DOCUMENT_UPLOAD_DIR"] = str(tmp_path / "private_uploads")
    headers = _token(client, "Asha Example")
    response = client.post("/api/documents", headers=headers, data={
        "documentType": "PAN_CARD", "confirmedDocumentType": "true", "file": (BytesIO((FIXTURES / "pan.pdf").read_bytes()), "pan.pdf", "application/pdf"),
    })
    assert response.status_code == 201
    body = response.get_json()
    assert body["success"] is True
    assert body["document"]["filename"] == "pan.pdf"
    assert body["document"]["status"] == "UPLOADED"
    pending = client.get("/api/documents/pending", headers=headers)
    assert pending.status_code == 200
    assert len(pending.get_json()["documents"]) == 1
    assert list((tmp_path / "private_uploads").rglob("*.pdf"))


def test_document_upload_rejects_missing_and_unsupported_files(client):
    headers = _token(client)
    missing = client.post("/api/documents", headers=headers, data={"documentType": "PAN_CARD"})
    assert missing.status_code == 400
    assert missing.get_json()["message"] == "Please select a document."
    unsupported = client.post("/api/documents", headers=headers, data={
        "documentType": "PAN_CARD", "confirmedDocumentType": "true", "file": (BytesIO(b"not allowed"), "script.js", "application/javascript"),
    })
    assert unsupported.status_code == 400
    assert "Only PDF" in unsupported.get_json()["message"]


def test_address_upload_rejects_another_document_type_filename(client):
    headers = _token(client)
    response = client.post("/api/documents", headers=headers, data={
        "documentType": "ADDRESS_PROOF",
        "confirmedDocumentType": "true",
        "file": (BytesIO(b"not inspected"), "salary_slip.pdf", "application/pdf"),
    })
    assert response.status_code == 400
    assert "selected document type" in response.get_json()["message"]


def test_document_upload_accepts_png_and_rejects_oversized_file(client, app, tmp_path, monkeypatch):
    monkeypatch.setattr("ml.documents.extraction._ocr", lambda image: "Synthetic address proof")
    app.config["DOCUMENT_UPLOAD_DIR"] = str(tmp_path / "private_uploads")
    app.config["MAX_DOCUMENT_SIZE_BYTES"] = 5 * 1024 * 1024
    headers = _token(client)
    png = client.post("/api/documents", headers=headers, data={
        "documentType": "ADDRESS_PROOF", "confirmedDocumentType": "true", "file": (BytesIO((FIXTURES / "address.png").read_bytes()), "address.png", "image/png"),
    })
    assert png.status_code == 201
    app.config["MAX_DOCUMENT_SIZE_BYTES"] = 4
    oversized = client.post("/api/documents", headers=headers, data={
        "documentType": "BANK_STATEMENT", "confirmedDocumentType": "true", "file": (BytesIO(b"12345"), "statement.pdf", "application/pdf"),
    })
    assert oversized.status_code == 400
    assert "size exceeds" in oversized.get_json()["message"]


def test_admin_document_feed_lists_documents_linked_to_submitted_applications(client, app):
    with app.app_context():
        applicant_user = User(email="submitted-doc@example.com", full_name="Submitted Applicant", role="client")
        applicant_user.set_password("password123")
        admin_user = User(email="doc-admin@example.com", full_name="Document Admin", role="admin")
        admin_user.set_password("password123")
        db.session.add_all([applicant_user, admin_user])
        db.session.flush()
        applicant = Applicant(user_id=applicant_user.id, full_name=applicant_user.full_name)
        db.session.add(applicant)
        db.session.flush()
        application = Application(applicant_id=applicant.id, features_json="{}")
        db.session.add(application)
        db.session.flush()
        document = Document(user_id=applicant_user.id, application_id=application.id, document_type="PAN_CARD", storage_reference="test://submitted-pan", original_filename="pan.pdf", mime_type="application/pdf", file_size=1, status="NEEDS_REVIEW")
        db.session.add(document)
        db.session.flush()
        verification = DocumentVerification(document_id=document.id, status="NEEDS_REVIEW", confidence=0.45, verification_message="Manual review required.")
        verification.set_extracted_information({})
        verification.set_mismatches(["Name could not be confirmed."])
        db.session.add(verification)
        db.session.commit()
        token = issue_token(admin_user)

    response = client.get("/api/documents/pending", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    row = response.get_json()["documents"][0]
    assert row["applicant"]["full_name"] == "Submitted Applicant"
    assert row["applicant"]["email"] == "submitted-doc@example.com"
    assert row["documentType"] == "PAN_CARD"
    assert row["verification"]["mismatches"] == ["Name could not be confirmed."]


def test_admin_can_preview_submitted_bank_statement_pdf(client, app, tmp_path):
    app.config["DOCUMENT_UPLOAD_DIR"] = str(tmp_path / "private_uploads")
    applicant_headers = _token(client, "Asha Example")
    bank_pdf = (FIXTURES / "bank_statement.pdf").read_bytes()
    uploaded = client.post("/api/documents", headers=applicant_headers, data={
        "slot": "bank_statement",
        "file": (BytesIO(bank_pdf), "statement.pdf", "application/pdf"),
    })
    assert uploaded.status_code == 201, uploaded.get_json()
    document_id = uploaded.get_json()["document"]["id"]

    with app.app_context():
        applicant_user = User.query.filter_by(email="document@example.com").one()
        admin_user = User(email="preview-admin@example.com", full_name="Preview Admin", role="admin")
        admin_user.set_password("password123")
        db.session.add(admin_user)
        applicant = Applicant(user_id=applicant_user.id, full_name=applicant_user.full_name)
        db.session.add(applicant)
        db.session.flush()
        application = Application(applicant_id=applicant.id, features_json="{}")
        db.session.add(application)
        db.session.flush()
        Document.query.get(document_id).application_id = application.id
        db.session.commit()
        admin_headers = {"Authorization": f"Bearer {issue_token(admin_user)}"}

    preview = client.get(f"/api/documents/{document_id}/file", headers=admin_headers)
    assert preview.status_code == 200
    assert preview.mimetype == "application/pdf"
    assert preview.data == bank_pdf
