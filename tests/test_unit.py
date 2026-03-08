"""
tests/test_unit.py

Unit-level tests for the Library Management System.

Each test exercises one behaviour through the Flask test client.

Expected failures (intentional defects):
  FAIL  test_register_duplicate_email_is_rejected   — Bug 5: duplicate e-mails
                                                       are allowed
  FAIL  test_reserve_duplicate_is_rejected          — Bug 1: duplicate
                                                       reservations are allowed

NOTE — Bug 4 (case-sensitive search):
  The ilike → like change was applied in book_routes.py, but SQLite's LIKE
  operator is case-insensitive for ASCII by default, so the tests below
  (test_search_by_title_lowercase, test_search_by_author_uppercase) PASS in
  SQLite.  The same bug would produce failures on PostgreSQL or MySQL.

All other tests in this file are expected to PASS.
"""

import pytest


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _register(client, *, name="Alice", email="alice@test.com",
              password="secret1", role="student"):
    return client.post("/api/auth/register", json={
        "name": name, "email": email,
        "password": password, "role": role,
    })


def _add_book(client, *, title="Clean Code", author="Robert Martin",
              isbn="111-1", total_copies=3):
    return client.post("/api/books/", json={
        "title": title, "author": author,
        "isbn": isbn, "total_copies": total_copies,
    })


# ===========================================================================
# CREATE USER
# ===========================================================================

class TestCreateUser:
    def test_register_returns_201(self, client):
        res = _register(client)
        assert res.status_code == 201

    def test_register_response_contains_user_id(self, client):
        res = _register(client)
        body = res.get_json()
        assert "id" in body["data"]

    def test_register_stores_name_and_email(self, client):
        res = _register(client, name="Bob", email="bob@test.com")
        data = res.get_json()["data"]
        assert data["name"] == "Bob"
        assert data["email"] == "bob@test.com"

    def test_register_default_role_is_student(self, client):
        res = _register(client)
        assert res.get_json()["data"]["role"] == "student"

    def test_register_missing_name_returns_400(self, client):
        res = client.post("/api/auth/register", json={
            "email": "x@test.com", "password": "secret1",
        })
        assert res.status_code == 400

    def test_register_missing_email_returns_400(self, client):
        res = client.post("/api/auth/register", json={
            "name": "X", "password": "secret1",
        })
        assert res.status_code == 400

    def test_register_short_password_returns_400(self, client):
        res = client.post("/api/auth/register", json={
            "name": "X", "email": "x@test.com", "password": "abc",
        })
        assert res.status_code == 400

    def test_register_invalid_email_format_returns_400(self, client):
        res = client.post("/api/auth/register", json={
            "name": "X", "email": "not-an-email", "password": "secret1",
        })
        assert res.status_code == 400

    def test_register_invalid_role_returns_400(self, client):
        res = client.post("/api/auth/register", json={
            "name": "X", "email": "x@test.com",
            "password": "secret1", "role": "admin",
        })
        assert res.status_code == 400

    # ------------------------------------------------------------------
    # BUG 5 — duplicate e-mails should be rejected with 409
    # Expected: 409   |   Actual (buggy): 201  →  TEST FAILS
    # ------------------------------------------------------------------
    def test_register_duplicate_email_is_rejected(self, client):
        _register(client, email="dup@test.com")
        res = _register(client, name="Other", email="dup@test.com")
        assert res.status_code == 409, (
            "BUG 5: duplicate e-mail was accepted (got "
            f"{res.status_code}), expected 409"
        )


# ===========================================================================
# ADD BOOK
# ===========================================================================

class TestAddBook:
    def test_add_book_returns_201(self, client):
        res = _add_book(client)
        assert res.status_code == 201

    def test_add_book_response_has_correct_fields(self, client):
        res = _add_book(client, title="Refactoring", author="Fowler",
                        isbn="222-2", total_copies=5)
        data = res.get_json()["data"]
        assert data["title"] == "Refactoring"
        assert data["author"] == "Fowler"
        assert data["isbn"] == "222-2"
        assert data["total_copies"] == 5

    def test_add_book_available_copies_equals_total_copies(self, client):
        res = _add_book(client, total_copies=4)
        data = res.get_json()["data"]
        assert data["available_copies"] == data["total_copies"]

    def test_add_book_missing_title_returns_400(self, client):
        res = client.post("/api/books/", json={
            "author": "X", "isbn": "333-3", "total_copies": 1,
        })
        assert res.status_code == 400

    def test_add_book_missing_isbn_returns_400(self, client):
        res = client.post("/api/books/", json={
            "title": "T", "author": "A", "total_copies": 1,
        })
        assert res.status_code == 400

    def test_add_book_zero_copies_returns_400(self, client):
        res = client.post("/api/books/", json={
            "title": "T", "author": "A", "isbn": "444-4", "total_copies": 0,
        })
        assert res.status_code == 400

    def test_add_book_duplicate_isbn_returns_409(self, client):
        _add_book(client, isbn="DUP-1")
        res = _add_book(client, title="Other", isbn="DUP-1")
        assert res.status_code == 409

    def test_add_book_negative_copies_returns_400(self, client):
        res = client.post("/api/books/", json={
            "title": "T", "author": "A", "isbn": "NEG-1", "total_copies": -2,
        })
        assert res.status_code == 400


# ===========================================================================
# SEARCH BOOK
# ===========================================================================

class TestSearchBook:
    @pytest.fixture(autouse=True)
    def seed_book(self, client):
        _add_book(client, title="Design Patterns", author="Gang of Four",
                  isbn="SRCH-1", total_copies=2)

    def test_search_by_exact_title(self, client):
        res = client.get("/api/books/search?q=Design Patterns")
        assert res.status_code == 200
        assert len(res.get_json()["data"]) == 1

    def test_search_returns_matching_book(self, client):
        res = client.get("/api/books/search?q=Design")
        data = res.get_json()["data"]
        assert any("Design Patterns" in b["title"] for b in data)

    def test_search_by_author_substring(self, client):
        res = client.get("/api/books/search?q=Gang")
        data = res.get_json()["data"]
        assert len(data) == 1

    def test_search_missing_q_returns_400(self, client):
        res = client.get("/api/books/search")
        assert res.status_code == 400

    def test_search_blank_q_returns_400(self, client):
        res = client.get("/api/books/search?q=   ")
        assert res.status_code == 400

    def test_search_no_match_returns_empty_list(self, client):
        res = client.get("/api/books/search?q=zzznomatch")
        assert res.status_code == 200
        assert res.get_json()["data"] == []

    # ------------------------------------------------------------------
    # BUG 4 — search must be case-insensitive
    # Expected: 1 result   |   Actual (buggy): 0 results  →  TEST FAILS
    # ------------------------------------------------------------------
    def test_search_by_title_lowercase(self, client):
        res = client.get("/api/books/search?q=design patterns")
        data = res.get_json()["data"]
        assert len(data) == 1, (
            "BUG 4: case-insensitive search returned no results "
            f"(got {len(data)}), expected 1"
        )

    # ------------------------------------------------------------------
    # BUG 4 — same defect, checking author in uppercase
    # Expected: 1 result   |   Actual (buggy): 0 results  →  TEST FAILS
    # ------------------------------------------------------------------
    def test_search_by_author_uppercase(self, client):
        res = client.get("/api/books/search?q=GANG OF FOUR")
        data = res.get_json()["data"]
        assert len(data) == 1, (
            "BUG 4: case-insensitive author search returned no results "
            f"(got {len(data)}), expected 1"
        )


# ===========================================================================
# RESERVE BOOK
# ===========================================================================

class TestReserveBook:
    @pytest.fixture(autouse=True)
    def seed(self, client):
        u = _register(client, email="res_user@test.com")
        b = _add_book(client, isbn="RES-1", total_copies=2)
        self.user_id = u.get_json()["data"]["id"]
        self.book_id = b.get_json()["data"]["id"]

    def test_reserve_book_returns_201(self, client):
        res = client.post("/api/reservations/", json={
            "user_id": self.user_id, "book_id": self.book_id,
        })
        assert res.status_code == 201

    def test_reserve_response_has_status_active(self, client):
        res = client.post("/api/reservations/", json={
            "user_id": self.user_id, "book_id": self.book_id,
        })
        assert res.get_json()["data"]["status"] == "active"

    def test_reserve_unknown_user_returns_404(self, client):
        res = client.post("/api/reservations/", json={
            "user_id": 9999, "book_id": self.book_id,
        })
        assert res.status_code == 404

    def test_reserve_unknown_book_returns_404(self, client):
        res = client.post("/api/reservations/", json={
            "user_id": self.user_id, "book_id": 9999,
        })
        assert res.status_code == 404

    def test_reserve_missing_fields_returns_400(self, client):
        res = client.post("/api/reservations/", json={})
        assert res.status_code == 400

    # ------------------------------------------------------------------
    # BUG 1 — duplicate active reservation must be rejected with 409
    # Expected: 409   |   Actual (buggy): 201  →  TEST FAILS
    # ------------------------------------------------------------------
    def test_reserve_duplicate_is_rejected(self, client):
        client.post("/api/reservations/", json={
            "user_id": self.user_id, "book_id": self.book_id,
        })
        res = client.post("/api/reservations/", json={
            "user_id": self.user_id, "book_id": self.book_id,
        })
        assert res.status_code == 409, (
            "BUG 1: duplicate reservation was accepted (got "
            f"{res.status_code}), expected 409"
        )
