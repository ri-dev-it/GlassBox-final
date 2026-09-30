"""Pure, explainable consistency checks. Evidence excludes raw identifiers."""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from ml.documents.identity import name_score


def result(name, status, reason, evidence=None):
    return {"name": name, "status": status, "reason": reason, "evidence": evidence or {}}


def amount(text, label):
    match = re.search(r"^" + label + r"\s*:\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)\s*$", text, re.I | re.M)
    if not match:
        return None
    try:
        return float(Decimal(match.group(1).replace(",", "")))
    except InvalidOperation:
        return None


def salary_arithmetic(fields, tolerance=1):
    values = [fields.get(k) for k in ("gross", "deductions", "net_pay")]
    if any(v is None for v in values):
        return result("salary_arithmetic", "WARN", "Gross, deductions, or net pay could not be extracted.")
    gross, deductions, net = values
    valid = min(values) >= 0 and abs(gross - deductions - net) <= tolerance
    return result("salary_arithmetic", "PASS" if valid else "FAIL",
                  "Gross minus deductions matches net pay." if valid else "Salary arithmetic does not reconcile.",
                  {"difference": round(gross - deductions - net, 2)})


def metadata_checks(metadata):
    flags = []
    if re.search(r"photoshop|canva|illustrator", " ".join(metadata.get(k, "") for k in ("Producer", "Creator")), re.I):
        flags.append("PDF reports an image/design editor.")
    def date(value):
        match = re.search(r"(?:D:)?(\d{14})", value or "")
        try:
            return datetime.strptime(match.group(1), "%Y%m%d%H%M%S") if match else None
        except ValueError:
            return None
    created, modified = date(metadata.get("CreationDate")), date(metadata.get("ModDate"))
    if created and modified and modified > created:
        flags.append("PDF modification time is later than creation time.")
    return result("pdf_metadata", "WARN" if flags else "PASS",
                  " ".join(flags) if flags else "No configured PDF metadata warning detected; this does not establish authenticity.")


def identity_checks(fields, anchor, threshold=88):
    if not anchor or not anchor.get("name"):
        return [result("identity_name", "WARN", "A valid Aadhaar name anchor is required.")]
    if not fields.get("name"):
        return [result("identity_name", "WARN", "Document holder name could not be extracted.")]
    score = name_score(fields["name"], anchor["name"])
    checks = [result("identity_name", "PASS" if score >= threshold else "FAIL",
                     "Holder matches identity anchor." if score >= threshold else "Holder name does not match the Aadhaar identity.", {"score": round(score, 2), "threshold": threshold})]
    if fields.get("dob") and anchor.get("dob"):
        def normalize(value):
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    return datetime.strptime(value, fmt).date().isoformat()
                except ValueError:
                    continue
            return None
        a, b = normalize(fields["dob"]), normalize(anchor["dob"])
        checks.append(result("identity_dob", "WARN" if not a or not b else "PASS" if a == b else "FAIL",
                             "DOB comparison complete." if a and b else "DOB could not be normalized."))
    return checks
