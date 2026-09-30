"""Append-only extraction/check snapshots; never raw OCR or full identifiers."""
import datetime
import json
from app.extensions import db


class DocumentAudit(db.Model):
    __tablename__ = "document_audits"
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    file_hash = db.Column(db.String(64), nullable=False, index=True)
    aadhaar_hash = db.Column(db.String(64), nullable=True, index=True)
    slot = db.Column(db.String(40), nullable=False)
    fields_json = db.Column(db.Text, nullable=False, default="{}")
    checks_json = db.Column(db.Text, nullable=False, default="[]")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    document = db.relationship("Document", backref="audits")

    @property
    def fields(self):
        return json.loads(self.fields_json)

    @property
    def checks(self):
        return json.loads(self.checks_json)


class VerificationReport(db.Model):
    __tablename__ = "verification_reports"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=True, index=True)
    verdict = db.Column(db.String(20), nullable=False)
    report_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)

    def to_dict(self):
        return json.loads(self.report_json)
