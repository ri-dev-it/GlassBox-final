import datetime
import json

from app.extensions import db


class GovernanceCheck(db.Model):
    """Historical fairness governance decision for a model version."""

    __tablename__ = "governance_checks"

    id = db.Column(db.Integer, primary_key=True)
    model_key = db.Column(db.String(100), nullable=False, index=True)
    model_version = db.Column(db.String(100), nullable=False)
    passed = db.Column(db.Boolean, nullable=False)
    failed_checks_json = db.Column(db.Text, nullable=False, default="[]")
    checked_at = db.Column(
        db.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    def set_failed_checks(self, checks: list[str]) -> None:
        self.failed_checks_json = json.dumps(checks)

    def to_dict(self) -> dict:
        return {
            "model_key": self.model_key,
            "model_version": self.model_version,
            "passed": self.passed,
            "failed_checks": json.loads(self.failed_checks_json),
            "checked_at": (
                self.checked_at.isoformat() if self.checked_at else None
            ),
        }
