"""
Tests for registration, login, and role protection (spec section 40).
"""


def register(client, email="test@example.com", password="password123", full_name="Test User"):
    return client.post("/api/auth/register", json={"email": email, "password": password, "full_name": full_name})


def test_register_creates_applicant(client):
    resp = register(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["user"]["role"] == "applicant"
    assert "token" in body


def test_register_client_choice_still_persists_backward_compatible_applicant(client):
    resp = client.post("/api/auth/register", json={
        "email": "client@example.com", "password": "password123", "full_name": "Client", "role": "client",
    })
    assert resp.status_code == 201
    assert resp.get_json()["user"]["role"] == "applicant"


def test_register_cannot_self_assign_role(client):
    """Public registration must never grant loan_officer/admin (security)."""
    resp = client.post("/api/auth/register", json={
        "email": "hacker@example.com", "password": "password123",
        "full_name": "Hacker", "role": "admin",
    })
    assert resp.status_code == 201
    assert resp.get_json()["user"]["role"] == "applicant"


def test_register_duplicate_email_rejected(client):
    register(client)
    resp = register(client)
    assert resp.status_code == 409


def test_register_weak_password_rejected(client):
    resp = client.post("/api/auth/register", json={
        "email": "weak@example.com", "password": "123", "full_name": "Weak Pass",
    })
    assert resp.status_code == 400


def test_login_success(client):
    register(client)
    resp = client.post("/api/auth/login", json={"email": "test@example.com", "password": "password123"})
    assert resp.status_code == 200
    assert "token" in resp.get_json()


def test_login_wrong_password_rejected(client):
    register(client)
    resp = client.post("/api/auth/login", json={"email": "test@example.com", "password": "wrongpass"})
    assert resp.status_code == 401


def test_protected_route_requires_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_protected_route_with_token(client):
    register(client)
    login_resp = client.post("/api/auth/login", json={"email": "test@example.com", "password": "password123"})
    token = login_resp.get_json()["token"]
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json()["user"]["email"] == "test@example.com"


def test_staff_endpoint_forbidden_for_applicant(client):
    register(client)
    login_resp = client.post("/api/auth/login", json={"email": "test@example.com", "password": "password123"})
    token = login_resp.get_json()["token"]
    resp = client.post(
        "/api/auth/create-staff",
        json={"email": "officer@example.com", "password": "password123", "full_name": "Officer", "role": "loan_officer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
