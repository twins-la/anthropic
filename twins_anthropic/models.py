"""Response builders + synthetic-content helpers for the Anthropic twin.

The twin emits the canonical Anthropic Messages API response shape,
documented at https://docs.anthropic.com/en/api/messages (retrieved
2026-05-08). Content is synthetic but the structure is verbatim, so SDKs
that parse the response work without modification.
"""

from datetime import datetime, timezone
from typing import Optional


def now_iso_z() -> str:
    """ISO-8601 UTC timestamp with millisecond precision and ``Z`` suffix."""
    n = datetime.now(tz=timezone.utc)
    return f"{n.strftime('%Y-%m-%dT%H:%M:%S')}.{n.microsecond // 1000:03d}Z"


def now_unix() -> int:
    """Current UTC time as a Unix epoch in seconds."""
    return int(datetime.now(tz=timezone.utc).timestamp())


def _last_user_text(messages: list) -> str:
    """Extract a best-effort plain-text view of the last user message."""
    for msg in reversed(messages or []):
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
            if parts:
                return " ".join(parts)
        return ""
    return ""


def build_synthetic_response_text(messages: list, model: str) -> str:
    """Deterministic, non-empty synthetic stub that echoes the prompt."""
    last = _last_user_text(messages)
    snippet = last[:80]
    return f"[{model} synthetic response] You said: {snippet}"


def count_input_tokens(messages: list, system: str = "") -> int:
    """Word-count heuristic: approx 4 chars per token, minimum 1."""
    total_chars = 0
    if isinstance(system, str):
        total_chars += len(system)
    elif isinstance(system, list):
        for block in system:
            if isinstance(block, dict) and block.get("type") == "text":
                total_chars += len(str(block.get("text", "")))
    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text":
                    total_chars += len(str(block.get("text", "")))
                elif btype == "tool_use":
                    total_chars += len(str(block.get("input", "")))
                elif btype == "tool_result":
                    inner = block.get("content")
                    if isinstance(inner, str):
                        total_chars += len(inner)
                    elif isinstance(inner, list):
                        for sub in inner:
                            if isinstance(sub, dict) and sub.get("type") == "text":
                                total_chars += len(str(sub.get("text", "")))
    tokens = (total_chars + 3) // 4
    return max(tokens, 1)


def build_message_response(
    *,
    message_id: str,
    model: str,
    content_text: str,
    input_tokens: int,
    output_tokens: int,
    stop_reason: str = "end_turn",
    thinking_text: Optional[str] = None,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> dict:
    """Canonical Messages API response (non-streaming)."""
    content: list[dict] = []
    if thinking_text:
        content.append({"type": "thinking", "thinking": thinking_text})
    content.append({"type": "text", "text": content_text})

    usage: dict = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
    if cache_creation_tokens:
        usage["cache_creation_input_tokens"] = cache_creation_tokens
    if cache_read_tokens:
        usage["cache_read_input_tokens"] = cache_read_tokens

    return {
        "id": f"msg_{message_id}",
        "type": "message",
        "role": "assistant",
        "content": content,
        "model": model,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": usage,
    }
