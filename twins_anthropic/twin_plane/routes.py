"""Twin Plane management API for the Anthropic twin.

Served at ``/_twin/`` per TWIN_PLANE.md. The Anthropic twin's account
kind is ``api_key``: a synthetic ``sk-ant-twin-...`` credential issued to
a tenant for use against the Messages API surface.

Public endpoints (``health``, ``scenarios``, ``references``, ``settings``,
``agent-instructions``, ``POST /tenants``) are unauthenticated; everything
else requires tenant or operator-admin auth.
"""

import logging

from flask import Blueprint, Response, g, jsonify, request

from twins_local.tenants import (
    generate_tenant_id,
    generate_tenant_secret,
    hash_secret,
    reject_default_in_cloud,
)

from .. import __version__
from ..auth import hash_api_key
from ..errors import plane_error
from ..logs import emit
from ..models import now_iso_z
from ..sids import generate_api_key, generate_api_key_id, generate_feedback_id
from .auth import require_tenant, require_tenant_or_admin

logger = logging.getLogger(__name__)

twin_plane_bp = Blueprint("twin_plane", __name__, url_prefix="/_twin")


# ---- Public info endpoints ----


@twin_plane_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "twin": "anthropic", "version": __version__})


@twin_plane_bp.route("/scenarios", methods=["GET"])
def scenarios():
    return jsonify(
        {
            "scenarios": [
                {
                    "name": "messages-api",
                    "status": "supported",
                    "description": (
                        "Emulates the public Anthropic Messages API "
                        "surface — POST /v1/messages (full + SSE "
                        "streaming), POST /v1/messages/count_tokens, "
                        "GET /v1/models[/{id}], plus the "
                        "prompt-caching-2024-07-31 and extended-thinking "
                        "beta headers. Synthetic responses; consumer "
                        "SDKs work unchanged."
                    ),
                    "capabilities": [
                        "messages_api",
                        "messages_api_streaming",
                        "count_tokens",
                        "models_list",
                        "prompt_caching_beta",
                        "extended_thinking_beta",
                    ],
                }
            ]
        }
    )


@twin_plane_bp.route("/references", methods=["GET"])
def references():
    return jsonify(
        {
            "references": [
                {
                    "title": "Anthropic Messages API",
                    "url": "https://docs.anthropic.com/en/api/messages",
                    "retrieved": "2026-05-08",
                },
                {
                    "title": "Anthropic Messages API — Streaming",
                    "url": "https://docs.anthropic.com/en/api/messages-streaming",
                    "retrieved": "2026-05-08",
                },
                {
                    "title": "Anthropic Messages API — Count Tokens",
                    "url": "https://docs.anthropic.com/en/api/messages-count-tokens",
                    "retrieved": "2026-05-08",
                },
                {
                    "title": "Anthropic Models API — List Models",
                    "url": "https://docs.anthropic.com/en/api/models-list",
                    "retrieved": "2026-05-08",
                },
                {
                    "title": "Anthropic — Prompt Caching",
                    "url": "https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching",
                    "retrieved": "2026-05-08",
                },
                {
                    "title": "Anthropic — Extended Thinking",
                    "url": "https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking",
                    "retrieved": "2026-05-08",
                },
            ]
        }
    )


@twin_plane_bp.route("/settings", methods=["GET"])
def get_settings():
    return jsonify(
        {
            "twin": "anthropic",
            "version": __version__,
            "base_url": g.base_url,
        }
    )


@twin_plane_bp.route("/agent-instructions", methods=["GET"])
def agent_instructions_endpoint():
    """Plain-text agent instructions per TWIN_PLANE.md."""
    from ..explainer import AGENT_INSTRUCTIONS

    return Response(AGENT_INSTRUCTIONS, mimetype="text/plain")


# ---- Tenants (bootstrap) ----


@twin_plane_bp.route("/tenants", methods=["POST"])
def create_tenant():
    payload = request.get_json(silent=True) or {}
    friendly_name = payload.get("friendly_name", "") if isinstance(payload, dict) else ""

    tenant_id = generate_tenant_id()
    if g.is_cloud:
        reject_default_in_cloud(tenant_id)

    tenant_secret = generate_tenant_secret()
    tenant = g.tenants.create_tenant(
        tenant_id=tenant_id,
        secret_hash=hash_secret(tenant_secret),
        friendly_name=friendly_name,
    )

    emit(
        g.storage,
        tenant_id=tenant_id,
        plane="twin",
        operation="twin.tenant.create",
        resource={"type": "tenant", "id": tenant_id},
    )

    resp = jsonify(
        {
            "tenant_id": tenant_id,
            "tenant_secret": tenant_secret,
            "friendly_name": tenant["friendly_name"],
            "created_at": tenant["created_at"],
        }
    )
    resp.status_code = 201
    return resp


# ---- Logs ----


@twin_plane_bp.route("/logs", methods=["GET"])
@require_tenant_or_admin
def list_logs():
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)
    tenant_id = None if g.is_admin else g.tenant_id
    entries = g.storage.list_logs(limit=limit, offset=offset, tenant_id=tenant_id)
    return jsonify({"logs": entries, "limit": limit, "offset": offset})


# ---- Accounts (api keys) ----


def _api_key_public(row: dict, *, raw_api_key: str | None = None) -> dict:
    out = {
        "kind": "api_key",
        "api_key_id": row["key_id"],
        "tenant_id": row["tenant_id"],
        "friendly_name": row.get("friendly_name", ""),
    }
    if raw_api_key is not None:
        out["api_key"] = raw_api_key
    return out


@twin_plane_bp.route("/accounts", methods=["POST"])
@require_tenant
def create_account():
    payload = request.get_json(silent=True) or {}
    kind = payload.get("kind", "api_key")
    if kind != "api_key":
        return plane_error(
            f"Unknown account kind {kind!r}; only 'api_key' is supported", 400
        )

    api_key = generate_api_key()
    key_id = generate_api_key_id()
    row = g.storage.create_api_key(
        tenant_id=g.tenant_id,
        key_id=key_id,
        key_hash=hash_api_key(api_key),
        friendly_name=payload.get("friendly_name", ""),
    )
    emit(
        g.storage,
        tenant_id=g.tenant_id,
        plane="twin",
        operation="twin.account.create",
        resource={"type": "api_key", "id": key_id},
        details={"kind": "api_key"},
    )
    resp = jsonify(_api_key_public(row, raw_api_key=api_key))
    resp.status_code = 201
    return resp


@twin_plane_bp.route("/accounts", methods=["GET"])
@require_tenant_or_admin
def list_accounts():
    tenant_filter = None if g.is_admin else g.tenant_id
    rows = g.storage.list_api_keys(tenant_id=tenant_filter)
    return jsonify({"accounts": [_api_key_public(r) for r in rows]})


# ---- Messages history ----


@twin_plane_bp.route("/messages", methods=["GET"])
@require_tenant_or_admin
def list_messages():
    """List the (request, response) history for the calling tenant."""
    limit = request.args.get("limit", 100, type=int)
    tenant_filter = None if g.is_admin else g.tenant_id
    rows = g.storage.list_messages(tenant_id=tenant_filter, limit=limit)
    return jsonify({"messages": rows, "limit": limit})


# ---- Feedback ----


@twin_plane_bp.route("/feedback", methods=["POST"])
@require_tenant
def submit_feedback():
    payload = request.get_json(silent=True) or {}
    body = payload.get("body")
    if not body or not isinstance(body, str) or not body.strip():
        return plane_error("'body' is required", 400)

    feedback_id = generate_feedback_id()
    now = now_iso_z()
    record = g.storage.create_feedback(
        {
            "id": feedback_id,
            "tenant_id": g.tenant_id,
            "body": body.strip(),
            "category": payload.get("category", ""),
            "context": payload.get("context", {}),
            "status": "pending",
            "date_created": now,
            "date_updated": now,
        }
    )
    emit(
        g.storage,
        tenant_id=g.tenant_id,
        plane="twin",
        operation="twin.feedback.submit",
        resource={"type": "feedback", "id": feedback_id},
        details={"category": record["category"]},
    )
    return jsonify(record), 201


@twin_plane_bp.route("/feedback", methods=["GET"])
@require_tenant_or_admin
def list_feedback():
    status = request.args.get("status")
    tenant_id = None if g.is_admin else g.tenant_id
    items = g.storage.list_feedback(status=status, tenant_id=tenant_id)
    return jsonify({"feedback": items})
