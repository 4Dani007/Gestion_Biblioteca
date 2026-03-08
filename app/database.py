"""
app/database.py

Database initialization for the Library Management System.

This module creates the single SQLAlchemy `db` instance that is shared
across the entire application. It is intentionally kept separate from
`__init__.py` to avoid circular imports — models import `db` from here,
and the factory imports `db` from here to call `db.init_app(app)`.

Usage:
    from app.database import db
"""

from flask_sqlalchemy import SQLAlchemy

# The central SQLAlchemy instance.
# It is not bound to any app at creation time; `db.init_app(app)` inside
# `create_app()` performs the actual binding (application factory pattern).
db = SQLAlchemy()
