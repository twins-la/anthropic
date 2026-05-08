"""Log records emitted by the twin must satisfy LOGGING.md §3.2."""

from twins_local.logs import VALID_OUTCOMES, VALID_PLANES


def _conformant(record: dict) -> None:
    """Strict §3.2 check — same vocabulary as bf + telegram + twilio."""
    required = {
        "timestamp",
        "twin",
        "tenant_id",
        "correlation_id",
        "plane",
        "operation",
        "resource",
        "outcome",
        "reason",
        "details",
    }
    assert required.issubset(record.keys()), record
    assert record["twin"] == "anthropic"
    assert record["plane"] in VALID_PLANES
    assert record["outcome"] in VALID_OUTCOMES
    if record["outcome"] == "failure":
        assert record["reason"] and isinstance(record["reason"], str)
    assert isinstance(record["details"], dict)


def test_account_create_emits_normative_log(client, tenant, tenant_headers):
    client.post(
        "/_twin/accounts",
        json={"kind": "api_key", "friendly_name": "Test"},
        headers=tenant_headers,
    )
    logs = client.get("/_twin/logs", headers=tenant_headers).get_json()["logs"]
    assert logs
    for record in logs:
        _conformant(record)
    creates = [r for r in logs if r["operation"] == "twin.account.create"]
    assert creates


def test_messages_create_emits_normative_log(client, tenant_headers, api_key_headers):
    client.post(
        "/v1/messages",
        json={
            "model": "claude-3-5-sonnet-latest",
            "max_tokens": 16,
            "messages": [{"role": "user", "content": "hi"}],
        },
        headers=api_key_headers,
    )
    logs = client.get("/_twin/logs", headers=tenant_headers).get_json()["logs"]
    for record in logs:
        _conformant(record)
    creates = [r for r in logs if r["operation"] == "data.messages.create"]
    assert creates
    assert creates[0]["resource"]["type"] == "message"
