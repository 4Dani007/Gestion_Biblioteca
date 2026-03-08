"""
app/routes/reservation_routes.py

Reservation management routes for the Library Management System.

Endpoints (all under /api/reservations):
  POST /  — Place a reservation on a book.
  GET  /  — List reservations, optionally filtered by user.

Business rules enforced here:
  - A book can only be reserved if available_copies > 0.
  - A user cannot hold more than one active reservation for the same book.
"""

from flask import Blueprint, request
from sqlalchemy.orm import joinedload

from ..database import db
from ..models import Book, Reservation, ReservationStatus, User
from ..utils import error_response, success_response, validate_required_fields

reservation_bp = Blueprint("reservations", __name__)


# ---------------------------------------------------------------------------
# POST /api/reservations/
# ---------------------------------------------------------------------------

@reservation_bp.route("/", methods=["POST"])
def create_reservation():
    """
    Place a reservation on an available book.

    Request JSON:
        {
            "user_id": int  (required),
            "book_id": int  (required)
        }

    Business rules:
        - user_id must reference an existing user.
        - book_id must reference an existing book.
        - book.available_copies must be > 0.
        - The user must not already hold an active reservation for that book.

    Responses:
        201  { "data": <reservation> }
        400  { "error": "..." }   — missing / invalid fields
        404  { "error": "..." }   — user or book not found
        409  { "error": "..." }   — no copies available or duplicate reservation
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

    # Business rule: reservation requires at least one available copy.
    if book.available_copies < 1:
        return error_response(
            f"No available copies of '{book.title}' to reserve.",
            409,
        )

    reservation = Reservation(
        user_id=user_id,
        book_id=book_id,
        status=ReservationStatus.active,
    )
    db.session.add(reservation)
    db.session.commit()

    db.session.refresh(reservation)
    return success_response(reservation.to_dict_full(), 201)


# ---------------------------------------------------------------------------
# GET /api/reservations/
# ---------------------------------------------------------------------------

@reservation_bp.route("/", methods=["GET"])
def list_reservations():
    """
    Return reservations, optionally filtered by user or status.

    Query params (all optional):
        user_id — return only reservations belonging to this user.
        status  — filter by status: active | completed | cancelled.

    Responses:
        200  { "data": [ <reservation>, ... ] }
        400  { "error": "..." }   — invalid user_id or status value
    """
    query = db.session.query(Reservation).options(
        joinedload(Reservation.user),
        joinedload(Reservation.book),
    )

    # Optional filter: by user
    raw_user_id = request.args.get("user_id")
    if raw_user_id is not None:
        try:
            user_id = int(raw_user_id)
        except ValueError:
            return error_response("Query parameter 'user_id' must be an integer.")
        query = query.filter(Reservation.user_id == user_id)

    # Optional filter: by status
    raw_status = request.args.get("status")
    if raw_status is not None:
        valid_statuses = {s.value for s in ReservationStatus}
        if raw_status not in valid_statuses:
            return error_response(
                f"'status' must be one of: {', '.join(sorted(valid_statuses))}."
            )
        query = query.filter(Reservation.status == ReservationStatus(raw_status))

    reservations = query.order_by(Reservation.reservation_date.desc()).all()
    return success_response([r.to_dict_full() for r in reservations])
