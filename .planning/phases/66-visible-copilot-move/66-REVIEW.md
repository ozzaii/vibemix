---
phase: 66-visible-copilot-move
reviewed: 2026-05-22T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - src/vibemix/agent/dj_cohost.py
  - src/vibemix/state/coach.py
  - tests/agent/test_citation_strip_emit.py
  - tests/agent/test_dj_cohost_linter.py
  - tests/state/test_coach.py
  - tests/repo/test_no_recall_antifeatures.py
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 66: Code Review Report

**Reviewed:** 2026-05-22
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Phase 66 ("Visible Copilot Move") wires the recall chip into `_build_citation_strip`, adds a coach-tier `RECALL_CALLBACK_COOLDOWN_S=120.0s` cooldown, threads two prompt fragments (transition-shape + vocabulary) into `AICoach.build_prompt` via the `recall_fragment_for_event` helper, and lands a static anti-feature gate in `tests/repo/test_no_recall_antifeatures.py`.

The bulk of the implementation is careful: the cold-path byte-identity contract holds (recall_moments=None / [] / no-kwarg all return identical strings, pinned by `test_task_for_event_byte_identical_v5_baseline_no_recall`); the cooldown arms strictly on the `else:` branch of the bus-emit try in the bus path; the strongest-survivor-only interpolation is structural (only `recall_moments[0].record_id` is fed to the template); the Phase 65 floor stays untouched (`clear_source("recall")` is still unconditional per `recall_enabled` turn, the `bump_generation` flag survives on the reactive clear, registration writes BEFORE the snapshot).

The headline defect: the **bus-less cooldown arm path** (dj_cohost.py:1635-1654) arms on `citation_action in ("emit", "bypass")` using a **raw `parse_citations(full_text)` scan** that is NOT registry-validated. On the bypass path, a FABRICATED `[recall:<unregistered>]` atom will arm the cooldown — breaking the "REACHED the audience" semantic the bus path enforces structurally (the chip-strip filters by registry presence). The two paths must produce the same arm/no-arm decision; today they don't.

Secondary concerns: the anti-feature tuple has obvious-gap synonyms (e.g. "your typical move", "you've been"), the linter-stripped test is partially undermined by the fact that the stripper replaces STRINGS with `""` (so even a real forbidden phrase inside a string literal won't trip the gate — defense-in-depth depends on the §RECALL-EAR Kaan-ear check), and the bus-less arm path additionally has a subtle redundancy with `_recall_enabled` (it arms even when recall is OFF, which is a no-harm but spec-violating path).

## Critical Issues

### CR-01: Bus-less cooldown arm uses raw parse_citations (skips registry-validation), arms on bypass with fabricated recall atoms

**File:** `src/vibemix/agent/dj_cohost.py:1635-1654`
**Issue:** The bus-less cooldown arm scans `full_text` with `parse_citations(...)` and arms if ANY `("recall", body)` atom appears. This differs from the bus path (lines 1592-1634), which builds `strip` via `_build_citation_strip` — which only emits chips for atoms that **resolve in the registry**. On the BYPASS path (`citation_action == "bypass"`, linter said `invalid` but the one-shot bypass let the unverified text through), `full_text` can contain a FABRICATED `[recall:<unregistered_id>]`. The bus path correctly does NOT arm in that case (the unregistered atom yields no chip). The bus-less path arms anyway. The two paths must yield the same decision per the strict "REACHED the audience" semantic locked in CONTEXT.md Area 1 Q3.

A secondary leak: this arm runs even when `self._recall_enabled is False` (the outer condition checks only `citation_action` and `_ipc_bus is None`). If a future flag-OFF code path were ever to emit a `[recall:...]` atom (today the prompt fragment is gated by `recall_enabled`, so this is theoretical), the cooldown would arm with no recall service in play — a state confusion the design explicitly tries to avoid.

**Fix:** Mirror the bus path's structural filter — validate against the registry, or simply reuse the same `_build_citation_strip` lens:

```python
elif self._ipc_bus is None and citation_action in ("emit", "bypass"):
    # Phase 66 (COPILOT-02) — bus-less arm path. Mirror the bus path's
    # structural filter: only arm when a [recall:<id>] atom that resolves
    # IN THE REGISTRY survives. parse_citations alone would also arm on a
    # fabricated recall id under bypass (linter let it through), breaking
    # the "REACHED the audience" semantic the bus path enforces.
    if not self._recall_enabled or self._registry is None:
        pass  # feature OFF or no registry — never arm without backing state
    else:
        try:
            strip = _build_citation_strip(
                reaction_text=full_text,
                registry=self._registry,
            )
            if any(
                chip.get("event_id", "").startswith("recall:")
                for chip in strip
            ):
                self._last_recall_callback_at = time.time()
        except Exception as _e:  # noqa: BLE001
            print(f"\n[recall cooldown arm err] {_e}", file=sys.stderr)
```

This unifies the bus and bus-less arm logic on the same structural lens (`_build_citation_strip`), eliminating the bypass-asymmetry and the flag-OFF arm path in one move.

## Warnings

### WR-01: Anti-feature forbidden-phrase tuple has obvious-synonym gaps

**File:** `tests/repo/test_no_recall_antifeatures.py:118-130`
**Issue:** The FORBIDDEN_RECALL_PHRASES tuple covers the cardinal failure modes from 66-RESEARCH §Pitfall 6 but misses near-synonyms that any production-corpus drift would naturally land on. Examples not in the tuple:
- "your typical" / "your typical move" (paraphrase of "tendency")
- "you've been" / "you've usually" (past-tense tendency)
- "your habit" / "your habits"
- "you keep doing" / "you keep" (recurrence claim)
- "your style" (personalization-as-attribute)
- "your move would" / "you'd usually" (predictive personalization)
- "try next" / "play next" (next-track paraphrase)
- "you should ride" / "you should drop" (recommendation paraphrase that "you should play" doesn't catch)
- "I'd recommend" (contraction not caught by "i recommend")

Note: the comment at the top of the file acknowledges the gate is VACUOUS-GREEN at land (no forbidden phrase in TARGET_FILES today, and the stripper removes STRING contents anyway — see WR-02 below). So this gate's real lifetime value is "human-readable signal that Kaan/PR reviewers should rerun the Kaan-ear check if a tuple-listed phrase ever surfaces". The narrower the tuple, the weaker the signal.

**Fix:** Either expand the tuple to cover the obvious-synonyms above, or rename the gate to make its limited scope explicit (e.g. `FORBIDDEN_LITERAL_RECALL_PHRASES` + a docstring note that the real defense is the Kaan-ear runtime check). Concretely, at minimum add:
```python
FORBIDDEN_RECALL_PHRASES: tuple[str, ...] = (
    "you tend to", "you usually", "you always", "you've been", "you've usually",
    "your tendency", "your tendencies", "your typical", "your habit", "your habits",
    "your style",
    "based on your past", "based on your history",
    "next track", "play next", "try next",
    "you should play", "you should try", "you should ride", "you should drop",
    "i recommend", "i'd recommend", "my recommendation",
    "you keep", "you keep doing",
)
```

### WR-02: Static gate is functionally vacuous against TARGET_FILES — the comment is honest but the test name overpromises

**File:** `tests/repo/test_no_recall_antifeatures.py:172-256`
**Issue:** The module docstring explicitly documents that the tokenize stripper replaces STRING tokens with `""` AND removes COMMENT tokens. For human English prose (multi-word strings), the ONLY place a forbidden phrase can live in source is inside a STRING or COMMENT — Python identifiers cannot contain spaces. Therefore the main scan is mathematically incapable of firing on prompt fragment literals (the place where a forbidden phrase WOULD reach Gemini). The gate as written can ONLY catch a Python NAME-token sequence — which is impossible for multi-word English prose. This is acknowledged in the module docstring ("The main scan is necessarily VACUOUS against TARGET_FILES").

So the test's name (`test_no_recall_antifeatures_in_coach_surface_COPILOT03`) reads as a defense-in-depth gate, but in fact the gate's only mechanical claim is "no future commit accidentally adds an English-prose anti-feature phrase as a Python NAME token" — which is syntactically impossible. The actual defense (Kaan-ear check, KAAN-ACTION-LEGAL.md §RECALL-EAR) lives elsewhere.

This is not a code defect — the implementation matches the documented semantic — but the test gives a false sense of security to any reader who hasn't read the divergence section in the module docstring.

**Fix:** Either:
1. Rename the test to `test_no_recall_antifeatures_in_coach_NAME_tokens_only_COPILOT03` to be explicit about what it actually checks; OR
2. Add a SECOND scan that does NOT strip STRING tokens — only COMMENTS — so prompt fragment literals are scanned for forbidden phrases. This would correctly fire if a future engineer copy-pastes "you tend to" into a fragment template body. The cost: the in-template "do NOT claim a tendency ('you usually do', 'you always')" examples become offenders. Carve out by listing the current template literal substrings as known-good, OR re-author the templates so their negative examples use different lexicalizations (e.g. replace `'you usually do'` with `'YOU-USUALLY-DO'` so the gate doesn't trip while Gemini still sees the negative-example pattern).

The current implementation chose path 1 implicitly (the gate is type-level only); the test name should be made explicit so future maintainers don't loosen the stripper assuming the gate would catch a regression.

### WR-03: Cooldown can suppress recall on the FIRST recall-eligible turn after an unrelated bypass turn

**File:** `src/vibemix/agent/dj_cohost.py:845-848` + the bus-less arm at 1635-1654 + the bus arm at 1611-1634
**Issue:** Consider this sequence under `recall_enabled=True`:
1. Turn N is a recall-eligible event (TRACK_CHANGE). Survivors arrive, recall_moments non-empty, the fragment is built, Gemini emits `[recall:<id>]`. Linter passes (the id was registered). Bus emit succeeds. Cooldown arms at t=N.
2. Turn N+1 is the same event class within 120s. Cooldown gate at line 845-848 drops survivors to `[]`. Correct — no callback this turn.

Now consider this alternate sequence:
1. Turn N is recall-eligible. Survivors non-empty. Fragment built. Gemini emits a fabricated `[recall:<bad>]`. Linter says invalid. should_bypass() returns True (one-shot bypass fires). Text emitted. citation_action == "bypass". Bus path: `_build_citation_strip` returns `[]` (fabricated id has no chip). `any(...startswith("recall:"))` is False. **Cooldown does NOT arm.** Good — the audience heard a fabricated callback, but the cooldown thinks no recall reached them. Future turn N+1 will allow another recall.

Now repeat sequence with the bus-less path:
1. Same fabricated-recall-under-bypass turn. `parse_citations(full_text)` finds `("recall", "<bad>")`. Cooldown arms with a fabricated atom backing it. Turn N+1 within 120s now suppresses a LEGITIMATE recall that should have surfaced.

This is the CR-01 issue's downstream user-visible effect: in the bus-less path, a bypass turn that leaked a fabricated recall now suppresses legitimate recalls for 120s.

**Fix:** Fix CR-01. Same fix closes this.

### WR-04: `_record_said` history line uses `state.set_seconds`, not the turn-fired set_seconds — small but real cross-turn drift

**File:** `src/vibemix/agent/dj_cohost.py:579-590` (`_record_said`)
**Issue:** `_record_said` reads `self._state.set_seconds` AT THE TIME `_record_said` is called — which is AFTER the entire llm_node call has completed (stream consumed, lint gate, bus emit). On a 2-3s reaction turn, the set_seconds at write time is 2-3s AFTER the event fired. The history line `[M:SS]` then carries the END-of-reaction set time, not the EVENT-fired set time. Downstream, the prompt's "RECENT THINGS YOU JUST SAID" clause asks Gemini to compare set times. So the history clauses appear ~2-3s late, which over a session can produce minor drift in Gemini's "how long ago did I cover that" reasoning.

This is a pre-existing concern, not introduced by Phase 66 — but Phase 66 didn't change `_record_said` while adding callable patterns that compare set times. If a future fix wants to preserve the EVENT-fired set time, capture it at `set_next_event` time and pass it through.

**Fix:** Capture `ev.state.set_seconds` at set_next_event time and store it alongside `_pending_event`, then read it in `_record_said`. Alternatively, accept the drift as documented behavior and add a comment to `_record_said` clarifying the timing semantic.

```python
def _record_said(self, text: str, set_s_at_event: float | None = None) -> None:
    # Use the EVENT-fired set time when provided; fall back to live state
    # for legacy callers that don't yet thread the event-fired value.
    set_s = (
        set_s_at_event
        if set_s_at_event is not None
        else (getattr(self._state, "set_seconds", 0.0) or 0.0)
    )
    ...
```

## Info

### IN-01: `_maybe_dispatch_recall` imports inside the function body — fine for laziness, but the import error is silently swallowed

**File:** `src/vibemix/agent/dj_cohost.py:642-651`
**Issue:** The lazy import of `vibemix.memory.retrieval` is wrapped in a bare `except Exception` that logs to stderr and returns. If the memory module is renamed or its public surface drifts, the agent will silently skip recall dispatch — not an outright failure, but `recall_enabled=True` users will see no recall callbacks with no actionable signal beyond a stderr line that won't be looked at.

**Fix:** Promote the import-failure log to a `recorder.log_event("recall_import_failure", ...)` so events.jsonl surfaces it for coach-loop tails. The diagnostic-trail value is high; cost is one extra log line per import failure (rare).

### IN-02: `recall_fragment_for_event` docstring describes the helper as called from `AICoach.build_prompt` in the non-diet path — but the actual integration is in `build_prompt`, not at `dj_cohost.py:827`

**File:** `src/vibemix/state/coach.py:166-171`
**Issue:** The docstring says: "It is called from `AICoach.build_prompt` in the non-diet path; the diet path skips it entirely". Correct. But the parenthetical "the existing `_bp_kwargs` logic at `dj_cohost.py:827` already withholds `recall_moments` from the diet call" is a stale line reference — the current code at line 921-923 builds `_bp_kwargs` and conditionally adds `recall_moments`. The reference is approximately correct but the line number is wrong, and the language ("already withholds") is backward — the agent only ADDS the kwarg when `recall_moments and not diet`, so the diet path doesn't withhold, it never adds.

**Fix:** Update the docstring to describe the actual logic and drop the stale line reference, or use a name-anchor reference (e.g. "see the `_bp_kwargs` construction in `DJCoHostAgent.llm_node`") that doesn't go stale on line drift.

### IN-03: Cooldown docstring at `dj_cohost.py:520-531` references a test that doesn't appear to exist by that exact name

**File:** `src/vibemix/agent/dj_cohost.py:520-535` (in the `_last_recall_callback_at` docstring)
**Issue:** The comment says the gate is "pinned by `test_cooldown_suppresses_back_to_back_recalls_COPILOT02`" and walks through a mocked t=100.0 / t=180.0 scenario. The test exists at `tests/agent/test_dj_cohost_linter.py:673` and matches the scenario. But the docstring also says "the plain `0.0` initializer would incorrectly trip the gate" — verified, since the gap on the first turn would be (100.0 - 0.0) = 100.0 < 120.0 → suppress. The `-inf` init is correct. Just confirming the docstring's reasoning checks out.

No fix needed — this is informational. The reasoning is sound and the test pins it.

---

_Reviewed: 2026-05-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
