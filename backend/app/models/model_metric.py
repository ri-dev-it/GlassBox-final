import datetime

from app.extensions import db


class ModelMetric(db.Model):
    """Held-out classification metric snapshot for a trained model artifact."""

    __tablename__ = "model_metrics"

    id = db.Column(db.Integer, primary_key=True)
    model_key = db.Column(db.String(100), nullable=False, index=True)
    model_version = db.Column(db.String(100), nullable=False)
    precision = db.Column(db.Float, nullable=False)
    recall = db.Column(db.Float, nullable=False)
    f1 = db.Column(db.Float, nullable=False)
    roc_auc = db.Column(db.Float, nullable=False)
    dataset_size = db.Column(db.Integer, nullable=True)
    test_size = db.Column(db.Integer, nullable=True)
    evaluated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    def to_dict(self) -> dict:
        return {
            "model_key": self.model_key,
            "model_version": self.model_version,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "roc_auc": self.roc_auc,
            "dataset_size": self.dataset_size,
            "test_size": self.test_size,
            "evaluated_at": (
                self.evaluated_at.isoformat() if self.evaluated_at else None
            ),
        }
