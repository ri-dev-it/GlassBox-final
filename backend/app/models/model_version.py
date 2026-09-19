import datetime
import json

from app.extensions import db


class ModelVersion(db.Model):
    __tablename__ = "model_versions"

    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(50), nullable=False, index=True)
    version_number = db.Column(db.Integer, nullable=False)
    trained_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    file_path = db.Column(db.String(512), nullable=False)
    metrics_json = db.Column(db.Text, nullable=False, default="{}")
    governance_passed = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=False, index=True)

    __table_args__ = (
        db.UniqueConstraint("model_name", "version_number", name="uq_model_versions_name_number"),
    )

    def set_metrics(self, metrics: dict) -> None:
        self.metrics_json = json.dumps(metrics)

    def get_metrics(self) -> dict:
        return json.loads(self.metrics_json or "{}")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "model_name": self.model_name,
            "version_number": self.version_number,
            "trained_at": self.trained_at.isoformat() if self.trained_at else None,
            "file_path": self.file_path,
            "metrics": self.get_metrics(),
            "governance_passed": self.governance_passed,
            "is_active": self.is_active,
        }