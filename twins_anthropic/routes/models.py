"""Anthropic ``GET /v1/models`` endpoints.

Reference:
  - https://docs.anthropic.com/en/api/models-list (retrieved 2026-05-08)

The model list is hardcoded at the platform's current cutoff. The shape
matches the public API verbatim so consumer SDKs that paginate or
inspect ``data[*].id`` work without modification.
"""

from flask import Blueprint, g, jsonify

from ..auth import require_api_key
from ..errors import anthropic_not_found
from ..logs import emit

models_bp = Blueprint("models", __name__)


MODELS: list[dict] = [
    {
        "id": "claude-opus-4-7",
        "type": "model",
        "display_name": "Claude Opus 4.7",
        "created_at": "2026-01-15T00:00:00Z",
    },
    {
        "id": "claude-sonnet-4-6",
        "type": "model",
        "display_name": "Claude Sonnet 4.6",
        "created_at": "2025-12-10T00:00:00Z",
    },
    {
        "id": "claude-haiku-4-5-20251001",
        "type": "model",
        "display_name": "Claude Haiku 4.5",
        "created_at": "2025-10-01T00:00:00Z",
    },
    {
        "id": "claude-3-5-sonnet-latest",
        "type": "model",
        "display_name": "Claude 3.5 Sonnet (Latest)",
        "created_at": "2024-10-22T00:00:00Z",
    },
    {
        "id": "claude-3-5-haiku-latest",
        "type": "model",
        "display_name": "Claude 3.5 Haiku (Latest)",
        "created_at": "2024-10-22T00:00:00Z",
    },
    {
        "id": "claude-3-opus-latest",
        "type": "model",
        "display_name": "Claude 3 Opus (Latest)",
        "created_at": "2024-02-29T00:00:00Z",
    },
]


def _model_by_id(model_id: str) -> dict | None:
    for m in MODELS:
        if m["id"] == model_id:
            return m
    return None


@models_bp.route("/v1/models", methods=["GET"])
@require_api_key
def list_models():
    emit(
        g.storage,
        tenant_id=g.api_key_tenant_id,
        plane="data",
        operation="data.models.list",
        outcome="success",
        details={"count": len(MODELS)},
    )
    return jsonify(
        {
            "data": MODELS,
            "has_more": False,
            "first_id": MODELS[0]["id"] if MODELS else None,
            "last_id": MODELS[-1]["id"] if MODELS else None,
        }
    )


@models_bp.route("/v1/models/<model_id>", methods=["GET"])
@require_api_key
def get_model(model_id: str):
    model = _model_by_id(model_id)
    if not model:
        emit(
            g.storage,
            tenant_id=g.api_key_tenant_id,
            plane="data",
            operation="data.models.retrieve",
            resource={"type": "model", "id": model_id},
            outcome="failure",
            reason="unknown-model",
        )
        return anthropic_not_found(f"model {model_id!r} not found")
    emit(
        g.storage,
        tenant_id=g.api_key_tenant_id,
        plane="data",
        operation="data.models.retrieve",
        resource={"type": "model", "id": model_id},
        outcome="success",
    )
    return jsonify(model)
