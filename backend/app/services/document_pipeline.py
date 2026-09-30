"""Upload orchestration. No raw extracted text, identifiers, or filenames in logs."""
import hashlib
import hmac
import json
import re
import uuid
import sys
from datetime import date
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from flask import current_app
from app.extensions import db
from app.models import Document, DocumentVerification, DocumentAudit, VerificationReport, DocumentTransaction
from ml.documents.classifier import classify
from ml.documents.extraction import ExtractionError, detect_type, extract
from ml.documents.identity import AADHAAR, mask_identifiers, verhoeff
from ml.documents.checks import amount, salary_arithmetic, metadata_checks, identity_checks
from ml.documents.bank import parse_statement, balance_check, bank_features
from ml.documents.consistency import cross_checks

SLOTS = {"aadhaar": "AADHAAR_CARD", "salary_slip": "SALARY_SLIP",
         "bank_statement": "BANK_STATEMENT", "income_certificate": "EMPLOYMENT_INCOME_PROOF"}


def check(name, status, reason, evidence=None):
    return {"name": name, "status": status, "reason": reason, "evidence": evidence or {}}


def field(text, labels):
    match = re.search(r"^(?:" + labels + r")\s*:\s*([^\n]+)", text, re.I | re.M)
    return mask_identifiers(match.group(1).strip())[:150] if match else None


def upload(user, file, slot):
    if slot not in SLOTS:
        raise ExtractionError("Unsupported document slot.")
    limit = current_app.config.get("MAX_DOCUMENT_SIZE_BYTES", 5 * 1024 * 1024)
    data = file.stream.read(limit + 1)
    if not data or len(data) > limit:
        raise ExtractionError("File size exceeds the allowed limit or file is empty.")
    csv_mode = False
    try:
        mime, extension = detect_type(data)
    except ExtractionError:
        if slot != "bank_statement":
            raise
        try:
            text = data.decode("utf-8-sig")
            if "\x00" in text:
                raise ValueError()
            parse_statement(text, csv_mode=True)
        except (UnicodeError, ValueError):
            raise ExtractionError("Expected a valid PDF/image or normalized bank CSV.") from None
        mime, extension, csv_mode = "text/csv", "csv", True
    if csv_mode:
        metadata, tables = {}, []
    else:
        text, metadata, tables = extract(data, mime)
    transactions = []
    prediction = classify(text)
    matched = prediction["type"] == slot and prediction["confidence"] >= current_app.config.get("DOCUMENT_TYPE_THRESHOLD", 0.65)
    checks = [check("document_type", "PASS" if matched else "FAIL",
                    "Document matches slot." if matched else "Wrong document type or insufficient classification confidence.", prediction)]
    fields = {"name": field(text, "name|employee name|account holder|holder name"),
              "dob": field(text, "dob|date of birth")}
    checks.append(metadata_checks(metadata))
    if slot == "salary_slip":
        fields.update({"gross": amount(text, "gross"), "deductions": amount(text, "deductions"),
                       "net_pay": amount(text, "net pay"), "employer": field(text, "employer"),
                       "pay_period": field(text, "pay period")})
        checks.append(salary_arithmetic(fields))
    if slot == "income_certificate":
        fields["annual_income"] = amount(text, "annual income")
        fields["employer"] = field(text, "employer")
    if slot == "bank_statement":
        try:
            transactions = parse_statement(text, tables, csv_mode)
            checks.append(balance_check(transactions))
            fields["bank_features"] = bank_features(transactions)
        except ValueError:
            transactions = []
            checks.append(check("bank_arithmetic", "WARN", "Statement layout or transaction values could not be parsed."))
    identifier_hash = None
    if slot == "aadhaar":
        match = AADHAAR.search(text)
        number = re.sub(r"\D", "", match.group()) if match else ""
        valid = verhoeff(number)
        checks.append(check("aadhaar_checksum", "PASS" if valid else "FAIL", "Checksum valid." if valid else "Missing identifier or invalid Verhoeff checksum."))
        if valid:
            secret = current_app.config.get("AADHAAR_HASH_KEY")
            if not secret:
                raise ExtractionError("Configure AADHAAR_HASH_KEY before accepting identity documents.")
            identifier_hash = hmac.new(secret.encode(), number.encode(), hashlib.sha256).hexdigest()
            fields["aadhaar"] = "********" + number[-4:]
    digest = hashlib.sha256(data).hexdigest()
    duplicate = DocumentAudit.query.filter(DocumentAudit.file_hash == digest, DocumentAudit.user_id != user.id).first()
    reused = identifier_hash and DocumentAudit.query.filter(DocumentAudit.aadhaar_hash == identifier_hash, DocumentAudit.user_id != user.id).first()
    checks.append(check("reuse", "FAIL" if duplicate or reused else "PASS",
                        "Document or identity is already associated with another account." if duplicate or reused else "No cross-account reuse detected."))
    if slot == "aadhaar":
        checks.extend(identity_checks(fields, {"name": user.full_name}, current_app.config.get("DOCUMENT_NAME_THRESHOLD", 88)))
    status = "REJECTED" if any(c["status"] == "FAIL" for c in checks) else "NEEDS_REVIEW"
    directory = Path(current_app.config["DOCUMENT_UPLOAD_DIR"])
    directory.mkdir(parents=True, exist_ok=True)
    # Retain only a masked extraction summary for Aadhaar, never the original card.
    if slot == "aadhaar" or AADHAAR.search(text):
        from reportlab.pdfgen import canvas
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer)
        pdf.drawString(40, 800, "Masked identity extraction - not an original document")
        for index, (key, value) in enumerate(fields.items()):
            pdf.drawString(40, 770 - index * 20, f"{key}: {value or 'Not extracted'}")
        pdf.save()
        stored_data, extension, mime = buffer.getvalue(), "pdf", "application/pdf"
    else:
        # Unknown/wrong-slot files can contain identity documents: do not retain them.
        stored_data = data if matched else b""
    path = directory / f"{uuid.uuid4().hex}.{extension}"
    try:
        path.write_bytes(stored_data)
        document = Document(user_id=user.id, document_type=SLOTS[slot], storage_reference=str(path),
                            original_filename=f"{slot}.{extension}", mime_type=mime, file_size=len(stored_data), status=status)
        db.session.add(document)
        db.session.flush()
        audit = DocumentAudit(document_id=document.id, user_id=user.id, file_hash=digest,
                              aadhaar_hash=identifier_hash, slot=slot, fields_json=json.dumps(fields), checks_json=json.dumps(checks))
        db.session.add(audit)
        for index, transaction in enumerate(transactions):
            db.session.add(DocumentTransaction(document_id=document.id, sequence=index,
                date=date.fromisoformat(transaction["date"]), description=mask_identifiers(transaction["description"]),
                debit=transaction["debit"], credit=transaction["credit"], balance=transaction["balance"]))
        verification = DocumentVerification(document_id=document.id, status=status, confidence=prediction["confidence"],
            verification_message="Heuristic extraction completed; identity and consistency checks required.")
        verification.set_extracted_information(fields)
        verification.set_mismatches([c["reason"] for c in checks if c["status"] != "PASS"])
        db.session.add(verification)
        db.session.flush()
        report = build_report(user.id, persist=True)
        slot_checks = [c for c in report["checks"] if c.get("slot") == slot]
        document.status = "REJECTED" if any(c["status"] == "FAIL" for c in slot_checks) else "NEEDS_REVIEW" if any(c["status"] == "WARN" for c in slot_checks) else "VERIFIED"
        verification.status = document.status
        verification.verification_message = "Heuristic checks completed; not government or bank authentication."
        verification.set_mismatches([c["reason"] for c in slot_checks if c["status"] != "PASS"])
        db.session.commit()
    except Exception:
        db.session.rollback()
        path.unlink(missing_ok=True)
        raise
    return document, slot_checks


def latest_audits(user_id, application_id=None):
    rows = (DocumentAudit.query.join(Document).filter(Document.user_id == user_id,
            Document.application_id == application_id).order_by(DocumentAudit.id).all())
    return {row.slot: row for row in rows}


def build_report(user_id, application_id=None, persist=False):
    audits = latest_audits(user_id, application_id)
    checks = []
    anchor = audits.get("aadhaar")
    anchor_fields = anchor.fields if anchor and anchor.aadhaar_hash and not any(c["status"] == "FAIL" for c in anchor.checks) else None
    for slot in SLOTS:
        row = audits.get(slot)
        if not row:
            checks.append({**check("required_document", "WARN", "Required document has not been uploaded."), "slot": slot})
            continue
        slot_checks = row.checks.copy()
        if slot != "aadhaar":
            slot_checks.extend(identity_checks(row.fields, anchor_fields, current_app.config.get("DOCUMENT_NAME_THRESHOLD", 88)))
        if slot == "aadhaar" and not row.fields.get("dob"):
            slot_checks.append(check("identity_dob", "WARN", "Aadhaar DOB could not be extracted."))
        checks.extend({**c, "slot": slot} for c in slot_checks)
    bank = audits.get("bank_statement")
    transactions = [r.to_dict() for r in DocumentTransaction.query.filter_by(document_id=bank.document_id).order_by(DocumentTransaction.sequence)] if bank else []
    checks.extend({**c, "slot": "cross_document"} for c in cross_checks(
        audits["salary_slip"].fields if "salary_slip" in audits else {},
        audits["income_certificate"].fields if "income_certificate" in audits else {}, transactions,
        current_app.config.get("DOCUMENT_SALARY_TOLERANCE", 0.02), current_app.config.get("DOCUMENT_ANNUAL_TOLERANCE", 0.20)))
    verdict = "REJECTED" if any(c["status"] == "FAIL" for c in checks) else "NEEDS_REVIEW" if any(c["status"] == "WARN" for c in checks) else "VERIFIED"
    report = {"verdict": verdict, "checks": checks,
              "reasons": [c["reason"] for c in checks if c["status"] != "PASS"],
              "identity": {k: v for k, v in (anchor_fields or {}).items() if k in {"name", "dob", "aadhaar"}},
              "features": audits["bank_statement"].fields.get("bank_features", {}) if "bank_statement" in audits else {}}
    if persist:
        for slot, row in audits.items():
            slot_checks = [c for c in checks if c.get("slot") == slot]
            status = "REJECTED" if any(c["status"] == "FAIL" for c in slot_checks) else "NEEDS_REVIEW" if any(c["status"] == "WARN" for c in slot_checks) else "VERIFIED"
            row.document.status = status
            if row.document.verification:
                row.document.verification.status = status
                row.document.verification.set_mismatches([c["reason"] for c in slot_checks if c["status"] != "PASS"])
        db.session.add(VerificationReport(user_id=user_id, application_id=application_id,
                                         verdict=verdict, report_json=json.dumps(report)))
    return report


def apply_verdict(decision, verdict):
    """Document policy can only make a decision more restrictive."""
    if verdict in {"REJECTED", "NEEDS_REVIEW"} and decision in {"APPROVE", "APPROVED"}:
        return "REVIEW"
    return decision


def stored_report(user_id, application_id=None):
    if application_id is None:
        return build_report(user_id)
    row = VerificationReport.query.filter_by(user_id=user_id, application_id=application_id).order_by(VerificationReport.id.desc()).first()
    return row.to_dict() if row else build_report(user_id, application_id)
