"""
Tests for the application/prediction API's validation and authorization
(spec section 40). These don't require a trained model -- they test
validation and access control, which don't depend on ml/ being trained.
"""


def register_and_login(client, email="applicant@example.com", full_name="Applicant"):
    client.post("/api/auth/register", json={"email": email, "password": "password123", "full_name": full_name})
    resp = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    return resp.get_json()["token"]


def test_predict_requires_auth(client):
    resp = client.post("/api/predict", json={})
    assert resp.status_code == 401


def test_predict_rejects_incomplete_payload(client):
    token = register_and_login(client)
    resp = client.post("/api/predict", json={"age": 30}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400
    assert "errors" in resp.get_json()


def test_predict_rejects_invalid_categorical_value(client):
    token = register_and_login(client)
    payload = {
        "checking_account_status": "not-a-real-option",
        "duration_months": 12, "credit_history": "no credits taken",
        "purpose": "education", "credit_amount": 1000,
        "savings_account": "< 100 DM", "employment_since": "1-4 years",
        "installment_rate_percent": 2, "personal_status_sex": "male:single",
        "other_debtors_guarantors": "none", "present_residence_since": 2,
        "property": "car or other", "age": 30, "other_installment_plans": "none",
        "housing": "own", "existing_credits_count": 1, "job": "skilled employee/official",
        "num_dependents": 1, "telephone": "none", "foreign_worker": "yes",
    }
    resp = client.post("/api/predict", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


def test_applications_list_requires_auth(client):
    resp = client.get("/api/applications")
    assert resp.status_code == 401


def test_applications_list_empty_for_new_user(client):
    token = register_and_login(client)
    resp = client.get("/api/applications", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json()["applications"] == []


def test_fairness_report_requires_staff_role(client):
    token = register_and_login(client)  # applicant, not staff
    resp = client.get("/api/analytics/fairness", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
