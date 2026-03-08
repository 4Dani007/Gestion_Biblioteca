"""
tests/test_auth.py

Integration tests for authentication endpoints (/api/auth).

Tests cover:
  - POST /api/auth/register  (success, duplicate email, missing fields, invalid role)
  - POST /api/auth/login     (success, wrong password, unknown email, missing fields)
"""

import pytest


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------

class TestRegister:

    def test_register_success(self, client):
        """Valid payload creates a user and returns 201 with user data."""
        payload = {
            "name": "Alice Test",
            "email": "alice@test.com",
            "password": "Secret123",
            "role": "student",
        }
        resp = client.post("/api/auth/register", json=payload)
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["email"] == "alice@test.com"
        assert data["role"] == "student"
        assert "password" not in data

    def test_register_default_role_is_student(self, client):
        """Omitting role defaults to 'student'."""
        payload = {"name": "Bob", "email": "bob@test.com", "password": "Secret123"}
        resp = client.post("/api/auth/register", json=payload)
        assert resp.status_code == 201
        assert resp.get_json()["data"]["role"] == "student"

    def test_register_librarian_role(self, client):
        """Explicitly passing role='librarian' is accepted."""
        payload = {
            "name": "Lib Person",
            "email": "lib@test.com",
            "password": "Secret123",
            "role": "librarian",
        }
        resp = client.post("/api/auth/register", json=payload)
        assert resp.status_code == 201
        assert resp.get_json()["data"]["role"] == "librarian"

    def test_register_duplicate_email_returns_409(self, client):
        """Registering the same email twice returns 409 Conflict."""
        payload = {"name": "Carol", "email": "carol@test.com", "password": "Secret123"}
        client.post("/api/auth/register", json=payload)
        resp = client.post("/api/auth/register", json=payload)
        assert resp.status_code == 409
        assert "error" in resp.get_json()

    def test_register_missing_name_returns_400(self, client):
        """Missing 'name' field returns 400."""
        resp = client.post(
            "/api/auth/register",
            json={"email": "x@test.com", "password": "Secret123"},
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_register_missing_email_returns_400(self, client):
        """Missing 'email' field returns 400."""
        resp = client.post(
            "/api/auth/register",
            json={"name": "X", "password": "Secret123"},
        )
        assert resp.status_code == 400

    def test_register_missing_password_returns_400(self, client):
        """Missing 'password' field returns 400."""
        resp = client.post(
            "/api/auth/register",
            json={"name": "X", "email": "x@test.com"},
        )
        assert resp.status_code == 400

    def test_register_short_password_returns_400(self, client):
        """Password shorter than 6 characters returns 400."""
        resp = client.post(
            "/api/auth/register",
            json={"name": "X", "email": "short@test.com", "password": "abc"},
        )
        assert resp.status_code == 400

    def test_register_invalid_email_format_returns_400(self, client):
        """Malformed email address returns 400."""
        resp = client.post(
            "/api/auth/register",
            json={"name": "X", "email": "not-an-email", "password": "Secret123"},
        )
        assert resp.status_code == 400

    def test_register_invalid_role_returns_400(self, client):
        """Unknown role value returns 400."""
        resp = client.post(
            "/api/auth/register",
            json={
                "name": "X",
                "email": "x2@test.com",
                "password": "Secret123",
                "role": "admin",
            },
        )
        assert resp.status_code == 400

    def test_register_empty_json_returns_400(self, client):
        """Empty body returns 400."""
        resp = client.post("/api/auth/register", json={})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------

class TestLogin:

    @pytest.fixture(autouse=True)
    def _seed_user(self, client):
        """Register a user before every test in this class."""
        client.post(
            "/api/auth/register",
            json={
                "name": "Login User",
                "email": "login@test.com",
                "password": "Correct123",
                "role": "student",
            },
        )

    def test_login_success(self, client):
        """Valid credentials return 200 with user data and success message."""
        resp = client.post(
            "/api/auth/login",
            json={"email": "login@test.com", "password": "Correct123"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["user"]["email"] == "login@test.com"
        assert "message" in data
        assert "password" not in data["user"]

    def test_login_wrong_password_returns_401(self, client):
        """Wrong password returns 401."""
        resp = client.post(
            "/api/auth/login",
            json={"email": "login@test.com", "password": "WrongPass"},
        )
        assert resp.status_code == 401
        assert "error" in resp.get_json()

    def test_login_unknown_email_returns_401(self, client):
        """Non-existent email returns 401 (no information leak)."""
        resp = client.post(
            "/api/auth/login",
            json={"email": "nobody@test.com", "password": "Whatever"},
        )
        assert resp.status_code == 401

    def test_login_missing_email_returns_400(self, client):
        """Missing 'email' field returns 400."""
        resp = client.post("/api/auth/login", json={"password": "Correct123"})
        assert resp.status_code == 400

    def test_login_missing_password_returns_400(self, client):
        """Missing 'password' field returns 400."""
        resp = client.post("/api/auth/login", json={"email": "login@test.com"})
        assert resp.status_code == 400

    def test_login_empty_body_returns_400(self, client):
        """Empty body returns 400."""
        resp = client.post("/api/auth/login", json={})
        assert resp.status_code == 400
