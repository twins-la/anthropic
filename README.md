# Anthropic Twin

A digital twin of the public [Anthropic Messages API](https://docs.anthropic.com/en/api/messages) for [twins.la](https://twins.la). Synthetic responses only — the twin never calls `api.anthropic.com`. The shape matches the real API verbatim, so consumer SDKs (`anthropic`, etc.) work without modification.

## What this is

- **`POST /v1/messages`** — full or SSE streaming via `stream: true`. Returns the canonical Messages API response shape (`id`, `type`, `role`, `content`, `model`, `stop_reason`, `stop_sequence`, `usage`).
- **`POST /v1/messages/count_tokens`** — returns `{input_tokens: N}` from a deterministic word-count heuristic.
- **`GET /v1/models`, `GET /v1/models/{id}`** — fixed model catalog at the platform's current cutoff.
- **Beta headers** — `prompt-caching-2024-07-31` (returns `cache_creation_input_tokens` / `cache_read_input_tokens` in `usage`) and `extended-thinking-...` (emits a `thinking` content block before `text`).

## Supported scenarios

See [`SCENARIOS.md`](SCENARIOS.md) for the full scope and authoritative references.

- `messages-api` — Messages API (full + streaming), count_tokens, models list, prompt-caching beta, extended-thinking beta.

## Usage

This package is not run directly. It is loaded by a host:

- **Local**: `twins-anthropic-local` (sibling package under `twins_anthropic_local/`) — run via `python -m twins_anthropic_local`.
- **Cloud**: available at [anthropic.twins.la](https://anthropic.twins.la).

## Quick Start (local)

```bash
pip install -e . ./twins_anthropic_local/
python -m twins_anthropic_local
```

Then drive a synthetic Messages API call:

```bash
# Bootstrap a tenant
curl -X POST http://localhost:8080/_twin/tenants \
  -H "Content-Type: application/json" \
  -d '{"friendly_name": "Dev"}'
# -> { "tenant_id": "...", "tenant_secret": "..." }

# Mint an api key for the tenant
curl -X POST http://localhost:8080/_twin/accounts \
  -u "TENANT_ID:TENANT_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"kind":"api_key","friendly_name":"Demo Key"}'
# -> { "api_key": "sk-ant-twin-...", "api_key_id": "...", ... }

# Call the Messages API
curl -X POST http://localhost:8080/v1/messages \
  -H "x-api-key: $API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-3-5-sonnet-latest","max_tokens":64,
       "messages":[{"role":"user","content":"hi"}]}'
# -> { "id":"msg_...", "type":"message", "role":"assistant",
#      "content":[{"type":"text","text":"[claude-3-5-sonnet-latest synthetic response] You said: hi"}],
#      "model":"...", "stop_reason":"end_turn", "usage":{...} }
```

The Twin Plane (`/_twin/*`) is documented in [twins-la/TWIN_PLANE.md](https://github.com/twins-la/twins-la/blob/main/TWIN_PLANE.md).

## Tests

```bash
pip install -e .[dev] ./twins_anthropic_local/
pytest tests/
```

## License

MIT — see [LICENSE](LICENSE).
