# Phase 79: LENS — Three Grounded Modes - Pattern Map

**Mapped:** 2026-05-26
**Files analyzed:** 9 (3 source-edit + 1 source-add-in-place + 5 test)
**Analogs found:** 9 / 9 (every new file copies an in-repo analog; zero greenfield)

> All line numbers below were re-verified against live source in this session
> (`live-tuning-or-brain` branch). The lens layer is **strictly additive over an
> untouched `build_system_instruction`** — the v4 byte-identity golden stays green
> by construction.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/vibemix/prompts/matrix.py` (ADD `LENS_TO_MODE_MOOD` + `build_lens_instruction`) | prompt-builder / config | transform (selector) | `_CURATOR_LENS_TO_MOOD` + `build_curator_instruction` **in the same file** (matrix.py:834-841, Phase 77) | exact |
| `src/vibemix/runtime/settings.py` (ADD `_apply_lens` + `_VALID_LENSES` + dispatch case) | middleware (settings-bus handler) | request-response (validate→persist) | `_apply_skill` (settings.py:409-436) | exact |
| `src/vibemix/agent/dj_cohost.py` (EDIT `_resolve_prompt_cell` to read shared lens) | service (agent build) | transform | `_resolve_prompt_cell` itself (dj_cohost.py:309-329) + its `mood` override param | exact (self-edit) |
| `src/vibemix/library/agent.py` (EDIT lazy seam: swap hardcoded `"tutor"`) | service (curator backend) | transform | the two cached seam fns (agent.py:102-123) | exact (self-edit) |
| `src/vibemix/library/codex_curate.py` (EDIT lazy seam: swap hardcoded `"tutor"`) | service (curator backend) | transform | `library/agent.py` seam (same pattern, codex_curate.py:92-94) | exact |
| `tests/prompts/test_lens.py` (NEW) | test | unit | `tests/library/test_curator_persona_seam.py` (xfail-strict Wave-0 scaffold) + `tests/prompts/test_matrix.py` (byte-identity goldens) | exact |
| `tests/runtime/test_settings_apply.py` (ADD `_apply_lens` tests) | test | unit | `test_skill_happy_path`/`test_skill_invalid_value_rejected` (test_settings_apply.py:315-341) | exact |
| `tests/library/test_curator_persona_seam.py` (ADD lens-read assertion) | test | unit | the file's existing seam-tier tests | exact (self-edit) |
| `tests/agent/test_dj_cohost.py` (ADD lens→cell + cold-path byte-identity) | test | unit | existing `_resolve_prompt_cell` tests in that file | role-match |

---

## Pattern Assignments

### `src/vibemix/prompts/matrix.py` — `LENS_TO_MODE_MOOD` + `build_lens_instruction` (LENS-01)

**Analog:** `_CURATOR_LENS_TO_MOOD` + `build_curator_instruction` — **the same module**, added Phase 77. This is the canonical map to promote/mirror.

**The canonical map to mirror** (matrix.py:827-838, VERIFIED):
```python
# Phase 77 Plan 02 — WIRE-04: charter lens → matrix mood vocabulary.
# Anti-prompt-injection (T-77-02-01): this map keys a FIXED dict — the lens
# is never sourced from user input...
_CURATOR_LENS_TO_MOOD: dict[str, str] = {
    "tutor": "teacher",
    "hype": "hype-man",
    "critique": "coach",
}
```

> The co-host map ADDS the `mode` half (which `_CELLS` cell to pick). The lens
> *vocabulary* must stay identical to `_CURATOR_LENS_TO_MOOD` so both surfaces
> share one lens enum. Recommended new constant (planner has discretion on tuples,
> CONTEXT §Claude's Discretion; values mirror RESEARCH A1):
```python
LENS_TO_MODE_MOOD: dict[str, tuple[str, str]] = {
    "hype":     ("hype",  "hype-man"),   # → today's co-host default (byte-identity anchor)
    "critique": ("coach", "coach"),
    "tutor":    ("coach", "teacher"),
}
```

**The builder to delegate to — DO NOT MODIFY** (matrix.py:698-766, VERIFIED). Note its existing fail-loud guards (the pattern `build_lens_instruction` must copy):
```python
def build_system_instruction(
    skill: str = "intermediate",
    mode: str = "hype",
    mood: str = "hype-man",
    *,
    include_citation_grammar: bool = True,
    include_listening_fallback: bool = True,
    include_tag_dsl: bool = True,
) -> str:
    ...
    skill_norm = skill.lower().strip()
    mode_norm = mode.lower().strip()
    if skill_norm not in _VALID_SKILLS:
        raise ValueError(f"unknown skill {skill!r} — must be one of {sorted(_VALID_SKILLS)}")
    if mode_norm not in _VALID_MODES:
        raise ValueError(f"unknown mode {mode!r} — must be one of {sorted(_VALID_MODES)}")
    if mood not in MOOD_PERSONAS:
        raise ValueError(f"unknown mood {mood!r} — must be one of {sorted(MOOD_PERSONAS.keys())}")
    body = _CELLS[(skill_norm, mode_norm)]
    if mode_norm == "coach":
        persona = MOOD_PERSONAS[mood]
        body = body.replace("{mood_persona}", persona)
    ...
```

**The validate-and-delegate wrapper to mirror** — copy `build_curator_instruction`'s fail-loud guard shape (matrix.py:881-888, VERIFIED):
```python
    lens_norm = lens.lower().strip()
    if lens_norm not in _CURATOR_LENS_TO_MOOD:
        raise ValueError(
            f"unknown lens {lens!r} — must be one of "
            f"{sorted(_CURATOR_LENS_TO_MOOD.keys())}"
        )
    persona = MOOD_PERSONAS[_CURATOR_LENS_TO_MOOD[lens_norm]]
```

So `build_lens_instruction(lens, skill)` = `lower().strip()` → guard against `LENS_TO_MODE_MOOD` → unpack `(mode, mood)` → `return build_system_instruction(skill, mode, mood, **kw)`. Byte-identity follows because `build_lens_instruction("hype", "intermediate")` resolves to `build_system_instruction("intermediate", "hype", "hype-man")` — the exact default cell.

**Critical (Pitfall 1):** Do NOT touch `build_system_instruction`, `_CELLS` (matrix.py:685), `MOOD_PERSONAS` (matrix.py:51), or any cell constant. The v4 goldens in `tests/prompts/test_matrix.py` assert on those.

---

### `src/vibemix/runtime/settings.py` — `_apply_lens` + `_VALID_LENSES` (LENS-02)

**Analog:** `_apply_skill` (settings.py:409-436) — the closest match: it validates an enum, persists to `ConfigStore.extra`, takes effect on the *next agent build* (no live ws emit), and survives relaunch. `_apply_mood` is a *fuller* analog but adds a `MusicState` write + ws emit that the lens does NOT need (per RESEARCH Open-Q2 recommendation: follow the `_apply_skill` next-build path).

**Enum constant to mirror** (settings.py:49 + 56, VERIFIED):
```python
_VALID_MOODS: frozenset[str] = frozenset({"hype-man", "teacher", "coach"})
...
_VALID_SKILLS: frozenset[str] = frozenset({"beginner", "intermediate", "pro"})
```
→ add `_VALID_LENSES: frozenset[str] = frozenset({"hype", "critique", "tutor"})`.

**Handler body to copy** (settings.py:409-436, VERIFIED — `_apply_skill`):
```python
async def _apply_skill(self, value: Any) -> tuple[bool, str | None]:
    if not isinstance(value, str) or value not in _VALID_SKILLS:
        return (
            False,
            f"skill must be one of {sorted(_VALID_SKILLS)}, got {value!r}",
        )
    import os  # noqa: PLC0415
    os.environ[_ENV_SKILL_LEVEL] = value
    self.config_store.extra["skill"] = value
    save_config(self.config_store)
    return (True, None)
```
→ `_apply_lens` = same shape; persist `self.config_store.extra["lens"] = value` + `save_config(...)`. (Lens does NOT need an env-var export like skill does, because the co-host reads `extra["lens"]` directly at `_resolve_prompt_cell` — see Pitfall 3 note below.)

**Dispatch case to add** (settings.py:185-193, VERIFIED — the `apply()` if-ladder):
```python
        if field == "mood":
            return await self._apply_mood(value)
        if field == "skill":
            return await self._apply_skill(value)
        if field == "click_through":
            return await self._apply_click_through(value)
        if field == "lighter_blur":
            return await self._apply_lighter_blur(value)
        return (False, f"unknown settings field: {field!r}")
```
→ add `if field == "lens": return await self._apply_lens(value)` before the fallthrough.

**Pitfall 3 (VERIFIED):** `_apply_mode` writes `ConfigStore.mode` + `event_detector.set_mode` but does NOT set `VIBEMIX_MODE`, so the live co-host cell does not change on a mode toggle (orphaned env-read at `_resolve_prompt_cell`). Route the lens through ONE consistent read (`ConfigStore.extra["lens"]`), NOT the disconnected `VIBEMIX_MODE` env. Do not fix the legacy mode gap as a side-quest.

---

### `src/vibemix/agent/dj_cohost.py` — `_resolve_prompt_cell` reads shared lens (LENS-02)

**Analog:** the function itself (dj_cohost.py:309-329, VERIFIED). It already accepts a `mood` override that wins over the env var — the lens read slots in at the same precedence point.

```python
def _resolve_prompt_cell(mood: str | None = None) -> str:
    skill = os.environ.get(ENV_SKILL_LEVEL, DEFAULT_SKILL_LEVEL)
    mode = os.environ.get(ENV_MODE, DEFAULT_MODE)
    if mood is None:
        mood = os.environ.get(ENV_MOOD, DEFAULT_MOOD)
    return build_system_instruction(skill, mode, mood)
```

**Defaults that anchor cold-path byte-identity** (dj_cohost.py:115-117, VERIFIED):
```python
DEFAULT_SKILL_LEVEL = "intermediate"
DEFAULT_MODE = "hype"
DEFAULT_MOOD = "hype-man"
```

**Edit shape:** when a shared lens is present (read from `ConfigStore.extra["lens"]`), resolve `(mode, mood) = LENS_TO_MODE_MOOD[lens]` and call `build_system_instruction(skill, mode, mood)` (or `build_lens_instruction(lens, skill)`). When NO lens is set (cold path), keep the existing env/`DEFAULT_*` resolution **unchanged** → byte-identical to today. The live `MusicState.mood` override at the agent-build call site (dj_cohost.py:444-452, VERIFIED) stays as the existing mood path.

> The agent build also reuses `_resolve_prompt_cell` for the `GeminiContextCache`
> system-instruction parity (`__main__.py`, per RESEARCH §Responsibility Map) —
> routing lens through this one function keeps cache + live in lockstep automatically.

---

### `src/vibemix/library/agent.py` + `codex_curate.py` — swap hardcoded `"tutor"` (LENS-02)

**Analog:** the existing lazy seam (agent.py:102-123, VERIFIED) — Phase 77 built this seam SO Phase 79 only swaps the argument.

```python
def _system_instruction() -> str:
    global _SYSTEM_INSTRUCTION_CACHE
    if _SYSTEM_INSTRUCTION_CACHE is None:
        from vibemix.prompts.matrix import build_curator_instruction
        _SYSTEM_INSTRUCTION_CACHE = (
            build_curator_instruction("tutor") + "\n" + _RULES_BLOCK    # ← swap "tutor"
        )
    return _SYSTEM_INSTRUCTION_CACHE
```
Two call sites in agent.py (lines 109, 121) + one in codex_curate.py:94 (VERIFIED):
```python
_SYSTEM_PROMPT_CACHE = build_curator_instruction("tutor") + " " + _RULES_BLOCK
```

**Edit shape:** replace the literal `"tutor"` with a read of the shared lens — `build_curator_instruction(_shared_lens())` where `_shared_lens()` reads `ConfigStore.extra["lens"]` and **defaults to `"tutor"`** when unset (per RESEARCH Open-Q1 recommendation: per-surface default-when-unset preserves both cold paths byte-identical — curator→`tutor`, co-host→`hype`).

**GOTCHA (module-global cache):** all three seams cache the built instruction in a module global (`_SYSTEM_INSTRUCTION_CACHE` / `_INTERACTIVE_SYSTEM_INSTRUCTION_CACHE` / `_SYSTEM_PROMPT_CACHE`). A lens change after the first build will NOT re-read unless the cache is invalidated. Planner decision: either (a) read the lens at the *start* of each `_system_instruction()` call and skip the cache when the lens differs from the cached one, or (b) accept "next-process" semantics for the curator (matches the curator's one-shot CLI lifecycle). Tests must reset these globals between cases (the existing seam test already imports the modules directly).

---

## Shared Patterns

### Fail-loud enum validation at the trust boundary
**Source:** `build_system_instruction` mood guard (matrix.py:761-764) + `_apply_skill` enum guard (settings.py:423-427) + `build_curator_instruction` lens guard (matrix.py:882-886).
**Apply to:** `build_lens_instruction` (raise `ValueError` on unknown lens) AND `_apply_lens` (return `(False, "...")` on bad value). NO silent fallback — masks config typos. This is the established anti-injection pattern (T-13-05-06 / T-77-02-01): the lens is a validated enum that only SELECTS a fixed-dict fragment; user input never enters the prompt text.
```python
if lens_norm not in LENS_TO_MODE_MOOD:
    raise ValueError(f"unknown lens {lens!r} — must be one of {sorted(LENS_TO_MODE_MOOD)}")
```

### `ConfigStore.extra` round-trip persistence (no schema bump)
**Source:** `_apply_mood` (settings.py:383-384) + `_apply_skill` (settings.py:434-435) + `_apply_click_through` (settings.py:455-456).
**Apply to:** `_apply_lens`. `mood`/`skill`/`click_through` all persist in `extra` (an untyped dict) — survives relaunch, no `config_store.py` dataclass field, no schema migration. Lens rides the identical path.
```python
self.config_store.extra["lens"] = value
save_config(self.config_store)
```

### Lens-blind citation-grounding gate (invariant #2 — NO code change, test-only)
**Source:** `CitationLinter.check(text, registry_snapshot, *, mode="live")` (citation_linter.py:94-137, VERIFIED).
**Apply to:** the `test_lens.py` three-lenses-through-the-gate proof. The linter validates citation atoms against the `EvidenceRegistry` snapshot at the response level — it NEVER reads the prompt cell. So `LintResult.valid` depends only on registry membership, identical across all three lenses. The decision ladder (linter docstring): `0 citations → no_citations`; malformed atom → `malformed_atom`; atom not in registry → `invalid_atoms`; all valid → `valid`.
> **CAVEAT (RESEARCH §Sources + CLAUDE invariant #2 wording):** the ack-bank was
> RETIRED 2026-05-19 — un-cited output now strips to `<silence/>`, NOT to an
> ack-bank line. CONTEXT/REQUIREMENTS still say "ack-bank fallback" but the live
> behavior is strip-to-`<silence/>`. The test asserts the strip *decision* is
> lens-independent; phrase it as "strips" not "acks".

---

## Test Pattern Assignments

### `tests/prompts/test_lens.py` (NEW)
**Analog:** `tests/library/test_curator_persona_seam.py` (the Phase-77 Wave-0 scaffold — same xfail-strict-until-built shape, imports modules directly, no network/no genai.Client/no API key) + `tests/prompts/test_matrix.py` byte-identity goldens.
**Covers:** `LENS_TO_MODE_MOOD` maps all 3 lenses to valid cells; per-lens prompt-shape (hype-man / coach-cell / teacher persona markers); unknown-lens `ValueError`; **default-lens byte-identity** (`build_lens_instruction("hype","intermediate") == build_system_instruction("intermediate","hype")`); three-lenses-through-the-gate (build a sys-instruction under each lens, run one cited + one un-cited reply through `parse_citations` + `CitationLinter.check`, assert `LintResult.valid` identical across lenses); shared-selection-flows-to-both.

### `tests/runtime/test_settings_apply.py` (ADD)
**Analog:** `test_skill_happy_path` (line 315), `test_skill_invalid_value_rejected` (line 328), `test_skill_non_string_rejected` (line 341) — VERIFIED. Mirror exactly for `_apply_lens`: happy path persists `store.extra["lens"]`, invalid enum rejected `(False, ...)`, non-string rejected, persists-to-disk via the `_redirect_config_path` fixture.

### `tests/library/test_curator_persona_seam.py` (ADD)
**Analog:** the file's own seam-tier tests. ADD: curator seam reads the shared lens (not hardcoded `"tutor"`); default `"tutor"` when `extra["lens"]` unset (cold-path byte-identity). Reset the module-global caches between cases.

### `tests/agent/test_dj_cohost.py` (ADD)
**Analog:** existing `_resolve_prompt_cell` tests in that file (monkeypatch env vars). ADD: lens → `(mode, mood)` resolution; cold-path (no lens set) byte-identical to today's `DEFAULT_*` resolution.

---

## No Analog Found

None. Every file in this phase extends an existing, verified in-repo pattern. This is a pure additive prompt-architecture refactor with zero new infrastructure (RESEARCH §Summary).

---

## Planner Decision Flags (verified caveats the planner must resolve)

1. **`lens` on the `SettingsState` wire snapshot = a schema bump.** Adding `lens` to `SettingsStatePayload` (messages.py:349-369) + `SettingsState.make(...)` (session_loop.py:1190-1202) requires editing `tauri/ui/src/ipc/messages.schema.json` (the `SettingsState` `$comment` at line 1310 + a new optional enum prop alongside `mood`/`skill` at 1380-1404) **AND running `npm run codegen:ipc`** (the frontend ajv validator is PRE-COMPILED — MEMORY: `feedback_schema_edit_needs_codegen_ipc`). The **smaller-diff path** that avoids the schema bump: persist `lens` only in `ConfigStore.extra["lens"]` (read directly by both builders), and do NOT round-trip it through the wire snapshot for v1. RESEARCH's anti-pattern list says "no new ws port / IPC envelope" — a new *field on an existing snapshot* is borderline; the extra-only path is strictly cleaner and satisfies LENS-02 (both builders read the shared value). **Recommendation: extra-only, no schema bump, for the smallest additive diff.** If a UI selector is later wanted (explicitly deferred in CONTEXT), the schema+codegen step is the follow-up.

2. **One global default lens vs per-surface default-when-unset** (RESEARCH Open-Q1). Recommendation: per-surface default-when-unset (co-host→`hype`, curator→`tutor`) so both cold paths stay byte-identical; once the user explicitly sets a lens, that one value drives both.

3. **Curator module-global cache invalidation** (see seam section gotcha) — read-lens-per-call vs next-process semantics.

4. **Tutor maps to `(coach, teacher)` for v1** (RESEARCH A3, Pitfall 4) — no dedicated `TUTOR_*` cell. Tutor fidelity is judged by Phase 81 BENCH + Kaan's ear (parked). Do NOT build a bespoke tutor cell this phase.

## Metadata

**Analog search scope:** `src/vibemix/prompts/`, `src/vibemix/runtime/`, `src/vibemix/agent/`, `src/vibemix/library/`, `src/vibemix/coach/`, `src/vibemix/ui_bus/`, `tests/prompts/`, `tests/runtime/`, `tests/library/`, `tauri/ui/src/ipc/`
**Files scanned:** matrix.py, settings.py, dj_cohost.py, library/agent.py, library/codex_curate.py, citation_linter.py, session_loop.py, messages.py, messages.schema.json, test_settings_apply.py, test_curator_persona_seam.py
**All line numbers re-verified against live source (branch `live-tuning-or-brain`).**
**Pattern extraction date:** 2026-05-26
