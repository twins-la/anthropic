"""Local-host configuration. Values come from the environment so the
container deployment can override them without code changes."""

import os
from pathlib import Path

DB_PATH = os.environ.get(
    "TWIN_DB_PATH", str(Path.home() / ".twins" / "anthropic.sqlite3")
)
HOST = os.environ.get("TWIN_HOST", "0.0.0.0")
PORT = int(os.environ.get("TWIN_PORT", "8080"))
BASE_URL = os.environ.get("TWIN_BASE_URL", f"http://localhost:{PORT}")
ADMIN_TOKEN = os.environ.get("TWIN_ADMIN_TOKEN", "")
