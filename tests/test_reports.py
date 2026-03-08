"""
tests/test_reports.py

Integration tests for reporting endpoints (/api/reports).

Tests cover:
  - GET /api/reports/loans          (all loans, filter by status)
  - GET /api/reports/popular-books  (ranking, limit param)
"""

import pytest


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded(client):
    """
    Create 1 user + 2 books and borrow book A, leaving book B unborrowed.
    Returns a dict with ids for easy reference in tests.
    """
    user = client.post(
        "/api/auth/register",
        json={"name": "Report User", "email": "reportuser@test.com", "password": "Pass123"},
    ).get_json()["data"]

    book_a = client.post(
        "/api/books/",
        json={"title": "Popular Book A", "author": "Auth A", "isbn": "RPT-A", "total_copies": 3},
    ).get_json()["data"]

    book_b = client.post(
        "/api/books/",
        json={"title": "Unpopular Book B", "author": "Auth B", "isbn": "RPT-B", "total_copies": 2},
    ).get_json()["data"]

    # Borrow book A twice
    loan1 = client.post(
        "/api/loans/borrow", json={"user_id": user["id"], "book_id": book_a["id"]}
    ).get_json()["data"]
    loan2 = client.post(
        "/api/loans/borrow", json={"user_id": user["id"], "book_id": book_a["id"]}
    ).get_json()["data"]

    # Return loan1
    client.post("/api/loans/return", json={"loan_id": loan1["id"]})

    return {
        "user": user,
        "book_a": book_a,
        "book_b": book_b,
        "loan1_id": loan1["id"],
        "loan2_id": loan2["id"],
    }


# ---------------------------------------------------------------------------
# GET /api/reports/loans
# ---------------------------------------------------------------------------

class TestLoansReport:

    def test_loans_report_returns_200(self, client):
        """Empty database returns 200 with zero loans."""
        resp = client.get("/api/reports/loans")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "total" in data
        assert "loans" in data
        assert data["total"] == 0

    def test_loans_report_total_matches_loans_length(self, client, seeded):
        """'total' equals the length of 'loans' array."""
        resp = client.get("/api/reports/loans")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["total"] == len(data["loans"])

    def test_loans_report_includes_created_loans(self, client, seeded):
        """Seeded loans appear in the report."""
        data = client.get("/api/reports/loans").get_json()["data"]
        ids = [l["id"] for l in data["loans"]]
        assert seeded["loan1_id"] in ids
        assert seeded["loan2_id"] in ids

    def test_loans_report_embeds_user_and_book(self, client, seeded):
        """Each loan entry has embedded 'user' and 'book' objects."""
        data = client.get("/api/reports/loans").get_json()["data"]
        assert len(data["loans"]) > 0
        loan = data["loans"][0]
        assert "user" in loan and loan["user"] is not None
        assert "book" in loan and loan["book"] is not None

    def test_loans_report_filter_borrowed(self, client, seeded):
        """Filtering by status=borrowed returns only active loans."""
        data = client.get("/api/reports/loans?status=borrowed").get_json()["data"]
        assert all(l["status"] == "borrowed" for l in data["loans"])

    def test_loans_report_filter_returned(self, client, seeded):
        """Filtering by status=returned returns only returned loans."""
        data = client.get("/api/reports/loans?status=returned").get_json()["data"]
        assert all(l["status"] == "returned" for l in data["loans"])

    def test_loans_report_invalid_status_returns_400(self, client):
        """Unknown status param returns 400."""
        resp = client.get("/api/reports/loans?status=invalid")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/reports/popular-books
# ---------------------------------------------------------------------------

class TestPopularBooks:

    def test_popular_books_returns_200(self, client):
        """Empty database returns 200 with zero books."""
        resp = client.get("/api/reports/popular-books")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "total" in data
        assert "books" in data

    def test_popular_books_includes_loan_count(self, client, seeded):
        """Each book entry includes a 'loan_count' field."""
        data = client.get("/api/reports/popular-books").get_json()["data"]
        assert len(data["books"]) > 0
        for book in data["books"]:
            assert "loan_count" in book

    def test_popular_books_ranked_by_loan_count(self, client, seeded):
        """Book A (2 loans) appears before Book B (0 loans) in the ranking."""
        data = client.get("/api/reports/popular-books").get_json()["data"]
        books = data["books"]
        titles = [b["title"] for b in books]
        assert titles.index("Popular Book A") < titles.index("Unpopular Book B")

    def test_popular_books_book_a_has_correct_count(self, client, seeded):
        """Book A has loan_count == 2."""
        data = client.get("/api/reports/popular-books").get_json()["data"]
        book_a = next(b for b in data["books"] if b["title"] == "Popular Book A")
        assert book_a["loan_count"] == 2

    def test_popular_books_book_b_has_zero_loans(self, client, seeded):
        """Book B with no loans has loan_count == 0."""
        data = client.get("/api/reports/popular-books").get_json()["data"]
        book_b = next(b for b in data["books"] if b["title"] == "Unpopular Book B")
        assert book_b["loan_count"] == 0

    def test_popular_books_limit_param(self, client, seeded):
        """limit param caps the number of results."""
        data = client.get("/api/reports/popular-books?limit=1").get_json()["data"]
        assert len(data["books"]) == 1

    def test_popular_books_invalid_limit_returns_400(self, client):
        """Non-integer limit returns 400."""
        resp = client.get("/api/reports/popular-books?limit=abc")
        assert resp.status_code == 400

    def test_popular_books_zero_limit_returns_400(self, client):
        """limit=0 returns 400."""
        resp = client.get("/api/reports/popular-books?limit=0")
        assert resp.status_code == 400
