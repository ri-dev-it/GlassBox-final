import datetime
import json

from app.extensions import db


class Document(db.Model):
    """Private uploaded document. The file is never served by a public route."""
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=True, index=True)
    document_type = db.Column(db.String(40), nullable=False)
    storage_reference = db.Column(db.String(512), nullable=False, unique=True)
    original_filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="UPLOADED")
    document_status = db.Column(db.String(20), nullable=False, default="pending")
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    verification = db.relationship("DocumentVerification", backref="document", uselist=False, cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        verification = self.verification.to_dict() if self.verification else None
        return {
            "id": self.id, "documentType": self.document_type, "status": self.status,
            "filename": self.original_filename, "uploadedAt": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "verification": verification,
            "documentStatus": self.document_status,
            "reviewedBy": self.reviewed_by,
            "reviewedAt": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }


class DocumentVerification(db.Model):
    __tablename__ = "document_verifications"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False, unique=True, index=True)
    status = db.Column(db.String(20), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    extracted_information_json = db.Column(db.Text, nullable=False, default="{}")
    mismatches_json = db.Column(db.Text, nullable=False, default="[]")
    verification_message = db.Column(db.String(1000), nullable=False)
    verified_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def set_extracted_information(self, value: dict) -> None:
        self.extracted_information_json = json.dumps(value)

    def set_mismatches(self, value: list) -> None:
        self.mismatches_json = json.dumps(value)

    def to_dict(self) -> dict:
        return {"documentType": self.document.document_type, "status": self.status,
                "confidence": self.confidence, "extractedInformation": json.loads(self.extracted_information_json),
                "mismatches": json.loads(self.mismatches_json), "verificationMessage": self.verification_message,
                "verifiedAt": self.verified_at.isoformat() if self.verified_at else None}
