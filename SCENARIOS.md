# Anthropic Twin — Supported Scenarios

The twin emulates the public Anthropic Messages API surface with synthetic, deterministic responses. The response shape is byte-for-byte the same as the real API — consumer SDKs that parse responses (`anthropic`, etc.) work without modification — but the *content* is a stub that echoes the prompt, so no live credits are consumed and no quota is hit.

## `messages-api` (Supported)

Within this scenario, code that issues Messages API traffic against this twin behaves the same way (response-shape-wise) as it does against `api.anthropic.com`.

### Scope

**In scope:**

- `POST /v1/messages` (non-streaming) — full Anthropic Messages API response with `id`, `type`, `role`, `content`, `model`, `stop_reason`, `stop_sequence`, `usage`.
- `POST /v1/messages` with `stream: true` — Server-Sent Events sequence: `message_start`, `content_block_start`, `content_block_delta+`, `content_block_stop`, `message_delta`, `message_stop` (plus `thinking_delta` blocks under the extended-thinking beta).
- `POST /v1/messages/count_tokens` — returns `{input_tokens: N}` from a deterministic word-count heuristic.
- `GET /v1/models` — list with `data`, `has_more`, `first_id`, `last_id`. Catalog: `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`, `claude-3-5-sonnet-latest`, `claude-3-5-haiku-latest`, `claude-3-opus-latest`.
- `GET /v1/models/{model_id}` — single model lookup; 404 with `not_found_error` envelope on unknown id.
- `anthropic-version` header (any `YYYY-MM-DD` value) is required and validated for presence.
- `anthropic-beta: prompt-caching-2024-07-31` — accepts `cache_control: {type: "ephemeral"}` on content blocks; returns `cache_creation_input_tokens` and `cache_read_input_tokens` in `usage` (synthetic split: first call always creates).
- `anthropic-beta: extended-thinking-...` — accepts `thinking: {type: "enabled", budget_tokens: N}` in the request body; emits a `thinking` content block before the `text` block.
- Authentication: `x-api-key` header (case-insensitive). Keys are minted via `POST /_twin/accounts` per tenant.

**Out of scope (behaviour may be fabricated or absent):**

- Real model inference. Responses are deterministic synthetic text that echoes the last user message; no real LLM is contacted.
- Files API (`/v1/files`).
- Batches API (`/v1/messages/batches`).
- Computer-use, code-execution, citations.
- Vision: image content blocks are accepted in the request shape but not interpreted (the twin records them in history without analysing).
- Tool-use loops are accepted as input but the synthetic response does not actually invoke tools; the response is always plain text (plus optional `thinking`).
- Real prompt-caching semantics (TTL, hit/miss decisions). The twin always reports the marked blocks as `cache_creation` on every call.

## Authoritative References

- Anthropic Messages API — https://docs.anthropic.com/en/api/messages (retrieved 2026-05-08)
- Anthropic Messages API — Streaming — https://docs.anthropic.com/en/api/messages-streaming (retrieved 2026-05-08)
- Anthropic Messages API — Count Tokens — https://docs.anthropic.com/en/api/messages-count-tokens (retrieved 2026-05-08)
- Anthropic Models API — List Models — https://docs.anthropic.com/en/api/models-list (retrieved 2026-05-08)
- Anthropic — Prompt Caching — https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching (retrieved 2026-05-08)
- Anthropic — Extended Thinking — https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking (retrieved 2026-05-08)

### Version

- 0.1.0 — Initial release. Messages API (full + SSE streaming), count_tokens, models list, prompt-caching and extended-thinking betas. Synthetic deterministic responses; consumer SDK shape-fidelity verified.
