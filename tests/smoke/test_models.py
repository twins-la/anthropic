"""``GET /v1/models[/{model_id}]``."""


def test_list_models(client, api_key_headers):
    resp = client.get("/v1/models", headers=api_key_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert isinstance(body["data"], list)
    assert body["has_more"] is False
    ids = [m["id"] for m in body["data"]]
    for expected in (
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
        "claude-3-5-sonnet-latest",
        "claude-3-5-haiku-latest",
        "claude-3-opus-latest",
    ):
        assert expected in ids
    assert body["first_id"] == ids[0]
    assert body["last_id"] == ids[-1]


def test_list_models_requires_auth(client):
    resp = client.get(
        "/v1/models",
        headers={"anthropic-version": "2023-06-01"},
    )
    assert resp.status_code == 401


def test_get_known_model(client, api_key_headers):
    resp = client.get("/v1/models/claude-opus-4-7", headers=api_key_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == "claude-opus-4-7"
    assert body["type"] == "model"


def test_get_unknown_model_returns_404(client, api_key_headers):
    resp = client.get("/v1/models/no-such-model", headers=api_key_headers)
    assert resp.status_code == 404
    body = resp.get_json()
    assert body["type"] == "error"
    assert body["error"]["type"] == "not_found_error"
