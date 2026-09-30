"""Bounded extraction. Raw text stays in memory and is never persisted."""
from io import BytesIO


class ExtractionError(ValueError):
    pass


def detect_type(data):
    import filetype
    kind = filetype.guess(data)
    if kind is None or kind.mime not in {"application/pdf", "image/png", "image/jpeg"}:
        raise ExtractionError("Only PDF, JPG, and PNG files with valid content are supported.")
    return kind.mime, kind.extension


def _ocr(image):
    import pytesseract
    if image.width * image.height > 20_000_000:
        raise ExtractionError("OCR image exceeds the 20 megapixel limit.")
    try:
        return pytesseract.image_to_string(image, timeout=30)
    except pytesseract.TesseractNotFoundError:
        raise ExtractionError("OCR requires Tesseract. Install Tesseract and add it to PATH.") from None
    except RuntimeError:
        raise ExtractionError("OCR timed out; upload a smaller, clearer document.") from None


def extract(data, mime):
    try:
        if mime == "application/pdf":
            import pdfplumber
            with pdfplumber.open(BytesIO(data)) as pdf:
                if len(pdf.pages) > 20:
                    raise ExtractionError("PDF exceeds the 20-page limit.")
                metadata = {k: str(v) for k, v in (pdf.metadata or {}).items()
                            if k in {"Producer", "Creator", "CreationDate", "ModDate"}}
                texts, tables = [], []
                for index, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    if len(text.strip()) < 25:
                        from pdf2image import convert_from_bytes
                        from pdf2image.exceptions import PDFInfoNotInstalledError
                        try:
                            images = convert_from_bytes(data, dpi=120, first_page=index + 1,
                                                        last_page=index + 1, timeout=30)
                        except PDFInfoNotInstalledError:
                            raise ExtractionError("Scanned PDFs require Poppler and Tesseract on PATH.") from None
                        text = _ocr(images[0])
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
        raise ExtractionError("Document cannot be read. Use an unencrypted, valid PDF or clear image.") from None
