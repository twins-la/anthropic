"""Sweep test: unknown ``/v1/<rest>`` paths return Anthropic-shaped JSON 404.

Closes twins-la/twins-la#2 (anthropic half): without the catch-all in
``routes/api_data.py``, Flask falls through to its default HTML 404 on
any unimplemented endpoint, which breaks SDK consumers.

Path-agnostic sweep — asserts the rendered envelope rather than
enumerating expected misses.
"""

import pytest


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "v1/foo"),
        ("POST", "v1/messages-misspell"),
        ("GET", "v1/Models"),  # mixed case
        ("DELETE", "v1/random/nested/path"),
        ("PUT", "v1/files/abc"),
        ("PATCH", "v1/no-such-resource"),
    ],
)
def test_unknown_v1_path_returns_json_404(client, method, path):
    full = f"/{path}"
    resp = client.open(
        full,
        method=method,
        json={"foo": "bar"} if method in ("POST", "PUT", "PATCH") else None,
    )
    assert resp.status_code == 404, f"{method} {full} got {resp.status_code}"
    assert resp.headers["Content-Type"].startswith("application/json"), (
        f"{method} {full} returned {resp.headers.get('Content-Type')!r} "
        f"body={resp.get_data(as_text=True)[:200]!r}"
    )
    body = resp.get_json()
    assert body is not None and "type" in body
    assert body["type"] == "error"
    assert body["error"]["type"] == "not_found_error"


def test_unknown_v1_path_no_html_leak(client):
    """Belt-and-braces: HTML 404 must never appear on any /v1/* miss."""
    resp = client.get("/v1/literally-anything")
    body = resp.get_data(as_text=True)
    assert "<!doctype" not in body.lower()
