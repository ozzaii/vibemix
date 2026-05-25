---
phase: 77-wire-connect-the-islands
plan: 02
subsystem: prompts + library-curator
tags: [wire, wire-04, persona-seam, curator, matrix, anti-injection, no-live-path-boundary]
requires:
  - "src/vibemix/prompts/matrix.py (MOOD_PERSONAS — the fixed anti-injection persona dict)"
  - "src/vibemix/library/agent.py (gemini ViberAgent system instructions)"
  - "src/vibemix/library/codex_curate.py (codex _SYSTEM_PROMPT + build_prompt)"
  - "src/vibemix/library/mcp_server.py (codex tool-boundary server — verify-only)"
  - "tests/library/test_curator_persona_seam.py (Wave-0 scaffold from 77-01)"
provides:
  - "vibemix.prompts.matrix.build_curator_instruction(lens='tutor') -> str — the single curator-voice seam"
  - "library/agent.py voice sourced from the seam (lazy, PEP 562)"
  - "library/codex_curate.py voice sourced from the seam (lazy, PEP 562)"
affects:
  - "Phase 79 (three-lens-as-modes propagation rides this seam)"
tech-stack:
  added: []
  patterns:
    - "NEW sibling fn (build_curator_instruction) — does NOT touch the v4-byte-identity golden"
    - "charter lens -> matrix mood map (tutor->teacher / hype->hype-man / critique->coach)"
    - "lazy PEP 562 __getattr__ + cached builders to keep the prompts import off the curator import-time boundary"
    - "anti-prompt-injection: persona drawn ONLY from the fixed MOOD_PERSONAS dict, never user input"
key-files:
  created: []
  modified:
    - src/vibemix/prompts/matrix.py
    - src/vibemix/library/agent.py
    - src/vibemix/library/codex_curate.py
    - src/vibemix/library/mcp_server.py
    - tests/library/test_curator_persona_seam.py
decisions:
  - "Lens->mood mapping: tutor->teacher (curator default), hype->hype-man, critique->coach (RESEARCH Open Q2). Charter lens 'critique' maps to the matrix 'coach' mood; the curator default lens is 'tutor'."
  - "mcp_server.py A2 resolution: VERIFIED no own system prompt — it exposes the 3 grounded tools over STDIO and grounding lives at the tool boundary (LibraryToolset seen-set gate). Voice reaches Codex via codex_curate._SYSTEM_PROMPT (now seam-sourced). Documented with a code comment; no functional change needed."
  - "Seam imported LAZILY inside cached builders (PEP 562 __getattr__), NOT at module top-level — an eager 'from vibemix.prompts.matrix import ...' regressed tests/memory/test_no_live_path_import.py (vibemix.prompts is a forbidden surface on the memory storage-spine boundary). Lazy import preserves the boundary while still making the curators consume the seam."
metrics:
  duration: "~13 min (incl. two 4-min full-suite runs)"
  completed: "2026-05-26"
  tasks: 2
  files: 5
---

# Phase 77 Plan 02: WIRE-04 Shared Curator Persona Seam Summary

`prompts/matrix.py` is now the single source of truth for the curator voice. A NEW `build_curator_instruction(lens="tutor")` sibling composes the persona CHARACTER from the fixed `MOOD_PERSONAS` dict (no co-host-runtime blocks — no TTS tag DSL, no citation grammar, no fail-soft fragment), and BOTH curator backends (gemini `library/agent.py`, codex `library/codex_curate.py`) consume it instead of a hardcoded opener — while preserving their grounding RULES verbatim. The codex MCP server inherits the voice through the codex path (verified — no own prompt). Honest green: no API key, no `genai.Client`.

## What Was Built

| Task | File | Change |
|------|------|--------|
| 1 | `src/vibemix/prompts/matrix.py` | NEW `build_curator_instruction(lens="tutor") -> str` sibling of `build_system_instruction`; `_CURATOR_LENS_TO_MOOD` map; ValueError guard on unknown lens. Draws persona from `MOOD_PERSONAS` only. |
| 1 | `tests/library/test_curator_persona_seam.py` | Un-xfailed the SEAM-EXISTS tier (2 tests now real passes). |
| 2 | `src/vibemix/library/agent.py` | `_SYSTEM_INSTRUCTION` + `_INTERACTIVE_SYSTEM_INSTRUCTION` persona openers sourced from the seam via lazy cached builders + PEP 562 `__getattr__`; RULES + FLOW blocks preserved verbatim; call sites `:264`/`:295` route through `_system_instruction()` / `_interactive_system_instruction()`. `model_router.resolve("library_agent")` untouched. |
| 2 | `src/vibemix/library/codex_curate.py` | `_SYSTEM_PROMPT` opener sourced from the seam (lazy + PEP 562); codex rule #3 (final JSON) + `_OUTPUT_SCHEMA` verbatim; `build_prompt(theme)` shape unchanged (now calls `_system_prompt()`). |
| 2 | `src/vibemix/library/mcp_server.py` | Documentation-only comment: voice inherited via the codex_curate seam (verified — no own prompt). |
| 2 | `tests/library/test_curator_persona_seam.py` | Un-xfailed the VOICE-FROM-SEAM tier (2 tests now real passes). |

## Lens → Mood mapping (Open Q2 resolution)

| Charter lens | Matrix mood (MOOD_PERSONAS key) | Notes |
|--------------|---------------------------------|-------|
| `tutor` (curator default) | `teacher` | "patient, vocabulary-rich, framework-anchored" |
| `hype` | `hype-man` | "high-energy, all-caps emotional, party-anchored" |
| `critique` | `coach` | "frank, post-mortem-anchored, debrief-style" |

Full three-lens-as-modes propagation is Phase 79; Phase 77 builds only the seam + the sane `tutor` default.

## mcp_server.py verification (A2)

VERIFIED no change needed. `library/mcp_server.py` carries NO system prompt of its own: `build_server()` exposes only the 3 grounded tools (`search_vibe` / `get_track_features` / `create_playlist`) over STDIO, each delegating to the shared `LibraryToolset`. Grounding (the seen-set gate + `create_playlist` library re-validation) lives at the tool boundary, not in a prompt. The curator voice reaches Codex through `codex_curate._SYSTEM_PROMPT` (now seam-sourced) — so the codex backend is provably NOT persona-blind (CURATE acid test). A one-line code comment records the finding so it is not a silent orphan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Eager seam import regressed the memory no-live-path boundary**
- **Found during:** Task 2 (full-suite run after the initial straightforward top-level-import swap)
- **Issue:** Adding `from vibemix.prompts.matrix import build_curator_instruction` at the top of `library/agent.py` / `codex_curate.py` made `vibemix.prompts` load transitively whenever the curator was imported. `library/__init__` eagerly imports `library.agent`, and the memory storage spine reaches the library path transitively — so `import vibemix.memory.store` now dragged `vibemix.prompts` into `sys.modules`, breaking `tests/memory/test_no_live_path_import.py::{test_importing_memory_loads_no_coach_loop, test_importing_ingest_loads_no_coach_loop}` (both list `vibemix.prompts` as a FORBIDDEN live-path surface).
- **Fix:** Moved the seam import to LAZY — function-local imports inside cached builders (`_system_instruction()` / `_interactive_system_instruction()` / `_system_prompt()`), with the module-level constants exposed via PEP 562 `__getattr__` (mirroring the `state/__init__` lazy-load pattern the boundary test's own comment cites). The curators still consume the seam (source greps + attribute access + `build_prompt` all confirm), but importing them no longer touches `vibemix.prompts`.
- **Files modified:** `src/vibemix/library/agent.py`, `src/vibemix/library/codex_curate.py`
- **Verification:** `import vibemix.memory.store` + `import vibemix.memory.ingest` → zero `vibemix.prompts` modules in `sys.modules`; both boundary tests green.
- **Commit:** 556b9c2 (folded into the Task 2 commit — it is part of doing the swap correctly)

## Verification

- Plan-scoped: `PYTHONPATH=src pytest -q tests/prompts/test_matrix.py tests/library/test_curator_persona_seam.py tests/library/test_agent.py tests/library/test_codex_curate.py` — all green; the 4 Wave-0 xfails flipped to real passes.
- No-live-path boundary: `tests/memory/test_no_live_path_import.py` green (regression fixed).
- Model-literal gate: `tests/repo/test_model_literal_gate.py` green (10 passed — no model literal introduced).
- Matrix v4-byte-identity golden: green (`build_system_instruction` + `_CELLS` + `MOOD_PERSONAS` untouched).
- Full suite: **4445 passed, 26 skipped, 7 xfailed, 4 xpassed, 0 failed** (237s). The 7 xfails are the remaining WIRE-01/05/06 scaffolds for Plans 03/04; the 4 XPASS are pre-existing live-hardware (`V7-LIVE`) markers. No `genai.Client`, no `GEMINI_API_KEY`.

## Self-Check: PASSED

- FOUND: src/vibemix/prompts/matrix.py (build_curator_instruction present)
- FOUND: src/vibemix/library/agent.py (lazy seam builders present)
- FOUND: src/vibemix/library/codex_curate.py (lazy seam builder present)
- FOUND: src/vibemix/library/mcp_server.py (verified-no-change comment present)
- FOUND: tests/library/test_curator_persona_seam.py (4 xfail markers removed)
- FOUND commit 18f9b61 (Task 1), 556b9c2 (Task 2)
