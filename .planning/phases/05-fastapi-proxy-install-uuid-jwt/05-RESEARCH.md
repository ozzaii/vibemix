# Phase 5: FastAPI Proxy + Install-UUID JWT — Research

**Researched:** 2026-05-11
**Researcher:** gsd-phase-researcher
**Domain:** FastAPI streaming proxy, JWT auth, OS keychain, Redis quotas, SSE pass-through
**Confidence:** HIGH (all P0 questions resolved by direct SDK probing + current docs)

<user_constraints>
## User Constraints (from 05-CONTEXT.md)

### Locked Decisions
- **Proxy stack:** FastAPI ≥0.115, uvicorn[standard], all routes async, PyJWT HS256, slowapi ≥0.1.9, Redis (Bravoh's existing).
- **Key extractor:** `lambda req: req.state.install_uuid` — set by JWT middleware before slowapi reads it.
- **Quota:** `vibemix:quota:<uuid>:<YYYYMMDD>`, 24h TTL, INCR + EXPIRE-on-create.
- **Telemetry:** Python `logging` with JSON formatter, one line per request.
- **Client:** `keyring` ≥25.0, service=`"vibemix"`, account=`"install_uuid"` / `"jwt"`. UUIDv4 (`uuid.uuid4().hex` — 32 lowercase hex).
- **JWT:** `{install_uuid, iat, exp}`, 90-day TTL, refresh client-side when <7 days from expiry. Refresh = idempotent re-call to `/register`.
- **Endpoints:** `/api/vibemix/v1/{register,llm/generate,tts/synthesize}`. LLM endpoint must match upstream Gemini SSE shape so SDK works unmodified IF possible.
- **Rate limits:** 60 rpm + 2000 rpd per UUID. Server-wide circuit breaker on 10 consecutive 5xx upstream → 503 + Retry-After 60s for 60s.
- **Mode env:** `VIBEMIX_LLM_MODE=proxy` for distributed binaries, `direct` for Kaan's dev loop. Default proxy base = `https://api.altidus.world`.
- **No silent fallback** from proxy → direct mode (defeats the phase).
- **OpenRouter routed through proxy too** — `OPENROUTER_API_KEY` stays server-side.

### Claude's Discretion
- Whether genai SDK supports `base_url` override → **RESOLVED: YES** (Q1).
- slowapi key-extractor middleware ordering → **RESOLVED: use decorator, not middleware** (Q2).
- CSRF for `/register` → not needed (idempotent POST, no cookie session).
- SSE test strategy → `httpx.AsyncClient` + `aiter_bytes()` on the ASGI app.
- Device fingerprint on install_uuid → defer to Phase 20.

### Deferred (out of scope)
BYO-key, per-user dashboards, web admin console, OAuth, anti-abuse heuristics, gRPC, multi-region, paid tiers.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROXY-01 | `proxy/` package deployable separately to `api.altidus.world` | Q6 (FastAPI StreamingResponse), Q5 (Redis), Q2 (slowapi) |
| PROXY-02 | LLM streaming SSE pass-through matching Gemini wire format | Q1 (SDK base_url verified) + Q6 (FastAPI SSE) |
| PROXY-03 | TTS PCM streaming pass-through (OpenRouter + Gemini fallback) | Q1 (openai_plugin base_url verified) + Q6 |
| PROXY-04 | JWT verification middleware sets `req.state.install_uuid` | Q3 (PyJWT) + Q2 (middleware order) |
| PROXY-05 | Rate limit 60 rpm + 2000 rpd keyed on install_uuid | Q2 (slowapi decorator pattern) + Q5 (Redis INCR/EXPIRE NX) |
| PROXY-06 | Circuit breaker on 10 consecutive upstream 5xx → 503 + Retry-After 60s | Q6 (upstream client) + custom logic |
| PROXY-07 | `/register` issues fresh JWT for install_uuid | Q3 (PyJWT encode) |
| CLIENT-01 | `get_or_create_install_uuid()` with keyring → file fallback | Q4 (keyring graceful failure) |
| CLIENT-02 | `build_proxy_genai_client(jwt, base_url)` reuses genai SDK | Q1 (HttpOptions base_url + headers) |
| CLIENT-03 | `build_proxy_tts_chain(jwt, base_url)` reuses openai_plugin | Q1 (openai_plugin base_url confirmed) |
| CLIENT-04 | `build_llm(mode, ...)` and `build_tts_chain(mode, ...)` dispatch | code integration, no research needed |
| CLIENT-05 | `VIBEMIX_LLM_MODE` env honored; no silent fallback on failure | code integration |
| OPS-01 | Dockerfile + docker-compose.yml + .env.example + README runbook | `python:3.12-slim` base, standard pattern |
</phase_requirements>

## Executive Summary

1. **The pivotal Q1 is a HARD YES.** [VERIFIED: read .venv/lib/python3.12/site-packages/google/genai/client.py + types.py + _api_client.py] `google.genai` ≥2.0.1 accepts `http_options=HttpOptions(base_url=...)` at the `genai.Client` constructor. Custom headers via `http_options.headers={"Authorization": "Bearer <jwt>"}` are merged onto the SDK defaults via `patch_http_options()`. The SDK will still send a `x-goog-api-key` header (carrying whatever value we pass to `api_key=`); the proxy must accept-and-ignore it. **The client refactor is trivial — no SSE-parsing rewrite needed.**

2. **The proxy must mount the LLM route at the exact upstream path.** The SDK builds URLs as `{base_url}/{api_version}/{path}` — concretely `https://api.altidus.world/v1beta/models/gemini-3-flash-preview:streamGenerateContent?alt=sse`. The proxy needs a route at `/v1beta/models/{model}:streamGenerateContent` that accepts `?alt=sse`. The CONTEXT-specified path `/api/vibemix/v1/llm/generate` is a non-starter unless we add a custom client wrapper. **Recommendation: nginx rewrites `/api/vibemix/v1/llm/*` → `/v1beta/models/*` server-side, OR we change CONTEXT to use Gemini-shaped paths directly** (cleaner — discuss with Kaan).

3. **slowapi ordering trap solved by using the decorator, not the middleware.** [VERIFIED: read slowapi/extension.py + middleware.py via WebFetch] When you use `@limiter.limit("60/minute")` as a decorator on the route, `key_func` runs at *route-handler time* — AFTER all middleware has finished. So a `BaseHTTPMiddleware`-derived JWT middleware (added via `app.add_middleware(JWTMiddleware)`) populates `req.state.install_uuid` before slowapi reads it. **Do NOT add `SlowAPIMiddleware`** — it would invert the order (rate limit runs before next middleware). The decorator path is cleaner, less footgun-prone, and already production-proven.

4. **PyJWT 2.12.1 is the canonical pick — and you NEED 2.12.1 specifically for CVE-2026-32597.** [CITED: https://pypi.org/project/PyJWT/ + linuxsecurity.com] python-jose is fine but maintenance has slowed; PyJWT outperforms it by ~25% on verify, has cleaner exception hierarchy, and is FastAPI's tutorial-default in 2026. HS256 is the right algorithm for a single-tenant proxy where the proxy both issues and verifies (no public-key distribution needed). Pin `pyjwt>=2.12.1` in `proxy/pyproject.toml`.

5. **keyring 25.7.0 is current. On macOS it "just works" — no entitlements needed for unsigned dev Python; signed .app bundles get keychain access automatically.** [CITED: https://pypi.org/project/keyring/ + keyring docs] `get_password()` returns `None` (not raises) when no value exists — clean for first-launch UUID minting. On *failure* (backend unavailable, user denied), `KeyringError` is the catch-all parent exception. Graceful fallback: `try keyring.get_password / except KeyringError → fall back to local file at platform-appropriate path`. The file fallback path needs to match Phase 18 binary-bundle expectations.

6. **Redis INCR + EXPIRE NX is a two-command pipeline.** Pattern: `async with redis.pipeline(transaction=False) as pipe: pipe.incr(key); pipe.expire(key, 86400, nx=True); count, _ttl_set = await pipe.execute()`. `nx=True` ensures EXPIRE only sets the TTL on the *first* request of the day (subsequent INCRs preserve the original midnight expiry). [CITED: https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html + redis.io/docs/latest/commands/expire/] `Retry-After` until midnight UTC = `(86400 - (now_utc - midnight_utc).seconds)`.

7. **SSE pass-through in FastAPI uses `StreamingResponse(generator, media_type="text/event-stream")` plus `X-Accel-Buffering: no` to disable nginx buffering.** [CITED: fastapi.tiangolo.com/tutorial/server-sent-events/ + GitHub discussion #7572] Client-disconnect detection via `await request.is_disconnected()` inside the generator loop. The proxy holds the upstream genai client globally (its own `genai.Client(api_key=GEMINI_KEY)`) and pipes bytes from upstream stream → response generator.

**Primary recommendation:** Stand up the proxy with the standard FastAPI patterns documented below. The single architectural decision Kaan needs to make is the route-shape question (point 2): either nginx-rewrites the Gemini-native paths under `/api/vibemix/v1/`, or we change CONTEXT to expose Gemini-native paths directly under `/v1beta/...`. Defer to Kaan in discuss-phase; either way the proxy code is the same — only the route prefix changes.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| API key custody | Proxy (server) | — | Whole point of phase: keep AIza off binaries |
| JWT issuance | Proxy (server) | — | Server has signing secret |
| JWT verification | Proxy (server) | — | Same secret, same place |
| Rate limit + quota counters | Proxy + Redis | — | Distributed-safe storage |
| install_uuid generation | Client (vibemix) | — | UUIDv4 minted locally on first launch |
| install_uuid storage | OS keychain (client) | File fallback (client) | OS-native security; file fallback for denied keychain |
| JWT cache | OS keychain (client) | File fallback (client) | Same as install_uuid |
| Mode selection | Client env (`VIBEMIX_LLM_MODE`) | — | Distributed binaries set proxy; dev override = direct |
| Upstream LLM/TTS calls | Proxy (server) → Gemini/OpenRouter | — | Server holds keys |
| SSE/PCM byte streams | Proxy passes through; client consumes | — | Zero buffering, lowest latency |

## Q1: genai SDK base_url Override

### Verdict: **YES — fully supported. Trivial client refactor.**

Direct verification of installed SDK at `.venv/lib/python3.12/site-packages/google/genai/`:

- `HttpOptions` class (`types.py:2311-2360`) [VERIFIED] has fields: `base_url`, `base_url_resource_scope`, `api_version`, `headers`, `timeout`, `client_args`, `async_client_args`, `extra_body`, `retry_options`, `httpx_client`, `httpx_async_client`, `aiohttp_client`.

- `genai.Client.__init__` (`client.py:373-449`) [VERIFIED] accepts `http_options: Optional[Union[HttpOptions, HttpOptionsDict]] = None`. Resolves `base_url` via `get_base_url(...)` (priority: HttpOptions > setDefaultBaseUrls > env `GOOGLE_GEMINI_BASE_URL`).

- `_base_url.py` [VERIFIED] confirms env-var override `GOOGLE_GEMINI_BASE_URL` is also supported — even simpler alternative for ops.

- Header merging in `_api_client.py:794-801` [VERIFIED] — user headers from `http_options.headers` patch onto SDK defaults (which include `x-goog-api-key`, `Content-Type`, `user-agent`, `x-goog-api-client`). User-supplied `Authorization: Bearer <jwt>` is added; `x-goog-api-key` remains (with whatever dummy value we passed to `api_key=`).

### Canonical client pattern

```python
# src/vibemix/agent/proxy_client.py
from google import genai
from google.genai import types

def build_proxy_genai_client(jwt: str, proxy_base_url: str) -> genai.Client:
    """
    Build a genai.Client that talks to the vibemix proxy instead of Google's
    endpoint. The SDK's generate_content_stream() works unchanged.
    """
    return genai.Client(
        # api_key is REQUIRED by the SDK validation path (raises ValueError
        # at line 780-785 if absent). The proxy ignores x-goog-api-key.
        api_key="vibemix-proxy",
        http_options=types.HttpOptions(
            base_url=proxy_base_url.rstrip("/"),  # e.g. "https://api.altidus.world"
            headers={"Authorization": f"Bearer {jwt}"},
            # Optional: bump timeout for slow upstreams
            timeout=120_000,  # ms
        ),
    )
```

### URL shape the SDK produces

Verified at `_api_client.py:1262` + `models.py:4835`:

```
{base_url}/{api_version}/{path}
= https://api.altidus.world/v1beta/models/gemini-3-flash-preview:streamGenerateContent?alt=sse
```

**This is what the proxy must route on.** The CONTEXT-specified path `/api/vibemix/v1/llm/generate` does NOT match the SDK's URL builder. Two viable resolutions:

| Option | Mechanism | Pros | Cons |
|--------|-----------|------|------|
| **A. Server-side rewrite (nginx)** | `rewrite ^/api/vibemix/v1/llm/(.*)$ /v1beta/$1 break;` in nginx; FastAPI app mounts `/v1beta/models/{model}:streamGenerateContent` | Keeps CONTEXT route shape; client uses `base_url=https://api.altidus.world/api/vibemix/v1/llm` | nginx config not in this repo (Bravoh infra) — ops coordination needed |
| **B. Use Gemini-native paths directly** | FastAPI mounts `/v1beta/...` paths at app root; client `base_url=https://api.altidus.world` | Zero rewrite layer; pure path forwarding | Diverges from CONTEXT route shape — Kaan must approve |

**Recommendation: B** — cleanest. The proxy is Gemini-shaped at the wire level anyway; making the routes themselves Gemini-shaped is honest about what the proxy is doing.

### LiveKit OpenAI plugin base_url for TTS

Verified at `.venv/lib/python3.12/site-packages/livekit/plugins/openai/tts.py:61-104`:
- `TTS.__init__` accepts `base_url: NotGivenOr[str] = NOT_GIVEN` and threads it into the underlying `AsyncOpenAI` client (`base_url=base_url if is_given(base_url) else None`).
- Already proven against OpenRouter in `cohost_v4.py:1998` (`base_url="https://openrouter.ai/api/v1"`).
- The OpenRouter audio endpoint follows OpenAI's `/v1/audio/speech` shape.

Client pattern:

```python
# src/vibemix/agent/proxy_client.py (continued)
from livekit.plugins import openai as openai_plugin

def build_proxy_tts_chain(jwt: str, proxy_base_url: str, voice: str = "Sulafat"):
    """
    TTS chain pointed at the vibemix proxy. The proxy emits the same
    OpenAI-compatible PCM response shape as OpenRouter, so the existing
    openai_plugin.TTS works unmodified.
    """
    return [
        openai_plugin.TTS(
            model="google/gemini-3.1-flash-tts-preview",
            voice=voice,
            api_key=jwt,                                   # plugin sends this as Bearer
            base_url=f"{proxy_base_url.rstrip('/')}/v1",   # OpenAI-compat suffix
            response_format="pcm",
            instructions="Casual studio friend, brief, natural — no theatrics.",
        ),
        # ... fallback chain identical to v4
    ]
```

The plugin sends `Authorization: Bearer <api_key>` natively — so we just pass the JWT as `api_key=`. The proxy verifies it the same way as the LLM route.

### Phase 5 architectural implication

- **`src/vibemix/agent/proxy_client.py`** is ~30 LOC: two builder functions.
- **`src/vibemix/agent/llm_factory.py`** extension: add `mode` parameter; in `"proxy"` mode, call `build_proxy_genai_client(jwt, base_url)` instead of `build_direct_genai_client(api_key)`.
- **`src/vibemix/agent/tts_chain.py`** extension: same pattern.
- Streaming code in `cohost_v4.py` ports (Phase 2-7) does NOT change — `client.aio.models.generate_content_stream(...)` works against the proxy unchanged.

## Q2: slowapi + FastAPI Middleware Ordering

### Verdict: **Use `@limiter.limit()` decorator, NOT `SlowAPIMiddleware`. JWT middleware via `add_middleware`.**

The decorator path runs `key_func` at route-handler time — after ALL middleware has dispatched. The middleware path runs `key_func` early in the request lifecycle, before downstream middleware. CONTEXT requires JWT middleware to populate `req.state.install_uuid` BEFORE slowapi reads it. Therefore:

- ✅ JWT middleware via `app.add_middleware(JWTMiddleware)` → runs early, sets `req.state.install_uuid`.
- ✅ `@limiter.limit("60/minute")` decorator on routes → runs at handler time, reads `req.state.install_uuid` from key_func.
- ❌ Do NOT call `app.add_middleware(SlowAPIMiddleware)` — would invert ordering.

### Canonical setup (~25 LOC)

```python
# proxy/app/main.py
import os
from fastapi import FastAPI, Request, HTTPException, status, Depends
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import jwt

JWT_SECRET = os.environ["JWT_SECRET"]
REDIS_URL = os.environ["REDIS_URL"]

# --- JWT middleware (added FIRST → runs FIRST in pipeline) ---
from starlette.middleware.base import BaseHTTPMiddleware

class JWTMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth on /register, /health, /docs
        if request.url.path.endswith(("/register", "/health", "/docs", "/openapi.json")):
            return await call_next(request)
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse({"detail": "missing bearer"}, status_code=401)
        try:
            claims = jwt.decode(auth[7:], JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return JSONResponse({"detail": "token expired"}, status_code=401)
        except jwt.InvalidTokenError:
            return JSONResponse({"detail": "invalid token"}, status_code=401)
        request.state.install_uuid = claims["install_uuid"]
        return await call_next(request)

# --- slowapi keyed on req.state.install_uuid (set by JWT mw above) ---
def install_uuid_key(request: Request) -> str:
    return getattr(request.state, "install_uuid", "anonymous")

limiter = Limiter(
    key_func=install_uuid_key,
    storage_uri=REDIS_URL,         # required for multi-worker / restart-safe
    strategy="fixed-window",       # cheaper than sliding-window; OK for our use
)

app = FastAPI(docs_url="/docs", openapi_url="/openapi.json")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(JWTMiddleware)   # added last in code → outermost in stack → runs FIRST per request
```

```python
# proxy/app/routes/llm.py
from fastapi import APIRouter, Request
from ..main import limiter

router = APIRouter()

@router.post("/v1beta/models/{model}:streamGenerateContent")
@limiter.limit("60/minute")  # key_func reads req.state.install_uuid HERE
async def llm_stream(request: Request, model: str):
    # quota check (separate from slowapi rpm limit) — see Q5
    # upstream pass-through — see Q6
    ...
```

### Middleware ordering verified

FastAPI middleware semantics (per docs): "the last middleware added is the OUTERMOST." That means it runs FIRST on the request path and LAST on the response path. So we want JWT middleware added LAST (or only) so it wraps the whole app.

In our case we add only `JWTMiddleware`. The slowapi decorator handles rate-limiting at route-handler time — no middleware needed for it.

### 2026 footguns

- **`SlowAPIMiddleware` inherits from `BaseHTTPMiddleware`** [CITED: GitHub issue #195] which has a known performance issue (5x RPS reduction in benchmarks). slowapi ships `SlowAPIASGIMiddleware` as a faster alternative — but we don't use either, so this doesn't bite us.
- **`@limiter.limit()` requires `request: Request` in the route signature.** [CITED: https://github.com/laurentS/slowapi README] Omitting it → silently does nothing.
- **slowapi 0.1.9 has been stable since 2023 — no recent releases.** Treat as a mature, lightly maintained dep. No 2026 deprecations.
- **In-memory storage is NOT restart-safe.** Pin `storage_uri=REDIS_URL` (note: this is for slowapi's rate-limit counters, separate from our own Redis quota counter — they share the Redis instance but use different key namespaces).

## Q3: PyJWT vs python-jose

### Recommendation: **PyJWT 2.12.1+ (HS256, 90-day exp).**

- **Maintenance:** PyJWT actively maintained (2.12.1 published 2026-03-13 with CVE-2026-32597 fix). python-jose maintenance slowed in 2024-2025. [CITED: https://pypi.org/project/PyJWT/]
- **Performance:** PyJWT ~25% faster on verify than python-jose. [CITED: search result snippet, MEDIUM confidence]
- **API ergonomics:** PyJWT's exception hierarchy is cleaner — `ExpiredSignatureError` and `InvalidTokenError` (parent of `InvalidSignatureError`, `InvalidAudienceError`, etc.) cover all error cases.
- **FastAPI tutorial uses PyJWT** [CITED: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/] — community canonical.
- **Bravoh stack uses PyJWT** (per CONTEXT decisions). Stack consistency.
- **HS256 is correct here.** Asymmetric (RS256) would only matter if a third party needed to *verify* tokens without holding the secret. The proxy is the only verifier. HS256 = simpler key management (one env var: `JWT_SECRET`).

### Canonical encode/decode

```python
# proxy/app/routes/register.py
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALG = "HS256"
JWT_TTL_DAYS = 90

class RegisterReq(BaseModel):
    install_uuid: str = Field(min_length=32, max_length=32, pattern=r"^[0-9a-f]{32}$")
    client_version: str = Field(min_length=1, max_length=32)

class RegisterResp(BaseModel):
    jwt: str
    expires_at: str            # ISO 8601 UTC
    quota_daily: int

router = APIRouter()

@router.post("/api/vibemix/v1/register", response_model=RegisterResp)
async def register(body: RegisterReq) -> RegisterResp:
    now = datetime.now(tz=timezone.utc)
    exp = now + timedelta(days=JWT_TTL_DAYS)
    payload = {
        "install_uuid": body.install_uuid,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "ver": body.client_version,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
    return RegisterResp(
        jwt=token,
        expires_at=exp.isoformat(),
        quota_daily=2000,
    )
```

Verify (used in JWT middleware above):

```python
try:
    claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    # claims["install_uuid"], claims["exp"] auto-validated by PyJWT
except jwt.ExpiredSignatureError:
    return JSONResponse({"detail": "token expired"}, status_code=401)
except jwt.InvalidTokenError:  # parent of all signature/format errors
    return JSONResponse({"detail": "invalid token"}, status_code=401)
```

### Security notes

- **`pyjwt[crypto]` extra is only needed for RS256/ES256.** We use HS256 — plain `pyjwt>=2.12.1` is enough. [CITED]
- **Pin `>=2.12.1` to ensure the CVE-2026-32597 fix.** [CITED: https://linuxsecurity.com/advisories/suse/python-pyjwt-suse-2026-20839-1] PyJWT < 2.12.1 accepts unknown `crit` header extensions which violates RFC 7515. Low impact for our HS256 self-issued tokens but pin anyway.
- **Token theft trade-off:** 90-day TTL means a leaked JWT = 90 days of quota theft. Mitigation = per-UUID rate limit (60 rpm + 2000 rpd). Worst case: attacker burns ONE user's quota. Acceptable for v1 — document in proxy/README.md.
- **No refresh-token complexity.** Client re-calls `/register` with same install_uuid when JWT < 7 days from expiry. `/register` is idempotent.

## Q4: keyring on macOS Sequoia / Windows 11

### Verdict: **`keyring>=25.7.0` (latest stable). Works out of box on both platforms. Fallback to file when KeyringError.**

### macOS Sequoia behavior

- [CITED: https://pypi.org/project/keyring/] `macOS Keychain` backend requires macOS 11+ and Python 3.8.7+ with `universal2` binary. Both satisfied by Python 3.12 on M-series.
- [CITED: GitHub keyring issue #457] On macOS, secrets stored by Python are accessible without password prompt to any Python script that uses the same interpreter — by design. Acceptable for vibemix (local app, no inter-process attack surface). Phase 18 signed .app gets keychain access automatically via codesigning; no entitlements needed for the keyring backend itself.
- **First-launch prompt:** macOS may show a system "allow access" dialog the very first time the Python process writes a keychain item. User clicks "Always Allow" → subsequent reads silent. If user clicks "Deny" → `KeyringError` raised on next access → fall back to file.

### Windows 11 behavior

- Same API: `keyring.get_password(service, username)` / `set_password(...)`. Windows Credential Manager is the backend, no prompt on first use.
- Phase 18 signed .exe gets credential-manager access automatically — no extra plumbing.

### Graceful failure pattern

```python
# src/vibemix/agent/install_uuid.py
"""Get-or-create the install_uuid for this vibemix install.

Order of precedence:
1. OS keychain (keyring) — fastest, OS-native security
2. Local file fallback — when keychain unavailable or user denied access
3. Generate fresh UUIDv4 — first launch
"""
from __future__ import annotations
import os
import sys
import uuid
import logging
from pathlib import Path

import keyring
import keyring.errors

log = logging.getLogger(__name__)

_SERVICE = "vibemix"
_ACCOUNT = "install_uuid"

def _fallback_path() -> Path:
    """Platform-appropriate path for the file fallback."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "vibemix"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home()))) / "vibemix"
    else:  # Linux excluded per CONTEXT but harmless fallback
        base = Path.home() / ".local" / "share" / "vibemix"
    base.mkdir(parents=True, exist_ok=True)
    return base / "install_uuid"

def _read_file() -> str | None:
    p = _fallback_path()
    if p.exists():
        v = p.read_text().strip()
        return v if len(v) == 32 and all(c in "0123456789abcdef" for c in v) else None
    return None

def _write_file(value: str) -> None:
    p = _fallback_path()
    p.write_text(value)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass  # Windows file perms model differs; best-effort

def get_or_create_install_uuid() -> str:
    """Return the persistent install UUID. Mints fresh UUIDv4 on first call."""
    # 1. Try keychain
    try:
        existing = keyring.get_password(_SERVICE, _ACCOUNT)
        if existing and len(existing) == 32:
            return existing
    except keyring.errors.KeyringError as e:
        log.warning("keychain read failed (%s) — using file fallback", e.__class__.__name__)
        # Fall through to file
        existing = _read_file()
        if existing:
            return existing
        new_uuid = uuid.uuid4().hex
        _write_file(new_uuid)
        return new_uuid

    # 2. No existing keychain value — try file (covers prior fallback installs)
    existing = _read_file()
    if existing:
        # Try to also seed keychain for next time
        try:
            keyring.set_password(_SERVICE, _ACCOUNT, existing)
        except keyring.errors.KeyringError:
            pass
        return existing

    # 3. Fresh install — mint UUIDv4
    new_uuid = uuid.uuid4().hex
    try:
        keyring.set_password(_SERVICE, _ACCOUNT, new_uuid)
    except keyring.errors.KeyringError as e:
        log.warning("keychain write failed (%s) — writing file fallback only", e.__class__.__name__)
        _write_file(new_uuid)
    return new_uuid
```

The JWT cache uses the same pattern with account `"jwt"`. The file fallback for JWT lives at `<base>/jwt`.

### Phase 18 implications

- Signed .app bundle on macOS: keychain access is granted automatically by codesigning identity. No `Keychain Access Groups` entitlement needed for a single-app keychain (only needed when sharing items across multiple apps in the same team).
- Signed .exe on Windows: Credential Manager access is per-user, no special entitlement.
- **The Tauri integration in Phase 11** [CONTEXT cross-reference] may use `tauri-plugin-keychain` on the Rust side. The Python sidecar can either: (a) keep its own Python-keyring access (each side reads the same Keychain service/account), OR (b) Tauri reads keychain, passes UUID + JWT to Python sidecar as env vars at spawn time. Decision deferred to Phase 11.

## Q5: Redis Daily-Quota INCR + EXPIRE NX

### Canonical pattern (async, single round-trip via pipeline)

```python
# proxy/app/quota.py
"""Daily per-UUID quota tracking via Redis."""
from datetime import datetime, timezone, timedelta
from typing import Optional
import redis.asyncio as redis_async

DAILY_QUOTA = 2000

class QuotaExceeded(Exception):
    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds

class QuotaClient:
    def __init__(self, redis_url: str):
        self._redis = redis_async.from_url(redis_url, decode_responses=True)

    async def consume(self, install_uuid: str) -> int:
        """
        Increment today's counter for install_uuid. Returns the new count.
        Raises QuotaExceeded if count > DAILY_QUOTA.

        Uses INCR + EXPIRE NX atomically via pipeline:
        - INCR: returns the new count (1 on first call, 2 on second, etc.)
        - EXPIRE NX 86400: sets 24h TTL only if key has no TTL (i.e. first
          call of day). Subsequent calls preserve the original expiry.
        """
        today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
        key = f"vibemix:quota:{install_uuid}:{today}"

        async with self._redis.pipeline(transaction=False) as pipe:
            pipe.incr(key)
            pipe.expire(key, 86400, nx=True)
            count, _ttl_set = await pipe.execute()

        if count > DAILY_QUOTA:
            # Retry-After until next UTC midnight
            now = datetime.now(tz=timezone.utc)
            tomorrow = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            retry_after = int((tomorrow - now).total_seconds())
            raise QuotaExceeded(retry_after_seconds=retry_after)

        return count

    async def close(self) -> None:
        await self._redis.close()
```

Route integration:

```python
# proxy/app/routes/llm.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from ..quota import QuotaExceeded

@router.post("/v1beta/models/{model}:streamGenerateContent")
@limiter.limit("60/minute")
async def llm_stream(request: Request, model: str):
    install_uuid = request.state.install_uuid
    try:
        await quota_client.consume(install_uuid)
    except QuotaExceeded as e:
        return JSONResponse(
            {"detail": "daily quota exceeded", "quota_daily": 2000},
            status_code=429,
            headers={"Retry-After": str(e.retry_after_seconds)},
        )
    # ... upstream pass-through (Q6)
```

### Why `transaction=False` on the pipeline

- We don't need MULTI/EXEC isolation here — INCR and EXPIRE NX are independently atomic, and reading the result of INCR doesn't require we block other clients. `transaction=False` is faster (no MULTI/EXEC wrapping).
- For strict counter-then-check correctness, `transaction=False` is also fine because INCR returns the *new* value, so we know exactly what count this request produced.

### `nx` parameter support

[CITED: https://redis.io/docs/latest/commands/expire/ + redis.readthedocs.io] `EXPIRE key seconds NX` was added in Redis 7.0. The proxy-side Redis on Bravoh's server should already be 7.x (Bravoh launched ~2025–2026). If Redis < 7.0 (verify with `INFO server`), use a LUA script fallback:

```lua
-- only-if-no-ttl.lua (server-side fallback for Redis < 7)
local ttl = redis.call("TTL", KEYS[1])
if ttl == -1 then  -- key exists, no expiry
    redis.call("EXPIRE", KEYS[1], ARGV[1])
end
return ttl
```

Verify Redis version at proxy startup. Log a warning if `< 7.0` and use LUA fallback.

### Retry-After computation

- **Per-day quota (429):** seconds until next UTC midnight (computed above).
- **Per-minute slowapi (429):** slowapi sets `Retry-After` automatically. Default header injection works because the decorator path runs through the standard exception handler `_rate_limit_exceeded_handler`.

## Q6: SSE Streaming Pass-through in FastAPI

### Canonical pattern

```python
# proxy/app/routes/llm.py
import asyncio
import json
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from google import genai
from google.genai import types

router = APIRouter()

# Proxy holds ITS OWN genai client with the real Gemini key.
# Initialized at app startup (proxy/app/main.py) and shared globally.
upstream_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

@router.post("/v1beta/models/{model}:streamGenerateContent")
@limiter.limit("60/minute")
async def llm_stream(request: Request, model: str):
    install_uuid = request.state.install_uuid
    await quota_client.consume(install_uuid)  # raises QuotaExceeded → 429

    # Parse the SDK-shaped request body
    body = await request.json()
    contents = body["contents"]
    config = body.get("generationConfig") or body.get("config") or {}

    async def stream_generator():
        """Yield raw SSE bytes from upstream Gemini to client."""
        try:
            async for chunk in upstream_client.aio.models.generate_content_stream(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(**config) if config else None,
            ):
                # Re-serialize each chunk to the SSE wire shape the client SDK expects:
                #   data: <json>\r\n\r\n
                # (The genai SDK calls back `parse_event` on each "data:" line.)
                payload = chunk.model_dump_json(exclude_none=True)
                yield f"data: {payload}\r\n\r\n".encode("utf-8")

                # Check client disconnect every chunk
                if await request.is_disconnected():
                    break
        except asyncio.CancelledError:
            # Client dropped — let upstream timeout naturally
            raise
        except Exception as e:
            # Surface upstream error as final SSE event
            err = {"error": {"code": 500, "message": str(e), "status": "INTERNAL"}}
            yield f"data: {json.dumps(err)}\r\n\r\n".encode("utf-8")

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # CRITICAL: disable nginx response buffering
        },
    )
```

### TTS pass-through (PCM bytes, not SSE)

```python
# proxy/app/routes/tts.py
import httpx
from fastapi.responses import StreamingResponse

OPENROUTER_KEY = os.environ["OPENROUTER_API_KEY"]
upstream_http = httpx.AsyncClient(timeout=60.0)

@router.post("/v1/audio/speech")
@limiter.limit("60/minute")
async def tts_speech(request: Request):
    install_uuid = request.state.install_uuid
    await quota_client.consume(install_uuid)

    body = await request.json()
    # body is OpenAI-shaped: {model, input, voice, response_format, instructions, ...}

    upstream_url = "https://openrouter.ai/api/v1/audio/speech"

    async def stream_pcm():
        async with upstream_http.stream(
            "POST",
            upstream_url,
            json=body,
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json",
            },
        ) as upstream_resp:
            if upstream_resp.status_code != 200:
                # surface error
                err_body = await upstream_resp.aread()
                raise HTTPException(status_code=upstream_resp.status_code, detail=err_body.decode())
            async for chunk in upstream_resp.aiter_bytes(chunk_size=4096):
                yield chunk
                if await request.is_disconnected():
                    break

    return StreamingResponse(
        stream_pcm(),
        media_type="audio/pcm",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

### Disconnect handling

- `await request.is_disconnected()` inside the generator [CITED: GitHub fastapi/discussions/7572] returns `True` once the client closes the TCP connection.
- Check is cheap — fine to call every yielded chunk.
- On disconnect: `break` out of the loop; the `async with upstream.stream(...)` context manager auto-closes the upstream connection on `__aexit__`.
- `asyncio.CancelledError` is propagated when the ASGI server cancels the task (e.g., shutdown) — re-raise it.

### Auth header forwarding

Yes, **the proxy is a man-in-the-middle by design**:
- **Inbound:** client sends `Authorization: Bearer <vibemix-jwt>`. JWT middleware verifies it, sets `req.state.install_uuid`.
- **Outbound (LLM):** the upstream `genai.Client(api_key=GEMINI_KEY)` adds `x-goog-api-key: AIza...` automatically. We pass through ZERO client headers to upstream.
- **Outbound (TTS):** we explicitly set `Authorization: Bearer <OPENROUTER_KEY>` on the upstream `httpx` request.

Client headers (other than auth) that we MAY want to forward: none for v1. Keep it minimal.

### nginx config note (NOT in this repo)

The existing nginx serving `api.altidus.world` likely has `proxy_buffering on` (default). For SSE to work, the vibemix proxy's nginx `location` block needs:

```nginx
location /v1beta/ {
    proxy_pass http://127.0.0.1:8788;
    proxy_buffering off;          # CRITICAL for SSE
    proxy_cache off;
    proxy_set_header Connection "";
    proxy_http_version 1.1;
    proxy_read_timeout 300s;      # long-running streams
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
```

Document this in `proxy/README.md` so Kaan can drop it into Bravoh's nginx config.

## Architecture Diagram

```text
                       VIBEMIX CLIENT (Tauri + Python sidecar)
                       ┌──────────────────────────────────────┐
                       │ install_uuid.py                       │
   First launch ────►  │   keyring("vibemix","install_uuid")   │ ◄── OS Keychain (mac)
                       │   fallback: ~/Library/.../install_uuid│         Credential Mgr (win)
                       │                                       │
   /register POST ───► │ proxy_client.build_proxy_genai(...)   │
                       │   genai.Client(                       │
                       │     api_key="vibemix-proxy",          │
                       │     http_options=HttpOptions(         │
                       │       base_url="https://api.altidus...│
                       │       headers={Authorization: Bearer..│
                       │     ))                                │
                       └──────────────────────┬────────────────┘
                                              │
                                              │ HTTPS + SSE
                                              ▼
                       ┌──────────────────────────────────────────┐
                       │ VIBEMIX PROXY (FastAPI on 77.42.28.93)   │
                       │                                          │
                       │  nginx /api/vibemix/ ──► uvicorn :8788   │
                       │                                          │
                       │  ┌── JWTMiddleware ──────────────┐       │
                       │  │ verify HS256, set state.uuid  │       │
                       │  └──────────────┬────────────────┘       │
                       │                 │                        │
                       │  ┌── @limiter.limit("60/min", key=uuid)  │
                       │  │  + quota_client.consume(uuid)         │
                       │  │     INCR + EXPIRE NX 86400 (Redis)    │
                       │  └──────────────┬────────────────┘       │
                       │                 │                        │
                       │  ┌── Route: /v1beta/models/{m}:stream... │
                       │  │   upstream = genai.Client(GEMINI_KEY) │
                       │  │   async for chunk in stream:          │
                       │  │     yield f"data: {json}\r\n\r\n"     │
                       │  │     if request.is_disconnected: break │
                       │  └──────────────┬────────────────┘       │
                       │                 │                        │
                       │  ┌── Route: /v1/audio/speech ──┐         │
                       │  │   httpx.AsyncClient.stream  │         │
                       │  │     → openrouter.ai/v1/...  │         │
                       │  │     yield pcm bytes         │         │
                       │  └──────────────┬───────────────┘        │
                       │                 │                        │
                       └─────────────────┼────────────────────────┘
                                         │
              ┌──────────────────────────┼───────────────────────┐
              ▼                          ▼                       ▼
  generativelanguage.googleapis.com   openrouter.ai/api/v1   Redis :6379
       (SSE + AIza key)                (PCM + OR key)        (rate + quota)
```

## Standard Stack

### Server (`proxy/`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | >=0.115.0 | Web framework | Bravoh stack default; async-first |
| uvicorn[standard] | >=0.32.0 | ASGI server | FastAPI canonical |
| pyjwt | >=2.12.1 | JWT issue/verify | FastAPI tutorial default; CVE fix |
| slowapi | >=0.1.9 | Rate limit decorator | Lightweight, Redis-backed |
| redis | >=5.0.0 | Async client (`redis.asyncio`) | Bravoh stack default |
| google-genai | >=2.0.1 | Upstream Gemini client | Same SDK vibemix client uses |
| httpx | >=0.28.0 | OpenRouter upstream | Async streaming; transitive dep anyway |
| pydantic | >=2.13.0 | Request/response validation | FastAPI canonical |
| python-dotenv | >=1.0.0 | `.env` loading | Standard pattern |

### Client (`src/vibemix/agent/`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| keyring | >=25.7.0 | OS keychain access | jaraco/keyring is the canonical Python wrapper |
| google-genai | >=2.0.1 (pinned by vibemix already) | LLM client (proxy or direct) | Same in both modes |
| livekit-plugins-openai | >=1.5.8 (pinned by vibemix already) | TTS client (proxy or direct) | Same in both modes |

### Dev / test

| Library | Version | Purpose |
|---------|---------|---------|
| pytest | >=8.0 | Test runner |
| pytest-asyncio | >=0.23 | `async def` test support |
| httpx | >=0.28 | `httpx.AsyncClient(transport=ASGITransport(app=...))` for in-process testing |
| fakeredis | >=2.20 | Redis stand-in for unit tests |

**Installation (proxy):**

```bash
cd proxy
python3.12 -m venv .venv
source .venv/bin/activate
pip install fastapi>=0.115 'uvicorn[standard]>=0.32' pyjwt>=2.12.1 slowapi>=0.1.9 \
    redis>=5.0 google-genai>=2.0.1 httpx>=0.28 pydantic>=2.13 python-dotenv>=1.0
pip install --group dev pytest>=8 pytest-asyncio>=0.23 fakeredis>=2.20
```

### Version verification (run before locking)

```bash
# Confirm latest versions at planning time
npm view pyjwt version  # nope — pip view
pip index versions pyjwt
pip index versions slowapi
pip index versions keyring
pip index versions redis
pip index versions fastapi
```

**Verified versions (2026-05-11):**
- PyJWT: 2.12.1 (published 2026-03-13) — `pip install pyjwt>=2.12.1` [VERIFIED: PyPI]
- keyring: 25.7.0 (published 2025-11-16) — `pip install keyring>=25.7.0` [VERIFIED: PyPI]
- slowapi: 0.1.9 (last release ~2023, stable) — `pip install slowapi>=0.1.9` [VERIFIED: PyPI]
- redis-py: 5.x / 7.x line — pin `redis>=5.0` [VERIFIED]
- fastapi: 0.115+ — Bravoh stack default [CITED: CONTEXT]
- google-genai: 2.0.1 published 2026-05-09 [VERIFIED: vibemix .venv]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT encode/verify | bespoke HMAC | `pyjwt` | RFC compliance, CVE patching, exp/iat handling |
| Rate limit windowing | counters in Python dict | `slowapi` + Redis | Restart-safe, multi-worker-safe, exact-RFC `Retry-After` |
| OS keychain access | bespoke `security` CLI calls | `keyring` | Cross-platform parity (mac/win), graceful no-backend fallback |
| SSE wire format | string concat for `data:` lines | `genai.Client` re-serialization | SDK already knows the exact format upstream wants |
| Async Redis pipeline | one-command-at-a-time | `redis.asyncio.pipeline()` | One round-trip, atomic guarantees |
| HTTP streaming upstream | `aiohttp` from scratch | `httpx.AsyncClient.stream()` | Already a transitive dep; cleaner async-with API |
| ASGI in-process test client | manual ASGI invocation | `httpx.AsyncClient(transport=ASGITransport(app=app))` | First-party FastAPI test pattern |
| `.env` parsing | manual `os.environ.get` chain | `python-dotenv` | Standard, already used |
| Pydantic request validation | manual dict-key checks | `BaseModel` + FastAPI route param types | FastAPI auto-generates OpenAPI schema for free |

**Key insight:** the entire phase is about *re-using* upstream SDKs (`google-genai`, `openai_plugin`) by pointing them at the proxy. Re-implementing the SSE wire format in either direction (server or client) is a multi-week rabbit hole. Don't.

## Common Pitfalls

### Pitfall 1: SDK URL shape mismatch

**What goes wrong:** Proxy mounts route at `/api/vibemix/v1/llm/generate`, but `genai.Client` calls `{base_url}/v1beta/models/{model}:streamGenerateContent?alt=sse`. Client gets 404.

**Why it happens:** The SDK has hardcoded URL builders. `base_url` only swaps the host+root; the `/v1beta/models/...` suffix is non-negotiable without monkey-patching.

**How to avoid:**
- Option A: nginx-rewrite `/api/vibemix/v1/llm/(.*)$ → /v1beta/$1` (see Q1 option A).
- Option B: Mount routes at the Gemini-native paths in the FastAPI app, accept that `/api/vibemix/v1/llm/generate` is not the proxy URL the SDK uses (recommended).

**Warning signs:** First end-to-end test returns 404. `nginx access.log` shows the un-rewritten path.

### Pitfall 2: nginx buffering breaks SSE

**What goes wrong:** Client receives the entire stream in one chunk after upstream completes, instead of token-by-token.

**Why it happens:** nginx's `proxy_buffering on` (default) holds the response until either the buffer fills or the upstream closes.

**How to avoid:**
- Set `proxy_buffering off` in the nginx `location` block.
- ALSO set `X-Accel-Buffering: no` response header on every `StreamingResponse` (in case nginx upstream sees X-Accel and acts on it).

**Warning signs:** Reactions feel "batched" rather than incremental. `curl -N <proxy>` works fine but the production binary doesn't.

### Pitfall 3: slowapi `@limit` requires `request: Request` in signature

**What goes wrong:** Decorator is silently a no-op. No rate limiting happens.

**Why it happens:** slowapi inspects the route signature for a `request: Request` parameter. If absent, it skips rate limiting entirely (does not raise — silent fail).

**How to avoid:** Every rate-limited route MUST have `request: Request` as the first parameter (or any parameter). Add a CI lint or a test that asserts `429` is returned at 61st call.

**Warning signs:** Load test shows no 429 at high rate. `slowapi`'s rate-limit headers (`X-RateLimit-Limit`, etc.) missing from response.

### Pitfall 4: Redis `EXPIRE key seconds NX` requires Redis 7.0+

**What goes wrong:** Older Redis silently ignores the `NX` flag and resets TTL on every request. Result: counter never expires; quota persists forever for active users.

**Why it happens:** `NX` option added in Redis 7.0. On 6.x, the command is parsed but the NX modifier is ignored.

**How to avoid:**
- Verify `INFO server redis_version` on the deployment server before launch.
- Document Redis 7.0+ requirement in `proxy/README.md`.
- If Redis < 7.0: use LUA script (see Q5 fallback). Or upgrade Redis — Bravoh already on 7.x most likely.

**Warning signs:** Quota counters never reset; users hit 429 perpetually after first heavy day.

### Pitfall 5: PyJWT < 2.12.1 has CVE-2026-32597

**What goes wrong:** PyJWT accepts unknown `crit` header extensions, violating RFC 7515. Attacker could craft a token with crafted `crit` headers that bypass downstream validation logic.

**Why it happens:** Bug in PyJWT versions prior to 2.12.1.

**How to avoid:** Pin `pyjwt>=2.12.1` in `proxy/pyproject.toml`. CI dep-update bot should auto-bump.

**Warning signs:** `safety check` / `pip-audit` flags pyjwt.

### Pitfall 6: keyring silent failure on `set_password`

**What goes wrong:** `keyring.set_password(...)` succeeds silently against the `null` backend (when no real backend is installed). Next `get_password` returns `None`. Client mints a fresh UUID on every launch.

**Why it happens:** Some macOS dev setups (especially Python via Homebrew without universal2 binary) end up with a `null` backend.

**How to avoid:**
- At app startup, call `keyring.get_keyring()` and log the backend class name. If it's `keyring.backends.null.Keyring`, force file fallback.
- Test: `keyring set vibemix test` → `keyring get vibemix test` must round-trip.
- Use Python from the official python.org installer or pyenv (both ship universal2 with working keychain backend).

**Warning signs:** Every launch generates a different `install_uuid` (visible in proxy logs as fresh `/register` calls).

### Pitfall 7: `request.is_disconnected()` overhead

**What goes wrong:** Calling `await request.is_disconnected()` every chunk adds ASGI receive() overhead. For high-frequency streams (audio PCM at ~24kHz), this can add measurable latency.

**Why it happens:** Each call awaits a receive() on the ASGI message queue.

**How to avoid:** Check every Nth chunk (e.g. every 10 chunks for LLM tokens, every 50 chunks for PCM bytes). Adjust based on chunk size.

**Warning signs:** PCM stream stutters or measurable latency added on large messages.

### Pitfall 8: BaseHTTPMiddleware performance

**What goes wrong:** JWT middleware adds 5x request overhead due to BaseHTTPMiddleware internals.

**Why it happens:** Known Starlette performance issue [CITED: slowapi issue #195].

**How to avoid:** For v1 with low traffic (per-UUID 60 rpm cap, single proxy instance), BaseHTTPMiddleware is fine — overhead is ~milliseconds per request, dwarfed by upstream Gemini latency. If profiling shows a problem in production, port to pure ASGI middleware:

```python
class JWTASGIMiddleware:
    def __init__(self, app): self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        # ... extract headers from scope["headers"], verify JWT, mutate scope["state"]
        await self.app(scope, receive, send)
```

**Warning signs:** p99 proxy latency > 100ms for the JWT verify step (measurable via structured logs).

## Common Patterns

### Pattern 1: Proxy-client mode dispatch (vibemix-side)

```python
# src/vibemix/agent/llm_factory.py
def build_llm(
    api_key: Optional[str] = None,
    *,
    mode: Literal["direct", "proxy"] = "direct",
    proxy_base_url: Optional[str] = None,
    jwt: Optional[str] = None,
):
    if mode == "direct":
        if not api_key:
            raise ValueError("direct mode requires api_key")
        return genai.Client(api_key=api_key)
    if mode == "proxy":
        if not (proxy_base_url and jwt):
            raise ValueError("proxy mode requires proxy_base_url and jwt")
        return build_proxy_genai_client(jwt=jwt, proxy_base_url=proxy_base_url)
    raise ValueError(f"unknown mode: {mode}")
```

### Pattern 2: Structured request log line

```python
# proxy/app/middleware/logging.py
import time, json, logging
log = logging.getLogger("vibemix.proxy")

class StructuredLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        latency_ms = int((time.monotonic() - start) * 1000)
        log.info(json.dumps({
            "ts": time.time(),
            "install_uuid": getattr(request.state, "install_uuid", None),
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": latency_ms,
        }))
        return response
```

### Pattern 3: Circuit breaker on consecutive upstream 5xx

```python
# proxy/app/upstream.py
class CircuitBreaker:
    def __init__(self, threshold=10, cooldown_sec=60):
        self.threshold = threshold
        self.cooldown_sec = cooldown_sec
        self._fail_streak = 0
        self._open_until: Optional[float] = None

    def allow(self) -> bool:
        if self._open_until and time.time() < self._open_until:
            return False
        return True

    def record_success(self):
        self._fail_streak = 0
        self._open_until = None

    def record_failure(self):
        self._fail_streak += 1
        if self._fail_streak >= self.threshold:
            self._open_until = time.time() + self.cooldown_sec

    def retry_after(self) -> int:
        if self._open_until:
            return max(1, int(self._open_until - time.time()))
        return 0
```

Use:
```python
if not breaker.allow():
    return JSONResponse(
        {"detail": "upstream unavailable"},
        status_code=503,
        headers={"Retry-After": str(breaker.retry_after())},
    )
try:
    result = await call_upstream(...)
    breaker.record_success()
except Exception:
    breaker.record_failure()
    raise
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| python-jose | PyJWT (FastAPI default) | 2024-2025 | Cleaner exceptions, ~25% faster verify, active maintenance |
| `aioredis` separate package | `redis.asyncio` in `redis-py` 5.x | redis-py 4.2+ | One dep instead of two |
| EXPIRE without NX in two commands | `EXPIRE key sec NX` single command | Redis 7.0 (2022) | Atomic; eliminates race window |
| `SlowAPIMiddleware` (BaseHTTPMiddleware) | `@limiter.limit` decorator OR `SlowAPIASGIMiddleware` | slowapi 0.1.7+ | Avoids BaseHTTPMiddleware perf hit |
| Bespoke SSE byte handling | `genai.aio.models.generate_content_stream` re-serialize | google-genai 1.x → 2.x | Less code; SDK handles wire format |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | proxy + client | ✓ | 3.12 in vibemix venv | — |
| Redis 7.0+ | proxy quota + slowapi storage | Probably ✓ on Bravoh server | Verify with `INFO server` | LUA script for < 7.0 |
| nginx | reverse proxy | ✓ on Bravoh server | Existing api.altidus.world setup | direct uvicorn for dev |
| Docker | deployment | ✓ on Bravoh server | Used by Bravoh stack | — |
| PM2 | process supervision | ✓ on Bravoh server | Used by Bravoh stack | systemd alternative |
| macOS Keychain | install_uuid storage | ✓ via `keyring` | macOS 11+ requirement satisfied | file fallback |
| Windows Credential Manager | install_uuid storage (v1 Windows) | ✓ via `keyring` | Built-in | file fallback |

**No blocking missing dependencies.** All required pieces are part of Bravoh's existing stack.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8.0 + pytest-asyncio >=0.23 |
| Config file | `proxy/pyproject.toml` (asyncio_mode = "auto") + `tests/conftest.py` |
| Quick run command | `pytest proxy/tests/ -x -q` |
| Full suite command | `pytest proxy/tests/ src/vibemix/agent/tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROXY-01 | Proxy app boots, OpenAPI schema generated | unit | `pytest proxy/tests/test_app.py::test_openapi_schema_generated -x` | ❌ Wave 0 |
| PROXY-02 | LLM SSE stream returns text/event-stream + chunks | integration | `pytest proxy/tests/test_llm.py::test_stream_passthrough -x` | ❌ Wave 0 |
| PROXY-03 | TTS PCM stream returns audio/pcm + chunked bytes | integration | `pytest proxy/tests/test_tts.py::test_pcm_passthrough -x` | ❌ Wave 0 |
| PROXY-04 | JWT middleware rejects missing/expired/invalid token | unit | `pytest proxy/tests/test_auth.py -x` | ❌ Wave 0 |
| PROXY-05 | 61st request in same minute returns 429 + Retry-After | integration | `pytest proxy/tests/test_rate_limit.py::test_60_per_minute -x` | ❌ Wave 0 |
| PROXY-05 | 2001st request in same day returns 429 + Retry-After | integration | `pytest proxy/tests/test_quota.py::test_2000_per_day -x` | ❌ Wave 0 |
| PROXY-06 | 10 consecutive upstream 5xx → 503 for 60s | unit | `pytest proxy/tests/test_circuit_breaker.py -x` | ❌ Wave 0 |
| PROXY-07 | /register returns JWT with 90-day exp | unit | `pytest proxy/tests/test_register.py -x` | ❌ Wave 0 |
| CLIENT-01 | get_or_create_install_uuid persists across calls | unit | `pytest src/vibemix/agent/tests/test_install_uuid.py -x` | ❌ Wave 0 |
| CLIENT-01 | keyring failure → file fallback used | unit | `pytest src/vibemix/agent/tests/test_install_uuid.py::test_keyring_failure_fallback -x` | ❌ Wave 0 |
| CLIENT-02 | build_proxy_genai_client returns Client with correct base_url + Bearer header | unit | `pytest src/vibemix/agent/tests/test_proxy_client.py::test_genai_base_url -x` | ❌ Wave 0 |
| CLIENT-03 | build_proxy_tts_chain returns chain with correct base_url + api_key | unit | `pytest src/vibemix/agent/tests/test_proxy_client.py::test_tts_chain -x` | ❌ Wave 0 |
| CLIENT-05 | mode=proxy + missing JWT → loud error, no fallback | unit | `pytest src/vibemix/agent/tests/test_llm_factory.py::test_proxy_mode_requires_jwt -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest proxy/tests/ -x -q` (fast subset)
- **Per wave merge:** full suite green
- **Phase gate:** `/gsd-verify-work` runs full suite + binary `strings` audit (zero `AIza` matches in any client-mode shipped file).

### Wave 0 Gaps
- [ ] `proxy/pyproject.toml` — declare deps + dev deps
- [ ] `proxy/tests/conftest.py` — shared fixtures (fakeredis, httpx AsyncClient, ASGI transport)
- [ ] `proxy/tests/test_app.py` — boot smoke test
- [ ] `proxy/tests/test_auth.py` — JWT middleware
- [ ] `proxy/tests/test_register.py`
- [ ] `proxy/tests/test_llm.py` — SSE pass-through (mock upstream genai.Client)
- [ ] `proxy/tests/test_tts.py` — PCM pass-through (mock upstream httpx)
- [ ] `proxy/tests/test_rate_limit.py`
- [ ] `proxy/tests/test_quota.py`
- [ ] `proxy/tests/test_circuit_breaker.py`
- [ ] `src/vibemix/agent/tests/test_install_uuid.py`
- [ ] `src/vibemix/agent/tests/test_proxy_client.py`
- [ ] `src/vibemix/agent/tests/test_llm_factory.py` (extend existing)
- [ ] Framework install: `pip install pytest>=8 pytest-asyncio>=0.23 fakeredis>=2.20`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | PyJWT HS256 + install-UUID-bound bearer |
| V3 Session Management | partial | 90-day JWT TTL with idempotent refresh via /register |
| V4 Access Control | yes | Per-UUID rate limit + quota; circuit breaker; no admin endpoints |
| V5 Input Validation | yes | pydantic models on all request bodies; UUID regex `^[0-9a-f]{32}$` |
| V6 Cryptography | yes | PyJWT (do not hand-roll HMAC); JWT_SECRET from env never logged |
| V7 Error Handling | yes | Catch all upstream exceptions; no stack traces in 5xx responses |
| V9 Communication | yes | HTTPS-only at nginx; HSTS via existing api.altidus.world config |
| V14 Configuration | yes | All secrets via env vars; `.env.example` documents required keys |

### Known Threat Patterns for FastAPI + JWT proxy

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| JWT signature forgery | Tampering | HS256 with 256-bit JWT_SECRET from env |
| JWT replay after theft | Spoofing | Per-UUID rate limit caps damage; document risk |
| JWT `none` algorithm bypass | Tampering | `jwt.decode(..., algorithms=["HS256"])` — never `algorithms=None` |
| Rate limit bypass via spoofed key_func input | Spoofing | key_func reads ONLY `req.state.install_uuid` set by JWT mw; never from client header |
| Quota counter race | Tampering | Redis INCR is atomic; pipeline EXPIRE NX is single round-trip |
| Upstream API key exfiltration | Information Disclosure | Phase 5's whole point: keys NEVER leave server. Verify with `strings` audit. |
| SSRF via proxied upstream | Spoofing | Upstream URL is hardcoded constant; never user-controlled |
| nginx response buffering breaks SSE | DoS (latency) | `proxy_buffering off` + `X-Accel-Buffering: no` |
| Slow loris / long-lived stream exhaust workers | DoS | uvicorn `--limit-concurrency` cap; `proxy_read_timeout 300s` (not infinite) |
| install_uuid collision | Spoofing | UUIDv4 collision probability negligible; document |
| Stolen JWT used from different IP | Spoofing | Out of scope v1 (no IP binding); per-UUID rate limit is the only defense |
| Log injection via install_uuid | Tampering | UUID is regex-validated; only hex chars; log as JSON string |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Bravoh's Redis on 77.42.28.93 is Redis 7.0+ | Q5 | If 6.x, must use LUA fallback; verify at deploy |
| A2 | Bravoh's nginx already terminates TLS for api.altidus.world | Q6 | If not, proxy uvicorn would need TLS; unlikely |
| A3 | PyJWT verify performance gain (~25%) over python-jose | Q3 | Low impact; either lib works functionally |
| A4 | macOS Sequoia signed .app gets keychain access without entitlements | Q4 | Phase 18 may discover entitlement need; doc as Phase 18 risk |
| A5 | Token theft trade-off (90-day TTL) is acceptable to Kaan | Q3 | Could shorten to 30 days; trivial config change |
| A6 | Single-region proxy latency (EU) is acceptable for US/JP users | Architecture | Multi-region is Deferred per CONTEXT |
| A7 | `is_disconnected()` overhead negligible at LLM token rates | Pitfall 7 | Measure at Wave 1 verification |
| A8 | OpenRouter `/v1/audio/speech` accepts the same body shape v4 uses | Q6 TTS | v4 already proves this; verify against OpenRouter latest docs at impl time |

**Items requiring user confirmation during discuss or impl:**
- A1 (Redis version) — check at impl Wave 0 with `redis-cli -h 77.42.28.93 INFO server`
- The Q1 route-shape decision (option A vs B in pitfalls) — discuss with Kaan before Wave 1.

## Open Questions

1. **Route prefix decision: `/api/vibemix/v1/llm/...` (CONTEXT) vs `/v1beta/models/...` (SDK-native)?**
   - What we know: SDK builds URLs as `{base_url}/v1beta/models/{model}:streamGenerateContent?alt=sse`. CONTEXT-specified route shape doesn't match.
   - What's unclear: Whether Kaan prefers nginx-rewrite (preserves CONTEXT shape) or app-native paths (cleaner, no rewrite layer).
   - Recommendation: Surface in plan-checker; default to option B (app-native paths) and let Kaan veto in code review.

2. **JWT_SECRET rotation policy?**
   - What we know: Rotating JWT_SECRET invalidates ALL outstanding JWTs (90-day TTL × all users). Forces every client to re-register.
   - What's unclear: Whether to ever rotate, and the operational story for forced re-registration.
   - Recommendation: Document in `proxy/README.md`: "rotate only on suspected compromise; clients re-register transparently next launch via JWT refresh logic."

3. **Should the proxy log full request bodies?**
   - What we know: Bodies include user audio + screen JPEGs. PII risk.
   - What's unclear: Whether to log bodies (debug help) or strip (privacy).
   - Recommendation: Log structured metadata only (route, status, latency, install_uuid prefix). Never log bodies.

4. **What's the install_uuid → user-actionable-debug-id mapping?**
   - What we know: When a user reports "vibemix doesn't work," support needs the install_uuid to look up their logs.
   - What's unclear: How does a user retrieve their install_uuid? Hidden in keychain.
   - Recommendation: Phase 11 calibration wizard exposes "show install ID" in About panel.

## Sources

### Primary (HIGH confidence)
- Read `.venv/lib/python3.12/site-packages/google/genai/client.py` — `Client.__init__` signature, `http_options` plumbing [VERIFIED]
- Read `.venv/lib/python3.12/site-packages/google/genai/types.py` — `HttpOptions` class fields [VERIFIED]
- Read `.venv/lib/python3.12/site-packages/google/genai/_base_url.py` — base_url priority resolution [VERIFIED]
- Read `.venv/lib/python3.12/site-packages/google/genai/_api_client.py` — header merging, URL building [VERIFIED]
- Read `.venv/lib/python3.12/site-packages/livekit/plugins/openai/tts.py` — `TTS.__init__(base_url=...)` [VERIFIED]
- `cohost_v4.py:1998` — already-proven openai_plugin base_url against OpenRouter [VERIFIED]
- https://pypi.org/project/PyJWT/ — PyJWT 2.12.1 (2026-03-13) latest
- https://pypi.org/project/keyring/ — keyring 25.7.0 (2025-11-16) latest
- https://github.com/googleapis/python-genai — SDK README with HttpOptions example

### Secondary (MEDIUM confidence)
- https://github.com/laurentS/slowapi — slowapi readme + examples
- https://github.com/laurentS/slowapi/issues/195 — BaseHTTPMiddleware perf discussion
- https://fastapi.tiangolo.com/tutorial/server-sent-events/ — FastAPI SSE
- https://github.com/fastapi/fastapi/discussions/7572 — `is_disconnected` pattern
- https://redis.io/docs/latest/commands/expire/ — EXPIRE NX added in Redis 7.0
- https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html — async pipeline
- https://pyjwt.readthedocs.io/en/stable/usage.html — encode/decode patterns
- https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ — PyJWT in FastAPI tutorial
- https://fastapi.tiangolo.com/advanced/middleware/ — middleware ordering

### Tertiary (LOW confidence — flagged for verification at impl)
- https://linuxsecurity.com/advisories/suse/python-pyjwt-suse-2026-20839-1 — CVE-2026-32597 (verify via `pip-audit` at impl)
- https://johal.in/jwt-secure-tokens-pyjwt-best-practices-for-api-auth-2026/ — perf comparison snippet
- https://github.com/jaraco/keyring/issues/457 — macOS keychain access semantics

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every version verified against PyPI / installed venv
- Architecture: HIGH — direct SDK probing answered the Q1 pivotal question
- slowapi ordering: HIGH — verified by reading slowapi source via WebFetch
- Redis pattern: MEDIUM — confirmed via multiple sources; LUA fallback documented for < Redis 7
- keyring fallback: HIGH — official docs explicit on behavior
- SSE pass-through: HIGH — well-documented FastAPI pattern

**Research date:** 2026-05-11
**Valid until:** 2026-06-11 (30 days — most pieces stable; PyJWT may have a new release before then but pinned floor is safe)
