"""
tests/test_system.py

End-to-end system test for the Library Management System.

Simulates a realistic user journey through the full lifecycle of a library
interaction using only the HTTP API via the Flask test client:

    Step 1 — Register a new user
    Step 2 — Search for a book
    Step 3 — Reserve the book
    Step 4 — Borrow the book
    Step 5 — Return the book

A second scenario exercises the same workflow with a second user to verify
that the system handles concurrent interactions correctly.

Expected failures (intentional defects):
  FAIL  test_full_workflow_copies_restored_after_return  — Bug 3: returning
                                                           a book does NOT
                                                           increment
                                                           available_copies
  FAIL  test_second_user_cannot_borrow_exhausted_book    — Bug 2: borrowing
                                                           is allowed even
                                                           when copies == 0
  FAIL  test_duplicate_email_rejected_during_registration — Bug 5: duplicate
                                                            e-mails are allowed

NOTE — Bug 4 (case-sensitive search):
  test_search_is_case_insensitive PASSES in SQLite because SQLite's LIKE
  operator is case-insensitive for ASCII characters by default.  The bug
  would produce a failure on PostgreSQL or MySQL.

All other tests / assertions in this file are expected to PASS.
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _post(client, url, payload):
    return client.post(url, json=payload)


def _get(client, url):
    return client.get(url)


def _register(client, name, email, password="Password1", role="student"):
    res = _post(client, "/api/auth/register",
                {"name": name, "email": email,
                 "password": password, "role": role})
    assert res.status_code == 201, (
        f"Registration failed for {email}: {res.get_json()}"
    )
    return res.get_json()["data"]


def _add_book(client, title, author, isbn, copies):
    res = _post(client, "/api/books/",
                {"title": title, "author": author,
                 "isbn": isbn, "total_copies": copies})
    assert res.status_code == 201, (
        f"Book creation failed: {res.get_json()}"
    )
    return res.get_json()["data"]


def _search(client, term):
    res = _get(client, f"/api/books/search?q={term}")
    assert res.status_code == 200
    return res.get_json()["data"]


def _reserve(client, user_id, book_id):
    return _post(client, "/api/reservations/",
                 {"user_id": user_id, "book_id": book_id})


def _borrow(client, user_id, book_id):
    return _post(client, "/api/loans/borrow",
                 {"user_id": user_id, "book_id": book_id})


def _return_book(client, loan_id):
    return _post(client, "/api/loans/return", {"loan_id": loan_id})


def _available_copies(client, book_id):
    res = _get(client, "/api/books/")
    books = res.get_json()["data"]
    book = next((b for b in books if b["id"] == book_id), None)
    assert book is not None, f"Book {book_id} not found in catalogue"
    return book["available_copies"]


# ===========================================================================
# SYSTEM TEST — Full single-user workflow
# ===========================================================================

class TestFullWorkflow:
    """
    Exercises the complete happy-path lifecycle for a single user borrowing
    and returning one book.
    """

    @pytest.fixture(autouse=True)
    def setup_catalogue(self, client):
        self.book = _add_book(
            client,
            title="The Pragmatic Programmer",
            author="Hunt and Thomas",
            isbn="SYS-001",
            copies=2,
        )
        self.book_id = self.book["id"]
        self.initial_copies = self.book["available_copies"]

    # --- Step 1: Register ---

    def test_step1_register_user(self, client):
        user = _register(client, "Carlos", "carlos@lib.com")
        assert user["id"] > 0
        assert user["email"] == "carlos@lib.com"

    # --- Step 2: Search ---

    def test_step2_search_returns_book(self, client):
        results = _search(client, "Pragmatic")
        titles = [b["title"] for b in results]
        assert "The Pragmatic Programmer" in titles

    # ------------------------------------------------------------------
    # BUG 4 — lowercase search term must find the book
    # Expected: 1+ results   |   Actual (buggy): 0  →  TEST FAILS
    # ------------------------------------------------------------------
    def test_search_is_case_insensitive(self, client):
        results = _search(client, "pragmatic programmer")
        assert len(results) >= 1, (
            f"BUG 4: case-insensitive search returned {len(results)} results, "
            "expected at least 1"
        )

    # --- Step 3: Reserve ---

    def test_step3_reserve_book(self, client):
        user = _register(client, "Diana", "diana@lib.com")
        res = _reserve(client, user["id"], self.book_id)
        assert res.status_code == 201
        assert res.get_json()["data"]["status"] == "active"

    # --- Step 4: Borrow ---

    def test_step4_borrow_book_creates_loan(self, client):
        user = _register(client, "Eva", "eva@lib.com")
        res = _borrow(client, user["id"], self.book_id)
        assert res.status_code == 201
        assert res.get_json()["data"]["status"] == "borrowed"

    def test_step4_borrow_decrements_available_copies(self, client):
        user = _register(client, "Felix", "felix@lib.com")
        before = _available_copies(client, self.book_id)
        _borrow(client, user["id"], self.book_id)
        after = _available_copies(client, self.book_id)
        assert after == before - 1

    # --- Step 5: Return ---

    def test_step5_return_sets_status_to_returned(self, client):
        user = _register(client, "Gina", "gina@lib.com")
        loan_res = _borrow(client, user["id"], self.book_id)
        loan_id = loan_res.get_json()["data"]["id"]
        ret = _return_book(client, loan_id)
        assert ret.status_code == 200
        assert ret.get_json()["data"]["status"] == "returned"

    def test_step5_return_sets_return_date(self, client):
        user = _register(client, "Hugo", "hugo@lib.com")
        loan_id = _borrow(client, user["id"], self.book_id).get_json()["data"]["id"]
        ret = _return_book(client, loan_id)
        assert ret.get_json()["data"]["return_date"] is not None

    # ------------------------------------------------------------------
    # BUG 3 — available_copies must increase by 1 after a return
    # Expected: copies_after_borrow + 1   |   Actual (buggy): unchanged
    # TEST FAILS
    # ------------------------------------------------------------------
    def test_full_workflow_copies_restored_after_return(self, client):
        user = _register(client, "Irene", "irene@lib.com")

        copies_before_borrow = _available_copies(client, self.book_id)
        loan_id = _borrow(client, user["id"], self.book_id).get_json()["data"]["id"]
        copies_after_borrow = _available_copies(client, self.book_id)

        assert copies_after_borrow == copies_before_borrow - 1, (
            "Borrow should decrement available_copies"
        )

        _return_book(client, loan_id)
        copies_after_return = _available_copies(client, self.book_id)

        assert copies_after_return == copies_after_borrow + 1, (
            f"BUG 3: available_copies after return is {copies_after_return}, "
            f"expected {copies_after_borrow + 1} — stock was not restored"
        )


# ===========================================================================
# SYSTEM TEST — Two-user scenario with copy exhaustion
# ===========================================================================

class TestTwoUserWorkflow:
    """
    Two users interact with the same single-copy book.
    Verifies that the second user cannot borrow while the book is on loan.
    """

    @pytest.fixture(autouse=True)
    def setup(self, client):
        self.book = _add_book(
            client,
            title="Clean Architecture",
            author="Robert Martin",
            isbn="SYS-002",
            copies=1,
        )
        self.book_id = self.book["id"]
        self.user1 = _register(client, "Jack", "jack@lib.com")
        self.user2 = _register(client, "Karen", "karen@lib.com")

    def test_first_user_can_borrow_single_copy(self, client):
        res = _borrow(client, self.user1["id"], self.book_id)
        assert res.status_code == 201

    # ------------------------------------------------------------------
    # BUG 2 — second borrow must be rejected when copies == 0
    # Expected: 409   |   Actual (buggy): 201  →  TEST FAILS
    # ------------------------------------------------------------------
    def test_second_user_cannot_borrow_exhausted_book(self, client):
        _borrow(client, self.user1["id"], self.book_id)
        copies = _available_copies(client, self.book_id)
        assert copies == 0, (
            f"After first borrow, available_copies should be 0, got {copies}"
        )
        res = _borrow(client, self.user2["id"], self.book_id)
        assert res.status_code == 409, (
            f"BUG 2: second borrow succeeded with 0 copies available "
            f"(got {res.status_code}), expected 409"
        )

    def test_after_return_second_user_can_borrow(self, client):
        loan_id = _borrow(client, self.user1["id"], self.book_id).get_json()["data"]["id"]
        _return_book(client, loan_id)
        res = _borrow(client, self.user2["id"], self.book_id)
        assert res.status_code == 201, (
            "After the first user returns the book, the second user "
            f"should be able to borrow it (got {res.status_code})"
        )


# ===========================================================================
# SYSTEM TEST — Duplicate e-mail registration
# ===========================================================================

class TestDuplicateEmailRegistration:
    """
    Verifies that the system prevents two accounts sharing the same e-mail.
    """

    # ------------------------------------------------------------------
    # BUG 5 — duplicate e-mail must be rejected with 409
    # Expected: 409   |   Actual (buggy): 201  →  TEST FAILS
    # ------------------------------------------------------------------
    def test_duplicate_email_rejected_during_registration(self, client):
        _register(client, "Lena", "lena@lib.com")
        res = client.post("/api/auth/register", json={
            "name": "Lena Clone",
            "email": "lena@lib.com",
            "password": "Password1",
            "role": "student",
        })
        assert res.status_code == 409, (
            f"BUG 5: duplicate e-mail registration was accepted "
            f"(got {res.status_code}), expected 409"
        )

    def test_two_users_with_different_emails_can_register(self, client):
        u1 = _register(client, "Mike", "mike@lib.com")
        u2 = _register(client, "Nina", "nina@lib.com")
        assert u1["id"] != u2["id"]
