"""Shared fixtures for the Anthropic twin smoke tests.

Spins the twin up in-process via Flask's test client, with SQLite storage
and an in-process SQLiteTenantStore. No Docker or external services
needed.
"""

import base64
import os
import sys

import pytest

# twins_anthropic_local sibling lives inside this repo; put the repo root
# on sys.path so it can import from a checkout that has not been pip-installed.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from twins_anthropic.app import create_app  # noqa: E402
from twins_anthropic_local.storage_sqlite import SQLiteStorage  # noqa: E402
from twins_local.tenants import (  # noqa: E402
    SQLiteTenantStore,
    ensure_default_tenant,
    generate_tenant_id,
    generate_tenant_secret,
    hash_secret,
)


@pytest.fixture
def tenant_store(tmp_path):
    store = SQLiteTenantStore(db_path=str(tmp_path / "tenants.sqlite3"))
    ensure_default_tenant(store)
    return store


@pytest.fixture
def storage(tmp_path):
    return SQLiteStorage(db_path=str(tmp_path / "test_twin.db"))


@pytest.fixture
def twin_app(storage, tenant_store):
    app = create_app(
        storage=storage,
        tenants=tenant_store,
        config={"base_url": "http://localhost:8080"},
    )
    app.config["TESTING"] = True
    app._tenant_store = tenant_store  # type: ignore[attr-defined]
    app._storage = storage  # type: ignore[attr-defined]
    return app


@pytest.fixture
def client(twin_app):
    return twin_app.test_client()


def _basic_header(tenant_id: str, tenant_secret: str) -> dict:
    creds = base64.b64encode(f"{tenant_id}:{tenant_secret}".encode()).decode()
    return {"Authorization": f"Basic {creds}"}


@pytest.fixture
def tenant(tenant_store):
    tenant_id = generate_tenant_id()
    tenant_secret = generate_tenant_secret()
    tenant_store.create_tenant(
        tenant_id=tenant_id,
        secret_hash=hash_secret(tenant_secret),
        friendly_name="Test Tenant",
    )
    return {"tenant_id": tenant_id, "tenant_secret": tenant_secret}


@pytest.fixture
def tenant_headers(tenant):
    return _basic_header(tenant["tenant_id"], tenant["tenant_secret"])


def _mint_api_key(client, tenant_headers) -> str:
    resp = client.post(
        "/_twin/accounts",
        json={"kind": "api_key", "friendly_name": "Test Key"},
        headers=tenant_headers,
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return resp.get_json()["api_key"]


@pytest.fixture
def api_key(client, tenant_headers):
    return _mint_api_key(client, tenant_headers)


@pytest.fixture
def api_key_headers(api_key):
    return {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }


@pytest.fixture
def make_tenant(client, tenant_store):
    """Factory for additional tenants in cross-isolation tests."""

    def _make():
        tenant_id = generate_tenant_id()
        tenant_secret = generate_tenant_secret()
        tenant_store.create_tenant(
            tenant_id=tenant_id,
            secret_hash=hash_secret(tenant_secret),
            friendly_name="t",
        )
        headers = _basic_header(tenant_id, tenant_secret)
        api_key = _mint_api_key(client, headers)
        return {
            "tenant_id": tenant_id,
            "tenant_headers": headers,
            "api_key": api_key,
            "api_key_headers": {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        }

    return _make
