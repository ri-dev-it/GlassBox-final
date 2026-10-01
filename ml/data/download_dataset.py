"""
Download and label the Statlog (German Credit Data) dataset from the UCI
Machine Learning Repository.

Source:
    https://archive.ics.uci.edu/dataset/144/statlog+german+credit+data
    (raw file: german.data, whitespace-separated, no header)

This is a real, public, well-documented credit-risk dataset: 1000
applicants, 20 features, binary target (good/bad credit risk). It is
commonly used in credit-scoring and fairness research because it
includes a personal-status/sex field and age, which we use (as a
documented proxy) for the fairness audit in Milestone 11.

Run this once, with an internet connection, before training:

    cd ml
    python data/download_dataset.py

It writes a labeled CSV to data/raw/german_credit.csv. Nothing here is
fabricated -- every row is a real record from the UCI dataset; this
script only adds human-readable column names and decodes the coded
categorical values into readable text.
"""

import os
import sys
import urllib.request

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RAW_DATA_FILE, DATA_RAW_DIR  # noqa: E402

SOURCE_URL = (
    "https://archive.ics.uci.edu/ml/machine-learning-databases/"
    "statlog/german/german.data"
)

# Column order per the UCI documentation (german.doc).
COLUMNS = [
    "checking_account_status",
    "duration_months",
    "credit_history",
    "purpose",
    "credit_amount",
    "savings_account",
    "employment_since",
    "installment_rate_percent",
    "personal_status_sex",
    "other_debtors_guarantors",
    "present_residence_since",
    "property",
    "age",
    "other_installment_plans",
    "housing",
    "existing_credits_count",
    "job",
    "num_dependents",
    "telephone",
    "foreign_worker",
    "credit_risk_raw",  # 1 = good, 2 = bad (UCI encoding)
]

# Coded-value -> readable-text lookups, taken directly from the UCI
# codebook (german.doc). Kept verbatim/faithful to the source document.
DECODE_MAPS = {
    "checking_account_status": {
        "A11": "< 0 DM",
        "A12": "0-200 DM",
        "A13": ">= 200 DM",
        "A14": "no checking account",
    },
    "credit_history": {
        "A30": "no credits taken",
        "A31": "all credits paid back duly (this bank)",
        "A32": "existing credits paid back duly till now",
        "A33": "delay in past payments",
        "A34": "critical account / other credits existing",
    },
    "purpose": {
        "A40": "new car",
        "A41": "used car",
        "A42": "furniture/equipment",
        "A43": "radio/television",
        "A44": "domestic appliances",
        "A45": "repairs",
        "A46": "education",
        "A48": "retraining",
        "A49": "business",
        "A410": "other",
    },
    "savings_account": {
        "A61": "< 100 DM",
        "A62": "100-500 DM",
        "A63": "500-1000 DM",
        "A64": ">= 1000 DM",
        "A65": "unknown/no savings account",
    },
    "employment_since": {
        "A71": "unemployed",
        "A72": "< 1 year",
        "A73": "1-4 years",
        "A74": "4-7 years",
        "A75": ">= 7 years",
    },
    "personal_status_sex": {
        "A91": "male:divorced/separated",
        "A92": "female:divorced/separated/married",
        "A93": "male:single",
        "A94": "male:married/widowed",
        "A95": "female:single",
    },
    "other_debtors_guarantors": {
        "A101": "none",
        "A102": "co-applicant",
        "A103": "guarantor",
    },
    "property": {
        "A121": "real estate",
        "A122": "building society savings/life insurance",
        "A123": "car or other",
        "A124": "unknown/no property",
    },
    "other_installment_plans": {
        "A141": "bank",
        "A142": "stores",
        "A143": "none",
    },
    "housing": {
        "A151": "rent",
        "A152": "own",
        "A153": "for free",
    },
    "job": {
        "A171": "unemployed/unskilled non-resident",
        "A172": "unskilled resident",
        "A173": "skilled employee/official",
        "A174": "management/self-employed/highly qualified",
    },
    "telephone": {
        "A191": "none",
        "A192": "registered",
    },
    "foreign_worker": {
        "A201": "yes",
        "A202": "no",
    },
}


def derive_sex(personal_status_sex_decoded: str) -> str:
    """
    The dataset encodes sex jointly with marital status. We split out a
    'sex' column as a documented proxy attribute for fairness analysis
    (see docs/fairness/README.md). This is NOT a self-reported gender
    field -- it's inferred from the joint category, which is a real
    limitation of this dataset that the fairness dashboard documents.
    """
    return (
        "male" if personal_status_sex_decoded.startswith("male") else "female"
    )


def main():
    os.makedirs(DATA_RAW_DIR, exist_ok=True)
    local_raw_path = os.path.join(DATA_RAW_DIR, "german.data")

    print(f"Downloading dataset from {SOURCE_URL} ...")
    urllib.request.urlretrieve(SOURCE_URL, local_raw_path)

    df = pd.read_csv(local_raw_path, sep=r"\s+", header=None, names=COLUMNS)

    for col, mapping in DECODE_MAPS.items():
        df[col] = df[col].map(mapping)

    # UCI encodes 1=good credit, 2=bad credit. Convert to
    # 1=good/approve-eligible, 0=bad.
    df["credit_risk"] = (df["credit_risk_raw"] == 1).astype(int)
    df = df.drop(columns=["credit_risk_raw"])

    df["sex"] = df["personal_status_sex"].apply(derive_sex)

    df.to_csv(RAW_DATA_FILE, index=False)
    print(f"Wrote {len(df)} rows, {df.shape[1]} columns to {RAW_DATA_FILE}")
    print(f"Class distribution:\n{df['credit_risk'].value_counts(
                normalize=True)}")


if __name__ == "__main__":
    main()
