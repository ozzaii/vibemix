# Phase 5: FastAPI Proxy + Install-UUID JWT - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up the production security firewall that keeps the raw Gemini `AIza...` key off every distributed binary. After Phase 5:
- A FastAPI proxy lives in `proxy/` (deployable separately to `api.altidus.world` via Docker on Bravoh's existing 77.42.28.93 server).
- The proxy gates LLM streaming and TTS calls with install-UUID JWTs, slowapi rate limiting (60 rpm / 2000 rpd per UUID), and Redis-backed daily quota tracking.
- vibemix client gains a "proxy" mode alongside the "direct" mode (v4 compatibility kept) — `build_llm(mode, ...)` and `build_tts_chain(mode, ...)` route to either path.
- On first launch, vibemix mints a fresh `install_uuid` (UUIDv4) and stores it in the OS keychain via `keyring`. The proxy issues a long-lived JWT signed by the proxy's secret; the client caches it (also keychain).
- Direct path stays in repo as opt-in (`VIBEMIX_LLM_MODE=direct`), but the default and the Phase 11 calibration wizard / Phase 18 binary both use proxy mode.

**In scope:**
- `proxy/` package (separate Python project — own `pyproject.toml`, own venv). Endpoints, JWT issuance, JWT verification middleware, slowapi rate limiter, Redis quota, structured logging, OpenAPI docs.
  - `proxy/app/main.py` — FastAPI app
  - `proxy/app/routes/llm.py` — `POST /api/vibemix/v1/llm/generate` (multimodal streaming proxy for `gemini-3-flash-preview`)
  - `proxy/app/routes/tts.py` — `POST /api/vibemix/v1/tts/synthesize` (proxies both OpenRouter `google/gemini-3.1-flash-tts-preview` and Gemini native TTS fallbacks)
  - `proxy/app/routes/register.py` — `POST /api/vibemix/v1/register` — accepts `install_uuid` (client-generated), returns JWT
  - `proxy/app/middleware/auth.py` — JWT bearer verification (PyJWT)
  - `proxy/app/middleware/rate_limit.py` — slowapi instance bound to `install_uuid`
  - `proxy/app/quota.py` — Redis daily-quota client (`vibemix:quota:<uuid>:<YYYYMMDD>` counter)
  - `proxy/app/upstream.py` — `genai.Client(api_key=GEMINI_KEY)` and `openai_plugin` clients (proxy's own keys)
  - `proxy/Dockerfile` + `proxy/docker-compose.yml` + `proxy/.env.example`
  - `proxy/tests/` — unit + integration tests using `httpx.AsyncClient` against ASGI app + `fakeredis`
- `src/vibemix/agent/install_uuid.py` — `get_or_create_install_uuid()` using `keyring` (macOS Keychain, Windows Credential Manager). Generates UUIDv4 on first call, caches in keychain at `vibemix.install_uuid` service.
- `src/vibemix/agent/proxy_client.py` — `build_proxy_genai_client(jwt, proxy_base_url)` and `build_proxy_tts_chain(jwt, proxy_base_url)`. Uses `genai.Client(http_options=types.HttpOptions(base_url=...))` (or equivalent SDK escape hatch) and `openai_plugin.TTS(base_url=...)`.
- `src/vibemix/agent/llm_factory.py` — extend `build_llm(api_key=None, *, mode="direct", proxy_base_url=None, jwt=None)` so callers can pick mode.
- `src/vibemix/agent/tts_chain.py` — same extension on `build_tts_chain(...)`.
- `src/vibemix/__main__.py` — read `VIBEMIX_LLM_MODE` env (default "proxy" for distributed binaries, "direct" for dev override). Default proxy_base_url = `https://api.altidus.world`.
- Tests for client side: keychain mocking, proxy URL injection, JWT header presence.
- `proxy/README.md` — deployment runbook (Docker compose up, env vars, nginx upstream, PM2 restart, log paths).

**Out of scope:**
- Actual deployment to `api.altidus.world` — Kaan deploys at his convenience. Phase 5 ships the code + runbook; deployment is operational work.
- nginx config in this repo — lives in Bravoh's infra (`/etc/nginx/sites-available/api.altidus.world` already exists).
- Per-user account system / login UI — install-UUID is the only identifier; no email/password. Phase 20+ may revisit if abuse patterns demand.
- Per-user dashboards / usage analytics UI — Phase 5 logs structured usage; surfacing is future work.
- BYO-key feature ("use my own Gemini key") — Phase 5 ships proxy-only for distributed users; opt-in BYO-key is post-v1.
- OpenRouter direct usage by clients — Phase 5 routes ALL OpenRouter calls through the proxy too (so `OPENROUTER_API_KEY` also stays server-side).

</domain>

<decisions>
## Implementation Decisions

### Proxy stack (locked)
- **Framework:** FastAPI ≥0.115 (Bravoh already uses FastAPI — consistent stack).
- **Server:** `uvicorn[standard]` for production. Single-process behind nginx (Bravoh's existing pattern).
- **Async:** all routes async. Upstream Gemini/OpenRouter calls use `genai.Client.aio` and `httpx.AsyncClient`.
- **Auth:** `PyJWT` (Bravoh stack default). HS256 with proxy-side `JWT_SECRET` env var.
- **Rate limit:** `slowapi` ≥0.1.9. Key function: `lambda req: req.state.install_uuid` (set by JWT middleware).
- **Quota:** Redis (Bravoh already runs Redis at the server). Key pattern `vibemix:quota:<uuid>:<YYYYMMDD>`. INCR with EXPIRE-on-create (24h TTL).
- **Telemetry:** Python `logging` with JSON formatter. One log line per request with `install_uuid`, route, status, latency_ms, tokens_in, tokens_out (when available).

### Client-side UUID + JWT (locked)
- **Library:** `keyring` ≥25.0 — cross-platform OS keychain. macOS Keychain + Windows Credential Manager out-of-box. Linux excluded from v1 anyway.
- **Service/account naming:** service=`"vibemix"`, account=`"install_uuid"` and `"jwt"`.
- **UUID format:** UUIDv4 (`uuid.uuid4().hex` — 32 lowercase hex chars).
- **JWT contents:** `{"install_uuid": "...", "iat": ..., "exp": ... (90 days)}`. Long-lived because there's no user login flow; rotation happens client-side when JWT < 7 days from expiry.
- **JWT refresh:** Client calls `/api/vibemix/v1/register` again with current install_uuid (idempotent). Proxy returns a fresh JWT.

### Endpoint shapes (locked, designed for minimum vibemix-side change)
- `POST /api/vibemix/v1/register` — request: `{"install_uuid": "<32 hex>", "client_version": "0.1.0"}`. Response: `{"jwt": "...", "expires_at": "...", "quota_daily": 2000}`.
- `POST /api/vibemix/v1/llm/generate` — request: standard `genai.generate_content_stream` request body (model, contents with Parts including audio/image, config). Bearer header `Authorization: Bearer <jwt>`. Response: streaming SSE matching upstream Gemini SSE shape so the client SDK works unmodified IF possible. (Research question: can genai.Client be pointed at a custom base_url and reuse its SDK?)
- `POST /api/vibemix/v1/tts/synthesize` — request: `{"text": "...", "model": "google/gemini-3.1-flash-tts-preview" | "gemini-3.1-flash-tts-preview" | ...}`. Bearer auth. Response: streaming PCM (24kHz mono int16) matching OpenRouter `response_format=pcm` shape.

### Rate limit + quota (locked from CONTEXT discuss / project decisions)
- Per-UUID: **60 requests/minute** (slowapi).
- Per-UUID: **2000 requests/day** (Redis INCR + EXPIRE 24h).
- Server-wide circuit breaker: if Gemini/OpenRouter upstream returns 5xx for 10 consecutive requests, proxy returns 503 + `Retry-After: 60s` to clients for the next 60s. (Defends against billing accidents.)

### Deployment (documented, not automated this phase)
- Docker image: `vibemix-proxy:0.1.0` based on `python:3.12-slim`.
- `docker-compose.yml` ties proxy + Redis. Redis ALREADY runs on 77.42.28.93 — compose file uses external network in prod, internal `redis:7-alpine` for local dev.
- nginx config (NOT in this repo — Bravoh infra): adds `location /api/vibemix/ { proxy_pass http://127.0.0.1:8788; }`.
- PM2 process: `pm2 start "docker-compose up" --name vibemix-proxy` (or systemd unit — Kaan picks).
- Env vars: `GEMINI_API_KEY` (proxy-side), `OPENROUTER_API_KEY` (proxy-side), `JWT_SECRET` (proxy-side), `REDIS_URL`, `ALLOWED_ORIGINS` (CORS for any future web client).

### Client default (locked)
- `VIBEMIX_LLM_MODE` env: `"proxy"` for distributed binaries (Phase 18 installer sets this), `"direct"` for Kaan's dev loop (his current `.env` keys keep working).
- Default `VIBEMIX_PROXY_BASE_URL = "https://api.altidus.world"`.
- If `mode="proxy"` but `keyring` raises or proxy returns 401, log clear error and exit with actionable message — DO NOT silently fall back to direct (that would defeat the entire phase).

### Claude's Discretion
- Whether genai SDK supports `base_url` override (needs research). If yes → reuse SDK as-is, just point base_url at proxy. If no → client wraps `httpx.AsyncClient` directly with SSE parsing.
- Exact slowapi key extractor middleware ordering (needs verification — slowapi has known footguns with FastAPI middleware order).
- Whether to add CSRF for `/register` (probably no — it's an idempotent POST with a client-generated UUID; no cookie session).
- Test strategy for streaming SSE — `httpx.AsyncClient` with `aiter_bytes()` or recorded fixtures.
- Whether install_uuid generation should also stamp a `device_fingerprint` (CPU id, OS version) for anti-abuse — defer, leaving room for Phase 20 if abuse appears.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (from Phases 1-4)
- `src/vibemix/agent/llm_factory.py` already has `build_llm(api_key)` from Phase 4 — Phase 5 extends with `mode/proxy_base_url/jwt` params.
- `src/vibemix/agent/tts_chain.py` already has `build_tts_chain(gemini_key, openrouter_key)` from Phase 4 — Phase 5 extends similarly + the OpenRouter monkey-patch needs to apply EVEN IN proxy mode (the proxy issues SDK-shaped responses but the client TTS plugin still uses AudioChunkedStream).
- `src/vibemix/__main__.py` from Phase 4 wires env reads — Phase 5 adds VIBEMIX_LLM_MODE + VIBEMIX_PROXY_BASE_URL.
- `cohost_v4.py` reads `OPENROUTER_API_KEY` from `.env` — Phase 5 makes that optional (direct mode only) and routes proxy-mode clients to the proxy.

### Bravoh Infrastructure (CLAUDE.md)
- Server: `ssh altidus` → `77.42.28.93:2847`
- Redis: already running on server (Bravoh backend uses it).
- Nginx: already serving `api.altidus.world` (Bravoh API).
- PM2: already managing Bravoh services (`bravoh-api`, `bravoh-celery`).
- Pattern: vibemix proxy will be a NEW service alongside Bravoh, not embedded into Bravoh backend (clean separation — Bravoh launches March 2026 closed beta; vibemix proxy stays independently deployable).

### Integration Points
- **Phase 11 (Tauri shell)** — Tauri's Rust side reads the install_uuid from keychain via `tauri-plugin-keychain`. Hands off to Python sidecar. Phase 5's `install_uuid.py` is the Python-side counterpart.
- **Phase 18 (Distribution)** — installer build sets `VIBEMIX_LLM_MODE=proxy` baked into the bundle. Binary attack verification confirms zero `AIza` in `strings` output (the whole point of Phase 5).
- **Phase 20 (Day-Zero Ops)** — CI deploys the proxy on tag push; second-responder rota watches proxy logs for 5xx spikes.

</code_context>

<specifics>
## Specific Ideas

- **JWT TTL of 90 days** is intentional — there's no user login, no rotation event other than client refresh. Long-lived JWT means even an offline client (90-min flight without WiFi at the start) can still issue tokens after reconnect.
- **slowapi key extractor** must run AFTER JWT middleware so `req.state.install_uuid` is set. Verify middleware ordering.
- **Redis quota key TTL of 24h** with INCR semantics — when key doesn't exist (first request of day), SET with EXPIRE; subsequent INCR doesn't reset TTL. Use `INCR` + `EXPIRE` pair atomically via pipeline.
- **Streaming SSE proxy** — the LLM endpoint must pass through Gemini's SSE stream so vibemix's `generate_content_stream` works unmodified IF possible. If genai SDK can't be pointed at a custom base_url, fall back to client-side `httpx.AsyncClient` SSE parsing — but that's a bigger client refactor.
- **TTS PCM streaming** — OpenRouter returns chunked PCM; proxy passes through as-is. Client's livekit-plugins-openai (with monkey-patch) consumes it as before.
- **OpenAPI docs** auto-generated at `/api/vibemix/v1/docs` (FastAPI default) — handy for debug.
- **Keyring graceful failure** — on macOS first launch, system may prompt user to allow Keychain access. If user denies, fall back to a local file at `~/Library/Application Support/vibemix/install_uuid` (Linux-equivalent path on Windows). Log clearly when this happens.

</specifics>

<deferred>
## Deferred Ideas

- BYO-key mode (user supplies own Gemini key) — post-v1
- Per-user dashboards / usage analytics UI — post-v1
- Web-based admin console for proxy ops — Phase 20+ if needed
- OAuth / passwordless login — not in v1; UUID is enough
- Anti-abuse heuristics beyond rate limit (device fingerprint, IP reputation) — Phase 20+ if abuse appears
- gRPC for upstream Gemini (HTTP/2 might be slightly faster) — premature; HTTP works
- Per-region proxy deployment for latency — single region (EU/Bravoh's server) is fine for v1
- BYOK for OpenRouter — same answer as above
- Subscription tiers / paid quotas — out of scope; free OSS forever

</deferred>
