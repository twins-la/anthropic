"""Explainer landing page + agent instructions for the Anthropic twin.

Serves:
  GET /                          — HTML explainer page for humans and agents
  GET /_twin/agent-instructions  — Plain-text agent instructions (lives in
                                    twin_plane/routes.py)
"""

from flask import Blueprint

explainer_bp = Blueprint("explainer", __name__)

AGENT_INSTRUCTIONS = """\
# Anthropic Messages API Twin — anthropic.twins.la

A digital twin of the public Anthropic Messages API. Synthetic responses
only — the twin never calls api.anthropic.com. The shape matches the
real API verbatim, so consumer SDKs work without modification.

## Authentication

Twin Plane: HTTP Basic (tenant_id:tenant_secret)
  Bootstrap a tenant first:
    POST /_twin/tenants -> {tenant_id, tenant_secret}

Twin Plane Admin: Bearer token (set by deployment owner)
  Authorization: Bearer <admin_token>
  Or: X-Twin-Admin-Token: <admin_token>

Provider (data plane):
  x-api-key: sk-ant-twin-...    (mint via POST /_twin/accounts)
  anthropic-version: 2023-06-01 (any value accepted)

  Optional:
  anthropic-beta: prompt-caching-2024-07-31
  anthropic-beta: extended-thinking-2025-01-15

## Key Endpoints

Twin Plane (no auth):
  GET  /_twin/health
  GET  /_twin/scenarios
  GET  /_twin/settings
  GET  /_twin/references
  GET  /_twin/agent-instructions
  POST /_twin/tenants

Twin Plane (Basic tenant_id:tenant_secret):
  POST /_twin/accounts            — kind=api_key — returns {api_key} once
  GET  /_twin/accounts            — list api keys (masked)
  GET  /_twin/messages            — message history for this tenant
  GET  /_twin/logs
  POST /_twin/feedback
  GET  /_twin/feedback

Provider (x-api-key + anthropic-version):
  POST /v1/messages               — full or SSE streaming via stream:true
  POST /v1/messages/count_tokens
  GET  /v1/models
  GET  /v1/models/<model_id>

## Quick Start (local)

1. pip install twins-anthropic twins-anthropic-local
   python -m twins_anthropic_local

2. Bootstrap a tenant:
   curl -X POST http://localhost:8080/_twin/tenants \\
     -H "Content-Type: application/json" \\
     -d '{"friendly_name": "Dev"}'
   # -> { tenant_id, tenant_secret }

3. Mint an api key:
   curl -X POST http://localhost:8080/_twin/accounts \\
     -u "TENANT_ID:TENANT_SECRET" \\
     -H "Content-Type: application/json" \\
     -d '{"kind":"api_key","friendly_name":"Demo Key"}'
   # -> { api_key, api_key_id, ... }

4. Call the Messages API:
   curl -X POST http://localhost:8080/v1/messages \\
     -H "x-api-key: $API_KEY" \\
     -H "anthropic-version: 2023-06-01" \\
     -H "Content-Type: application/json" \\
     -d '{"model":"claude-3-5-sonnet-latest","max_tokens":64,
          "messages":[{"role":"user","content":"hi"}]}'
   # -> { id, type:"message", role:"assistant", content:[{type:"text",...}], ... }

## Reference

GitHub:           https://github.com/twins-la/anthropic
Project overview: https://twins.la
All twins:        https://github.com/twins-la/twins-la
"""


EXPLAINER_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>anthropic.twins.la &mdash; Anthropic Messages API Twin</title>
    <link rel="icon" type="image/png" href="https://twins.la/twins.png">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            min-height: 100vh;
            background: #f8f8f8;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            color: #374151;
            padding: 4rem 2rem;
            line-height: 1.7;
        }
        main { max-width: 700px; margin: 0 auto; }
        h1 {
            font-size: clamp(2rem, 5vw, 3rem);
            font-weight: 600;
            letter-spacing: -0.03em;
            color: #1a2e4a;
            margin-bottom: 0.5rem;
        }
        h1 .anthropic { color: #cc785c; }
        .tagline { font-size: 1.1rem; color: #6b7280; margin-bottom: 2.5rem; font-weight: 300; }
        h2 {
            font-size: 1.25rem;
            font-weight: 600;
            color: #1a2e4a;
            margin: 2rem 0 0.75rem;
            letter-spacing: -0.01em;
        }
        p { margin-bottom: 1rem; color: #6b7280; }
        p strong { color: #1a2e4a; }
        a { color: #cc785c; text-decoration: none; }
        a:hover { color: #a45d44; text-decoration: underline; }
        ul { list-style: none; padding: 0; margin-bottom: 1rem; }
        ul li { padding: 0.3rem 0; color: #6b7280; }
        ul li::before { content: "\\2192  "; color: #cc785c; }
        code {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85em;
            background: #f3f4f6;
            padding: 0.15em 0.4em;
            border-radius: 4px;
            color: #1a2e4a;
            border: 1px solid #e5e7eb;
        }
        .snippet-box {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 1.5rem;
            margin: 1rem 0;
            position: relative;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        .snippet-box pre {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: #6b7280;
            white-space: pre-wrap;
            word-break: break-word;
            line-height: 1.5;
            max-height: 400px;
            overflow-y: auto;
        }
        .copy-btn {
            position: absolute;
            top: 0.75rem;
            right: 0.75rem;
            background: #f3f4f6;
            color: #6b7280;
            border: 1px solid #e5e7eb;
            padding: 0.3rem 0.7rem;
            border-radius: 6px;
            font-size: 0.75rem;
            cursor: pointer;
            font-family: 'Inter', sans-serif;
            transition: background 0.15s, color 0.15s;
        }
        .copy-btn:hover { background: #1a2e4a; color: #ffffff; }
        .links { margin-top: 2.5rem; padding-top: 1.5rem; border-top: 1px solid #e5e7eb; }
        .links a { margin-right: 1.5rem; font-size: 0.9rem; }
        footer { margin-top: 3rem; color: #6b7280; font-size: 0.8rem; }
        footer .dot { color: #cc785c; }
        .breadcrumb { margin-bottom: 0.5rem; font-size: 0.85rem; }
        .breadcrumb a { color: #0e7490; }
        .breadcrumb a:hover { color: #1a2e4a; }
    </style>
</head>
<body>
    <main>
        <p class="breadcrumb"><a href="https://twins.la">twins.la</a></p>
        <h1><span class="anthropic">anthropic</span>.twins.la</h1>
        <p class="tagline">A digital twin of the Anthropic Messages API.</p>

        <h2>What is this?</h2>
        <p>
            A high-fidelity digital twin of the public Anthropic Messages
            API. The twin returns synthetic, deterministic responses that
            match the real API's shape exactly &mdash; consumer SDKs
            (<code>anthropic</code>, etc.) work without modification.
        </p>
        <p>
            Use it to prototype, run CI, or test integrations without
            burning live credits or hitting quotas.
        </p>

        <h2>Supported scenarios</h2>
        <ul>
            <li><code>messages-api</code> &mdash; <code>POST /v1/messages</code> (full + SSE streaming), <code>POST /v1/messages/count_tokens</code>, <code>GET /v1/models[/{id}]</code>, plus <code>prompt-caching-2024-07-31</code> and <code>extended-thinking</code> beta headers.</li>
        </ul>

        <h2>How to use it</h2>
        <p>
            <strong>Cloud:</strong> Mint an api key via
            <code>POST /_twin/accounts</code> on
            <code>https://anthropic.twins.la</code>, then point your
            Anthropic SDK at the twin's base URL.
        </p>
        <p>
            <strong>Local:</strong> Install with
            <code>pip install twins-anthropic-local</code> and run a local
            instance on any port. Same API, same behaviour, your machine.
        </p>

        <h2>For agents</h2>
        <p>
            Copy this into your agent's system prompt, tool configuration, or
            CLAUDE.md. Also available as plain text at
            <a href="/_twin/agent-instructions"><code>/_twin/agent-instructions</code></a>.
        </p>
        <div class="snippet-box">
            <button class="copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('agent-snippet').textContent).then(()=>{this.textContent='Copied!';setTimeout(()=>this.textContent='Copy',1500)})">Copy</button>
            <pre id="agent-snippet">""" + AGENT_INSTRUCTIONS.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + """</pre>
        </div>

        <div class="links">
            <a href="https://github.com/twins-la/anthropic">GitHub</a>
            <a href="https://twins.la">twins.la</a>
            <a href="/_twin/health">Health</a>
            <a href="/_twin/scenarios">Scenarios</a>
        </div>

        <footer>twins.la <span class="dot">&middot;</span> Where agents meet their environment.</footer>
    </main>
</body>
</html>
"""


@explainer_bp.route("/", methods=["GET"])
def explainer_page():
    return EXPLAINER_HTML
