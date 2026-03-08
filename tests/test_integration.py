"""
tests/test_integration.py

Integration tests for the Library Management System.

These tests verify that operations across multiple components produce the
correct side-effects on the database state (availability counters, loan
records, reservation records).

Expected failures (intentional defects):
  FAIL  test_borrow_rejected_when_no_copies_available   — Bug 2: borrowing
                                                           is allowed even
                                                           when copies == 0
  FAIL  test_return_restores_available_copies           — Bug 3: returning
                                                           does NOT increment
                                                           available_copies
  FAIL  test_reserve_duplicate_for_same_user_rejected   — Bug 1: duplicate
                                                           reservations are
                                                           allowed

All other tests in this file are expected to PASS.
"""

import pytest


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _register(client, email="user@lib.com", name="User", password="pass99",
              role="student"):
    res = client.post("/api/auth/register",
                      json={"name": name, "email": email,
                            "password": password, "role": role})
    return res.get_json()["data"]["id"]


def _add_book(client, isbn="B-001", copies=3):
    res = client.post("/api/books/", json={
        "title": "Test Book", "author": "Test Author",
        "isbn": isbn, "total_copies": copies,
    })
    return res.get_json()["data"]["id"]


def _get_book(client, book_id):
    res = client.get("/api/books/")
    books = res.get_json()["data"]
    return next((b for b in books if b["id"] == book_id), None)


def _borrow(client, user_id, book_id):
    return client.post("/api/loans/borrow",
                       json={"user_id": user_id, "book_id": book_id})


def _return(client, loan_id):
    return client.post("/api/loans/return", json={"loan_id": loan_id})


def _reserve(client, user_id, book_id):
    return client.post("/api/reservations/",
                       json={"user_id": user_id, "book_id": book_id})


# ===========================================================================
# BORROWING — creates loan record
# ===========================================================================

class TestBorrowCreatesLoanRecord:
    @pytest.fixture(autouse=True)
    def seed(self, client):
        self.uid = _register(client, email="borrow1@test.com")
        self.bid = _add_book(client, isbn="LN-001", copies=2)

    def test_borrow_returns_201(self, client):
        res = _borrow(client, self.uid, self.bid)
        assert res.status_code == 201

    def test_borrow_response_contains_loan_id(self, client):
        res = _borrow(client, self.uid, self.bid)
        assert "id" in res.get_json()["data"]

    def test_borrow_loan_status_is_borrowed(self, client):
        res = _borrow(client, self.uid, self.bid)
        assert res.get_json()["data"]["status"] == "borrowed"

    def test_borrow_loan_has_correct_user_and_book(self, client):
        res = _borrow(client, self.uid, self.bid)
        data = res.get_json()["data"]
        assert data["user_id"] == self.uid
        assert data["book_id"] == self.bid

    def test_borrow_loan_date_is_set(self, client):
        res = _borrow(client, self.uid, self.bid)
        assert res.get_json()["data"]["loan_date"] is not None

    def test_borrow_return_date_is_null_initially(self, client):
        res = _borrow(client, self.uid, self.bid)
        assert res.get_json()["data"]["return_date"] is None

    def test_borrow_decrements_available_copies(self, client):
        before = _get_book(client, self.bid)["available_copies"]
        _borrow(client, self.uid, self.bid)
        after = _get_book(client, self.bid)["available_copies"]
        assert after == before - 1

    def test_borrow_unknown_user_returns_404(self, client):
        res = _borrow(client, 9999, self.bid)
        assert res.status_code == 404

    def test_borrow_unknown_book_returns_404(self, client):
        res = _borrow(client, self.uid, 9999)
        assert res.status_code == 404

    # ------------------------------------------------------------------
    # BUG 2 — borrow must be rejected when available_copies == 0
    # Expected: 409   |   Actual (buggy): 201  →  TEST FAILS
    # ------------------------------------------------------------------
    def test_borrow_rejected_when_no_copies_available(self, client):
        uid2 = _register(client, email="borrow2@test.com")
        _borrow(client, self.uid, self.bid)
        _borrow(client, uid2, self.bid)
        res = _borrow(client, self.uid, self.bid)
        assert res.status_code == 409, (
            "BUG 2: borrow succeeded even with 0 available copies "
            f"(got {res.status_code}), expected 409"
        )


# ===========================================================================
# RETURNING — updates loan status
# ===========================================================================

class TestReturnUpdatesLoanStatus:
    @pytest.fixture(autouse=True)
    def seed(self, client):
        self.uid = _register(client, email="ret1@test.com")
        self.bid = _add_book(client, isbn="LN-002", copies=2)
        borrow_res = _borrow(client, self.uid, self.bid)
        self.loan_id = borrow_res.get_json()["data"]["id"]
        self.copies_before_return = _get_book(client, self.bid)["available_copies"]

    def test_return_responds_200(self, client):
        res = _return(client, self.loan_id)
        assert res.status_code == 200

    def test_return_sets_status_to_returned(self, client):
        _return(client, self.loan_id)
        res = _return(client, self.loan_id)
        assert res.status_code == 409

    def test_return_sets_return_date(self, client):
        res = _return(client, self.loan_id)
        assert res.get_json()["data"]["return_date"] is not None

    def test_return_loan_status_is_returned(self, client):
        res = _return(client, self.loan_id)
        assert res.get_json()["data"]["status"] == "returned"

    def test_return_already_returned_gives_409(self, client):
        _return(client, self.loan_id)
        res = _return(client, self.loan_id)
        assert res.status_code == 409

    def test_return_unknown_loan_gives_404(self, client):
        res = _return(client, 99999)
        assert res.status_code == 404

    # ------------------------------------------------------------------
    # BUG 3 — returning must restore available_copies by 1
    # Expected: copies_before + 1   |   Actual (buggy): copies unchanged
    # TEST FAILS
    # ------------------------------------------------------------------
    def test_return_restores_available_copies(self, client):
        _return(client, self.loan_id)
        after = _get_book(client, self.bid)["available_copies"]
        expected = self.copies_before_return + 1
        assert after == expected, (
            f"BUG 3: available_copies after return is {after}, "
            f"expected {expected} — stock was not restored"
        )


# ===========================================================================
# RESERVING — affects book visibility / prevents duplicates
# ===========================================================================

class TestReservationSideEffects:
    @pytest.fixture(autouse=True)
    def seed(self, client):
        self.uid = _register(client, email="res1@test.com")
        self.bid = _add_book(client, isbn="LN-003", copies=3)

    def test_reservation_created_with_active_status(self, client):
        res = _reserve(client, self.uid, self.bid)
        assert res.status_code == 201
        assert res.get_json()["data"]["status"] == "active"

    def test_reservation_links_correct_user_and_book(self, client):
        res = _reserve(client, self.uid, self.bid)
        data = res.get_json()["data"]
        assert data["user_id"] == self.uid
        assert data["book_id"] == self.bid

    def test_reservation_date_is_set(self, client):
        res = _reserve(client, self.uid, self.bid)
        assert res.get_json()["data"]["reservation_date"] is not None

    def test_different_users_can_reserve_same_book(self, client):
        uid2 = _register(client, email="res2@test.com")
        res1 = _reserve(client, self.uid, self.bid)
        res2 = _reserve(client, uid2, self.bid)
        assert res1.status_code == 201
        assert res2.status_code == 201

    def test_reservation_rejected_when_no_copies(self, client):
        uid2 = _register(client, email="res3@test.com")
        uid3 = _register(client, email="res4@test.com")
        uid4 = _register(client, email="res5@test.com")
        _reserve(client, self.uid, self.bid)
        _reserve(client, uid2, self.bid)
        _reserve(client, uid3, self.bid)
        res = _reserve(client, uid4, self.bid)
        assert res.status_code == 409

    # ------------------------------------------------------------------
    # BUG 1 — second reservation for same user+book must be rejected
    # Expected: 409   |   Actual (buggy): 201  →  TEST FAILS
    # ------------------------------------------------------------------
    def test_reserve_duplicate_for_same_user_rejected(self, client):
        _reserve(client, self.uid, self.bid)
        res = _reserve(client, self.uid, self.bid)
        assert res.status_code == 409, (
            "BUG 1: duplicate reservation was accepted "
            f"(got {res.status_code}), expected 409"
        )
