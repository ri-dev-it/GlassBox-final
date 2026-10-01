"""Transparent rules combined with a small synthetic-text classifier."""

import json
import re
from functools import lru_cache
from pathlib import Path

RULES = {
    "aadhaar": [
        r"government[\s.,:/-]+of[\s.,:/-]+india",
        r"unique[\s.,:/-]+identification[\s.,:/-]+authority|uidai",
        r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b",
        r"\bdob\b|\byob\b|date of birth|year of birth",
        r"\bmale\b|\bfemale\b",
    ],
    "salary_slip": [
        r"salary slip|pay\s?slip",
        r"\bbasic\b",
        r"\bhra\b",
        r"\bgross\b",
        r"deductions",
        r"net pay",
        r"employer",
        r"pay period",
    ],
    "bank_statement": [
        r"bank statement",
        r"\bifsc\b",
        r"account (number|no)",
        r"debit",
        r"credit",
        r"balance",
        r"\d{4}-\d{2}-\d{2}",
    ],
    "pan": [
        r"permanent account number|\bpan\s+card\b",
        r"\b[A-Z]{5}\d{4}[A-Z]\b",
        r"income tax department",
        r"government of india",
    ],
}


@lru_cache(maxsize=1)
def text_model():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline

    rows = json.loads(
        Path(__file__).with_name("synthetic_texts.json").read_text()
    )
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2)),
        LogisticRegression(C=8, random_state=42),
    )
    model.fit(
        [r["text"] for r in rows if r["split"] == "train"],
        [r["type"] for r in rows if r["split"] == "train"],
    )
    return model


def classify(text):
    evidence = {
        kind: [
            pattern for pattern in patterns if re.search(pattern, text, re.I)
        ]
        for kind, patterns in RULES.items()
    }
    model = text_model()
    probabilities = dict(zip(model.classes_, model.predict_proba([text])[0]))
    scores = {
        kind: (
            0.75 * len(evidence[kind]) / len(RULES[kind])
            + 0.25 * probabilities[kind]
        )
        for kind in RULES
    }
    kind = max(scores, key=scores.get)
    return {
        "type": kind,
        "confidence": round(float(scores[kind]), 4),
        "evidence": evidence[kind],
        "scores": {k: round(float(v), 4) for k, v in scores.items()},
    }
