"""Assemble downloadable assessment reports from stored analysis records."""

from io import BytesIO

from app.models import Application
from app.services.indian_feature_mapper import model_value_to_indian_display

DISCLAIMER = "This explanation reflects the model's reasoning and does not guarantee a real-world lending decision."


def _factor_reason(contribution: dict) -> str:
    magnitude = abs(float(contribution["contribution"]))
    strength = "strongly" if magnitude >= 0.08 else "moderately" if magnitude >= 0.03 else "slightly"
    outcome = "approval" if contribution["direction"] == "positive" else "rejection"
    value = model_value_to_indian_display(contribution["feature"], contribution["value"])
    return f"{contribution['label']} was {value}, which {strength} pushed this prediction toward {outcome}."


def _reported_factor(contribution: dict) -> dict:
    return {
        "feature": contribution["feature"],
        "label": contribution["label"],
        "value": model_value_to_indian_display(contribution["feature"], contribution["value"]),
        "contribution": contribution["contribution"],
        "direction": contribution["direction"],
        "reason": _factor_reason(contribution),
    }


def get_report(application_id: int, user) -> dict | None:
    application = Application.query.get(application_id)
    if not application or (user.role in {"applicant", "client"} and application.applicant.user_id != user.id):
        return None
    if not application.prediction:
        return {"application": application.to_dict(), "report": None}

    explanations = {item.method: item for item in application.prediction.explanations}
    shap = explanations.get("shap")
    lime = explanations.get("lime")
    if not shap or not lime:
        # An incomplete historical record should be visible as such instead of
        # being silently recreated with new model/explainer output.
        return {"application": application.to_dict(), "report": None}

    prediction = application.prediction.to_dict()
    shap_factors = [_reported_factor(item) for item in shap.get_contributions()[:5]]
    lime_factors = [_reported_factor(item) for item in lime.get_contributions()[:3]]
    report = {
        "application_id": application.to_dict()["application_id"],
        "decision": prediction["decision"],
        "probability": prediction["probability"],
        "confidence": round((prediction["probability"] if prediction["decision"] == "APPROVE" else 1 - prediction["probability"]) * 100, 1),
        "factors": shap_factors,
        "lime": {"summary": lime.plain_english, "factors": lime_factors},
        "risk": {"score": prediction["risk_score"], "level": prediction["risk_level"]},
        "disclaimer": DISCLAIMER,
    }
    return {"application": application.to_dict(), "report": report}


def create_pdf(report: dict) -> BytesIO:
    """Render the stored report as a formatted PDF document."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except ImportError as error:
        raise RuntimeError("PDF support is unavailable. Install backend requirements including reportlab.") from error

    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4, rightMargin=1.7 * cm, leftMargin=1.7 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("ReportTitle", parent=styles["Title"], textColor=colors.HexColor("#102a4c"), spaceAfter=10)
    heading = ParagraphStyle("ReportHeading", parent=styles["Heading2"], textColor=colors.HexColor("#0d3b70"), spaceBefore=12, spaceAfter=6)
    body = ParagraphStyle("ReportBody", parent=styles["BodyText"], leading=16, spaceAfter=6)
    story = [Paragraph("Loan Assessment Report", title), Paragraph(f"Application ID: {report['application_id']}", body)]
    decision_color = "#177245" if report["decision"] == "APPROVE" else "#b7791f" if report["decision"] == "REVIEW" else "#b42318"
    story += [Paragraph(f"Decision: <font color='{decision_color}'><b>{report['decision'].title()}</b></font>", heading)]
    story.append(Paragraph(f"Model probability of approval: <b>{report['probability'] * 100:.1f}%</b><br/>Confidence in this outcome: <b>{report['confidence']:.1f}%</b>", body))
    story.append(Paragraph("Top contributing factors", heading))
    factor_rows = [[Paragraph("Factor", body), Paragraph("Direction", body), Paragraph("Explanation", body)]]
    for factor in report["factors"]:
        factor_rows.append([Paragraph(factor["label"], body), Paragraph(factor["direction"].title(), body), Paragraph(factor["reason"], body)])
    factors = Table(factor_rows, colWidths=[4.1 * cm, 2.4 * cm, 10.2 * cm], repeatRows=1)
    factors.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f1fb")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story += [factors, Paragraph("LIME-based local explanation", heading), Paragraph(report["lime"]["summary"].replace("\n", "<br/>"), body)]
    story += [Paragraph("Risk analysis", heading), Paragraph(f"Model-derived risk score: <b>{report['risk']['score']}/100</b> ({report['risk']['level'].title()} risk).", body)]
    story += [Spacer(1, 8), Paragraph(report["disclaimer"], ParagraphStyle("Disclaimer", parent=body, textColor=colors.HexColor("#64748b"), fontSize=8, leading=11))]
    document.build(story)
    output.seek(0)
    return output
