---
phase: 28-library-intelligence-v1
plan: 04
subsystem: library
tags: [grounding, anti-hallucination, event-gated, P48, P56, threshold-gate]

requires:
  - phase: 28-01
    provides: LibraryEmbedder
  - phase: 28-02
    provides: LibraryStore + open_store
  - phase: 18
    provides: EvidenceRegistry.register_library

provides:
  - Grounding pipeline (identify_playing + Grounding class)
  - Event-gated cost contract (TRACK_AWARE_EVENTS only)
  - 0.7 / 0.6 threshold ladder (cited / uncertain / below_threshold)
  - Wave 0 Bravoh proxy probe (scripts/probe_proxy_embed.py)
  - KAAN-ACTION-PROXY.md (proxy 404 documented + remediation)
  - P48 closure: invocation test + E2E test

affects: [28-08]

tech-stack:
  added: []
  patterns:
    - "Event-gated embed (cost-ceiling P56 mitigation)"
    - "Graceful degradation on proxy/embed failure"
    - "Thread-safe latest-citation snapshot for agent prompt builder"

key-files:
  created:
    - src/vibemix/library/grounding.py
    - scripts/probe_proxy_embed.py
    - tests/library/test_grounding.py
    - tests/integration/test_library_wired_into_main.py
    - tests/integration/test_track_citation_validates_end_to_end.py
    - .planning/phases/28-library-intelligence-v1/KAAN-ACTION-PROXY.md
  modified:
    - src/vibemix/__main__.py (Grounding boot wiring after register_library)
    - src/vibemix/library/__init__.py

key-decisions:
  - "Event-gated grounding (Option B per RESEARCH Open Q1) — embed only on TRACK_CHANGE/LAYER_ARRIVAL/MIX_MOVE. Lands at ~€27/month vs €1500/month for continuous."
  - "Threshold ladder: 0.7 cited / 0.6 uncertain / <0.6 below_threshold."
  - "Boot wiring is try-guarded — Grounding=None on failure, agent path tolerates."
  - "No EvidenceRegistry subscriber API exists — Grounding is invoked directly by the agent's event-emit path (Plan 28-04 ships the primitive; agent integration is a Phase 29+ task)."
  - "Bravoh proxy lacks models:embedContent route — KAAN-ACTION-PROXY.md filed; tests mock embed_content so unit + integration suites pass."

patterns-established:
  - "Pattern: Wave 0 probe scripts surface external blockers as KAAN-ACTION-*.md files; tests mock around them."
  - "Pattern: Grounding class holds latest CITED citation; agent reads via get_latest_citation()."
---

# Plan 28-04 — Event-Gated Grounding

Status: complete. 19/19 tests pass. Production proxy gap deferred via KAAN-ACTION-PROXY.md.

## What landed

### `src/vibemix/library/grounding.py`
- `identify_playing(embedder, store, audio_bytes, event_type)` — single-call audio embed + cosine top-1 + threshold decision.
- `Grounding` class — holds latest CITED citation, thread-safe via lock.
- Constants locked: `CITATION_THRESHOLD = 0.7`, `UNCERTAIN_THRESHOLD = 0.6`, `TRACK_AWARE_EVENTS = {TRACK_CHANGE, LAYER_ARRIVAL, MIX_MOVE}`.

### Wave 0 proxy probe — `scripts/probe_proxy_embed.py`

```
$ python scripts/probe_proxy_embed.py
{
  "status": "endpoint_missing",
  "http_status": 404,
  "url": "https://api.altidus.world/v1beta/models/gemini-embedding-2:embedContent",
  "remediation": "Bravoh proxy does NOT route models:embedContent. Either patch the proxy to forward this endpoint to Gemini, or fall back to MOCK_PROXY_FOR_DEV=1 in tests."
}
```

→ Filed `KAAN-ACTION-PROXY.md` with FastAPI patch snippet. All Phase 28 tests mock `embed_content` so the suite is green; production grounding will silently fall through to `decision="below_threshold"` until the proxy is patched.

### Boot wiring (`__main__.py`)

After `register_library` (P48 chain preserved):

```python
grounding = None
if library_cache.exists():
    try:
        from vibemix.library import Grounding, LibraryEmbedder, open_store
        embedder = LibraryEmbedder(genai_client)
        store = open_store()
        grounding = Grounding(embedder, store)
        print("-> grounding: armed (event-gated, threshold=0.7)")
    except Exception as e:
        print(f"-> grounding: disabled ({e})", file=sys.stderr)
```

The agent integration (passing `grounding=` kwarg into the cohost class) is a follow-up Phase 29+ task — Plan 28-04 ships the primitive + boot wiring.

## Test posture

- `pytest tests/library/test_grounding.py`: 12 unit tests (thresholds, event filter, no-audio, failure graceful, Grounding state)
- `pytest tests/integration/test_library_wired_into_main.py`: 6 P48 invocation tests
- `pytest tests/integration/test_track_citation_validates_end_to_end.py`: 1 P48 E2E chain
- Total: 19 pass in <2s.

## P48 status

- ✓ `register_library` still wired in `__main__.py` (grep returns 2)
- ✓ Grounding constructed after `register_library` (chain order asserted)
- ✓ E2E test covers the drag-drop → registry → grounding → citation chain

## Deviations from plan

- **No EvidenceRegistry subscriber API**: the plan assumed `evidence_registry.on_event(callback)`; the actual Phase 18 EvidenceRegistry doesn't expose one. Grounding is invoked directly via `Grounding.on_event(event_type, audio_bytes)` from the caller. Agent-side integration deferred to Phase 29+.
- **dj_cohost.py untouched**: agent prompt-injection of citations is a follow-up — Plan 28-04 ships the lookup primitive only.
- **Bravoh proxy 404**: documented in KAAN-ACTION-PROXY.md; production grounding ships with graceful degradation.
