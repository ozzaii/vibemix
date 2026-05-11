---
phase: 05-fastapi-proxy-install-uuid-jwt
type: summary
status: complete
date_completed: 2026-05-11
requirements_covered:
  - ARCH-08
  - ARCH-09
  - ARCH-10
waves:
  - "05-01: proxy scaffold (FastAPI app + healthz + pydantic-settings + Redis quota helper + Dockerfile + compose)"
  - "05-02: JWT auth (HS256 only, alg=none blocked) + /register + slowapi limiter wiring (IP-keyed /register)"
  - "05-03: LLM SSE + TTS PCM proxy routes (gemini-native paths, circuit breaker, upstream-secret sanitization)"
  - "05-04: client install_uuid + JWT cache + proxy-mode factory dispatch (no silent fallback)"
  - "05-05: deployment runbook + 8-gate verification + phase close"
metrics:
  total_tasks: 13
  proxy_tests: 79
  client_tests_added: 39
  client_suite_total: 385
  duration_minutes: ~70
key-files:
  created:
    - proxy/pyproject.toml
    - proxy/Dockerfile
    - proxy/docker-compose.yml
    - proxy/.env.example
    - proxy/.gitignore
    - proxy/README.md
    - proxy/uv.lock
    - proxy/app/__init__.py
    - proxy/app/config.py
    - proxy/app/main.py
    - proxy/app/auth.py
    - proxy/app/quota.py
    - proxy/app/upstream.py
    - proxy/app/middleware/__init__.py
    - proxy/app/middleware/jwt.py
    - proxy/app/middleware/rate_limit.py
    - proxy/app/routes/__init__.py
    - proxy/app/routes/register.py
    - proxy/app/routes/gemini.py
    - proxy/app/routes/openai_compat.py
    - src/vibemix/agent/install_uuid.py
    - src/vibemix/agent/jwt_cache.py
    - src/vibemix/agent/proxy_client.py
    - tests/agent/test_install_uuid.py
    - tests/agent/test_jwt_cache.py
    - tests/agent/test_proxy_client.py
    - tests/agent/test_no_aiza_in_client.py
    - tests/test_phase05_verification.py
  modified:
    - .gitignore
    - pyproject.toml
    - src/vibemix/agent/llm_factory.py
    - src/vibemix/agent/tts_chain.py
    - src/vibemix/agent/__init__.py
    - src/vibemix/__main__.py
    - tests/agent/test_llm_factory.py
    - tests/agent/test_tts_chain.py
    - tests/test_main_smoke.py
decisions:
  - "Proxy routes mirror Gemini-native paths (/v1beta/models/{model}:streamGenerateContent) and OpenAI-compatible TTS path (/v1/audio/speech). CONTEXT's `/api/vibemix/v1/llm/generate` superseded by RESEARCH Q1 — verified genai SDK URL builder uses {base_url}/v1beta/models/..."
  - "google_plugin.LLM accepts `http_options=HttpOptions(base_url, headers)` directly (verified in livekit/plugins/google/llm.py:117). Proxy mode passes that kwarg; no separate genai.Client construction needed for the LLM plugin."
  - "JWT TTL = 90 days. HS256 only. `algorithms=['HS256']` explicit allowlist on every decode (alg=none attack blocked)."
  - "slowapi via @limiter.limit() decorator — NOT SlowAPIMiddleware. Decorator runs key_func at handler time, AFTER JWTMiddleware sets request.state.install_uuid (RESEARCH Q2)."
  - "/register is IP-keyed (slowapi.util.get_remote_address); LLM + TTS routes are install_uuid-keyed. Anti-register-spam."
  - "NO silent fallback proxy → direct. Setup failures sys.exit non-zero with clear messages. Locked per CONTEXT."
  - "mode='direct' is the Phase 5 default (Kaan's dev rig keeps working). Phase 18 installer flips to 'proxy' for distributed binaries."
  - "Redis 7.0+ required for EXPIRE NX. Documented in proxy/README.md."
  - "Upstream secret sanitization: on upstream 4xx/5xx, response NEVER echoes upstream body. Test LLM-07 pins zero AIza leakage in sanitized responses."
---

# Phase 5: FastAPI Proxy + Install-UUID JWT — SUMMARY

## What Shipped

**Server-side `proxy/`** — independent Python project (own `pyproject.toml`, own `uv.lock`, own `.venv`):

- `GET /healthz` — liveness (unauth).
- `POST /api/vibemix/v1/register` — install_uuid → JWT (unauth + IP-keyed rate limit).
- `POST /v1beta/models/{model}:streamGenerateContent` — Gemini LLM SSE pass-through (JWT-gated, per-uuid rate limit, daily quota, circuit breaker).
- `POST /v1beta/models/{model}:generateContent` — non-streaming sibling.
- `POST /v1/audio/speech` — OpenAI-compatible TTS proxied to OpenRouter (chunked PCM stream).

**Auth**: PyJWT 2.12.1+ (CVE-2026-32597 patch). HS256 only — `algorithms=["HS256"]` explicit allowlist. **alg=none attack blocked** (T-05-09 mitigation).

**Rate limit**: slowapi 0.1.9+ via `@limiter.limit("60/minute")` decorator. Per-install_uuid for LLM/TTS; per-IP for `/register`.

**Quota**: Redis INCR + EXPIRE NX (Redis 7.0+ required). 2000 rpd per UUID. 429 + Retry-After (to next UTC midnight) on exceed.

**Circuit breaker**: 10 consecutive upstream 5xx → 503 + Retry-After: 60 for 60s. Per-route (gemini_breaker vs openrouter_breaker).

**Streaming SSE pass-through**: `StreamingResponse(generator, media_type="text/event-stream")` + `X-Accel-Buffering: no`. `is_disconnected()` polled every Nth chunk (Pitfall 7).

**Upstream secret sanitization**: 502 `{"detail": "upstream auth failure"}` on upstream 4xx — raw body NEVER echoed. CI pins zero AIza in response bodies (`test_llm_07_upstream_auth_failure_sanitized`).

**Docker + Compose**: `python:3.12-slim` multi-stage image, non-root uid 10001. Compose for local dev (proxy + redis:7-alpine).

**Client-side `src/vibemix/`**:

- `install_uuid.py` — keyring primary + file fallback at `~/Library/Application Support/vibemix/install_uuid` (macOS) or `%APPDATA%/vibemix/install_uuid` (Windows). Detects `keyring.backends.null.Keyring` (Pitfall 6) and forces file fallback. POSIX `chmod 0o600`.
- `jwt_cache.py` — keychain-cached JWT, refresh via POST `/api/vibemix/v1/register` when < 7 days from expiry (or expired, or missing). Sanitized RuntimeError on /register non-200.
- `proxy_client.py` — `build_proxy_genai_client(jwt, base_url)` + `build_proxy_tts_chain(jwt, base_url)`. Module-load `import vibemix.agent.tts_chain` triggers the OpenRouter monkey-patch (load-bearing — applies in proxy mode too because the proxy emits PCM at `/v1/audio/speech`).
- `llm_factory.build_llm` extended: `build_llm(api_key=None, *, mode='direct', proxy_base_url=None, jwt=None)`. Direct mode = Phase 4 byte-identical. Proxy mode threads `HttpOptions(base_url, Authorization: Bearer JWT)` into `google_plugin.LLM`.
- `tts_chain.build_tts_chain` extended same way. Proxy mode returns 1-entry `FallbackAdapter` via `build_proxy_tts_chain`.
- `__main__.py` reads `VIBEMIX_LLM_MODE` (default `direct`) + `VIBEMIX_PROXY_BASE_URL` (default `https://api.altidus.world`). Loud sys.exit on any proxy-mode setup failure — **NO silent fallback**.

**Deployment runbook**: `proxy/README.md` covers prereqs (Redis 7.0+, Docker, nginx, PM2), local dev, prod deploy on 77.42.28.93, nginx config block (`proxy_buffering off` for SSE — Pitfall 2), JWT rotation procedure, troubleshooting matrix (Pitfalls 2/4/6 referenced), security notes, Phase 11/18/20 carry-forward.

## Architectural Decisions

1. **Gemini-native paths over CONTEXT's `/api/vibemix/v1/llm/generate`** (RESEARCH Q1). Verified by reading genai SDK source: the SDK builds URLs as `{base_url}/v1beta/models/{model}:streamGenerateContent`. The proxy mirrors that exact path; the client points its existing SDK at the proxy with no SSE-parsing rewrite. ROADMAP Success Criterion 2 text reconciled.

2. **TTS at OpenAI-compatible `/v1/audio/speech`**. The vibemix client uses `livekit-plugins-openai.TTS(base_url=...)` which POSTs to `/audio/speech` — proxy mounts the path and forwards to OpenRouter.

3. **JWT TTL = 90 days** (CONTEXT decision-locked; supersedes stale ROADMAP `15-30 min`). No user login = no rotation event. Long TTL means even offline-then-online clients can mint tokens. Risk capped by per-UUID rate limit + 2000 rpd quota.

4. **`@limiter.limit()` decorator, NOT `SlowAPIMiddleware`** (RESEARCH Q2). Decorator runs `key_func` at handler time — AFTER `JWTMiddleware` sets `request.state.install_uuid`. Middleware-ordering trap avoided.

5. **IP-keyed limit on `/register`** (install_uuid doesn't exist yet at register time). Blocks register-spam attacks.

6. **NO silent fallback proxy → direct**. Proxy mode setup failure exits non-zero with clear error pointing to a fix path. Silent fallback would defeat the entire security goal of Phase 5.

7. **`google_plugin.LLM` accepts `http_options` directly**. Verified at `.venv/lib/python3.12/site-packages/livekit/plugins/google/llm.py:117`. The proxy-mode LLM factory passes `HttpOptions(base_url, headers={'Authorization': 'Bearer JWT'})` straight in — no separate `genai.Client` construction needed for the LLM plugin. (Note: `__main__.py` does build a separate `genai.Client` via `build_proxy_genai_client` for the DJCoHostAgent multimodal `llm_node` override.)

8. **`mode='direct'` is the Phase 5 default**. Phase 18 installer flips to `'proxy'`. Kaan's dev rig keeps working with `.env` keys.

9. **Redis 7.0+ required**. `EXPIRE key seconds NX` was added in Redis 7.0; older versions silently ignore the NX modifier. Bravoh's server already runs Redis 7.x. Documented as a deployment prereq.

## Deviations from CONTEXT

- **Route paths**: CONTEXT specified `/api/vibemix/v1/llm/generate` + `/api/vibemix/v1/tts/synthesize`. Actual paths are `/v1beta/models/{model}:streamGenerateContent` + `/v1beta/models/{model}:generateContent` + `/v1/audio/speech`. Rationale per RESEARCH Q1: the genai SDK has hardcoded URL builders. Either we mount Gemini-native paths in the FastAPI app (chosen — Option B) or we add an nginx rewrite layer (rejected — adds infra complexity for zero gain). Same logic for TTS: `livekit-plugins-openai.TTS(base_url=...)` posts to `/audio/speech`, so the proxy mounts at `/v1/audio/speech` directly.
- **JWT TTL**: CONTEXT specified 90 days (locked). ROADMAP's `15-30 min` text was stale — reconciled.
- **TTS chain in proxy mode**: client-side chain has 1 entry (vs direct mode's 2-3 entries). The proxy handles upstream fallback internally via circuit breaker + future Gemini-native fallback route (deferred to Phase 5 follow-up if needed).

## Acceptance Gates

All 8 gates pass per `tests/test_phase05_verification.py`:

| Gate | What | Result |
|------|------|--------|
| G1 | Full vibemix client suite green | ✅ 385 tests |
| G2 | Full proxy suite green | ✅ 79 tests |
| G3 | Zero AIza pattern in `src/vibemix/` | ✅ — phase invariant |
| G4 | Zero AIza/sk-or-v1- in `proxy/.env.example` | ✅ |
| G5 | POC files diff-untouched vs Phase 4 close | ✅ |
| G6 | JWT alg=none attack rejected | ✅ — load-bearing security gate |
| G7 | install_uuid persists via keyring + file fallback | ✅ |
| G8 | Direct mode preserves Phase 4 behavior (regression-safe) | ✅ |

## Carry-Forward

- **Phase 6 (Genre-Aware Phase Detection)**: independent of Phase 5; no integration needed.
- **Phase 7 (Windows Port)**: `install_uuid.py` file fallback path `%APPDATA%/vibemix/install_uuid` already wired; Windows-specific tests added (UUID-04).
- **Phase 11 (Tauri shell)**: Rust side may use `tauri-plugin-keychain` to read install_uuid; Python sidecar reads the same Keychain service. Decision deferred.
- **Phase 18 (Distribution)**: installer build flips `VIBEMIX_LLM_MODE=proxy` default. Binary attack verification (VERIFY-04) asserts zero `AIza` in `strings` output.
- **Phase 20 (Day-Zero Ops)**: CI deploys proxy on tag push; second-responder rota watches upstream 5xx spikes; structured-logging middleware extension with metrics export.

## Operational Status

- Code complete, tests green, proxy runnable locally (`cd proxy && uv run uvicorn app.main:app --port 8788`).
- **Server deployment to `api.altidus.world` PENDING Kaan's operational schedule.** Plan 05-05 ships the runbook (`proxy/README.md`); deployment is a separate operational task. Phase 5 closes regardless of deployment timing.

## Wave Commits

- Wave 1: `c04b403` — proxy scaffold
- Wave 2: `1549130` — JWT auth + /register + slowapi
- Wave 3: `ba8a013` — LLM SSE + TTS PCM routes + circuit breaker
- Wave 4: `3a3bc4c` — client install_uuid + JWT cache + factory mode dispatch
- Wave 5: (this commit) — runbook + 8-gate verification + phase close

## Self-Check: PASSED

All files referenced above exist; all wave commits present in `git log --oneline`.
