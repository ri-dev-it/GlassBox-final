import datetime
import secrets

import jwt
from flask import current_app
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import User


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def register_user(
    email: str, password: str, full_name: str, role: str = "applicant"
) -> User:
    if User.query.filter_by(email=email).first():
        raise AuthError("Email already registered.", 409)

    user = User(email=email, full_name=full_name, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def authenticate_user(email: str, password: str) -> User:
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        raise AuthError("Invalid email or password.", 401)
    return user


def authenticate_google_user(
    email: str, full_name: str, google_sub: str
) -> User:
    """Find or create an account for a verified Google subject.

    Email-only matching is deliberately insufficient: silently attaching Google
    to an existing password account would bypass the project's account-linking
    policy. Google-only accounts are matched by Google's stable subject ID.
    """
    user = User.query.filter_by(google_sub=google_sub).first()
    if user:
        if user.email != email:
            raise AuthError(
                "The Google account email changed. Contact support to update"
                " your account.",
                409,
            )
        return user

    if User.query.filter_by(email=email).first():
        raise AuthError(
            "An account already exists with this email. Please use the"
            " existing login method.",
            409,
        )

    user = User(
        email=email,
        full_name=full_name or email.split("@", 1)[0],
        google_sub=google_sub,
    )
    # OAuth-only users never use this password. A random password hash
    # maintains
    # the existing non-null password schema without allowing a known password.
    user.set_password(secrets.token_urlsafe(48))
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        # Two callbacks can race after both observe no account. Resolve the
        # winner by stable Google subject, while preserving email uniqueness.
        db.session.rollback()
        user = User.query.filter_by(google_sub=google_sub).first()
        if user and user.email == email:
            return user
        if User.query.filter_by(email=email).first():
            raise AuthError(
                "An account already exists with this email. Please use the"
                " existing login method.",
                409,
            )
        raise AuthError(
            "Unable to create the Google account. Please try again.", 409
        )
    return user


def issue_token(user: User) -> str:
    payload = {
        "user_id": user.id,
        "role": user.role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(
        payload, current_app.config["SECRET_KEY"], algorithm="HS256"
    )
