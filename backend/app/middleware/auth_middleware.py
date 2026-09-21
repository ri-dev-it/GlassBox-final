"""
JWT authentication and role-based access control.

Admin-only / role-gated endpoints MUST use these decorators on the
backend -- hiding a nav link on the frontend is not access control
(spec section 30).
"""

from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

from app.models import User


def _get_token_from_header() -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]
    return None


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _get_token_from_header()
        if not token:
            return jsonify({"error": "Missing authentication token"}), 401
        try:
            payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        user = User.query.get(payload.get("user_id"))
        if not user:
            return jsonify({"error": "User not found"}), 401

        g.current_user = user
        return f(*args, **kwargs)

    return decorated


def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(*args, **kwargs):
            effective_role = "applicant" if g.current_user.role == "client" else g.current_user.role
            if effective_role not in allowed_roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)

        return decorated

    return decorator
