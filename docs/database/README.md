# Database

MySQL, accessed via SQLAlchemy (`backend/app/models/`). The complete reference
schema is in `database/schema.sql`. Local SQLite development starts with
`create_all()` and applies additive compatibility columns for pre-existing
local databases; it never deletes or rebuilds application data. For MySQL,
apply the reference schema on a fresh database or manage equivalent changes
through your deployment migration process.

    mysql -u <user> -p < database/schema.sql

## Tables

The document pipeline adds three tables through revisions `m920260930`,
`n1020260930`, and `o1120260930`:

- **document_audits**: append-only upload SHA-256, optional keyed Aadhaar hash,
  user/document linkage, slot, masked extracted fields JSON and structured checks JSON.
- **verification_reports**: timestamped verdict/check snapshots, scoped to user
  and optionally application. Historical application reports do not change when
  an applicant uploads a new document for another application.
- **document_transactions**: normalized date, description, debit, credit, balance,
  keyed by document and sequence, with fixed-precision monetary columns.

No full Aadhaar number or raw OCR text belongs in any database field. Private
uploaded Aadhaar files are replaced by masked summaries before storage. Original
file SHA-256 permits reuse detection even though the retained summary differs.
New tables work with SQLite for tests and MySQL for deployment; run Alembic
upgrades on an existing managed database, not the fresh-schema SQL script.

- **users** -- login credentials, role (`client` / `admin` for current signup,
  `loan_officer`, plus supported legacy `applicant` rows).
- **applicants** -- one per user; kept separate from `users` so a future
  "apply on someone else's behalf" flow doesn't require restructuring.
- **applications** -- raw submitted feature payload (JSON-encoded), loan type, and one row per submission.
- **predictions** -- three-band decision (`APPROVE`, `REVIEW`, or `DECLINE`) + probability + model. Legacy `APPROVED`/`REJECTED` values remain readable in historical rows.
- **explanations** -- SHAP and LIME rows (method column), each with contributions (JSON) + plain-English text.
- **counterfactuals** -- found/message/alternatives (JSON) per prediction.
- **documents** and **document_verifications** -- uploaded document metadata,
  applicant/application linkage, and AI-assisted verification records. Staged
  uploads receive an `application_id` only after successful analysis submission. Each document also has an independent human-review status (`pending`, `approved`, or `rejected`), reviewer, and review timestamp.
- **bank_eligibility_results** -- legacy per-application educational bank-profile results.
- **merchant_transaction_profiles** -- persisted transaction behavior features plus actual monthly GMV/inflow used by merchant checks.
- **merchant_transaction_history** -- daily GMV, order, refund, and chargeback records for fraud review.
- **merchant_fraud_checks** -- persisted fraud score, rule flags, and flagged days.
- **merchant_tier_assessments** -- persisted Capital tier-gap results.
- **portfolio_exposure_snapshots** -- portfolio tier counts, simulated exposure, and blocking-signal summaries.
- **merchant_document_verifications** -- manual declared GST/bank values and consistency results, separate from uploaded-document verification.
- **model_metrics** -- held-out precision, recall, F1, and ROC-AUC snapshots for both income-based and transaction-based model versions.
- **governance_checks** -- historical fairness gate pass/fail decisions and failed checks per model version.
- **grounded_explanations** -- cached plain-English explanations keyed to an application or merchant, with source (`llm`/`template`) and SHAP driver names.

The merchant risk tables are additive to the original loan schema. Apply the
latest migration with `flask db upgrade`; `database/schema.sql` is also kept
as a complete fresh-MySQL reference. Capital thresholds and exposure amounts
are illustrative demo values, not real Razorpay Capital policy.

The existing `predictions.decision` column is already a string (`VARCHAR(20)`),
so no boolean-to-enum migration is required; new three-band values fit without
rewriting historical records.

## Admin accounts

The current registration endpoint accepts `client` and `admin` roles to match
the two choices in the signup form; `client` is the applicant-facing role.
The API documentation describes this public signup behavior. For a local
first admin account, the seed utility is also available:

    cd backend
    python ../database/seeds/seed_admin.py admin@example.com "Admin Name" a-strong-password

Admins can also create `loan_officer` or `admin` staff accounts via
`POST /api/auth/create-staff`. Production deployments should restrict public
admin signup to their own account provisioning policy.
