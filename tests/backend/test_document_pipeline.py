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
    reused = send(client, other, "aadhaar")
    assert reused.status_code == 422
    assert any(c["name"] == "reuse" and c["status"] == "FAIL" for c in reused.json["checks"])
    with app.app_context():
        from app.models import VerificationReport
        assert VerificationReport.query.count() == 3


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
