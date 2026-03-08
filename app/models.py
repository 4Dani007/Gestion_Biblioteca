"""
app/models.py

SQLAlchemy ORM models for the Library Management System.

Design decisions:
  - Python `enum.Enum` classes drive every constrained-value column.
    SQLAlchemy stores enum values as VARCHAR strings, which keeps SQLite
    compatibility while letting Python validate values at the ORM layer.
  - Relationships use `back_populates` (explicit) instead of `backref`
    (implicit) so both sides of every association are visible in this file.
  - `cascade="all, delete-orphan"` on User → Loan/Reservation ensures that
    deleting a user also removes their loans and reservations automatically.
  - Each model exposes a `to_dict()` method for JSON serialisation.
    Dates are emitted as ISO-8601 strings; enum fields as their string value.
    Foreign-key IDs are included; full nested objects are deliberately
    excluded to avoid accidental N+1 loading in route handlers.
"""

import enum
from datetime import datetime, timezone
from .database import db


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enum definitions
# ---------------------------------------------------------------------------

class UserRole(enum.Enum):
    """Access levels available to library users."""
    student = "student"
    community = "community"
    librarian = "librarian"


class LoanStatus(enum.Enum):
    """Life-cycle states of a physical book loan."""
    borrowed = "borrowed"
    returned = "returned"


class ReservationStatus(enum.Enum):
    """Life-cycle states of a book reservation."""
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


# ---------------------------------------------------------------------------
# Model: User
# ---------------------------------------------------------------------------

class User(db.Model):
    """
    A library patron or staff member.

    Roles:
        student   — enrolled student, standard borrowing limits.
        community — non-student community member, reduced limits.
        librarian — staff; can manage books, loans and reservations.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    # Store only hashed passwords — plain-text is never persisted.
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.Enum(UserRole),
        nullable=False,
        default=UserRole.student,
    )
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    # One user → many loans / reservations.
    # cascade="all, delete-orphan" keeps referential integrity when a user is deleted.
    loans = db.relationship(
        "Loan",
        back_populates="user",
        lazy="select",
        cascade="all, delete-orphan",
    )
    reservations = db.relationship(
        "Reservation",
        back_populates="user",
        lazy="select",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        """
        Serialise to a JSON-safe dictionary.
        Password hash is intentionally omitted from the output.
        """
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<User id={self.id} name={self.name!r} role={self.role.value!r}>"


# ---------------------------------------------------------------------------
# Model: Book
# ---------------------------------------------------------------------------

class Book(db.Model):
    """
    A book title held by the library.

    `available_copies` tracks real-time stock; it is decremented when a loan
    is created and incremented when the loan is returned. It must never exceed
    `total_copies` or drop below zero — these invariants are enforced in the
    service layer (to be implemented).
    """
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=False, index=True)
    total_copies = db.Column(db.Integer, nullable=False, default=1)
    available_copies = db.Column(db.Integer, nullable=False, default=1)

    loans = db.relationship(
        "Loan",
        back_populates="book",
        lazy="select",
    )
    reservations = db.relationship(
        "Reservation",
        back_populates="book",
        lazy="select",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "isbn": self.isbn,
            "total_copies": self.total_copies,
            "available_copies": self.available_copies,
            # Derived convenience flag — useful for UI availability indicators.
            "is_available": self.available_copies > 0,
        }

    def __repr__(self) -> str:
        return (
            f"<Book id={self.id} title={self.title!r} "
            f"available={self.available_copies}/{self.total_copies}>"
        )


# ---------------------------------------------------------------------------
# Model: Loan
# ---------------------------------------------------------------------------

class Loan(db.Model):
    """
    Records a physical copy being borrowed by a user.

    `loan_date`   — set automatically to UTC now when the record is created.
    `return_date` — NULL while the book is still out; filled when returned.
    `status`      — transitions: borrowed → returned.
    """
    __tablename__ = "loans"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_id = db.Column(
        db.Integer,
        db.ForeignKey("books.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    loan_date = db.Column(db.DateTime, nullable=False, default=_utcnow)
    return_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(
        db.Enum(LoanStatus),
        nullable=False,
        default=LoanStatus.borrowed,
    )

    # Many-to-one back-references
    user = db.relationship("User", back_populates="loans")
    book = db.relationship("Book", back_populates="loans")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "book_id": self.book_id,
            "loan_date": self.loan_date.isoformat() if self.loan_date else None,
            "return_date": self.return_date.isoformat() if self.return_date else None,
            "status": self.status.value,
        }

    def to_dict_full(self) -> dict:
        """
        Extended serialisation that embeds related User and Book summaries.
        Only call this when you know both relationships are already loaded
        (e.g. after an explicit joinedload) to avoid silent N+1 queries.
        """
        base = self.to_dict()
        base["user"] = self.user.to_dict() if self.user else None
        base["book"] = self.book.to_dict() if self.book else None
        return base

    def __repr__(self) -> str:
        return (
            f"<Loan id={self.id} user={self.user_id} "
            f"book={self.book_id} status={self.status.value!r}>"
        )


# ---------------------------------------------------------------------------
# Model: Reservation
# ---------------------------------------------------------------------------

class Reservation(db.Model):
    """
    Holds a user's place in queue for a book with no available copies.

    `reservation_date` — set automatically when the record is created.
    `status` transitions:
        active    → completed  (when the reserved copy is handed to the user)
        active    → cancelled  (when the user cancels or the reservation expires)
    """
    __tablename__ = "reservations"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_id = db.Column(
        db.Integer,
        db.ForeignKey("books.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    reservation_date = db.Column(db.DateTime, nullable=False, default=_utcnow)
    status = db.Column(
        db.Enum(ReservationStatus),
        nullable=False,
        default=ReservationStatus.active,
    )

    # Many-to-one back-references
    user = db.relationship("User", back_populates="reservations")
    book = db.relationship("Book", back_populates="reservations")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "book_id": self.book_id,
            "reservation_date": (
                self.reservation_date.isoformat() if self.reservation_date else None
            ),
            "status": self.status.value,
        }

    def to_dict_full(self) -> dict:
        """
        Extended serialisation with embedded User and Book summaries.
        Same N+1 caveat as Loan.to_dict_full() applies here.
        """
        base = self.to_dict()
        base["user"] = self.user.to_dict() if self.user else None
        base["book"] = self.book.to_dict() if self.book else None
        return base

    def __repr__(self) -> str:
        return (
            f"<Reservation id={self.id} user={self.user_id} "
            f"book={self.book_id} status={self.status.value!r}>"
        )
