from tests.backend.test_applications import register_and_login


def test_partial_dependence_endpoint_returns_curves(client, monkeypatch):
    token = register_and_login(client, "pdp@example.com")
    curves = [{
        "feature": "duration_months",
        "label": "Loan Duration (months)",
        "points": [{"value": 12.0, "approval_probability": 0.6}],
    }]
    monkeypatch.setattr("app.services.ml_service.get_partial_dependence", lambda: curves)

    response = client.get("/api/explain/partial-dependence", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.get_json() == {"curves": curves}


def test_partial_dependence_endpoint_requires_auth(client):
    response = client.get("/api/explain/partial-dependence")
    assert response.status_code == 401