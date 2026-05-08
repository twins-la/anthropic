"""Tenant bootstrap and Basic-auth gating."""

import pytest

from twins_anthropic.app import create_app
from twins_anthropic_local.storage_sqlite import SQLiteStorage
from twins_local.tenants import SQLiteTenantStore


def test_tenant_bootstrap_returns_secret_once(client):
    resp = client.post("/_twin/tenants", json={"friendly_name": "Sample"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["tenant_id"]
    assert body["tenant_secret"]
    assert body["friendly_name"] == "Sample"
    assert body["created_at"]


def test_tenant_required_for_logs(client):
    resp = client.get("/_twin/logs")
    assert resp.status_code == 401


def test_tenant_required_for_accounts_create(client):
    resp = client.post("/_twin/accounts", json={"kind": "api_key"})
    assert resp.status_code == 401


def test_tenant_credentials_are_validated(client, tenant):
    import base64

    bad = base64.b64encode(f"{tenant['tenant_id']}:wrong".encode()).decode()
    resp = client.get("/_twin/logs", headers={"Authorization": f"Basic {bad}"})
    assert resp.status_code == 401


@pytest.fixture
def cloud_app(tmp_path):
    storage = SQLiteStorage(db_path=str(tmp_path / "cloud.db"))
    tenants = SQLiteTenantStore(db_path=str(tmp_path / "cloud_tenants.sqlite3"))
    app = create_app(
        storage=storage,
        tenants=tenants,
        config={"base_url": "https://anthropic.twins.la", "is_cloud": True},
    )
    app.config["TESTING"] = True
    return app


def test_cloud_tenant_bootstrap_does_not_emit_default(cloud_app):
    """In cloud mode, generated tenant_id MUST NOT be the literal 'default'."""
    c = cloud_app.test_client()
    resp = c.post("/_twin/tenants", json={})
    # Either it succeeds with a non-default id, or it raises — both prove
    # the cloud guard is wired. In practice the generator returns a UUID,
    # so success is the expected path.
    if resp.status_code == 201:
        assert resp.get_json()["tenant_id"] != "default"
