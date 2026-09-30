from io import BytesIO
from pathlib import Path
import pytest

FIXTURES = Path(__file__).parents[1] / "fixtures/documents"


@pytest.fixture
def document_headers(client, app, tmp_path):
    app.config.update(DOCUMENT_UPLOAD_DIR=str(tmp_path), AADHAAR_HASH_KEY="test-only-secret")
    response = client.post("/api/auth/register", json={"full_name": "Asha Example", "email": "asha@example.test", "password": "strong-password-123"})
    return {"Authorization": "Bearer " + response.get_json()["token"]}


def send(client, headers, slot, filename=None):
    return client.post("/api/documents", headers=headers, data={"slot": slot,
        "file": (BytesIO((FIXTURES / (filename or f"{slot}.pdf")).read_bytes()), "upload.pdf")})


def test_wrong_slot_and_masking(client, document_headers):
    wrong = send(client, document_headers, "aadhaar", "salary_slip.pdf")
    assert wrong.status_code == 422
    assert wrong.json["checks"][0]["status"] == "FAIL"
    good = send(client, document_headers, "aadhaar")
    assert good.status_code == 201
    assert "99998888" not in good.get_data(as_text=True)
    assert good.json["document"]["verification"]["extractedInformation"]["aadhaar"].startswith("********")


def test_upload_requires_auth_and_real_content(client, document_headers):
    assert send(client, {}, "aadhaar").status_code == 401
    response = client.post("/api/documents", headers=document_headers,
        data={"slot": "aadhaar", "file": (BytesIO(b"not a pdf"), "x.pdf")})
    assert response.status_code == 400


def test_identity_mismatch_and_reuse(client, app, document_headers):
    assert send(client, document_headers, "aadhaar").status_code == 201
    wrong = send(client, document_headers, "salary_slip", "mismatched_salary.pdf")
    assert wrong.status_code == 422
    assert any(c["name"] == "identity_name" and c["status"] == "FAIL" for c in wrong.json["checks"])
    response = client.post("/api/auth/register", json={"full_name": "Asha Example", "email": "another@example.test", "password": "strong-password-123"})
    other = {"Authorization": "Bearer " + response.json["token"]}
    # Different file bytes, same identifier: exercise Aadhaar hash reuse itself.
    reused = client.post('/api/documents', headers=other, data={'slot': 'aadhaar',
        'file': (BytesIO((FIXTURES / 'aadhaar.pdf').read_bytes() + b'\n%different serialization\n'), 'identity.pdf')})
    assert reused.status_code == 422
    assert any(c["name"] == "reuse" and c["status"] == "FAIL" for c in reused.json["checks"])
    with app.app_context():
        from app.models import VerificationReport
        assert VerificationReport.query.count() == 3
    copied = send(client, other, 'salary_slip', 'mismatched_salary.pdf')
    assert any(c['name'] == 'reuse' and c['status'] == 'FAIL' for c in copied.json['checks'])


@pytest.mark.parametrize("decision,verdict,expected", [("APPROVE", "REJECTED", "REVIEW"),
    ("APPROVE", "NEEDS_REVIEW", "REVIEW"), ("DECLINE", "NEEDS_REVIEW", "DECLINE"),
    ("APPROVE", "VERIFIED", "APPROVE"), ("REVIEW", "REJECTED", "REVIEW")])
def test_decision_policy(decision, verdict, expected):
    from app.services.document_pipeline import apply_verdict
    assert apply_verdict(decision, verdict) == expected


def test_report_auth_and_complete_documents(client, document_headers):
    assert client.get('/api/documents/report').status_code == 401
    for slot in ('aadhaar', 'salary_slip', 'bank_statement', 'income_certificate'):
        assert send(client, document_headers, slot).status_code == 201
    report = client.get('/api/documents/report', headers=document_headers)
    assert report.json['verdict'] == 'VERIFIED'
    assert report.json['features']['avg_monthly_credits'] == 45000


def test_csv_transactions_persist(client, app, document_headers):
    text = 'Bank Statement\nAccount holder: Asha Example\nAccount number: 12345678\nIFSC: DEMO0000001\ndate,description,debit,credit,balance\n2026-01-01,Salary,0,45000,45000\n2026-01-02,EMI,5000,0,40000\n'
    response = client.post('/api/documents', headers=document_headers, data={'slot': 'bank_statement', 'file': (BytesIO(text.encode()), 'statement.csv')})
    assert response.status_code == 201
    with app.app_context():
        from app.models import DocumentTransaction
        assert DocumentTransaction.query.count() == 2


def test_submission_override_snapshot_and_report_privacy(client, app, document_headers, monkeypatch):
    from app.services import application_service as service
    from app.models import User, Document
    from ml.documents.extraction import extract
    for slot in ('aadhaar', 'salary_slip', 'bank_statement', 'income_certificate'):
        assert send(client, document_headers, slot).status_code == 201
    assert send(client, document_headers, 'salary_slip', 'mismatched_salary.pdf').status_code == 422
    monkeypatch.setattr(service.ab_test_service, 'get_assignment', lambda _: None)
    monkeypatch.setattr(service.ml_service, 'predict_application', lambda _: {'prediction': 'APPROVE', 'probability': 0.95})
    monkeypatch.setattr(service.ml_service, 'get_model_metadata', lambda: {'final_model': 'test'})
    for method in ('get_shap_explanation', 'get_lime_explanation'):
        monkeypatch.setattr(service.ml_service, method, lambda *args: {'contributions': [], 'plain_english': 'Model explanation.'})
    monkeypatch.setattr(service.ml_service, 'get_shap_lime_comparison', lambda *args: {})
    with app.app_context():
        user = User.query.filter_by(email='asha@example.test').one()
        result = service.submit_application(user, {})
        application_id = result['application']['id']
        assert result['prediction']['decision'] == 'REVIEW'
        assert 'Document verification: REJECTED' in result['shap']['plain_english']
        assert all(b['decision'] != 'APPROVED' for b in result['bankEligibility'])
        identity = Document.query.filter_by(document_type='AADHAAR_CARD').first()
        masked_text, _, _ = extract(Path(identity.storage_reference).read_bytes(), identity.mime_type)
        assert '999988887779' not in masked_text
    saved = client.get(f'/api/documents/applications/{application_id}/report', headers=document_headers)
    assert saved.json['verdict'] == 'REJECTED'
    # Re-uploading for a new application must not mutate the submitted snapshot.
    send(client, document_headers, 'aadhaar')
    assert client.get(f'/api/documents/applications/{application_id}/report', headers=document_headers).json == saved.json
    other = client.post('/api/auth/register', json={'full_name': 'Other Person', 'email': 'other@example.test', 'password': 'strong-password-123'})
    headers = {'Authorization': 'Bearer ' + other.json['token']}
    assert client.get(f'/api/documents/applications/{application_id}/report', headers=headers).status_code == 404


def test_invalid_slot_size_and_checksum(client, app, document_headers):
    assert send(client, document_headers, 'unknown', 'aadhaar.pdf').status_code == 400
    app.config['MAX_DOCUMENT_SIZE_BYTES'] = 10
    assert send(client, document_headers, 'aadhaar').status_code == 400
    app.config['MAX_DOCUMENT_SIZE_BYTES'] = 5 * 1024 * 1024
    response = send(client, document_headers, 'aadhaar', 'invalid_aadhaar.pdf')
    assert response.status_code == 422
    assert any(c['name'] == 'aadhaar_checksum' and c['status'] == 'FAIL' for c in response.json['checks'])
