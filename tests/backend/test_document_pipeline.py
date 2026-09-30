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
