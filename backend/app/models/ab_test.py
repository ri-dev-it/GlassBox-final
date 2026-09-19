import datetime

from app.extensions import db


class ABTest(db.Model):
    __tablename__ = "ab_tests"

    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(50), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    control_version_id = db.Column(db.Integer, db.ForeignKey("model_versions.id"), nullable=False)
    treatment_version_id = db.Column(db.Integer, db.ForeignKey("model_versions.id"), nullable=False)
    traffic_percentage = db.Column(db.Float, nullable=False, default=50.0)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)

    control_version = db.relationship("ModelVersion", foreign_keys=[control_version_id])
    treatment_version = db.relationship("ModelVersion", foreign_keys=[treatment_version_id])
    results = db.relationship("ABTestResult", backref="ab_test", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "model_name": self.model_name,
            "name": self.name,
            "control_version_id": self.control_version_id,
            "treatment_version_id": self.treatment_version_id,
            "traffic_percentage": self.traffic_percentage,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }


class ABTestResult(db.Model):
    __tablename__ = "ab_test_results"

    id = db.Column(db.Integer, primary_key=True)
    ab_test_id = db.Column(db.Integer, db.ForeignKey("ab_tests.id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey("predictions.id", ondelete="SET NULL"), nullable=True, index=True)
    variant = db.Column(db.String(20), nullable=False)
    model_version_id = db.Column(db.Integer, db.ForeignKey("model_versions.id"), nullable=False)
    decision = db.Column(db.String(20), nullable=False)
    probability = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    model_version = db.relationship("ModelVersion")
    prediction = db.relationship("Prediction")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ab_test_id": self.ab_test_id,
            "prediction_id": self.prediction_id,
            "variant": self.variant,
            "model_version_id": self.model_version_id,
            "decision": self.decision,
            "probability": self.probability,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }