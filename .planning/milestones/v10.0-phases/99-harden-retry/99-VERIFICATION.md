---
phase: 99-harden-retry
phase_name: HARDEN-RETRY — Viber Tool-Retry Policy (Factor 9)
verified: 2026-05-28T00:00:00Z
status: human_needed
score: 7/7 must-haves verified (engineering complete; 2 KAAN-ACTION items deferred to milestone close)
acid_test: passed
req_coverage: 7/7
cardinal_invariants: held
disjointness_contract: held
kaan_action_parked: 2  # §HARDEN-PHASE-A-EAR-PASS + §HARDEN-PHASE-A-ENV-PROPAGATION-VERIFY
overrides_applied: 0
re_verification:
  previous_status: null  # initial verification
  previous_score: null
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "§HARDEN-PHASE-A-EAR-PASS — funded-Codex-key ear-pass on the three seeded hint case strings"
    expected: |
      On Kaan's funded Codex key (no test substitute possible — anti-slop verdict is human-perceptual):
        Case A — `library curate "any theme"` against empty library cache prints to stderr:
          [viber/codex] tool_starvation: library has 0 tracks — run `library ingest` first
        Case B — `library curate "uplifting 200 BPM ambient"` against real library with no match:
          [viber/codex] tool_starvation: no tracks matched 'uplifting 200 BPM ambient' — try a broader theme or different BPM range
        Case C — known-broken handler triggers ≥3 consecutive errors:
          [viber/codex] tool_starvation: tool '<name>' kept failing — try again or check codex installation
      Kaan's question (from PROJECT.md): "Does it sound like a real friend telling you the library is empty, or like generic error text?"
      Verdict options: approved (ships) / tweak now (name case + new wording) / defer to milestone close (rides forward).
    why_human: |
      Anti-slop tone is a human-perceptual release gate per CLAUDE.md core value
      ("real DJ friend in your ear, not voice assistant doing music commentary").
      No automated check can substitute for Kaan's ear. Tests pin SUBSTRINGS
      ("library has 0 tracks", "no tracks matched", "kept failing") not full
      strings, so ear-pass wording tweaks around the load-bearing substrings
      won't break the seal — only removal of the key phrase themselves would.
      Default per `gsd-autonomous fully` mode = defer to milestone close.
  - test: "§HARDEN-PHASE-A-ENV-PROPAGATION-VERIFY — Codex CLI → MCP subprocess env-var passthrough verification"
    expected: |
      On first real Codex run (Codex CLI installed + logged in + funded key + VIBEMIX_CODEX_ALLOW_SHELL=1):
        $ uv run python -m vibemix library curate "any theme" 2>&1 | head -40
      Look for the FIRST `[viber-mcp]` stderr line emitted by mcp_server.py:71-76:
        PASS:    [viber-mcp] VIBEMIX_STOP_REASON_FILE=/var/folders/.../T/viber-codex-XXXXX/stop_reason.json
        FAIL:    [viber-mcp] VIBEMIX_STOP_REASON_FILE=<absent>
      Four verdict outcomes per Plan 99-08 Task 4 table:
        passthrough verified → DISCHARGED, B1 risk CLOSED
        passthrough broken   → files HARDEN-FUTURE-N (three investigation paths documented in 99-08-SUMMARY)
        MCP failed to boot   → separate bug filed
        skip (Codex not installed) → rides forward (TAKEN at phase close per `gsd-autonomous fully`)
    why_human: |
      The Codex CLI → MCP-child subprocess boundary is owned by Codex's CLI
      subprocess-spawning behavior — an EXTERNAL binary outside vibemix's
      control. No unit test can simulate it because the question IS whether
      the real Codex preserves the env var across the boundary. Only a live
      Codex run reveals the truth (the silent-no-op failure mode is the
      whole reason Channel A's observability probe exists at mcp_server.py:72).
      Plan 99-04 / Plan 99-08 explicitly observe-then-defer; default per
      `gsd-autonomous fully` mode = rides forward to milestone close.
---

# Phase 99: HARDEN-RETRY Verification Report

**Phase Goal (from ROADMAP.md):** When Viber runs against an empty / starved library / unmatched theme, it terminates with an honest, actionable `stop_reason="tool_starvation"` payload that the CLI surfaces as a non-zero exit + a real diagnosis. Today the same scenario returns "no playlist" with no diagnosis — Codex's MCP harness retries internally but vibemix has no consecutive-error counter or terminal stop_reason for tool starvation. This is the Factor 9 closure (compact errors into context window → make the agent terminate honestly when retries can't recover).

**Acid Test (from PROJECT.md):** Codex backend against an intentionally empty library returns honest `tool_starvation: library has 0 tracks — run \`library ingest\` first` with a non-zero exit on the CLI.

**Verified:** 2026-05-28
**Status:** `human_needed` (engineering complete + 2 KAAN-ACTION items requiring funded-Codex-key ear-pass)
**Re-verification:** No — initial verification

---

## Acid Test Verdict: PASSED (engineering surface)

The acid-test predicate is structurally proven by `tests/library/test_codex_curate_stop_reason.py::test_uniform_propagation_curate_path` (lines 357-413):

| Predicate | Evidence | Status |
| --------- | -------- | ------ |
| Empty library triggers `tool_starvation` | `_empty_library()` fixture + `_build_starvation_payload` returns `{"reason": "tool_starvation", "hint": "library has 0 tracks — run \`library ingest\` first", ...}` | ✓ VERIFIED via real generator pre-check at test line 382 |
| Hint reaches `CodexCurateResult.error` | Wrapper short-circuits at `codex_curate.py:532-548`; test asserts `"library has 0 tracks" in res.error` at line 408 | ✓ VERIFIED |
| CLI exits non-zero (10) on `tool_starvation` | `__main__.py:2669` and `:2719` both return `10 if result.stop_reason == "tool_starvation" else 1`; `tests/library/test_cli_exit_codes.py` pins both paths | ✓ VERIFIED |
| Exit code distinguishes from "no playlist" | `no_playlist` returns 1; `tool_starvation` returns 10; documented at `__main__.py:2667` ("Plan 99-06 / Decision 6: 10 = tool_starvation, 1 = other failures") | ✓ VERIFIED |

The real KAAN ear-pass on the funded Codex key is the human-perceptual layer (parked, see human_verification frontmatter).

---

## Goal Achievement

### Observable Truths (mapped to ROADMAP Success Criteria)

| #   | Truth (Success Criterion) | Status | Evidence |
| --- | ------------------------- | ------ | -------- |
| 1   | Empty library cache produces `stop_reason="tool_starvation"` w/ hint naming empty library as cause | ✓ VERIFIED | `toolset.py:1051-1052` Case A generator + `tests/library/test_toolset_starvation.py` substring assertions ("library has 0 tracks") + `tests/library/test_codex_curate_stop_reason.py:357-413` end-to-end wrapper propagation test |
| 2   | Narrow-theme zero-match library produces `tool_starvation` w/ hint naming narrow theme | ✓ VERIFIED | `toolset.py:1055-1060` Case B generator (interpolates `args.get("query","")` into hint) + `tests/library/test_codex_curate_stop_reason.py:410-474` build_set_with_codex propagation test using "too-narrow-theme" theme |
| 3   | CLI exit code 10 (`tool_starvation`) distinct from successful "no playlist" exit | ✓ VERIFIED | `__main__.py:2669, 2719` `return 10 if result.stop_reason == "tool_starvation" else 1`; `tests/library/test_cli_exit_codes.py` exit-code dispatch tests; PROJECT.md acid-test directly proven |
| 4   | Counter writes confined to handler-entry/exit sites (single-writer analog of Invariant #1) AND starvation short-circuits BEFORE `create_playlist` library re-validation | ✓ VERIFIED | (a) `_consecutive_empties` writes ONLY at `toolset.py:128, 1188, 1208` (verified via `grep -rn` — 0 matches outside toolset.py in `src/`); (b) `dispatch()` checks `self.stop_reason is not None` at `toolset.py:1142` BEFORE the handler dispatch table at 1145; (c) `tests/repo/test_no_seen_relaxation.py` AST gate pins `self.seen.add` count = 2 (unchanged from pre-Phase-99 baseline); (d) `tests/library/test_toolset_starvation.py::test_starvation_short_circuits_create_playlist` confirms via RuntimeError sentinel |
| 5   | `curate_with_codex` AND `build_set_with_codex` surface `tool_starvation` uniformly to all callers (CLI + Telegram + GUI) | ✓ VERIFIED | Both wrappers have identical side-channel-read short-circuit (`codex_curate.py:532-548` + `:847-861`); `tests/library/test_codex_curate_stop_reason.py::test_to_dict_serializes_starvation_shape` pins shape parity (`set(d.keys()) == set(d2.keys())`); Telegram normalizer at `__main__.py:2917-2945`; format_reply branch at `telegram_bridge.py:118` |

**Score:** 5/5 Success Criteria + 7/7 REQ-IDs verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/vibemix/library/toolset.py` | Counter attr + threshold const + starvation hook in dispatch | ✓ VERIFIED | `TOOL_STARVATION_THRESHOLD = 3` at line 75; `_consecutive_empties` + `stop_reason` at lines 128-129; `_build_starvation_payload` at 1022-1073; `_write_side_channel` at 1075-1113; `_is_empty_or_error` at 1115-1131; threshold-trip block at 1187-1208; `__all__` exports `TOOL_STARVATION_THRESHOLD` at 1341 (WR-01 fix) |
| `src/vibemix/library/codex_curate.py` | Side-channel read + propagation in both wrappers | ✓ VERIFIED | curate_with_codex: tempdir + env var + short-circuit at 461-548; build_set_with_codex: parallel at 779-861; CodexCurateResult shape at 201-218 with `tool_starvation` listed in _STOP_REASONS at 227 |
| `src/vibemix/library/mcp_server.py` | B1 startup probe (stderr line at MCP child boot) | ✓ VERIFIED | `print(f"[viber-mcp] VIBEMIX_STOP_REASON_FILE=...")` at lines 71-76 — emits absent/path on every MCP subprocess boot, the live-Codex acid test |
| `src/vibemix/library/telegram_bridge.py` | `tool_starvation` branch in `format_reply` | ✓ VERIFIED | Branch at line 118 `if norm.get("stop_reason") == "tool_starvation"` BEFORE the generic error fall-through; preserved `strip_leaks` privacy posture |
| `src/vibemix/__main__.py` | CLI exit-code dispatch + Telegram normalizer | ✓ VERIFIED | curate at 2669 (`return 10 if result.stop_reason == "tool_starvation" else 1`); build-set at 2719; `_normalize_codex_curate_result` at 2917-2945; LiveKit handoff at `:1353` UNTOUCHED |
| `tests/library/test_toolset_starvation.py` | Scaffold + dispatch + threshold-trip + create_playlist short-circuit tests | ✓ VERIFIED | All scenarios from REQ-06: zero-track, narrow theme, dispatch error path, counter reset on success, create_playlist short-circuit |
| `tests/library/test_toolset_starvation_concurrency.py` | Concurrency acid test (parallel dispatch monotonic) | ✓ VERIFIED | File exists; included in 53/53 Phase 99 chain run |
| `tests/library/test_codex_curate_stop_reason.py` | Wrapper propagation seal (3 integration tests) | ✓ VERIFIED | 7 tests total (4 from 99-04 + 3 from 99-08 seal); all green |
| `tests/library/test_cli_exit_codes.py` | CLI exit 10 dispatch + Telegram normalizer | ✓ VERIFIED | Pins __main__.py:2669/2719 + 2917-2945 |
| `tests/library/test_telegram_bridge.py` | `format_reply` tool_starvation branch | ✓ VERIFIED | Plan 99-07 RED-then-GREEN tests + regression pin |
| `tests/repo/test_no_seen_relaxation.py` | AST gate (Invariant #2 + single-writer + propagation whitelist) | ✓ VERIFIED | 3 gates: `test_seen_writes_unchanged_from_baseline` (count=2), `test_consecutive_empties_single_writer` (toolset.py only), `test_stop_reason_writes_confined_to_toolset` (4-file whitelist) |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `dispatch()` (toolset.py:1133) | `_build_starvation_payload` (1022) | Direct method call at 1203 | ✓ WIRED | Threshold-trip block invokes on first-write-wins guard `self.stop_reason is None` |
| `_build_starvation_payload` | `_write_side_channel` (1075) | Direct method call at 1206 | ✓ WIRED | Side-channel write rides same first-write-wins guard |
| `_write_side_channel` | `VIBEMIX_STOP_REASON_FILE` env var | `os.environ.get` at 1100 | ✓ WIRED | Silent no-op when env var absent (env-gated) |
| `curate_with_codex` | side-channel file | `tempfile.TemporaryDirectory` + env var + `Path(stop_reason_path).exists()` check at 532 | ✓ WIRED | Reads file INSIDE tempdir block (Pitfall 4 avoided per REVIEW.md §5.3) |
| `build_set_with_codex` | side-channel file | Identical pattern at 779-861 | ✓ WIRED | Parallel implementation, same shape |
| `mcp_server.build_toolset` | B1 stderr probe | `print(f"[viber-mcp] VIBEMIX_STOP_REASON_FILE=...")` at 71-76 | ✓ WIRED | Emits on every MCP subprocess boot — live-Codex acid test |
| `CodexCurateResult.to_dict()` | CLI exit-code dispatch | `result.stop_reason == "tool_starvation"` at `__main__.py:2669, 2719` | ✓ WIRED | Returns exit 10 on match |
| `format_reply` (telegram_bridge.py:107) | `tool_starvation` rendering | `if norm.get("stop_reason") == "tool_starvation"` at 118 | ✓ WIRED | Branch fires BEFORE generic error fall-through |
| `_normalize_codex_curate_result` | Telegram `format_reply` | `{"ok": False, "stop_reason": "tool_starvation", "hint": ...}` at __main__.py:2941-2944 | ✓ WIRED | Uniform shape across CLI + Telegram surfaces |

### Data-Flow Trace (Level 4) — Acid Test Path

| Stage | Data Variable | Source | Produces Real Data | Status |
| ----- | ------------- | ------ | ------------------ | ------ |
| Counter increment | `self._consecutive_empties` | dispatch() handler return + `_is_empty_or_error` predicate at 1187 | YES (real counter state from real dispatch returns) | ✓ FLOWING |
| Threshold-trip payload | `self.stop_reason` | `_build_starvation_payload(last_tool=name, args=args)` at 1203 | YES (deterministic 3-case logic over real library state — `self._library.tracks`) | ✓ FLOWING |
| Side-channel write | `payload` JSON file | `_write_side_channel(self.stop_reason)` at 1206 | YES (real payload from real generator; env-gated, silent no-op when absent) | ✓ FLOWING (env-gated) |
| Wrapper read | `payload` from `stop_reason_path` | `json.loads(Path(stop_reason_path).read_text())` at codex_curate.py:534-537 | YES (real file read inside tempdir block) | ✓ FLOWING |
| CLI dispatch | `result.stop_reason` | `CodexCurateResult.stop_reason` from wrapper at codex_curate.py:543 | YES (real dataclass field) | ✓ FLOWING |
| Exit code | `return 10` | `__main__.py:2669, 2719` ternary on `result.stop_reason` | YES (real exit code emitted to process exit) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Seal tests pass on current source | `python3 -m pytest -q tests/library/test_codex_curate_stop_reason.py -v` | `7 passed in 0.14s` | ✓ PASS |
| Phase 99 verify chain (53 tests, no regressions) | `python3 -m pytest -q tests/library/test_toolset_starvation.py tests/library/test_toolset_starvation_concurrency.py tests/library/test_codex_curate_stop_reason.py tests/library/test_cli_exit_codes.py tests/library/test_telegram_bridge.py tests/repo/test_no_seen_relaxation.py` | `53 passed in 5.41s` | ✓ PASS |
| Broader library suite + AST gate | `python3 -m pytest -q tests/library/ tests/repo/test_no_seen_relaxation.py` | `648 passed, 1 skipped, 1 xfailed in 11.64s` (xfail pre-existing budget gate, unrelated) | ✓ PASS |
| Acid test (empty library → tool_starvation) | Inspected `test_uniform_propagation_curate_path` (lines 357-413) — real `_build_starvation_payload` against zero-track library produces `{"reason": "tool_starvation", "hint": "library has 0 tracks — ..."}`; wrapper short-circuits with `CodexCurateResult(stop_reason="tool_starvation", error="library has 0 tracks — ...")` | Test green | ✓ PASS |
| Live Codex run against empty library (B1 boundary) | Requires funded Codex key — NOT runnable in this environment | n/a | ? SKIP (routed to human_verification) |
| Ear-pass on three seeded hint case strings | Requires Kaan's ear — human-perceptual anti-slop verdict | n/a | ? SKIP (routed to human_verification) |

### Probe Execution

No `scripts/*/tests/probe-*.sh` for this phase (engineering-only phase; no migration/tooling probes). The B1 startup probe at `mcp_server.py:71-76` IS the probe surface but it requires a live Codex run on Kaan's funded key (routed to human_verification §HARDEN-PHASE-A-ENV-PROPAGATION-VERIFY).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| HARDEN-RETRY-01 | 99-01 → 99-02 | LibraryToolset per-instance consecutive-empty/error counter | ✓ SATISFIED | `self._consecutive_empties: int = 0` at toolset.py:128; counter mutation at 1188/1208 (single-writer pinned) |
| HARDEN-RETRY-02 | 99-03 → 99-04 | After N=3 consecutive empties, terminal `stop_reason="tool_starvation"` payload | ✓ SATISFIED | Threshold trip at toolset.py:1199-1206; terminal short-circuit at 1142-1143; `tests/library/test_toolset_starvation.py` |
| HARDEN-RETRY-03 | 99-03 | Actionable hint, 3 cases (zero-track / narrow-theme / tool error) | ✓ SATISFIED | `_build_starvation_payload` at toolset.py:1022-1073; 3-case dispatch verified inline at 1051-1067; substrings pinned in `test_toolset_starvation.py` |
| HARDEN-RETRY-04 | 99-06 | CLI non-zero exit (10) distinct from "no playlist" (1) | ✓ SATISFIED | `__main__.py:2669, 2719` ternary; `tests/library/test_cli_exit_codes.py` pins both code paths |
| HARDEN-RETRY-05 | 99-05 | Invariant #2 holds (additive, no `seen` relaxation) | ✓ SATISFIED | `self.seen.add` count = 2 (unchanged); `tests/repo/test_no_seen_relaxation.py` 3-gate AST suite + `test_starvation_short_circuits_create_playlist` with RuntimeError sentinel proves create_playlist re-validation is NEVER reached after threshold trip |
| HARDEN-RETRY-06 | spread 99-02 → 99-08 | Failing-then-passing tests for 6+ scenarios | ✓ SATISFIED | All 6 scenarios covered: zero-track (test_toolset_starvation.py), narrow theme (test_codex_curate_stop_reason.py:test_uniform_propagation_build_set_path), dispatch error (test_toolset_starvation.py), counter reset (test_toolset_starvation.py:200-211), create_playlist short-circuit (test_toolset_starvation.py:650+), wrapper propagation (test_codex_curate_stop_reason.py) |
| HARDEN-RETRY-07 | 99-04 + 99-06 + 99-07 + 99-08 | Uniform propagation CLI + Telegram + GUI | ✓ SATISFIED | All three surfaces wired: CLI at `__main__.py:2669/2719`; Telegram at `telegram_bridge.py:118` + normalizer at `__main__.py:2917-2945`; GUI consumes the `CodexCurateResult.to_dict()` shape pinned by `test_to_dict_serializes_starvation_shape` (key-set parity cross-check) |

### Cardinal Invariants Verification

| Invariant | Status | Evidence |
| --------- | ------ | -------- |
| **#1 single-writer (analog)** | ✓ HELD | `_consecutive_empties` writes appear ONLY in `src/vibemix/library/toolset.py` (lines 128, 1188, 1208 — verified by `grep -rn` on `src/`); writes occur on the dispatch-calling thread AFTER `fut.result()` returns and the `ThreadPoolExecutor` worker is joined (toolset.py:1168-1175); same serialization analog as `_genre_lookup` at toolset.py:407-411; AST gate `tests/repo/test_no_seen_relaxation.py::test_consecutive_empties_single_writer` green |
| **#2 citation grounding** | ✓ HELD | `self.seen.add` count = 2 (unchanged from pre-Phase-99 baseline) — verified by `grep -rn "self\.seen\.add" src/` returning exactly 2 hits at toolset.py:157 (search_vibe) and toolset.py:616 (discover_pool); terminal short-circuit at `toolset.py:1142-1143` fires BEFORE the handler dispatch table at 1145, so `create_playlist`'s seen-set gate (1st gate) AND `create_playlist.create_playlist`'s library re-validation (2nd gate) are NEVER reached after threshold trip; `test_no_seen_relaxation.py::test_seen_writes_unchanged_from_baseline` pins baseline; `test_toolset_starvation.py::test_starvation_short_circuits_create_playlist` confirms with RuntimeError sentinel on module-bound `create_playlist` callable |
| **#3 trust the audio** | ✓ HELD (N/A direct) | Live co-host (`src/vibemix/agent/`, `__main__.py:1353` LiveKit handoff) untouched by Phase 99 (verified — 0 files in `src/vibemix/agent/` modified across all 27 Phase 99 commits); the curation-surface extension of "trust the audio" via deterministic 3-case hint (never LLM-generated) is documented in `_build_starvation_payload` docstring at toolset.py:1029 |
| **#4 one socket** | ✓ HELD (N/A direct) | No new ws traffic; CLI + MCP STDIO + Telegram long-poll surfaces only; the side-channel file transport is local-FS via env-gated tempdir, never a port |

### Disjointness Contract Verification

| Forbidden Area | Status | Evidence |
| -------------- | ------ | -------- |
| `src/vibemix/agent/*` (live co-host) | ✓ UNTOUCHED | Verified: 0 files in `src/vibemix/agent/` across all 27 Phase 99 commits; `grep -rn "tool_starvation\|stop_reason" src/vibemix/agent/` returns 0 matches |
| `src/vibemix/__main__.py:1353` (LiveKit handoff) | ✓ UNTOUCHED | Verified by reading lines 1348-1359 — content matches Phase 77 Plan 04 (`-> grounding: disabled` print at 1353); Phase 99 only touched lines 2547-2945 (CLI dispatch + normalizer) |
| `src/vibemix/intel/*` | ✓ UNTOUCHED | Verified: 0 files in `src/vibemix/intel/` across all 27 Phase 99 commits; `grep -rn "tool_starvation\|stop_reason" src/vibemix/intel/` returns 0 matches |
| `tauri/ui/*` (frontend wiring handoff) | ✓ UNTOUCHED | Verified: 0 files in `tauri/ui/` across all 27 Phase 99 commits; `grep -rn` on `tauri/ui/src/` returns 0 matches for `tool_starvation` |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |

(None blocking. The REVIEW.md identified 3 WARNING-level items in the depth-standard review; all 3 are documented as FIXED via commits 6de3ac2f, 11bb45e8, ec3757a5. The 6 INFO items are non-blocking nits documented for forward-compat / clarity. Verified WR-01 fix: `__all__` at toolset.py:1341 includes `TOOL_STARVATION_THRESHOLD`. Verified WR-03 fix: `_write_side_channel` catches `(OSError, TypeError, ValueError)` at toolset.py:1106.)

### Human Verification Required

#### 1. §HARDEN-PHASE-A-EAR-PASS — funded-Codex-key ear-pass on the three seeded hint case strings

**Test:** On Kaan's funded Codex key, run three scenarios:
- Case A — `library curate "any theme"` against empty library cache (`rm ~/.cache/vibemix/library.pkl` first)
- Case B — `library curate "uplifting 200 BPM ambient"` against real library w/ no match
- Case C — induce a known-broken handler to cause ≥3 consecutive `{"error": ...}` returns

**Expected:** stderr contains the three case strings verbatim (or close enough that the substrings `"library has 0 tracks"`, `"no tracks matched"`, `"kept failing"` survive). Ask the PROJECT.md question: *"Does it sound like a real friend telling you the library is empty, or like generic error text?"* Verdict: approved / tweak now (name case + new wording) / defer to milestone close.

**Why human:** Anti-slop tone is human-perceptual; no automated check substitutes for Kaan's ear. Tests pin SUBSTRINGS not full strings, so ear-pass tweaks around the load-bearing substrings won't break the seal. Default per `gsd-autonomous fully` mode = defer to milestone close.

#### 2. §HARDEN-PHASE-A-ENV-PROPAGATION-VERIFY — Codex CLI → MCP subprocess env-var passthrough

**Test:** On a Codex install with `codex login` complete:
```bash
codex --version
codex login
export VIBEMIX_CODEX_ALLOW_SHELL=1
uv run python -m vibemix library curate "any theme" 2>&1 | head -40
```

**Expected:** First `[viber-mcp]` stderr line emitted by mcp_server.py:71-76. Four observable outcomes per the Plan 99-04 / 99-08 Task 4 verdict table:
- PASS: `[viber-mcp] VIBEMIX_STOP_REASON_FILE=/var/folders/.../T/viber-codex-XXXXX/stop_reason.json` → DISCHARGED, B1 risk CLOSED
- FAIL: `[viber-mcp] VIBEMIX_STOP_REASON_FILE=<absent>` → files HARDEN-FUTURE-N (three investigation paths)
- MCP failed to boot → separate bug filed
- skip (Codex not installed) → rides forward

**Why human:** The Codex CLI → MCP-child subprocess boundary is owned by an EXTERNAL binary (Codex). Only a live Codex run reveals whether env var preservation works.

### Gaps Summary

**No engineering gaps.** All 7 HARDEN-RETRY REQ-IDs satisfied, all 5 ROADMAP Success Criteria met, all 4 Cardinal Invariants held, disjointness contract held, acid test predicate proven via seal tests.

**Two KAAN-ACTION items parked** per PROJECT.md `gsd-autonomous fully` mode default — both are human-perceptual / external-binary-dependent verifications that no automated check can substitute for. Status `human_needed` reflects this — engineering is done; what remains is Kaan's ear and a real Codex run.

---

## Cross-Reference Verification

**Re-confirmation of REVIEW.md verdicts (depth-standard code review on 2026-05-28):**

1. **REVIEW.md verdict CLEAN** (0 BLOCKER, 3 WARNING all fixed, 6 INFO non-blocking) — re-verified:
   - WR-01: `__all__` at toolset.py:1341 includes `TOOL_STARVATION_THRESHOLD` ✓
   - WR-02: Comment at toolset.py:119-124 reflects shipped state ✓
   - WR-03: `_write_side_channel` catches `(OSError, TypeError, ValueError)` at 1106 ✓

2. **Test green-ness:** Phase 99 verify chain 53/53; library island 648/0 (1 skipped + 1 xfailed unrelated to Phase 99).

3. **Pre-existing failures in unrelated subsystems** (documented in `deferred-items.md`): 15 failures in audit/e2e/repo/scripts/security/sidecar/ui_bus, NONE caused by Phase 99 — verified via Plan 99-08 Task 2 baseline check.

---

_Verified: 2026-05-28_
_Verifier: Claude (gsd-verifier, Opus 4.7 1M-context)_
_Depth: goal-backward (PROJECT.md acid test + ROADMAP Success Criteria + REQ-IDs + Cardinal Invariants + Disjointness Contract)_
