"""
Business logic for submitting an application and running it through the
full ML pipeline (predict -> SHAP -> LIME -> counterfactual), persisting
every step so it can be re-fetched without recomputation later.
"""

import datetime

from app.extensions import db
from app.models import Applicant, Application, Prediction, Explanation, Counterfactual, Document, Notification
from app.services import ab_test_service
from app.services import ml_service
from app.services.bank_eligibility_service import create_bank_eligibilities
from app.services.document_verification_service import verify_document
from app.services.document_pipeline import build_report, stored_report, apply_verdict


def get_or_create_applicant(user) -> Applicant:
    applicant = Applicant.query.filter_by(user_id=user.id).first()
    if not applicant:
        applicant = Applicant(user_id=user.id, full_name=user.full_name)
        db.session.add(applicant)
        db.session.commit()
    return applicant


def submit_application(user, features: dict, loan_type: str = "PERSONAL_LOAN", submission_details: dict | None = None) -> dict:
    applicant = get_or_create_applicant(user)
    document_report = build_report(user.id)

    # Run all ML work before persisting the application.  If an explainer or
    # model asset fails, no incomplete "Under Review" application is left in
    # the database.
    assignment = ab_test_service.get_assignment("credit_history")
    result = ml_service.predict_application(features, assignment["version"] if assignment else None) if assignment else ml_service.predict_application(features)
    metadata = ml_service.get_model_metadata()
    shap_result = ml_service.get_shap_explanation(features, result["prediction"], result["probability"])
    lime_result = ml_service.get_lime_explanation(features, result["prediction"], result["probability"])
    model_decision = result["prediction"]
    result["prediction"] = apply_verdict(model_decision, document_report["verdict"])
    policy_note = "\nDocument verification: " + document_report["verdict"] + ". " + " ".join(dict.fromkeys(document_report["reasons"]))
    if result["prediction"] != model_decision:
        policy_note += f" Model decision {model_decision} was overridden to {result['prediction']} for document review."
    shap_result["plain_english"] += policy_note
    lime_result["plain_english"] += policy_note
    if result["prediction"] == "DECLINE":
        cf_result = ml_service.get_counterfactual(features)
    else:
        cf_result = {
            "found": False,
            "message": "Counterfactual suggestions are only generated for rejected applications.",
            "alternatives": [],
        }

    application = Application(applicant_id=applicant.id, loan_type=loan_type)
    application.set_features(features | {"loan_type": loan_type, **(submission_details or {})})
    db.session.add(application)
    db.session.flush()
    # Staged documents remain private and user-owned until a successful submission.
    pending_documents = Document.query.filter_by(user_id=user.id, application_id=None).all()
    for document in pending_documents:
        document.application_id = application.id
        if document.verification and not document.audits:
            verify_document(document, user.full_name)
    build_report(user.id, application.id, persist=True)
    application.public_id = f"APP-{application.created_at.year if application.created_at else __import__('datetime').datetime.utcnow().year}-{application.id:04d}"

    prediction = Prediction(
        application_id=application.id,
        decision=result["prediction"],
        probability=result["probability"],
        model_name=metadata.get("final_model", "unknown"),
    )
    db.session.add(prediction)
    db.session.flush()
    if assignment:
        ab_test_service.record_result(assignment, prediction, result["prediction"], result["probability"])

    # Persist the previously generated explanations alongside the prediction.
    shap_explanation = Explanation(prediction_id=prediction.id, method="shap")
    shap_explanation.set_contributions(shap_result["contributions"])
    shap_explanation.plain_english = shap_result["plain_english"]
    db.session.add(shap_explanation)

    lime_explanation = Explanation(prediction_id=prediction.id, method="lime")
    lime_explanation.set_contributions(lime_result["contributions"])
    lime_explanation.plain_english = lime_result["plain_english"]
    db.session.add(lime_explanation)

    counterfactual = Counterfactual(prediction_id=prediction.id, found=cf_result["found"], message=cf_result["message"])
    counterfactual.set_alternatives(cf_result["alternatives"])
    db.session.add(counterfactual)

    # General model probability plus published, project-level profile thresholds.
    bank_eligibilities = create_bank_eligibilities(application.id, result["probability"], features)
    db.session.add_all(bank_eligibilities)

    db.session.commit()

    return {
        "application": application.to_dict(),
        "prediction": prediction.to_dict(),
        "shap": shap_explanation.to_dict(),
        "lime": lime_explanation.to_dict(),
        "comparison": ml_service.get_shap_lime_comparison(shap_result["contributions"], lime_result["contributions"]),
        "counterfactual": counterfactual.to_dict(),
        "documents": [document.to_dict() for document in pending_documents],
        "documentVerification": document_report,
        "bankEligibility": [record.to_dict() for record in bank_eligibilities],
    }


def get_applications_for_user(user) -> list:
    applicant = Applicant.query.filter_by(user_id=user.id).first()
    if not applicant:
        return []
    return [app.to_dict() | {"prediction": app.prediction.to_dict() if app.prediction else None}
            for app in applicant.applications]


def get_application_detail(application_id: int, user) -> dict | None:
    application = Application.query.get(application_id)
    if not application:
        return None

    # Applicants may only view their own applications; staff may view any.
    if user.role in {"applicant", "client"} and application.applicant.user_id != user.id:
        return None

    prediction = application.prediction
    if not prediction:
        return {"application": application.to_dict(), "prediction": None}

    explanations = {e.method: e.to_dict() for e in prediction.explanations}
    counterfactual = prediction.counterfactuals[0].to_dict() if prediction.counterfactuals else None

    comparison = None
    if "shap" in explanations and "lime" in explanations:
        comparison = ml_service.get_shap_lime_comparison(
            explanations["shap"]["contributions"], explanations["lime"]["contributions"]
        )

    return {
        "application": application.to_dict(),
        "prediction": prediction.to_dict(),
        "shap": explanations.get("shap"),
        "lime": explanations.get("lime"),
        "comparison": comparison,
        "counterfactual": counterfactual,
        "documents": [document.to_dict() for document in application.documents],
        "documentVerification": stored_report(application.applicant.user_id, application.id),
        "bankEligibility": [record.to_dict() for record in application.bank_eligibilities],
    }


def get_all_applications() -> list:
    """Staff/admin view of every application, for the analytics dashboard."""
    return [
        app.to_dict() | {"prediction": app.prediction.to_dict() if app.prediction else None,
                         "applicant": {"full_name": app.applicant.full_name, "email": app.applicant.user.email}}
        for app in Application.query.order_by(Application.created_at.desc()).all()
    ]


def get_pending_admin_reviews() -> list:
    """Return model REVIEW applications awaiting an admin decision."""
    applications = (
        Application.query.join(Prediction)
        .filter(Prediction.decision == "REVIEW", Application.admin_decision.is_(None))
        .order_by(Application.created_at.asc())
        .all()
    )
    return [
        app.to_dict() | {
            "prediction": app.prediction.to_dict() if app.prediction else None,
            "shap": next((e.to_dict() for e in app.prediction.explanations if e.method == "shap"), None) if app.prediction else None,
            "lime": next((e.to_dict() for e in app.prediction.explanations if e.method == "lime"), None) if app.prediction else None,
            "counterfactual": app.prediction.counterfactuals[0].to_dict() if app.prediction and app.prediction.counterfactuals else None,
            "applicant": {
                "full_name": app.applicant.full_name,
                "email": app.applicant.user.email,
            },
        }
        for app in applications
    ]


def decide_admin_review(application_id: int, decision: str, admin_id: int, feedback: str | None = None) -> dict | None:
    """Record one immutable admin decision for a pending REVIEW application."""
    application = Application.query.get(application_id)
    if (
        not application
        or not application.prediction
        or application.prediction.decision != "REVIEW"
        or application.admin_decision is not None
    ):
        return None
    application.admin_decision = decision
    application.admin_decided_by = admin_id
    application.admin_decided_at = datetime.datetime.utcnow()
    feedback = (feedback or "").strip()[:900] or None
    application.admin_feedback = feedback
    application_ref = application.public_id or application.to_dict()["application_id"]
    outcome = "approved" if decision == "APPROVE" else "rejected"
    message = f"Your application {application_ref} has been {outcome}."
    if feedback:
        message = f"{message} {'Feedback' if decision == 'REJECT' else 'Note'}: {feedback}"
    db.session.add(Notification(
        user_id=application.applicant.user_id,
        application_id=application.id,
        message=message,
        type="status_update",
        decision_type=outcome,
    ))
    db.session.commit()
    return application.to_dict() | {"prediction": application.prediction.to_dict()}
