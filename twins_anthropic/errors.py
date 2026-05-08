"""HTTP error helpers — match Anthropic's JSON error envelope.

Anthropic API errors use the shape ``{"type": "error", "error": {"type":
<str>, "message": <str>}}``. The Twin Plane uses the platform-canonical
``{"error": <str>}`` per TWIN_PLANE.md.

Reference:
  - https://docs.anthropic.com/en/api/errors (retrieved 2026-05-08)
"""

from flask import jsonify


def anthropic_error(error_type: str, message: str, status: int):
    """Anthropic API error envelope."""
    resp = jsonify({"type": "error", "error": {"type": error_type, "message": message}})
    resp.status_code = status
    return resp


def anthropic_unauthorized(message: str = "authentication required"):
    return anthropic_error("authentication_error", message, 401)


def anthropic_invalid_request(message: str):
    return anthropic_error("invalid_request_error", message, 400)


def anthropic_not_found(message: str = "resource not found"):
    return anthropic_error("not_found_error", message, 404)


def plane_error(message: str, status: int = 400):
    """Twin Plane error shape — ``{"error": "<msg>"}`` per TWIN_PLANE.md."""
    resp = jsonify({"error": message})
    resp.status_code = status
    return resp
