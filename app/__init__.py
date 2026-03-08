"""
app/__init__.py

Application factory for the Library Management System.

This module implements the Flask application factory pattern, which allows
creating multiple instances of the app with different configurations — essential
for separating test, development, and production environments.
"""

from flask import Flask, jsonify
from .database import db
from .config import config_by_name


def create_app(config_name: str = "development") -> Flask:
    """
    Factory function that creates and configures the Flask application.

    Args:
        config_name: One of 'development', 'testing', or 'production'.
                     Defaults to 'development'.

    Returns:
        A fully configured Flask application instance.
    """
    app = Flask(__name__)

    # Load configuration class based on the environment name
    app.config.from_object(config_by_name[config_name])

    # Initialize SQLAlchemy with this app instance
    db.init_app(app)

    # Register blueprints (route groups)
    _register_blueprints(app)

    with app.app_context():
        # Models must be imported before db.create_all() so SQLAlchemy's
        # metadata registry knows which tables to create.
        from . import models  # noqa: F401

        # Create all database tables if they don't exist.
        # SQLAlchemy inspects the registered models and emits
        # CREATE TABLE IF NOT EXISTS, so this is safe on every startup.
        db.create_all()

        # Populate seed data only for development and production.
        # Tests use an in-memory database and manage their own fixtures,
        # so seeding is skipped to keep the test environment clean.
        if not app.config.get("TESTING", False):
            from .seeds import seed_database
            seed_database()

    _register_index(app)

    return app


def _register_index(app: Flask) -> None:
    """Attach a root GET / endpoint that lists every available API route."""

    @app.route("/", methods=["GET"])
    def index():
        return jsonify({
            "service": "Library Management System API",
            "version": "1.0.0",
            "endpoints": {
                "auth": {
                    "POST /api/auth/register": "Create a new user account",
                    "POST /api/auth/login":    "Authenticate with email + password",
                },
                "books": {
                    "GET  /api/books/":              "List all books",
                    "GET  /api/books/search?q=":     "Search books by title or author",
                    "POST /api/books/":              "Add a new book",
                    "PUT  /api/books/<id>":          "Update a book",
                },
                "loans": {
                    "POST /api/loans/borrow": "Borrow a book (decrements available copies)",
                    "POST /api/loans/return": "Return a borrowed book (restores available copies)",
                },
                "reservations": {
                    "POST /api/reservations/": "Place a reservation on an available book",
                    "GET  /api/reservations/": "List reservations (filter: ?user_id= &status=)",
                },
                "reports": {
                    "GET /api/reports/loans":         "Full loan history with user + book details",
                    "GET /api/reports/popular-books": "Books ranked by borrow count (?limit=)",
                },
            },
        })


def _register_blueprints(app: Flask) -> None:
    """
    Register all route blueprints onto the Flask app.

    Each blueprint corresponds to a domain area (auth, books, loans, etc.)
    and is mounted under its own URL prefix.
    """
    from .routes.auth_routes import auth_bp
    from .routes.book_routes import book_bp
    from .routes.loan_routes import loan_bp
    from .routes.reservation_routes import reservation_bp
    from .routes.report_routes import report_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(book_bp, url_prefix="/api/books")
    app.register_blueprint(loan_bp, url_prefix="/api/loans")
    app.register_blueprint(reservation_bp, url_prefix="/api/reservations")
    app.register_blueprint(report_bp, url_prefix="/api/reports")
