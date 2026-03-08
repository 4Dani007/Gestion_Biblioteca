"""
app/routes/report_routes.py

Reporting routes for the Library Management System.

Endpoints (all under /api/reports):
  GET /loans          — Full loan history with embedded user + book details.
  GET /popular-books  — Books ranked by total borrow count.
"""

from flask import Blueprint, request
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from ..database import db
from ..models import Book, Loan, LoanStatus
from ..utils import error_response, success_response

report_bp = Blueprint("reports", __name__)

_DEFAULT_POPULAR_LIMIT = 10
_MAX_POPULAR_LIMIT = 100


# ---------------------------------------------------------------------------
# GET /api/reports/loans
# ---------------------------------------------------------------------------

@report_bp.route("/loans", methods=["GET"])
def loans_report():
    """
    Return the full loan history enriched with user and book details.

    Optionally filter by loan status.

    Query params (optional):
        status — borrowed | returned  (omit for all loans)

    Responses:
        200  { "data": { "total": int, "loans": [ <loan_full>, ... ] } }
        400  { "error": "..." }   — invalid status value
    """
    valid_statuses = {s.value for s in LoanStatus}
    raw_status = request.args.get("status")

    query = db.session.query(Loan).options(
        joinedload(Loan.user),
        joinedload(Loan.book),
    )

    if raw_status is not None:
        if raw_status not in valid_statuses:
            return error_response(
                f"'status' must be one of: {', '.join(sorted(valid_statuses))}."
            )
        query = query.filter(Loan.status == LoanStatus(raw_status))

    loans = query.order_by(Loan.loan_date.desc()).all()

    return success_response(
        {
            "total": len(loans),
            "loans": [loan.to_dict_full() for loan in loans],
        }
    )


# ---------------------------------------------------------------------------
# GET /api/reports/popular-books
# ---------------------------------------------------------------------------

@report_bp.route("/popular-books", methods=["GET"])
def popular_books():
    """
    Return books ranked by total number of times they have been borrowed,
    including books that have never been borrowed (loan_count = 0).

    Query params (optional):
        limit — max number of results (default 10, max 100).

    Responses:
        200  { "data": { "total": int, "books": [ <book_with_count>, ... ] } }
        400  { "error": "..." }   — invalid limit value
    """
    raw_limit = request.args.get("limit", _DEFAULT_POPULAR_LIMIT)
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return error_response("'limit' must be an integer.")
    if limit < 1 or limit > _MAX_POPULAR_LIMIT:
        return error_response(f"'limit' must be between 1 and {_MAX_POPULAR_LIMIT}.")

    # LEFT OUTER JOIN so books with zero loans still appear in the ranking.
    loan_count_col = func.count(Loan.id).label("loan_count")
    rows = (
        db.session.query(Book, loan_count_col)
        .outerjoin(Loan, Book.id == Loan.book_id)
        .group_by(Book.id)
        .order_by(loan_count_col.desc(), Book.title)
        .limit(limit)
        .all()
    )

    results = [
        {**book.to_dict(), "loan_count": count}
        for book, count in rows
    ]

    return success_response({"total": len(results), "books": results})
