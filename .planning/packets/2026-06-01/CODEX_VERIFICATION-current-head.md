# CODEX Verification — Current HEAD

- **Date:** 2026-06-01
- **Verifier:** Claude (read-only coordinator; Codex is the implementer)
- **HEAD pinned this pass:** `e5c0e34e774f3e9c4f3978ed04a0b9c7b761a19a` (`fix(tts): keep explicit local voice on device`)
- **Method:** 22-agent read-only workflow (`wf_c96f6f8d-aa8`) — 1 evidence agent + 1 adversarial skeptic per item, across 5 commits + 6 lanes. Every claim carries a `file:line` anchor, a test result, or an explicit NOT-FOUND. Commit verification used immutable `git show <hash>`; dirty-remnant analysis used `git diff HEAD`. Raw evidence: [`_verification-raw-wf_c96f6f8d.json`](_verification-raw-wf_c96f6f8d.json).
- **No product code was edited, staged, or committed.** Only `.planning/packets/2026-06-01/` docs were written.
- **Caveat — the tree is MOVING:** a concurrent Codex/Claude session edits the working tree (e.g. `agent/line_voice.py`, `tests/agent/test_tts_chain.py` appeared mid-pass). Line numbers below may drift by a few lines; the symbol/`file:line` anchors were correct at HEAD `e5c0e34e`. Re-pin HEAD before acting.

---

## Verdict table — LAND commits since `2bd44cc5`

| Commit | Title | Class | Skeptic | One-line |
|---|---|---|---|---|
| `302d747d` | feat(library): export auto-cued folders | **ACCEPTED** | unchanged · high | `library cue <folder>` CLI real, deterministic, offline; 18 tests pass. App/hardware import unproven. |
| `3892f4bd` | fix(runtime): supervise live bus task failures | **ACCEPTED** | unchanged · high | ws_broadcast loop restart-supervised; 6 other loops crash-observed. NOT a speech change. Live recovery unproven. |
| `6254c923` | fix(deps): sync optional local tts lock | **ACCEPTED** | unchanged · high | uv.lock synced for `tts-local` extra + sentencepiece→ai-local; strictly extra-gated, not base. |
| `8105b04f` | feat(library): write opt-in Serato cue tags | **ACCEPTED** (byte-conformance) / **NEEDS LIVE PROOF** (app-visual) | unchanged · high | Serato Markers2 writer opt-in, double-gated, merge-preserved, mutagen lazy/optional; byte-roundtrip covered. Real-Serato render = human eye-check. |
| `e5c0e34e` | fix(tts): keep explicit local voice on device | **ACCEPTED** (source-level) | unchanged · high | When `VIBEMIX_LOCAL_TTS` + cached, both chains return MOSS-only (no silent paid fallback). Packaged/live MOSS unproven. ⚠️ dirty tree goes further (see HOLD). |

> **All 5 commits survived adversarial refutation at high confidence.** No over-claims; no commit asserts live or packaged behavior it cannot prove. Skeptics re-ran tests and re-read source independently.

---

## Per-commit detail

### `302d747d` — export auto-cued folders → ACCEPTED
- **Files:** `src/vibemix/__main__.py` (+82: `sp_cue` subparser + `_cmd_library_cue`), `src/vibemix/library/cue_folder.py` (new 245L), `tests/library/test_cue_folder.py` (236L), `tests/library/test_cue_folder_cli.py` (95L).
- **Tests:** `uv run pytest -q tests/library/test_cue_folder.py tests/library/test_cue_folder_cli.py` → **18 passed**. Live argparse probe resolves `func=_cmd_library_cue` via `_build_library_subparsers` (`__main__.py:3201`) + library-argv dispatch (`__main__.py:6871`).
- **Proves:** CLI path real & reachable; `cue_folder.py` deterministically walks a folder (`sorted(rglob)` filtered by `SUPPORTED_SUFFIXES`, `cue_folder.py:117`), maps `CueAnchor`s to ascending-numbered hot-cues (`anchors_to_marks` sorted by `start_s`, capped at 8 pads, `:81`), writes Rekordbox `collection.xml` and/or order-only M3U8 deterministically (`write_m3u8 :144-156`). Fully offline — grep `genai|GEMINI|google|api_key` = NOT-FOUND. Heavy deps lazy (`detect_cues_auto`, `export_set` imported inside functions). Invariant #3 honored: anchorless file → skipped, no fabricated cue (`:133-141`).
- **Does NOT prove:** real `detect_cues_auto`/CUE-DETR ONNX produces musically-correct anchors (every test injects a fake detect fn); real Rekordbox import / hardware pad render; packaged-binary reachability (verified on `uv run` source, not the frozen sidecar — plain `uv run python -m vibemix` prunes `onnxruntime`).
- **Correction:** the task's command name `export-cued-folder` is **inaccurate** — actual subcommand is `library cue <folder>` (no `export-cued-folder` parser exists).
- **Dirty remnants:** the 3 feature files are **clean at HEAD**. Shared `__main__.py` carries ~203 dirty lines / 13 hunks; only **one** is cue-adjacent (the `8105b04f` Serato help-text touch) → hunk-stage with cue-export, never whole-file.
- **No grounding-review needed** — offline library/CLI path; touches nothing the co-host says or when.

### `3892f4bd` — supervise live bus task failures → ACCEPTED
- **Files:** `src/vibemix/__main__.py` (+91), `tests/runtime/test_main_supervision.py` (new 117L).
- **Tests:** `uv run pytest -q tests/runtime/test_main_supervision.py` → passed.
- **Proves:** a failing `ws_broadcast` loop is caught, logged to stderr **and** the structured trace sink, and restarted with a `stop_event`-gated retry delay (no more permanently-dark UI). The other 6 long-running `*_loop` tasks get a crash-observer that logs once with the correct task name. Respects cooperative `stop_event` shutdown.
- **NOT HOLD-sensitive:** adds nothing the co-host says, changes nothing about when it speaks — `coach_loop`/`dj_cohost`/`prompts`/`event_detector`/`drop_predict`/heartbeat untouched; `coach_task` is observed (log-only).
- **Does NOT prove:** live-runtime recovery in the packaged app (a real `ws_broadcast` exception recovering the UI within `retry_delay`) — that needs `drive-vibemix`.
- **Dirty remnants:** `__main__.py` dirty hunks do **not** overlap the committed supervisor region (verified: 5 supervisor symbols byte-identical to HEAD in the dirty diff).

### `6254c923` — sync optional local tts lock → ACCEPTED
- **Files:** `uv.lock` (+25/-1).
- **Proves:** lock synced to a pyproject change adding a `tts-local` optional extra + `sentencepiece` to `ai-local`, for the opt-in MOSS voice. **`sentencepiece` is strictly extra-gated** — not in base deps, no markerless `requires-dist` entry.
- **Does NOT prove:** MOSS works end-to-end (runtime wiring is separate/uncommitted); the PyInstaller spec bundles `sentencepiece` (**it does not** — see moss-tts lane).
- **Dirty remnants:** `uv.lock` is committed-clean (`git diff HEAD -- uv.lock` empty). Note: confirm the `tts-local`/`sentencepiece` `pyproject.toml` change is itself committed (the evidence agent observed it in the working tree; re-pin HEAD to confirm since the tree moved).

### `8105b04f` — write opt-in Serato cue tags → ACCEPTED (byte-conformance) / NEEDS LIVE PROOF (app-visual)
- **Files:** `pyproject.toml` (+8 `serato` extra), `src/vibemix/__main__.py` (+96), `src/vibemix/library/cue_folder.py` (+54: `tag_folder_serato`), `src/vibemix/library/export_serato.py` (**new 271L**), `tests/library/test_export_serato.py` (new 180L), `tests/library/test_cue_folder.py` (+38), `tests/library/test_cue_folder_cli.py` (+32), `uv.lock` (+15).
- **Tests:** `uv run pytest -q tests/library/test_export_serato.py tests/library/test_cue_folder.py tests/library/test_cue_folder_cli.py` → passed (incl. the package-checklist's 29-test cue+serato run).

**The 7 questions (all answered with evidence):**
1. **CLI real?** YES, reachable. `--write-tags` (`store_true`) + `--no-merge` on the `cue` subparser (`__main__.py:2767-2778`); `_cmd_library_cue` branches to `tag_folder_serato(allow_write=True, …)` (`__main__.py:6104-6118`). Live argparse probe confirms.
2. **Tag-writing opt-in?** YES — **double-gated, default OFF.** CLI `--write-tags` default `False`; AND `write_serato_cues(allow_write=False default)` in `export_serato.py`. Both must be explicitly enabled.
3. **Avoids app-visual claim?** YES. `export_serato.py:25-26` docstring: *"Whether a specific Mixxx/Serato/Rekordbox build renders the pad is a human eye-check — green tests prove format conformance, not that product conclusion."*
4. **Existing cues merge-preserved?** YES. `_merge_cues` (`export_serato.py:189-196`) unions by pad index — vibemix cues win their own pads, every other pad kept. `_write_geob` (`:222-237`) keeps non-Serato GEOB frames intact.
5. **mutagen optional + lock synced?** YES. `pyproject.toml:179-181` `serato=["mutagen>=1.47"]` (comment flags GPL-2.0+, runtime dep, lazy, never vendored). Import is **lazy/function-local** inside `_read_geob`/`_write_geob`. `uv.lock` synced (`marker == "extra == 'serato'"`). The markerless `mutagen` ref at uv.lock:2192 is resolved as a transitive/sub-dependency entry, **not** a base-dep leak.
6. **Tests sufficient for byte/round-trip?** COVERED: golden-oracle exact-spec bytes (`test_cue_entry_matches_exact_spec_bytes`), inner-blob header+terminator, outer GEOB container header, unpadded-base64 decode, encode→decode field round-trip, merge-preserve, opt-in gate. **Gap:** no round-trip against a file written by **real Serato** (current fixtures are vibemix-written).
7. **Remains before app claim?** (1) Human eye-check that cues render as pads in a real Serato/Mixxx/Rekordbox build (the no-slop gate). (2) Round-trip vs a real Serato-authored Markers2 fixture. (3) GUI surface (none exists — see frontend lane).
- **Dirty remnants:** `export_serato.py` + `cue_folder.py` **clean at HEAD**; `__main__.py` dirty (~+53/-43, ~10 unrelated lanes), only one cosmetic Serato comment edit in the cue block.

### `e5c0e34e` (HEAD) — keep explicit local voice on device → ACCEPTED (source-level)
- **Files:** `src/vibemix/agent/local_tts.py`, `agent/proxy_client.py`, `agent/tts_chain.py`, `tests/agent/test_local_tts.py`, `tests/agent/test_proxy_client.py`.
- **Tests:** `uv run pytest -q tests/agent/test_local_tts.py tests/agent/test_proxy_client.py` → passed.
- **Proves (source-level):** when `VIBEMIX_LOCAL_TTS` truthy **and** the MOSS model is cached (`local_tts_enabled()` True), **both** `_build_direct_chain` (BYO-key) and `build_proxy_tts_chain` (keyless) return a MOSS-only `FallbackAdapter` and do **not** silently fall through to a paid/cloud provider. Correctly wired into BOTH builders (the chain-change contract).
- **Does NOT prove:** packaged/live MOSS readiness — no fresh PyInstaller build, no live `python -m vibemix` run, no proof the ~728MB ONNX model is cached or that synthesis produces audio on a real rig. (That is NEEDS_LIVE_PROOF.)
- **⚠️ Dirty remnants — SUBSTANTIAL and design-changing:** the working tree carries concurrent uncommitted edits that go **far beyond** `e5c0e34e`. `tts_chain.py` is being rewritten to **MOSS-only in ALL modes** (Cartesia/Gemini/OpenRouter instantiation removed) and the no-speech failure mode changed (raise `LocalTTSUnavailable`). **That is a live-voice + failure-mode change → HOLD pending Kaan ear-pass** (see moss-tts lane). `e5c0e34e` itself landed only the safe opt-in half ("keep the local voice when explicitly chosen").

---

## Dirty-tree staging map (HEAD `e5c0e34e`)

The dirty-package checker is **GREEN** — every dirty path is assigned to an Include/Hold lane (`scripts/check_dirty_package_plan.py --strict-assignments` → "every dirty path is assigned"). The shared-file collisions require **hunk-level** staging:

| File | Hunks → lane | Land disposition |
|---|---|---|
| `src/vibemix/__main__.py` | ~13 hunks / ~10 lanes (1A observability, 5C/5E/5F freshness, cue-export, 1C eval, 10 cost, 14 tts-shutdown, 15 16ch, deck-audio master) + cue Serato help-text + `:803 VIBEMIX_DROP_CALL` default | **Hunk-stage only.** Never whole-file. The `:803 setdefault('VIBEMIX_DROP_CALL','1')` hunk is HOLD (see below). |
| `src/vibemix/runtime/coach.py` | `:696-718` DROP-call speech block (HOLD) · `:195,:222-241,:628` docstring/comment (Package 9 prose, SAFE_NOW) | Split: prose hunks landable; DROP speech block HOLD. |
| `src/vibemix/state/event_detector.py` (+38) | DROP event firing path + `_drop_call_enabled` gate | **HOLD** (changes WHEN it speaks). |
| `src/vibemix/state/drop_predict.py` (+34) | `should_arm_drop_call`, `drop_call_cue`, `DROP_ARM_WINDOW_S` | **HOLD** (defines WHEN; needs grounding-review). |
| `src/vibemix/agent/tts_chain.py` / `local_tts.py` / `proxy_client.py` / `line_voice.py` | MOSS-only-in-all-modes rewrite | **HOLD** pending Kaan ear-pass (live voice + failure-mode change). |
| `tauri/ui/src/shell/app.ts` | `wireSettingsNav` dead-control **fix** | **SAFE_NOW** — land with a regression test (Board #1). |
| `tauri/ui/src/session/components/{picker,rocker,group}.ts`, `shell/shell.css` | CSS visual polish | **HOLD lane** "Frontend Shell Settings Proof" — needs visual proof before product claim. |
| `tests/*` (deck_capture, deck_signal, midi/state, drop_predict, main_smoke, tts_chain) | mixed | Stage with their owning package hunks. |

---

## Corrections to prior ground-state (recorded for the index)

1. **`ipc.library.*` is NOT pure-dead vestigial.** The frontend agent found it **conditionally both-ended** (registration gated on `if ipc_router is not None`). Reconcile with the INDEX/sweep "vestigial" claim **before** deleting any `ipc.library.*` type. The *real product path* is still Tauri `invoke()` (9 `library_*` commands both-wired, `main.rs:104-113` ↔ `api.ts`).
2. **`watchfiles` is NOT a direct vibemix dependency** — `rg 'watchfiles|watchdog' pyproject.toml` = empty. It may exist transitively in `uv.lock`, but a true watcher slice must add it to a `pyproject` extra **and** the PyInstaller specs (it ships a Rust native extension). This reconciles the checklist's "uv.lock already contains watchfiles" (transitive, not declared).
3. **13 (not 14) `FRESHNESS_GUARDED_TOOLS`** (`toolset.py:77-93` frozenset).
4. **`src/vibemix/runtime/drop_reaction.py` IS committed at HEAD** (not untracked).
5. **No event-driven fs-watcher exists** — only `parent_watchdog.py` (orphan-poll). Library freshness is poll/stat-based via 3 committed mechanisms: boot nudge (`__main__.py:1629`), 10s background poll (`staleness.py:236`), on-demand tool-call guard (`mcp_server.py:108`).

---

## What this pass does NOT cover (honest boundary)

- No live/packaged proof of anything — this is a source + unit-test verification. Final FLX4/audio/controller live acceptance and packaged-DMG behavior remain open (latest signed artifact `dist/fresh-20260601-latest/vibemix-0.0.1.dmg` predates the staleness-replay fix).
- The two HOLD-HARD items (DROP-call, MOSS-only-always) need a **grounding-review** (`vibemix-grounding-review` skill) and a **Kaan ear-pass** respectively before any land.

---

## Post-pin update — HEAD advanced to `440fcd56` during this pass

Codex landed one more commit while this verification ran (the tree was moving, as flagged):

### `440fcd56` — fix(tts): make moss the only voice source → ACCEPTED (source-level) · ⚠️ PACKAGED GATE OPEN (now a hard ship blocker)
- This is **board item H1** (MOSS-only-always TTS) landing the previously-dirty rewrite. **`Signed-off-by: Kaan Özkan`** — so the source-level design decision is Kaan-approved.
- **Files:** `agent/tts_chain.py` (−210 net; now `_build_moss_chain`), `agent/local_tts.py`, `agent/proxy_client.py`, `agent/line_voice.py`, `agent/config.py`, `agent/__init__.py` + tests (`test_tts_chain.py`, `test_tts_chain_cartesia.py`, `test_local_tts.py`, `test_proxy_client.py`, `test_line_voice.py`, `test_main_smoke.py`, `test_phase05_verification.py`).
- **Tests (re-run at `440fcd56`):** `uv run pytest -q tests/agent/test_tts_chain.py tests/agent/test_local_tts.py tests/agent/test_proxy_client.py tests/agent/test_line_voice.py tests/agent/test_tts_chain_cartesia.py tests/test_main_smoke.py` → **61 passed**.
- **Proves (source-level):** the chain is cleanly MOSS-only — module comment "no longer instantiates OpenAI, Gemini-native, or Cartesia TTS providers" (`tts_chain.py:11`); cloud kwargs are accepted-but-ignored (`tts_chain.py:41 _ = (gemini_api_key, …)`); the no-speech failure mode is **`raise LocalTTSUnavailable`** instead of routing to a cloud fallback (`tts_chain.py:59-60`). The no-paid-fallback intent is now structural, not opt-in.
- **⚠️ Does NOT prove — and this is now a HARD SHIP BLOCKER:** **`sentencepiece` is STILL absent from BOTH PyInstaller specs** (`rg sentencepiece vibemix-core.{macos,windows}.spec` = NOT-FOUND). With MOSS as the *only* voice source, a frozen build that can't load `sentencepiece` will raise `LocalTTSUnavailable` and **the packaged co-host goes silent**. Before `440fcd56`, missing-MOSS fell back to cloud; now there is no fallback. So the H1 gate is not just "nice to verify" — it must close before any packaged build ships.
- **Remaining HOLD gate (carried, now critical):** (1) add `sentencepiece` (and confirm `onnxruntime`/`tokenizers`) to BOTH PyInstaller specs; (2) Kaan **live ear-pass** (`VIBEMIX_LOCAL_TTS=1 uv run --extra ai-local python -m vibemix`) — voice quality + that it actually speaks; (3) Windows path proof; (4) confirm the ~728MB MOSS ONNX model is present/downloaded on a fresh install or the app degrades gracefully (not silently mute).
- **Net:** source design is sound and Kaan-signed; **do not cut a packaged/signed DMG until `sentencepiece` is bundled and the live ear-pass passes**, or the shipped co-host will be mute.
