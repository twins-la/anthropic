"""``POST /v1/messages/count_tokens``."""


def test_count_tokens_happy(client, api_key_headers):
    resp = client.post(
        "/v1/messages/count_tokens",
        json={
            "model": "claude-3-5-sonnet-latest",
            "messages": [{"role": "user", "content": "hello world"}],
        },
        headers=api_key_headers,
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert "input_tokens" in body
    assert body["input_tokens"] >= 1


def test_count_tokens_empty_messages_returns_minimum(client, api_key_headers):
    resp = client.post(
        "/v1/messages/count_tokens",
        json={"model": "claude-3-5-sonnet-latest", "messages": []},
        headers=api_key_headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()["input_tokens"] == 1


def test_count_tokens_requires_auth(client):
    resp = client.post(
        "/v1/messages/count_tokens",
        json={"model": "claude-3-5-sonnet-latest", "messages": []},
        headers={"anthropic-version": "2023-06-01", "Content-Type": "application/json"},
    )
    assert resp.status_code == 401


def test_count_tokens_missing_model_rejected(client, api_key_headers):
    resp = client.post(
        "/v1/messages/count_tokens",
        json={"messages": []},
        headers=api_key_headers,
    )
    assert resp.status_code == 400
