from flask import Blueprint, g, jsonify

from app.extensions import db
from app.middleware.auth_middleware import roles_required
from app.models import Notification

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.get("/notifications")
@roles_required("applicant", "admin")
def list_notifications():
    notifications = (
        Notification.query.filter_by(user_id=g.current_user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .all()
    )
    return (
        jsonify({"notifications": [item.to_dict() for item in notifications]}),
        200,
    )


@notifications_bp.patch("/notifications/<int:notification_id>/read")
@roles_required("applicant", "admin")
def mark_notification_read(notification_id: int):
    notification = Notification.query.filter_by(
        id=notification_id, user_id=g.current_user.id
    ).first()
    if notification is None:
        return jsonify({"error": "Notification not found."}), 404
    notification.is_read = True
    db.session.commit()
    return jsonify({"notification": notification.to_dict()}), 200
