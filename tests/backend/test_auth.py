"""
Tests for registration, login, and role protection (spec section 40).
"""


def register(client, email="test@example.com", password="password123", full_name="Test User", role="client"):
    return client.post("/api/auth/register", json={"email": email, "password": password, "full_name": full_name, "role": role})


def test_register_applicant_choice_creates_client(client):
    resp = register(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["user"]["role"] == "client"
    assert "token" in body


def test_register_admin_checker_choice_creates_admin(client):
    resp = register(client, email="admin@example.com", full_name="Admin", role="admin")
    assert resp.status_code == 201
    assert resp.get_json()["user"]["role"] == "admin"


def test_register_rejects_role_outside_the_two_signup_choices(client):
    resp = client.post("/api/auth/register", json={
        "email": "hacker@example.com", "password": "password123",
            "full_name": "Hacker", "role": "loan_officer",
    })
    assert resp.status_code == 400
    assert "Role must be one of" in resp.get_json()["errors"][-1]


def test_google_login_reports_missing_server_configuration(client):
    response = client.get("/api/auth/google")
    assert response.status_code == 302
    assert "Google+sign-in+is+not+configured+on+this+server" in response.headers["Location"]


def test_google_login_redirects_to_google_when_credentials_are_configured(client, app):
    app.config.update(GOOGLE_CLIENT_ID="test-client-id", GOOGLE_CLIENT_SECRET="test-client-secret")
    response = client.get("/api/auth/google")
    assert response.status_code == 302
    assert response.headers["Location"].startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=test-client-id" in response.headers["Location"]


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


def test_login_returns_the_persisted_signup_role(client):
    register(client, email="checker@example.com", full_name="Checker", role="admin")
    resp = client.post("/api/auth/login", json={"email": "checker@example.com", "password": "password123"})
    assert resp.status_code == 200
    assert resp.get_json()["user"]["role"] == "admin"


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
