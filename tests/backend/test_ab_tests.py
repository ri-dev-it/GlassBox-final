from app.extensions import db
from app.models import ABTestResult, ModelVersion, User
from app.services import ab_test_service
from test_applications import register_and_login


def _staff_token(client):
    token = register_and_login(client, "ab-admin@example.com")
    user = User.query.filter_by(email="ab-admin@example.com").first()
    user.role = "admin"
    db.session.commit()
    return token


def _versions():
    versions = []
    for number in (1, 2):
        version = ModelVersion(
            model_name="credit_history", version_number=number,
            file_path=f"/tmp/model-{number}.joblib", governance_passed=True,
        )
        db.session.add(version)
        versions.append(version)
    db.session.commit()
    return versions


def test_ab_test_lifecycle_and_results(client):
    token = _staff_token(client)
    first, second = _versions()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/models/credit_history/ab-tests", json={
        "name": "income rollout", "control_version_id": first.id,
        "treatment_version_id": second.id, "traffic_percentage": 100,
    }, headers=headers)
    assert response.status_code == 201
    test_id = response.get_json()["test"]["id"]

    assignment = ab_test_service.get_assignment("credit_history")
    assert assignment["variant"] == "treatment"
    ab_test_service.record_result(assignment, None, "APPROVE", 0.9)
    db.session.commit()

    response = client.get(f"/api/models/credit_history/ab-tests/{test_id}/results", headers=headers)
    assert response.status_code == 200
    assert response.get_json()["summary"]["treatment"]["count"] == 1
    assert response.get_json()["results"][0]["model_version_id"] == second.id

    response = client.post(f"/api/models/credit_history/ab-tests/{test_id}/end", headers=headers)
    assert response.status_code == 200
    assert response.get_json()["test"]["status"] == "ended"


def test_ab_test_requires_staff_role(client):
    token = register_and_login(client, "ab-applicant@example.com")
    response = client.post("/api/models/credit_history/ab-tests", json={}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403