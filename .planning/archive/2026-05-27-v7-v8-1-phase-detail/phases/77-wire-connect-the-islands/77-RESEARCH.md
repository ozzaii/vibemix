# Phase 77: WIRE — Connect the Islands - Research

**Researched:** 2026-05-26
**Domain:** Internal Python wiring — connecting already-built, orphaned subsystems at known integration points in `src/vibemix/`. No new libraries, no external research.
**Confidence:** HIGH (every claim verified against the live source this session; line numbers below are confirmed-current, not the drifted figures in `.planning/archive/2026-05-27-stale-one-mind-research/connection-map.md`)

## Summary

This is a pure **wiring** phase. All four wires connect code that already exists and is already tested in isolation — the work is adding optional parameters / gated call sites so the orphaned pieces run on the live `main()` path. Nothing here adds DSP, AI providers, ws ports, IPC envelopes, or MIR libraries. The four cardinal invariants hold by **additive gated design**: when the new param/flag is absent, the cold path is byte-identical to today's shipped behavior, so the existing 4449-test suite stays green unchanged.

The highest-leverage and most structurally interesting wire is **WIRE-01** (Grounding → live agent). The good news: vibemix already shipped an almost-identical seam in Phase 65 — the `MemoryRecall` pre-dispatch (`dj_cohost.py:838-965` `_maybe_dispatch_recall` + the llm_node pull/registration block). WIRE-01 should mirror that exact pattern (`Grounding.on_event` off-loop on track-aware events → `get_latest_citation()` pull in `llm_node` → inject `[track:<id>]` → resolves in `EvidenceRegistry` because `register_library` already registered every track id). The `Grounding` class even documents that its `clear()` lifecycle is the model the recall path copied — so the seam shape is already proven.

**Primary recommendation:** For each wire, add the smallest additive diff that the existing tested seams already demonstrate. WIRE-01 mirrors the recall pre-dispatch. WIRE-04 extracts a curator-voice helper from `prompts/matrix.py` that both curator backends import (replacing 3 hardcoded string constants). WIRE-05 calls `_session_ipc._fire_ingest(...)` (the SessionLoop instance already lives in `main()`) gated on `VIBEMIX_RECALL_ENABLED`. WIRE-06 flips two `override=False` → `override=True` in `_load_env_robust()`. Honest green = unit tests without the API; live e2e on the funded key is a KAAN-ACTION.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Grounding lookup (audio→library cosine) | `library/grounding.py` (`Grounding`) | — | Already owns it; thread-safe latch. Agent only consults read-only. |
| Citation injection into prompt | `agent/dj_cohost.py` (`llm_node`) | `state/evidence_registry.py` (resolves `[track:<id>]`) | The reaction-build path is the only place a citation enters a Gemini turn; registry is the gate. |
| Persona/lens source of truth | `prompts/matrix.py` | — | Charter + CONTEXT lock this as the single voice source. |
| Curator voice consumption | `library/agent.py`, `library/codex_curate.py`, `library/mcp_server.py` | reads `prompts/matrix.py` | Both backends currently hardcode; they become consumers, not owners. |
| Memory ingest dispatch | `runtime/session_loop.py` (`_fire_ingest`) | `memory/ingest.py` (does the work) | Ingest entry already exists; `main()` just needs to call it. |
| Env-key loading | `__main__.py` (`_load_env_robust`) | — | Single app-entry function; the override fix lives here. |

## Standard Stack

**No new packages.** This phase installs nothing. Everything is internal `src/vibemix/` wiring against already-pinned deps (`google-genai`, `numpy`, `python-dotenv`, `livekit-agents`). The Package Legitimacy Audit is therefore N/A — see below.

### Internal modules in play (the "stack" for this phase)

| Module | Role in this phase | Verified location |
|--------|-------------------|-------------------|
| `library/grounding.py` `Grounding` | WIRE-01 source object (built, never passed) | `grounding.py:169-220`; built at `__main__.py:1134-1162` |
| `agent/dj_cohost.py` `DJCoHostAgent` | WIRE-01 injection target | `__init__` at `dj_cohost.py:340-422`; built at `__main__.py:1047-1090` |
| `state/evidence_registry.py` | WIRE-01 citation gate | `register_library` at `evidence_registry.py:273-318`; already called `__main__.py:1101` |
| `prompts/matrix.py` `build_system_instruction` | WIRE-04 persona source | `matrix.py:698-823` |
| `library/agent.py` `ViberAgent` | WIRE-04 gemini backend (hardcodes voice) | `_SYSTEM_INSTRUCTION` `agent.py:58-71`, `_INTERACTIVE_SYSTEM_INSTRUCTION` `agent.py:189-202` |
| `library/codex_curate.py` | WIRE-04 codex backend (hardcodes voice) | `_SYSTEM_PROMPT` `codex_curate.py:60-75`; consumed via `build_prompt` `:126-127` |
| `runtime/session_loop.py` `SessionLoop` | WIRE-05 ingest entry | `_fire_ingest` at `session_loop.py:862`; `run_boot_sweeps` `:689`; `on_session_close` `:725` |
| `__main__.py` `_load_env_robust` | WIRE-06 fix site | `__main__.py:117-182` (two `override=False` at `:173` + `:182`) |

[VERIFIED: codebase grep + Read, 2026-05-26]

## Package Legitimacy Audit

**N/A — this phase installs zero external packages.** All work is internal wiring against already-pinned, already-audited dependencies in `pyproject.toml` + `uv.lock`. The anti-creep acid test in REQUIREMENTS.md explicitly forbids any new AI/embedding provider, MIR library, ws port, or IPC envelope. No slopcheck run required.

## Architecture Patterns

### System Architecture Diagram (the four wires)

```
WIRE-01  (mirror of the Phase-65 recall seam)
  coach_loop ──set_next_event(ev)──▶ DJCoHostAgent
                                       │
                  _maybe_dispatch_grounding(ev)   [NEW, gated on grounding is not None]
                                       │  (track-aware ev only; off-loop run_in_executor)
                                       ▼
                          Grounding.on_event(type, audio_bytes)  [library/grounding.py — EXISTS]
                                       │  cosine top-1 vs library.db, threshold 0.7
                                       ▼
                          latch Citation (track_id)
   llm_node ──get_latest_citation()──▶ inject "[track:<id>]" into prompt
                                       │
                                       ▼
              EvidenceRegistry.has("track", id, t)  ── register_library already seeded ids
                                       │  citation gate (invariant #2) PASSES
                                       ▼
                          Gemini reaction cites the REAL playing track

WIRE-04
  prompts/matrix.py ──curator-voice helper [NEW]──┬──▶ library/agent.py (gemini)
                                                  ├──▶ library/codex_curate.py (codex)
                                                  └──▶ library/mcp_server.py

WIRE-05  (gated on VIBEMIX_RECALL_ENABLED)
  main() boot ───▶ _session_ipc._fire_ingest("boot")            [SessionLoop already in main()]
  main() finally ─▶ _session_ipc._fire_ingest("close", dir)     [alongside retention sweep]
                          │
                          ▼
              memory/ingest.py run_ingest_sweep / ingest_session  → memory.db fills

WIRE-06
  _load_env_robust():  load_dotenv(..., override=True)  ──▶ .env funded key wins over ghost shell var
```

### Pattern 1: Mirror the recall pre-dispatch seam (WIRE-01)
**What:** The Phase 65 `MemoryRecall` wiring is a complete, tested template for "consult an off-loop service on track-aware events and inject the result into the next Gemini turn." WIRE-01 is the same shape.
**When to use:** WIRE-01 implementation.
**Reference (the model to copy):**
```python
# Source: src/vibemix/agent/dj_cohost.py:855-965 (recall pre-dispatch)
def _maybe_dispatch_recall(self, ev: Event) -> None:
    if not self._recall_enabled or self._recall is None:
        return                         # gate: cold path byte-identical
    if ev.type not in RECALL_EVENT_GATE:
        return                         # event gate (HEARTBEAT etc. skip)
    loop = asyncio.get_running_loop()  # silent return if no loop (unit tests)
    async def _run():
        await asyncio.wait_for(
            loop.run_in_executor(None, recall.on_event, ...),
            timeout=RECALL_DEADLINE_S)
    self._recall_task = asyncio.create_task(_run())
```
WIRE-01's analogue: `_maybe_dispatch_grounding(ev)` gated on `self._grounding is not None`, event-gated by `library.grounding.TRACK_AWARE_EVENTS` (`{"TRACK_CHANGE","LAYER_ARRIVAL","MIX_MOVE"}`, already defined `grounding.py:46-48`), calls `self._grounding.on_event(ev.type, audio_bytes, event_id=...)` off-loop. `llm_node` then pulls `self._grounding.get_latest_citation()` and, if `.is_cited`, injects `[track:<track_id>]` into the prompt. The agent already calls `Grounding.clear()`-style lifecycle (`dj_cohost.py:2111-2122` clears recall at turn end) — add the grounding clear() alongside it.

**Audio source for grounding:** the agent already holds `self._clean_audio_buf` (`dj_cohost.py:449`) and builds WAV bytes for the multimodal Part in `llm_node`. Reuse that same buffer snapshot for the grounding embed (do NOT add a second capture path). `identify_playing` tolerates `audio_bytes=None` → returns a below-threshold Citation, so a missing buffer degrades silently.

### Pattern 2: Extract a curator-voice helper, don't reuse the full co-host instruction (WIRE-04)
**What:** `build_system_instruction()` (`matrix.py:698`) returns the FULL live co-host system prompt — it appends `CITATION_GRAMMAR_BLOCK`, `IM_LISTENING_FRAGMENT`, and `TTS_TAG_DSL_BLOCK` (TTS expressivity tags). Those are co-host-runtime concerns and are WRONG for a text-only playlist curator. WIRE-04 must NOT pass the raw co-host instruction to the curator.
**When to use:** WIRE-04.
**Recommended approach:** Add a curator-context helper in `prompts/matrix.py` (single source of truth, per CONTEXT decision) that exposes the lens *voice* — e.g. `build_curator_instruction(lens: str = "tutor") -> str` — composing the persona character (drawn from the same hype/coach/tutor lens vocabulary already in `matrix.py`) WITHOUT the citation-grammar / TTS-tag / fail-soft co-host blocks, and prepending it to the curator's existing non-negotiable grounding RULES (the seen-set / no-invented-id contract at `agent.py:62-70` / `codex_curate.py:62-74` — those rules are grounding invariants and MUST be preserved verbatim). Then:
- `library/agent.py`: replace the `_SYSTEM_INSTRUCTION` / `_INTERACTIVE_SYSTEM_INSTRUCTION` literal bodies with `build_curator_instruction(...) + <the existing RULES block>`.
- `library/codex_curate.py`: replace `_SYSTEM_PROMPT` body the same way; `build_prompt` (`:126`) keeps its `{system}\n\nTheme: {theme}` shape.
- `library/mcp_server.py`: the grep showed NO system prompt in mcp_server (its grounding is at the tool boundary). Confirm it inherits voice via the codex path; it likely needs no voice change — verify during planning and document that explicitly so it isn't an orphan.

**CONTEXT note:** "curator default = the curator-appropriate lens (tutor/curator voice), overridable." So `build_curator_instruction` defaults to the tutor lens but accepts an override; lens selection being shared state across surfaces is the LENS phase (79) — Phase 77 only builds the *seam*, not the live lens-switch propagation.

### Pattern 3: Reuse the already-instantiated SessionLoop handler bag (WIRE-05)
**What:** `main()` already builds a `SessionLoop` instance (`_session_ipc`, `__main__.py:1210-1218`) and calls only `register_handlers()`, deliberately never `run()` (`:1219-1221`). WIRE-05 calls the ingest entries on that SAME instance — no new SessionLoop, no `run()`.
**Critical nuance:** `run_boot_sweeps()` and `on_session_close()` fire BOTH a retention sweep AND ingest. The live `main()` ALREADY does its own retention sweeps (boot `__main__.py:632-646`, close `:1361-1377`). Calling the full `run_boot_sweeps()`/`on_session_close()` would DOUBLE the retention sweep. **Call `_fire_ingest("boot")` and `_fire_ingest("close", session_dir=...)` directly** (`session_loop.py:862`) — the ingest-only piece — NOT the combined sweep methods.
**Gating:** wrap both calls in `if recall_enabled:` (the `VIBEMIX_RECALL_ENABLED` value already resolved at `__main__.py:1024`). Default OFF → additive no-op.
**Scope nuance:** `_session_ipc` is defined inside the `try:` at `__main__.py:1202` and may be `None` on the except path (`:1226-1228`). The boot ingest call must guard `_session_ipc is not None`; the finally-block close call must too (the variable is in scope there). Confirm variable visibility into the finally during planning.

### Pattern 4: dotenv override (WIRE-06)
**What:** `_load_env_robust()` (`__main__.py:117-182`) currently loads with `override=False` in both branches (`:173`, `:182`). A stale shell `GEMINI_API_KEY` shadows `.env`. Flip to `override=True`.
**Tension to resolve (planner decision):** The existing docstring (`:128-133`) deliberately chose `override=False` so a key injected by the Tauri shell into the process env is NOT clobbered by a stale on-disk `.env`. CONTEXT.md WIRE-06 picks `.env`-wins (`override=True`). These conflict for the Tauri-injects-key scenario. **Recommendation:** flip to `override=True` per CONTEXT (the funded `.env` is the source of truth for the dev/local path; the bug being fixed is real). Document the behavior change to the Tauri-injection path in the plan and update the docstring so the next reader understands the reversal. If a more surgical fix is wanted, an alternative is to clear a known-ghost key before load — but CONTEXT explicitly chose `override=True`, so default to that. [ASSUMED — see A1: the Tauri shell key-injection path is not exercised in this session; the override flip is correct for the diagnosed bug but its effect on a Tauri-injected key is inferred from the docstring, not observed.]

### Anti-Patterns to Avoid
- **Reordering the agent/grounding build to pass grounding at construction.** `grounding` is built at `__main__.py:1134` AFTER the agent at `:1047`. Tempting to reorder, but the recall pattern shows the cleaner additive path: pass via a kwarg that defaults None, OR add a post-construction setter. Prefer matching the recall kwarg style (`grounding: "Grounding | None" = None`) and moving the grounding build ABOVE the agent build IF that's a clean diff; otherwise a `agent.attach_grounding(g)` setter keeps construction order untouched. Planner's call (CONTEXT grants discretion) — smallest additive diff wins.
- **Passing the full co-host system instruction to the curator** (WIRE-04). It carries TTS tags + citation grammar irrelevant to a text playlist agent. Extract the voice, keep the curator's grounding RULES.
- **Calling `run_boot_sweeps()`/`on_session_close()` for WIRE-05.** Double-retention bug. Call `_fire_ingest` only.
- **Inline-awaiting the grounding embed in `llm_node`** (WIRE-01). That's a TTFT regression — the recall seam exists precisely to keep the embed off the reaction hot path. Pre-dispatch + latch + pull, never inline-await.
- **Hardcoding a Gemini model literal** anywhere. CI grep gate (`tests/repo/test_model_literal_gate.py:35-37`) bans `gemini-3-flash` etc. under `src/vibemix/`. Grounding already resolves the model via `library.embed.GEMINI_EMBEDDING_MODEL`; curator already uses `model_router.resolve(...)`. Touch nothing here.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Off-loop service dispatch on track-aware events | A new threading/queue mechanism | The `_maybe_dispatch_recall` pattern (`dj_cohost.py:855`) | Already tested, handles cancel/timeout/no-loop. |
| Citation that survives the gate | A new bypass in the linter | `register_library` already seeds `track:<id>` (`evidence_registry.py:273`) | `[track:<id>]` resolves today — no linter change needed. |
| Audio bytes for grounding embed | A second audio capture path | `self._clean_audio_buf` WAV snapshot already built in `llm_node` | One socket / single source; avoids a second capture. |
| Memory ingest | A new ingest call | `_fire_ingest` on the existing `_session_ipc` (`session_loop.py:862`) | Off-loop, idempotent (marker-gated), best-effort, already tested. |
| Env loading | A custom env parser | `load_dotenv(override=True)` | One-line flip of an existing, tested function. |

**Key insight:** Every wire in this phase has a tested precedent already shipped in the codebase. The risk is NOT "how do I build it" — it's "did I preserve the byte-identical cold path so the 4449-test suite stays green."

## Common Pitfalls

### Pitfall 1: Breaking byte-identity of the cold path
**What goes wrong:** A new kwarg or call changes behavior even when the feature is off, breaking existing golden/byte-identity tests (e.g. `tests/prompts/test_matrix.py` v4-byte-identity, `tests/agent/test_dj_cohost*`).
**Why it happens:** Adding the citation injection / curator voice unconditionally instead of behind the `grounding is not None` / lens gate.
**How to avoid:** Default every new param to `None`/off. For WIRE-04, the matrix v4-byte-identity golden is on `build_system_instruction('intermediate','hype')` with the co-host blocks — the curator helper is a NEW function, so it can't touch that golden as long as you don't modify the shared cell constants.
**Warning signs:** any test in `tests/prompts/test_matrix.py`, `tests/agent/test_dj_cohost.py`, `tests/library/test_grounding.py` going red.

### Pitfall 2: Double retention sweep (WIRE-05)
**What goes wrong:** Calling `run_boot_sweeps()`/`on_session_close()` runs retention twice (main() already does it).
**How to avoid:** Call only `_fire_ingest(...)`. Verified: retention lives at `__main__.py:632-646` (boot) + `:1361-1377` (close); ingest is the separable piece inside `_fire_ingest` (`session_loop.py:862-919`).
**Warning signs:** recordings pruned twice; `ipc.recordings.usage` emitted twice.

### Pitfall 3: WIRE-06 reverses a deliberate decision
**What goes wrong:** `override=True` clobbers a Tauri-shell-injected process-env key with a stale on-disk `.env`.
**Why it happens:** The original `override=False` was chosen on purpose (`:128-133`).
**How to avoid:** Per CONTEXT, `.env` wins — flip to `override=True`, update the docstring to record the reversal, and ensure the local/dev funded key in `.env` is correct. The diagnosed bug (ghost `...QSFyBQ` shadowing funded `...32u744`) is real and this fixes it.
**Warning signs:** a Tauri-bundled install where the key is injected via process env instead of `.env` could regress — flag as KAAN-ACTION verify if the bundled path matters for this milestone.

### Pitfall 4: mcp_server.py orphaned in WIRE-04
**What goes wrong:** WIRE-04 wires `agent.py` + `codex_curate.py` but forgets `mcp_server.py`, leaving one backend persona-blind (fails the CURATE acid test).
**How to avoid:** grep showed `mcp_server.py` has no system prompt of its own (grounding is at the tool boundary). Confirm during planning that it inherits voice through the codex path; if it does, document "no change needed, verified" — don't leave it silently unaddressed.

## Code Examples

### WIRE-01 — citation injection survives the gate (the mechanism, verified)
```python
# Source: src/vibemix/library/grounding.py:82-166 + state/evidence_registry.py:273-318
# 1. Grounding cites a real track id when cosine >= 0.7:
citation = grounding.get_latest_citation()   # -> Citation | None
if citation is not None and citation.is_cited:
    prompt += f" [track:{citation.track_id}]"
# 2. register_library already seeded EVERY library track id as a "track" observation,
#    so EvidenceRegistry.has("track", citation.track_id, t) returns True
#    -> the CitationLinter (dj_cohost.py:1737+) does NOT strip the turn. Invariant #2 holds.
```

### WIRE-06 — the one-line fix + its test shape
```python
# Source: src/vibemix/__main__.py:173,182  (flip both)
load_dotenv(dotenv_path=str(cand), override=True)   # was override=False
...
load_dotenv(override=True)                          # was override=False
# Test: set os.environ["GEMINI_API_KEY"]="DECOY", write a .env with REAL key,
# call _load_env_robust(), assert os.environ["GEMINI_API_KEY"] == "REAL".
```

## Runtime State Inventory

> This phase has a refactor/wiring flavor; the relevant question is "what stored/registered state must change." Most categories are N/A because no string is being renamed — this is wiring, not rebranding.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `memory.db` (sqlite-vec) currently EMPTY on the live path. WIRE-05 starts populating it when `VIBEMIX_RECALL_ENABLED=1`. No migration — it fills forward from new sessions. | none (forward-fill; gated off by default) |
| Live service config | None — no external service config carries a renamed string. | None — verified by grep (no rename in this phase). |
| OS-registered state | None. | None — verified (no OS registrations touched). |
| Secrets/env vars | `GEMINI_API_KEY` resolution behavior CHANGES (WIRE-06 `override=True`): a ghost shell var no longer wins. `VIBEMIX_RECALL_ENABLED` (existing flag) now actually gates ingest too. No key value changes. | Code change only; document the override reversal. |
| Build artifacts | None — no packaging/egg-info/binary affected. | None — verified. |

**The canonical question — after all files are updated, what runtime state still carries old behavior?** Only the env-var resolution order (WIRE-06) is a true runtime-behavior change; it is intentional and the point of the fix. `memory.db` fills forward; no back-migration of past sessions is in scope.

## State of the Art

N/A — internal wiring phase, no ecosystem/library currency concerns. The relevant "state of the art" is the in-repo Phase-65 recall seam, which is the current and correct pattern to mirror for WIRE-01.

## Project Constraints (from CLAUDE.md + CONVENTIONS)

- **Gemini-only.** No second AI/embedding provider. Grounding + curator already Gemini; touch nothing.
- **Model selection config-driven** via `model_router.resolve(...)` — zero hardcoded literals (CI grep gate `tests/repo/test_model_literal_gate.py`). Grounding uses `library.embed.GEMINI_EMBEDDING_MODEL`; curator uses the router. Do not inline a model name.
- **DI-over-globals:** state allocated in `main()`, passed explicitly (the grounding-kwarg approach matches this).
- **Additive gated design:** new capability behind a flag/optional param; cold path byte-identical (the four cardinal invariants).
- **Conventions:** `from __future__ import annotations`, PEP 604 unions, `snake_case` modules, `_prefixed` private helpers, `*_loop` async tasks, `threading.Lock` for cross-thread state (no async queues across the audio/loop boundary).
- **GSD workflow:** edits go through a GSD command, not direct repo edits.
- **frontend-enforcement skill:** loaded but **not applicable** — this phase touches zero UI/frontend code (no `tauri/ui/`, no `mascot.html`, no CSS). Noted for completeness.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | WIRE-06 `override=True` is correct for this milestone even though it reverses the deliberate Tauri-injection precedence; the Tauri-injects-key path is not exercised this session. | Pattern 4 / Pitfall 3 | A bundled install that injects the key via process env (not `.env`) could regress to using a stale `.env` key. Mitigated by: CONTEXT explicitly chose `.env`-wins; flag as KAAN-ACTION verify if bundled-install key injection matters now. |
| A2 | `mcp_server.py` needs no voice change because grounding is at the tool boundary and it has no system prompt of its own. | Pitfall 4 / WIRE-04 | If mcp_server DOES inject a hidden voice, the codex backend stays persona-blind (CURATE acid test fails). Mitigated by: planner verifies during implementation and documents the finding. |
| A3 | Reusing `self._clean_audio_buf` for the grounding embed is the right audio source (vs the mic ring or lookahead). | Pattern 1 / Don't Hand-Roll | If the clean buffer isn't populated at the dispatch point, grounding gets `None` audio and silently never cites. Mitigated by: `identify_playing` tolerates `None` (returns below-threshold), so worst case is no-citation, not a crash; verify buffer timing in the live e2e KAAN-ACTION. |

## Open Questions

1. **Grounding injection: kwarg vs setter vs build-reorder?**
   - What we know: agent built at `__main__.py:1047`, grounding at `:1134` (after). Recall used a kwarg with build-before-agent ordering.
   - What's unclear: whether moving the grounding build above the agent build is a clean diff (it depends on `genai_client`/`deck_library` which are available earlier) or whether a post-construction `attach_grounding()` setter is cleaner.
   - Recommendation: CONTEXT grants discretion; prefer the kwarg + reorder if the grounding build deps are all available before `:1047` (they appear to be — `genai_client`, `library_cache`). Otherwise use a setter. Either preserves the cold path.

2. **Curator helper signature in matrix.py.**
   - What we know: CONTEXT wants a curator-context variant of the same lens, defaulting to tutor/curator voice, overridable.
   - What's unclear: exact function name + whether lens enum is `hype/coach/tutor` (matrix uses `hype/coach` modes + `hype-man/teacher/coach` moods; "tutor" is a charter lens not yet a matrix mode).
   - Recommendation: introduce `build_curator_instruction(lens="tutor")` mapping the charter's three lenses onto the existing matrix vocabulary; full three-lens-as-modes work is deferred to Phase 79 (LENS). Phase 77 only needs the seam + a sane default voice.

## Environment Availability

> Skip-eligible (no new external dependency). Documented for completeness.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python-dotenv | WIRE-06 | ✓ (already pinned) | per `uv.lock` | — |
| google-genai | WIRE-01 grounding embed, curator | ✓ (already pinned) | per `uv.lock` | grounding tolerates None → no citation |
| `library.db` (sqlite-vec) | WIRE-01 grounding lookup | ✓ if user embedded a library; `__main__.py:1136` gates on `library_cache.exists()` | — | grounding stays `None` (cold path) when no library |
| Funded `GEMINI_API_KEY` | live e2e of WIRE-01 grounding + curator | KAAN-ACTION (`...32u744`) | — | unit tests run without API (fakes) |

**Missing dependencies with no fallback:** none — every wire is unit-testable without the API; live grounding/curator verification is a produce-and-park KAAN-ACTION.

## Validation Architecture

> `nyquist_validation` treated as enabled (not explicitly false in config).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (`[tool.pytest.ini_options]` `pyproject.toml:208`; `addopts = "-ra --strict-markers"`) |
| Config file | `pyproject.toml` |
| Quick run command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/agent tests/library tests/memory tests/prompts -x` |
| Full suite command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` (4449 tests collected, 2026-05-26) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WIRE-01 | Agent accepts `grounding` kwarg/setter; cold path (grounding=None) byte-identical | unit | `pytest tests/agent/test_dj_cohost.py -q` | ✅ (extend) |
| WIRE-01 | On a track-aware event the agent dispatches `grounding.on_event` off-loop (executor thread != loop thread), never inline-awaits | unit (mirror recall) | `pytest tests/agent/ -k grounding -q` | ❌ Wave 0 (new, modeled on `tests/memory/test_ingest_wiring.py`) |
| WIRE-01 | A cited `[track:<id>]` resolves in `EvidenceRegistry` and survives the citation linter (not stripped) | unit | `pytest tests/agent/ -k citation -q` + assert via `register_library` seeded id | ❌ Wave 0 (new) |
| WIRE-01 | Source assertion: `dj_cohost.py` references `grounding`/`get_latest_citation` and the dispatch uses `run_in_executor` (off-loop proof) | source-text | `pytest tests/agent/ -k grounding_wiring -q` | ❌ Wave 0 (new, mirror `test_ingest_wiring.py` static tier) |
| WIRE-02 | (shipped `ccf4930`) 8 detectors surface evidence + register | regression pin | existing detector/coach tests stay green | ✅ pin only |
| WIRE-03 | (shipped `a9979b8`) `detected_genre` in evidence, confidence-gated | regression pin | existing `tests/state/*genre*` green | ✅ pin only |
| WIRE-04 | Both curator backends read the shared matrix seam (no hardcoded `_SYSTEM_INSTRUCTION`/`_SYSTEM_PROMPT` literal voice) | unit + source-text | `pytest tests/library/test_agent.py tests/library/test_codex_curate.py -q` | ✅ (extend) |
| WIRE-04 | Curator grounding RULES (seen-set / no-invented-id) preserved verbatim after voice swap | unit | `pytest tests/library/ -k grounding -q` | ✅ |
| WIRE-04 | matrix v4-byte-identity golden unaffected (co-host instruction unchanged) | regression | `pytest tests/prompts/test_matrix.py -q` | ✅ pin |
| WIRE-05 | With `VIBEMIX_RECALL_ENABLED` off, `main()` makes NO ingest call (cold path) | unit | source/behavior assertion on the gated call | ❌ Wave 0 (new) |
| WIRE-05 | With flag on, `main()` calls `_session_ipc._fire_ingest("boot")` + close-path ingest; retention NOT doubled | unit (mirror `test_ingest_wiring.py`) | `pytest tests/memory/test_ingest_wiring.py -q` (extend) | ✅ (extend) |
| WIRE-06 | A decoy `GEMINI_API_KEY` in `os.environ` is overridden by the `.env` value after `_load_env_robust()` | unit | `pytest tests/ -k load_env -q` (new test) | ❌ Wave 0 (new) |

### Sampling Rate
- **Per task commit:** `pytest -q tests/agent tests/library tests/memory tests/prompts -x` (the touched trees)
- **Per wave merge:** full suite `pytest -q`
- **Phase gate:** full suite green (4449+ new tests, 0 fail) before `/gsd:verify-work`; live e2e on funded key = KAAN-ACTION, never faked.

### Wave 0 Gaps
- [ ] `tests/agent/test_dj_cohost_grounding.py` — grounding kwarg/setter, off-loop dispatch, cited-track injection, cold-path byte-identity (covers WIRE-01); model the off-loop + static tier on `tests/memory/test_ingest_wiring.py`.
- [ ] `tests/agent/` source-text gate asserting grounding dispatch uses `run_in_executor` (off-loop proof, no inline embed).
- [ ] `tests/memory/test_ingest_wiring.py` — extend with a `main()`-path assertion (flag-on fires `_fire_ingest`, flag-off no-op, retention not doubled) for WIRE-05.
- [ ] `tests/` (likely `tests/repo/` or `tests/runtime/`) — `_load_env_robust()` decoy-override test for WIRE-06.
- [ ] `tests/library/` — extend `test_agent.py` + `test_codex_curate.py` to assert voice comes from the matrix seam and grounding RULES survive (WIRE-04).
- [ ] Regression pins for WIRE-02/03 (no new logic — just a guard test that the shipped behavior stays).

## Security Domain

> `security_enforcement` not explicitly false → included. This phase has a narrow but real security surface: WIRE-06 touches API-key loading.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | partial | Curator already validates: seen-set / library re-validation at the tool boundary (preserve verbatim in WIRE-04). Telegram allow-list unchanged. |
| V6 Cryptography | no | No new crypto; SQLCipher path explicitly unused (CLAUDE.md). |
| V7 Secrets / config (V14 secrets mgmt) | **yes** | WIRE-06: `GEMINI_API_KEY` loaded via `python-dotenv`; never embed a key in code. The override flip must not log the key value. |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key leaked to logs/stderr | Information Disclosure | WIRE-06: the diagnostic in `_load_env_robust` (`:184+`) prints WHICH file loaded, never the key value — keep it that way. Telegram bridge already path-scrubs outbound (CLAUDE.md). |
| Prompt injection via curator theme/persona | Tampering | Persona comes from the fixed matrix dict, never user input (`matrix.py:46` MOOD_PERSONAS anti-injection note). WIRE-04 must keep the curator voice sourced from the fixed seam, not user-controllable. |
| Hallucinated track id smuggled into a playlist/citation | Spoofing/Tampering | Grounding gate (invariant #2) + curator seen-set. WIRE-01 citation resolves only against `register_library` ids; WIRE-04 preserves the seen-set RULES. |

## Sources

### Primary (HIGH confidence — read this session)
- `src/vibemix/library/grounding.py` (full) — `Grounding`, `identify_playing`, `Citation`, `TRACK_AWARE_EVENTS`, thresholds.
- `src/vibemix/agent/dj_cohost.py:331-422, 826-1144, 2100-2123` — constructor kwargs, recall pre-dispatch seam, llm_node pull/registration, turn-end clear.
- `src/vibemix/__main__.py:117-182 (env), 632-646 + 1361-1377 (retention), 1047-1090 (agent build), 1129-1162 (grounding build), 1199-1228 (SessionLoop handler-bag), 1015-1045 (recall flag).`
- `src/vibemix/prompts/matrix.py:46-95, 685-823` — persona cells, MOOD_PERSONAS, `build_system_instruction`.
- `src/vibemix/library/agent.py:58-71, 189-228, 264, 295` — hardcoded voice + ViberAgent.
- `src/vibemix/library/codex_curate.py:60-127` — codex `_SYSTEM_PROMPT` + `build_prompt`.
- `src/vibemix/runtime/session_loop.py:689-743, 862-919, 1275-1304` — ingest entries, `_fire_ingest`, `run()`.
- `src/vibemix/state/evidence_registry.py:273-362` — `register_library`, `snapshot`, `has`.
- `tests/memory/test_ingest_wiring.py` (head) — the off-loop wiring-test template.
- `tests/repo/test_model_literal_gate.py:35-37` — the model-literal CI gate.
- `.planning/archive/2026-05-27-stale-one-mind-research/connection-map.md`, `.planning/archive/2026-05-27-stale-one-mind-research/one-mind-charter.md`, `.planning/phases/77-wire-connect-the-islands/77-CONTEXT.md`, `.planning/REQUIREMENTS.md`.

### Secondary / Tertiary
- None — no web sources needed for an internal wiring phase.

## Metadata

**Confidence breakdown:**
- WIRE-01 (grounding→agent): HIGH — exact recall-seam precedent verified in-source; citation gate mechanism confirmed end-to-end.
- WIRE-04 (persona): HIGH on the hardcoded sites + matrix seam; MEDIUM on the exact curator-helper shape (discretionary; A2 mcp_server open).
- WIRE-05 (memory ingest): HIGH — `_session_ipc` already in `main()`; double-retention pitfall confirmed by reading both sweep methods.
- WIRE-06 (env override): HIGH on the fix location/mechanism; the Tauri-injection precedence reversal is A1 (assumed acceptable per CONTEXT).
- Validation architecture: HIGH — test infra mapped, 4449 tests collect clean, precedents identified.

**Research date:** 2026-05-26
**Valid until:** ~30 days (internal code; line numbers may drift on unrelated commits — the anchors are function/symbol names, which are stable).
