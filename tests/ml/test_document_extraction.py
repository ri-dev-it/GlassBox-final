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


def test_photo_preprocessing_deskews_and_upscales_low_resolution_text():
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    from ml.documents.extraction import _estimate_skew, _preprocess_image

    image = Image.new("L", (540, 330), 205)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=20)
    for index, line in enumerate((
        "Government of India",
        "Unique Identification Authority",
        "Name: Asha Example",
        "DOB: 15/01/1995",
    )):
        draw.text((18, 16 + index * 54), line, fill=90, font=font)
    photographed = image.rotate(
        6, expand=True, fillcolor=205
    ).filter(ImageFilter.GaussianBlur(0.45))

    assert _estimate_skew(photographed) == pytest.approx(-6, abs=1.5)
    assert _estimate_skew(Image.new("L", (100, 100), 255)) == 0
    assert max(_preprocess_image(photographed).size) >= 1400


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


def test_missing_tesseract_is_explicit(monkeypatch):
    from PIL import Image
    import pytesseract
    from ml.documents.extraction import _ocr
    def missing(*args, **kwargs):
        raise pytesseract.TesseractNotFoundError()
    monkeypatch.setattr(pytesseract, 'image_to_string', missing)
    with pytest.raises(ExtractionError, match='Install Tesseract'):
        _ocr(Image.new('RGB', (10, 10)))


def test_scanned_pdf_uses_bundled_renderer_without_poppler(monkeypatch):
    from io import BytesIO
    from PIL import Image
    from ml.documents import extraction
    buffer = BytesIO()
    with Image.new('RGB', (200, 100), 'white') as image:
        image.save(buffer, format='PDF')
    seen = []
    def ocr(image):
        seen.append(image.size)
        return 'Synthetic OCR text'
    monkeypatch.setenv('PATH', '')
    monkeypatch.setattr(extraction, '_ocr', ocr)
    text, _, _ = extraction.extract(buffer.getvalue(), 'application/pdf')
    assert text == 'Synthetic OCR text'
    assert len(seen) == 1
    assert seen[0][0] > 0 and seen[0][1] > 0


def test_explicit_tesseract_path_is_used(monkeypatch):
    from PIL import Image
    import pytesseract
    from ml.documents.extraction import _ocr
    monkeypatch.setenv('TESSERACT_CMD', '/configured/tesseract')
    monkeypatch.setattr(pytesseract.pytesseract, 'tesseract_cmd', 'tesseract')
    def ocr(image, **kwargs):
        assert pytesseract.pytesseract.tesseract_cmd == '/configured/tesseract'
        return 'Synthetic OCR text'
    monkeypatch.setattr(pytesseract, 'image_to_string', ocr)
    assert _ocr(Image.new('RGB', (10, 10))) == 'Synthetic OCR text'


def test_dob_normalization_and_mismatch():
    from ml.documents.checks import identity_checks
    assert identity_checks({'name': 'Asha Example', 'dob': '15/01/1995'}, {'name': 'Asha Example', 'dob': '1995-01-15'})[-1]['status'] == 'PASS'
    assert identity_checks({'name': 'Asha Example', 'dob': '1994-01-15'}, {'name': 'Asha Example', 'dob': '1995-01-15'})[-1]['status'] == 'FAIL'
