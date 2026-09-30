import json
from pathlib import Path
import pytest
from ml.documents.identity import verhoeff, mask_identifiers
from ml.documents.classifier import classify, text_model
from ml.documents.extraction import detect_type, ExtractionError
from ml.documents.identity import name_score
from ml.documents.checks import salary_arithmetic, metadata_checks
from ml.documents.bank import balance_check


def test_verhoeff_and_mask():
    assert verhoeff("999988887779")
    assert not verhoeff("999988887778")
    assert not verhoeff("123")
    assert mask_identifiers("9999 8888 7778") == "********7778"


def test_synthetic_classifier_accuracy():
    path = Path(__file__).parents[2] / "ml/documents/synthetic_texts.json"
    rows = [r for r in json.loads(path.read_text()) if r["split"] == "test"]
    predictions = text_model().predict([r["text"] for r in rows])
    accuracy = sum(p == r["type"] for p, r in zip(predictions, rows)) / len(rows)
    print(f"Synthetic template holdout accuracy: {accuracy:.3f} ({len(rows)} samples)")
    assert accuracy >= 0.9
    for row in rows:
        assert classify(row["text"])["type"] == row["type"]


def test_content_validation():
    with pytest.raises(ExtractionError):
        detect_type(b"fake PDF")


@pytest.mark.parametrize("left,right,match", [
    ("Asha Example", "Asha Example", True), ("Dr A. Example", "Asha Example", True),
    ("Example Asha", "asha example", True), ("Rohan Different", "Asha Example", False),
    ("Asha Wrong", "Asha Example", False), ("A E", "Asha Example", False)])
def test_names(left, right, match):
    assert (name_score(left, right) >= 88) == match


def test_arithmetic_and_metadata():
    assert salary_arithmetic({"gross": 50000, "deductions": 5000, "net_pay": 45000})["status"] == "PASS"
    assert salary_arithmetic({"gross": 50000, "deductions": 5000, "net_pay": 49000})["status"] == "FAIL"
    assert salary_arithmetic({})["status"] == "WARN"
    rows = [{"balance": 100}, {"debit": 20, "credit": 0, "balance": 80}]
    assert balance_check(rows)["status"] == "PASS"
    rows[1]["balance"] = 90
    assert balance_check(rows)["status"] == "FAIL"
    assert metadata_checks({"Producer": "Canva"})["status"] == "WARN"
    assert metadata_checks({"CreationDate": "D:20260101000000", "ModDate": "D:20260102000000"})["status"] == "WARN"
