"""Anthropic ``POST /v1/messages/count_tokens`` endpoint.

Reference:
  - https://docs.anthropic.com/en/api/messages-count-tokens (retrieved 2026-05-08)

The twin uses a deterministic word-count heuristic; sufficient fidelity
for fixture-driven tests where the consumer cares about *that* a count is
returned and that the shape is stable, not the exact value real Anthropic
would return.
"""

from flask import Blueprint, g, jsonify, request

from ..auth import require_api_key
from ..errors import anthropic_invalid_request
from ..logs import emit
from ..models import count_input_tokens

count_tokens_bp = Blueprint("count_tokens", __name__)


@count_tokens_bp.route("/v1/messages/count_tokens", methods=["POST"])
@require_api_key
def count_tokens():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return anthropic_invalid_request("request body must be a JSON object")

    model = payload.get("model")
    messages = payload.get("messages")

    if not model or not isinstance(model, str):
        emit(
            g.storage,
            tenant_id=g.api_key_tenant_id,
            plane="data",
            operation="data.messages.count_tokens",
            outcome="failure",
            reason="missing-model",
        )
        return anthropic_invalid_request("'model' is required")

    if not isinstance(messages, list):
        emit(
            g.storage,
            tenant_id=g.api_key_tenant_id,
            plane="data",
            operation="data.messages.count_tokens",
            outcome="failure",
            reason="missing-messages",
        )
        return anthropic_invalid_request("'messages' must be a list")

    system = payload.get("system", "")
    input_tokens = count_input_tokens(messages, system=system if isinstance(system, (str, list)) else "")

    emit(
        g.storage,
        tenant_id=g.api_key_tenant_id,
        plane="data",
        operation="data.messages.count_tokens",
        outcome="success",
        details={"model": model, "input_tokens": input_tokens},
    )
    return jsonify({"input_tokens": input_tokens})
