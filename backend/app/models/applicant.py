import datetime

from app.extensions import db


class Applicant(db.Model):
    """An applicant profile a user submits loan applications under."""

    __tablename__ = "applicants"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    full_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    applications = db.relationship(
        "Application", backref="applicant", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }
