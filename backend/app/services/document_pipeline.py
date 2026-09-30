"""Upload orchestration. No raw extracted text, identifiers, or filenames in logs."""
import hashlib
import hmac
import json
import re
import uuid
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from flask import current_app
from app.extensions import db
from app.models import Document, DocumentVerification, DocumentAudit
from ml.documents.classifier import classify
from ml.documents.extraction import ExtractionError, detect_type, extract
from ml.documents.identity import AADHAAR, mask_identifiers, verhoeff

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
    mime, extension = detect_type(data)
    text, metadata, tables = extract(data, mime)
    prediction = classify(text)
    matched = prediction["type"] == slot and prediction["confidence"] >= current_app.config.get("DOCUMENT_TYPE_THRESHOLD", 0.65)
    checks = [check("document_type", "PASS" if matched else "FAIL",
                    "Document matches slot." if matched else "Wrong document type or insufficient classification confidence.", prediction)]
    fields = {"name": field(text, "name|employee name|account holder|holder name"),
              "dob": field(text, "dob|date of birth")}
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
    status = "REJECTED" if any(c["status"] == "FAIL" for c in checks) else "NEEDS_REVIEW"
    directory = Path(current_app.config["DOCUMENT_UPLOAD_DIR"])
    directory.mkdir(parents=True, exist_ok=True)
    # Retain only a masked extraction summary for Aadhaar, never the original card.
    if slot == "aadhaar":
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
        verification = DocumentVerification(document_id=document.id, status=status, confidence=prediction["confidence"],
            verification_message="Heuristic extraction completed; identity and consistency checks required.")
        verification.set_extracted_information(fields)
        verification.set_mismatches([c["reason"] for c in checks if c["status"] != "PASS"])
        db.session.add(verification)
        db.session.commit()
    except Exception:
        db.session.rollback()
        path.unlink(missing_ok=True)
        raise
    return document, checks
