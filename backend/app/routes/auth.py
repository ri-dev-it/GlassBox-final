import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import (
    Blueprint,
    current_app,
    g,
    jsonify,
    redirect,
    request,
    session,
)

from app.middleware.auth_middleware import roles_required
from app.schemas.auth_schema import (
    validate_register_payload,
    validate_login_payload,
    validate_create_staff_payload,
)
from app.services.auth_service import (
    AuthError,
    register_user,
    authenticate_user,
    authenticate_google_user,
    issue_token,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    errors = validate_register_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400

    try:
        user = register_user(
            email=data["email"].strip().lower(),
            password=data["password"],
            full_name=data["full_name"].strip(),
            role=data.get("role", "client"),
        )
    except AuthError as e:
        return jsonify({"error": e.message}), e.status_code

    token = issue_token(user)
    return jsonify({"token": token, "user": user.to_dict()}), 201


@auth_bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    errors = validate_login_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400

    try:
        user = authenticate_user(
            data["email"].strip().lower(), data["password"]
        )
    except AuthError as e:
        return jsonify({"error": e.message}), e.status_code

    token = issue_token(user)
    return jsonify({"token": token, "user": user.to_dict()}), 200


@auth_bp.get("/auth/google")
def google_login():
    """Start Google OAuth. Credentials are deliberately supplied by env
    vars."""
    requested_page = request.args.get("next", "login")
    return_page = requested_page if requested_page == "register" else "login"
    client_id = current_app.config["GOOGLE_CLIENT_ID"]
    client_secret = current_app.config["GOOGLE_CLIENT_SECRET"]
    if not client_id or not client_secret:
        error_query = urlencode(
            {"error": "Google sign-in is not configured on this server."}
        )
        return redirect(
            f"{current_app.config['FRONTEND_URL']}/{return_page}?{error_query}"
        )

    state = secrets.token_urlsafe(32)
    session["google_oauth_state"] = state
    session["google_oauth_page"] = return_page
    params = {
        "client_id": client_id,
        "redirect_uri": current_app.config["GOOGLE_REDIRECT_URI"],
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return redirect(
        f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    )


@auth_bp.get("/auth/google/callback")
def google_callback():
    frontend_url = current_app.config["FRONTEND_URL"]
    page = session.pop("google_oauth_page", "login")
    login_url = f"{frontend_url}/{page}"
    error = request.args.get("error")
    if error or not secrets.compare_digest(
        request.args.get("state", ""), session.pop("google_oauth_state", "")
    ):
        message = (
            "Google sign-in was cancelled."
            if error == "access_denied"
            else "Unable to authenticate with Google. Please try again."
        )
        return redirect(f"{login_url}?{urlencode({'error': message})}")

    try:
        token_request = Request(
            "https://oauth2.googleapis.com/token",
            data=urlencode(
                {
                    "code": request.args["code"],
                    "client_id": current_app.config["GOOGLE_CLIENT_ID"],
                    "client_secret": current_app.config[
                        "GOOGLE_CLIENT_SECRET"
                    ],
                    "redirect_uri": current_app.config["GOOGLE_REDIRECT_URI"],
                    "grant_type": "authorization_code",
                }
            ).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urlopen(token_request, timeout=10) as response:
            import json

            access_token = json.load(response)["access_token"]
        with urlopen(
            Request(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            ),
            timeout=10,
        ) as response:
            profile = json.load(response)
        if (
            not profile.get("email")
            or profile.get("email_verified") is not True
            or not profile.get("sub")
        ):
            raise AuthError(
                "Google did not provide a verified email address.", 400
            )
        user = authenticate_google_user(
            profile["email"].strip().lower(),
            profile.get("name", ""),
            profile["sub"],
        )
        token = issue_token(user)
        # Keep the app JWT in the fragment so it is not sent in HTTP requests,
        # access logs, or referrer headers. The callback page consumes it once.
        return redirect(f"{frontend_url}/auth/google/callback#token={token}")
    except AuthError as exc:
        return redirect(f"{login_url}?{urlencode({'error': exc.message})}")
    except (KeyError, HTTPError, URLError, TimeoutError, ValueError):
        return redirect(
            f"{login_url}?"
            + urlencode(
                {
                    "error": (
                        "Unable to authenticate with Google. Please try again."
                    )
                }
            )
        )


@auth_bp.post("/auth/logout")
def logout():
    # Stateless JWT -- logout is handled client-side by discarding the token.
    # (A token-blocklist could be added here if server-side revocation is
    # required.)
    return jsonify({"message": "Logged out."}), 200


@auth_bp.get("/auth/me")
@roles_required("applicant", "loan_officer", "admin")
def me():
    return jsonify({"user": g.current_user.to_dict()}), 200


@auth_bp.post("/auth/create-staff")
@roles_required("admin")
def create_staff():
    """Admin-only: create a loan_officer or admin account."""
    data = request.get_json(silent=True) or {}
    errors = validate_create_staff_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400

    try:
        user = register_user(
            email=data["email"].strip().lower(),
            password=data["password"],
            full_name=data["full_name"].strip(),
            role=data["role"],
        )
    except AuthError as e:
        return jsonify({"error": e.message}), e.status_code

    return jsonify({"user": user.to_dict()}), 201
