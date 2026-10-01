"""Augment UCI rows with independent synthetic bank histories for plumbing
demos.

These are NOT real linked applicant transactions and not evidence of predictive
utility. Do not derive histories from the target label (that would leak it).
"""

import sys
from pathlib import Path
import random
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Local imports require the repository path configured above.
from ml.documents.bank import bank_features  # noqa: E402


def augment(frame, seed=42):
    rng = random.Random(seed)
    features = []
    for _ in range(len(frame)):
        salary, balance = rng.randint(15000, 150000), rng.randint(-5000, 50000)
        rows = []
        for month in range(1, 7):
            credit = round(salary * rng.uniform(0.8, 1.2), 2)
            balance += credit
            rows.append(
                {
                    "date": f"2025-{month:02d}-01",
                    "description": "Salary DEMO",
                    "debit": 0,
                    "credit": credit,
                    "balance": balance,
                }
            )
            for day, label in [(5, "EMI"), (10, "ATM"), (25, "Groceries")]:
                debit = round(salary * rng.uniform(0.05, 0.45), 2)
                balance -= debit
                rows.append(
                    {
                        "date": f"2025-{month:02d}-{day:02d}",
                        "description": label,
                        "debit": debit,
                        "credit": 0,
                        "balance": balance,
                    }
                )
        features.append(bank_features(rows))
    return pd.concat(
        [frame.reset_index(drop=True), pd.DataFrame(features)], axis=1
    )


if __name__ == "__main__":
    source = ROOT / "ml/data/raw/german_credit.csv"
    target = ROOT / "ml/data/processed/synthetic_individual_bank.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    augment(pd.read_csv(source)).to_csv(target, index=False)
    print(
        f"Wrote synthetic bank augmentation to {target}; no real transaction"
        " linkage."
    )
