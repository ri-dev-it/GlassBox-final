import datetime
import json

from app.extensions import db


class GroundedExplanation(db.Model):
    __tablename__ = "grounded_explanations"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer,
        db.ForeignKey("applications.id"),
        nullable=True,
        unique=True,
        index=True,
    )
    merchant_id = db.Column(
        db.String(100), nullable=True, unique=True, index=True
    )
    text = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(20), nullable=False)
    grounded_in_json = db.Column(db.Text, nullable=False, default="[]")
    generated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def set_grounded_in(self, features: list[str]) -> None:
        self.grounded_in_json = json.dumps(features)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "application_id": self.application_id,
            "merchant_id": self.merchant_id,
            "text": self.text,
            "source": self.source,
            "grounded_in": json.loads(self.grounded_in_json),
            "generated_at": (
                self.generated_at.isoformat() if self.generated_at else None
            ),
        }
