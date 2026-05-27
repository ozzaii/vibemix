# Phase 77: WIRE — Connect the Islands - Pattern Map

**Mapped:** 2026-05-26
**Files analyzed:** 4 source files modified + 4 test files (new/extended)
**Analogs found:** 8 / 8 (every wire has an in-repo tested precedent)

All line numbers below were **re-verified against live source this session** (not the RESEARCH.md figures). They are current as of 2026-05-26.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/vibemix/agent/dj_cohost.py` (WIRE-01) | agent / pre-dispatch seam | event-driven (off-loop consult → latch → pull) | **self** — Phase-65 `_maybe_dispatch_recall` (same file) | exact (in-file twin) |
| `src/vibemix/__main__.py` (WIRE-01 + 05 + 06) | orchestrator / DI wiring | request-response (boot wiring) | self — existing `recall=`/`grounding=` build sites | exact |
| `src/vibemix/prompts/matrix.py` (WIRE-04) | prompt source-of-truth | transform (skill/mode/mood → string) | self — `build_system_instruction` | exact (new sibling fn) |
| `src/vibemix/library/agent.py` (WIRE-04) | service / curator (gemini) | request-response | `prompts/matrix.py` (becomes consumer) | role-match |
| `src/vibemix/library/codex_curate.py` (WIRE-04) | service / curator (codex) | request-response | `library/agent.py` (same swap) | exact |
| `src/vibemix/library/mcp_server.py` (WIRE-04) | service / tool boundary | request-response | — verify-only (no system prompt, A2) | n/a |
| `tests/agent/test_dj_cohost_grounding.py` (NEW) | test | event-driven | `tests/memory/test_ingest_wiring.py` | exact template |
| `tests/memory/test_ingest_wiring.py` (EXTEND, WIRE-05) | test | event-driven | self | exact |
| `tests/library/test_agent.py` + `test_codex_curate.py` (EXTEND, WIRE-04) | test | request-response | self | exact |
| `tests/runtime/` or `tests/repo/` env-override test (NEW, WIRE-06) | test | config | research §Code Examples shape | role-match |

---

## Pattern Assignments

### WIRE-01 — `src/vibemix/agent/dj_cohost.py` (agent, event-driven)

**Analog: the Phase-65 recall seam IN THE SAME FILE.** This is the strongest possible precedent — the grounding consult is structurally identical and the agent already holds the grounding-shaped service contract (`Grounding.on_event` / `get_latest_citation` / `clear` mirror `MemoryRecall.on_event` / `get_latest` / `clear`). Mirror the recall seam exactly at 4 points.

**Point 1 — Constructor kwarg** (`dj_cohost.py:340-422`, the kwargs-only block; recall kwarg at `:410-421`). Add `grounding` + (optionally) reuse a gate exactly like `recall` / `recall_enabled`:
```python
# Phase 65 Plan 04 — the precedent to copy verbatim (dj_cohost.py:410-421):
recall: "MemoryRecall | None" = None,
recall_enabled: bool = False,
```
WIRE-01 adds `grounding: "Grounding | None" = None`. Default `None` → cold path byte-identical (the v5.0 baseline guarantee that keeps the 4449-test suite green). Store it in `__init__` body next to `self._recall = recall` (search the same constructor body).

**Point 2 — Pre-dispatch on track-aware events** in `set_next_event` (`dj_cohost.py:826-853`), which calls `self._maybe_dispatch_recall(ev)` at `:853`. Add a sibling call `self._maybe_dispatch_grounding(ev)`. The recall dispatcher to mirror is `_maybe_dispatch_recall` (`dj_cohost.py:855-965`):
```python
# dj_cohost.py:855-965 — the template. Key beats to copy:
def _maybe_dispatch_recall(self, ev: Event) -> None:
    if not self._recall_enabled or self._recall is None:
        return                                    # gate → cold path byte-identical
    ...
    if ev.type not in RECALL_EVENT_GATE:          # event gate
        return
    try:
        loop = asyncio.get_running_loop()         # silent return if no loop (unit tests)
    except RuntimeError:
        return
    async def _run() -> None:
        try:
            await asyncio.wait_for(
                loop.run_in_executor(None, recall.on_event, ev.type, query_text, current_session_id),
                timeout=RECALL_DEADLINE_S)
        except asyncio.CancelledError:
            raise                                 # cancel ≠ clear (new event preempts)
        except (TimeoutError, asyncio.TimeoutError):
            recall.clear()                        # late memory worse than none
        except Exception as _e:
            recall.clear(); print(f"[recall dispatch err] {_e}", file=sys.stderr)
    prev = self._recall_task                       # cancel + replace prior in-flight
    if prev is not None and not prev.done():
        prev.cancel()
    self._recall_task = asyncio.create_task(_run())
```
WIRE-01 analogue: gate on `self._grounding is not None`, event-gate on `vibemix.library.grounding.TRACK_AWARE_EVENTS` (= `{"TRACK_CHANGE","LAYER_ARRIVAL","MIX_MOVE"}`, already a frozenset at `grounding.py:46-48`), and call `self._grounding.on_event(ev.type, audio_bytes, event_id=...)` off-loop via `run_in_executor`. **Audio source:** reuse the existing `self._clean_audio_buf` WAV snapshot that `llm_node` already builds (constructor stores it at `dj_cohost.py:449`) — do NOT add a second capture path (A3). `identify_playing` tolerates `audio_bytes=None` → returns a below-threshold `Citation`, so a missing buffer degrades silently (never crashes).

**Point 3 — Pull + inject in `llm_node`**, modeled on the recall pull/register block (`dj_cohost.py:998-1120`, inside the `try:`/`finally:` around `:998-1125`). The recall block pulls `self._recall.get_latest()` and registers ids in the EvidenceRegistry **before** the per-turn `snapshot = self._registry.snapshot()` at `:1144`. Grounding is simpler — `register_library` already seeded every track id (see Shared Patterns), so no per-turn registration is needed; just pull + inject:
```python
# WIRE-01 injection (mirror of grounding.py:178-180 doc + matches the
# recall pull at dj_cohost.py:1037). Pull BEFORE the prompt is built:
if self._grounding is not None:
    cit = self._grounding.get_latest_citation()   # Citation | None
    if cit is not None and cit.is_cited:
        # inject "[track:<id>]" into the prompt text Part — resolves in
        # EvidenceRegistry (register_library seeded it) → linter keeps it
        ... f" [track:{cit.track_id}]"
```
The cited `[track:<id>]` survives the CitationLinter (the anti-slop gate, invariant #2) because `register_library` already wrote every library track id as a `"track"` observation (see Shared Patterns / `evidence_registry.register_library`).

**Point 4 — Clear at turn end**, mirror `dj_cohost.py:2111-2122`:
```python
# dj_cohost.py:2118-2122 — the recall clear lifecycle to copy:
if self._recall_enabled and self._recall is not None:
    try:
        self._recall.clear()
    except Exception as _e:   # pragma: no cover — defensive only
        print(f"[recall clear err] {_e}", file=sys.stderr)
```
WIRE-01 adds `if self._grounding is not None: self._grounding.clear()` alongside it. `Grounding.clear()` exists (`grounding.py:216-220`) — its docstring literally says the recall path copied this lifecycle, so the seam shape is proven.

**Anti-patterns (verified live):**
- Grounding is built at `__main__.py:1134-1162` **AFTER** the agent at `:1047-1090` (confirmed). Prefer the recall kwarg style; either reorder the grounding build above the agent (its deps `genai_client`/`deck_library`/`library_cache` are available earlier) OR add a post-construction `attach_grounding()` setter. Planner's call — smallest additive diff.
- NEVER inline-await the embed in `llm_node` (TTFT regression). Pre-dispatch + latch + pull only — that is the entire reason the recall seam exists.

---

### WIRE-01 supporting — `src/vibemix/library/grounding.py` (read-only, no change)

This file is the **source object, fully built** — do not modify it. Verified contract:
- `TRACK_AWARE_EVENTS` frozenset at `grounding.py:46-48` — the event gate to import.
- `Grounding.on_event(event_type, audio_bytes, *, event_id=None, mime_type="audio/wav")` at `:188-209` — off-loop entry; stores latest CITED citation under a `threading.Lock`.
- `Grounding.get_latest_citation() -> Citation | None` at `:211-214`.
- `Grounding.clear()` at `:216-220`.
- `Citation.is_cited` property at `:69-71`; `track_id` populated only when `decision == "cited"` (cosine ≥ 0.7, `:160-166`).
- `identify_playing` tolerates `audio_bytes=None` → below-threshold Citation (`:108-115`), never raises on embed failure (`:139-147`).

---

### WIRE-04 — `src/vibemix/prompts/matrix.py` (transform, NEW sibling function)

**Analog: `build_system_instruction` in the same file** (`matrix.py:698-823`). Add a NEW `build_curator_instruction(lens: str = "tutor") -> str` sibling — do NOT reuse `build_system_instruction`, because it appends co-host-runtime blocks that are WRONG for a text curator:
- `CITATION_GRAMMAR_BLOCK` (appended `:788-789`)
- `IM_LISTENING_FRAGMENT` (appended `:800-801`)
- `TTS_TAG_DSL_BLOCK` / `COACH_TAG_DSL_BLOCK` + `COACH_CLOSING_BLOCK` (appended `:808-822`)

**Persona source to draw the voice from** — `MOOD_PERSONAS` (`matrix.py:51-64`), the fixed anti-injection dict (note at `:46-48`):
```python
# matrix.py:51-64 — the fixed persona vocabulary (anti-prompt-injection: never user input)
MOOD_PERSONAS: dict[str, str] = {
    "hype-man": ("You're high-energy, all-caps emotional, party-anchored — ..."),
    "teacher":  ("You're patient, vocabulary-rich, framework-anchored — ..."),
    "coach":    ("You're frank, post-mortem-anchored, debrief-style — ..."),
}
```
`build_curator_instruction` composes the lens *voice* (default "tutor" → maps onto the `teacher` persona vocabulary) WITHOUT the citation-grammar / TTS / fail-soft blocks, and the curator file prepends it to its existing grounding RULES (preserved verbatim — see below). Open Q2: charter lenses are `hype/coach/tutor`; matrix moods are `hype-man/teacher/coach`. Map `tutor→teacher`. Full three-lens-as-modes is Phase 79 — Phase 77 only builds the seam + a sane default.

**v4-byte-identity safety:** the golden in `tests/prompts/test_matrix.py` pins `build_system_instruction('intermediate','hype')`. A NEW function cannot touch that golden **as long as you do not modify the shared cell constants** (`_CELLS` at `:685-692`, `MOOD_PERSONAS`).

---

### WIRE-04 — `src/vibemix/library/agent.py` (service, gemini curator)

**Analog: itself + matrix seam.** Two hardcoded voice constants become consumers:
- `_SYSTEM_INSTRUCTION` (`agent.py:58-71`) — used at `agent.py:264` (passed as `system_instruction=` into `_run_loop`).
- `_INTERACTIVE_SYSTEM_INSTRUCTION` (`agent.py:189-202`) — used at `agent.py:295`.

**The non-negotiable RULES that MUST survive verbatim** (`agent.py:62-70` — the seen-set / no-invented-id grounding contract):
```python
# agent.py:61-70 — PRESERVE THESE VERBATIM (grounding invariant, V5 input validation):
"RULES (non-negotiable):\n"
"1. You may ONLY put a track in a playlist if a prior search_vibe call "
"returned its track_id in THIS conversation. Never invent a track_id, ..."
"2. Keys/BPM come from get_track_features (deterministic) — never compute ..."
"3. When you have chosen the tracks, call create_playlist exactly once ..."
```
Swap shape: `_SYSTEM_INSTRUCTION = build_curator_instruction("tutor") + "\n" + <the existing RULES block>`. The interactive variant keeps its `FLOW:` section (`:192-202`) verbatim; only the persona opener (`:190-191`) is sourced from the matrix seam. Call sites at `:264` / `:295` are unchanged. Model resolution at `agent.py:224` (`model_router.resolve("library_agent")`) is untouched — no model literal change.

---

### WIRE-04 — `src/vibemix/library/codex_curate.py` (service, codex curator)

**Analog: `library/agent.py` (same swap).** `_SYSTEM_PROMPT` (`codex_curate.py:60-74`) carries the identical RULES contract (`:64-73`) — preserve verbatim. It is consumed by `build_prompt(theme)` at `:126-127`:
```python
# codex_curate.py:126-127 — keep this shape; only _SYSTEM_PROMPT's voice changes:
def build_prompt(theme: str) -> str:
    return f"{_SYSTEM_PROMPT}\n\nTheme: {theme.strip()}"
```
Swap: `_SYSTEM_PROMPT = build_curator_instruction("tutor") + "\n" + <RULES block>`. Note rule #3 differs from agent.py (codex returns final JSON `{name, track_ids, rationale}` rather than calling `create_playlist`) — keep codex's rule #3 (`:70-73`) and `_OUTPUT_SCHEMA` (`:81-90`) verbatim.

---

### WIRE-04 — `src/vibemix/library/mcp_server.py` (verify-only, A2)

Research grep found NO system prompt in `mcp_server.py` (grounding lives at the tool boundary). **Action: verify during planning that it inherits voice via the codex path, then document "no change needed — verified" so it is not a silent orphan.** If it DOES carry a hidden voice, swap it too (CURATE acid test — both backends must speak the shared seam).

---

### WIRE-05 — `src/vibemix/__main__.py` + `src/vibemix/runtime/session_loop.py` (orchestrator, event-driven gated)

**Analog: the already-instantiated `_session_ipc` SessionLoop in `main()`** (`__main__.py:1210-1218`), which currently calls ONLY `register_handlers()` (`:1221`), never `run()`. Call the ingest entry on that SAME instance.

**The ingest entry to call** — `_fire_ingest` (`session_loop.py:862-924`):
```python
# session_loop.py:862 — call THIS directly (the ingest-only piece):
async def _fire_ingest(self, trigger: str, *, session_dir: Path | None = None) -> None:
    # trigger == "boot"  → run_ingest_sweep over recordings tree (idempotent)
    # trigger == "close" → ingest_session(session_dir) for the just-finished session
    if self.recordings_root is None:
        return                              # None-guard (mirror retention guard)
    # ... all heavy work inside loop.run_in_executor(_worker); best-effort, never-raise
```

**CRITICAL — do NOT call `run_boot_sweeps()` / `on_session_close()`.** Those fire BOTH retention AND ingest; `main()` already runs its own retention sweeps at boot (`__main__.py:632-646`) and close (`__main__.py:1361-1377`, verified this session). Calling the combined methods = **double retention** (recordings pruned twice, `ipc.recordings.usage` emitted twice). Call `_fire_ingest("boot")` and `_fire_ingest("close", session_dir=...)` ONLY.

**Gating** — wrap both in `if recall_enabled:` using the value already resolved at `__main__.py:1024`:
```python
# __main__.py:1024 — the flag is already resolved here, reuse it:
recall_enabled = os.environ.get("VIBEMIX_RECALL_ENABLED", "0").strip().lower() not in (...)
```
Default OFF → additive no-op (cold path byte-identical, no behavior change for the default user).

**Scope guard** — `_session_ipc` is defined inside the `try:` at `__main__.py:1202` and is NOT assigned on the except path (`:1226-1228`, which sets `ipc_router = None`). Guard the boot ingest call with `if _session_ipc is not None`. The close-path call lives in the `finally`/close region (around `:1361-1377`); confirm `_session_ipc` is in scope there during planning and guard it too.

---

### WIRE-06 — `src/vibemix/__main__.py` `_load_env_robust()` (config, one-line flip)

**Analog: the function itself** (`__main__.py:117-182`). Two `override=False` → `override=True`:
```python
# __main__.py:173 (the per-candidate load) — flip:
load_dotenv(dotenv_path=str(cand), override=False)   # → override=True
# __main__.py:182 (the no-.env-found fallback) — flip:
load_dotenv(override=False)                          # → override=True
```
**Reverses a deliberate decision** (docstring `:128-133` chose `override=False` so a Tauri-shell-injected process-env key is NOT clobbered by a stale `.env`). CONTEXT picks `.env`-wins. **Update the docstring** (`:128-133`) to record the reversal so the next reader understands it. A1: the Tauri-injection path is not exercised this session — flag as KAAN-ACTION verify if the bundled-install key-injection path matters for this milestone.
**Security:** the diagnostic at `:184+` prints WHICH file loaded, never the key value — keep it that way (V7 secrets).

---

## Shared Patterns

### Citation gate (WIRE-01) — `register_library` already seeds track ids
**Source:** `src/vibemix/state/evidence_registry.py` `register_library` (per research `:273-318`), already called on the live path at `__main__.py:1101`.
**Apply to:** WIRE-01 — this is WHY a `[track:<id>]` citation survives the CitationLinter (invariant #2) with zero linter change.
```python
# __main__.py:1098-1103 — the live seeding call (verified):
if library_cache.exists():
    lib = RekordboxLibrary()
    if lib.try_load_cache():
        registered = evidence_registry.register_library(lib)   # seeds every track:<id>
        deck_library = lib
        print(f"-> library: {registered} tracks registered for [track:<id>] citations")
```
Because every library track id is registered as a `"track"` observation, `EvidenceRegistry.has("track", citation.track_id, t)` returns True → the linter does NOT strip the turn.

### Additive gated cold-path (ALL wires)
**Source:** the `recall`/`recall_enabled` kwarg pattern (`dj_cohost.py:410-421`) + the `grounding is not None` lazy build (`__main__.py:1134-1162`).
**Apply to:** every wire. New param defaults `None`/off; new flag (`VIBEMIX_RECALL_ENABLED`) defaults off; new function (`build_curator_instruction`) doesn't touch the v4 golden. When off, behavior is byte-identical → the 4449-test suite stays green unchanged.

### Off-loop dispatch (WIRE-01 + WIRE-05)
**Source:** `loop.run_in_executor(None, svc.method, ...)` wrapped in `asyncio.wait_for(timeout=...)` (recall: `dj_cohost.py:917-925`; ingest: `session_loop.py:891-924`).
**Apply to:** WIRE-01 grounding dispatch, WIRE-05 ingest. Never inline-await the heavy work on the reaction loop.

### No hardcoded model literal (WIRE-01 + WIRE-04)
**Source:** CI gate `tests/repo/test_model_literal_gate.py:35-37`. Grounding resolves via `library.embed.GEMINI_EMBEDDING_MODEL` (`grounding.py:34,124`); curator via `model_router.resolve("library_agent")` (`agent.py:224`). **Touch neither** — no model name enters any diff.

---

## Test Patterns

### Off-loop wiring test (WIRE-01 new, WIRE-05 extend)
**Template: `tests/memory/test_ingest_wiring.py`** (verified head `:1-75`). Two-tier structure to copy:
1. **Source-text gate** (`:74+`) — assert the wiring imports the service and the call appears as a `run_in_executor` argument (off-loop static proof).
2. **Behavioural** — monkeypatch the service entrypoints + lazy builders to fakes (`FakeBus`/`FakeRecorder`/`FakeEmbedder` at `:48-71`), drive the seam under asyncio, assert recorded executor-thread id != event-loop thread id (off-loop proof) + None-guard + failure-swallow. **No network** — fakes stand in, no `genai.Client` ever built.

New `tests/agent/test_dj_cohost_grounding.py` mirrors this for WIRE-01: grounding kwarg/setter, off-loop dispatch on track-aware events, cited-`[track:<id>]` injection survives the linter, cold-path (grounding=None) byte-identity.

### WIRE-06 env-override test (new)
```python
# Shape (research §Code Examples): set decoy, write .env with real key, assert real wins
os.environ["GEMINI_API_KEY"] = "DECOY"
# write a .env with GEMINI_API_KEY=REAL at a probed candidate path
_load_env_robust()
assert os.environ["GEMINI_API_KEY"] == "REAL"
```
Place under `tests/runtime/` or `tests/repo/`.

---

## No Analog Found

None. Every wire has a tested in-repo precedent — this is the defining property of this phase.

| File | Note |
|------|------|
| `src/vibemix/library/mcp_server.py` | Not "no analog" — **verify-only** (A2): confirm it has no own system prompt and inherits voice via codex, then document. |

---

## Metadata

**Analog search scope:** `src/vibemix/{agent,library,prompts,runtime,state}/`, `src/vibemix/__main__.py`, `tests/memory/`.
**Files read this session (verified, non-overlapping):** `dj_cohost.py` (820-980, 331-460, 978-1148, 2095-2123), `grounding.py` (1-230), `library/agent.py` (40-115, 185-234, 255-322), `codex_curate.py` (50-135), `prompts/matrix.py` (40-100, 685-824), `session_loop.py` (855-924), `__main__.py` (117-187, 1047-1166, 1196-1230, 1355-1384), `tests/memory/test_ingest_wiring.py` (1-75).
**Pattern extraction date:** 2026-05-26
**Note:** RESEARCH.md line numbers all matched live source within ±2 lines; the figures above are the re-verified current values.
