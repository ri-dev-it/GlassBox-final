import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
STAFF_ROLES = {"loan_officer", "admin"}
PUBLIC_ROLES = {"client", "admin"}


def validate_register_payload(data: dict) -> list[str]:
    """
    Public self-registration exposes the two account types offered by the UI:
    applicant (persisted as ``client``) and admin/checker (``admin``).
    """
    errors = []
    email = data.get("email", "")
    password = data.get("password", "")
    full_name = data.get("full_name", "")
    role = data.get("role", "client")

    if not email or not EMAIL_RE.match(email):
        errors.append("A valid email is required.")
    if not password or len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if not full_name or not full_name.strip():
        errors.append("Full name is required.")
    if role not in PUBLIC_ROLES:
        errors.append(f"Role must be one of {sorted(PUBLIC_ROLES)}.")

    return errors


def validate_login_payload(data: dict) -> list[str]:
    errors = []
    if not data.get("email"):
        errors.append("Email is required.")
    if not data.get("password"):
        errors.append("Password is required.")
    return errors


def validate_create_staff_payload(data: dict) -> list[str]:
    errors = validate_register_payload(data)
    role = data.get("role")
    if role not in STAFF_ROLES:
        errors.append(f"Role must be one of {sorted(STAFF_ROLES)}.")
    return errors
