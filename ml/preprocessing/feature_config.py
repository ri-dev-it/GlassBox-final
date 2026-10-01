"""
Single source of truth describing every model feature: its dtype,
readable label, and whether it may be varied by DiCE when generating
counterfactuals. The frontend application form and the backend
validators mirror this (see frontend/src/utils/featureConfig.ts and
backend/app/schemas/application_schema.py) -- if you add/remove a
feature here, update those too.
"""

# category: "numeric" | "categorical"
# mutable: whether DiCE is allowed to suggest changing this feature.
#          Protected/identity attributes and slow-to-change demographics
#          are marked immutable (see Milestone 24 / section 24 spec).
import os

FEATURES = {
    "checking_account_status": {
        "label": "Checking Account Status",
        "category": "categorical",
        "options": ["< 0 DM", "0-200 DM", ">= 200 DM", "no checking account"],
        "mutable": True,
    },
    "duration_months": {
        "label": "Loan Duration (months)",
        "category": "numeric",
        "min": 4,
        "max": 72,
        "mutable": True,
    },
    "credit_history": {
        "label": "Credit History",
        "category": "categorical",
        "options": [
            "no credits taken",
            "all credits paid back duly (this bank)",
            "existing credits paid back duly till now",
            "delay in past payments",
            "critical account / other credits existing",
        ],
        "mutable": True,
    },
    "purpose": {
        "label": "Loan Purpose",
        "category": "categorical",
        "options": [
            "new car",
            "used car",
            "furniture/equipment",
            "radio/television",
            "domestic appliances",
            "repairs",
            "education",
            "retraining",
            "business",
            "other",
        ],
        "mutable": True,
    },
    "credit_amount": {
        "label": "Loan Amount (₹)",
        "category": "numeric",
        "min": 250,
        "max": 20000,
        "mutable": True,
    },
    "savings_account": {
        "label": "Savings Account Balance",
        "category": "categorical",
        "options": [
            "< 100 DM",
            "100-500 DM",
            "500-1000 DM",
            ">= 1000 DM",
            "unknown/no savings account",
        ],
        "mutable": True,
    },
    "employment_since": {
        "label": "Employment Duration",
        "category": "categorical",
        "options": [
            "unemployed",
            "< 1 year",
            "1-4 years",
            "4-7 years",
            ">= 7 years",
        ],
        "mutable": True,
    },
    "installment_rate_percent": {
        "label": "Installment Rate (% of income)",
        "category": "numeric",
        "min": 1,
        "max": 4,
        "mutable": True,
    },
    "personal_status_sex": {
        "label": "Personal Status",
        "category": "categorical",
        "options": [
            "male:divorced/separated",
            "female:divorced/separated/married",
            "male:single",
            "male:married/widowed",
            "female:single",
        ],
        "mutable": (
            False
        ),  # encodes sex -- protected attribute, never suggested as a change
    },
    "other_debtors_guarantors": {
        "label": "Other Debtors / Guarantors",
        "category": "categorical",
        "options": ["none", "co-applicant", "guarantor"],
        "mutable": True,
    },
    "present_residence_since": {
        "label": "Years at Present Residence",
        "category": "numeric",
        "min": 0,
        "max": 50,
        "mutable": True,
    },
    "property": {
        "label": "Property",
        "category": "categorical",
        "options": [
            "real estate",
            "building society savings/life insurance",
            "car or other",
            "unknown/no property",
        ],
        "mutable": True,
    },
    "age": {
        "label": "Age",
        "category": "numeric",
        "min": 18,
        "max": 100,
        "mutable": False,  # protected/demographic attribute
    },
    "other_installment_plans": {
        "label": "Other Installment Plans",
        "category": "categorical",
        "options": ["bank", "stores", "none"],
        "mutable": True,
    },
    "housing": {
        "label": "Housing",
        "category": "categorical",
        "options": ["rent", "own", "for free"],
        "mutable": True,
    },
    "existing_credits_count": {
        "label": "Existing Credits at This Bank",
        "category": "numeric",
        "min": 0,
        "max": 10,
        "mutable": True,
    },
    "job": {
        "label": "Job Category",
        "category": "categorical",
        "options": [
            "unemployed/unskilled non-resident",
            "unskilled resident",
            "skilled employee/official",
            "management/self-employed/highly qualified",
        ],
        "mutable": True,
    },
    "num_dependents": {
        "label": "Number of Dependents",
        "category": "numeric",
        "min": 0,
        "max": 10,
        "mutable": True,
    },
    "telephone": {
        "label": "Registered Telephone",
        "category": "categorical",
        "options": ["none", "registered"],
        "mutable": True,
    },
    "foreign_worker": {
        "label": "Foreign Worker",
        "category": "categorical",
        "options": ["yes", "no"],
        "mutable": False,  # immutable status attribute
    },
}

TARGET_COLUMN = "credit_risk"

# Historical statement measurements are immutable in recourse: never suggest
# rewriting past transactions. Existing protected features remain immutable.
BANK_DOCUMENT_FEATURES = (
    os.environ.get("BANK_DOCUMENT_FEATURES", "false").lower() == "true"
)
if BANK_DOCUMENT_FEATURES:
    try:
        from documents.bank import BANK_FEATURES
    except ModuleNotFoundError:
        from ml.documents.bank import BANK_FEATURES
    FEATURES.update(
        {
            name: {
                "label": name.replace("_", " ").title(),
                "category": "numeric",
                "mutable": False,
            }
            for name in BANK_FEATURES
        }
    )

NUMERIC_FEATURES = [
    f for f, cfg in FEATURES.items() if cfg["category"] == "numeric"
]
CATEGORICAL_FEATURES = [
    f for f, cfg in FEATURES.items() if cfg["category"] == "categorical"
]
MUTABLE_FEATURES = [f for f, cfg in FEATURES.items() if cfg["mutable"]]
IMMUTABLE_FEATURES = [f for f, cfg in FEATURES.items() if not cfg["mutable"]]

# Not fed to the model as a feature (used only for the fairness audit).
PROTECTED_ATTRIBUTE_COLUMN = "sex"


def label_for(feature_name: str) -> str:
    return FEATURES.get(feature_name, {}).get(
        "label", feature_name.replace("_", " ").title()
    )
