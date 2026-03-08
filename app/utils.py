"""
app/utils.py

Shared helpers used across all route modules.

Helpers:
  validate_required_fields — returns a list of field names that are missing
                             or blank in a dict payload.
  error_response           — builds a consistent { "error": ... } JSON reply.
  success_response         — builds a consistent { "data": ... } JSON reply.
  validate_positive_int    — checks that a value is an integer >= 1.
"""

from __future__ import annotations
from typing import Any
from flask import jsonify


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_required_fields(data: dict, required: list[str]) -> list[str]:
    """
    Return the names of any fields that are absent or empty in `data`.

    A field is considered missing if its value is None, an empty string,
    or not present in the dict at all.

    Example:
        missing = validate_required_fields(body, ["name", "email"])
        if missing:
            return error_response(f"Missing fields: {missing}")
    """
    return [field for field in required if not data.get(field)]


def validate_positive_int(value: Any, field_name: str) -> str | None:
    """
    Return an error string if `value` is not a positive integer, else None.

    Accepts both int and string representations so it works with JSON and
    form data alike.
    """
    try:
        as_int = int(value)
    except (TypeError, ValueError):
        return f"'{field_name}' must be an integer."
    if as_int < 1:
        return f"'{field_name}' must be greater than zero."
    return None


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def error_response(message: str, status: int = 400):
    """
    Return a JSON error envelope with a consistent shape.

    Shape: { "error": "<message>" }
    """
    return jsonify({"error": message}), status


def success_response(data: Any, status: int = 200):
    """
    Return a JSON success envelope with a consistent shape.

    Shape: { "data": <data> }
    """
    return jsonify({"data": data}), status
