"""``POST /v1/messages`` with ``stream: true`` — SSE event sequence."""

import json


def _parse_sse(raw: str) -> list[tuple[str, dict]]:
    """Parse an SSE stream (event/data pairs) into [(event_name, data_obj)]."""
    events: list[tuple[str, dict]] = []
    current_event: str | None = None
    current_data_lines: list[str] = []
    for line in raw.split("\n"):
        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current_data_lines.append(line[len("data:"):].strip())
        elif line == "":
            if current_event and current_data_lines:
                payload = "\n".join(current_data_lines)
                try:
                    events.append((current_event, json.loads(payload)))
                except json.JSONDecodeError:
                    events.append((current_event, {"raw": payload}))
            current_event = None
            current_data_lines = []
    return events


def test_messages_streaming_sequence(client, api_key_headers):
    resp = client.post(
        "/v1/messages",
        json={
            "model": "claude-3-5-sonnet-latest",
            "max_tokens": 64,
            "stream": True,
            "messages": [{"role": "user", "content": "stream me"}],
        },
        headers=api_key_headers,
    )
    assert resp.status_code == 200
    assert resp.mimetype == "text/event-stream"
    raw = resp.get_data(as_text=True)
    events = _parse_sse(raw)
    names = [name for name, _ in events]

    # Required ordering anchors:
    assert names[0] == "message_start"
    assert "content_block_start" in names
    assert "content_block_delta" in names
    assert "content_block_stop" in names
    assert "message_delta" in names
    assert names[-1] == "message_stop"

    # Sequence sanity: the first content_block_start precedes deltas which
    # precede content_block_stop, and message_delta precedes message_stop.
    cbs = names.index("content_block_start")
    cbd = names.index("content_block_delta")
    cbstop = names.index("content_block_stop")
    md = names.index("message_delta")
    mstop = names.index("message_stop")
    assert cbs < cbd < cbstop < md < mstop

    # text_delta payloads carry the "text_delta" type
    text_deltas = [
        d for n, d in events
        if n == "content_block_delta" and d.get("delta", {}).get("type") == "text_delta"
    ]
    assert text_deltas
    full_text = "".join(d["delta"]["text"] for d in text_deltas)
    assert "synthetic response" in full_text.lower()
