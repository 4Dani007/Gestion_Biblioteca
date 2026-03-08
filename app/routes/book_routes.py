"""
app/routes/book_routes.py

Book catalogue routes for the Library Management System.

Endpoints (all under /api/books):
  GET  /          — List every book in the catalogue.
  GET  /search    — Full-text search across title and author (?q=<term>).
  POST /          — Add a new book (librarian only in a future auth layer).
  PUT  /<id>      — Update an existing book's metadata.
"""

from flask import Blueprint, request

from ..database import db
from ..models import Book
from ..utils import (
    error_response,
    success_response,
    validate_required_fields,
    validate_positive_int,
)

book_bp = Blueprint("books", __name__)


# ---------------------------------------------------------------------------
# GET /api/books/
# ---------------------------------------------------------------------------

@book_bp.route("/", methods=["GET"])
def list_books():
    """
    Return all books in the catalogue ordered by title.

    Responses:
        200  { "data": [ <book>, ... ] }
    """
    books = Book.query.order_by(Book.title).all()
    return success_response([b.to_dict() for b in books])


# ---------------------------------------------------------------------------
# GET /api/books/search?q=<term>
# ---------------------------------------------------------------------------

@book_bp.route("/search", methods=["GET"])
def search_books():
    """
    Search the catalogue by title or author substring (case-insensitive).

    Query params:
        q  (required) — search term, minimum 1 character.

    Responses:
        200  { "data": [ <book>, ... ] }
        400  { "error": "..." }   — missing or blank query term
    """
    term = (request.args.get("q") or "").strip()
    if not term:
        return error_response("Query parameter 'q' is required and cannot be blank.")

    pattern = f"%{term}%"
    books = (
        Book.query
        .filter(
            db.or_(
                Book.title.like(pattern),
                Book.author.like(pattern),
            )
        )
        .order_by(Book.title)
        .all()
    )
    return success_response([b.to_dict() for b in books])


# ---------------------------------------------------------------------------
# POST /api/books/
# ---------------------------------------------------------------------------

@book_bp.route("/", methods=["POST"])
def create_book():
    """
    Add a new book to the library catalogue.

    Request JSON:
        {
            "title":         str  (required),
            "author":        str  (required),
            "isbn":          str  (required, unique),
            "total_copies":  int  (required, >= 1)
        }

    `available_copies` is initialised to `total_copies` on creation.

    Responses:
        201  { "data": <book> }
        400  { "error": "..." }   — missing / invalid fields
        409  { "error": "..." }   — ISBN already exists
    """
    body = request.get_json(silent=True) or {}

    missing = validate_required_fields(body, ["title", "author", "isbn", "total_copies"])
    if missing:
        return error_response(f"Missing required fields: {', '.join(missing)}")

    title = body["title"].strip()
    author = body["author"].strip()
    isbn = body["isbn"].strip()
    total_copies = body["total_copies"]

    if not title:
        return error_response("'title' cannot be blank.")
    if not author:
        return error_response("'author' cannot be blank.")
    if not isbn:
        return error_response("'isbn' cannot be blank.")

    err = validate_positive_int(total_copies, "total_copies")
    if err:
        return error_response(err)
    total_copies = int(total_copies)

    if Book.query.filter_by(isbn=isbn).first():
        return error_response(f"A book with ISBN '{isbn}' already exists.", 409)

    book = Book(
        title=title,
        author=author,
        isbn=isbn,
        total_copies=total_copies,
        available_copies=total_copies,
    )
    db.session.add(book)
    db.session.commit()

    return success_response(book.to_dict(), 201)


# ---------------------------------------------------------------------------
# PUT /api/books/<id>
# ---------------------------------------------------------------------------

@book_bp.route("/<int:book_id>", methods=["PUT"])
def update_book(book_id: int):
    """
    Update an existing book's metadata.

    Accepts a partial payload — only the provided fields are updated.
    Updating `total_copies` also adjusts `available_copies` by the same
    delta so the in-flight loan count is preserved.

    Request JSON (all optional):
        {
            "title":        str,
            "author":       str,
            "isbn":         str,
            "total_copies": int  (>= 1)
        }

    Responses:
        200  { "data": <book> }
        400  { "error": "..." }   — invalid field value
        404  { "error": "..." }   — book not found
        409  { "error": "..." }   — new ISBN conflicts with another book
    """
    book = db.session.get(Book, book_id)
    if not book:
        return error_response(f"Book with id {book_id} not found.", 404)

    body = request.get_json(silent=True) or {}

    if "title" in body:
        title = body["title"].strip()
        if not title:
            return error_response("'title' cannot be blank.")
        book.title = title

    if "author" in body:
        author = body["author"].strip()
        if not author:
            return error_response("'author' cannot be blank.")
        book.author = author

    if "isbn" in body:
        isbn = body["isbn"].strip()
        if not isbn:
            return error_response("'isbn' cannot be blank.")
        existing = Book.query.filter_by(isbn=isbn).first()
        if existing and existing.id != book_id:
            return error_response(f"A book with ISBN '{isbn}' already exists.", 409)
        book.isbn = isbn

    if "total_copies" in body:
        err = validate_positive_int(body["total_copies"], "total_copies")
        if err:
            return error_response(err)
        new_total = int(body["total_copies"])
        # Keep available_copies consistent: adjust by the same delta applied
        # to total_copies so that copies currently on loan remain accounted for.
        delta = new_total - book.total_copies
        book.total_copies = new_total
        book.available_copies = max(0, book.available_copies + delta)

    db.session.commit()
    return success_response(book.to_dict())
