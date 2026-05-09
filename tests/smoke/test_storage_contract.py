"""Structural guard for the cold-start signing-key race class.

Closes twins-la/anthropic#1: this twin currently has no signing-key surface,
so there is no get-then-put primitive to fix today. This test is the
forward-looking guard: if a future PR adds `get_signing_key` or
`put_signing_key` without also adding the atomic
`get_or_create_signing_key`, the test fails — preserving the
race-safe pattern documented in `twins_anthropic/storage.py`'s
concurrency contract.

The pattern is implemented in twins-la/aoai and
twins-la/microsoft-bot-framework — see those repos' storage modules
for the canonical implementation.
"""

from twins_anthropic.storage import TwinStorage


def test_signing_key_methods_require_atomic_get_or_create():
    """If signing-key methods are added to the ABC, the atomic primitive must
    exist alongside them.
    """
    methods = {
        m for m in dir(TwinStorage)
        if not m.startswith("_") and callable(getattr(TwinStorage, m, None))
    }
    has_get = "get_signing_key" in methods
    has_put = "put_signing_key" in methods
    has_atomic = "get_or_create_signing_key" in methods

    if has_get or has_put:
        assert has_atomic, (
            "twins_anthropic.storage.TwinStorage now exposes a signing-key "
            "surface (get_signing_key or put_signing_key) but is missing "
            "`get_or_create_signing_key`. Adding get/put without the atomic "
            "primitive re-introduces the cold-start race documented in "
            "twins-la/anthropic#1. See the concurrency contract in "
            "twins_anthropic/storage.py and the canonical implementation in "
            "twins-la/aoai's storage layer."
        )


def test_storage_concurrency_contract_documented():
    """The TwinStorage class docstring must mention the concurrency contract.

    A future maintainer who removes the contract section from the docstring
    must also confront whether the rule itself is still required — and this
    test forces that confrontation rather than allowing silent doc rot.
    """
    docstring = TwinStorage.__doc__ or ""
    assert "Concurrency contract" in docstring, (
        "TwinStorage.__doc__ must contain the 'Concurrency contract' section "
        "that names the get_or_create_<x> pattern. See twins-la/anthropic#1."
    )
    assert "get_or_create" in docstring, (
        "TwinStorage.__doc__ must reference the get_or_create_<x> primitive "
        "by name in the concurrency contract section."
    )
