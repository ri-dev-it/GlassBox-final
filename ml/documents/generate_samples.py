"""Generate explicitly synthetic classifier examples; no personal
identifiers."""

import json
from pathlib import Path

TEMPLATES = {
    "aadhaar": [
        (
            "Government of India Unique Identification Authority DOB Female"
            " identity"
        ),
        "UIDAI Government of India YOB Male resident card",
    ],
    "salary_slip": [
        "Salary slip Basic HRA Gross Deductions Net Pay Employer Pay period",
        (
            "Payslip employee earnings Basic Gross HRA deductions net pay"
            " employer"
        ),
    ],
    "bank_statement": [
        "Bank statement IFSC Account number Debit Credit Balance",
        "Account no IFSC bank statement date debit credit closing balance",
    ],
    "pan": [
        (
            "Permanent Account Number PAN card Income Tax Department"
            " Government of India ABCDE1234F"
        ),
        (
            "Income Tax Department Government of India Permanent Account"
            " Number identity PAN card"
        ),
    ],
}


def generate():
    rows = []
    for kind, templates in TEMPLATES.items():
        for i in range(40):
            rows.append(
                {
                    "type": kind,
                    "text": (
                        f"{templates[i % 2]} Example district {i} fictional"
                        " sample"
                    ),
                    "split": "train" if i < 30 else "test",
                }
            )
    Path(__file__).with_name("synthetic_texts.json").write_text(
        json.dumps(rows, indent=2)
    )


if __name__ == "__main__":
    generate()
