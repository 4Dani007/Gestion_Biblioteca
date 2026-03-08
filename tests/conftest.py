"""
tests/conftest.py

Pytest configuration and shared fixtures for the Library Management System.

Key fixtures:
  app       — A single Flask application instance configured for testing.
              Uses an in-memory SQLite database; tables are created once for
              the whole session and dropped at the end.

  clean_db  — autouse, function-scoped. Deletes every row from every table
              after each test so the next test starts with a clean slate.
              Deletion order respects foreign-key constraints:
                reservations → loans → books → users.

  client    — Function-scoped Flask test client. Each test gets a fresh
              client; the underlying app and database stay alive.

  db_session — Yields the Flask-SQLAlchemy scoped session inside an app
               context. Useful for ORM-level assertions or seeding without
               going through HTTP.
"""

import pytest
from app import create_app
from app.database import db as _db


# ---------------------------------------------------------------------------
# Session-wide application
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    """
    Create a Flask application configured for testing once per session.

    `scope="session"` avoids recreating the app and its in-memory SQLite
    database on every test — only row-level cleanup is needed between tests.
    """
    flask_app = create_app("testing")

    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.drop_all()


# ---------------------------------------------------------------------------
# Per-test database cleanup  (autouse → runs for every test automatically)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function", autouse=True)
def clean_db(app):
    """
    Truncate all tables after each test to guarantee isolation.

    Deletion order must respect foreign-key constraints so that rows
    referencing other rows are removed first.

    Using DELETE (not DROP TABLE) keeps the schema intact across tests.
    """
    yield  # let the test run first

    with app.app_context():
        from app.models import Reservation, Loan, Book, User

        # If a test left the session in a rolled-back state (e.g. due to a
        # DB constraint violation), reset it before issuing the DELETEs.
        _db.session.rollback()

        # Child tables before parent tables to avoid FK constraint errors.
        _db.session.query(Reservation).delete()
        _db.session.query(Loan).delete()
        _db.session.query(Book).delete()
        _db.session.query(User).delete()
        _db.session.commit()


# ---------------------------------------------------------------------------
# Test client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def client(app):
    """
    Provide a Flask test client for HTTP-level integration tests.

    `scope="function"` pairs with `clean_db` to ensure every test gets both
    a fresh HTTP client and an empty database.
    """
    return app.test_client()


# ---------------------------------------------------------------------------
# Direct ORM session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session(app):
    """
    Yield the Flask-SQLAlchemy scoped session inside an active app context.

    Useful for seeding data directly via ORM or making assertions on the
    database state without going through the HTTP layer.

    `clean_db` handles post-test row deletion, so this fixture only needs
    to expose the session — no additional rollback logic required.
    """
    with app.app_context():
        yield _db.session
