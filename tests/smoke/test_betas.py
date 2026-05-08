"""Beta-header surfaces — prompt-caching + extended-thinking."""


def test_prompt_caching_beta_returns_cache_creation(client, api_key_headers):
    headers = {**api_key_headers, "anthropic-beta": "prompt-caching-2024-07-31"}
    resp = client.post(
        "/v1/messages",
        json={
            "model": "claude-3-5-sonnet-latest",
            "max_tokens": 64,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "static prefix " * 100,
                            "cache_control": {"type": "ephemeral"},
                        },
                        {"type": "text", "text": "tail"},
                    ],
                }
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    usage = resp.get_json()["usage"]
    assert usage.get("cache_creation_input_tokens", 0) > 0
    # First call: nothing was previously cached, so reads should not appear.
    assert "cache_read_input_tokens" not in usage or usage["cache_read_input_tokens"] == 0


def test_prompt_caching_without_beta_does_not_emit_cache_fields(client, api_key_headers):
    """Without the beta header, cache_control on blocks is ignored."""
    resp = client.post(
        "/v1/messages",
        json={
            "model": "claude-3-5-sonnet-latest",
            "max_tokens": 64,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "static prefix " * 100,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                }
            ],
        },
        headers=api_key_headers,
    )
    usage = resp.get_json()["usage"]
    assert "cache_creation_input_tokens" not in usage


def test_extended_thinking_beta_emits_thinking_block(client, api_key_headers):
    headers = {**api_key_headers, "anthropic-beta": "extended-thinking-2025-01-15"}
    resp = client.post(
        "/v1/messages",
        json={
            "model": "claude-opus-4-7",
            "max_tokens": 256,
            "thinking": {"type": "enabled", "budget_tokens": 100},
            "messages": [{"role": "user", "content": "think for me"}],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    content = resp.get_json()["content"]
    assert content[0]["type"] == "thinking"
    assert content[0]["thinking"]
    assert content[1]["type"] == "text"


def test_extended_thinking_zero_budget_rejected(client, api_key_headers):
    headers = {**api_key_headers, "anthropic-beta": "extended-thinking-2025-01-15"}
    resp = client.post(
        "/v1/messages",
        json={
            "model": "claude-opus-4-7",
            "max_tokens": 256,
            "thinking": {"type": "enabled", "budget_tokens": 0},
            "messages": [{"role": "user", "content": "x"}],
        },
        headers=headers,
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["type"] == "invalid_request_error"


def test_extended_thinking_without_beta_header_ignored(client, api_key_headers):
    """Without the header, ``thinking`` is silently ignored — no error."""
    resp = client.post(
        "/v1/messages",
        json={
            "model": "claude-opus-4-7",
            "max_tokens": 64,
            "thinking": {"type": "enabled", "budget_tokens": 100},
            "messages": [{"role": "user", "content": "x"}],
        },
        headers=api_key_headers,
    )
    assert resp.status_code == 200
    content = resp.get_json()["content"]
    assert content[0]["type"] == "text"
