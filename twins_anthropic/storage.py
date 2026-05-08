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
    """Storage backend contract that hosts must implement."""

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
