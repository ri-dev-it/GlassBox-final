import datetime
import json

from app.extensions import db


class Counterfactual(db.Model):
    __tablename__ = "counterfactuals"

    id = db.Column(db.Integer, primary_key=True)
    prediction_id = db.Column(
        db.Integer, db.ForeignKey("predictions.id"), nullable=False, index=True
    )
    found = db.Column(db.Boolean, nullable=False, default=False)
    message = db.Column(db.Text, nullable=True)
    alternatives_json = db.Column(db.Text, nullable=False, default="[]")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def set_alternatives(self, alternatives: list) -> None:
        # DiCE returns NumPy scalar values (for example ``np.int64``) for
        # counterfactual feature changes.  Convert those values at the
        # persistence boundary so rejected applications can be stored and
        # returned through Flask's JSON response just like approved ones.
        self.alternatives_json = json.dumps(
            alternatives,
            default=lambda value: (
                value.item() if hasattr(value, "item") else str(value)
            ),
        )

    def get_alternatives(self) -> list:
        return json.loads(self.alternatives_json)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "prediction_id": self.prediction_id,
            "found": self.found,
            "message": self.message,
            "alternatives": self.get_alternatives(),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }
