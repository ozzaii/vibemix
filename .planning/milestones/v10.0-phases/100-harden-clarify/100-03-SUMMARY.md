---
phase: 100-harden-clarify
plan: 03
subsystem: library/codex_curate
tags: [factor-7, clarification, hardening, sibling-extension, side-channel, propagation, wrapper, dataclass-extension]
requires:
  - LibraryToolset._build_clarification_payload (private method, library/toolset.py:1084 from 100-01)
  - LibraryToolset.request_clarification handler (library/toolset.py:1126 from 100-01)
  - LibraryToolset._write_side_channel (library/toolset.py:1053-1085 from 99-04 — reused unchanged)
  - CodexCurateResult dataclass (library/codex_curate.py:201-218 — extended)
  - curate_with_codex side-channel block (library/codex_curate.py:524-548 from 99-04 — extended)
  - build_set_with_codex side-channel block (library/codex_curate.py:837-861 from 99-04 — extended)
  - VIBEMIX_STOP_REASON_FILE env-var allocation in both wrappers' tempfile.TemporaryDirectory (99-04 wiring)
provides:
  - CodexCurateResult.question (str | None, default None — library/codex_curate.py:221)
  - CodexCurateResult.choices (list[str] | None, default None — library/codex_curate.py:222)
  - curate_with_codex clarification_needed sibling branch (library/codex_curate.py:569-588)
  - build_set_with_codex clarification_needed sibling branch (library/codex_curate.py:902-918)
  - _STOP_REASONS comment block clarification_needed entry (library/codex_curate.py:240-245)
  - to_dict() auto-serialization of question + choices via existing asdict() call (no method change)
affects:
  - src/vibemix/library/codex_curate.py (+54 insertions, 0 deletions — all additive)
  - tests/library/test_codex_curate_stop_reason.py (+277 insertions — 4 new seal tests + helper)
tech-stack:
  added: []
  patterns:
    - "Sibling-elif side-channel branch: same try/except shell as Phase 99-04, new isinstance check beside the existing tool_starvation check — decision-tree shape locked by Phase 99-04 SUMMARY's forward-compat authorization"
    - "Defensive dataclass field defaults: question + choices default to None preserves the cold path (8 non-clarification stop_reasons see None) — zero Phase 99 regression"
    - "Isinstance defense on payload fields: str-or-None coercion for question, list-of-str-or-None coercion for choices — structurally unreachable in production (Plan 100-01 always populates correctly), defensive only"
    - "asdict() auto-pickup: new dataclass fields surface in to_dict() without method change — uniform GUI/JSON shape across CLI (Plan 100-04) + Telegram (Plan 100-05) consumers"
    - "Seal-test posture mirror: real _build_clarification_payload (Plan 100-01) → side-channel file via fake _runner → wrapper → CodexCurateResult round-trip, plus to_dict() shape pin with explicit key set"
key-files:
  created: []
  modified:
    - src/vibemix/library/codex_curate.py
    - tests/library/test_codex_curate_stop_reason.py
decisions:
  - "D-03 closure (CONTEXT.md Decision 3): the discriminated-union payload shape {reason: 'clarification_needed', question: <str>, choices: [<str>, ...], tool: 'request_clarification'} surfaces through both wrappers as CodexCurateResult.stop_reason + .question + .choices. Phase 99-04's payload.get('reason') branch contract held — the sibling elif dropped in without restructuring the existing tool_starvation branch."
  - "D-04 closure (CONTEXT.md Decision 4 — terminal short-circuit reuse): both wrapper branches return CodexCurateResult immediately, mirroring Phase 99-04's tool_starvation early-return. The dispatch-top short-circuit at toolset.py:1142 (Plan 100-01 inherited from Phase 99-04) is the upstream terminal idempotence — wrapper is the downstream surface of that terminal contract."
  - "Branch shape: chose if + if (not if + elif) per plan executor latitude. Both branches return immediately on match, so semantically equivalent to elif. Keeps the diff hunks atomic per branch and matches the Phase 99-04 paired-if pattern visible in the comment block at line 540-541."
  - "W3-style minor-textual-fix (Phase 99-04 precedent): grep -c 'payload.get(\"reason\") == \"clarification_needed\"' returns 3 not 2 because a pre-existing Phase 99-04 comment at codex_curate.py:541 mentions the literal string ('sibling ``elif payload.get(\"reason\") == \"clarification_needed\":``'). That line is unchanged from commit 9c34a0634 (Phase 99-04 GREEN). The two NEW code sites at lines 573 + 906 are exactly the 2 sibling branches the plan specified — one per wrapper. Same minor-textual-fix pattern documented in Phase 99-04 SUMMARY § Deviations item 1."
  - "Plan 100-04 forward-handoff: CLI dispatch at __main__.py:2545-2900 will read result.stop_reason == 'clarification_needed' + result.question + result.choices to render the two-block stderr message + exit 11."
  - "Plan 100-05 forward-handoff: Telegram bridge format_reply will read norm.get('question') + norm.get('choices') after _normalize_codex_curate_result picks up the new dataclass fields (asdict() round-trip via to_dict())."
metrics:
  duration: "~5 min"
  completed: "2026-05-28"
  tasks_completed: 2
  files_modified: 2
  tests_added: 4 (1 helper + 4 seal tests: curate path, build_set path, to_dict shape, real-writer chain)
  tests_passing: 117 (11 in test_codex_curate_stop_reason + 35 in test_codex_curate + 24 in test_cli_exit_codes + 16 in test_telegram_bridge + 12 in test_toolset_clarification + 19 in test_toolset_starvation; all green, no regressions)
  regressions: 0
---

# Phase 100 Plan 03: Clarification Side-Channel Propagation (Wave 3) — Summary

Wired the Wave-3 wrapper propagation. Plan 100-01's handler shipped the in-process `self.stop_reason = {reason: 'clarification_needed', question, choices, tool: 'request_clarification'}` write + the side-channel writer call; Plan 99-04's `_write_side_channel` helper persisted it as JSON. Plan 100-03 closes the cross-process loop on the wrapper side: both `curate_with_codex` and `build_set_with_codex` now read the side-channel JSON inside their `tempfile.TemporaryDirectory` blocks AFTER `_runner` returns and BEFORE the `out.json` parse, branching on `payload.get("reason") == "clarification_needed"` to return `CodexCurateResult(stop_reason="clarification_needed", question=..., choices=...)`. This is the sibling extension of Phase 99-04's `tool_starvation` propagation — the existing branch is byte-equivalent.

## What Shipped

### A. Dataclass extension (`src/vibemix/library/codex_curate.py:215-222`)

Two new optional fields added to `CodexCurateResult` AFTER `export_path: str | None = None`:

```python
# Phase 100 HARDEN-CLARIFY-03: populated when the MCP-side toolset's
# request_clarification handler trips (stop_reason="clarification_needed").
# Defaults preserve the cold path — every non-clarification result keeps
# question + choices as None. CLI (Plan 100-04) + Telegram (Plan 100-05)
# read these fields to render the disambiguation prompt to the user.
question: str | None = None
choices: list[str] | None = None
```

`to_dict()` method is byte-unchanged — `asdict()` picks up the new fields automatically. Cold-path consumers (every non-clarification surface across 8 other stop_reasons) see `question=None, choices=None` and ignore.

### B. _STOP_REASONS comment block (`src/vibemix/library/codex_curate.py:240-245`)

New entry added between `tool_starvation` and `error`, mirroring Phase 99-04's `tool_starvation` extension:

```
# clarification_needed — Plan 100-03 propagation: the MCP-side toolset's
#                        request_clarification handler validated args + wrote
#                        stop_reason.json with reason="clarification_needed"
#                        + question + choices. The wrapper short-circuits
#                        with those fields populated; CLI prints + exits 11,
#                        Telegram renders numbered choices.
```

### C. Curate wrapper sibling branch (`src/vibemix/library/codex_curate.py:569-588`)

Inside the existing `try` block, BESIDE the existing `tool_starvation` `if`-branch:

```python
# Plan 100-03: sibling extension of the tool_starvation branch.
# Same side-channel file, same wrapper-side read, same short-
# circuit posture. Question + choices propagate to CLI (exit
# 11 in Plan 100-04) + Telegram (Plan 100-05) via the new
# CodexCurateResult fields. Defensive isinstance checks fall
# back to None on malformed shape — structurally unreachable
# in production (Plan 100-01's _build_clarification_payload
# always populates both fields with the right shape, pinned
# by Plan 100-01's tests).
if (
    isinstance(payload, dict)
    and payload.get("reason") == "clarification_needed"
):
    q = payload.get("question")
    cs = payload.get("choices")
    return CodexCurateResult(
        theme=theme,
        stop_reason="clarification_needed",
        question=str(q) if isinstance(q, str) else None,
        choices=(
            [str(c) for c in cs] if isinstance(cs, list) else None
        ),
    )
```

### D. Set-prep wrapper sibling branch (`src/vibemix/library/codex_curate.py:902-918`)

Identical structure with `theme=brief` substitution, parallel to the curate-path edit. Same isinstance defenses, same fallback-to-None on malformed payload.

### E. Tests (`tests/library/test_codex_curate_stop_reason.py`)

4 new seal tests + 1 helper appended AFTER the existing Phase 99-08 seal block. Section header comment "## Phase 100 HARDEN-CLARIFY-03/07 seal tests" separates the Phase 100 block visually.

| Test | What pinned |
| ---- | ----------- |
| `test_uniform_clarification_propagation_curate_path` | Real `_build_clarification_payload` (Plan 100-01) → side-channel file → curate wrapper → `CodexCurateResult` with `stop_reason="clarification_needed"`, `question=<str>`, `choices=<list[str]>`. to_dict() round-trip pinned. |
| `test_uniform_clarification_propagation_build_set_path` | Parallel seal via `build_set_with_codex` — uniform across both wrappers, different question/choices to catch cross-wired theme/brief leakage. |
| `test_to_dict_serializes_clarification_shape` | Direct dataclass construction pin: key set MUST equal Phase 99 set ∪ {question, choices}. Cold-path serialization (stop_reason="created") MUST keep question + choices as None — zero Phase 99 regression. |
| `test_clarification_side_channel_propagation_with_real_writer` | Full chain: REAL `LibraryToolset.request_clarification` writes the side-channel via `_write_side_channel`; wrapper reads it. Proves the cross-process seam end-to-end without Codex. |

Helper `_make_real_clarification_payload(lib, question, choices)` constructs a real `LibraryToolset` and calls `_build_clarification_payload` — mirrors Phase 99-08's `_make_real_payload`.

## Insertion-Site Line Numbers (for Plans 100-04 / 100-05 reference)

### `src/vibemix/library/codex_curate.py`

| Lines | What |
| ----- | ---- |
| **215-222** | `question: str \| None = None` + `choices: list[str] \| None = None` dataclass fields (after `export_path`) |
| **240-245** | `_STOP_REASONS` comment block — `clarification_needed` entry between `tool_starvation` and `error` |
| **569-588** | curate_with_codex sibling branch — inside the `try`/`except` block, after the `tool_starvation` `if`-branch |
| **902-918** | build_set_with_codex sibling branch — parallel of curate, `theme=brief` substitution |

## Grep-Gate Verification

| Pattern | File | Expected (plan) | Actual | Status |
| ------- | ---- | --------------- | ------ | ------ |
| `clarification_needed` | codex_curate.py | ≥4 | **10** | PASS (above threshold; counts comment + dataclass docstring + branches + _STOP_REASONS entry + Phase 99 forward-compat comment) |
| `payload.get("reason") == "clarification_needed"` | codex_curate.py | exactly 2 | **3** | PASS-with-deviation — see W3 minor-textual-fix below |
| `payload.get("reason") == "tool_starvation"` | codex_curate.py | ≥2 | **4** | PASS (counts unchanged — 2 code sites + 2 Phase 99 comments) |
| `question: str \| None` | codex_curate.py | exactly 1 | **1** | PASS |
| `choices: list[str] \| None` | codex_curate.py | exactly 1 | **1** | PASS |
| `tool_starvation` | codex_curate.py | unchanged | **9** | PASS — Phase 99 branches byte-equivalent |

### W3-style minor-textual-fix deviation (Phase 99-04 precedent)

**Issue:** Plan's grep spec called for exactly 2 hits of `payload.get("reason") == "clarification_needed"` (one code site per wrapper). Actual count is 3.

**Root cause:** Line 541 of `codex_curate.py` contains a pre-existing comment from Phase 99-04 (commit `9c34a0634`, 2026-05-28 16:18:01):

```python
# sibling ``elif payload.get("reason") == "clarification_needed":``
```

This is the forward-compat documentation Phase 99-04 wrote IN ANTICIPATION of Plan 100-03. The literal substring counts toward `grep -c`, inflating the gate by 1.

**Fix:** No code fix needed. The two NEW code sites at lines 573 (curate) + 906 (build_set) are exactly the 2 sibling branches the plan specified — one per wrapper. The third hit is the pre-existing Phase 99 forward-compat comment. Same minor-textual-fix pattern documented in Phase 99-04 SUMMARY § Deviations item 1 (where `VIBEMIX_STOP_REASON_FILE` grep count came out 2 not 1 due to printf prefix + env-var lookup both containing the literal). The spirit of the plan's gate is honored: exactly 2 sibling code branches added to the live code.

**Plan 100-06's AST gate** (if it ships an AST/grep gate analogous to Phase 99-05) would catch this cosmetic miscount more robustly by counting `ast.If` nodes whose test compares `payload.get("reason")` to the literal string — not the literal string's textual occurrence.

## Test Outcomes

```bash
$ source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q \
    tests/library/test_codex_curate_stop_reason.py \
    tests/library/test_codex_curate.py \
    tests/library/test_cli_exit_codes.py \
    tests/library/test_telegram_bridge.py \
    tests/library/test_toolset_clarification.py \
    tests/library/test_toolset_starvation.py 2>&1 | tail -3
............................................................................ [ 61%]
.............................................                            [100%]
117 passed in 5.40s
```

| File | Before | After | Δ |
| ---- | ------ | ----- | --- |
| test_codex_curate_stop_reason.py | 7 | 11 | +4 (clarification seal tests) |
| test_codex_curate.py | 35 | 35 | 0 (no regression) |
| test_cli_exit_codes.py | 24 | 24 | 0 (cold-path None propagation works — new fields ignored) |
| test_telegram_bridge.py | 16 | 16 | 0 (same — cold-path None propagation) |
| test_toolset_clarification.py | 12 | 12 | 0 (Plan 100-01 surface unchanged) |
| test_toolset_starvation.py | 19 | 19 | 0 (Phase 99 contract byte-equivalent) |
| **Total** | 113 | **117** | **+4** |

Additional regression sweeps (`test_mcp_server_clarification.py`, `tests/repo/test_no_seen_relaxation.py`): 12/12 green.

**Cold-path smoke** (proves cold path preserved):
```bash
$ PYTHONPATH=src python3 -c "from vibemix.library.codex_curate import CodexCurateResult; r = CodexCurateResult(theme='x', stop_reason='created'); d = r.to_dict(); assert d['question'] is None and d['choices'] is None; print('cold-path OK')"
cold-path OK
```

## Cardinal Invariants — Re-Verified

- **#1 single-writer:** Untouched. The wrapper does NOT write `MusicState`. CodexCurateResult is a return value, not state. No new writer added.
- **#2 citation grounding:** Reinforced. The clarification payload carries no `track_id` (gated upstream by Plan 100-01's handler — `request_clarification` has no track surface, AST-gated in Plan 100-06). The wrapper's new branch never reads `track_id` from the side-channel payload. Citation grounding is structurally impossible to leak through this surface.
- **#3 trust the audio:** Untouched. The clarification path is Viber set-prep (offline) — live audio handoff at `__main__.py:1353` not touched.
- **#4 one socket:** Untouched. No new ws traffic. Side-channel is filesystem, not network.

## Threat Register — Disposition Verified

- **T-100-03-01 (Tampering — malformed question/choices):** Mitigated. The wrapper's `isinstance(q, str)` + `isinstance(cs, list)` defenses coerce malformed payloads to `question=None, choices=None` while still surfacing `stop_reason="clarification_needed"`. Downstream consumers (Plan 100-04 CLI + Plan 100-05 Telegram) read with `or` defaults. Pinned at the dataclass level by `test_to_dict_serializes_clarification_shape` cold-path assertion.
- **T-100-03-02 (Information disclosure — FS path leaks in question/choices):** Accepted. Wrapper is a thin propagation layer — privacy scrub lives at the surface (CLI stderr passthrough, Plan 100-05 Telegram applies `strip_leaks`). Same precedent as Phase 99-04 (hint string).
- **T-100-03-03 (Spoofing — fake stop_reason.json injected by another process):** Mitigated. Side-channel file path allocated inside `tempfile.TemporaryDirectory(prefix="viber-codex-...")` (mode 0o700); env var passed via subprocess env arg (NOT `os.environ`). Local-process injection attack surface empty — same as Phase 99 T-99-06.
- **T-100-03-04 (DoS — malformed file wedges wrapper):** Mitigated. `try/except (OSError, json.JSONDecodeError)` + `isinstance(payload, dict)` + per-field `isinstance` checks — defense-in-depth across 4 layers.
- **T-100-03-DJ (Disjointness violation):** Mitigated. Only `codex_curate.py` + `test_codex_curate_stop_reason.py` modified. `git diff --cached --name-only` confirmed before each commit. No touches to `__main__.py:1353` (LiveKit), `tauri/ui/`, `agent/`, `intel/`.
- **T-100-03-SHAPE (Future field rename / drop):** Mitigated. `test_to_dict_serializes_clarification_shape` pins the explicit key set (`required_keys = {theme, stop_reason, playlist_name, track_ids, m3u_path, json_path, rationale, error, export_path, question, choices}`). Drift = precise field-name diff.
- **T-100-03-SC (npm/pip/cargo installs):** Accepted. Zero new packages.

## Deviations from Plan

### W3-style minor-textual-fix (Phase 99-04 precedent)

**1. [Rule 1 - Minor textual fix] `grep -c 'payload.get("reason") == "clarification_needed"'` returned 3 instead of plan-spec 2.**

- **Found during:** Task 2 grep verification.
- **Issue:** A pre-existing Phase 99-04 comment at `codex_curate.py:541` mentions the literal `elif payload.get("reason") == "clarification_needed":` as forward-compat documentation. That comment is from commit `9c34a0634` (Phase 99-04 GREEN, 2026-05-28 16:18:01) and is NOT part of Plan 100-03's diff. It inflates the grep gate by 1.
- **Fix:** No code change needed. The two new code sites at lines 573 (curate_with_codex) + 906 (build_set_with_codex) are exactly the 2 sibling branches Plan 100-03 specified — one per wrapper. Same minor-textual-fix pattern as Phase 99-04 SUMMARY § Deviations item 1. The plan's grep gate exists to count code sites; the comment-only third hit is byte-equivalent forward-compat already present.
- **Files modified:** None (no fix applied).
- **Commit:** N/A.

### Architectural Decisions Not Made (Rule 4 not triggered)

None. Every change was additive code or test extension. The plan's `<antipatterns_to_avoid>` block + the Phase 99-04 SUMMARY's forward-compat authorization pre-empted every architectural decision. Wrapper sibling branches sit beside the existing `tool_starvation` branch in `if + if` form (semantic-equivalent to `if + elif` because both return immediately on match). Phase 99 branches byte-equivalent.

## Notes for Downstream Plans

- **Plan 100-04** (CLI exit code 11): `result.stop_reason == "clarification_needed"` + `result.question` + `result.choices` are now populated through both wrappers. CLI dispatch at `__main__.py:2545-2900` adds the exit-11 branch reading these fields directly. The two-block stderr render (Decision 6) reads `result.question` for the prompt line and iterates `result.choices` for the numbered list.
- **Plan 100-05** (Telegram format_reply branch): `_normalize_codex_curate_result` helper in `__main__.py` will surface `question` + `choices` via `asdict()` round-trip — no helper modification needed (the new dataclass fields flow through `to_dict()` automatically). Telegram bridge's `format_reply` branches on `norm.get("stop_reason") == "clarification_needed"` and reads `norm["question"]` + `norm["choices"]` (both pre-`strip_leaks`).
- **Plan 100-06** (AST gate for no track_id surface): The wrapper additions in this plan DO NOT add a `track_id` read — `q = payload.get("question")` and `cs = payload.get("choices")` are the only payload reads. The AST gate (if it scopes to codex_curate.py) will see zero `track_id` references in the new code.
- **Plan 100-07** (integration seal): The full chain (real toolset.request_clarification → side-channel → wrapper → CodexCurateResult → CLI exit 11 + Telegram format) is now exercisable via `test_clarification_side_channel_propagation_with_real_writer` (this plan's 4th seal test). Plan 100-07 can extend it to also assert the CLI exit code + Telegram format strings.

## Self-Check: PASSED

- `[ VERIFIED ]` `src/vibemix/library/codex_curate.py` exists; CodexCurateResult.question (line 221) + .choices (line 222) present
- `[ VERIFIED ]` curate_with_codex clarification_needed sibling branch at lines 569-588
- `[ VERIFIED ]` build_set_with_codex clarification_needed sibling branch at lines 902-918
- `[ VERIFIED ]` _STOP_REASONS comment block clarification_needed entry at lines 240-245
- `[ VERIFIED ]` `tests/library/test_codex_curate_stop_reason.py` extended with 4 new seal tests (lines 575-846)
- `[ VERIFIED ]` Commit `2e028bbd` exists (test RED)
- `[ VERIFIED ]` Commit `1bebc2a1` exists (impl GREEN)
- `[ VERIFIED ]` `grep -c "clarification_needed" src/vibemix/library/codex_curate.py` = 10
- `[ VERIFIED ]` `grep -c 'payload.get("reason") == "clarification_needed"' src/vibemix/library/codex_curate.py` = 3 (W3 deviation documented — 2 code sites + 1 Phase 99 comment)
- `[ VERIFIED ]` `grep -c 'payload.get("reason") == "tool_starvation"' src/vibemix/library/codex_curate.py` = 4 (Phase 99 byte-equivalent)
- `[ VERIFIED ]` `grep -c "question: str | None" src/vibemix/library/codex_curate.py` = 1
- `[ VERIFIED ]` `grep -c "choices: list\[str\] | None" src/vibemix/library/codex_curate.py` = 1
- `[ VERIFIED ]` 11/11 tests in test_codex_curate_stop_reason.py PASS (4 new + 7 Phase 99 regression)
- `[ VERIFIED ]` 117/117 across broader regression sweep (codex_curate + cli_exit_codes + telegram_bridge + toolset_clarification + toolset_starvation)
- `[ VERIFIED ]` Cold-path smoke: CodexCurateResult(theme='x', stop_reason='created').to_dict() has question=None, choices=None
- `[ VERIFIED ]` No deletions in codex_curate.py diff (`git diff --stat` shows +54/0)
- `[ VERIFIED ]` Disjointness: only codex_curate.py + test_codex_curate_stop_reason.py staged in each commit
