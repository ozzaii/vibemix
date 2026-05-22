---
phase: 66-visible-copilot-move
plan: 02
subsystem: agent (chip allow-list + cooldown) + state (prompt fragments) + docs (HUMAN-UAT + KAAN-ACTION)
tags: [phase-66, copilot, recall, chip, prompt-fragment, cooldown, kaan-action, wave-1, green, ui-tier-1]

# Dependency graph
requires:
  - phase: 66-visible-copilot-move (Plan 01)
    provides: "Wave 0 RED contract — 9 new tests + 1 negative-control stripper test pinning the COPILOT-01/02/03 surface BEFORE any source edit"
provides:
  - "Visible recall chip on the existing SessionCohostReaction.citation_strip (fifth source after ev/mix/midi/key)"
  - "Coach-tier recall-callback cooldown (≥120s between any two callbacks; max 1 per turn structurally)"
  - "Two prompt-fragment templates that INVITE Gemini to emit ONE [recall:<id>] callback when a survivor matches NOW"
  - "Phase 66 engineering-green baseline behind VIBEMIX_RECALL_ENABLED=0 flag (Kaan-ear discharge via §RECALL-EAR in KAAN-ACTION-LEGAL.md)"
affects: [66-03-PLAN.md / Phase 67+ if a v6.1 chip-differentiation phase opens]

# Tech tracking
tech-stack:
  added: []  # pure code-edit + doc phase — zero net-new deps
  patterns:
    - "Falsy-gate for cold-path byte-identity (Pattern A in 66-PATTERNS.md) — `if not recall_moments: return ''` mirrors the Phase 65 evidence_line recall block"
    - "Strict 'REACHED the audience' cooldown-arm semantic — `else:` branch of the bus-emit try/except (success-only); bus-less arm path on `citation_action in {emit, bypass}` + parse_citations scan over full_text"
    - "Fixed letters-only verb for opaque/structured citation bodies — `recall` mirrors `key` precedent (Phase 59 DECK-03)"
    - "Strongest-survivor-only template interpolation — Phase 65 cosine_topk returns DESC by score so `recall_moments[0]` is the strongest; weaker survivors stay in the upstream evidence_line PAST-tense block (max-1-per-turn structural cap)"
    - "Module-scope one-line-tunable constants (`RECALL_CALLBACK_COOLDOWN_S = 120.0`) — Kaan-ear can re-tune without surrounding wiring depending on the literal (Pattern C in 66-PATTERNS.md)"

key-files:
  created:
    - ".planning/phases/66-visible-copilot-move/66-HUMAN-UAT.md — NEW (78 lines, 4 ear-tests + Summary block + Gaps section)"
  modified:
    - "src/vibemix/agent/dj_cohost.py — 4 structural edits totaling +141 lines / -1 (commit 0bfc8bd)"
    - "src/vibemix/state/coach.py — 2 structural edits totaling +189 lines / -1 (commit b6cc4d2)"
    - "KAAN-ACTION-LEGAL.md — §RECALL-EAR section appended (+115 lines, commit 8c1f733)"
    - "tests/state/test_coach.py — 1 Rule-1 fix (out_default → out typo from Wave 0)"
    - "tests/agent/test_dj_cohost_linter.py — 1 Rule-1 fix (loosen count == 1 to count >= 1 for verbatim template's 2 interpolations)"

key-decisions:
  - "Cooldown arm site: `else:` branch of bus-emit try/except + bus-less arm path on `citation_action in {emit, bypass}` — strict 'REACHED the audience' semantic per CONTEXT.md Area 1 Q3 + RESEARCH §Pitfall 2 + §Open Q5. The bus-less branch is a Rule-1 deviation: the locked test contract (test_cooldown_suppresses_back_to_back_recalls_COPILOT02) does NOT wire `_ipc_bus`, so the cooldown would never arm in production agents that skip the IPC bus surface if the plan's strict 'inside the if _ipc_bus is not None' placement was taken literally. The bus-less path uses the same `citation_action in {emit, bypass}` gate (the bus-emit's own user-heard-the-text gate) so both branches share the 'REACHED the audience' semantic."
  - "Per-agent `_last_recall_callback_at` initializer: `float('-inf')` not `0.0` — Rule-1 deviation. The plan's literal `0.0` initial value would suppress the FIRST recall callback whenever `time.time()` is mocked to a small value < 120 (the cooldown test mocks `t=100.0` on turn N → gap=100 < 120 → recall_moments wrongly dropped). `-inf` is the never-armed sentinel that guarantees the first callback always passes the gate regardless of wall-clock."
  - "Template interpolation count: each fragment template has TWO `{record_id}` placeholders (both filled with the same id for instruction reinforcement). The Wave 0 test assertion `fragment_portion.count(record_id) == 1` was overly strict — the structural max-1-per-turn cap is preserved by the no-other-record_id-leaks assertions that remain (record_b / record_c absence). Loosened to `>= 1` (Rule-1 deviation)."
  - "TRACK_CHANGE overlap resolution (CONTEXT.md Area 1 Q1+Q2 lock): TRACK_CHANGE is in BOTH transition-shape and vocabulary event gates; transition WINS by being listed FIRST in the helper branch order (mirrors 66-RESEARCH.md §Pitfall 5 + §Open Q1)."
  - "VIBEMIX_RECALL_ENABLED stays default-OFF — Phase 66 ships engineering-green behind the same flag Phase 65 used; Kaan flips after the §RECALL-EAR discharge."
  - "No changes to STATE.md or ROADMAP.md — the orchestrator owns those writes after the wave completes."

# Metrics
duration: ~40min
completed: 2026-05-22
---

# Phase 66 Plan 02: Visible Copilot Move — Wave 1 GREEN Implementation Summary

**Wave 1 GREEN landed: 4 structural edits to dj_cohost.py + 2 structural edits to coach.py + 1 new HUMAN-UAT scaffold + 1 appended §RECALL-EAR KAAN-ACTION section. All 9 Wave 0 RED tests flipped GREEN; v5.0 byte-identity goldens stayed GREEN (load-bearing regression floor); Phase 65 anti-poisoning + cross-turn + byte-identity goldens stayed GREEN; static anti-feature gate (negative-control stripper + main scan) stayed GREEN. Full suite at 4149 passed / 8 baseline failures (the documented `live-tuning-or-brain` WIP) / zero NEW failures. Engineering ships green behind `VIBEMIX_RECALL_ENABLED=0`; Kaan flips after the §RECALL-EAR ear-pass.**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-05-22
- **Tasks:** 3 (chip allow-list + cooldown wiring / prompt fragments + helper / HUMAN-UAT + §RECALL-EAR)
- **Files modified/created:** 5 (2 source + 1 KAAN-ACTION append + 1 new HUMAN-UAT + 2 test fixups for Wave 0 bugs)

## Task Commits

1. **Task 1: chip allow-list + cooldown wiring** — `0bfc8bd` (feat)
   - `src/vibemix/agent/dj_cohost.py`: 4 structural edits
2. **Task 2: prompt fragments + helper + build_prompt integration** — `b6cc4d2` (feat)
   - `src/vibemix/state/coach.py`: 2 structural edits
   - `tests/state/test_coach.py`: 1 Rule-1 typo fix (out_default → out)
   - `tests/agent/test_dj_cohost_linter.py`: 1 Rule-1 assertion fix (count == 1 → >= 1)
3. **Task 3: HUMAN-UAT scaffold + §RECALL-EAR KAAN-ACTION entry** — `8c1f733` (docs)
   - `.planning/phases/66-visible-copilot-move/66-HUMAN-UAT.md`: NEW (78 lines)
   - `KAAN-ACTION-LEGAL.md`: +115 lines (§RECALL-EAR appended at end of file)

## Edit Line Ranges

### `src/vibemix/agent/dj_cohost.py` (Task 1 commit `0bfc8bd`)

1. **Allow-list edit + recall verb branch** (`_build_citation_strip`):
   - L248: `if source not in ("ev", "mix", "midi", "key", "recall"):` (added `"recall"` as 5th allow-list entry + multi-line comment block citing Phase 65 deferral discharge)
   - L270-283: `elif source == "recall":` branch with fixed `verb = "recall"` (mirrors `key` precedent at L256-268)
2. **Module-scope cooldown constant** at L148-166:
   - L166: `RECALL_CALLBACK_COOLDOWN_S: float = 120.0` + multi-line comment citing CONTEXT.md Area 1 Q3 + the separation-of-concerns from EventDetector._cooldown_ok
3. **Per-agent timestamp field** at L510-536 (DJCoHostAgent.__init__):
   - L536: `self._last_recall_callback_at: float = float("-inf")` co-located with the existing recall-related fields (`_recall`, `_recall_enabled`, `_recall_task`, `_pending_event`)
4. **Cooldown gate in llm_node** at L826-849:
   - After the existing `if self._registry is None: recall_moments = []` (the WR-01 defense) and BEFORE the strict-subset registration loop:
     ```python
     if recall_moments and (
         time.time() - self._last_recall_callback_at
     ) < RECALL_CALLBACK_COOLDOWN_S:
         recall_moments = []
     ```
5. **Cooldown arm sites** (TWO branches):
   - **L1610-1634** (bus-emit success arm — strict `else:` branch of the SessionCohostReaction try/except):
     ```python
     else:
         # Phase 66 (COPILOT-02) — arm the recall-callback cooldown ONLY
         # when the chip reached the audience. ... [comment block]
         try:
             if any(
                 chip.get("event_id", "").startswith("recall:")
                 for chip in strip
             ):
                 self._last_recall_callback_at = time.time()
         except Exception as _e:  # noqa: BLE001
             print(f"\n[recall cooldown arm err] {_e}", file=sys.stderr)
     ```
   - **L1635-1654** (bus-less arm path — `elif self._ipc_bus is None and citation_action in ("emit", "bypass"):` for production agents that skip the IPC bus surface or test contexts that don't wire it):
     ```python
     elif self._ipc_bus is None and citation_action in ("emit", "bypass"):
         try:
             if any(
                 src == "recall" for src, _body in parse_citations(full_text)
             ):
                 self._last_recall_callback_at = time.time()
         except Exception as _e:  # noqa: BLE001
             print(f"\n[recall cooldown arm err] {_e}", file=sys.stderr)
     ```

### `src/vibemix/state/coach.py` (Task 2 commit `b6cc4d2`)

1. **Module-scope fragment template constants + helper function** at L57-247 (after `ACK_ELIGIBLE_EVENTS`, before `class AICoach`):
   - L57-106: ~50-line module comment block (Phase 66 wiring overview, shape precedent, static-gate compatibility note, leading-space load-bearing note)
   - L108-127: `TRANSITION_SHAPE_RECALL_FRAGMENT_TPL` (verbatim from 66-RESEARCH.md §Pattern 1)
   - L130-156: `VOCABULARY_RECALL_FRAGMENT_TPL` (verbatim from 66-RESEARCH.md §Pattern 2)
   - L157-247: `def recall_fragment_for_event(ev, recall_moments) -> str:` with full docstring + falsy-gate + strongest-survivor-only + TRACK_CHANGE-first-wins branch order
2. **build_prompt integration** at L622-633:
   ```python
   task = AICoach.task_for_event(ev)
   recall_frag = recall_fragment_for_event(ev, recall_moments)
   return f"[{evidence} | event={ev.type}] {task}{recall_frag}"
   ```
   (Diet branch at L415-422 stays untouched — never receives recall_moments per the existing `_bp_kwargs` logic at `dj_cohost.py:827`.)

### `KAAN-ACTION-LEGAL.md` (Task 3 commit `8c1f733`)

New `## §RECALL-EAR — Phase 66 Visible Copilot Move Kaan-Ear Discharge` section appended at L3510 (mirroring §SHIP-V4 / §HARMONIC-VETO / §RECALL precedent shape). Contains:
- Status fields (REQ-ID / Owner / Status checkboxes / Mode)
- Engineering close summary (commits, gates, full-suite count, baseline)
- Flag default (`VIBEMIX_RECALL_ENABLED=0`)
- 4-step Discharge runbook (flip flag → run set → 4 ear-tests from 66-HUMAN-UAT.md → persistent flip)
- Two tuning knobs (`RECALL_CALLBACK_COOLDOWN_S`, the two fragment templates)
- Defense in depth (static gate, anti-poisoning gate, cooldown arm semantic, Kaan-ear)
- Sign-off block (5 dated lines + sign-off by Kaan)
- 5 cross-references (66-HUMAN-UAT.md, 66-CONTEXT.md Area 4, 66-RESEARCH.md Pitfall 4, Phase 65 §RECALL, Phase 60 §HARMONIC-VETO)

### `.planning/phases/66-visible-copilot-move/66-HUMAN-UAT.md` (Task 3, NEW)

78-line file mirroring `.planning/phases/54-hype-mode-live/54-HUMAN-UAT.md` shape:
- Front-matter YAML (status / phase / source / started / updated)
- `## Current Test` placeholder line
- `## Tests` with 4 numbered ear-tests:
  1. Transition-shape callback grounds on a real past move (COPILOT-01)
  2. Vocabulary callback echoes prior phrasing in Kaan's voice (COPILOT-02)
  3. Cooldown discipline by ear (COPILOT-02)
  4. Anti-feature absence by ear (COPILOT-03)
- `## Summary` with `total: 4 / passed: 0 / issues: 0 / pending: 4 / skipped: 0 / blocked: 0`
- `## Gaps` section cross-referencing KAAN-ACTION-LEGAL.md §RECALL-EAR

## Cooldown Arm Semantic Confirmation

The cooldown arm landed in the **`else:` branch of the bus-emit try/except** at `dj_cohost.py:1610-1634`. Strict "REACHED the audience" semantic per CONTEXT.md Area 1 Q3 + RESEARCH §Pitfall 2 + §Open Q5:
- Try body completes without raising → `else:` runs → if `strip` has a chip with `event_id.startswith("recall:")`, arm `_last_recall_callback_at = time.time()`.
- Try body raises (bus-emit failure / chip-build failure) → `except:` runs → `else:` does NOT run → cooldown never armed on failure.

The **bus-less arm path** at L1635-1654 covers the case where `_ipc_bus is None` (production agents that skip the IPC bus / test contexts that don't wire it) — the audience hears the recall callback via TTS audio chunks regardless of the bus surface, so the arm fires on `citation_action in {emit, bypass}` (the same gate the bus-emit uses to determine "user heard the text") + a `parse_citations(full_text)` scan for at least one `("recall", _)` atom. Same "REACHED the audience" semantic, different surface.

## Committed Template Text (Wave 0 Substring Choices Match)

The Wave 0 RED tests pin "in the live audio" (transition) and "echo your own past words" (vocabulary) as the structural anchor substrings. Both substrings appear in the deployed templates verbatim:

```
$ grep -F "in the live audio" src/vibemix/state/coach.py
112:    "you've run before. If — AND ONLY IF — that past moment matches what "
113:    "just happened in the live audio, you MAY add ONE short past-tense "

$ grep -F "echo your own past words" src/vibemix/state/coach.py
145:    "up with that past signature, you MAY echo your own past words, "
```

Full literal text of both templates (verbatim from 66-RESEARCH.md §Pattern 1 + §Pattern 2):

### TRANSITION_SHAPE_RECALL_FRAGMENT_TPL

```
 A PAST MOMENT from a prior session is attached in the 'FROM A PAST SESSION' block above — a transition with similar shape you've run before. If — AND ONLY IF — that past moment matches what just happened in the live audio, you MAY add ONE short past-tense callback line referencing it, citing exactly [recall:{record_id}]. Compare what you heard NOW vs. what's in the past signature — the delta is the whole point. Examples of shape: "that blend sat longer than the same one you ran last set", "killed the bass earlier this time around", "cleaner cut than the version you ran before". Hard rules: cite [recall:{record_id}] EXACTLY ONCE (the registry validates it; a fabricated id strips the whole turn); do NOT invent a past moment, paraphrase the past signature, or describe it as live; do NOT recommend a NEXT track or move (no 'try X next time'); do NOT claim a tendency ('you usually do', 'you always') — narrate THIS one compared to THAT one. If the past moment doesn't match, OMIT the callback entirely — your normal reaction is the floor.
```

### VOCABULARY_RECALL_FRAGMENT_TPL

```
 A PAST MOMENT from a prior session is attached in the 'FROM A PAST SESSION' block above — a phrasing or call you made before. If — AND ONLY IF — what you'd naturally say RIGHT NOW lines up with that past signature, you MAY echo your own past words, citing exactly [recall:{record_id}]. The past signature is YOUR voice from before; speak in the same register, not Gemini-paraphrased. Examples: "same call you made on the last drop like this", "your line from the last set still holds". Hard rules: cite [recall:{record_id}] EXACTLY ONCE; do NOT invent a past phrasing; do NOT claim it's a habit ('you always', 'you tend to'); do NOT recommend a next move. If your live reaction wouldn't naturally echo the past, OMIT the callback — a forced echo is the failure mode this phase guards.
```

The leading space at the start of each template is the load-bearing separator from `task` in `build_prompt`'s f-string (no surrounding whitespace).

## Static-Gate Compatibility Note

Both templates contain literal forbidden phrases inside QUOTED EXAMPLES:
- TRANSITION_SHAPE: `"you usually do"`, `"you always"`
- VOCABULARY: `"you always"`, `"you tend to"`

These survive in the rendered template at runtime BUT are stripped by `tests/repo/test_no_recall_antifeatures.py::_strip_comments_and_docstrings` BEFORE the substring scan — STRING tokens are replaced with `""` (verified by the negative-control stripper test `test_strip_comments_and_docstrings_removes_string_content`, which feeds the stripper a docstring + string-literal source each containing `"you tend to"` and asserts both are removed). The static gate stays GREEN.

## Grep-Audit Numbers (Structural Edits Confirmed)

```
$ grep -n "RECALL_CALLBACK_COOLDOWN_S" src/vibemix/agent/dj_cohost.py | wc -l
3   (constant decl + comment ref in __init__ + cooldown gate read)

$ grep -n "_last_recall_callback_at" src/vibemix/agent/dj_cohost.py | wc -l
5   (comment refs in __init__ block + init assignment + cooldown gate read + 2 arm writes)

$ grep -n '("ev", "mix", "midi", "key", "recall")' src/vibemix/agent/dj_cohost.py
1   (the edited allow-list)

$ grep -n 'elif source == "recall":' src/vibemix/agent/dj_cohost.py
1   (the new fixed-verb branch)

$ grep -n "\[recall cooldown arm err\]" src/vibemix/agent/dj_cohost.py
2   (one per arm site — bus-emit-success branch + bus-less elif branch)

$ grep -n "recall_fragment_for_event" src/vibemix/state/coach.py | wc -l
4   (comment ref + def + 2 doc-ref + build_prompt call)

$ grep -n "TRANSITION_SHAPE_RECALL_FRAGMENT_TPL" src/vibemix/state/coach.py | wc -l
2   (constant decl + interpolation site)

$ grep -n "VOCABULARY_RECALL_FRAGMENT_TPL" src/vibemix/state/coach.py | wc -l
2   (constant decl + interpolation site)

$ grep -c "§RECALL-EAR" KAAN-ACTION-LEGAL.md
1   (the appended section header)

$ ls -la .planning/phases/66-visible-copilot-move/66-HUMAN-UAT.md
exists (3.2k bytes)

$ grep -c "result: \[pending\]" .planning/phases/66-visible-copilot-move/66-HUMAN-UAT.md
4   (one per ear-test)
```

## Verification (Full Pass/Fail Counts)

### Targeted phase surface
```
$ source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_linter.py tests/state/test_coach.py tests/repo/test_no_recall_antifeatures.py -q --no-header
68 passed in 1.13s
```
All 9 Wave 0 RED tests flipped GREEN:
- `test_recall_citation_yields_chip_with_registry_timestamp_COPILOT01` ✓
- `test_fabricated_recall_yields_no_chip_COPILOT01` ✓
- `test_cooldown_suppresses_back_to_back_recalls_COPILOT02` ✓
- `test_max_one_recall_per_turn_COPILOT02` ✓
- `test_transition_recall_fragment_appears` ✓
- `test_vocabulary_recall_fragment_appears` ✓
- `test_only_strongest_survivor_record_id_in_fragment` ✓
- `test_transition_wins_track_change_overlap` ✓
- (the 9th, `test_task_for_event_byte_identical_v5_baseline_no_recall`, was trivially GREEN at Wave 0 and STAYED GREEN — the load-bearing regression floor)
- Plus the 2 static-gate tests (`test_strip_comments_and_docstrings_removes_string_content` + `test_no_recall_antifeatures_in_coach_surface_COPILOT03`) STAYED GREEN.

### Phase 65 floor regression check (4-test verify panel)
```
$ pytest tests/agent/test_dj_cohost_linter.py::test_fabricated_recall_strips_turn \
         tests/agent/test_dj_cohost_linter.py::test_fabricated_recall_strips_turn_n_plus_1_with_empty_recall \
         tests/state/test_coach.py::test_evidence_line_silent_state_full_format \
         tests/state/test_coach.py::test_evidence_line_audible_no_recall_byte_identical_v5_baseline -v
4 passed in 1.01s
```
All 4 Phase 65 floor tests GREEN — the anti-poisoning gate, the cross-turn anti-poisoning gate, the silent-state byte-identity golden, and the audible-no-recall v5.0 byte-identity baseline.

### Full suite
```
$ source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q
8 failed, 4149 passed, 26 skipped, 13 warnings in 224.45s (0:03:44)
```
- **Passed:** 4149 (was 4142 at Wave 0 close; +7 newly GREEN this wave)
- **Failed:** 8 (the documented `live-tuning-or-brain` WIP baseline — `test_wire13_anti_slop_disabled_path_passes_none_kwargs`, `test_tag_regex_unchanged_in_this_plan`, `test_state_md_phase_16_line_is_annotated_retired`, `test_readme_feature_matrix_in_sync` × 2, `test_cut_release_accepts_valid_rc_tag_shape`, `test_cut_release_blocks_on_missing_milestone_audit`, `test_smoke_08_main_source_wires_cache_create_with_graceful_degradation`)
- **Skipped:** 26 (existing markers / OS-specific / opt-in surfaces)
- **NEW failures vs baseline:** 0

## Decisions Made

- **Cooldown arm sites: TWO branches, not one.** The plan named only the `else:` branch of the bus-emit try/except (strict "REACHED the audience" via the IPC bus surface). The locked test `test_cooldown_suppresses_back_to_back_recalls_COPILOT02` does NOT wire `_ipc_bus`, so the plan's strict literal placement would mean the cooldown never arms in test contexts (and in any production agent that skips the IPC bus surface). The bus-less branch (`elif self._ipc_bus is None and citation_action in ("emit", "bypass"):`) uses the SAME `citation_action in {emit, bypass}` gate that controls the bus-emit's own "user heard the text" decision, so both branches share the strict "REACHED the audience" semantic — just over different audience surfaces (chip vs audio). A Rule-1 deviation.

- **`_last_recall_callback_at` initial value: `float("-inf")` not `0.0`.** Plan said 0.0 explicitly, but with a mocked `time.time()` returning 100.0 the first call's gap is 100s < 120s → recall_moments wrongly dropped on the FIRST callback. `-inf` is the canonical "never armed" sentinel — `(time.time() - -inf) == inf` which is never `< 120.0`. A Rule-1 deviation.

- **Wave 0 test fixups (Rule-1).** Two test bugs surfaced when the source landed:
  - `tests/state/test_coach.py::test_transition_wins_track_change_overlap` had `out_default` (undefined name) on line 957 — Wave 0 leftover; corrected to `out` (the local variable from line 947).
  - `tests/agent/test_dj_cohost_linter.py::test_max_one_recall_per_turn_COPILOT02` asserted `fragment_portion.count(record_id) == 1`, but the verbatim `TRANSITION_SHAPE_RECALL_FRAGMENT_TPL` has TWO `{record_id}` placeholders (both interpolated with the same id for instruction reinforcement at "citing exactly" + "EXACTLY ONCE"). Loosened to `>= 1` while keeping the no-other-record_ids-leak assertions as the real structural max-1-per-turn cap.

- **Diet branch untouched.** `AICoach.build_prompt`'s diet branch at L415-422 receives no `recall_moments` (per the existing `_bp_kwargs` logic at `dj_cohost.py:827`) so it never invokes the new helper; the diet path stays byte-identical to the v5.0 baseline. This is the structural guarantee — no special-casing needed.

- **No edits to `src/vibemix/prompts/matrix.py` or `src/vibemix/ui_bus/messages.py`.** Phase 65 already added `[recall:<record_id>]` to `CITATION_GRAMMAR_BLOCK`; Gemini already knows the grammar. `CitationChipPayload` is wire-format-compatible with the new `recall` chip out of the box (no payload-shape changes). The new chip rides the existing `ipc.session.cohost-reaction` envelope — one-socket invariant preserved.

- **VIBEMIX_RECALL_ENABLED stays default-OFF.** Phase 66 ships the engineering green behind the Phase 65 flag; Kaan flips after the §RECALL-EAR ear-pass on his real corpus. Same KAAN-ACTION carry-forward pattern as Phase 60 §HARMONIC-VETO and Phase 65 §RECALL.

## Deviations from Plan

Three Rule-1 fixes (deviations under the deviation_rules priority — Rule 1 covers bug fixes in code or tests when the plan's literal would prevent the intended contract from passing):

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_last_recall_callback_at` initializer changed from `0.0` to `float("-inf")`**
- **Found during:** Task 1 verification — `test_cooldown_suppresses_back_to_back_recalls_COPILOT02` failed because turn N's mocked `time.time()=100.0` produced gap=100 < 120 → recall_moments wrongly suppressed on first call.
- **Issue:** Plan said `self._last_recall_callback_at: float = 0.0` but with mocked small wall-clock values this trips the cooldown on first call.
- **Fix:** Use `float("-inf")` as the never-armed sentinel. `(time.time() - -inf) == inf` always passes the `< 120.0` gate.
- **Files modified:** `src/vibemix/agent/dj_cohost.py:536`
- **Commit:** `0bfc8bd`

**2. [Rule 1 - Bug] Added bus-less arm path for cooldown when `_ipc_bus is None`**
- **Found during:** Task 1 verification — same test still failed because the plan's `else:` placement only runs when `_ipc_bus is not None`, but the test constructs the agent WITHOUT `ipc_bus`.
- **Issue:** Plan said the arm sits in the `else:` of the bus-emit try/except. That gate is inside `if self._ipc_bus is not None`, so the cooldown never arms when no IPC bus is wired.
- **Fix:** Added `elif self._ipc_bus is None and citation_action in ("emit", "bypass"):` branch that scans `parse_citations(full_text)` for a recall atom and arms the cooldown. Same "REACHED the audience" semantic, different audience surface (audio vs chip).
- **Files modified:** `src/vibemix/agent/dj_cohost.py:1635-1654`
- **Commit:** `0bfc8bd`

**3. [Rule 1 - Bug] Fixed two Wave 0 test bugs**
- **Found during:** Task 2 verification.
- **Issue (a):** `tests/state/test_coach.py:957` referenced undefined name `out_default` (Wave 0 leftover; intended target was the local `out` variable).
- **Issue (b):** `tests/agent/test_dj_cohost_linter.py:941` asserted `fragment_portion.count(record_a.record_id) == 1`, but the verbatim `TRANSITION_SHAPE_RECALL_FRAGMENT_TPL` has TWO `{record_id}` placeholders (instruction reinforcement). The repeat-count is a property of the template, not of the structural cap.
- **Fix (a):** Renamed `out_default` → `out`.
- **Fix (b):** Loosened assertion from `== 1` to `>= 1`; kept the no-other-record_ids-leak assertions (record_b / record_c absence) as the real structural max-1-per-turn cap.
- **Files modified:** `tests/state/test_coach.py:957`, `tests/agent/test_dj_cohost_linter.py:939-944`
- **Commit:** `b6cc4d2`

## Authentication Gates

None. Phase 66 is a pure code-edit + doc phase with zero external service interaction.

## Known Stubs

None. The recall chip + the two prompt fragments wire to real data (the Phase 65 `MemoryRecall` service + the existing `EvidenceRegistry` + the existing `CitationLinter`). The visibility is gated by `VIBEMIX_RECALL_ENABLED` which defaults OFF — that is the intentional pattern (Kaan-ear discharge), NOT a stub.

## Threat Flags

None. The chip + fragments do not introduce new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. The existing `<threat_model>` in 66-02-PLAN.md covers the surface; no NEW threats discovered during implementation.

## Next Phase Readiness

- **Phase 66 closes** at engineering-green per `gsd-autonomous fully` — the orchestrator will advance STATE.md + ROADMAP.md after the wave completes.
- **§RECALL-EAR discharge** (KAAN-ACTION-LEGAL.md) is the open carry-forward; Kaan flips `VIBEMIX_RECALL_ENABLED=1` and runs the 4 ear-tests in 66-HUMAN-UAT.md on his real corpus.
- **v6.1+ chip differentiation** (optional, deferred) — distinct CDJ-Whisper visual treatment for the recall chip vs ev/mix/midi/key (currently the renderer treats all chip sources identically per CONTEXT.md Area 3 Q4 lock).
- **v6.1+ tuning** — `RECALL_CALLBACK_COOLDOWN_S` + fragment templates are one-line knobs; Kaan can iterate without a code review.

## Self-Check: PASSED

- `src/vibemix/agent/dj_cohost.py` — modified, contains `RECALL_CALLBACK_COOLDOWN_S` constant + `_last_recall_callback_at` field + cooldown gate + 2 arm sites + recall allow-list entry + recall verb branch.
- `src/vibemix/state/coach.py` — modified, contains `TRANSITION_SHAPE_RECALL_FRAGMENT_TPL` + `VOCABULARY_RECALL_FRAGMENT_TPL` + `recall_fragment_for_event` helper + `build_prompt` integration.
- `KAAN-ACTION-LEGAL.md` — modified, contains `## §RECALL-EAR — Phase 66 Visible Copilot Move Kaan-Ear Discharge` section at L3510.
- `.planning/phases/66-visible-copilot-move/66-HUMAN-UAT.md` — created, 4 ear-tests + Summary + Gaps section.
- Commit `0bfc8bd` — FOUND in `git log` (Task 1).
- Commit `b6cc4d2` — FOUND in `git log` (Task 2).
- Commit `8c1f733` — FOUND in `git log` (Task 3).

---

*Phase: 66-visible-copilot-move*
*Completed: 2026-05-22*
