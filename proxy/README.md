# vibemix proxy

> FastAPI gateway keeping the Gemini API key off vibemix's distributed binaries.

## What it does

Receives bearer-JWT-authenticated requests from vibemix clients and proxies them to upstream Gemini (LLM streaming + non-streaming) and OpenRouter (TTS PCM streaming) with the proxy's own API keys held server-side. The vibemix client binary never contains an `AIza...` key string.

- **`/api/vibemix/v1/register`** — install-UUID → JWT exchange (idempotent, IP-rate-limited).
- **`/v1beta/models/{model}:streamGenerateContent`** — Gemini LLM SSE pass-through (JWT-gated, per-UUID rate limited, daily quota enforced, circuit-broken).
- **`/v1beta/models/{model}:generateContent`** — non-streaming sibling.
- **`/v1/audio/speech`** — OpenAI-compatible TTS proxied to OpenRouter (chunked PCM stream).
- **`/healthz`** — unauthenticated liveness.

Rate limits: 60 rpm per install_uuid (configurable), 2000 rpd per install_uuid via Redis `INCR`+`EXPIRE NX`. Server-wide circuit breaker opens after 10 consecutive upstream 5xx and returns `503 + Retry-After: 60` for 60s.

## Architecture

```
                       VIBEMIX CLIENT (Python sidecar / Tauri)
                       ┌──────────────────────────────────────┐
                       │ install_uuid.py  →  keyring/file     │
                       │ jwt_cache.py     →  /register POST   │
                       │ proxy_client.py  →  genai.Client     │
                       │                     (base_url=proxy) │
                       └──────────────────────┬───────────────┘
                                              │ HTTPS + SSE
                                              ▼
                       ┌──────────────────────────────────────────┐
                       │ VIBEMIX PROXY  (FastAPI on 77.42.28.93)  │
                       │   nginx /v1beta + /v1 + /api/vibemix     │
                       │     → uvicorn 127.0.0.1:8788             │
                       │   JWTMiddleware (HS256, alg=none blocked)│
                       │   @limiter.limit(per-uuid)               │
                       │   QuotaClient (Redis INCR + EXPIRE NX)   │
                       │   CircuitBreaker (10 consec 5xx → 503)   │
                       └────────────┬──────────────────┬──────────┘
                                    │                  │
                                    ▼                  ▼
                 generativelanguage.googleapis.com   openrouter.ai
                       (Gemini, SSE)                  (PCM)
```

The proxy is an independent service alongside Bravoh's main app (bravoh-api / bravoh-celery) on the same Redis instance. The `vibemix:quota:*` key namespace keeps quota state isolated from Bravoh's keys.

## Prerequisites

- **Server**: Bravoh's existing 77.42.28.93 (`ssh altidus`).
- **Redis 7.0+**: required for the `EXPIRE key seconds NX` semantics (Pitfall 4). Verify on the server:
  ```bash
  redis-cli INFO server | grep redis_version
  ```
  If `redis_version < 7.0`, upgrade Redis OR use the LUA-script fallback documented in `.planning/phases/05-fastapi-proxy-install-uuid-jwt/05-RESEARCH.md` Q5.
- **Docker + Docker Compose**: already installed for Bravoh stack.
- **nginx**: already serving `api.altidus.world` for Bravoh. We add three `location` blocks (see below).
- **PM2** (or systemd): supervision for `docker start -a vibemix-proxy`.
- **Python 3.12** on the dev machine: `uv` runs commands locally.

## Local development

```bash
cd proxy
cp .env.example .env
# Edit .env — fill GEMINI_API_KEY, OPENROUTER_API_KEY (real values); generate JWT_SECRET:
python3 -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(64))" >> .env
# REDIS_URL — for local dev:
#   REDIS_URL=redis://localhost:6379/0
# (or use the bundled docker-compose to spin up a fresh redis:7-alpine)

uv sync
uv run uvicorn app.main:app --reload --port 8788
# Visit http://localhost:8788/docs for the OpenAPI explorer
```

For local end-to-end smoke with a vibemix client pointed at the local proxy:

```bash
# Terminal 1 — proxy
cd proxy && uv run uvicorn app.main:app --port 8788

# Terminal 2 — vibemix client in proxy mode
VIBEMIX_LLM_MODE=proxy VIBEMIX_PROXY_BASE_URL=http://localhost:8788 python -m vibemix
```

## Production deployment

1. **SSH to server**
   ```bash
   ssh altidus  # → 77.42.28.93:2847
   sudo mkdir -p /var/www/vibemix-proxy
   sudo chown $USER:$USER /var/www/vibemix-proxy
   cd /var/www/vibemix-proxy
   ```

2. **Sync source** (one-shot copy from dev machine; subsequent updates via git)
   ```bash
   # On dev machine
   cd /Users/ozai/projects/dj-set-ai/proxy
   rsync -avz --exclude .venv --exclude __pycache__ --exclude .env \
       ./ altidus:/var/www/vibemix-proxy/
   ```

3. **Server-side `.env`**
   ```bash
   cd /var/www/vibemix-proxy
   cp .env.example .env
   chmod 600 .env
   # Edit with nano/vim — paste real GEMINI_API_KEY, OPENROUTER_API_KEY.
   # Generate JWT_SECRET fresh:
   python3 -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(64))" >> .env
   # Point at Bravoh's existing Redis:
   #   REDIS_URL=redis://localhost:6379/0
   ```

4. **Build + run via Docker**
   ```bash
   docker build -t vibemix-proxy:0.1.0 .
   docker run -d --name vibemix-proxy \
     --network host \
     --env-file .env \
     --restart unless-stopped \
     vibemix-proxy:0.1.0
   ```
   Alternative via docker-compose (compose file uses an internal redis — override `REDIS_URL` if you point at Bravoh's Redis):
   ```bash
   docker compose up -d
   ```

5. **PM2 supervision** (optional — `--restart unless-stopped` on `docker run` already covers most cases)
   ```bash
   pm2 start "docker start -a vibemix-proxy" --name vibemix-proxy
   pm2 save
   pm2 startup  # one-time, follow the printed instructions
   ```

6. **nginx config** — add to `/etc/nginx/sites-available/api.altidus.world`:
   ```nginx
   # vibemix proxy locations (Phase 5 — RESEARCH Q6)
   location /v1beta/ {
       proxy_pass http://127.0.0.1:8788;
       proxy_buffering off;          # CRITICAL: SSE needs streaming (Pitfall 2)
       proxy_cache off;
       proxy_set_header Connection "";
       proxy_http_version 1.1;
       proxy_read_timeout 300s;
   }
   location /v1/ {
       proxy_pass http://127.0.0.1:8788;
       proxy_buffering off;
       proxy_set_header Connection "";
       proxy_http_version 1.1;
       proxy_read_timeout 300s;
   }
   location /api/vibemix/ {
       proxy_pass http://127.0.0.1:8788;
       proxy_set_header Connection "";
       proxy_http_version 1.1;
   }
   location = /healthz {
       proxy_pass http://127.0.0.1:8788/healthz;
   }
   ```
   Then: `sudo nginx -t && sudo nginx -s reload`.

7. **Smoke test** from any machine
   ```bash
   curl https://api.altidus.world/healthz
   # → {"status":"ok"}

   curl -X POST https://api.altidus.world/api/vibemix/v1/register \
     -H "Content-Type: application/json" \
     -d '{"install_uuid":"'$(python3 -c "import uuid; print(uuid.uuid4().hex)")'", "client_version":"0.1.0"}'
   # → {"jwt":"eyJ...","expires_at":"2026-08-09T...","quota_daily":2000}
   ```

## Observability

- Container logs: `docker logs -f vibemix-proxy`
- PM2 logs (if used): `pm2 logs vibemix-proxy`
- Structured-request logging: each route emits a `vibemix.proxy.*` logger line. Phase 5 ships minimal structured logging; Phase 20 may add Prometheus exporter + Bravoh dashboard integration.
- Health check probe (uptime watcher): `curl https://api.altidus.world/healthz` every 60s.

## JWT_SECRET rotation

Rotating `JWT_SECRET` invalidates ALL outstanding JWTs (90-day TTL × every active install). Procedure:

1. Generate new secret: `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`
2. Update `/var/www/vibemix-proxy/.env`: `JWT_SECRET=<new>`
3. Restart proxy: `docker restart vibemix-proxy` (or `pm2 restart vibemix-proxy`)
4. Clients hit `401` on next request → vibemix client's `get_or_refresh_jwt` detects the failure and POSTs `/register` again automatically (idempotent). Recovery is transparent to the user on next launch.

Rotate ONLY on suspected compromise (e.g., server breach, leaked `.env`). The 90-day TTL + per-UUID rate limit + 2000/day quota cap damage from any single leaked JWT to one install's daily budget.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| 404 on `/v1beta/models/.../streamGenerateContent` | nginx location block missing | Add the `/v1beta/` location block above |
| SSE chunks arrive batched (no streaming feel) | nginx `proxy_buffering on` (default) | Set `proxy_buffering off` (Pitfall 2) |
| Daily quota counter never expires | Redis < 7.0 (Pitfall 4) | `redis-cli INFO server` → if `< 7.0`, upgrade OR use the LUA fallback (RESEARCH Q5) |
| Every vibemix launch hits `/register` | Client keyring is null backend (Pitfall 6) | Client falls back to `~/Library/Application Support/vibemix/install_uuid` — confirm the file exists with 32 hex chars |
| 401 `{"detail":"invalid token"}` after rotation | Expected — clients auto-recover on next launch via `get_or_refresh_jwt` | None; document in user-facing release notes |
| Circuit breaker stuck open | 10 consecutive upstream 5xx | Check Gemini/OpenRouter status pages; breaker auto-resets after 60s |
| Container won't start | Missing required env var in `.env` | Check stderr: pydantic `ValidationError` lists the missing field name (never the value — safe to log) |
| Body shape mismatch on /v1/audio/speech | Client SDK changed payload schema | Verify livekit-plugins-openai TTS still uses OpenAI-compat body |
| `EXPIRE NX` ignored | Redis 6.x doesn't support NX modifier (Pitfall 4) | Upgrade Redis to 7.0+ OR switch to the LUA fallback |
| Keyring "null backend" warning in client logs | Dev Python from Homebrew without universal2 binary | Use python.org installer or pyenv (both ship universal2 with working Keychain backend) — Pitfall 6 |

## Security notes

- All upstream secrets (`GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `JWT_SECRET`) live ONLY in `/var/www/vibemix-proxy/.env` on the server. Permissions: `chmod 600 .env`. Never commit.
- `.env.example` ships placeholders only — CI gate `tests/test_phase05_verification.py::test_g4_proxy_env_example_no_real_keys` asserts no `AIza`/`sk-or-v1-` patterns.
- Container runs as non-root (uid 10001 `appuser`).
- Vibemix clients (PyInstaller binaries from Phase 18) contain ZERO upstream-API-key strings. CI gate `test_g3_zero_aiza_in_client` + Phase 18's binary `strings` audit pin this.
- HTTPS terminated at nginx; the proxy container speaks plain HTTP on `127.0.0.1:8788` only.
- JWT alg=none algorithm-confusion attack blocked by `algorithms=["HS256"]` explicit allowlist. Test `proxy/tests/test_auth.py::test_auth_06_alg_none_blocked` pins this.
- `/register` is IP-rate-limited (NOT install-UUID-keyed) at `RATE_LIMIT_PER_MIN` rpm — blocks register-spam attacks.

## Phase carry-forward

- **Phase 11 (Tauri shell)**: Rust side may use `tauri-plugin-keychain` to read install_uuid; the Python sidecar's `install_uuid.py` is the Python-side counterpart. Both can read the same Keychain service (`vibemix` / `install_uuid`).
- **Phase 18 (Distribution)**: installer build flips `VIBEMIX_LLM_MODE=proxy` default in the bundled `__main__.py`. Binary attack verification (VERIFY-04) asserts zero `AIza` matches in `strings` output of the .app / .exe.
- **Phase 20 (Day-Zero Ops)**: CI deploys this proxy on tag push; second-responder rota watches for upstream 5xx spikes; Prometheus exporter optional.
