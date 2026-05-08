"""``POST /v1/messages`` — happy path, validation, auth, isolation."""


def test_messages_happy_path_non_streaming(client, api_key_headers):
    resp = client.post(
        "/v1/messages",
        json={
            "model": "claude-3-5-sonnet-latest",
            "max_tokens": 64,
            "messages": [{"role": "user", "content": "hi there"}],
        },
        headers=api_key_headers,
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["id"].startswith("msg_")
    assert body["type"] == "message"
    assert body["role"] == "assistant"
    assert body["model"] == "claude-3-5-sonnet-latest"
    assert body["stop_reason"] == "end_turn"
    assert body["stop_sequence"] is None
    assert isinstance(body["content"], list)
    assert body["content"][0]["type"] == "text"
    assert "synthetic response" in body["content"][0]["text"].lower()
    usage = body["usage"]
    assert usage["input_tokens"] >= 1
    assert usage["output_tokens"] >= 1


def test_messages_string_content(client, api_key_headers):
    resp = client.post(
        "/v1/messages",
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 16,
            "messages": [{"role": "user", "content": "ping"}],
        },
        headers=api_key_headers,
    )
    assert resp.status_code == 200


def test_messages_blocks_content(client, api_key_headers):
    resp = client.post(
        "/v1/messages",
        json={
            "model": "claude-3-5-sonnet-latest",
            "max_tokens": 16,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "hello in blocks"}],
                }
            ],
        },
        headers=api_key_headers,
    )
    assert resp.status_code == 200


def test_missing_api_key_rejected(client):
    resp = client.post(
        "/v1/messages",
        json={"model": "claude-3-5-sonnet-latest", "max_tokens": 8, "messages": [{"role": "user", "content": "x"}]},
        headers={"anthropic-version": "2023-06-01", "Content-Type": "application/json"},
    )
    assert resp.status_code == 401
    body = resp.get_json()
    assert body["type"] == "error"
    assert body["error"]["type"] == "authentication_error"


def test_missing_anthropic_version_rejected(client, api_key):
    resp = client.post(
        "/v1/messages",
        json={"model": "claude-3-5-sonnet-latest", "max_tokens": 8, "messages": [{"role": "user", "content": "x"}]},
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["type"] == "error"
    assert body["error"]["type"] == "invalid_request_error"


def test_unknown_api_key_rejected(client):
    resp = client.post(
        "/v1/messages",
        json={"model": "claude-3-5-sonnet-latest", "max_tokens": 8, "messages": [{"role": "user", "content": "x"}]},
        headers={
            "x-api-key": "sk-ant-twin-not-a-real-key",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 401
    assert resp.get_json()["error"]["type"] == "authentication_error"


def test_missing_model_rejected(client, api_key_headers):
    resp = client.post(
        "/v1/messages",
        json={"max_tokens": 8, "messages": [{"role": "user", "content": "x"}]},
        headers=api_key_headers,
    )
    assert resp.status_code == 400


def test_missing_messages_rejected(client, api_key_headers):
    resp = client.post(
        "/v1/messages",
        json={"model": "claude-3-5-sonnet-latest", "max_tokens": 8},
        headers=api_key_headers,
    )
    assert resp.status_code == 400


def test_empty_messages_rejected(client, api_key_headers):
    resp = client.post(
        "/v1/messages",
        json={"model": "claude-3-5-sonnet-latest", "max_tokens": 8, "messages": []},
        headers=api_key_headers,
    )
    assert resp.status_code == 400


def test_missing_max_tokens_rejected(client, api_key_headers):
    resp = client.post(
        "/v1/messages",
        json={"model": "claude-3-5-sonnet-latest", "messages": [{"role": "user", "content": "x"}]},
        headers=api_key_headers,
    )
    assert resp.status_code == 400


def test_negative_max_tokens_rejected(client, api_key_headers):
    resp = client.post(
        "/v1/messages",
        json={
            "model": "claude-3-5-sonnet-latest",
            "max_tokens": -5,
            "messages": [{"role": "user", "content": "x"}],
        },
        headers=api_key_headers,
    )
    assert resp.status_code == 400


def test_cross_tenant_history_isolation(client, make_tenant):
    """An api-key from tenant A MUST NOT see tenant B's message history."""
    a = make_tenant()
    b = make_tenant()

    # Tenant A drives a messages call
    client.post(
        "/v1/messages",
        json={
            "model": "claude-3-5-sonnet-latest",
            "max_tokens": 16,
            "messages": [{"role": "user", "content": "tenant-a"}],
        },
        headers=a["api_key_headers"],
    )

    # Tenant B drives one of its own
    client.post(
        "/v1/messages",
        json={
            "model": "claude-3-5-sonnet-latest",
            "max_tokens": 16,
            "messages": [{"role": "user", "content": "tenant-b"}],
        },
        headers=b["api_key_headers"],
    )

    a_history = client.get("/_twin/messages", headers=a["tenant_headers"]).get_json()["messages"]
    b_history = client.get("/_twin/messages", headers=b["tenant_headers"]).get_json()["messages"]

    assert all(m["tenant_id"] == a["tenant_id"] for m in a_history)
    assert all(m["tenant_id"] == b["tenant_id"] for m in b_history)
    assert a_history and b_history


def test_cross_tenant_apikey_does_not_leak_other_tenants_logs(client, make_tenant):
    a = make_tenant()
    b = make_tenant()

    client.post(
        "/v1/messages",
        json={
            "model": "claude-3-5-sonnet-latest",
            "max_tokens": 16,
            "messages": [{"role": "user", "content": "tenant-a"}],
        },
        headers=a["api_key_headers"],
    )

    a_logs = client.get("/_twin/logs", headers=a["tenant_headers"]).get_json()["logs"]
    b_logs = client.get("/_twin/logs", headers=b["tenant_headers"]).get_json()["logs"]
    assert all(r["tenant_id"] == a["tenant_id"] for r in a_logs)
    assert all(r["tenant_id"] == b["tenant_id"] for r in b_logs)
