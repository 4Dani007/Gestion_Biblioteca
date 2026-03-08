"""
tests/test_reservations.py

Integration tests for reservation endpoints (/api/reservations).

Tests cover:
  - POST /api/reservations/  (success, no copies, duplicate, missing fields)
  - GET  /api/reservations/  (list all, filter by user_id, filter by status)
"""

import pytest


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_id(client):
    resp = client.post(
        "/api/auth/register",
        json={"name": "Res User", "email": "resuser@test.com", "password": "Pass123", "role": "student"},
    )
    return resp.get_json()["data"]["id"]


@pytest.fixture
def book_id(client):
    resp = client.post(
        "/api/books/",
        json={"title": "Res Book", "author": "Author", "isbn": "RES-001", "total_copies": 3},
    )
    return resp.get_json()["data"]["id"]


@pytest.fixture
def reservation_id(client, user_id, book_id):
    """Create one reservation and return its id."""
    resp = client.post("/api/reservations/", json={"user_id": user_id, "book_id": book_id})
    assert resp.status_code == 201
    return resp.get_json()["data"]["id"]


# ---------------------------------------------------------------------------
# POST /api/reservations/
# ---------------------------------------------------------------------------

class TestCreateReservation:

    def test_create_reservation_success(self, client, user_id, book_id):
        """Valid reservation returns 201 with embedded user and book."""
        resp = client.post("/api/reservations/", json={"user_id": user_id, "book_id": book_id})
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["status"] == "active"
        assert data["user"]["id"] == user_id
        assert data["book"]["id"] == book_id
        assert data["reservation_date"] is not None

    def test_create_reservation_no_copies_returns_409(self, client, user_id):
        """Reserving a book with 0 available copies returns 409."""
        # Create book with 1 copy then borrow it
        b = client.post("/api/books/", json={"title": "Full Book", "author": "A", "isbn": "FULL-001", "total_copies": 1})
        bid = b.get_json()["data"]["id"]
        client.post("/api/loans/borrow", json={"user_id": user_id, "book_id": bid})

        resp = client.post("/api/reservations/", json={"user_id": user_id, "book_id": bid})
        assert resp.status_code == 409
        assert "error" in resp.get_json()

    def test_create_duplicate_reservation_returns_409(self, client, user_id, book_id, reservation_id):
        """A user cannot make a second active reservation for the same book."""
        resp = client.post("/api/reservations/", json={"user_id": user_id, "book_id": book_id})
        assert resp.status_code == 409
        assert "error" in resp.get_json()

    def test_create_reservation_unknown_user_returns_404(self, client, book_id):
        """Unknown user_id returns 404."""
        resp = client.post("/api/reservations/", json={"user_id": 99999, "book_id": book_id})
        assert resp.status_code == 404

    def test_create_reservation_unknown_book_returns_404(self, client, user_id):
        """Unknown book_id returns 404."""
        resp = client.post("/api/reservations/", json={"user_id": user_id, "book_id": 99999})
        assert resp.status_code == 404

    def test_create_reservation_missing_user_id_returns_400(self, client, book_id):
        """Missing user_id returns 400."""
        resp = client.post("/api/reservations/", json={"book_id": book_id})
        assert resp.status_code == 400

    def test_create_reservation_missing_book_id_returns_400(self, client, user_id):
        """Missing book_id returns 400."""
        resp = client.post("/api/reservations/", json={"user_id": user_id})
        assert resp.status_code == 400

    def test_create_reservation_empty_body_returns_400(self, client):
        """Empty body returns 400."""
        resp = client.post("/api/reservations/", json={})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/reservations/
# ---------------------------------------------------------------------------

class TestListReservations:

    def test_list_returns_200(self, client):
        """Empty state returns 200 with an empty list."""
        resp = client.get("/api/reservations/")
        assert resp.status_code == 200
        assert isinstance(resp.get_json()["data"], list)

    def test_list_includes_created_reservation(self, client, reservation_id, user_id, book_id):
        """After creating a reservation it appears in the list."""
        resp = client.get("/api/reservations/")
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.get_json()["data"]]
        assert reservation_id in ids

    def test_list_response_shape(self, client, reservation_id):
        """Each reservation object contains expected keys."""
        reservations = client.get("/api/reservations/").get_json()["data"]
        assert len(reservations) > 0
        r = reservations[0]
        for key in ("id", "user_id", "book_id", "status", "reservation_date", "user", "book"):
            assert key in r, f"Missing key: {key}"

    def test_list_filter_by_user_id(self, client, user_id, book_id, reservation_id):
        """Filtering by user_id returns only that user's reservations."""
        # Register a second user and create a reservation for them
        u2 = client.post(
            "/api/auth/register",
            json={"name": "User2", "email": "u2@test.com", "password": "Pass123"},
        ).get_json()["data"]["id"]
        b2 = client.post(
            "/api/books/",
            json={"title": "B2", "author": "A", "isbn": "B2-001", "total_copies": 1},
        ).get_json()["data"]["id"]
        client.post("/api/reservations/", json={"user_id": u2, "book_id": b2})

        resp = client.get(f"/api/reservations/?user_id={user_id}")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert all(r["user_id"] == user_id for r in data)

    def test_list_filter_by_status(self, client, reservation_id):
        """Filtering by status=active returns only active reservations."""
        resp = client.get("/api/reservations/?status=active")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert all(r["status"] == "active" for r in data)

    def test_list_invalid_user_id_param_returns_400(self, client):
        """Non-integer user_id query param returns 400."""
        resp = client.get("/api/reservations/?user_id=abc")
        assert resp.status_code == 400

    def test_list_invalid_status_param_returns_400(self, client):
        """Unknown status query param returns 400."""
        resp = client.get("/api/reservations/?status=unknown")
        assert resp.status_code == 400
