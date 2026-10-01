"""
Business logic for submitting an application and running it through the
full ML pipeline (predict -> SHAP -> LIME -> counterfactual), persisting
every step so it can be re-fetched without recomputation later.
"""

import datetime

from app.extensions import db
from app.models import (
    Applicant,
    Application,
    Prediction,
    Explanation,
    Counterfactual,
    Document,
    Notification,
    User,
)
from app.services import ab_test_service
from app.services import ml_service
from app.services.bank_eligibility_service import create_bank_eligibilities
from app.services.document_verification_service import verify_document
from app.services.document_pipeline import (
    build_report,
    stored_report,
    apply_verdict,
    require_submission_documents,
    RETIRED_DOCUMENT_TYPES,
)


def apply_bank_transaction_evidence(result, bank_features, bank_period):
    """Apply auditable, statement-derived risk adjustments to model odds."""
    from decisioning.bands import decide

    values = bank_features or {}
    observed_days = (bank_period or {}).get("observed_days", 0)
    adjustments = []

    def add(feature, label, amount, reason):
        if abs(amount) >= 0.02:
            adjustments.append({
                "feature": feature,
                "label": label,
                "value": values.get(feature),
                "adjustment": round(amount, 4),
                "reason": reason,
            })

    bounced = values.get("bounced_payment_count") or 0
    if bounced > 0:
        add(
            "bounced_payment_count", "Bounced payments",
            min(0.06 * bounced, 0.18),
            f"{int(bounced)} bounced or returned payment(s) were detected.",
        )

    overdraft_days = values.get("negative_balance_days") or 0
    if overdraft_days > 0:
        add(
            "negative_balance_days", "Overdraft days",
            min(0.02 * overdraft_days, 0.12),
            f"{int(overdraft_days)} day(s) had a negative balance.",
        )

    regularity = values.get("salary_regularity")
    credits = values.get("avg_monthly_credits") or 0
    if (
        observed_days >= 60
        and credits > 0
        and regularity is not None
        and regularity >= 2
    ):
        add(
            "salary_regularity", "Salary regularity", -0.02,
            f"Salary credits appeared in {int(regularity)} observed months.",
        )
        add(
            "avg_monthly_credits", "Average monthly credits", -0.02,
            f"Average monthly credits were ₹{credits:,.0f} with recurring "
            "salary deposits.",
        )
    if (
        observed_days >= 60
        and credits > 0
        and regularity is not None
        and regularity < 2
    ):
        add(
            "salary_regularity", "Salary regularity",
            0.08,
            "Salary credits were not consistent across the observed months.",
        )

    volatility = values.get("income_volatility")
    if observed_days >= 60 and volatility is not None and volatility >= 0.5:
        add(
            "income_volatility", "Income volatility",
            0.08,
            f"Monthly credit volatility was {volatility:.2f}.",
        )

    emi_share = values.get("emi_debit_share")
    if emi_share is not None and emi_share > 0.5:
        add(
            "emi_debit_share", "EMI / debit share", 0.06,
            f"EMI and loan debits were {emi_share:.0%} of debit transactions.",
        )

    emi_count = values.get("emi_debit_count") or 0
    if emi_count >= 3:
        add(
            "emi_debit_count", "EMI / loan debit count", 0.03,
            f"{int(emi_count)} EMI or loan debits appeared in the statement.",
        )

    obligation_ratio = values.get("fixed_obligation_to_income_ratio")
    if obligation_ratio is not None and obligation_ratio > 0.4:
        add(
            "fixed_obligation_to_income_ratio",
            "Fixed obligations to income",
            0.08 if obligation_ratio > 0.6 else 0.04,
            f"Fixed obligations were {obligation_ratio:.0%} of "
            "statement credits.",
        )

    cash_share = values.get("cash_withdrawal_share")
    if cash_share is not None and cash_share > 0.6:
        add(
            "cash_withdrawal_share", "Cash withdrawal share", 0.04,
            f"Cash withdrawals were {cash_share:.0%} of total debits.",
        )

    avg_credits = values.get("avg_monthly_credits") or 0
    avg_balance = values.get("avg_monthly_balance")
    if (
        avg_balance is not None
        and avg_credits > 0
        and avg_balance < avg_credits * 0.25
    ):
        add(
            "avg_monthly_balance", "Average monthly balance", 0.04,
            "Average monthly balance stayed below one quarter of "
            "monthly credits.",
        )
    minimum_balance = values.get("min_monthly_balance")
    if minimum_balance is not None and minimum_balance <= 0:
        add(
            "min_monthly_balance", "Minimum balance", 0.06,
            "The observed minimum balance was zero or below.",
        )
    elif (
        minimum_balance is not None
        and avg_credits > 0
        and minimum_balance < avg_credits * 0.1
    ):
        add(
            "min_monthly_balance", "Minimum balance", 0.03,
            "The observed minimum balance was below 10% of monthly credits.",
        )

    velocity = values.get("transaction_velocity")
    if velocity is not None and velocity > 10:
        add(
            "transaction_velocity", "Transaction velocity", 0.04,
            f"The statement averaged {velocity:.1f} transactions per day.",
        )

    if (
        observed_days >= 60
        and regularity is not None
        and regularity >= 2
        and (values.get("avg_monthly_balance") or 0) > 0
        and avg_balance >= avg_credits
        and not bounced
        and not overdraft_days
    ):
        add(
            "avg_monthly_balance", "Average monthly balance", -0.03,
            "Consistent salary credits and a positive average balance support "
            "repayment capacity.",
        )

    adjustment = max(
        -0.05, min(0.35, sum(row["adjustment"] for row in adjustments))
    )
    original_approval = float(result["probability"])
    adjusted_approval = min(1.0, max(0.0, original_approval - adjustment))
    adjusted_result = {
        **result,
        "probability": round(adjusted_approval, 4),
        "prediction": decide(1 - adjusted_approval),
    }
    start = (bank_period or {}).get("start")
    end = (bank_period or {}).get("end")
    period_label = (
        f"{start} to {end}" if start and end
        else "the available statement period"
    )
    if adjustments:
        descriptions = " ".join(
            f'{row["label"]}: {row["reason"]}' for row in adjustments
        )
        direction = "lowered" if adjustment > 0 else "raised"
        summary = (
            f"Transactions from {period_label} {direction} the model's "
            f"estimated approval probability from {original_approval:.0%} to "
            f"{adjusted_approval:.0%}. {descriptions}"
        )
    else:
        summary = (
            f"Transactions from {period_label} were included in the decision. "
            "No configured transaction risk indicator materially changed the "
            "model's estimated approval probability."
        )
    return adjusted_result, {
        "period": bank_period,
        "summary": summary,
        "baselineApprovalProbability": original_approval,
        "adjustedApprovalProbability": round(adjusted_approval, 4),
        "probabilityAdjustment": round(-adjustment, 4),
        "factors": adjustments,
    }


def get_or_create_applicant(user) -> Applicant:
    applicant = Applicant.query.filter_by(user_id=user.id).first()
    if not applicant:
        applicant = Applicant(user_id=user.id, full_name=user.full_name)
        db.session.add(applicant)
        db.session.commit()
    return applicant


def submit_application(
    user,
    features: dict,
    loan_type: str = "PERSONAL_LOAN",
    submission_details: dict | None = None,
) -> dict:
    applicant = get_or_create_applicant(user)
    User.query.filter_by(id=user.id).with_for_update().one()
    pending_documents = (
        Document.query.filter_by(user_id=user.id, application_id=None)
        .filter(Document.document_type.notin_(RETIRED_DOCUMENT_TYPES))
        .all()
    )
    document_report = build_report(user.id)
    require_submission_documents(document_report)
    from ml.documents.bank import BANK_FEATURES

    # Real statement measurements always enter the inference context. A model
    # trained with the optional bank schema consumes these as direct inputs;
    # the transparent policy below also adjusts compatible base-model odds.
    bank_features = document_report["features"]
    features = {
        **features,
        **{key: bank_features.get(key) for key in BANK_FEATURES},
    }

    # Run all ML work before persisting the application.  If an explainer or
    # model asset fails, no incomplete "Under Review" application is left in
    # the database.
    assignment = ab_test_service.get_assignment("credit_history")
    result = (
        ml_service.predict_application(
            features, assignment["version"] if assignment else None
        )
        if assignment
        else ml_service.predict_application(features)
    )
    model_result = result
    metadata = ml_service.get_model_metadata()
    shap_result = ml_service.get_shap_explanation(
        features, model_result["prediction"], model_result["probability"]
    )
    lime_result = ml_service.get_lime_explanation(
        features, model_result["prediction"], model_result["probability"]
    )
    result, transaction_reasoning = apply_bank_transaction_evidence(
        result,
        bank_features,
        document_report["bankStatement"].get("period"),
    )
    model_decision = result["prediction"]
    result["prediction"] = apply_verdict(
        model_decision, document_report["verdict"]
    )
    policy_note = (
        "\nDocument verification: "
        + document_report["verdict"]
        + ". "
        + " ".join(dict.fromkeys(document_report["reasons"]))
    )
    if result["prediction"] != model_decision:
        policy_note += (
            f" Model decision {model_decision} was overridden to"
            f" {result['prediction']} for document review."
        )
    transaction_note = (
        "\n\nBank statement transaction impact: "
        + transaction_reasoning["summary"]
    )
    shap_result["plain_english"] += policy_note + transaction_note
    lime_result["plain_english"] += policy_note + transaction_note
    if result["prediction"] == "DECLINE":
        cf_result = ml_service.get_counterfactual(features)
    else:
        cf_result = {
            "found": False,
            "message": (
                "Counterfactual suggestions are only generated for rejected"
                " applications."
            ),
            "alternatives": [],
        }
    if document_report["verdict"] != "VERIFIED":
        cf_result["message"] += (
            " Document verification must be resolved separately; model"
            " recourse cannot override document review."
        )

    application = Application(applicant_id=applicant.id, loan_type=loan_type)
    application.set_features(
        features | {
            "loan_type": loan_type,
            **(submission_details or {}),
            "transaction_decision_reasoning": transaction_reasoning,
        }
    )
    db.session.add(application)
    db.session.flush()
    # Staged documents remain private and user-owned until a successful
    # submission.
    for document in pending_documents:
        document.application_id = application.id
        if document.verification and not document.audits:
            verify_document(document, user.full_name)
    build_report(user.id, application.id, persist=True)
    application.public_id = f"APP-{application.created_at.year
                                   if application.created_at else
                                   __import__('datetime').datetime.utcnow().
                                   year} -{application.id: 04d} "

    prediction = Prediction(
        application_id=application.id,
        decision=result["prediction"],
        probability=result["probability"],
        model_name=metadata.get("final_model", "unknown"),
    )
    db.session.add(prediction)
    db.session.flush()
    if assignment:
        ab_test_service.record_result(
            assignment, prediction, result["prediction"], result["probability"]
        )

    # Persist the previously generated explanations alongside the prediction.
    shap_explanation = Explanation(prediction_id=prediction.id, method="shap")
    shap_explanation.set_contributions(shap_result["contributions"])
    shap_explanation.plain_english = shap_result["plain_english"]
    db.session.add(shap_explanation)

    lime_explanation = Explanation(prediction_id=prediction.id, method="lime")
    lime_explanation.set_contributions(lime_result["contributions"])
    lime_explanation.plain_english = lime_result["plain_english"]
    db.session.add(lime_explanation)

    counterfactual = Counterfactual(
        prediction_id=prediction.id,
        found=cf_result["found"],
        message=cf_result["message"],
    )
    counterfactual.set_alternatives(cf_result["alternatives"])
    db.session.add(counterfactual)

    # General model probability plus published, project-level profile
    # thresholds.
    bank_eligibilities = create_bank_eligibilities(
        application.id, result["probability"], features
    )
    if document_report["verdict"] != "VERIFIED":
        for record in bank_eligibilities:
            if record.decision == "APPROVED":
                record.decision = "NEEDS_REVIEW"
            values = record.to_dict()
            record.set_lists(
                values["reasons"]
                + ["Document verification: " + document_report["verdict"]],
                values["conditions"],
                values["riskIndicators"],
            )
    db.session.add_all(bank_eligibilities)

    db.session.commit()

    return {
        "application": application.to_dict(),
        "prediction": prediction.to_dict(),
        "shap": shap_explanation.to_dict(),
        "lime": lime_explanation.to_dict(),
        "comparison": ml_service.get_shap_lime_comparison(
            shap_result["contributions"], lime_result["contributions"]
        ),
        "counterfactual": counterfactual.to_dict(),
        "documents": _active_document_dicts(pending_documents),
        "documentVerification": document_report,
        "transactionReasoning": transaction_reasoning,
        "bankEligibility": [record.to_dict() for record in bank_eligibilities],
    }


def get_applications_for_user(user) -> list:
    applicant = Applicant.query.filter_by(user_id=user.id).first()
    if not applicant:
        return []
    return [
        app.to_dict()
        | {"prediction": app.prediction.to_dict() if app.prediction else None}
        for app in applicant.applications
    ]


def get_application_detail(application_id: int, user) -> dict | None:
    application = Application.query.get(application_id)
    if not application:
        return None

    # Applicants may only view their own applications; staff may view any.
    if (
        user.role in {"applicant", "client"}
        and application.applicant.user_id != user.id
    ):
        return None

    prediction = application.prediction
    if not prediction:
        return {"application": application.to_dict(), "prediction": None}

    explanations = {e.method: e.to_dict() for e in prediction.explanations}
    counterfactual = (
        prediction.counterfactuals[0].to_dict()
        if prediction.counterfactuals
        else None
    )

    comparison = None
    if "shap" in explanations and "lime" in explanations:
        comparison = ml_service.get_shap_lime_comparison(
            explanations["shap"]["contributions"],
            explanations["lime"]["contributions"],
        )

    return {
        "application": application.to_dict(),
        "prediction": prediction.to_dict(),
        "shap": explanations.get("shap"),
        "lime": explanations.get("lime"),
        "comparison": comparison,
        "counterfactual": counterfactual,
        "documents": _active_document_dicts(application.documents),
        "documentVerification": stored_report(
            application.applicant.user_id, application.id
        ),
        "transactionReasoning": application.get_features().get(
            "transaction_decision_reasoning"
        ),
        "bankEligibility": [
            record.to_dict() for record in application.bank_eligibilities
        ],
    }


def get_all_applications() -> list:
    """Staff/admin view of every application, for the analytics dashboard."""
    return [
        app.to_dict()
        | {
            "prediction": app.prediction.to_dict() if app.prediction else None,
            "applicant": {
                "full_name": app.applicant.full_name,
                "email": app.applicant.user.email,
            },
        }
        for app in Application.query.order_by(
            Application.created_at.desc()
        ).all()
    ]


def _active_document_dicts(documents):
    """Show current slots while preserving superseded records in the audit
    trail."""
    latest = {
        document.document_type: document
        for document in sorted(documents, key=lambda d: d.id)
        if document.document_type not in RETIRED_DOCUMENT_TYPES
    }
    return [document.to_dict() for document in latest.values()]


def get_pending_admin_reviews() -> list:
    """Return model REVIEW applications awaiting an admin decision."""
    applications = (
        Application.query.join(Prediction)
        .filter(
            Prediction.decision == "REVIEW",
            Application.admin_decision.is_(None),
        )
        .order_by(Application.created_at.asc())
        .all()
    )
    return [
        app.to_dict()
        | {
            "prediction": app.prediction.to_dict() if app.prediction else None,
            "shap": (
                next(
                    (
                        e.to_dict()
                        for e in app.prediction.explanations
                        if e.method == "shap"
                    ),
                    None,
                )
                if app.prediction
                else None
            ),
            "lime": (
                next(
                    (
                        e.to_dict()
                        for e in app.prediction.explanations
                        if e.method == "lime"
                    ),
                    None,
                )
                if app.prediction
                else None
            ),
            "counterfactual": (
                app.prediction.counterfactuals[0].to_dict()
                if app.prediction and app.prediction.counterfactuals
                else None
            ),
            "transactionReasoning": app.get_features().get(
                "transaction_decision_reasoning"
            ),
            "documents": _active_document_dicts(app.documents),
            "documentVerification": stored_report(
                app.applicant.user_id, app.id
            ),
            "applicant": {
                "full_name": app.applicant.full_name,
                "email": app.applicant.user.email,
            },
        }
        for app in applications
    ]


def decide_admin_review(
    application_id: int,
    decision: str,
    admin_id: int,
    feedback: str | None = None,
) -> dict | None:
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
    application_ref = (
        application.public_id or application.to_dict()["application_id"]
    )
    outcome = "approved" if decision == "APPROVE" else "rejected"
    message = f"Your application {application_ref} has been {outcome}."
    if feedback:
        message = (
            f"{message} {'Feedback' if decision == 'REJECT' else 'Note'}:"
            f" {feedback}"
        )
    db.session.add(
        Notification(
            user_id=application.applicant.user_id,
            application_id=application.id,
            message=message,
            type="status_update",
            decision_type=outcome,
        )
    )
    db.session.commit()
    return application.to_dict() | {
        "prediction": application.prediction.to_dict()
    }
