"""AI-assisted document verification boundary.

This intentionally performs consistency checks only. It is not government or
bank authentication. OCR is optional: deployments may install/configure an
OCR provider without changing routes or database code.
"""
import re
from pathlib import Path

from app.models import DocumentVerification

PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
AADHAAR_PATTERN = re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b")


def _read_text(path: str, mime_type: str) -> str:
    """Extract text when an optional OCR runtime is available; never log it."""
    try:
        if mime_type == "application/pdf":
            from pypdf import PdfReader  # optional deployment dependency
            return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
        from PIL import Image  # optional deployment dependency
        import pytesseract
        return pytesseract.image_to_string(Image.open(path))
    except Exception:
        return ""


def _masked(value: str, keep_start: int = 5, keep_end: int = 1) -> str:
    return value[:keep_start] + "*" * max(0, len(value) - keep_start - keep_end) + value[-keep_end:]


def verify_document(document, applicant_name: str) -> DocumentVerification:
    text = _read_text(document.storage_reference, document.mime_type)
    normalized_text = " ".join(text.upper().split())
    name_present = bool(applicant_name and applicant_name.upper() in normalized_text)
    extracted, mismatches = {}, []
    status, confidence = "NEEDS_REVIEW", 0.45

    if document.document_type == "PAN_CARD":
        match = PAN_PATTERN.search(normalized_text)
        if match:
            extracted["pan"] = _masked(match.group())
            extracted["panFormat"] = "Valid"
            if name_present:
                extracted["nameMatch"] = "Match"
                status, confidence = "VERIFIED", 0.88
            else:
                mismatches.append("Applicant name could not be confirmed from the document.")
                confidence = 0.65
        else:
            mismatches.append("A valid PAN-format identifier was not detected.")
            status, confidence = "NEEDS_REVIEW", 0.35
    elif document.document_type == "AADHAAR_CARD":
        match = AADHAAR_PATTERN.search(normalized_text)
        if match:
            extracted["aadhaar"] = _masked(re.sub(r"[ -]", "", match.group()), 0, 4)
            extracted["identifierStructure"] = "Detected"
            status, confidence = ("VERIFIED", 0.83) if name_present else ("NEEDS_REVIEW", 0.62)
            if not name_present:
                mismatches.append("Applicant name could not be confirmed from the document.")
        else:
            mismatches.append("An Aadhaar-style identifier was not detected.")
            confidence = 0.35
    else:
        # OCR availability and the applicant-name match are evidence, never proof.
        extracted["textDetected"] = bool(normalized_text)
        extracted["nameMatch"] = "Match" if name_present else "Not confirmed"
        if normalized_text and name_present:
            status, confidence = "VERIFIED", 0.74
        elif normalized_text:
            mismatches.append("Applicant name could not be confirmed from the document.")
            confidence = 0.55
        else:
            mismatches.append("Readable text could not be extracted; manual review is required.")
            confidence = 0.30

    message = ("Document information appears consistent with the submitted application. "
               "This is AI-assisted verification, not legal document authentication.") if status == "VERIFIED" else (
               "AI-assisted verification requires review. This result is not a government or bank authentication decision.")
    verification = document.verification or DocumentVerification(document_id=document.id)
    verification.status, verification.confidence, verification.verification_message = status, confidence, message
    verification.set_extracted_information(extracted)
    verification.set_mismatches(mismatches)
    document.status = status
    return verification
