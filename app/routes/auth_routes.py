"""
app/routes/auth_routes.py

Authentication routes for the Library Management System.

Endpoints (all under /api/auth):
  POST /register  — Create a new user account.
  POST /login     — Verify credentials and return the user record.

Passwords are hashed with Werkzeug's PBKDF2-SHA256 before storage.
Authentication state is intentionally stateless for this iteration —
no session cookies or JWT tokens are issued. Callers receive the user
object and are expected to supply user_id in subsequent requests.
This keeps the API simple for automated testing.
"""

import re
from werkzeug.security import check_password_hash, generate_password_hash
from flask import Blueprint, request

from ..database import db
from ..models import User, UserRole
from ..utils import error_response, success_response, validate_required_fields

auth_bp = Blueprint("auth", __name__)

# Minimal e-mail format check — not RFC-complete, intentionally lightweight.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Valid role values exposed to callers
_VALID_ROLES = {r.value for r in UserRole}


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------

@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new library user.

    Request JSON:
        {
            "name":     str  (required),
            "email":    str  (required, unique),
            "password": str  (required, min 6 chars),
            "role":     str  (optional — student | community | librarian,
                              defaults to "student")
        }

    Responses:
        201  { "data": <user> }
        400  { "error": "<reason>" }   — missing / invalid fields
        409  { "error": "..." }        — e-mail already registered
    """
    body = request.get_json(silent=True) or {}

    # --- required-field presence check ---
    missing = validate_required_fields(body, ["name", "email", "password"])
    if missing:
        return error_response(f"Missing required fields: {', '.join(missing)}")

    name = body["name"].strip()
    email = body["email"].strip().lower()
    password = body["password"]
    role_value = (body.get("role") or "student").strip().lower()

    # --- field-level validation ---
    if not name:
        return error_response("'name' cannot be blank.")

    if not _EMAIL_RE.match(email):
        return error_response("'email' is not a valid e-mail address.")

    if len(password) < 6:
        return error_response("'password' must be at least 6 characters.")

    if role_value not in _VALID_ROLES:
        return error_response(
            f"'role' must be one of: {', '.join(sorted(_VALID_ROLES))}."
        )

    # --- persist ---
    user = User(
        name=name,
        email=email,
        password=generate_password_hash(password),
        role=UserRole(role_value),
    )
    db.session.add(user)
    db.session.commit()

    return success_response(user.to_dict(), 201)


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate a user with e-mail and password.

    Request JSON:
        { "email": str, "password": str }

    Responses:
        200  { "data": { "user": <user>, "message": "Login successful." } }
        400  { "error": "..." }   — missing fields
        401  { "error": "..." }   — invalid credentials
    """
    body = request.get_json(silent=True) or {}

    missing = validate_required_fields(body, ["email", "password"])
    if missing:
        return error_response(f"Missing required fields: {', '.join(missing)}")

    email = body["email"].strip().lower()
    password = body["password"]

    user = User.query.filter_by(email=email).first()

    # Deliberately vague message — do not reveal whether the e-mail exists.
    if not user or not check_password_hash(user.password, password):
        return error_response("Invalid e-mail or password.", 401)

    return success_response({"user": user.to_dict(), "message": "Login successful."})
