# CODEX_READY — START-GATE commit + LEARN-orphan fix (backend-boot / keystone lane)

> Single-owner files: `src/vibemix/__main__.py` + `src/vibemix/runtime/session_loop.py`. Verified at HEAD `23bd6c0e` (2026-06-04). This is the #1 ship blocker per `SHIP-INGEST-2026-06-04.md`.

## Why this exists (the trap)

The START-GATE backend (locked decision #3) is fully implemented and green **against the working tree**, but it is **NOT committed**: `git show HEAD:src/vibemix/__main__.py | grep -c _activate_session` = **0** (working tree = 2); same for `session_loop.py` `_on_session_start`. It is an **803-line uncommitted diff** (`__main__.py` +738, `session_loop.py` +72) on a shared branch where any sibling `git checkout`/`reset` could wipe it. The committed `tests/test_main_smoke.py::test_smoke_03`/`test_smoke_03b_idle_is_cold_until_start` assert against this absent code, so a clean checkout of HEAD is **RED**.

**AND** the start-gate refactor stranded the entire **Learn runtime in dead code**: `main()` has a top-level `return` at `__main__.py:2314`, but `LessonRuntime(` is constructed at `:3606` and its loops spawn at `:3890` (`lesson_tick_task`) / `:3891` (`lesson_live_grade_task`) — all unreachable. Committing the seam as-is ships Learn DARK (896 tests green, never runs in the app). The W12 live-beatmatch credit is dark for the same family of reasons (`learn_progress=None` at `:2010`, no `learn_state` to the live refresh loop → `session_active` stays False → `coach.py:288` refuses credit).

This goal makes the start gate real at the committed tier WITHOUT darkening Learn.

## Bounded pieces (ONE commit-set, surgical)

1. **LEARN-ORPHAN FIX.** Lift the `LessonRuntime` construction (`:3606`), its task spawns (`lesson_tick_task` `:3890`, `lesson_live_grade_task` `:3891`, the `lesson_runtime.tick_loop` / `live_grade_loop`), the `_LessonRuntimeIpcAdapter` (`:3505`/`:3544`), `_learn_state = LearnState()` (`:3543`), the `_learn_progress` load (`:2409` region), and the learn IPC handler registration to **ABOVE the `main()` return at `:2314`**, into the idle boot shell. Learn must run at **IDLE** (it is NOT gated by Start; a user opens Learn without a live co-host session). Keep Invariant #3 intact via the existing `TwoDeckPlayer.can_play()` gate (practice audio never over a live set).

2. **WIRE W12 LIVE CREDIT.** Pass `learn_progress=_learn_progress` (not `None`) and `learn_state=_learn_state` into the live `coach_loop` (today `__main__.py:2010` passes `learn_progress=None`) and the live `state_refresh_loop` (today no `learn_state` → `_course3_session_lens_active(None)` → `session_active` False). After this a cited live `[ev:BEATMATCH_GRADED@t]` demonstration credits the skill on a REAL set, not just practice. (`runtime/coach.py:264 _credit_live_beatmatch_grade_receipts` is already wired into the loop at `:643`; it just needs the inputs.)

3. **PRUNE THE DEAD TAIL.** Remove the unreachable old eager-capture body from `:2316` to the end of the old `main()` (~1800 lines: the duplicate `open_passthrough_output`/`open_mic_capture`/`open_voice_output`/`open_capture`/`AgentSession`, and the SECOND `_ws_broadcast_once` definition at `~:3864` which is dead — the reachable one is `~:2250`). After pruning, grep-confirm no reachable code references a pruned symbol and `_ws_broadcast_once` is defined exactly once.

4. **R10 ONE-KWARG (same island).** `VoiceRecorder(root=recordings_root, evidence_registry=evidence_registry)` at `:1274` so `evidence_registry.json` is written on session close and debrief drill citations resolve `found=true` (today the recorder never gets the registry → all long-session citations `found=false`). If the `evidence_registry` object is not yet in scope at `:1274`, move the recorder construction to after the registry is built.

5. **CLI VERB (same island, 1 line, optional).** Add `"chatterbox","required","all"` to the argparse `choices` at `__main__.py:4816` (`install_models()` already dispatches them) so `library models --install chatterbox` works headless. Update the `sp_models` epilog accordingly.

6. **COMMIT surgically.** `git add src/vibemix/__main__.py src/vibemix/runtime/session_loop.py`; verify `git diff --cached --name-only` shows **ONLY those two** (CLAUDE.md shared-tree hazard: a sibling's `CLAUDE.md`/`config_store.py`/`ws_bus.py`/other dirty files must NOT be absorbed). Commit with `-s Kaan Özkan <rahipdotaci@gmail.com>`.

## PROOF (by-bus + clean-checkout, NOT working-tree-green)

- **Clean checkout green:** `git archive HEAD | tar -xC /tmp/sg-clean && (cd /tmp/sg-clean && PYTHONPATH=src python3 -m pytest tests/test_main_smoke.py -k "smoke_03 or idle_is_cold" -q)` PASSES — the committed test now has its source.
- **By-bus on the live sidecar** (`VIBEMIX_DEV_SIDECAR=1`, drive-vibemix, `pkill -f "python -m vibemix"` first): idle = no heavy model resident + no capture stream + Learn window answers `ipc.learn.*` (lesson reachable at idle); press Start → live graph activates + capture opens + `-> session ... active`; Stop → `session parked; live graph released`, models freed.
- **W12 live credit:** a cited live `[ev:BEATMATCH_GRADED@t]` resolves a skill credit on the bus during a driven set (not just practice).
- **Freshness gate:** `scripts/dist/check_sidecar_bundle_ready.py` reports `source_dirty=[]` for these two files.
- **Dead-tail gone:** grep shows `_ws_broadcast_once` defined once; no reachable reference to a pruned symbol.

## Island + law

ISLAND: `src/vibemix/__main__.py` + `src/vibemix/runtime/session_loop.py` ONLY. Do NOT touch `messages.schema.json` (frontend-lane owns it; `ipc.session.start/stop` types already exist). Do NOT touch `config_store.py` / `ws_bus.py` (other owners) unless strictly required, and then surgically.

STOP PROTOCOL: do this ONE bounded piece; prove by-bus + clean-checkout; commit; then HALT and report — end the loop. Do NOT keep the goal active waiting for the keystone capture / a signed DMG / a by-ear pass (those are Kaan's, not yours). If a sibling's uncommitted edit to `__main__.py` blocks you, STOP and report the blocker — do not clobber or spin.

SHARED LAW: one tree; `git add <exact paths>` NEVER `-A`; verify `git diff --cached --name-only`; socket `127.0.0.1:8765` one (pkill before probe); commit `-s Kaan Özkan <rahipdotaci@gmail.com>`.

## What this does NOT do (out of scope, separate goals)
- Does NOT prove the co-host sounds like a friend / is not slop (LIVE keystone = Kaan's ear).
- Does NOT close the narrator→coach gap on the master-only rig (the EQ-move guard is the only intel→voice path that fires without per-deck routing — separate engine-lane goal: voice the transition scorer/judge/move-grade without a two-deck requirement, or default per-deck capture on).
- Does NOT de-arm the GA-tag matrix (Windows/Intel in `release.yml` on `v*`) — Kaan/infra.
- Does NOT touch R10's debrief reader, W5 route-doctor `:922`, W15 mac screen-watch (separate small wires).
