import json
from pathlib import Path
import pytest
from ml.documents.identity import verhoeff, mask_identifiers
from ml.documents.classifier import classify, text_model
from ml.documents.extraction import detect_type, ExtractionError


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
