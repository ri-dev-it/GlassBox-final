# Applicant document verification

## Repository map

Flask routes call services, which use SQLAlchemy and `ml/`. Individual prediction,
SHAP/LIME and DiCE are orchestrated by `application_service.py` / `ml_service.py`.
React's application form embeds `DocumentVerificationSection`; Results shows stored
decisions. Alembic migrations live in `backend/migrations/versions`, with a MySQL
reference schema in `database/schema.sql`. Backend and ML pytest suites live in
`tests`; frontend uses Vitest.

The original applicant upload route is `backend/app/routes/documents.py`, with
optional extraction in `document_verification_service.py`. Merchant manual-value
checks remain separately available in `ml/verification/document_checker.py` for
backward compatibility; those are still simulated declarations.

## Upload boundary

Authenticated multipart `POST /api/documents` accepts `slot` (`aadhaar`,
`salary_slip`, `bank_statement`, `income_certificate`) and `file`. Existing
`documentType` names map to those slots. File content, not client MIME or filename,
determines PDF/PNG/JPEG format. Default limits: 5 MiB, 20 PDF pages, 20 megapixels,
30 seconds per OCR call. OCR requires Tesseract; scanned PDFs also require Poppler.
Digital PDFs use pdfplumber. Unreadable inputs produce explicit errors.

Rules contribute 75% and synthetic TF-IDF/logistic regression contributes 25% of
the type score. `DOCUMENT_TYPE_THRESHOLD` defaults to 0.65. Scores are heuristic,
not calibrated probabilities. Evidence contains rule patterns, never matching raw
identifiers. The synthetic template holdout is a smoke test, not real-document
accuracy or evidence of generalization.

Random filenames are stored under `DOCUMENT_UPLOAD_DIR`, outside the web root.
SHA-256 records refer to original uploaded bytes. Aadhaar original bytes are never
retained: only a masked PDF extraction summary is stored. The database contains
last four digits and an HMAC-SHA256 identifier digest using `AADHAAR_HASH_KEY` as a
secret salt. Use a stable, high-entropy secret shared across application workers;
rotating it requires a deliberate hash migration and breaks old reuse comparisons.
Raw text is transient. Do not enable request-body or SQL parameter logging for
document endpoints. Rejected wrong-slot originals are not retained.

## Identity and audit

`document_audits` stores extracted fields, hashes and structured checks; raw OCR
is never a database field. `verification_reports` stores immutable snapshots of
all slot checks, with `PASS`, `WARN`, or `FAIL`, reason and evidence. New uploads
supersede the active slot by increasing audit ID without deleting prior evidence.
Each application uses only its own staged uploads, preventing a later replacement
from changing historical reports.

The Aadhaar holder must match the registered account name. Other documents bind
to that anchor, with RapidFuzz and conservative initial/token normalization.
`DOCUMENT_NAME_THRESHOLD` defaults to 88/100. Missing names/anchors cause review;
conflicting names or DOBs fail. File and keyed identifier reuse across accounts
fails without disclosing the other account. Checksum or type failures also fail.
PDF editor metadata or a later modification timestamp only warns: legitimate
PDFs may have both. Salary gross minus deductions must equal net pay within one
currency unit. Bank running balances reconcile within 0.02; the first opening
balance cannot be independently checked.

Overall: any FAIL => REJECTED; otherwise any WARN or missing required slot =>
NEEDS_REVIEW; otherwise VERIFIED. VERIFIED means these checks passed, not that
the issuer authenticated the document.

## Limitations

## Reports and decision policy

`GET /api/documents/report` returns the current user's staged report.
`GET /api/documents/applications/<id>/report` returns the saved application report;
only the owner or staff may read it. All routes require JWT authentication.
The `/documents` frontend page (also embedded in `/apply`) has four upload slots,
upload progress, rejection reasons and a PASS/WARN/FAIL table. Results shows the
stored verdict. Missing documents require review. REJECTED or NEEDS_REVIEW caps
model approval at REVIEW, preserves model probability and adds the policy reason
to persisted SHAP/LIME explanation text. Declines are never upgraded.

## Limitations

This is heuristic consistency checking, not authentication or government database
verification. A checksum-valid number can be fabricated. Synthetic documents are
clearly marked and must never be presented as issued identities. OCR and layout
errors require review. Future production integrations: DigiLocker, Account
Aggregator, Aadhaar offline e-KYC/Secure QR signature verification, and PAN APIs.
