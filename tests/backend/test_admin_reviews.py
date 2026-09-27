import datetime

from app.extensions import db
from app.models import Applicant, Application, ModelVersion, Prediction, User
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
        json={"decision": "approve", "feedback": "Your next steps are in your inbox."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert decided.status_code == 200
    body = decided.get_json()["application"]
    assert body["admin_decision"] == "APPROVE"
    assert body["admin_decided_by"] is not None
    assert body["admin_decided_at"] is not None
    assert body["admin_feedback"] == "Your next steps are in your inbox."

    notifications = client.get("/api/notifications", headers={"Authorization": f"Bearer {applicant_token}"})
    assert notifications.status_code == 200
    notice = notifications.get_json()["notifications"][0]
    assert notice["application_id"] == application_id
    assert notice["message"].startswith("Your application APP-")
    assert "has been approved." in notice["message"]
    assert notice["is_read"] is False
    assert notice["decision_type"] == "approved"
    assert notice["message"].endswith("Note: Your next steps are in your inbox.")
    marked = client.patch(f"/api/notifications/{notice['id']}/read", headers={"Authorization": f"Bearer {applicant_token}"})
    assert marked.status_code == 200
    assert marked.get_json()["notification"]["is_read"] is True

    duplicate = client.post(
        f"/api/admin/applications/{application_id}/review",
        json={"decision": "REJECT"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert duplicate.status_code == 409


def test_rejection_notification_includes_admin_feedback(client, app):
    with app.app_context():
        applicant_user = make_user("reject-notification-applicant@example.com", "applicant")
        admin_user = make_user("reject-notification-admin@example.com", "admin")
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

    response = client.post(f"/api/admin/applications/{application_id}/review", json={
        "decision": "REJECT", "feedback": "Please provide updated income documents."
    }, headers={"Authorization": f"Bearer {admin_token}"})

    assert response.status_code == 200
    notifications = client.get("/api/notifications", headers={"Authorization": f"Bearer {applicant_token}"})
    assert notifications.status_code == 200
    message = notifications.get_json()["notifications"][0]["message"]
    assert notifications.get_json()["notifications"][0]["decision_type"] == "rejected"
    assert message.endswith("Feedback: Please provide updated income documents.")
    with app.app_context():
        assert Application.query.get(application_id).admin_feedback == "Please provide updated income documents."


def test_admin_overview_reports_review_decisions_and_model_governance(client, app):
    with app.app_context():
        applicant_user = make_user("overview-applicant@example.com", "applicant")
        admin_user = make_user("overview-admin@example.com", "admin")
        applicant = Applicant(user_id=applicant_user.id, full_name=applicant_user.full_name)
        db.session.add(applicant)
        db.session.flush()
        pending = Application(applicant_id=applicant.id, features_json="{}")
        approved = Application(applicant_id=applicant.id, features_json="{}", admin_decision="APPROVE", admin_decided_at=datetime.datetime.utcnow())
        rejected = Application(applicant_id=applicant.id, features_json="{}", admin_decision="REJECT", admin_decided_at=datetime.datetime.utcnow())
        db.session.add_all([pending, approved, rejected])
        db.session.flush()
        db.session.add(Prediction(application_id=pending.id, decision="REVIEW", probability=0.5, model_name="test"))
        db.session.add(ModelVersion(model_name="credit_history", version_number=1, file_path="test.joblib", governance_passed=True, is_active=True))
        db.session.commit()
        admin_token = issue_token(admin_user)

    response = client.get("/api/admin/overview", headers={"Authorization": f"Bearer {admin_token}"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["pending_review"] == 1
    assert body["approved_today"] == 1
    assert body["rejected_today"] == 1
    assert body["active_models"] == 1
    assert body["governed_models"] == 1
