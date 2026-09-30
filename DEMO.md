# Document verification demo

1. Install backend requirements, configure a private `AADHAAR_HASH_KEY`, apply
   migrations, and run backend/frontend as in README. Digital PDF fixtures do
   not need Tesseract. Regenerate with `python tests/fixtures/generate_documents.py`.
2. Register a **client** named **Asha Example** using a demo email. Use one account
   for all three scenarios: reusing the same identity in another account is blocked.
3. Open `/documents` (or the documents section of `/apply`). Files are in
   `tests/fixtures/documents/`; all are explicitly synthetic.

## 1. Consistent documents

Upload `aadhaar.pdf`, `salary_slip.pdf`, `bank_statement.pdf`, and
`income_certificate.pdf` into their corresponding slots. The report becomes
**VERIFIED**. It shows only a masked Aadhaar identifier and the measured bank
features. The salary credit is in January 2026 and the certificate matches gross
salary times twelve. VERIFIED means heuristic consistency, not issuer validation.

## 2. Wrong document in Aadhaar slot

Upload `wrong_slot.pdf` (a salary slip) into Aadhaar. The API responds **422**,
the UI explains the type mismatch, and the report is **REJECTED**. Restore
`aadhaar.pdf` before proceeding. Old audit snapshots remain available in the DB.

## 3. Another person's salary slip

Replace the salary slip with `mismatched_salary.pdf`. The holder name differs
from the identity anchor: upload is rejected and the report becomes **REJECTED**.
Submitting the loan cannot produce a model-based APPROVE: document policy caps
it at REVIEW, while an existing model DECLINE remains DECLINE. The SHAP/LIME
explanation text records the override. Restore `salary_slip.pdf` to recover.

Optional: `edited_salary.pdf` fails arithmetic. `aadhaar.png` exercises OCR and
requires Tesseract; extraction may require manual review. The default credit
model must already be trained to demonstrate a complete loan decision; a
VERIFIED document set does not guarantee model approval.
