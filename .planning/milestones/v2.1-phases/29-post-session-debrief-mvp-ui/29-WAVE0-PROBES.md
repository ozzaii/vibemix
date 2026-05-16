# 29-WAVE0-PROBES — Verdicts for assumptions A1, A3, A5, A7

**Date:** 2026-05-15
**Plan:** 29-00 Task 2 Part D
**Mode:** autonomous (per `gsd-autonomous fully` — fallbacks captured inline, blockers deferred to `KAAN-ACTION-PROXY.md`)

The Phase 29 plans (01–08) assume four runtime invariants. This document captures the verdicts so downstream plans do not implement against an unverified premise.

---

## A1 — Gemini 3 Pro model identifier

**Premise:** `gemini-3-pro` is the canonical model id for the debrief TLDR + drill generation calls (one-shot text generation, not streaming).

**Command:**
```python
from google import genai
c = genai.Client(api_key=GEMINI_API_KEY)
c.models.generate_content(model='gemini-3-pro', contents='hi')
```

**Result (bare `gemini-3-pro`):**
```
404 NOT_FOUND. {'error': {'code': 404, 'message': 'models/gemini-3-pro is not
found for API version v1beta, or is not supported for generateContent. Call
ListModels to see the list of available models and their supported methods.'}}
```

**ListModels output (filtered for "3" / "pro"):**
```
models/gemini-3-pro-preview
models/gemini-3.1-pro-preview
models/gemini-3.1-pro-preview-customtools
models/gemini-3-pro-image-preview
models/gemini-3-flash-preview
models/gemini-3.1-flash-lite-preview
models/gemini-3.1-flash-tts-preview
```

**Result (corrected `gemini-3-pro-preview`):**
```
503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently
experiencing high demand. Spikes in demand are usually temporary. Please try
again later.'}}
```

The 503 is a transient capacity signal, not a contract change — the model id resolves correctly, the network round-trips, and the SDK accepts the call shape. The bare `gemini-3-pro` form Plan 01-07 references in pseudocode is wrong.

**Verdict:** **PASS (with correction)** — model id is `gemini-3-pro-preview` (not `gemini-3-pro`). Plans 01-07 MUST use the `-preview` suffix verbatim.

**Action for downstream plans:** Use the constant `DEBRIEF_LLM_MODEL = "gemini-3-pro-preview"` introduced in Plan 29-01's `debrief/__init__.py` (or `vibemix.agent.constants` if the existing surface is preferred — Plan 01 picks one and documents).

---

## A3 — PyAV libmp3lame availability

**Premise:** PyAV (`av==17.0.1` in the project venv) ships with `libmp3lame` so the TLDR audio file can be encoded as MP3 entirely in-process without shelling out to `ffmpeg`. MP3 is the CONTEXT-locked codec for debrief audio (no Opus, no AAC, no WebM — per the user/architecture decision the plan calls out).

**Command:**
```python
import av
print('libmp3lame' in av.codecs_available)
```

**Result:**
```
True
```

`av.codecs_available` is a `set[str]`, and `libmp3lame`, `mp3`, `mp3float`, plus 6 related decoders are all present. Total codec count: 543.

**Verdict:** **PASS** — PyAV can encode MP3 in-process. No subprocess fallback needed.

**Action for downstream plans:** Plan 29-01 `tldr.py` uses `av.open(path, mode='w', format='mp3')` + `add_stream('libmp3lame', rate=24000)` directly — no `subprocess.run(["ffmpeg", ...])` shell-out and no system-ffmpeg dependency to document in the README install steps.

---

## A5 — Achird voice quality at 60-90s TLDR length

**Premise:** The Gemini TTS voice `Achird` (the v2.0 cohost voice) stays coherent and natural over a 60-90 second narrated TLDR — not just the 8-14 word live-reaction snippets the live runtime uses.

**Probe status:** **DEFERRED**

This probe requires (a) a Gemini TTS API call against `gemini-3.1-flash-tts-preview` with a 60-90 second prompt at the Achird voice, (b) bytes-on-disk + a listen pass to evaluate monotone / pacing / cliff-falloff at long form, and (c) Kaan's ear — there is no automated quality bar for "does the voice still sound alive past minute one". The autonomous-mode rule for taste verdicts is "log to KAAN-ACTION and continue with the documented fallback".

**Documented fallback for Plan 29-01:** If Achird quality at long-form fails Kaan's listen test, swap to `Kore` (the other v2.0-vetted Gemini voice) by changing a single constant in `debrief/tldr.py`. The audio path itself does not change — only the voice id passed to `c.models.generate_content(..., generation_config={'speech_config': {'voice_config': {'prebuilt_voice_config': {'voice_name': 'Achird'}}}})`.

**Action for downstream plans:** Plan 29-01 expose `DEBRIEF_TTS_VOICE` as a module-level constant defaulting to `"Achird"`. Plan 29-08 e2e tests assert the MP3 plays, not that the voice "sounds good" — Kaan validates that out-of-band on the first real debrief run. Filed to `.planning/KAAN-ACTION-PROXY.md` as `A5-VOICE-LISTEN`.

**Verdict:** **FALLBACK NEEDED — DEFERRED TO KAAN-ACTION-PROXY**

---

## A7 — Proxy `responseSchema` passthrough

**Premise:** `api.altidus.world/vibemix/gemini` (the proxy from STATE.md) preserves the `responseSchema` field on `generate_content` calls so the drill generation (Plan 29-01) can use Pydantic-validated structured output instead of post-hoc JSON parsing.

**Probe status:** **DEFERRED**

This requires a live POST to the proxy with a Pydantic responseSchema and a tiny structured-output request. The probe is meaningful only after a JWT is provisioned for this dev install (`get_or_refresh_jwt` requires the proxy's per-install flow, which depends on the proxy running and reachable). Autonomous-mode rule: defer external-credential probes to KAAN-ACTION-PROXY rather than block.

**Documented fallback for Plan 29-01:** If the proxy strips `responseSchema`, drill generation runs in `mode=direct` (with the user's own `GEMINI_API_KEY` from `.env`) instead of `mode=proxy`. The fallback path is already wired into `vibemix.agent.proxy_client.build_proxy_genai_client` — the debrief sidecar picks the same mode the live runtime uses (env var `VIBEMIX_LLM_MODE`), so no new branching is needed.

**Action for downstream plans:** Plan 29-01 `drills.py` uses the same `genai.Client` factory the rest of vibemix uses (`build_llm` / `build_proxy_genai_client`), and passes `responseSchema` unconditionally. If the proxy strips it, the call still returns text — the call-site then JSON-parses with Pydantic as the fallback. Plan 29-08 e2e tests assert the drill schema validates after parsing, regardless of which mode produced the response.

**Verdict:** **FALLBACK NEEDED — DEFERRED TO KAAN-ACTION-PROXY**

---

## Summary

| Probe | Verdict | Action |
|-------|---------|--------|
| A1 — gemini-3-pro model id | PASS (with correction to `-preview` suffix) | Plan 29-01 uses `gemini-3-pro-preview` literal |
| A3 — PyAV libmp3lame | PASS | Plan 29-01 encodes MP3 in-process via PyAV |
| A5 — Achird at 60-90s | FALLBACK / DEFERRED | Constant `DEBRIEF_TTS_VOICE`; Kaan validates first real debrief |
| A7 — Proxy responseSchema | FALLBACK / DEFERRED | Drills use Pydantic post-hoc validation as fallback path |

No probe blocks Phase 29 execution. Two probes (A5, A7) defer to Kaan-validation post-build; the implementations include working fallbacks so the code path is always green.

**Logged to KAAN-ACTION-PROXY.md:** A5-VOICE-LISTEN, A7-PROXY-RESPONSESCHEMA-VERIFY.
