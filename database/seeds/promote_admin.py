"""Promote an existing local test account to admin.

Usage from the repository root:
    python database/seeds/promote_admin.py test@example.com
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from app import create_app
from app.extensions import db
from app.models import User


def main():
    if len(sys.argv) != 2:
        print("Usage: python promote_admin.py <email>")
        sys.exit(1)

    email = sys.argv[1].strip().lower()
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"User {email} was not found.")
            sys.exit(1)
        user.role = "admin"
        db.session.commit()
        print(f"Promoted {email} to admin.")


if __name__ == "__main__":
    main()