"""Abstract storage interface for the Anthropic twin.

Hosts (local SQLite, cloud Postgres) implement this contract. The twin
package never imports a specific database driver.

Resources:

* ``api_keys`` — per-tenant Anthropic-style api keys (header ``x-api-key``).
* ``messages`` — request+response history for ``POST /v1/messages``.
* ``feedback`` — operator feedback queue (cross-cutting).
* ``logs`` — operation log (LOGGING.md §3.2 records).
"""

from abc import ABC, abstractmethod
from typing import Optional


class TwinStorage(ABC):
    """Storage backend contract that hosts must implement.

    Concurrency contract — read-then-write semantics:
        If a future resource needs "load existing or create new" behavior
        (e.g., a per-tenant signing keypair), do NOT split the operation
        into separate `get_<x>` and `put_<x>` storage methods invoked from
        the caller. The window between the unlocked SELECT and the put is
        enough for two concurrent first-time callers to both observe "no
        key" and both generate, producing transient duplicate state.

        Define a single atomic `get_or_create_<x>(self, key, generator)`
        storage method that holds `self._lock` across the entire
        check-and-create (SQLite) or `pg_advisory_xact_lock(hashtext(...))`
        within a single transaction (Postgres).

        See twins-la/aoai#2 + twins-la/microsoft-bot-framework#2 for the
        canonical implementation; twins-la/anthropic#1 documents the
        audit that confirmed this twin currently has no get-then-put
        primitive to fix. The forward-looking guard is enforced by
        tests/smoke/test_storage_contract.py — adding `get_signing_key`
        or `put_signing_key` without `get_or_create_signing_key` fails
        the test suite.
    """

    # -- API keys --

    @abstractmethod
    def create_api_key(
        self,
        *,
        tenant_id: str,
        key_id: str,
        key_hash: str,
        friendly_name: str,
    ) -> dict:
        """Persist an api-key record. Returns the stored row."""

    @abstractmethod
    def get_api_key_by_hash(self, key_hash: str) -> Optional[dict]:
        """Look up an api-key by its hash. Returns row or ``None``."""

    @abstractmethod
    def list_api_keys(self, *, tenant_id: Optional[str] = None) -> list[dict]:
        """List api-keys; ``tenant_id=None`` returns all (admin only)."""

    @abstractmethod
    def delete_api_key(self, key_id: str) -> None:
        """Delete an api-key by id. No-op if absent."""

    # -- Messages history --

    @abstractmethod
    def create_message(self, data: dict) -> dict:
        """Persist a request+response history row.

        ``data`` carries: ``id``, ``tenant_id``, ``model``,
        ``request_json``, ``response_json``, ``beta_headers``,
        ``date_created``.
        """

    @abstractmethod
    def get_message(self, message_id: str) -> Optional[dict]:
        """Fetch a message by id."""

    @abstractmethod
    def list_messages(
        self,
        *,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """List messages, optionally scoped by tenant."""

    # -- Feedback --

    @abstractmethod
    def create_feedback(self, data: dict) -> dict:
        """Persist a feedback record."""

    @abstractmethod
    def get_feedback(self, feedback_id: str) -> Optional[dict]:
        """Fetch a feedback record by id."""

    @abstractmethod
    def list_feedback(
        self,
        *,
        status: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> list[dict]:
        """List feedback, optionally filtered."""

    @abstractmethod
    def update_feedback(self, feedback_id: str, updates: dict) -> Optional[dict]:
        """Mutate a feedback record. Returns the updated dict or None."""

    # -- Logs --

    @abstractmethod
    def append_log(self, entry: dict) -> None:
        """Append an operation log entry. ``entry`` carries ``tenant_id``."""

    @abstractmethod
    def list_logs(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        tenant_id: Optional[str] = None,
    ) -> list[dict]:
        """Retrieve operation logs, optionally scoped to a tenant."""
