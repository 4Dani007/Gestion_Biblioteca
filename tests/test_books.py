"""
tests/test_books.py

Integration tests for book catalogue endpoints (/api/books).

Tests cover:
  - GET  /api/books/            (list all)
  - GET  /api/books/search?q=   (search by title / author)
  - POST /api/books/            (create)
  - PUT  /api/books/<id>        (update)
"""

import pytest

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_VALID_BOOK = {
    "title": "Test-Driven Development",
    "author": "Kent Beck",
    "isbn": "978-0321146533",
    "total_copies": 2,
}


def _create_book(client, payload=None):
    """POST a book and return the response."""
    return client.post("/api/books/", json=payload or _VALID_BOOK)


# ---------------------------------------------------------------------------
# GET /api/books/
# ---------------------------------------------------------------------------

class TestListBooks:

    def test_list_books_returns_200(self, client):
        """Empty catalogue returns 200 with an empty list."""
        resp = client.get("/api/books/")
        assert resp.status_code == 200
        assert isinstance(resp.get_json()["data"], list)

    def test_list_books_returns_seeded_books(self, client):
        """After creating a book it appears in the listing."""
        _create_book(client)
        resp = client.get("/api/books/")
        assert resp.status_code == 200
        titles = [b["title"] for b in resp.get_json()["data"]]
        assert "Test-Driven Development" in titles

    def test_list_books_response_shape(self, client):
        """Each book object contains the expected keys."""
        _create_book(client)
        books = client.get("/api/books/").get_json()["data"]
        assert len(books) > 0
        book = books[0]
        for key in ("id", "title", "author", "isbn", "total_copies", "available_copies", "is_available"):
            assert key in book, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# GET /api/books/search?q=
# ---------------------------------------------------------------------------

class TestSearchBooks:

    @pytest.fixture(autouse=True)
    def _seed_books(self, client):
        client.post("/api/books/", json={"title": "Clean Code", "author": "Robert C. Martin", "isbn": "978-0132350884", "total_copies": 1})
        client.post("/api/books/", json={"title": "Refactoring", "author": "Martin Fowler", "isbn": "978-0134757599", "total_copies": 1})

    def test_search_by_title(self, client):
        """Search term matching title returns that book."""
        resp = client.get("/api/books/search?q=clean")
        assert resp.status_code == 200
        titles = [b["title"] for b in resp.get_json()["data"]]
        assert "Clean Code" in titles

    def test_search_by_author(self, client):
        """Search term matching author returns that book."""
        resp = client.get("/api/books/search?q=fowler")
        assert resp.status_code == 200
        titles = [b["title"] for b in resp.get_json()["data"]]
        assert "Refactoring" in titles

    def test_search_case_insensitive(self, client):
        """Search is case-insensitive."""
        resp = client.get("/api/books/search?q=CLEAN")
        assert resp.status_code == 200
        assert len(resp.get_json()["data"]) > 0

    def test_search_no_results(self, client):
        """Term with no matches returns empty list, not an error."""
        resp = client.get("/api/books/search?q=zxqwerty999")
        assert resp.status_code == 200
        assert resp.get_json()["data"] == []

    def test_search_missing_q_param_returns_400(self, client):
        """Missing 'q' param returns 400."""
        resp = client.get("/api/books/search")
        assert resp.status_code == 400

    def test_search_blank_q_param_returns_400(self, client):
        """Blank 'q' param returns 400."""
        resp = client.get("/api/books/search?q=")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/books/
# ---------------------------------------------------------------------------

class TestCreateBook:

    def test_create_book_success(self, client):
        """Valid payload creates a book and returns 201."""
        resp = _create_book(client)
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["isbn"] == _VALID_BOOK["isbn"]
        assert data["available_copies"] == _VALID_BOOK["total_copies"]
        assert data["is_available"] is True

    def test_create_book_available_copies_equals_total(self, client):
        """available_copies is automatically set equal to total_copies."""
        resp = _create_book(client, {**_VALID_BOOK, "total_copies": 5})
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["available_copies"] == 5

    def test_create_book_missing_title_returns_400(self, client):
        """Missing 'title' returns 400."""
        payload = {k: v for k, v in _VALID_BOOK.items() if k != "title"}
        assert _create_book(client, payload).status_code == 400

    def test_create_book_missing_author_returns_400(self, client):
        """Missing 'author' returns 400."""
        payload = {k: v for k, v in _VALID_BOOK.items() if k != "author"}
        assert _create_book(client, payload).status_code == 400

    def test_create_book_missing_isbn_returns_400(self, client):
        """Missing 'isbn' returns 400."""
        payload = {k: v for k, v in _VALID_BOOK.items() if k != "isbn"}
        assert _create_book(client, payload).status_code == 400

    def test_create_book_missing_total_copies_returns_400(self, client):
        """Missing 'total_copies' returns 400."""
        payload = {k: v for k, v in _VALID_BOOK.items() if k != "total_copies"}
        assert _create_book(client, payload).status_code == 400

    def test_create_book_zero_copies_returns_400(self, client):
        """total_copies = 0 returns 400."""
        assert _create_book(client, {**_VALID_BOOK, "total_copies": 0}).status_code == 400

    def test_create_book_negative_copies_returns_400(self, client):
        """Negative total_copies returns 400."""
        assert _create_book(client, {**_VALID_BOOK, "total_copies": -1}).status_code == 400

    def test_create_book_duplicate_isbn_returns_409(self, client):
        """Duplicate ISBN returns 409 Conflict."""
        _create_book(client)
        resp = _create_book(client, {**_VALID_BOOK, "title": "Another Title"})
        assert resp.status_code == 409

    def test_create_book_empty_body_returns_400(self, client):
        """Empty body returns 400."""
        assert client.post("/api/books/", json={}).status_code == 400


# ---------------------------------------------------------------------------
# PUT /api/books/<id>
# ---------------------------------------------------------------------------

class TestUpdateBook:

    @pytest.fixture
    def book_id(self, client):
        """Create a book and return its id."""
        resp = _create_book(client)
        return resp.get_json()["data"]["id"]

    def test_update_title(self, client, book_id):
        """Updating the title persists and returns the new value."""
        resp = client.put(f"/api/books/{book_id}", json={"title": "New Title"})
        assert resp.status_code == 200
        assert resp.get_json()["data"]["title"] == "New Title"

    def test_update_author(self, client, book_id):
        """Updating the author persists correctly."""
        resp = client.put(f"/api/books/{book_id}", json={"author": "New Author"})
        assert resp.status_code == 200
        assert resp.get_json()["data"]["author"] == "New Author"

    def test_update_total_copies_adjusts_available(self, client, book_id):
        """Increasing total_copies by N also increases available_copies by N."""
        orig = client.get("/api/books/").get_json()["data"]
        orig_book = next(b for b in orig if b["id"] == book_id)
        orig_available = orig_book["available_copies"]

        resp = client.put(f"/api/books/{book_id}", json={"total_copies": orig_book["total_copies"] + 3})
        assert resp.status_code == 200
        assert resp.get_json()["data"]["available_copies"] == orig_available + 3

    def test_update_nonexistent_book_returns_404(self, client):
        """Updating a non-existent book returns 404."""
        resp = client.put("/api/books/99999", json={"title": "Ghost"})
        assert resp.status_code == 404

    def test_update_duplicate_isbn_returns_409(self, client, book_id):
        """Updating to an ISBN that belongs to another book returns 409."""
        other = client.post("/api/books/", json={
            "title": "Other Book", "author": "Other", "isbn": "000-OTHER", "total_copies": 1
        })
        other_isbn = other.get_json()["data"]["isbn"]
        resp = client.put(f"/api/books/{book_id}", json={"isbn": other_isbn})
        assert resp.status_code == 409

    def test_update_with_empty_body_returns_unchanged_book(self, client, book_id):
        """Empty body is a no-op and returns the unchanged book."""
        resp = client.put(f"/api/books/{book_id}", json={})
        assert resp.status_code == 200
        assert resp.get_json()["data"]["id"] == book_id
