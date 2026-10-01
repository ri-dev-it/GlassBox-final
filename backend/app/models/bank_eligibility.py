import datetime
import json

from app.extensions import db


class BankEligibilityResult(db.Model):
    __tablename__ = "bank_eligibility_results"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer,
        db.ForeignKey("applications.id"),
        nullable=False,
        index=True,
    )
    bank_name = db.Column(db.String(100), nullable=False)
    decision = db.Column(db.String(20), nullable=False)
    probability = db.Column(db.Float, nullable=False)
    reasons_json = db.Column(db.Text, nullable=False, default="[]")
    conditions_json = db.Column(db.Text, nullable=False, default="[]")
    risk_indicators_json = db.Column(db.Text, nullable=False, default="[]")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def set_lists(self, reasons: list, conditions: list, risks: list) -> None:
        self.reasons_json, self.conditions_json, self.risk_indicators_json = (
            json.dumps(reasons),
            json.dumps(conditions),
            json.dumps(risks),
        )

    def to_dict(self) -> dict:
        return {
            "bankName": self.bank_name,
            "decision": self.decision,
            "probability": self.probability,
            "reasons": json.loads(self.reasons_json),
            "conditions": json.loads(self.conditions_json),
            "riskIndicators": json.loads(self.risk_indicators_json),
        }
