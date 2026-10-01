"""Bounded extraction. Raw text stays in memory and is never persisted."""

from io import BytesIO
import math
import os


class ExtractionError(ValueError):
    pass


def detect_type(data):
    import filetype

    kind = filetype.guess(data)
    if kind is None or kind.mime not in {
        "application/pdf",
        "image/png",
        "image/jpeg",
    }:
        raise ExtractionError(
            "Only PDF, JPG, and PNG files with valid content are supported."
        )
    return kind.mime, kind.extension


def _estimate_skew(image):
    """Estimate small text-line rotation using a row projection profile."""
    import numpy as np
    from PIL import Image

    sample = image.copy()
    sample.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
    source = np.asarray(sample, dtype=np.uint8)
    if np.count_nonzero(source < 170) < 100:
        return 0.0

    def score(angle):
        rotated = sample.rotate(
            angle,
            resample=Image.Resampling.BILINEAR,
            expand=False,
            fillcolor=255,
        )
        rows = (np.asarray(rotated, dtype=np.uint8) < 170).sum(axis=1)
        return float(rows.var())

    zero_score = score(0)
    candidates = [step / 2 for step in range(-10, 11)]
    best = max(candidates, key=score)
    best_score = score(best)
    if best == 0 or best_score < zero_score * 1.015:
        return 0.0

    refine = [best + step / 10 for step in range(-5, 6)]
    best = max(refine, key=score)
    return best if abs(best) >= 0.3 else 0.0


def _preprocess_image(image):
    """Normalize photographed or scanned pages before Tesseract."""
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps

    normalized = ImageOps.exif_transpose(image).convert("L")
    normalized = ImageOps.autocontrast(normalized, cutoff=1)
    normalized = ImageEnhance.Contrast(normalized).enhance(1.35)
    angle = _estimate_skew(normalized)
    if angle:
        normalized = normalized.rotate(
            angle,
            resample=Image.Resampling.BICUBIC,
            expand=True,
            fillcolor=255,
        )

    width, height = normalized.size
    scale = min(
        2.5,
        1800 / max(width, height),
        math.sqrt(20_000_000 / (width * height)),
    )
    if scale > 1.05:
        normalized = normalized.resize(
            (round(width * scale), round(height * scale)),
            Image.Resampling.LANCZOS,
        )
    return normalized.filter(
        ImageFilter.UnsharpMask(radius=1.2, percent=140, threshold=3)
    )


def _ocr(image):
    import pytesseract

    # Support installed OCR tools without requiring a machine-wide PATH edit.
    pytesseract.pytesseract.tesseract_cmd = os.environ.get(
        "TESSERACT_CMD", ""
    ) or "tesseract"
    if image.width * image.height > 20_000_000:
        raise ExtractionError("OCR image exceeds the 20 megapixel limit.")
    try:
        prepared = _preprocess_image(image)
        if prepared.width * prepared.height > 20_000_000:
            raise ExtractionError("OCR image exceeds the 20 megapixel limit.")
        return pytesseract.image_to_string(
            prepared, config="--oem 3 --psm 6", timeout=30
        )
    except pytesseract.TesseractNotFoundError:
        raise ExtractionError(
            "OCR requires Tesseract. Install Tesseract and add it to PATH."
        ) from None
    except RuntimeError:
        raise ExtractionError(
            "OCR timed out; upload a smaller, clearer document."
        ) from None


def _scanned_pdf_page(data, index):
    """Render with bundled PDFium; no separate Poppler installation needed."""
    import pypdfium2

    with pypdfium2.PdfDocument(data) as document:
        page = document[index]
        try:
            width, height = page.get_size()
            scale = min(
                300 / 72,
                math.sqrt(20_000_000 / (width * height)),
            )
            bitmap = page.render(scale=scale)
            try:
                return bitmap.to_pil().copy()
            finally:
                bitmap.close()
        finally:
            page.close()


def extract(data, mime):
    try:
        if mime == "application/pdf":
            import pdfplumber

            with pdfplumber.open(BytesIO(data)) as pdf:
                if len(pdf.pages) > 20:
                    raise ExtractionError("PDF exceeds the 20-page limit.")
                metadata = {
                    k: str(v)
                    for k, v in (pdf.metadata or {}).items()
                    if k in {"Producer", "Creator", "CreationDate", "ModDate"}
                }
                texts, tables = [], []
                for index, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    if len(text.strip()) < 25:
                        with _scanned_pdf_page(data, index) as image:
                            text = _ocr(image)
                    texts.append(text)
                    tables.extend(page.extract_tables() or [])
                return "\n".join(texts), metadata, tables
        from PIL import Image

        with Image.open(BytesIO(data)) as img:
            if img.width * img.height > 20_000_000:
                raise ExtractionError("Image exceeds the 20 megapixel limit.")
            img.load()
            return _ocr(img), {}, []
    except ExtractionError:
        raise
    except Exception:
        raise ExtractionError(
            "Document cannot be read. Use an unencrypted, valid PDF or clear"
            " image."
        ) from None
