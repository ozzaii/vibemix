---
phase: 79-lens-three-grounded-modes
reviewed: 2026-05-26T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/vibemix/agent/dj_cohost.py
  - src/vibemix/library/agent.py
  - src/vibemix/library/codex_curate.py
  - src/vibemix/prompts/matrix.py
  - src/vibemix/runtime/settings.py
findings:
  critical: 2
  warning: 4
  info: 2
  total: 8
status: fixes_applied
fix_summary:
  fixed:
    - CR-01  # lens wins over auto-mood on the live co-host path
    - CR-02  # validate persisted lens before subscript (no KeyError)
    - WR-02  # _apply_lens rebuild parity with _apply_skill (doc the shared lifecycle)
    - WR-03  # curator _shared_lens() read-failure guard (default tutor)
    - WR-04  # curator instruction-cache check-then-set lock
  deferred:
    - WR-01  # lens absent from ipc.settings.set enum — UI wiring is a KAAN-ACTION follow-up (see below)
  not_fixed_info:
    - IN-01  # info, out of scope — but the new production-path test added under CR-01 closes the false-green
    - IN-02  # info, out of scope — the co-host consumer now re-validates (CR-02), satisfying the design intent
---

# Phase 79: Code Review Report

**Reviewed:** 2026-05-26
**Depth:** standard
**Files Reviewed:** 5
**Status:** fixes_applied

> **FIX PASS 2026-05-26** — Both BLOCKERs and 3 of 4 WARNINGs fixed and committed
> atomically; WR-01 is intentionally DEFERRED (UI wiring is a KAAN-ACTION
> follow-up). Full suite green without an API key (4499 passed; the only 3
> failures — `tests/repo/test_cut_release_dry_run.py` — are PRE-EXISTING on the
> base commit `6aa3f6f`: they require signed `.dmg/.pkg/.msi/.exe` artifacts in
> `dist/`, an artifact precondition unrelated to the lens code).
>
> - **CR-01** ✅ fixed — lens now resolved BEFORE the mood arg; an explicit valid
>   lens wins over the auto-derived live `MusicState.mood`; cold path
>   byte-identical. New production-path test `test_resolve_prompt_cell_lens_wins_over_live_mood`
>   (`mood="hype-man"` + `tutor` lens → tutor cell).
> - **CR-02** ✅ fixed — `lens in LENS_TO_MODE_MOOD` validation before subscript;
>   corrupt persisted value falls through to cold path, no `KeyError`. New test
>   `test_resolve_prompt_cell_corrupt_lens_falls_back_no_crash`.
> - **WR-02** ✅ fixed (doc) — `_apply_lens` parity with `_apply_skill` made
>   explicit; both ride the shared Plan 13-06 next-build lifecycle, no new
>   rebuild mechanism invented.
> - **WR-03** ✅ fixed — both curator `_shared_lens()` reads guarded, default
>   `"tutor"` on any failure.
> - **WR-04** ✅ fixed — module `threading.Lock` guards the check-then-set in all
>   three curator instruction-cache builders (gemini + codex).
> - **WR-01** ⏸ DEFERRED — see the WR-01 section. Lens persistence stays
>   extra-only by design (no schema bump this run); UI enum + lens-picker +
>   `codegen:ipc` + live verify is a KAAN-ACTION follow-up.
> - **IN-01 / IN-02** — Info, not in fix scope. The CR-01/CR-02 fixes
>   incidentally close both concerns (production-path test added; consumer now
>   re-validates).

## Summary

Phase 79 adds a "lens" persona-axis selector shared between the live co-host and
the curator. The curator-side cache invalidation, the matrix `build_lens_instruction`
seam, the `read_shared_lens` default handling, and `_apply_lens` enum validation are
all implemented soundly and largely match the existing `_apply_skill`/`_apply_mood`
patterns.

However, the **headline contract of the phase — "choosing the lens once flows to
the live co-host" — is broken on the actual production build path** (CR-01), and the
co-host's direct dict subscript of a persisted-but-unvalidated lens value can crash
agent construction (CR-02). Both are masked by tests that don't exercise the real
caller. There is also a wire-reachability gap: the IPC schema enum does not include
`"lens"`, so `_apply_lens` is currently unreachable from the UI (WR-01).

## Critical Issues

### CR-01: Lens never reaches the live co-host on the real build path (precedence bug)

**File:** `src/vibemix/agent/dj_cohost.py:341-353` (and caller `:480-481`)

**Issue:** `_resolve_prompt_cell` only consults the shared lens when `mood is None`:

```python
if mood is None:
    ...
    lens = read_shared_lens(load_config())
    if lens is not None:
        mode, lens_mood = LENS_TO_MODE_MOOD[lens]
        return build_system_instruction(skill, mode, lens_mood)
```

But the only production caller passes a non-`None` mood:

```python
# DJCoHostAgent.__init__  (line 480-481)
live_mood = getattr(state, "mood", None)
prompt_body = _resolve_prompt_cell(mood=live_mood)
```

`MusicState.mood` defaults to `"hype-man"` (`state/music_state.py:98`) and is never
`None` in a live session. So `mood` is always non-`None` at build time, the entire
lens block is skipped, and resolution falls through to `ENV_MODE` → `DEFAULT_MODE =
"hype"`. **Setting the lens to `tutor` or `critique` has zero effect on the live
co-host's mode** — it stays `hype`. The phase's core promise ("one selection flows
to BOTH surfaces") holds for the curator but is silently dead for the co-host.

The two tests that "prove" this (`tests/agent/test_dj_cohost.py:1212`,
`:1237`) call `dj_mod._resolve_prompt_cell()` with no argument (`mood=None`), so they
exercise a path the production code never takes — false green.

**Fix:** The lens (when set) must win over the live `MusicState.mood`, since lens is
the canonical persona axis that *determines* mode. Resolve the lens before applying
the mood override, e.g.:

```python
def _resolve_prompt_cell(mood: str | None = None) -> str:
    skill = os.environ.get(ENV_SKILL_LEVEL, DEFAULT_SKILL_LEVEL)
    # Shared lens wins over the live MusicState.mood: it IS the persona axis.
    try:
        from vibemix.runtime.config_store import load_config
        from vibemix.runtime.settings import read_shared_lens
        lens = read_shared_lens(load_config())
    except Exception:
        lens = None
    if lens is not None and lens in LENS_TO_MODE_MOOD:
        mode, lens_mood = LENS_TO_MODE_MOOD[lens]
        return build_system_instruction(skill, mode, lens_mood)
    # cold path (unchanged): env mood override > env/DEFAULT
    mode = os.environ.get(ENV_MODE, DEFAULT_MODE)
    if mood is None:
        mood = os.environ.get(ENV_MOOD, DEFAULT_MOOD)
    return build_system_instruction(skill, mode, mood)
```

Then add a test that calls `_resolve_prompt_cell(mood="hype-man")` (the real arg the
agent passes) with a `critique` lens set and asserts the coach cell is produced.
Decide explicitly whether the live mood-pill should still be able to override the
lens; if so, document and test that precedence — but the current behavior (mood
*silently disables* the lens) is not a deliberate precedence, it's a bug.

---

### CR-02: Corrupt/foreign persisted `extra["lens"]` crashes agent construction (KeyError)

**File:** `src/vibemix/agent/dj_cohost.py:349-353`

**Issue:** `read_shared_lens` returns *any* non-empty string from `extra["lens"]`
without validating it against the lens enum (`settings.py:88-91`). The co-host then
subscripts the map directly, **outside** the guarding `try/except`:

```python
if lens is not None:
    from vibemix.prompts.matrix import LENS_TO_MODE_MOOD
    mode, lens_mood = LENS_TO_MODE_MOOD[lens]   # KeyError if lens not a key
    return build_system_instruction(skill, mode, lens_mood)
```

The `try/except Exception` only wraps the `read_shared_lens(load_config())` call
(lines 342-348), not the subscript. So a `config.json` carrying e.g.
`extra["lens"] = "coach"` (a valid *mood* but not a lens key), or any stale/foreign/
hand-edited value, raises an uncaught `KeyError` and crashes agent construction —
exactly the cold-path regression the guard claims to prevent. The docstring asserts
"the builders re-validate the returned lens (defense-in-depth — T-79-03-02)", but
this path bypasses the builders and subscripts the dict raw, so that defense does
not exist here. `_apply_lens` validates on *write*, but disk can carry a value
written by another process/version/manual edit.

**Fix:** Validate before subscripting (and the fix for CR-01 above already includes
`lens in LENS_TO_MODE_MOOD`):

```python
if lens is not None and lens in LENS_TO_MODE_MOOD:
    mode, lens_mood = LENS_TO_MODE_MOOD[lens]
    return build_system_instruction(skill, mode, lens_mood)
# unknown persisted lens → fall through to cold path (or call build_lens_instruction
# which raises ValueError — but never let a raw KeyError escape construction)
```

Prefer delegating to `build_lens_instruction` (which validates with a clear
`ValueError`) over a bare subscript, OR fall through to the cold path for an unknown
value. Either way the raw `KeyError` must not escape.

## Warnings

### WR-01: `lens` is not in the IPC settings.set field enum — `_apply_lens` is unreachable from the UI

> **STATUS: DEFERRED (KAAN-ACTION).** Per the fix-scope decision this run does
> NOT touch `messages.schema.json` / run `npm run codegen:ipc`: the polished
> lens-picker UI control is explicitly deferred in 79-CONTEXT, and a schema bump
> needs live-app verification this autonomous run cannot do (invariant #4 — no
> IPC/schema bump). The shared-selection MECHANISM that LENS-02 requires (both
> surfaces read `extra["lens"]`) is implemented and now works end-to-end on the
> live co-host (CR-01). Lens persistence remains config-/extra-only for now.
>
> **Deferred follow-up (KAAN-ACTION):** add `"lens"` to the `ipc.settings.set`
> `field` enum in `tauri/ui/src/ipc/messages.schema.json`, run
> `npm run codegen:ipc` to regenerate `validator.generated.mjs`, confirm
> `check_ipc_schema.py` parity, wire a lens-picker control into the settings
> drawer, then verify LIVE in `cargo tauri dev`. Until then `_apply_lens` is a
> config-only handler, not a live UI control.


**File:** `src/vibemix/runtime/settings.py:474-502` (handler) — root cause in
`tauri/ui/src/ipc/messages.schema.json:1250-1262` (out of reviewed scope, flagged for completeness)

**Issue:** The `ipc.settings.set` `field` enum lists
`voice, mode, genre, output_device_id, output_profile, retention_days,
push_to_mute_hotkey, mood, click_through, lighter_blur, skill` — **`lens` is
absent**. The pre-compiled frontend validator (`validator.generated.mjs`, 0
occurrences of "lens") and the Python schema-parity check will reject an
`ipc.settings.set` with `field: "lens"` *before* it reaches `_apply_lens`. As
shipped, the new handler is dead code from the UI's perspective: the only way to set
the lens is to hand-edit `config.json`. Per the project memory note, a schema edit
also requires `npm run codegen:ipc` to regenerate the validator.

This is outside the 5 Python files under review, but it determines whether the
reviewed handler is reachable at all, so it is load-bearing for the phase.

**Fix:** Add `"lens"` to the `field` enum in `tauri/ui/src/ipc/messages.schema.json`,
regenerate the validator (`npm run codegen:ipc`), and confirm `check_ipc_schema.py`
parity. If the phase deliberately deferred the UI wiring, document `_apply_lens` as
config-only for now so it isn't mistaken for a live control.

### WR-02: Same-process lens change leaves the live co-host on the stale voice (no rebuild)

**File:** `src/vibemix/runtime/settings.py:474-502`

**Issue:** `_apply_skill` and `_apply_mood` both have an out-of-band mechanism to
make the change visible (env var read at next agent build; MusicState write + bus
emit + Plan 13-06 agent re-instantiation). `_apply_lens` only persists to
`extra["lens"]` and returns — it does not trigger a co-host agent rebuild, write
MusicState, or emit anything. The docstring claims it "takes effect on the next
agent build", but nothing in this path *causes* a rebuild. Combined with CR-01, the
live co-host will not pick up a lens change until the agent is independently
re-instantiated for some other reason (or process restart). The curator side is
fine (it reloads config + invalidates its cache per request).

**Fix:** Wire `_apply_lens` into the same agent-rebuild lifecycle that mood/skill
ride (Plan 13-06), or document that lens is restart-only and remove the "takes
effect on the next agent build" claim. At minimum, the divergence from
mood/skill behavior should be explicit, since the phase frames lens as the
*canonical* persona axis that supersedes mood.

### WR-03: Curator lens read does a synchronous disk load on every request with no failure guard

**File:** `src/vibemix/library/agent.py:106-118`, `src/vibemix/library/codex_curate.py:90-101`

**Issue:** Both curator `_shared_lens()` helpers call `load_config()` (a disk read)
on every cache-miss check. Unlike the co-host path (CR-01), there is no `try/except`
around `read_shared_lens(load_config())` here. `load_config()` itself swallows
`OSError`/`JSONDecodeError` and returns defaults (`config_store.py:298-303`), so a
corrupt file degrades gracefully — but any *other* exception (e.g. a permission
error surfaced differently, or a future `from_dict` change) would propagate out of
`_system_instruction()` and break curation. The co-host path guards this; the
curator path does not, an inconsistency given both read the same source.

**Fix:** For symmetry and robustness, wrap the curator `_shared_lens()` read in the
same guard the co-host uses, defaulting to `"tutor"` on any read failure:

```python
def _shared_lens() -> str:
    try:
        from vibemix.runtime.config_store import load_config
        from vibemix.runtime.settings import read_shared_lens
        return read_shared_lens(load_config(), default="tutor") or "tutor"
    except Exception:
        return "tutor"
```

### WR-04: Curator instruction caches are not thread-safe (check-then-set race)

**File:** `src/vibemix/library/agent.py:121-149`, `src/vibemix/library/codex_curate.py:104-113`

**Issue:** `_system_instruction` / `_interactive_system_instruction` / `_system_prompt`
read+compare+write module globals (`_..._CACHE`, `_..._LENS`) without a lock. If two
threads enter on a lens change concurrently, both can pass the
`cache is None or _LENS != lens` check, both rebuild, and one can write
`_CACHE`/`_LENS` interleaved with the other — leaving `_CACHE` built under lens A but
`_LENS` recording lens B, which then serves the wrong voice until the next change.
The curator backends are largely single-threaded per process today (CLI / MCP
subprocess), so the practical blast radius is small — hence WARNING not BLOCKER — but
the gemini agent does use a `ThreadPoolExecutor` for the model call (`agent.py:316`)
and nothing documents the single-thread assumption.

**Fix:** Either document the single-threaded invariant explicitly, or guard the
cache read/write with a module-level `threading.Lock` (cheap, only on the build
path). The build is idempotent, so a simpler fix is to set `_CACHE` last and assign
`_LENS` only after `_CACHE`, then re-read `_CACHE` once — but a lock is clearer.

## Info

### IN-01: Tests assert lens behavior on a code path the production caller never uses

**File:** `tests/agent/test_dj_cohost.py:1212-1258`

**Issue:** Both lens tests call `_resolve_prompt_cell()` (mood defaulting to `None`),
while `DJCoHostAgent.__init__` always calls `_resolve_prompt_cell(mood=live_mood)`
with a non-`None` mood. The tests are green but provide false confidence — they are
the reason CR-01 shipped undetected. Add a test that calls with the real argument
shape.

**Fix:** Add `test_resolve_prompt_cell_lens_wins_over_live_mood` that passes
`mood="hype-man"` plus a `critique` lens and asserts the coach cell, mirroring the
production call.

### IN-02: `read_shared_lens` returns `str | None` but the co-host treats every non-empty string as a valid lens

**File:** `src/vibemix/runtime/settings.py:68-91`

**Issue:** The function intentionally does not validate against `_VALID_LENSES`
(documented as "builders re-validate"), but as CR-02 shows, the co-host consumer does
not actually re-validate. Consider validating here against `_VALID_LENSES` and
returning `default` for an out-of-enum persisted value — it would make the function
safe-by-default for *all* consumers rather than relying on each caller to re-check.
This is a design suggestion; if kept as-is, every consumer must be audited for the
unvalidated-string contract (currently the co-host fails that audit — CR-02).

---

_Reviewed: 2026-05-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
