<!-- Auto-persisted from drift-verify utility run wf_1f8b30d4-c6e. Raw: _drift-raw-wf_1f8b30d4.json. Re-run: Workflow(scriptPath=_drift_verify.workflow.js, args={since:'dc4702ebddd7'}). -->

# DRIFT REPORT — HEAD `dc4702eb` (since `e5c0e34e`) · 2026-06-01

**VERDICT: Tree is SAFE to keep landing — zero HOLD-bleed in the 6 new commits; all are frontend/packaging/runtime-default fixes that do not ship net-new ungated speech.** One CRITICAL ship-blocker stands between HEAD and a shippable build (MOSS-model-absent boot crash), plus a now-RED dirty-package checker (a lane-assignment drift the concurrent session introduced — gate regression, not a bleed). Nothing live/packaged is proven; treat all DMG/voice claims as UNPROVEN.

## 1. What landed since `e5c0e34e` (newest-first)
| Commit | Class | speech/timing | hold_bleed |
|---|---|---|---|
| `dc4702eb` feat(tauri-ui): library freshness badge | ACCEPTED | no | no |
| `baeac434` fix(runtime): default packaged voice w/o drop speech | ACCEPTED | no | no |
| `07bf2f34` fix(packaging): bundle sentencepiece for moss | ACCEPTED | no | no |
| `dd71213d` fix(learn-runtime): refresh earned wall (doc/whitespace only) | ACCEPTED | no | no |
| `b16a9bf2` fix(ui-shell): keep settings drawer nav stable | ACCEPTED | no | no |
| `440fcd56` fix(tts): make moss the only voice source | NEEDS_LIVE_PROOF | no | **flagged** |

All 6 carry a DCO `Signed-off-by: Kaan Özkan` trailer; NONE is GPG-signed (`%GS` empty) — "signed" = sign-off, not crypto.
`440fcd56` is code-correct (70 targeted tests pass) but flagged `hold_bleed=true` only because, cut in isolation, it removes all cloud fallback BEFORE `07bf2f34` bundled sentencepiece — moot at HEAD since both landed.

## 2. HOLD-BLEED verdict — **CLEAN** (skeptic UPHELD, high confidence)
- **H-DROP HELD**: spoken DROP block is DIRTY-ONLY, absent from committed HEAD. `git show HEAD:src/vibemix/runtime/coach.py` has no `ev.type=="DROP"` block; `event_detector.py`/`drop_predict.py` DROP hunks are `+` in working tree only. Default OFF confirmed: `__main__.py:784` setdefaults ONLY `VIBEMIX_LOCAL_TTS`; no `VIBEMIX_DROP_CALL` anywhere (committed or dirty). The voiced path (`drop_reaction.py::reaction_line`) is additionally **orphaned/unimported** — doubly safe.
- Dirty audio/midi product files (`deck_capture.py`, `deck_signal.py`, `midi/state.py`) carry zero say/speak/reaction_line in added lines — perception-only.
- **WATCH-ITEM (carried)**: the entire DROP speech path is dirty in shared files (`coach.py`, `event_detector.py`, `drop_predict.py`, `__main__.py`). A whole-file `git add` of any of these would sweep ungated DROP speech in = CRITICAL bleed. **Future commits MUST hunk-stage.**

## 3. Ship-blockers RIGHT NOW
1. **CRITICAL — MOSS model not bundled / no auto-download → fresh-machine boot crash.** MOSS is now the ONLY voice (`tts_chain.py` `_build_moss_chain`); `build_local_tts_adapter()` raises `LocalTTSUnavailable` when model absent (`local_tts.py:307-310`), and `__main__.py:1290` (direct) / `:1301` (proxy) call it with NO surrounding try/except → uncaught raise crashes the sidecar at startup. Specs bundle `sentencepiece` but NOT the ~670MB ONNX model (no `datas` entry); no MOSS downloader exists in `src/vibemix/`. Kaan's dev cache masks it locally. **Fix:** wrap both call sites in `try/except LocalTTSUnavailable` → boot muted + clear banner (never crash); and/or add a MOSS auto-download mirroring `model_assets.install_clap_model`; and/or bundle the model in both specs.
2. **HIGH — stale signed DMG.** Newest `dist/fresh-20260601-latest/vibemix-0.0.1.dmg` mtime **08:32**; ALL TTS-defining commits land 12:33–12:59. No DMG after 12:00 exists (verified). Every packaged/signed/boots-clean claim = UNPROVEN. **Fix:** rebuild+re-sign+notarize+staple from HEAD — but only AFTER blocker #1, or the rebuild crashes on a clean machine.
3. **MED — dirty-package checker is RED (regression, not bleed).** `check_dirty_package_plan.py --strict-assignments` **exits 1** (re-confirmed this turn): `tauri/ui/library.html`, `src/library/library.css`, `state-machine.ts`, `state-machine.test.ts` are unassigned to any lane (concurrent session's library-freshness lane). The skeptic's correction stands — the GREEN reading in the delta/blocker scans is stale. **Fix:** assign those 4 paths to an Include/Hold lane before any commit.

## 4. HOLD-gate status
- **H-MOSS — PARTIAL (moved).** Movable source gate CLEARED: `sentencepiece` in both specs (`macos:148,169` / `windows:159,180`, committed `07bf2f34`) + declared dep. Runtime/packaged + Kaan ear-pass + Windows path + model-degrade UNPROVEN.
- **H-DROP — PARTIAL (moved).** "flip default OFF" sub-gate now SATISFIED (`baeac434`). HARD hold STANDS: grounding-review not run, no live on-beat proof, FP-rate unmeasured, speech still uncommitted.
- **H-WATCH — NO (moot).** No watcher code exists; `watchfiles` only transitive (`uv.lock:2280`).
- **H-BEAT — NO.** Consumer only (`skill_recognizer.py:154`); no production `BEATMATCH_GRADED` emitter; pinned by `tests/repo/test_live_reality_pins.py`.
- **H-CUE — NO.** `export_serato.py:25-26` refusal intact; no in-app render eye-check.
- **H-PKG — NO.** Stale DMG (see blocker #2).
- Stale-evidence correction: `.planning/packets/2026-06-01/_verification-raw-wf_c96f6f8d.json` (12:32) calls drop "armed ON by default via `__main__.py:803`" — STALE, predates `baeac434`. Default is OFF at HEAD.

## 5. Next-slice board
**landed_since `e5c0e34e`:** settings-nav fix (`b16a9bf2`) · freshness badge GUI (`dc4702eb`, 3 specs pass) · H-DROP default-OFF (`baeac434`) · sentencepiece-in-specs (`07bf2f34`) · moss-only voice (`440fcd56`) · earned-wall refresh (`dd71213d`).

**SAFE_NOW (ranked):**
1. **Fix the MOSS boot-crash** (blocker #1) — highest-leverage; unblocks H-PKG/H-MOSS frozen proof. `__main__.py:1290/1301` try/except + optional downloader. *Note: `__main__.py` is a dirty shared file — hunk-stage only.*
2. **Cue-export GUI** — surface the moat (CLI-only today; no `ipc.library.cue` type, no cue panel). `library_cmds.rs` + new shell panel + schema; run `codegen:ipc` + ipc-wiring-checker. Avoid editing dirty `__main__.py`/`coach.py`; reuse the existing `library cue` CLI. risk: med.
3. **Real-audio cue-detection eval gate** — automated correctness gate for the cue engine; mirror the CLAP-corpus fixture pattern. risk: low.

## 6. Codex, do this next
Wrap `build_tts_chain()` at `__main__.py:1290` and `:1301` in `try/except LocalTTSUnavailable` (boot muted + stderr banner, never crash) and assign the 4 unassigned library-freshness paths to a package lane to turn the dirty checker green — hunk-stage only.
