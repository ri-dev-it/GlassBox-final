import json

from app.extensions import db
from app.models import Applicant, Application, MerchantFraudCheck, Prediction, User
from app.services.auth_service import issue_token


def test_admin_dashboard_stats_uses_persisted_application_and_fraud_data(client, app):
    with app.app_context():
        admin = User(email="stats-admin@example.com", full_name="Stats Admin", role="admin")
        applicant_user = User(email="stats-applicant@example.com", full_name="Stats Applicant", role="applicant")
        admin.set_password("password123")
        applicant_user.set_password("password123")
        db.session.add_all([admin, applicant_user])
        db.session.flush()
        applicant = Applicant(user_id=applicant_user.id, full_name=applicant_user.full_name)
        db.session.add(applicant)
        db.session.flush()
        application = Application(applicant_id=applicant.id, features_json="{}")
        db.session.add(application)
        db.session.flush()
        db.session.add(Prediction(application_id=application.id, decision="REVIEW", probability=0.5, model_name="test"))
        db.session.add(MerchantFraudCheck(merchant_id="merchant-1", fraud_score=0.8, flags_json=json.dumps(["Refund spike", "Refund spike"]), flagged_days_json="[]"))
        db.session.commit()
        token = issue_token(admin)

    response = client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] == 1
    assert body["under_review"] == 1
    assert body["risk_distribution"]["medium"] == 1
    assert body["fraud_flag_summary"] == [{"flag": "Refund spike", "count": 2}]
