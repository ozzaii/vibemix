# KAAN-ACTION: Bravoh proxy needs `models:embedContent` route

**Status:** blocking for production grounding (Plan 28-04)
**Discovered:** 2026-05-15 by `scripts/probe_proxy_embed.py`
**Affects:** Phase 28 plans 28-03 (vibe-search), 28-04 (grounding), 28-05 (similar), 28-06 (importer), 28-08 (budget telemetry)
**Blocked surface:** every Phase 28 path that calls Gemini Embedding 2 in production

## What the probe found

```
$ python scripts/probe_proxy_embed.py
{
  "status": "endpoint_missing",
  "http_status": 404,
  "url": "https://api.altidus.world/v1beta/models/gemini-embedding-2:embedContent",
  "body_preview": "{\"detail\":\"Not Found\"}",
  "remediation": "Bravoh proxy does NOT route models:embedContent. ..."
}
```

The Bravoh proxy at `api.altidus.world` currently routes `generateContent` /
`streamGenerateContent` (Gemini text-gen) but NOT `embedContent` (the
Gemini Embedding 2 endpoint Phase 28 needs).

## What Kaan needs to do

Add the `models:embedContent` route to the Bravoh-side reverse proxy
(currently FastAPI per `proxy/main.py`). Same pass-through shape as
`generateContent` — just a different upstream path.

Concrete diff (FastAPI proxy, illustrative):

```python
@app.post("/v1beta/models/{model}:embedContent")
async def embed_proxy(model: str, request: Request, ...):
    upstream_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"
    body = await request.json()
    headers = {"x-goog-api-key": GEMINI_API_KEY, ...}
    async with httpx.AsyncClient() as client:
        r = await client.post(upstream_url, json=body, headers=headers)
    return Response(r.content, status_code=r.status_code, media_type="application/json")
```

Per-client rate limit (P56 cost ceiling at €50/month for vibemix):
suggest 50 embed requests/day/client.

## Test bypass while blocked

The Phase 28 test suites all mock `client.models.embed_content`, so unit +
integration tests run green without the proxy route. The end-to-end probe
script lives at `scripts/probe_proxy_embed.py` and is the canary —
re-running it after the proxy patch should return:

```
$ python scripts/probe_proxy_embed.py
{
  "status": "ok",
  "http_status": 200 | 401 | 403,
  ...
}
```

Plan 28-04 ships the production code path; the route gap means production
grounding fires `decision="below_threshold"` (graceful degradation) until
the proxy is patched. No vibemix code change needed once the route exists.

## Verification once unblocked

1. `python scripts/probe_proxy_embed.py` exits 0
2. Live `vibemix library search "techno"` returns non-empty results (with a
   library imported)
3. Live session emits `[track:<id>]` citations on track changes (Phase 16
   ear-test confirms via Kaan listening)
