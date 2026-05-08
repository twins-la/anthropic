"""Provider-side auth for the Anthropic twin's data plane.

Anthropic's data-plane auth model:

* ``x-api-key: <api key>`` (case-insensitive header)
* ``anthropic-version: <YYYY-MM-DD>`` (required, any value accepted)

The twin stores api keys under a deterministic SHA-256 lookup hash. Real
Anthropic api keys are high-entropy random strings (and the twin's are
the same shape), so a fast cryptographic hash is sufficient for storage
— the value is uninvertible in practice and the lookup is O(1).
"""

import functools
import hashlib

from flask import g, request

from twins_local.logs import ANONYMOUS_TENANT_ID

from .errors import anthropic_invalid_request, anthropic_unauthorized
from .logs import emit


def hash_api_key(api_key: str) -> str:
    """Deterministic SHA-256 hash for api-key storage + lookup."""
    return "sha256:" + hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def _read_api_key() -> str:
    """Header read is case-insensitive — Flask normalises automatically."""
    return (request.headers.get("x-api-key") or "").strip()


def _read_api_version() -> str:
    return (request.headers.get("anthropic-version") or "").strip()


def require_api_key(view_func):
    """Decorator: require ``x-api-key`` + ``anthropic-version`` headers.

    On success, sets ``g.api_key_tenant_id`` and ``g.api_key_id``. On
    failure, emits a normative log entry and returns the canonical
    Anthropic error envelope.
    """

    @functools.wraps(view_func)
    def wrapped(*args, **kwargs):
        api_key = _read_api_key()
        api_version = _read_api_version()

        if not api_version:
            emit(
                g.storage,
                tenant_id=ANONYMOUS_TENANT_ID,
                plane="data",
                operation="auth.api_key.validate",
                outcome="failure",
                reason="missing-anthropic-version",
            )
            return anthropic_invalid_request(
                "anthropic-version header is required"
            )

        if not api_key:
            emit(
                g.storage,
                tenant_id=ANONYMOUS_TENANT_ID,
                plane="data",
                operation="auth.api_key.validate",
                outcome="failure",
                reason="missing-api-key",
            )
            return anthropic_unauthorized("x-api-key header is required")

        row = g.storage.get_api_key_by_hash(hash_api_key(api_key))
        if not row:
            emit(
                g.storage,
                tenant_id=ANONYMOUS_TENANT_ID,
                plane="data",
                operation="auth.api_key.validate",
                outcome="failure",
                reason="unknown-api-key",
            )
            return anthropic_unauthorized("invalid x-api-key")

        g.api_key_tenant_id = row["tenant_id"]
        g.api_key_id = row["key_id"]
        emit(
            g.storage,
            tenant_id=row["tenant_id"],
            plane="data",
            operation="auth.api_key.validate",
            resource={"type": "api_key", "id": row["key_id"]},
            outcome="success",
        )
        return view_func(*args, **kwargs)

    return wrapped
