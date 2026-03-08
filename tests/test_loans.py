"""
tests/test_loans.py

Integration tests for loan endpoints (/api/loans).

Tests cover:
  - POST /api/loans/borrow  (success, no copies, invalid ids)
  - POST /api/loans/return  (success, already returned, bad loan id)
"""

import pytest


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_id(client):
    """Register a test user and return their id."""
    resp = client.post(
        "/api/auth/register",
        json={"name": "Loan User", "email": "loanuser@test.com", "password": "Pass123", "role": "student"},
    )
    return resp.get_json()["data"]["id"]


@pytest.fixture
def book_id(client):
    """Create a test book with 2 copies and return its id."""
    resp = client.post(
        "/api/books/",
        json={"title": "Loan Book", "author": "Author", "isbn": "LOAN-001", "total_copies": 2},
    )
    return resp.get_json()["data"]["id"]


@pytest.fixture
def active_loan_id(client, user_id, book_id):
    """Borrow the test book and return the loan id."""
    resp = client.post("/api/loans/borrow", json={"user_id": user_id, "book_id": book_id})
    assert resp.status_code == 201
    return resp.get_json()["data"]["id"]


# ---------------------------------------------------------------------------
# POST /api/loans/borrow
# ---------------------------------------------------------------------------

class TestBorrowBook:

    def test_borrow_success(self, client, user_id, book_id):
        """Valid borrow returns 201 with loan data and embedded user+book."""
        resp = client.post("/api/loans/borrow", json={"user_id": user_id, "book_id": book_id})
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["status"] == "borrowed"
        assert data["return_date"] is None
        assert data["user"]["id"] == user_id
        assert data["book"]["id"] == book_id

    def test_borrow_decrements_available_copies(self, client, user_id, book_id):
        """available_copies decreases by 1 after a borrow."""
        before = client.get("/api/books/").get_json()["data"]
        book_before = next(b for b in before if b["id"] == book_id)
        copies_before = book_before["available_copies"]

        client.post("/api/loans/borrow", json={"user_id": user_id, "book_id": book_id})

        after = client.get("/api/books/").get_json()["data"]
        book_after = next(b for b in after if b["id"] == book_id)
        assert book_after["available_copies"] == copies_before - 1

    def test_borrow_no_copies_returns_409(self, client, user_id):
        """Borrowing when available_copies == 0 returns 409."""
        # Create a book with only 1 copy and borrow it
        resp = client.post(
            "/api/books/",
            json={"title": "Scarce Book", "author": "A", "isbn": "SCARCE-001", "total_copies": 1},
        )
        scarce_id = resp.get_json()["data"]["id"]
        client.post("/api/loans/borrow", json={"user_id": user_id, "book_id": scarce_id})

        # Second borrow attempt should fail
        resp2 = client.post("/api/loans/borrow", json={"user_id": user_id, "book_id": scarce_id})
        assert resp2.status_code == 409
        assert "error" in resp2.get_json()

    def test_borrow_unknown_user_returns_404(self, client, book_id):
        """Unknown user_id returns 404."""
        resp = client.post("/api/loans/borrow", json={"user_id": 99999, "book_id": book_id})
        assert resp.status_code == 404

    def test_borrow_unknown_book_returns_404(self, client, user_id):
        """Unknown book_id returns 404."""
        resp = client.post("/api/loans/borrow", json={"user_id": user_id, "book_id": 99999})
        assert resp.status_code == 404

    def test_borrow_missing_user_id_returns_400(self, client, book_id):
        """Missing user_id returns 400."""
        resp = client.post("/api/loans/borrow", json={"book_id": book_id})
        assert resp.status_code == 400

    def test_borrow_missing_book_id_returns_400(self, client, user_id):
        """Missing book_id returns 400."""
        resp = client.post("/api/loans/borrow", json={"user_id": user_id})
        assert resp.status_code == 400

    def test_borrow_empty_body_returns_400(self, client):
        """Empty body returns 400."""
        resp = client.post("/api/loans/borrow", json={})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/loans/return
# ---------------------------------------------------------------------------

class TestReturnBook:

    def test_return_success(self, client, active_loan_id, book_id):
        """Returning a borrowed loan returns 200, sets status and return_date."""
        resp = client.post("/api/loans/return", json={"loan_id": active_loan_id})
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["status"] == "returned"
        assert data["return_date"] is not None

    def test_return_increments_available_copies(self, client, active_loan_id, book_id):
        """available_copies increases by 1 after a return."""
        before = client.get("/api/books/").get_json()["data"]
        book_before = next(b for b in before if b["id"] == book_id)
        copies_before = book_before["available_copies"]

        client.post("/api/loans/return", json={"loan_id": active_loan_id})

        after = client.get("/api/books/").get_json()["data"]
        book_after = next(b for b in after if b["id"] == book_id)
        assert book_after["available_copies"] == copies_before + 1

    def test_return_already_returned_returns_409(self, client, active_loan_id):
        """Returning a loan that is already returned gives 409."""
        client.post("/api/loans/return", json={"loan_id": active_loan_id})
        resp = client.post("/api/loans/return", json={"loan_id": active_loan_id})
        assert resp.status_code == 409
        assert "error" in resp.get_json()

    def test_return_unknown_loan_returns_404(self, client):
        """Unknown loan_id returns 404."""
        resp = client.post("/api/loans/return", json={"loan_id": 99999})
        assert resp.status_code == 404

    def test_return_missing_loan_id_returns_400(self, client):
        """Missing loan_id returns 400."""
        resp = client.post("/api/loans/return", json={})
        assert resp.status_code == 400
