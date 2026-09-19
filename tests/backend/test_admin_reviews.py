import datetime

from app.extensions import db
from app.models import Applicant, Application, Prediction, User
from app.services.auth_service import issue_token


def make_user(email: str, role: str):
    user = User(email=email, full_name=email.split("@", 1)[0], role=role)
    user.set_password("password123")
    db.session.add(user)
    db.session.flush()
    return user


def test_admin_review_queue_is_admin_only_and_records_decision(client, app):
    with app.app_context():
        applicant_user = make_user("review-applicant@example.com", "applicant")
        admin_user = make_user("review-admin@example.com", "admin")
        applicant = Applicant(user_id=applicant_user.id, full_name=applicant_user.full_name)
        db.session.add(applicant)
        db.session.flush()
        application = Application(applicant_id=applicant.id, features_json="{}", created_at=datetime.datetime.utcnow())
        db.session.add(application)
        db.session.flush()
        db.session.add(Prediction(application_id=application.id, decision="REVIEW", probability=0.5, model_name="test"))
        db.session.commit()
        applicant_token = issue_token(applicant_user)
        admin_token = issue_token(admin_user)
        application_id = application.id

    forbidden = client.get("/api/admin/applications/review", headers={"Authorization": f"Bearer {applicant_token}"})
    assert forbidden.status_code == 403

    pending = client.get("/api/admin/applications/review", headers={"Authorization": f"Bearer {admin_token}"})
    assert pending.status_code == 200
    assert pending.get_json()["applications"][0]["id"] == application_id

    decided = client.post(
        f"/api/admin/applications/{application_id}/review",
        json={"decision": "approve"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert decided.status_code == 200
    body = decided.get_json()["application"]
    assert body["admin_decision"] == "APPROVE"
    assert body["admin_decided_by"] is not None
    assert body["admin_decided_at"] is not None

    duplicate = client.post(
        f"/api/admin/applications/{application_id}/review",
        json={"decision": "REJECT"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert duplicate.status_code == 409