---
phase: 66-visible-copilot-move
reviewed: 2026-05-22T17:00:00Z
depth: standard
iteration: 2
files_reviewed: 6
files_reviewed_list:
  - src/vibemix/agent/dj_cohost.py
  - src/vibemix/state/coach.py
  - tests/agent/test_citation_strip_emit.py
  - tests/agent/test_dj_cohost_linter.py
  - tests/state/test_coach.py
  - tests/repo/test_no_recall_antifeatures.py
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
iter_1_fixes_confirmed: 4
v5_byte_identity: green
phase_65_anti_poisoning: green
---

# Phase 66: Code Review Report — Iteration 2

**Reviewed:** 2026-05-22T17:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Iteration:** 2 (re-review of iteration 1 fixes)
**Status:** issues_found (1 WARNING, 2 INFO; no BLOCKERs)

## Summary

Iteration 2 of Phase 66 review. The 4 iteration-1 fixes (CR-01 BLOCKER + WR-01/02/04) are confirmed correctly applied. The bus-less cooldown arm path now mirrors the bus path's structural lens via `_build_citation_strip`, closing the BLOCKER cleanly. Forbidden-phrase tuple expansion (WR-01), test rename (WR-02), and event-fired set_seconds capture (WR-04) all check out.

Full test suite for the Phase 65/66 surface is GREEN (110/110: tests/agent/test_dj_cohost_linter.py + test_citation_strip_emit.py + tests/repo/test_no_recall_antifeatures.py + tests/state/test_coach.py + tests/memory/). v5.0 byte-identity goldens still green. The 4 broader-suite failures (`test_readme_feature_matrix_sync.py`, `test_cut_release_invokes_bravoh_server.py`, `test_gate_42_hybrid_in_force.py`) are PRE-EXISTING repo-meta failures unrelated to this phase's surface.

Iteration 1 fix verifications (all CONFIRMED):

1. **CR-01 (BLOCKER) — Bus-less arm structural filter** — `dj_cohost.py:1665-1709`. The bus-less arm path now (a) guards on `not self._recall_enabled or self._registry is None` and skips arming if either fails, (b) calls `_build_citation_strip(reaction_text=full_text, registry=self._registry)` instead of raw `parse_citations()`, and (c) arms only when a chip with `event_id.startswith("recall:")` is in the strip. A fabricated `[recall:<unregistered>]` riding through bypass cannot register a chip (registry lookup returns no timestamps → `continue` in the strip builder), so the cooldown does NOT arm — symmetric with the bus path. Verified by re-running `test_cooldown_suppresses_back_to_back_recalls_COPILOT02` (GREEN) + tracing the fabricated-bypass path manually.

2. **WR-01 — Forbidden-phrase tuple expansion** — `tests/repo/test_no_recall_antifeatures.py:130-145`. Nine new entries: "your typical", "you've been", "i'd recommend", "play next", "you should play next", "consider playing", "track to play next", "your usual move", "your habit". Re-grep against `src/vibemix/state/coach.py` + `src/vibemix/prompts/matrix.py` returns ZERO hits for all 9 phrases — the gate stays VACUOUS-GREEN at land. Static gate test green.

3. **WR-02 — Static gate test name rename** — `tests/repo/test_no_recall_antifeatures.py:235`. Renamed to `test_no_recall_antifeatures_in_coach_surface_after_string_and_comment_scrub_COPILOT03`. The module docstring already explicitly documents the divergence-from-analog stripper semantics (lines 24-71); the renamed test reinforces this with the explicit mechanical claim ("after string and comment scrub") in the function name itself. Test still collected and green.

4. **WR-04 — `set_seconds` capture at event-fired time** — `dj_cohost.py:763-775`. `ev_set_seconds` is captured at the TOP of `llm_node` (before the LLM dispatch + stream + lint + bus emit, ~2-3s of drift in the prior code path), then threaded through all three `_record_said(...)` call sites at lines 1473, 1516, 1569 as `set_s_at_event=ev_set_seconds`. The `_record_said` signature (lines 579-603) was extended to accept the optional kwarg with a fallback to live `self._state.set_seconds` for legacy callers that don't yet thread the value. The capture is via `getattr(ev.state, "set_seconds", 0.0)` — `set_seconds` is a `@property` on `MusicState` (lines 147-148 of `music_state.py`) that returns `time.time() - self.set_start_at` LIVE, so the value is computed at the top-of-llm_node call site as intended.

No NEW BLOCKER issues introduced. The remaining findings below are non-blocking quality concerns surfaced by the iteration 2 audit.

## Warnings

### WR-05: No regression test for the WR-04 `set_s_at_event` fix

**File:** `src/vibemix/agent/dj_cohost.py:579-603, 763-775, 1473, 1516, 1569` / `tests/agent/` (missing)
**Issue:** WR-04 added the `set_s_at_event` kwarg + capture-at-top-of-llm_node behavior, but no regression test pins the contract. A future refactor that reverts the threading (drops `set_s_at_event=...` at any of the three call sites, or removes the capture at the top of llm_node) would silently regress to the multi-second-drift behavior the fix exists to prevent. The fallback path (`if set_s_at_event is not None: ... else: self._state.set_seconds`) means the legacy behavior re-engages with no test signal — _the fallback IS the regression footprint_.

The other three iter-1 fixes all have dedicated tests:
- CR-01 → bus-less arm symmetry pinned by the existing cooldown test (would fail under a fabricated-recall-arms-cooldown regression)
- WR-01 → static-gate test catches any of the 9 new phrases landing in source
- WR-02 → test name itself is the contract

WR-04 has none. Recommend adding a test that drives `llm_node` with `time.time` patched to advance during the stream, then asserts the `[M:SS]` stamp in `agent._ai_text_history[0]` reflects the event-fired-time set_seconds, not the post-emit time.

**Fix (sketch):**

```python
def test_record_said_uses_event_fired_set_seconds(mocker, tmp_path):
    """WR-04 regression — [M:SS] stamp reflects EVENT-fired set_seconds,
    not POST-emit set_seconds. A future refactor that drops set_s_at_event
    threading would multi-second-drift the timestamp."""
    agent, gen, recorder, state = _build_agent_legacy(mocker, tmp_path)
    state.set_start_at = 1000.0  # set started at t=1000
    # time at llm_node entry = 1060.0 (60s into set); time at _record_said
    # call would be 1063.5 (3.5s of stream/lint/emit drift).
    times = iter([1060.0, 1060.0, 1060.0, 1063.5, 1063.5])
    mocker.patch(
        "vibemix.agent.dj_cohost.time.time",
        side_effect=lambda: next(times, 1063.5),
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"X")
    mocker.patch.object(AICoach, "build_prompt", return_value="P")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["clean reply"])
    )
    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive(agent)
    # 60s = 1:00; if drift bug returns, stamp would be 1:03 instead.
    assert agent._ai_text_history[0].startswith("[1:00]"), (
        f"expected [1:00] event-fired stamp; got {agent._ai_text_history[0]!r}"
    )
```

## Info

### IN-01: One redundant entry in expanded FORBIDDEN_RECALL_PHRASES

**File:** `tests/repo/test_no_recall_antifeatures.py:139`
**Issue:** `"you should play next"` is a strict superset of `"you should play"` (already in the tuple at line 127). The gate is substring-based, so `"you should play next"` would already trip via the shorter form. The entry adds no coverage. Not a correctness bug — the gate is union-of-substrings — but it's dead expansion that future maintainers may copy-paste-extend with similar redundant pairs.

**Fix:** Either drop `"you should play next"` from the tuple, or keep it with a brief comment ("kept for explicit-name reads even though `you should play` already catches it"). Both are acceptable.

### IN-02: Forbidden-phrase coverage gaps still present after WR-01 expansion

**File:** `tests/repo/test_no_recall_antifeatures.py:118-146`
**Issue:** WR-01 closed 9 paraphrase gaps, but predictive-personalization classes are still uncovered. Examples that today would slip through the substring gate:

- `"you'll probably"` / `"you'll want to"` — predictive second-person ("you'll probably reach for the high pass" is a tendency claim with future-tense framing)
- `"that's your style"` / `"that's typical of you"` — third-person tendency
- `"your move is to"` — habit reframe
- `"based on your tendency"` — explicit version of `"based on your past"` already in the tuple

Not a correctness bug — pre-grep against current source confirms ZERO of these appear today. The gate is vacuous-green per the documented contract. But the WR-01 fix-pass framed itself as "expand … with synonym gaps" and these are obvious paraphrase classes the executor could have folded into the same fix wave.

**Fix:** Either (a) accept current coverage as sufficient and document iter-2's decision in the module docstring's "Pre-grep evidence" section, or (b) extend the tuple with the missing predictive-personalization class in a follow-up. Acceptable to defer to v6.1.

---

## Verification: v5.0 byte-identity goldens

Re-ran the three v5.0 byte-identity anchor tests:

- `tests/state/test_coach.py::test_evidence_line_audible_no_recall_byte_identical_v5_baseline` — PASSED
- `tests/state/test_coach.py::test_task_for_event_byte_identical_v5_baseline_no_recall` — PASSED
- `tests/state/test_coach.py::test_evidence_line_silent_state_full_format` — PASSED

The cold-path byte-identity floor (recall_moments=None == [] == no-kwarg, across all 9 event types: KAAN_SPOKE / MANUAL / TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE / HEARTBEAT / KEY_CLASH / TRANSITION_OPPORTUNITY) is intact.

## Verification: Phase 65 anti-poisoning gates

Re-ran the Phase 65 anti-poisoning headline tests:

- `tests/agent/test_dj_cohost_linter.py::test_fabricated_recall_strips_turn` — PASSED
- `tests/agent/test_dj_cohost_linter.py::test_fabricated_recall_strips_turn_n_plus_1_with_empty_recall` — PASSED (cross-turn rescope)
- `tests/agent/test_dj_cohost_linter.py::test_invalid_response_strips_silently` — PASSED
- `tests/agent/test_dj_cohost_linter.py::test_no_citations_response_strips` — PASSED

The Phase 65 anti-poisoning gate carries forward intact. The iter-2 fix to the bus-less arm path does not weaken the linter's existence-only branch — fabricated recall ids still strip the whole turn.

## Verification: Phase 66 cooldown contract tests

- `tests/agent/test_dj_cohost_linter.py::test_cooldown_suppresses_back_to_back_recalls_COPILOT02` — PASSED
- `tests/agent/test_dj_cohost_linter.py::test_max_one_recall_per_turn_COPILOT02` — PASSED

Both COPILOT-02 contract tests green. Cooldown "REACHED the audience" semantic holds across bus and bus-less paths after the CR-01 fix.

## Verification: Full test sweep

- Full suite (tests/agent/ + tests/state/ + tests/repo/ + tests/memory/): 1386 passed, 4 failed, 1 skipped.
- The 4 failures (`test_readme_feature_matrix_sync.py::*`, `test_cut_release_invokes_bravoh_server.py::test_tag_regex_unchanged_in_this_plan`, `test_gate_42_hybrid_in_force.py::test_state_md_phase_16_line_is_annotated_retired`) are PRE-EXISTING repo-meta failures unrelated to Phase 66's surface — confirmed by spot-check of failure messages (README sync drift, release tag regex, STATE.md phase-16 annotation). None touch the recall / coach / linter / prompt surface.

## Summary table

| Iter-1 finding | Fix commit | Iter-2 status | Outstanding |
|----------------|------------|---------------|-------------|
| CR-01 (BLOCKER) — Bus-less arm fabricated-id leak | `5f84f4d` | CONFIRMED FIXED — bus-less arm now mirrors bus-path structural lens via `_build_citation_strip` + flag-OFF guard | — |
| WR-01 — Forbidden phrase synonym gaps | `34ef104` | CONFIRMED FIXED — 9 new phrases, pre-grep ZERO hits, gate VACUOUS-GREEN | IN-01 (1 redundant), IN-02 (gaps remain) |
| WR-02 — Static gate test name | `8b385ce` | CONFIRMED FIXED — renamed to `..._after_string_and_comment_scrub_COPILOT03` | — |
| WR-04 — set_seconds captured at event-fired time | `5f27dcd` | CONFIRMED FIXED — capture-at-top-of-llm_node + threaded to 3 `_record_said` call sites | **WR-05 — no regression test** |

---

_Reviewed: 2026-05-22T17:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Iteration: 2_
