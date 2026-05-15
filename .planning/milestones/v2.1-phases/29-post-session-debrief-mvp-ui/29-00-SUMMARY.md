---
plan: 29-00
phase: 29-post-session-debrief-mvp-ui
status: complete
wave: 1
requirements: [DEBRIEF-08, DEBRIEF-09]
commits:
  - 1cfc0bb  # RED  — capability allowlist test
  - fbd6766  # GREEN — capability allowlist json
  - <task2>  # Task 2 monolithic commit (EvidenceRegistry snapshot + tests + fixtures + probes)
tasks_completed: 2/2
tests_added: 12
tests_passing: 12/12
regression_check: 199/199 (tests/audio + tests/runtime)
---

# Plan 29-00 Summary — Wave 0 Unblock

## What was built

### Task 1 — Capability allowlist regex + windows list (commits 1cfc0bb + fbd6766)

Updated `tauri/src-tauri/capabilities/default.json`:
- `shell:allow-execute` validator: `^--(wizard|session)$` → `^--(wizard|session|debrief)$`
- Second `args` entry added: `{ "validator": "^\\d{8}-\\d{6}$" }` for the session-dir positional. Rejects `../etc/passwd`-style traversal at the Tauri runtime layer; Plan 29-04 will add Rust-side `validate_under_root` defense-in-depth.
- `windows` array: `["main","mascot","overlay-*"]` → `["main","mascot","overlay-*","debrief"]`
- Long `description` doc-comment prefixed with "Phase 29-00:" explanation.

### Task 2 — EvidenceRegistry snapshot + debrief short-circuit + fixtures + Wave 0 probes

**Part A — EvidenceRegistry per-session snapshot persistence:**
- `VoiceRecorder.__init__` accepts keyword-only `evidence_registry=None`.
- `VoiceRecorder.close()` serializes the registry snapshot to `<session_dir>/evidence_registry.json` via atomic `os.replace` (tmp+rename). Backward-compat: zero-arg construction still works (no kwarg → no snapshot file).
- The snapshot uses the canonical `EvidenceRegistry.snapshot()` shape `{source: {key: [t, ...]}}` — Plan 29-02's sidecar will read this back at replay time.

**Part B — `--debrief` short-circuit verification:**
- 3 tests assert `cli_entry(["--debrief", SESSION])` dispatches to `_run_debrief_sidecar` BEFORE `main()` (the heavy live runtime). The short-circuit already existed in `__main__.py:1151` from Phase 25; these tests lock it in regression-style.

**Part C — Shared Phase 29 fixtures:**
- `tests/debrief/conftest.py` exposes `sample_session_dir`, `sample_events_jsonl_path`, `sample_evidence_registry_path`, `sample_voice_wav_path`.
- `tests/debrief/fixtures/` committed (via .gitignore allowlist):
  - `sample_events.jsonl` — 20-line slice of real session `recordings/20260515-112139/events.jsonl`.
  - `sample_evidence_registry.json` — synthesized snapshot with `ev` (HEARTBEAT/MIX_MOVE/PHASE) + `track` sources.
  - `sample_voice.wav` — 5-second silent 24kHz mono int16.

**Part D — Wave 0 assumption probes (`29-WAVE0-PROBES.md`):**
- **A1** (gemini-3-pro model id): **PASS with correction** — id is `gemini-3-pro-preview`. Bare `gemini-3-pro` → 404.
- **A3** (PyAV libmp3lame): **PASS** — present in `av.codecs_available`.
- **A5** (Achird voice at 60–90s): **FALLBACK / DEFERRED** → `KAAN-ACTION-PROXY.md` as `A5-VOICE-LISTEN`. Single-constant Kore fallback documented.
- **A7** (Proxy responseSchema passthrough): **FALLBACK / DEFERRED** → `KAAN-ACTION-PROXY.md` as `A7-PROXY-RESPONSESCHEMA-VERIFY`. Pydantic post-hoc validation fallback documented.

## Key files

- `tauri/src-tauri/capabilities/default.json` — validator regex + windows + description updated
- `src/vibemix/audio/recorder.py` — `evidence_registry` kwarg + snapshot serialization in `close()`
- `tests/capabilities/test_debrief_arg_allowlist.py` — 5 tests
- `tests/runtime/test_evidence_registry_snapshot_written.py` — 4 tests
- `tests/main/test_debrief_short_circuits_audio_init.py` — 3 tests
- `tests/debrief/conftest.py` + `tests/debrief/fixtures/{sample_events.jsonl,sample_evidence_registry.json,sample_voice.wav}`
- `.planning/phases/29-post-session-debrief-mvp-ui/29-WAVE0-PROBES.md` — A1/A3/A5/A7 verdicts
- `.planning/KAAN-ACTION-PROXY.md` — A5/A7 deferred items
- `.gitignore` — explicit allowlist for `tests/debrief/fixtures/`

## Deviations

- **`__main__.py` short-circuit was already in place.** Phase 25 Plan 25-03 already added `if args.debrief is not None: _run_debrief_sidecar(...); return` in `cli_entry()` BEFORE the `asyncio.run(main())` dispatch. The plan's Part B asked to "move" the dispatch above audio init, but inspection showed it was already structurally correct. Part B instead became a regression-lock — 3 tests assert the dispatch order so future refactors can't quietly break it.
- **EvidenceRegistry.snapshot() shape preserved.** The plan pseudocode in Task 2 Part A suggested a `{event_id: {evidence_text, timestamp, source}}` shape. The existing locked `snapshot()` method returns `{source: {key: tuple[float,...]}}` and is consumed by the Phase 20 linter — changing the shape would have rippled. We serialize that shape verbatim (`tuple` → JSON `list`). The debrief sidecar in Plan 29-02 will adapt to this shape; citation tooltips in Plan 29-05 will resolve against `(source, key, timestamp)` triples rather than synthetic `event_id` keys.
- **MP3 codec for TLDR audio**: Confirmed PyAV `libmp3lame` is in-process available (no subprocess fallback). Plan 29-01 can encode directly.

## Self-Check: PASSED

- [x] All `<acceptance_criteria>` for both tasks satisfied.
- [x] `pytest tests/capabilities tests/runtime/test_evidence_registry_snapshot_written.py tests/main/test_debrief_short_circuits_audio_init.py` → 12/12 pass.
- [x] Regression check on `tests/audio` + `tests/runtime` → 199/199 pass, no breakage.
- [x] `git log --grep="29-00"` returns 3 commits (RED, GREEN, Task 2).
- [x] Key files created and verified on disk: capabilities/default.json + recorder.py + 3 test files + conftest + 3 fixture files + WAVE0-PROBES.md + KAAN-ACTION-PROXY.md.

## What this unblocks

- **Plan 29-01** can lift the canonical `gemini-3-pro-preview` model id and the PyAV in-process MP3 encoder without further probing.
- **Plan 29-02** can read `<session>/evidence_registry.json` at replay time (it now exists on every real session).
- **Plan 29-04** can spawn a `--debrief <session-dir>` sidecar through the Tauri capability without triggering rejection.
- **Plan 29-04** can create a `WebviewWindow` with label `"debrief"` and have it inherit the default capability.
- **All Phase 29 tests** can use `tests/debrief/conftest.py` fixtures rather than rolling their own.

## Next-phase readiness

Wave 2 (29-01 + 29-03) is unblocked and can run in parallel:
- 29-01 (Python `src/vibemix/debrief/` package — chapters/tldr/drills/stripper) depends only on `evidence_registry.json` shape (locked here) and the `gemini-3-pro-preview` constant (locked here).
- 29-03 (debrief.v1 IPC schema) depends only on the wrapper-naming decisions already in 29-CONTEXT.md — independent of Plan 01's internals.
