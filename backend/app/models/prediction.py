import datetime

from app.extensions import db


class Prediction(db.Model):
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer,
        db.ForeignKey("applications.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    # APPROVE | REVIEW | DECLINE; legacy values remain readable
    decision = db.Column(db.String(20), nullable=False)
    # model probability of approval
    probability = db.Column(db.Float, nullable=False)
    model_name = db.Column(db.String(50), nullable=False)  # e.g. "xgboost"
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    explanations = db.relationship(
        "Explanation", backref="prediction", cascade="all, delete-orphan"
    )
    counterfactuals = db.relationship(
        "Counterfactual", backref="prediction", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        risk_probability = 1 - self.probability
        risk_level = {
            "APPROVE": "LOW",
            "REVIEW": "MEDIUM",
            "DECLINE": "HIGH",
        }.get(
            self.decision,
            (
                "LOW"
                if risk_probability < 0.30
                else "MEDIUM" if risk_probability < 0.60 else "HIGH"
            ),
        )
        return {
            "id": self.id,
            "application_id": self.application_id,
            "decision": self.decision,
            "probability": self.probability,
            "risk_score": round(risk_probability * 100),
            "risk_level": risk_level,
            "model_name": self.model_name,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }
