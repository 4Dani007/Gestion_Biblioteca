"""
app/seeds.py

Development seed data for the Library Management System.

`seed_database()` is idempotent: it checks whether the tables already
contain rows before inserting anything, so it is safe to call on every
application start without duplicating data.

Seed content:
  Users  — 1 librarian, 1 student, 1 community member
  Books  — 7 well-known titles across multiple genres

Passwords are hashed with Werkzeug's PBKDF2-SHA256 before storage.
Plain-text credentials are printed to stdout only when the seed actually
runs (i.e. on the very first start), so developers know what to use.
"""

from werkzeug.security import generate_password_hash
from .database import db
from .models import Book, User, UserRole


# ---------------------------------------------------------------------------
# Seed records
# ---------------------------------------------------------------------------

_USERS: list[dict] = [
    {
        "name": "Laura Librarian",
        "email": "librarian@library.com",
        "password": "Librarian123!",
        "role": UserRole.librarian,
    },
    {
        "name": "Sam Student",
        "email": "student@library.com",
        "password": "Student123!",
        "role": UserRole.student,
    },
    {
        "name": "Chris Community",
        "email": "community@library.com",
        "password": "Community123!",
        "role": UserRole.community,
    },
]

_BOOKS: list[dict] = [
    {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": "978-0132350884",
        "total_copies": 3,
        "available_copies": 3,
    },
    {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt & David Thomas",
        "isbn": "978-0135957059",
        "total_copies": 2,
        "available_copies": 2,
    },
    {
        "title": "Design Patterns",
        "author": "Erich Gamma, Richard Helm, Ralph Johnson & John Vlissides",
        "isbn": "978-0201633610",
        "total_copies": 2,
        "available_copies": 2,
    },
    {
        "title": "Introduction to Algorithms",
        "author": "Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest & Clifford Stein",
        "isbn": "978-0262046305",
        "total_copies": 4,
        "available_copies": 4,
    },
    {
        "title": "The Hitchhiker's Guide to the Galaxy",
        "author": "Douglas Adams",
        "isbn": "978-0345391803",
        "total_copies": 5,
        "available_copies": 5,
    },
    {
        "title": "1984",
        "author": "George Orwell",
        "isbn": "978-0451524935",
        "total_copies": 3,
        "available_copies": 3,
    },
    {
        "title": "Fluent Python",
        "author": "Luciano Ramalho",
        "isbn": "978-1492056355",
        "total_copies": 2,
        "available_copies": 2,
    },
]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def seed_database() -> None:
    """
    Populate the database with default users and books.

    Exits early without touching the database if either table already
    has rows — guarantees idempotency across multiple app restarts.
    """
    if User.query.first() is not None or Book.query.first() is not None:
        return

    _insert_users()
    _insert_books()
    db.session.commit()

    _print_credentials()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _insert_users() -> None:
    for data in _USERS:
        user = User(
            name=data["name"],
            email=data["email"],
            password=generate_password_hash(data["password"]),
            role=data["role"],
        )
        db.session.add(user)


def _insert_books() -> None:
    for data in _BOOKS:
        book = Book(
            title=data["title"],
            author=data["author"],
            isbn=data["isbn"],
            total_copies=data["total_copies"],
            available_copies=data["available_copies"],
        )
        db.session.add(book)


def _print_credentials() -> None:
    """Print seed credentials to stdout so developers know what to use."""
    separator = "-" * 52
    print(separator)
    print("  Database seeded — development credentials")
    print(separator)
    for u in _USERS:
        print(f"  [{u['role'].value:10}]  {u['email']}  /  {u['password']}")
    print(separator)
