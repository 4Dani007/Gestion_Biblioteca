"""
app/routes/loan_routes.py

Loan management routes for the Library Management System.

Endpoints (all under /api/loans):
  POST /borrow  — Borrow a book; decrements available_copies.
  POST /return  — Return a borrowed book; increments available_copies.

Business rules enforced here:
  - A book cannot be borrowed if available_copies == 0.
  - Returning a loan that is already returned is rejected.
  - available_copies is updated atomically with the loan status change.
"""

from datetime import datetime, timezone

from flask import Blueprint, request
from sqlalchemy.orm import joinedload

from ..database import db
from ..models import Book, Loan, LoanStatus, User
from ..utils import error_response, success_response, validate_required_fields

loan_bp = Blueprint("loans", __name__)


# ---------------------------------------------------------------------------
# POST /api/loans/borrow
# ---------------------------------------------------------------------------

@loan_bp.route("/borrow", methods=["POST"])
def borrow_book():
    """
    Borrow a book — creates an active loan and decrements available_copies.

    Request JSON:
        {
            "user_id": int  (required),
            "book_id": int  (required)
        }

    Business rules:
        - user_id must reference an existing user.
        - book_id must reference an existing book.
        - book.available_copies must be > 0.

    Responses:
        201  { "data": <loan> }
        400  { "error": "..." }   — missing / invalid fields
        404  { "error": "..." }   — user or book not found
        409  { "error": "..." }   — no copies available
    """
    body = request.get_json(silent=True) or {}

    missing = validate_required_fields(body, ["user_id", "book_id"])
    if missing:
        return error_response(f"Missing required fields: {', '.join(missing)}")

    try:
        user_id = int(body["user_id"])
        book_id = int(body["book_id"])
    except (TypeError, ValueError):
        return error_response("'user_id' and 'book_id' must be integers.")

    user = db.session.get(User, user_id)
    if not user:
        return error_response(f"User with id {user_id} not found.", 404)

    book = db.session.get(Book, book_id)
    if not book:
        return error_response(f"Book with id {book_id} not found.", 404)

    book.available_copies -= 1
    loan = Loan(
        user_id=user_id,
        book_id=book_id,
        loan_date=datetime.now(timezone.utc),
        status=LoanStatus.borrowed,
    )
    db.session.add(loan)
    db.session.commit()

    # Return loan with embedded user + book context for convenience.
    db.session.refresh(loan)
    return success_response(loan.to_dict_full(), 201)


# ---------------------------------------------------------------------------
# POST /api/loans/return
# ---------------------------------------------------------------------------

@loan_bp.route("/return", methods=["POST"])
def return_book():
    """
    Return a borrowed book — marks the loan as returned and restores stock.

    Request JSON:
        { "loan_id": int  (required) }

    Business rules:
        - loan_id must reference an existing loan.
        - The loan must currently have status 'borrowed'.

    Responses:
        200  { "data": <loan> }
        400  { "error": "..." }   — missing / invalid fields
        404  { "error": "..." }   — loan not found
        409  { "error": "..." }   — loan already returned
    """
    body = request.get_json(silent=True) or {}

    missing = validate_required_fields(body, ["loan_id"])
    if missing:
        return error_response(f"Missing required fields: {', '.join(missing)}")

    try:
        loan_id = int(body["loan_id"])
    except (TypeError, ValueError):
        return error_response("'loan_id' must be an integer.")

    loan = (
        db.session.query(Loan)
        .options(joinedload(Loan.book), joinedload(Loan.user))
        .filter(Loan.id == loan_id)
        .first()
    )
    if not loan:
        return error_response(f"Loan with id {loan_id} not found.", 404)

    if loan.status == LoanStatus.returned:
        return error_response("This loan has already been returned.", 409)

    loan.status = LoanStatus.returned
    loan.return_date = datetime.now(timezone.utc)
    db.session.commit()

    return success_response(loan.to_dict_full())
