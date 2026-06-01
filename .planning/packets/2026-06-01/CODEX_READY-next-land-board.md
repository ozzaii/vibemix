# CODEX_READY: Next Land Board

- **Date:** 2026-06-01 · **From:** Claude (read-only verifier) · **For:** Codex (implementer)
- **HEAD when authored:** `e5c0e34e`. **Re-pin HEAD before every pass** — the tree is moving.
- **Evidence:** [`CODEX_VERIFICATION-current-head.md`](CODEX_VERIFICATION-current-head.md) + [`NEXT-LAND-BOARD-current-head.md`](NEXT-LAND-BOARD-current-head.md) + [`_verification-raw-wf_c96f6f8d.json`](_verification-raw-wf_c96f6f8d.json).
- **Verified clean already landed (no action):** `302d747d`, `3892f4bd`, `6254c923`, `8105b04f`, `e5c0e34e` — all ACCEPTED, adversarially confirmed. The Serato writer (`8105b04f`) is opt-in/double-gated/merge-preserving/byte-conformant; only a real-Serato render eye-check remains.

---

## LAND QUEUE (clean signed commits, in order)

### L1 — `fix(tauri-ui): lock in settings-nav dead-control fix`
- **Include:** `tauri/ui/src/shell/app.ts` (the `wireSettingsNav` hunk **only**) + new `tauri/ui/tests/shell/settings-nav.spec.ts`.
- **Keep out:** `session/components/{picker,rocker,group}.ts`, `shell/shell.css` (CSS → Frontend Shell Settings Proof HOLD lane).
- **Proof:** `npm --prefix tauri/ui run build` · `npm --prefix tauri/ui test -- tests/shell/settings-nav.spec.ts tests/settings/drawer.spec.ts`.
- **Why:** closes a real stuck control (✕-close left Settings-nav one-way). No test references `wireSettingsNav` today.

### L2 — `feat(tauri): surface cue-export in the app (GUI button)`
- **Include:** `tauri/src-tauri/src/library_cmds.rs` (new `#[tauri::command]` → `library cue` / `export_cued_folder`), `tauri/src-tauri/src/main.rs` (register), `tauri/ui/src/ipc/messages.schema.json` (**then `npm run codegen:ipc`** — also stage `messages.ts` + `validator.generated.mjs`), `tauri/ui/src/library/` (button + api), new tauri vitest.
- **Keep out:** `src/vibemix/library/cue_folder.py`, `export_serato.py` (already landed — do not re-touch).
- **Proof:** `cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds` · `npm --prefix tauri/ui run check:ipc` · run `ipc-wiring-checker` (both ends MUST wire) · new vitest.
- **Constraint:** UI default must NOT pass `--write-tags` (Serato tag-write stays opt-in). Claim "export written", never "cues show in Serato".
- **Why:** the auto-cue/Serato/Rekordbox/M3U8 **moat** is CLI-only — `rg serato|cue-export|export-cued|cue_folder tauri/ui` = NOT-FOUND.

### L3 — `feat(tauri-ui): glanceable library-freshness badge`
- **Include:** `tauri/ui/src/shell/` (badge reading `stats.library_freshness_status`) + new vitest.
- **Keep out:** `src/vibemix/library/staleness.py` (landed — read-only consume).
- **Proof:** `npm --prefix tauri/ui run build` + new vitest; eye-check before any screenshot claim.
- **Why:** freshness exists only as footer text + settings banner; pairs with L5.

### L4 — `test(library): real-audio auto-cue eval gate`
- **Include:** `scripts/eval/cue_detect.py` (new), `tests/library/fixtures/cue_real_corpus/` (small committed anchors, license-clean), `tests/library/test_cue_detect_eval.py` (new).
- **Keep out:** the runtime `detect_cues_auto` producer (eval only). Keep ONNX out of CI (load committed anchors, mirror `scripts/eval/clap_retrieval.py`).
- **Proof:** `uv run python scripts/eval/cue_detect.py` · `uv run pytest -q tests/library/test_cue_detect_eval.py`.
- **Why:** every current cue test injects a **fake** detect — real CUE-DETR anchor quality is unproven; de-risk the moat before L2 ships its GUI.

### L5 — `feat(library): event-driven freshness watcher` (source slice; packaged proof deferred)
- **Include:** `src/vibemix/library/watcher.py` (new — best-effort, off-loop, debounced, **degrade-to-poll**), `src/vibemix/__main__.py` (boot wiring — **hunk-stage only**), `pyproject.toml` (add `watchfiles` to an extra), `vibemix-core.{macos,windows}.spec` (add the watchfiles native ext), `tests/library/test_watcher.py` (new).
- **Keep out:** the landed `staleness.py` poll (augment, never rip out — fall back to it).
- **Proof (source):** `uv run pytest -q tests/library/test_watcher.py` (XML mtime/content, moved/missing tracks, cue change, debounce, stale-status propagation, Viber refusing stale set-gen).
- **Deferred / NEEDS_LIVE_PROOF:** frozen-bundle smoke that `watchfiles` (Rust native ext) loads in the packaged app. Do NOT claim packaged watcher behavior from source tests.
- **Why:** the P0 freshness gap (checklist:2610). `watchfiles` is NOT a declared dep yet — must add it.

---

## HOLD QUEUE — DO NOT land without the gate

### H1 — MOSS-only no-paid-fallback TTS chain `[LANDED 440fcd56 (source) · PACKAGED GATE = HARD BLOCKER]`
- **Update:** landed during the verification pass as `440fcd56 fix(tts): make moss the only voice source` (Kaan signed-off, 61 tests pass). MOSS is now the **only** provider in **all** modes; no-speech → `raise LocalTTSUnavailable` (no cloud fallback).
- **NEXT ACTION (do this before any packaged/signed build):** add `sentencepiece` to BOTH `vibemix-core.{macos,windows}.spec` (currently NOT-FOUND → a frozen MOSS-only build goes **silent**) and confirm `onnxruntime`/`tokenizers` are bundled. Suggested: `fix(packaging): bundle sentencepiece for MOSS-only TTS`.
- **Then:** Kaan live ear-pass (`VIBEMIX_LOCAL_TTS=1 uv run --extra ai-local python -m vibemix`) + Windows path + MOSS model present-or-degrade-gracefully (not silently mute on a fresh install).

### H2 — DROP-call live hype line `[HOLD: HARD — grounding-review]`
- Net-new SPEECH: fixed line spoken on the 2s drop-arm window. `coach.py:696-718` (WHAT) + `event_detector.py` ceiling-priority DROP event (WHEN) + `drop_predict.py` `DROP_ARM_WINDOW_S` (WHEN).
- **Aggravating:** `__main__.py:803 setdefault('VIBEMIX_DROP_CALL','1')` = **ON BY DEFAULT**, contradicting the "dormant" comment.
- **Gate:** (1) `vibemix-grounding-review` PASS; (2) flip default to OFF or explicit Kaan sign-off; (3) live on-beat proof (2s window + TTS latency lands ON the drop); (4) `predicted_drop_in_sec` false-positive rate on real sets.
- **Landable now:** only the `coach.py` prose hunks (`:195`, `:222-241`, `:628`) — pure Package 9 docstring/comment — if cleanly separated from the DROP speech block.

### H3 — `BEATMATCH_GRADED` producer `[NEEDS_LIVE_PROOF_FIRST]`
- Beatmatch Mastered is intentionally uncreditable (masked, reality-pinned). Engine + recognizer exist; the real-time owned-deck producer + live proof do not. Do NOT unmask stored mastery without the producer.

---

## Shared-file hunk-staging recipe (mandatory — concurrent sessions on one tree)

`git add -p` is unavailable here. For shared files (`src/vibemix/__main__.py`, `coach.py`):
1. `git diff <file>` → write a filtered patch containing **only your slice's hunks** (drop everyone else's).
2. `git apply --cached --recount <your.patch>`.
3. **Verify before commit:** `git diff --cached --name-only` matches your intended set AND `git diff --cached <shared-file>` shows only your hunks.
4. Commit. (Atomic message-only fix if nothing else staged: `git commit --amend -m "…"`.)

**`__main__.py` hunk map at HEAD `e5c0e34e`:** ~13 hunks across ~10 lanes. The cue Serato help-text hunk → cue-export. The `:803 VIBEMIX_DROP_CALL` default hunk → **HOLD (H2)**. Freshness/observability/cost/tts-shutdown/16ch/deck-audio hunks → their own packages. **`coach.py`:** `:696-718` DROP block = HOLD (H2); `:195/:222-241/:628` prose = SAFE.

## Standing rules
- Re-run `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary` after each commit — keep it GREEN.
- `messages.schema.json` edit → `npm run codegen:ipc` (validator is pre-compiled) → stage schema + generated TS together.
- `ipc.library.*` is **conditionally** both-ended (gated on `if ipc_router is not None`) — reconcile before deleting any such type; the real library path is Tauri `invoke()`.
- Any packaged claim → rebuild/re-sign (latest signed artifact `dist/fresh-20260601-latest/vibemix-0.0.1.dmg` predates the staleness-replay fix).
- No spoken fallback/slop ships. Guarded/eval-only text may be logged, never voiced.
