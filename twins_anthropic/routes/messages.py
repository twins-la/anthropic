"""Anthropic ``POST /v1/messages`` endpoint (full + SSE streaming).

References:
  - https://docs.anthropic.com/en/api/messages (retrieved 2026-05-08)
  - https://docs.anthropic.com/en/api/messages-streaming (retrieved 2026-05-08)
  - https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching (retrieved 2026-05-08)
  - https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking (retrieved 2026-05-08)

Beta-header surfaces (``anthropic-beta``):

* ``prompt-caching-2024-07-31`` — when present, the twin counts tokens in
  content blocks marked with ``cache_control`` and reports them as
  ``cache_creation_input_tokens`` (first call always creates).
* ``extended-thinking`` (any value with this prefix) — when present and
  the request body has ``thinking: {type: "enabled", budget_tokens: N}``
  with N > 0, the response prepends a synthetic ``thinking`` content
  block before the ``text`` block.
"""

import json

from flask import Blueprint, Response, g, jsonify, request

from ..auth import require_api_key
from ..errors import anthropic_invalid_request
from ..logs import emit
from ..models import (
    build_message_response,
    build_synthetic_response_text,
    count_input_tokens,
    now_iso_z,
)
from ..sids import generate_message_id

messages_bp = Blueprint("messages", __name__)


def _parse_beta_headers() -> set[str]:
    raw = request.headers.get("anthropic-beta", "")
    return {b.strip() for b in raw.split(",") if b.strip()}


def _has_extended_thinking(betas: set[str]) -> bool:
    return any(b.startswith("extended-thinking") for b in betas)


def _count_cache_creation_tokens(messages: list, system) -> int:
    """Count tokens in any block carrying ``cache_control``."""
    total = 0
    if isinstance(system, list):
        for block in system:
            if isinstance(block, dict) and block.get("cache_control"):
                if block.get("type") == "text":
                    total += (len(str(block.get("text", ""))) + 3) // 4
    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if not block.get("cache_control"):
                continue
            if block.get("type") == "text":
                total += (len(str(block.get("text", ""))) + 3) // 4
            elif block.get("type") == "tool_use":
                total += (len(str(block.get("input", ""))) + 3) // 4
    return total


def _validate_request(payload: dict) -> tuple[str | None, str | None]:
    """Return ``(error_reason, error_message)`` or ``(None, None)`` on ok."""
    if not isinstance(payload, dict):
        return "bad-body", "request body must be a JSON object"
    model = payload.get("model")
    if not model or not isinstance(model, str):
        return "missing-model", "'model' is required"
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        return "missing-messages", "'messages' must be a non-empty list"
    max_tokens = payload.get("max_tokens")
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens <= 0:
        return "missing-max-tokens", "'max_tokens' must be a positive integer"
    return None, None


def _chunk_text(text: str, size: int = 5):
    for i in range(0, len(text), size):
        yield text[i : i + size]


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@messages_bp.route("/v1/messages", methods=["POST"])
@require_api_key
def create_message():
    payload = request.get_json(silent=True) or {}
    reason, message = _validate_request(payload)
    if reason:
        emit(
            g.storage,
            tenant_id=g.api_key_tenant_id,
            plane="data",
            operation="data.messages.create",
            outcome="failure",
            reason=reason,
        )
        return anthropic_invalid_request(message)

    model: str = payload["model"]
    messages: list = payload["messages"]
    max_tokens: int = payload["max_tokens"]
    system = payload.get("system", "")
    stream: bool = bool(payload.get("stream", False))
    thinking_cfg = payload.get("thinking")

    betas = _parse_beta_headers()
    prompt_caching = "prompt-caching-2024-07-31" in betas
    extended_thinking = _has_extended_thinking(betas)

    # Validate extended-thinking config when both header + body present.
    thinking_text: str | None = None
    if extended_thinking and isinstance(thinking_cfg, dict):
        if thinking_cfg.get("type") == "enabled":
            budget = thinking_cfg.get("budget_tokens")
            if not isinstance(budget, int) or isinstance(budget, bool) or budget <= 0:
                emit(
                    g.storage,
                    tenant_id=g.api_key_tenant_id,
                    plane="data",
                    operation="data.messages.create",
                    outcome="failure",
                    reason="bad-thinking-budget",
                )
                return anthropic_invalid_request(
                    "'thinking.budget_tokens' must be a positive integer"
                )
            thinking_text = "[synthetic reasoning trace]"

    cache_creation_tokens = _count_cache_creation_tokens(messages, system) if prompt_caching else 0

    content_text = build_synthetic_response_text(messages, model)
    # Honour max_tokens as an upper bound (4 chars/token approx).
    if max_tokens and len(content_text) > max_tokens * 4:
        content_text = content_text[: max_tokens * 4]

    input_tokens = count_input_tokens(messages, system=system if isinstance(system, (str, list)) else "")
    output_tokens = max((len(content_text) + 3) // 4, 1)
    message_id = generate_message_id()

    response_body = build_message_response(
        message_id=message_id,
        model=model,
        content_text=content_text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        stop_reason="end_turn",
        thinking_text=thinking_text,
        cache_creation_tokens=cache_creation_tokens,
        cache_read_tokens=0,
    )

    # Persist the (request, response) pair.
    g.storage.create_message(
        {
            "id": response_body["id"],
            "tenant_id": g.api_key_tenant_id,
            "model": model,
            "request_json": payload,
            "response_json": response_body,
            "beta_headers": sorted(betas),
            "date_created": now_iso_z(),
        }
    )

    emit(
        g.storage,
        tenant_id=g.api_key_tenant_id,
        plane="data",
        operation="data.messages.create",
        resource={"type": "message", "id": response_body["id"]},
        outcome="success",
        details={
            "model": model,
            "stream": stream,
            "betas": sorted(betas),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    )

    if stream:
        return Response(
            _stream_message(response_body, content_text, thinking_text),
            mimetype="text/event-stream",
        )

    return jsonify(response_body)


def _stream_message(response_body: dict, content_text: str, thinking_text: str | None):
    """Yield the canonical Anthropic SSE event sequence.

    Sequence (per messages-streaming spec):

      message_start
      [content_block_start (thinking) → content_block_delta (thinking_delta)+ → content_block_stop]?
      content_block_start (text) → content_block_delta (text_delta)+ → content_block_stop
      message_delta
      message_stop
    """
    msg_skeleton = dict(response_body)
    # ``content`` is empty in message_start per the spec; usage is partial.
    msg_skeleton = {
        **msg_skeleton,
        "content": [],
        "stop_reason": None,
        "stop_sequence": None,
        "usage": {
            "input_tokens": response_body["usage"].get("input_tokens", 0),
            "output_tokens": 1,
        },
    }
    yield _sse_event("message_start", {"type": "message_start", "message": msg_skeleton})

    block_index = 0
    if thinking_text:
        yield _sse_event(
            "content_block_start",
            {
                "type": "content_block_start",
                "index": block_index,
                "content_block": {"type": "thinking", "thinking": ""},
            },
        )
        for chunk in _chunk_text(thinking_text):
            yield _sse_event(
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": block_index,
                    "delta": {"type": "thinking_delta", "thinking": chunk},
                },
            )
        yield _sse_event(
            "content_block_stop",
            {"type": "content_block_stop", "index": block_index},
        )
        block_index += 1

    yield _sse_event(
        "content_block_start",
        {
            "type": "content_block_start",
            "index": block_index,
            "content_block": {"type": "text", "text": ""},
        },
    )
    for chunk in _chunk_text(content_text):
        yield _sse_event(
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": block_index,
                "delta": {"type": "text_delta", "text": chunk},
            },
        )
    yield _sse_event(
        "content_block_stop", {"type": "content_block_stop", "index": block_index}
    )

    yield _sse_event(
        "message_delta",
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn", "stop_sequence": None},
            "usage": {"output_tokens": response_body["usage"].get("output_tokens", 0)},
        },
    )
    yield _sse_event("message_stop", {"type": "message_stop"})
