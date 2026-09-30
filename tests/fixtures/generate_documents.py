"""Fictional fixtures only. Generated identifiers are not issued identities."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ml.documents.identity import verhoeff

ROOT = Path(__file__).parent / "documents"


def sample_texts():
    number = next("99998888777" + str(i) for i in range(10) if verhoeff("99998888777" + str(i)))
    return {
        "aadhaar": f"SYNTHETIC DEMO - NOT VALID ID\nGovernment of India\nUnique Identification Authority\nName: Asha Example\nDOB: 1995-01-15\nFemale\n{number}",
        "salary_slip": "SYNTHETIC DEMO\nSalary Slip\nEmployee name: Asha Example\nEmployer: Example Labs\nPay period: 2026-01\nBasic: 40000\nHRA: 10000\nGross: 50000\nDeductions: 5000\nNet Pay: 45000",
        "bank_statement": "SYNTHETIC DEMO\nBank Statement\nAccount holder: Asha Example\nIFSC: DEMO0000001\nAccount number: 12345678\nDate Description Debit Credit Balance\n2026-01-01 Opening 0 0 10000\n2026-01-05 Salary_Example_Labs 0 45000 55000\n2026-01-10 EMI 5000 0 50000\n2026-02-05 Salary_Example_Labs 0 45000 95000\n2026-02-10 ATM 10000 0 85000",
        "income_certificate": "SYNTHETIC DEMO\nIncome Certificate\nHolder name: Asha Example\nIssuing authority: Demo Tehsildar\nAnnual income: 600000\nCertificate number: DEMO-001",
    }


def generate():
    from reportlab.pdfgen import canvas
    from PIL import Image, ImageDraw
    ROOT.mkdir(parents=True, exist_ok=True)
    texts = sample_texts()
    texts["mismatched_salary"] = texts["salary_slip"].replace("Asha Example", "Rohan Different")
    texts["edited_salary"] = texts["salary_slip"].replace("45000", "49000")
    texts["wrong_slot"] = texts["salary_slip"]
    for name, text in texts.items():
        pdf = canvas.Canvas(str(ROOT / f"{name}.pdf"), invariant=1)
        for index, line in enumerate(text.splitlines()):
            pdf.drawString(40, 800 - index * 22, line)
        pdf.save()
    img = Image.new("RGB", (1200, 700), "white")
    ImageDraw.Draw(img).multiline_text((30, 30), texts["aadhaar"], fill="black", spacing=15, font_size=24)
    img.save(ROOT / "aadhaar.png")
    Image.new("RGB", (50, 50), "white").save(ROOT / "address.png")


if __name__ == "__main__":
    generate()
