"""Identifier generators for the Anthropic twin.

Real Anthropic message ids look like ``msg_01ABCxyz...``; api keys look
like ``sk-ant-api03-...``. The twin matches the format closely so
consumer code that parses or compares these does not need to special-case
the twin.
"""

import secrets


def generate_message_id() -> str:
    """Bare message id; the response builder prefixes ``msg_``."""
    return secrets.token_urlsafe(16)


def generate_api_key() -> str:
    """An Anthropic-shaped api key: ``sk-ant-twin-<random>``."""
    return f"sk-ant-twin-{secrets.token_urlsafe(40)}"


def generate_api_key_id() -> str:
    return f"apikey_{secrets.token_urlsafe(12)}"


def generate_feedback_id() -> str:
    return f"fb_{secrets.token_urlsafe(12)}"
