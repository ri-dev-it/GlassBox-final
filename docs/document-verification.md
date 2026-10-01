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
`pan`, `salary_slip`, `bank_statement`) and `file`. Existing
`documentType` names map to those slots. File content, not client MIME or filename,
determines PDF/PNG/JPEG format. Default limits: 5 MiB, 20 PDF pages, 20 megapixels,
30 seconds per OCR call. OCR requires Tesseract, on PATH or configured using
`TESSERACT_CMD`. Scanned PDFs use bundled PDFium; Poppler is not required.
Scanned PDF pages render at up to 300 DPI, bounded by the 20-megapixel OCR cap.
Digital PDFs use pdfplumber. Unreadable inputs produce explicit errors.

The upload path uses lightweight distinctive text markers only to reject an
obvious mismatch between the document and its selected slot. It has no
confidence-score gate. If OCR cannot read the page or no distinctive type
marker is found, the file is stored for review rather than rejected. This is a
demo usability check, not document authentication.

Holder-name matching is a soft check: a clear mismatch or missing name marks
the document for administrator review, but does not block upload. DOB, issuer
markers, Aadhaar checksum, PAN identifier extraction, metadata, and salary
arithmetic are informational/review signals, not upload gates.

Raster OCR applies EXIF orientation, grayscale/autocontrast normalization,
small-angle deskewing, bounded upscaling for small images, and sharpening using
Pillow. Pillow and NumPy are already in the backend environment; no OpenCV
dependency is required. OCR labels accept common punctuation/spacing errors
(for example, `DOB;` or `Name Asha`). Scanned PDF rendering uses up to 300 DPI,
bounded by the existing 20-megapixel cap.

For local diagnosis only, set `DOCUMENT_OCR_DIAGNOSTICS=true` in
`backend/.env` and restart the Flask development server. Diagnostics are emitted
only while Flask debug mode is on, and log OCR character/line counts, issuer and
field-recognition booleans, predicted type, and score. They never log the raw OCR
text, extracted name, DOB, or identifier. Set the flag back to `false` after the
re-test.

To physically inspect OCR text from Aadhaar/PAN during a local debug session,
also set `DOCUMENT_OCR_RAW_DEBUG=true` in `backend/.env` and restart Flask. Before
classification, the raw text is written to
`backend/private_uploads/ocr-debug/<slot>-<random>.txt`; the log prints only that
file path. This file contains sensitive extracted data. Inspect it locally,
delete it immediately after diagnosis, and turn the flag back off. Raw debug
capture requires Flask debug mode and is disabled by default. Never enable it
for shared or production accounts.

For a real browser smoke test, install `playwright` into the backend environment
and have Chrome and Tesseract installed, then run
`python tests/e2e/document_upload_smoke.py` from the repository root. It starts
isolated Flask/Vite servers and an in-memory database, uploads synthetic text
PDFs, a PNG, and a scanned PDF, and checks that PAN-in-Aadhaar is rejected and
application submission is disabled. It does not use existing accounts or files.

Random filenames are stored under `DOCUMENT_UPLOAD_DIR`, outside the web root.
Original accepted PDFs/images, including Aadhaar, are retained privately for
preview. Raw OCR text is not stored in database columns. Cross-account
duplicate-hash rejection is disabled for this demo workflow. An obvious
wrong-slot original is not retained. Do not enable request-body or SQL parameter
logging for document endpoints.

## Identity and audit

`document_audits` stores extracted fields, hashes and structured checks; raw OCR
is never a database field. `verification_reports` stores immutable snapshots of
all slot checks, with `PASS`, `WARN`, or `FAIL`, reason and evidence. New uploads
supersede the active slot by increasing audit ID without deleting prior evidence.
Each application uses only its own staged uploads, preventing a later replacement
from changing historical reports.

When a holder name is extracted, it is compared with the logged-in user's
registered name using RapidFuzz and conservative initial/token normalization.
`DOCUMENT_NAME_THRESHOLD` defaults to 88/100. A mismatch or missing name is a
review warning. Duplicate-file hashes, DOB differences, metadata, salary
arithmetic, and balance reconciliation are not upload rejection gates.

An obvious slot-type mismatch is REJECTED. Other consistency failures/warnings
produce NEEDS_REVIEW; accepted documents retain the `UPLOADED` state while admin
review flags remain visible. These checks do not authenticate the issuer.

## Reports and decision policy

`GET /api/documents/report` returns the current user's staged report.
`GET /api/documents/applications/<id>/report` returns the saved application report;
only the owner or staff may read it. All routes require JWT authentication.
The `/documents` frontend page (also embedded in `/apply`) has four upload slots,
upload progress, rejection reasons and a PASS/WARN/FAIL table. Results shows the
stored verdict. Missing documents require review. REJECTED or NEEDS_REVIEW caps
model approval at REVIEW, preserves model probability and adds the policy reason
to persisted SHAP/LIME explanation text. Declines are never upgraded.
The Results page groups the retained 90-day transaction table, computed features,
and transaction-adjusted probability explanation under Transaction Analysis.
Reports shows the same statement data and preview link in Submitted Form; the
admin document verification view previews the original bank PDF and its parsed
transaction details.

## Bank features and optional model

Bank CSV is the sole nonbinary upload exception: strict UTF-8, the exact header
`date,description,debit,credit,balance`, validated dates and finite monetary values.
Use metadata lines before that header (`Bank Statement`, `Account holder: ...`,
`Account number: ...`, `IFSC: ...`) for classification and identity binding.
Missing holder metadata cannot produce VERIFIED. CSV is not accepted in other slots.
PDF tables use the same five columns; plain text rows require date, description,
debit, credit, balance. Unsupported layouts require review instead of guessing.

The feature dictionary contains:

| Feature | Definition |
| --- | --- |
| avg_monthly_credits | Total credits / calendar months intersecting the observed window, including empty months |
| salary_regularity | Maximum distinct months with salary/payroll-labeled credits within 10% of an observed amount |
| avg_monthly_balance | Mean of monthly mean daily closing balances, carried forward within the observed window |
| min_monthly_balance | Minimum daily closing balance across observed months |
| emi_debit_count / emi_debit_share | EMI/loan/installment debit count / share of debit transactions |
| fixed_obligation_to_income_ratio | Total EMI/loan/installment debits / credits; null if no credits |
| bounced_payment_count | Rows with bounced/returned/dishonour/NSF descriptions |
| cash_withdrawal_share | ATM/cash-withdrawal debit amounts / total debits |
| negative_balance_days | Observed days with negative carried-forward closing balance |
| transaction_velocity | Nonzero transactions / observed calendar days |
| income_volatility | Population standard deviation of monthly credits / mean; null if no credits |

The window runs from first to last parsed transaction; it is not proof of complete
statement coverage. Partial months are not annualized. Transactions from different
uploads are not concatenated, avoiding duplicate counting. Transfer credits are
not necessarily income. Labels are heuristics, not a bank-confirmed obligation list.

For an accepted applicant statement, uploads retain only transactions dated in
the latest 90-day window ending on the newest parsed transaction. A statement
with no parsed transactions fails submission validation; at least two rows are
still needed for running-balance reconciliation. The report and result page show
the retained transaction table and observed date range.

At submission, extracted bank features override any client-supplied values and
are always passed in the inference feature dictionary. If a compatible
bank-document model is enabled, its trained pipeline consumes those features
directly and SHAP/LIME can attribute them. The checked-in default model has no
bank-document columns, so serving keeps it schema-compatible and applies a
separate bounded, rule-based probability adjustment to its output using named
statement features (salary regularity, credits, balances, EMI burden/count,
bounces, cash share, overdraft days, transaction velocity, and income
volatility). The baseline and adjusted probabilities, material feature factors,
and plain-language reason are persisted with the application and shown to
applicants and administrators. This adjustment is explicit policy, not a claim
that the default model learned those transaction relationships; recalibration
and governance review are required before production use.

Set `BANK_DOCUMENT_FEATURES=true` in both training and serving environments to
extend individual features and SHAP/LIME/DiCE inputs. Restart processes after
changing it. Training writes separate `bank_document_model.joblib` and metadata;
the default model is untouched. Generate the demo dataset with
`python ml/data/synthetic_individual_bank.py`, then run `python training/train.py`
from `ml/` with the flag set. The generator combines UCI rows with independent
synthetic histories, never using target labels to generate features. This tests
integration only: no claim of improved lending accuracy or real transaction linkage.
The normal governance gate still applies; a failed model is not saved. All bank
history features are immutable for DiCE; existing age/sex/nationality protections
remain. Serving supplies bank values from persisted extraction, not request JSON.

## Validation recorded during implementation

- Python backend/ML suite: 112 tests passed on Python 3.12 in the available
  Windows environment. Source uses Python 3.11-compatible syntax; Python 3.11
  execution remains a deployment check.
- Frontend: 10 Vitest tests passed; TypeScript/Vite production build passed.
- TF-IDF classifier: 40/40 correct (1.000 accuracy) on the generated synthetic
  template holdout. Templates overlap the training family; this is not real-world
  accuracy or an independent layout evaluation.
- Digital-PDF and normalized CSV paths, missing-Tesseract errors, and SQLite
  migration upgrade/downgrade were exercised. Tesseract is not installed in this
  environment, so actual OCR was not run. A live MySQL migration and the optional
  bank-augmented credit model retraining were not run.

## Extraction and deployment limitations

Field extraction currently supports explicit English labels (for example
`Employee name:`, `DOB:`, `Net Pay:`), normalized dates and the documented bank
columns. It does not support every bank layout, language, handwritten form or
multi-line transaction description. Unavailable fields require review. Missing
or unreadable file validation errors return 400; parsed rejected documents return
422 with saved checks. Uploads are not malware-scanned or digitally authenticated.
Storage permissions/encryption, retention policy, rate limits, and government
integration belong to deployment hardening. Pre-existing legacy Aadhaar originals
are not rewritten by database migrations; their preview is blocked, and operators
must separately redact/remove old private files under their retention policy.

Legacy fingerprint tables remain in the schema for existing records, but the
upload path no longer creates or checks duplicate ownership claims. MySQL locks
each account while publishing documents or binding a submission snapshot.
SQLite is a local demo/test store, not a multi-worker concurrency validation
target. The document migrations are reversible; tests exercise SQLite
upgrade/downgrade, not a live MySQL server.

### Reset local upload test data

In the current development setup, SQLite is `backend/xai_loan.db` and private
files are under `backend/private_uploads`. Stop Flask first. To reset all local
accounts, applications, upload records, legacy fingerprint rows, and private
uploaded files (but not `.env` or ML model files), run this PowerShell from the
repository root:

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
Copy-Item .\backend\xai_loan.db ".\backend\xai_loan.db.$stamp.bak"
Remove-Item .\backend\xai_loan.db, .\backend\xai_loan.db-wal, .\backend\xai_loan.db-shm -Force -ErrorAction SilentlyContinue
if (Test-Path .\backend\private_uploads) {
  Remove-Item .\backend\private_uploads -Recurse -Force
}
```

The development app factory recreates the empty SQLite schema at startup. This
is a destructive full local reset; do not run it against MySQL or any shared or
production database. Deleting a staged document through the API removes its
stored file and audit rows, but deliberately retains its fingerprint ownership
claim, so that alone will not allow the exact same file to be reused by another
account.

## Cross-document rules

Net salary must appear as a bank credit in the salary's `YYYY-MM` pay period,
within `DOCUMENT_SALARY_TOLERANCE` (default 0.02 relative). Missing month coverage
requires review, not a fabricated mismatch. Income-certificate annual income is
compared to **gross** monthly salary times 12, within
`DOCUMENT_ANNUAL_TOLERANCE` (default 0.20). Other sources of income or bonuses can
cause legitimate mismatches and need human adjudication. When available, employer
labels are compared; absence from a bank description warns, not proof of fraud.
All documents' holder names and DOBs bind to the same identity anchor.

## Scope and future integrations

This is heuristic consistency checking, not authentication or government database
verification. A checksum-valid number can be fabricated. Synthetic documents are
clearly marked and must never be presented as issued identities. OCR and layout
errors require review. Future production integrations: DigiLocker, Account
Aggregator, Aadhaar offline e-KYC/Secure QR signature verification, and PAN APIs.
