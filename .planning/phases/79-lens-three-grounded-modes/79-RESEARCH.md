# Phase 79: LENS — Three Grounded Modes - Research

**Researched:** 2026-05-26
**Domain:** Prompt-persona architecture (vibemix `prompts/matrix.py`) — additive lens layer over an existing data-driven mode×mood matrix, shared selection across two surfaces (live co-host + library curator)
**Confidence:** HIGH (all findings verified against live code in this session)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**LENS-01 — three grounded lenses over the same state**
- Introduce three **canonical lens names**: `hype` (party hype-man), `critique` (coach — "what would've been better / what to fix"), `tutor` (teaches DJing through who YOU are — semantics, reality, taste).
- A lens is a **prompt variant** that reads the SAME structured evidence (wired grounding + deltas/trajectory/genre). It changes the *intent/voice framing*, not the facts. Implemented as an additive lens layer over the existing `prompts/matrix.py` persona seam.
- **Resolve `critique` vs `coach` naming** (deferred from Phase-77 IN-02): `critique` is the canonical charter name; map it onto the existing matrix coach mode/mood additively (alias/lens-layer mapping) — do NOT rename matrix internals in a way that breaks the v4 `build_system_instruction` golden. The lens layer is the canonical surface; matrix modes/moods are the substrate it maps onto.
- `tutor` is the genuinely new lens (matrix has no tutor mode yet) — add it as a grounded teaching voice that explains based on the DJ's taste/semantics/reality.

**LENS-02 — shared lens selection**
- ONE shared lens-selection source of truth that BOTH surfaces read: the live co-host (`build_system_instruction` path) and the curator (`build_curator_instruction`, added Phase 77). Choosing a lens once flows to both.
- Reuse the Phase-77 unified persona seam — extend it with lens selection rather than adding a second mechanism. No new ws port / IPC envelope; if a runtime selector is needed it rides the existing settings/skill bus.
- Default lens preserves current behavior (cold-path byte-identity): the default selection produces a prompt byte-identical to today's.

**Citation grounding per lens (invariant #2)**
- Each lens output goes through the SAME citation-grounding gate. A lens cannot fabricate evidence; un-cited output strips to the ack-bank fallback regardless of lens. Pin this with a test that runs all three lenses through the gate.

### Claude's Discretion
- Exact lens→(mode,mood) mapping table, where the shared lens-selection state lives (profile vs a small shared module vs settings), and the lens enum/string representation — planner's call, smallest additive diff, follow `prompts/` + `profile/` conventions.

### Deferred Ideas (OUT OF SCOPE)
- Gemini hearing the audio as a secondary ear → Phase 80.
- The multi-dimensional bench that tests lens-fidelity → Phase 81 (this phase builds the lenses; the bench measures them).
- Curator+co-host engine/taste unification → Phase 82 (this phase shares the lens *selection*; full engine unification is 82).
- A polished UI control to pick the lens — out unless trivially riding the existing settings bus; the phase goal is the grounded lenses + shared selection, not new UI.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LENS-01 | hype / critique / tutor exist as three grounded prompt lenses over the same structured state | A canonical `_LENS_TO_MODE_MOOD` mapping layer (extending the existing `_CURATOR_LENS_TO_MOOD` from Phase 77) maps the 3 charter lenses onto the existing `(mode, mood)` substrate that already drives `build_system_instruction`. `hype`→`(hype, hype-man)`, `critique`→`(coach, coach)`, `tutor`→`(coach, teacher)`. No builder fork; the lens is a SELECTOR over the existing 6-cell matrix + 3-mood persona dict. The lone genuinely-new content is the `tutor` teaching framing (matrix has `teacher` mood but it has never been wired to the live co-host `build_system_instruction` path — only the curator uses it today). See §Standard Stack + §Architecture Patterns. |
| LENS-02 | Lens selection is shared across the co-host and curator surfaces | A single `lens` source of truth read by BOTH `build_system_instruction` (via a `lens=` kwarg or the runtime selector) AND `build_curator_instruction`. The curator already calls `build_curator_instruction("tutor")` hardcoded at its lazy seam (`library/agent.py:109/121`, `library/codex_curate.py:94`) — LENS-02 replaces that hardcode with a read from the shared selection. The co-host resolves persona from `VIBEMIX_MODE`/`VIBEMIX_MOOD` env + `MusicState.mood` today; the shared lens collapses those two axes into one. See §Architecture Patterns Pattern 2. |
</phase_requirements>

## Summary

Phase 79 is a **pure prompt-architecture refactor with zero new infrastructure**. The substrate already exists and is fully tested:

1. `prompts/matrix.py` carries a **data-driven 6-cell matrix** (`_CELLS`: 3 skills × 2 modes) plus a **3-entry mood-persona dict** (`MOOD_PERSONAS`: `hype-man` / `teacher` / `coach`). The co-host builder `build_system_instruction(skill, mode, mood, ...)` selects a cell and substitutes the mood persona; the curator builder `build_curator_instruction(lens)` (added Phase 77) draws ONLY the persona character from `MOOD_PERSONAS`.
2. Phase 77 **already established the lens vocabulary** as `_CURATOR_LENS_TO_MOOD = {"tutor": "teacher", "hype": "hype-man", "critique": "coach"}`. That is the canonical lens→substrate map — Phase 79 promotes it from curator-only to the shared surface and extends it so the co-host builder can be driven by a lens too.
3. The citation-grounding gate (invariant #2) is **lens-agnostic by construction**: `CitationLinter.check()` validates citations against the `EvidenceRegistry` snapshot at the response level, completely independent of which prompt cell produced the text. A lens changes the system instruction; it never touches the registry or the linter. So "all three lenses pass the gate" is provable by feeding three lens-built prompts through the same linter path and asserting the binary strip decision depends only on registry membership, not lens.

The hard constraint is the **v4 byte-identity golden** (`tests/prompts/test_matrix.py::test_q_v4_byte_identity_preserved_at_constant_level` + ~6 sibling tests). The default lens must produce a prompt byte-identical to today's `build_system_instruction("intermediate", "hype")`. This is achievable because the lens layer is a **selector that resolves to the existing `(mode, mood)` arguments** — when the lens resolves to `(hype, hype-man)` and goes through the unchanged builder, the output is byte-identical by construction.

**Primary recommendation:** Add a `LENS_TO_MODE_MOOD` mapping + a thin `build_lens_instruction(lens, skill)` wrapper (or a `lens=` kwarg on `build_system_instruction` that resolves to mode/mood) over the UNTOUCHED `build_system_instruction` builder. Store the shared lens selection in the existing settings bus (`ConfigStore.extra["lens"]`, mirroring `mood`/`skill`), read by both builders. Add the `tutor` lens as a new co-host teaching cell ONLY if `(coach, teacher)` over the existing COACH cells is judged insufficient — research recommends starting with the mapping-only approach (no new cell) and reserving a dedicated tutor cell for Phase 81 if the bench shows the mapped version under-teaches.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Lens → (mode, mood) resolution | `prompts/matrix.py` (pure data + function) | — | The matrix is the single persona source of truth; the lens is a selector layer over its existing data, not a new subsystem. |
| Shared lens selection state | `runtime/settings.py` + `ConfigStore.extra` | `runtime/session_loop.py` (snapshot emit) | `mood`/`skill`/`click_through` already live in `ConfigStore.extra` with `_apply_*` handlers on the existing settings bus. A `lens` selection rides the identical path — no new ws port, no new IPC envelope (LENS-02 constraint). |
| Co-host lens consumption | `agent/dj_cohost.py::_resolve_prompt_cell` | `__main__.py` (cache system instruction parity) | The co-host already resolves its cell from env/`MusicState.mood` at agent build. Lens resolution slots into this exact point. |
| Curator lens consumption | `library/agent.py` + `library/codex_curate.py` (lazy seam) | `library/mcp_server.py` (inherits via codex) | The Phase-77 seam already routes BOTH curator backends through `build_curator_instruction(lens)` — currently hardcoded `"tutor"`. LENS-02 replaces the hardcode with the shared read. |
| Citation grounding (per lens) | `coach/citation_linter.py` + `state/evidence_registry.py` | `agent/dj_cohost.py::llm_node` | Lens-agnostic by construction — the linter validates against the registry, never reads the prompt cell. No change needed; only a test that proves independence. |

## Standard Stack

### Core
This phase adds NO dependencies. All work is inside existing modules.

| Module | Role | Why It's the Right Home |
|--------|------|-------------------------|
| `src/vibemix/prompts/matrix.py` | The lens mapping layer + (optional) tutor cell | Already the single persona source of truth for BOTH surfaces; holds `_CELLS`, `MOOD_PERSONAS`, `build_system_instruction`, `build_curator_instruction`, `_CURATOR_LENS_TO_MOOD`. `[VERIFIED: read in session]` |
| `src/vibemix/runtime/settings.py` | The shared lens selection bus handler (`_apply_lens`) | Holds `_apply_mood` / `_apply_skill` / `_apply_click_through` — the exact `ConfigStore.extra` round-trip a lens selection mirrors. `_VALID_MOODS` / `_VALID_SKILLS` enums live here. `[VERIFIED: read in session]` |
| `src/vibemix/runtime/config_store.py` | Persistence of the lens selection (via `extra`) | `mood`/`skill`/`click_through` persist in `ConfigStore.extra` with no schema bump; lens rides the same path. `[VERIFIED: read in session]` |
| `src/vibemix/agent/dj_cohost.py` | Co-host lens consumption (`_resolve_prompt_cell`) | The single point where the co-host's prompt cell is resolved from env/`MusicState.mood`. `[VERIFIED: read in session]` |
| `src/vibemix/library/agent.py` + `codex_curate.py` | Curator lens consumption (lazy seam) | Already route through `build_curator_instruction("tutor")`; replace the hardcoded lens with the shared read. `[VERIFIED: read in session]` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Mapping lens → existing `(mode, mood)` cells | Three brand-new dedicated lens cells (`LENS_HYPE`, `LENS_CRITIQUE`, `LENS_TUTOR`) | New cells = a builder fork the CONTEXT explicitly forbids ("add lenses by extending the data + a mapping layer, not by forking the builder"). Mapping reuses the tuned-IP cells and keeps byte-identity trivially. **Use mapping.** |
| `ConfigStore.extra["lens"]` (settings bus) | A new field on the `profile/` long-term DJ profile | Profile is privacy-gated (`schema.py` Pitfall P51 — only an allowlist of fields may persist) and is a long-term identity store, not a session toggle. Lens is a per-session voice choice that mirrors `mood`/`skill` exactly. **Use settings bus.** |
| `ConfigStore.extra["lens"]` | A new small shared `prompts/lens_state.py` module | A module-level singleton violates the project's "DI over globals" convention (CLAUDE.md) and would need its own persistence + IPC plumbing. The settings bus already persists + emits + survives relaunch. **Use settings bus.** |
| Collapsing `mode`+`mood` into one `lens` axis | Keeping `mode` (hype/coach) and `mood` (hype-man/teacher/coach) as independent runtime axes AND adding lens on top | Three overlapping persona axes is the confusion the lens is meant to END. The lens IS the unified axis; `(mode, mood)` become its internal resolution targets. The runtime `_apply_mode`/`_apply_mood` handlers stay for backward-compat but the lens becomes the canonical surface. **Collapse via mapping; keep old handlers additive.** |

**Installation:** No packages. `npm`/`pip`/`cargo` unchanged.

## Package Legitimacy Audit

Not applicable — this phase installs no external packages. All work is internal Python module edits. `[VERIFIED: read in session — no new imports introduced by the design]`

## Architecture Patterns

### System Architecture Diagram

```
                         LENS SELECTION (one source of truth)
                         ConfigStore.extra["lens"]  ∈ {hype, critique, tutor}
                         set via settings bus _apply_lens (no new ws port)
                                    │
                 ┌──────────────────┴──────────────────┐
                 │                                      │
        LIVE CO-HOST surface                    LIBRARY CURATOR surface
                 │                                      │
   dj_cohost._resolve_prompt_cell(lens)      agent.py / codex_curate.py
                 │                              (lazy seam, was hardcoded "tutor")
                 ▼                                      ▼
   LENS_TO_MODE_MOOD[lens] → (mode, mood)     build_curator_instruction(lens)
                 │                                      │  _CURATOR_LENS_TO_MOOD[lens] → mood
                 ▼                                      ▼
   build_system_instruction(skill, mode, mood)   persona from MOOD_PERSONAS[mood]
        (UNTOUCHED builder — byte-identical             (UNTOUCHED — persona-only,
         when lens=hype → mode=hype,mood=hype-man)       no runtime blocks)
                 │                                      │
                 ▼                                      ▼
        system instruction string              curator voice string
                 │                                      │
                 ▼                                      │
   Gemini reaction (llm_node)                          (text playlist; no live gate)
                 │
                 ▼
   ════════ CITATION-GROUNDING GATE (invariant #2 — LENS-AGNOSTIC) ════════
   parse_citations(reply) → CitationLinter.check(registry_snapshot)
   ANY atom not in EvidenceRegistry  →  whole reply stripped to <silence/>
   (decision depends ONLY on registry membership, NEVER on which lens built the prompt)
                 │
                 ▼
        spoken reaction OR <silence/>
```

The lens enters at the system-instruction-build step on BOTH surfaces and exits before the gate. The gate is downstream and lens-blind — that is exactly why "all three lenses pass the gate" is true by construction.

### Recommended Project Structure (no new files required)
```
src/vibemix/prompts/matrix.py     # ADD: LENS_TO_MODE_MOOD map + build_lens_instruction()
                                  #      (extends existing _CURATOR_LENS_TO_MOOD vocabulary)
src/vibemix/runtime/settings.py   # ADD: _apply_lens handler + _VALID_LENSES enum
                                  #      + "lens" dispatch case (mirror _apply_mood)
src/vibemix/agent/dj_cohost.py    # EDIT: _resolve_prompt_cell reads shared lens → (mode,mood)
src/vibemix/library/agent.py      # EDIT: lazy seam reads shared lens (was hardcoded "tutor")
src/vibemix/library/codex_curate.py # EDIT: same lazy-seam lens read
tests/prompts/test_matrix.py      # ADD: lens→cell-shape + byte-identity-of-default-lens tests
tests/prompts/test_lens.py        # NEW (optional): all-three-lenses + shared-selection + gate
tests/agent/test_dj_cohost.py     # ADD: lens flows into _resolve_prompt_cell
tests/library/test_*_seam.py      # ADD: curator reads shared lens (not hardcoded)
```

### Pattern 1: Lens-as-selector over the untouched matrix (LENS-01)
**What:** A pure data map from the 3 canonical lenses to the existing `(mode, mood)` substrate, consumed by a thin wrapper that delegates to the UNCHANGED `build_system_instruction`.
**When to use:** This is the core of LENS-01.
**Example:**
```python
# Source: extends src/vibemix/prompts/matrix.py::_CURATOR_LENS_TO_MOOD (Phase 77, VERIFIED in session)
# [ASSUMED] exact tuple values — planner's call, smallest additive diff per CONTEXT discretion.

# The canonical lens → co-host (mode, mood) substrate map. Mirrors the existing
# _CURATOR_LENS_TO_MOOD (lens → curator mood) so both surfaces share the SAME lens vocabulary.
LENS_TO_MODE_MOOD: dict[str, tuple[str, str]] = {
    "hype":     ("hype",  "hype-man"),   # → HYPE_* cell + hype-man persona  (= today's default for lens=hype)
    "critique": ("coach", "coach"),      # → COACH_* cell + coach persona    (charter "critique" == matrix coach)
    "tutor":    ("coach", "teacher"),    # → COACH_* cell + teacher persona  (the new teaching voice)
}

def build_lens_instruction(lens: str = "hype", skill: str = "intermediate", **kw) -> str:
    """Resolve a charter lens to (mode, mood) and delegate to the UNTOUCHED builder.

    DEFAULT-LENS BYTE-IDENTITY: build_lens_instruction("hype", "intermediate")
    resolves to build_system_instruction("intermediate", "hype", "hype-man") —
    byte-identical to today's default co-host path. The v4 golden stays green
    because build_system_instruction is unchanged.
    """
    lens_norm = lens.lower().strip()
    if lens_norm not in LENS_TO_MODE_MOOD:
        raise ValueError(f"unknown lens {lens!r} — must be one of {sorted(LENS_TO_MODE_MOOD)}")
    mode, mood = LENS_TO_MODE_MOOD[lens_norm]
    return build_system_instruction(skill, mode, mood, **kw)
```
**Critical:** Do NOT modify `build_system_instruction`, `_CELLS`, `MOOD_PERSONAS`, or any cell constant. The lens layer is strictly additive and sits ABOVE the builder. The v4 golden asserts on the builder + constants; leaving them untouched keeps it green automatically.

### Pattern 2: Shared lens selection on the existing settings bus (LENS-02)
**What:** A single `lens` value persisted in `ConfigStore.extra["lens"]`, set via a new `_apply_lens` handler that mirrors `_apply_mood` exactly, read by BOTH the co-host (`_resolve_prompt_cell`) and the curator lazy seam.
**When to use:** This is the core of LENS-02. No new ws port, no new IPC envelope.
**Example:**
```python
# Source: mirrors src/vibemix/runtime/settings.py::_apply_skill (VERIFIED in session, lines 409-436)
# [ASSUMED] exact handler body — planner's call.
_VALID_LENSES: frozenset[str] = frozenset({"hype", "critique", "tutor"})

async def _apply_lens(self, value: Any) -> tuple[bool, str | None]:
    if not isinstance(value, str) or value not in _VALID_LENSES:
        return (False, f"lens must be one of {sorted(_VALID_LENSES)}, got {value!r}")
    self.config_store.extra["lens"] = value
    save_config(self.config_store)
    # If a live agent rebuild is needed, ride the SAME lifecycle mood/skill use
    # (agent re-instantiation reads the new lens at _resolve_prompt_cell time).
    return (True, None)
```
**Curator seam change (LENS-02):**
```python
# Source: src/vibemix/library/agent.py:109 (VERIFIED in session) — currently hardcoded "tutor".
# Replace the literal with a read of the shared selection.
#   build_curator_instruction(_shared_lens())   # _shared_lens() reads ConfigStore.extra["lens"], default "tutor"
```
**Co-host consumption (LENS-02):** `_resolve_prompt_cell` reads the shared lens, resolves `(mode, mood)` via `LENS_TO_MODE_MOOD`, and passes them to the unchanged builder. The existing `VIBEMIX_MODE`/`VIBEMIX_MOOD`/`MusicState.mood` resolution stays as the fallback/backward-compat default so the cold path is byte-identical.

### Pattern 3: Default-lens byte-identity (the hard gate)
**What:** The default lens must produce a co-host prompt byte-identical to today's `build_system_instruction("intermediate", "hype")`.
**Verified mechanism:** Today's co-host default resolves to `(skill=intermediate, mode=hype, mood=hype-man)` (from `DEFAULT_SKILL_LEVEL`/`DEFAULT_MODE`/`DEFAULT_MOOD` in `dj_cohost.py:115-117`). The `hype` lens maps to exactly `(hype, hype-man)`. So `build_lens_instruction("hype", "intermediate")` == `build_system_instruction("intermediate", "hype", "hype-man")` byte-for-byte.
**Test:** Assert `build_lens_instruction(DEFAULT_LENS) == build_system_instruction("intermediate", "hype")` AND that the existing v4 golden (`test_q_v4_byte_identity_preserved_at_constant_level`) is untouched/green.

### Anti-Patterns to Avoid
- **Forking the builder per lens.** CONTEXT explicitly forbids this. The lens is a selector, not a new builder.
- **Renaming matrix internals** (`coach` mode/mood → `critique`). This breaks the v4 golden + the Phase-77 `_CURATOR_LENS_TO_MOOD`. Keep matrix vocabulary stable; the lens layer is the canonical surface that maps ONTO `coach`.
- **Adding a new ws port or IPC envelope for lens selection.** The settings bus (`SettingsState` snapshot + `_apply_*` dispatch on the existing `127.0.0.1:8765` bus) already carries `mood`/`skill`/`click_through`. Add a `lens` field to `SettingsState.make(...)` and a `"lens"` dispatch case — that's the entire wire surface. (Invariant #4: one socket.)
- **Putting lens in the per-turn prompt or the profile.** Lens is a system-instruction selector, resolved at agent build time (like mood). It must NOT enter the per-turn prompt (would break `test_profile_not_in_per_turn_prompt.py` patterns) and must NOT go in the privacy-gated profile schema.
- **Touching the citation linter / evidence registry for lens.** The gate is downstream and lens-blind. Any change there is out of scope (CONTEXT: "NO new evidence/grounding mechanics").

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Lens → persona resolution | A new per-lens prompt-template engine | The existing `_CELLS` + `MOOD_PERSONAS` data + a `dict` map | Phase 77 already proved the data-driven approach; the cells are tuned IP. |
| Shared selection persistence | A new config field / new IPC message type | `ConfigStore.extra["lens"]` + `_apply_lens` (mirror `_apply_mood`) | `mood`/`skill` already do exactly this — zero schema bump, survives relaunch, rides existing bus. |
| Curator voice sourcing | Re-hardcoding a lens in each backend | The existing lazy `build_curator_instruction(lens)` seam | Phase 77 built this seam specifically so Phase 79 only swaps the lens argument. |
| Per-lens grounding enforcement | A lens-aware linter variant | The existing lens-blind `CitationLinter.check()` | The gate validates against the registry, not the prompt — lens-agnostic by construction. |

**Key insight:** The hardest engineering in this phase is *resisting the urge to build* — the substrate is already there. The real work is (1) one mapping dict, (2) one settings handler, (3) two seam edits, (4) tests that prove byte-identity + gate-independence.

## Common Pitfalls

### Pitfall 1: Breaking the v4 byte-identity golden
**What goes wrong:** Editing `build_system_instruction`, a cell constant, or `MOOD_PERSONAS` to "make room" for the lens — the golden tests in `tests/prompts/test_matrix.py` (`test_q_*`, `test_prompt_01_hype_intermediate_byte_identical_to_persona`, `test_persona_system_instruction_still_byte_equal_to_hype_intermediate`) fail.
**Why it happens:** Treating the lens as a builder change instead of a selector layer above the builder.
**How to avoid:** The lens layer ONLY adds a new map + wrapper above the untouched builder. Run `PYTHONPATH=src python3 -m pytest -q tests/prompts/test_matrix.py` after every edit — it must stay fully green.
**Warning signs:** Any diff inside `build_system_instruction`, `HYPE_INTERMEDIATE`, `_CELLS`, or `MOOD_PERSONAS`.

### Pitfall 2: The two-axis confusion (mode vs mood vs lens)
**What goes wrong:** The runtime has TWO persona axes today — `mode` (hype/coach, from `ConfigStore.mode`/`VIBEMIX_MODE`, drives `event_detector.set_mode` + cell selection) and `mood` (hype-man/teacher/coach, from `MusicState.mood`/`VIBEMIX_MOOD`, drives the persona fragment). The lens is a THIRD, unifying axis. If you add lens without reconciling, you get three overlapping controls and undefined precedence.
**Why it happens:** The `mode`/`mood` split predates the lens concept.
**How to avoid:** Make the lens the canonical surface that RESOLVES to `(mode, mood)`. The `hype`/`critique`/`tutor` lens deterministically sets both axes (`LENS_TO_MODE_MOOD`). Keep the legacy `_apply_mode`/`_apply_mood` handlers for backward-compat (don't delete — additive), but document that lens is now the intended control. When lens is set, it wins; when only legacy mode/mood are set (cold path), behavior is byte-identical to today.
**Warning signs:** A test where setting lens=`critique` but `MusicState.mood` still reads `hype-man` produces a hype prompt.

### Pitfall 3: `mode` is `coach` by default in ConfigStore but `hype` by default in dj_cohost
**What goes wrong:** `ConfigStore.mode` defaults to `"coach"` (`config_store.py:162`) but `DEFAULT_MODE` in `dj_cohost.py:116` is `"hype"`, and `_resolve_prompt_cell` reads `VIBEMIX_MODE` env (not `ConfigStore.mode`). These are NOT wired together today — `_apply_mode` sets `ConfigStore.mode` + `event_detector.set_mode` but does NOT set `VIBEMIX_MODE`, so the live co-host prompt cell does not actually change on a mode toggle (a known live-apply gap noted in the handoff). 
**Why it happens:** Historical wiring debt — the co-host cell resolution reads env, the settings bus writes config.
**How to avoid:** When the lens drives `_resolve_prompt_cell`, route it through a SINGLE consistent read (the shared `ConfigStore.extra["lens"]`, not the disconnected `VIBEMIX_MODE` env). This phase is the chance to make lens-driven cell selection actually apply live (resolve lens → mode/mood at agent build, like `mood` already does via `MusicState.mood`). Do NOT try to fix the orphaned `VIBEMIX_MODE` live-apply gap as a side quest — just make the LENS path apply correctly and leave the legacy mode path as-is.
**Warning signs:** Setting lens at runtime persists to config but the next agent build still produces the old cell.

### Pitfall 4: Tutor lens under-teaches when mapped to (coach, teacher)
**What goes wrong:** The `teacher` mood persona ("patient, vocabulary-rich, framework-anchored") was authored for the CURATOR (text playlist explanations), not the live co-host. Mapping `tutor`→`(coach, teacher)` reuses the COACH_* live cells with the teacher fragment — which may read as "gentle critique" rather than "teaches DJing through who you are".
**Why it happens:** No dedicated live tutor cell exists; the mapping reuses critique's cells.
**How to avoid:** Start with the mapping (smallest diff, byte-identity-safe). Pin a `lens→prompt-shape` assertion that the tutor prompt contains teaching markers (the `teacher` persona vocabulary). The "does the tutor actually teach well" judgment is explicitly **Phase 81 BENCH (lens dimension) + Kaan's ear** (CONTEXT §Verification reality) — do NOT block this phase on tutor fidelity. If the bench later proves it under-teaches, a dedicated `TUTOR_*` cell is a Phase-81-informed follow-up, NOT this phase.
**Warning signs:** Over-engineering a bespoke tutor cell now and breaking the additive/byte-identity discipline.

## Runtime State Inventory

> This is an additive prompt-architecture phase, not a rename/migration. Included for completeness since it touches a persisted config key.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `ConfigStore.extra["lens"]` is a NEW persisted key (joins existing `extra` keys: `mood`, `skill`, `click_through`, `first_run_state`). No existing data carries a "lens" string to migrate. | None — new key, defaulted to `"hype"`/`"tutor"` (default lens) when absent. Mirror the `mood`/`skill` `extra` round-trip. |
| Live service config | None — no external service stores a lens. | None — verified by grep: `lens` appears only in `library/` (curator hardcode) and a single unrelated `dj_cohost.py:2203` comment. |
| OS-registered state | None. | None — verified. |
| Secrets/env vars | The legacy `VIBEMIX_MODE`/`VIBEMIX_MOOD`/`VIBEMIX_SKILL_LEVEL` env vars stay (backward-compat cold path). The lens does NOT add a new required env var. | None — lens defaults when `extra["lens"]` absent. |
| Build artifacts | None — no compiled artifact carries lens. | None. |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (config in `[tool.pytest.ini_options]` in `pyproject.toml`) `[VERIFIED: CLAUDE.md + repo]` |
| Config file | `pyproject.toml` |
| Quick run command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/prompts/test_matrix.py tests/prompts/test_lens.py` |
| Full suite command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LENS-01 | `LENS_TO_MODE_MOOD` maps all 3 canonical lenses; each resolves to a valid `(mode, mood)` substrate cell | unit | `pytest tests/prompts/test_lens.py -k lens_map -x` | ❌ Wave 0 |
| LENS-01 | hype-lens prompt has hype shape (hype-man persona markers); critique-lens has coach-cell markers; tutor-lens has teacher persona markers | unit | `pytest tests/prompts/test_lens.py -k lens_prompt_shape -x` | ❌ Wave 0 |
| LENS-01 | unknown lens raises ValueError (fail loud, mirrors mood/skill guards) | unit | `pytest tests/prompts/test_lens.py -k unknown_lens -x` | ❌ Wave 0 |
| LENS-01 | **default-lens byte-identity**: `build_lens_instruction(DEFAULT_LENS) == build_system_instruction("intermediate","hype")` AND v4 golden green | unit | `pytest tests/prompts/test_matrix.py -k byte_identity && pytest tests/prompts/test_lens.py -k default_lens_byte_identical -x` | ⚠️ matrix golden exists; lens assertion ❌ Wave 0 |
| LENS-01 | **all three lenses pass the gate**: a cited reply built under each lens lints valid; an un-cited reply strips to `<silence/>` under each lens — the strip decision is identical across lenses (lens-blind gate) | unit | `pytest tests/prompts/test_lens.py -k lenses_through_gate -x` | ❌ Wave 0 |
| LENS-02 | both builders read ONE shared lens: setting `ConfigStore.extra["lens"]="critique"` flows to `_resolve_prompt_cell` (co-host) AND `build_curator_instruction` seam (curator) | unit | `pytest tests/prompts/test_lens.py -k shared_selection_flows_to_both -x` | ❌ Wave 0 |
| LENS-02 | `_apply_lens` validates the enum + persists to `extra` + survives reload (mirror `_apply_mood`/`_apply_skill`) | unit | `pytest tests/runtime/test_settings*.py -k apply_lens -x` | ❌ Wave 0 |
| LENS-02 | curator seam no longer hardcodes `"tutor"` — reads the shared lens (default `"tutor"` when unset) | unit | `pytest tests/library/test_curator_persona_seam.py -k lens -x` | ⚠️ seam test exists; lens-read assertion ❌ Wave 0 |
| LENS-02 | `SettingsState` snapshot carries `lens` (no new ws port / envelope — extends existing snapshot) | unit | `pytest tests/runtime/test_settings*.py -k snapshot_lens -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `PYTHONPATH=src python3 -m pytest -q tests/prompts/test_matrix.py tests/prompts/test_lens.py` (byte-identity + lens map — fast, < 5s)
- **Per wave merge:** `PYTHONPATH=src python3 -m pytest -q tests/prompts/ tests/library/ tests/runtime/ tests/agent/test_dj_cohost.py`
- **Phase gate:** Full suite green (`pytest -q`, ~4 min, ~4445+ passing baseline from Phase 77) before `/gsd:verify-work`. v4 golden + model-literal gate (`tests/repo/test_model_literal_gate.py`) + no-live-path boundary (`tests/memory/test_no_live_path_import.py`) MUST stay green.

### Wave 0 Gaps
- [ ] `tests/prompts/test_lens.py` — covers LENS-01 (map, prompt-shape, unknown-lens, default byte-identity, three-lenses-through-gate) + LENS-02 (shared-selection-flows-to-both)
- [ ] `tests/runtime/test_settings*.py` additions — `_apply_lens` + `SettingsState` lens snapshot (locate the existing settings test file; mirror `_apply_mood`/`_apply_skill` test patterns)
- [ ] `tests/library/test_curator_persona_seam.py` additions — curator reads shared lens, not hardcoded `"tutor"`
- [ ] `tests/agent/test_dj_cohost.py` additions — `_resolve_prompt_cell` resolves lens → `(mode, mood)`; byte-identity of the default-lens cold path
- [ ] No framework install needed — pytest already configured.

**The three-lenses-through-the-gate test (the invariant #2 proof) — design note:** build a system instruction under each lens, run a fixed cited reply + a fixed un-cited reply through `parse_citations` + `CitationLinter.check(registry_snapshot)`, and assert the `LintResult.valid` decision is identical across all three lenses (it depends only on registry membership). This proves a lens can change tone but cannot smuggle past the gate — the anti-slop release contract. The gate itself needs ZERO code change; the test documents its lens-independence.

## Security Domain

> `security_enforcement` config not located in this session; defaulting to enabled. This phase has a narrow, well-understood threat surface (prompt-injection), already mitigated by the established pattern.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface touched. |
| V3 Session Management | no | No sessions. |
| V4 Access Control | no | Local single-user app. |
| V5 Input Validation | **yes** | Lens enum validated against `_VALID_LENSES` frozenset at the trust boundary (`_apply_lens`), fail-loud `ValueError` — mirrors the established `_apply_mood`/`_apply_skill` + `build_system_instruction` mood-guard pattern. `[VERIFIED: read in session]` |
| V6 Cryptography | no | No crypto. |

### Known Threat Patterns for vibemix prompt architecture

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection — user input mutating the persona/lens voice | Tampering | The lens ONLY SELECTS a fragment from the fixed `MOOD_PERSONAS` / `LENS_TO_MODE_MOOD` dicts; user input never enters the system-instruction text. This is the documented anti-injection invariant (T-13-05-06, T-77-02-01) — extend it: the `lens` value is a validated enum, never a free string interpolated into the prompt. `[VERIFIED: read in session]` |
| Lens bypassing the citation-grounding gate (slop injection) | Spoofing / Tampering | The gate is lens-blind by construction (linter validates against the registry, not the prompt). The "three-lenses-through-the-gate" test pins this. No lens can fabricate evidence. (Invariant #2.) |
| Lens enum typo silently degrading to a default voice | Tampering | Fail-loud `ValueError` on unknown lens (mirrors the existing mood/skill guards), not silent fallback — surfaces config typos. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `LENS_TO_MODE_MOOD` values `hype→(hype,hype-man)`, `critique→(coach,coach)`, `tutor→(coach,teacher)` | Standard Stack, Pattern 1 | LOW — these mirror the VERIFIED Phase-77 `_CURATOR_LENS_TO_MOOD`; only the co-host `mode` half is new and is dictated by which cell (HYPE vs COACH) each lens needs. Planner has explicit discretion on exact tuples. |
| A2 | Shared lens lives in `ConfigStore.extra["lens"]` on the settings bus | Standard Stack, Pattern 2 | LOW — explicitly within Claude's Discretion; chosen by direct analogy to the VERIFIED `mood`/`skill` `extra` round-trip. Profile + standalone-module alternatives rejected with reasons. |
| A3 | Mapping `tutor`→`(coach,teacher)` is sufficient for v1 (no dedicated tutor cell) | Pitfall 4 | MEDIUM — tutor fidelity is judged by Phase 81 BENCH + Kaan's ear (parked, per CONTEXT). If the bench rejects it, a dedicated cell is a follow-up, not a regression of this phase. |
| A4 | The default lens is `hype` for the co-host (preserving today's `(intermediate, hype, hype-man)` default) and `tutor` for the curator (preserving Phase-77's `build_curator_instruction("tutor")` default) | Pattern 3, Pitfall 3 | LOW — both are the VERIFIED current defaults. The "one shared selection" still holds: the shared value defaults per-surface to its current behavior when unset, which keeps both cold paths byte-identical. (Planner should confirm whether the single shared lens should have ONE global default or per-surface defaults; recommendation: per-surface default-when-unset preserves byte-identity on both sides.) |
| A5 | `tests/runtime/` is the home for settings tests | Validation Architecture | LOW — planner should locate the actual settings test file (grep `_apply_mood` in tests) and mirror it; the exact path doesn't change the design. |

## Open Questions

1. **One global default lens, or per-surface default-when-unset?**
   - What we know: Today the co-host defaults to `hype` (`hype-man`) and the curator defaults to `tutor` (`teacher`). LENS-02 wants ONE shared selection.
   - What's unclear: When the user has NEVER set a lens, should both surfaces show the SAME lens (e.g. both `hype`), or each keep its current default?
   - Recommendation: Per-surface **default-when-unset** (co-host→`hype`, curator→`tutor`) so both cold paths stay byte-identical; once the user explicitly picks a lens, that ONE value drives BOTH surfaces. This satisfies "choose once → flows to both" while preserving byte-identity. Planner confirms.

2. **Does the live co-host need to rebuild the agent on a lens change, or is next-build enough?**
   - What we know: `_apply_skill` persists and takes effect "on the next agent build" (no live rebuild); `_apply_mood` does a live `MusicState.mood` write + agent re-instantiation (Plan 13-06).
   - What's unclear: Whether lens needs the live-rebuild path or the next-build path is acceptable for v1.
   - Recommendation: Follow the `_apply_skill` next-build path for the smallest diff (CONTEXT: a runtime selector "rides the existing settings/skill bus"). Live hot-swap is a polish concern, not a LENS-01/02 requirement. Planner confirms; if live-swap is wanted, reuse the existing mood re-instantiation lifecycle, not a new mechanism.

## Environment Availability

> Skipped — this phase is pure Python module edits + tests with no external dependency. No tool/service probe required. (Per Step 2.6 skip condition: code-only changes.)

## Sources

### Primary (HIGH confidence — all read in this session)
- `src/vibemix/prompts/matrix.py` — full shape: `build_system_instruction`, `build_curator_instruction`, `MOOD_PERSONAS`, `_CELLS`, `_CURATOR_LENS_TO_MOOD`, all 6 cells, citation grammar / TTS / coach blocks.
- `tests/prompts/test_matrix.py` — the v4 byte-identity golden (`test_q_*`, `test_prompt_01_*`, `test_persona_*`) + anchor/substrate tests the lens layer must not break.
- `src/vibemix/state/evidence_registry.py` + `src/vibemix/coach/citation_linter.py` — the lens-blind citation-grounding gate (invariant #2); ack-bank retired 2026-05-19 → strip-to-`<silence/>`.
- `src/vibemix/runtime/settings.py` — `_apply_mood` / `_apply_skill` / `_apply_mode` handlers, `_VALID_MOODS` / `_VALID_SKILLS` enums, the `extra` round-trip pattern, the `_apply_mode` live-apply gap.
- `src/vibemix/agent/dj_cohost.py` — `_resolve_prompt_cell`, `DEFAULT_SKILL_LEVEL`/`DEFAULT_MODE`/`DEFAULT_MOOD`, `ENV_*` vars, `MusicState.mood` resolution at agent build.
- `src/vibemix/library/agent.py` + `library/codex_curate.py` — the lazy curator seam currently hardcoding `build_curator_instruction("tutor")`.
- `src/vibemix/runtime/config_store.py` — `mode`/`extra` persistence; `mode` defaults to `"coach"` (vs dj_cohost `DEFAULT_MODE="hype"` — the two-axis gap).
- `src/vibemix/__main__.py` — mood seeding from `VIBEMIX_MOOD`, cache system-instruction parity (`_resolve_prompt_cell` reused for cache).
- `.planning/phases/77-wire-connect-the-islands/77-02-SUMMARY.md` — the Phase-77 shared persona seam this extends; lens→mood map established.
- `.planning/research/one-mind-charter.md` — "SPEAKS IN THREE VOICES" faculty; the substrate (one being, three lenses).
- `.planning/REQUIREMENTS.md` — LENS-01/02 definitions, anti-creep acid test.

### Secondary / Tertiary
- None — no web research needed; this is an internal-architecture phase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; every module home verified by reading the live code.
- Architecture: HIGH — the lens-as-selector + shared-settings-bus pattern is a direct extension of the VERIFIED Phase-77 seam + the established `mood`/`skill` `extra` pattern.
- Pitfalls: HIGH — the v4 golden, the mode/mood two-axis gap, and the lens-blind gate are all confirmed against the actual test + code surfaces.
- Tutor fidelity: MEDIUM (A3) — explicitly deferred to Phase 81 BENCH + Kaan's ear by CONTEXT; not a blocker for LENS-01/02.

**Research date:** 2026-05-26
**Valid until:** 2026-06-25 (30 days — stable internal architecture; the only drift risk is `matrix.py`/`settings.py` line numbers, which the plan should re-grep, not the design).
