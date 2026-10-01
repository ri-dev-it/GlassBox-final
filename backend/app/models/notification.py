import datetime

from app.extensions import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    application_id = db.Column(
        db.Integer,
        db.ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    message = db.Column(db.String(1000), nullable=False)
    type = db.Column(db.String(40), nullable=False, default="status_update")
    decision_type = db.Column(db.String(20), nullable=True)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        index=True,
    )

    application = db.relationship("Application")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "application_id": self.application_id,
            "message": self.message,
            "type": self.type,
            "decision_type": self.decision_type,
            "is_read": self.is_read,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }
