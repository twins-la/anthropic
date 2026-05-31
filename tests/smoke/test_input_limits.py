"""Resource-bound guards on the twin-plane surface (security hardening).

Covers TWAN-001 (limit clamp), TWAN-002 (MAX_CONTENT_LENGTH), and TWAN-004
(input length guards). Each test goes red if the corresponding guard is
removed from production.
"""


def test_list_logs_limit_is_clamped(client, tenant_headers):
    # Upper bound: an enormous limit is capped at 1000.
    resp = client.get("/_twin/logs?limit=10000000", headers=tenant_headers)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["limit"] == 1000


def test_list_logs_negative_limit_floored(client, tenant_headers):
    # A negative limit must not reach SQLite, where LIMIT -1 means unbounded.
    resp = client.get("/_twin/logs?limit=-1", headers=tenant_headers)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["limit"] == 1


def test_list_messages_limit_is_clamped(client, tenant_headers):
    resp = client.get("/_twin/messages?limit=10000000", headers=tenant_headers)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["limit"] == 1000


def test_oversize_request_body_rejected(client, tenant_headers):
    # Body larger than MAX_CONTENT_LENGTH (1 MB) → 413 before the handler runs.
    big = "x" * (1 * 1024 * 1024 + 1)
    resp = client.post(
        "/_twin/feedback",
        data='{"body": "' + big + '"}',
        content_type="application/json",
        headers=tenant_headers,
    )
    assert resp.status_code == 413, resp.get_data(as_text=True)


def test_tenant_friendly_name_length_guarded(client):
    # POST /_twin/tenants is public; an over-length friendly_name → 400.
    resp = client.post("/_twin/tenants", json={"friendly_name": "x" * 257})
    assert resp.status_code == 400, resp.get_data(as_text=True)


def test_account_friendly_name_length_guarded(client, tenant_headers):
    resp = client.post(
        "/_twin/accounts",
        json={"kind": "api_key", "friendly_name": "x" * 257},
        headers=tenant_headers,
    )
    assert resp.status_code == 400, resp.get_data(as_text=True)


def test_feedback_body_length_guarded(client, tenant_headers):
    resp = client.post(
        "/_twin/feedback", json={"body": "x" * 8193}, headers=tenant_headers
    )
    assert resp.status_code == 400, resp.get_data(as_text=True)


def test_feedback_category_length_guarded(client, tenant_headers):
    resp = client.post(
        "/_twin/feedback",
        json={"body": "ok", "category": "c" * 129},
        headers=tenant_headers,
    )
    assert resp.status_code == 400, resp.get_data(as_text=True)


def test_feedback_context_size_guarded(client, tenant_headers):
    resp = client.post(
        "/_twin/feedback",
        json={"body": "ok", "context": {"k": "v" * 5000}},
        headers=tenant_headers,
    )
    assert resp.status_code == 400, resp.get_data(as_text=True)
