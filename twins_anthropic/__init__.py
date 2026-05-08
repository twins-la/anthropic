"""Anthropic Messages API digital twin.

Emulates the public Anthropic Messages API surface — ``POST /v1/messages``
(both full and SSE-streaming responses), ``POST /v1/messages/count_tokens``,
and ``GET /v1/models[/{id}]`` — backed by deterministic synthetic
responses. The twin never calls ``api.anthropic.com``; it returns
canonical-shape fixtures so consumers can prototype, run CI, and exercise
the platform's multi-tenant Twin Plane on AI-shaped traffic without
burning live credits.

Beta-header surfaces (``anthropic-beta``):

* ``prompt-caching-2024-07-31`` — accepts ``cache_control`` on content
  blocks and returns ``cache_creation_input_tokens`` /
  ``cache_read_input_tokens`` in ``usage``.
* ``extended-thinking`` (any value with this prefix) — accepts
  ``thinking: {type, budget_tokens}`` and emits a ``thinking`` content
  block before the ``text`` block.
"""

__version__ = "0.1.0"
