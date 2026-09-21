from io import BytesIO

from app.extensions import db
from app.models import Applicant, Application, Document, DocumentVerification, User
from app.services.auth_service import issue_token


def _token(client):
    response = client.post("/api/auth/register", json={
        "full_name": "Document Test", "email": "document@example.com", "password": "strong-password-123",
    })
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


def test_authenticated_document_upload_persists_record(client, app, tmp_path):
    app.config["DOCUMENT_UPLOAD_DIR"] = str(tmp_path / "private_uploads")
    headers = _token(client)
    response = client.post("/api/documents", headers=headers, data={
        "documentType": "PAN_CARD", "file": (BytesIO(b"sample pdf document"), "pan.pdf", "application/pdf"),
    })
    assert response.status_code == 201
    body = response.get_json()
    assert body["success"] is True
    assert body["document"]["filename"] == "pan.pdf"
    assert body["document"]["status"] in {"VERIFIED", "NEEDS_REVIEW"}
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
        "documentType": "PAN_CARD", "file": (BytesIO(b"not allowed"), "script.js", "application/javascript"),
    })
    assert unsupported.status_code == 400
    assert "Only PDF" in unsupported.get_json()["message"]


def test_document_upload_accepts_png_and_rejects_oversized_file(client, app, tmp_path):
    app.config["DOCUMENT_UPLOAD_DIR"] = str(tmp_path / "private_uploads")
    app.config["MAX_DOCUMENT_SIZE_BYTES"] = 4
    headers = _token(client)
    png = client.post("/api/documents", headers=headers, data={
        "documentType": "ADDRESS_PROOF", "file": (BytesIO(b"png"), "address.png", "image/png"),
    })
    assert png.status_code == 201
    oversized = client.post("/api/documents", headers=headers, data={
        "documentType": "BANK_STATEMENT", "file": (BytesIO(b"12345"), "statement.pdf", "application/pdf"),
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
    assert row["applicant"] == {"full_name": "Submitted Applicant", "email": "submitted-doc@example.com"}
    assert row["documentType"] == "PAN_CARD"
    assert row["verification"]["mismatches"] == ["Name could not be confirmed."]
