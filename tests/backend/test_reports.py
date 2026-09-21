from app.extensions import db
from app.models import Applicant, Application, Explanation, Prediction, User
from app.services.auth_service import issue_token


def test_admin_can_load_a_persisted_application_report(client, app):
    with app.app_context():
        admin = User(email="report-admin@example.com", full_name="Report Admin", role="admin")
        applicant_user = User(email="report-applicant@example.com", full_name="Report Applicant", role="applicant")
        admin.set_password("password123")
        applicant_user.set_password("password123")
        db.session.add_all([admin, applicant_user])
        db.session.flush()
        applicant = Applicant(user_id=applicant_user.id, full_name=applicant_user.full_name)
        db.session.add(applicant)
        db.session.flush()
        application = Application(applicant_id=applicant.id, features_json='{"duration": 12}')
        db.session.add(application)
        db.session.flush()
        prediction = Prediction(application_id=application.id, decision="REVIEW", probability=0.5, model_name="test")
        db.session.add(prediction)
        db.session.flush()
        for method in ("shap", "lime"):
            explanation = Explanation(prediction_id=prediction.id, method=method, plain_english=f"Stored {method} explanation.")
            explanation.set_contributions([{"feature": "duration", "label": "Duration", "value": 12, "contribution": -0.1, "direction": "negative"}])
            db.session.add(explanation)
        db.session.commit()
        token = issue_token(admin)
        application_id = application.id

    response = client.get(f"/api/applications/{application_id}/report", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    report = response.get_json()["report"]
    assert report["decision"] == "REVIEW"
    assert report["factors"][0]["label"] == "Duration"
    assert report["lime"]["summary"] == "Stored lime explanation."
