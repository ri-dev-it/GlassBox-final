"""Refresh the document pipeline appendix in the fresh MySQL schema."""
from pathlib import Path
import sys
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable, CreateIndex

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.extensions import db
from app.models import DocumentAudit, VerificationReport, DocumentTransaction, DocumentFingerprint


def main():
    dialect = mysql.dialect()
    blocks = []
    for model in (DocumentAudit, VerificationReport, DocumentTransaction, DocumentFingerprint):
        table = model.__table__
        blocks.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";")
        blocks.extend(str(CreateIndex(index).compile(dialect=dialect)) + ";" for index in sorted(table.indexes, key=lambda i: i.name))
    marker = "-- Document upload verification pipeline (generated appendix)"
    path = ROOT / "database/schema.sql"
    text = path.read_text(encoding="utf-8").split(marker)[0].rstrip()
    output = text + "\n\n" + marker + "\n\n" + "\n\n".join(blocks)
    path.write_text("\n".join(line.rstrip() for line in output.splitlines()) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
