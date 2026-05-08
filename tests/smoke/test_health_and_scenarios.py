"""Twin Plane info endpoints — health, scenarios, references, settings."""


def test_health(client):
    resp = client.get("/_twin/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["twin"] == "anthropic"
    assert body["version"] == "0.1.0"


def test_scenarios(client):
    resp = client.get("/_twin/scenarios")
    assert resp.status_code == 200
    scenarios = resp.get_json()["scenarios"]
    names = [s["name"] for s in scenarios]
    assert "messages-api" in names
    for s in scenarios:
        assert s["status"] == "supported"
        assert s["capabilities"]


def test_references_present_and_dated(client):
    resp = client.get("/_twin/references")
    assert resp.status_code == 200
    refs = resp.get_json()["references"]
    assert len(refs) >= 1
    for r in refs:
        assert r["title"]
        assert r["url"].startswith("https://")
        assert r["retrieved"]


def test_settings(client):
    resp = client.get("/_twin/settings")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["twin"] == "anthropic"
    assert body["version"] == "0.1.0"
    assert body["base_url"] == "http://localhost:8080"


def test_agent_instructions(client):
    resp = client.get("/_twin/agent-instructions")
    assert resp.status_code == 200
    assert resp.mimetype == "text/plain"
    body = resp.get_data(as_text=True)
    assert "anthropic" in body.lower()
    assert "/_twin/tenants" in body
    assert "/v1/messages" in body


def test_explainer_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "anthropic.twins.la" in body
