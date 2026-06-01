# NEXT LAND BOARD — Current HEAD

- **Date:** 2026-06-01 · **Author:** Claude (read-only) · **HEAD:** `e5c0e34e`
- **Source of evidence:** workflow `wf_c96f6f8d-aa8` (6 lane investigations, each adversarially verified) + [`CODEX_VERIFICATION-current-head.md`](CODEX_VERIFICATION-current-head.md). Raw: [`_verification-raw-wf_c96f6f8d.json`](_verification-raw-wf_c96f6f8d.json).
- **Purpose:** rank the next slices so Codex can keep landing **clean signed commits** — SAFE_NOW first, HOLD/proof-gated items flagged so they are NOT landed by accident.
- **Posture:** anything that changes what the co-host SAYS or WHEN it speaks is HOLD until `vibemix-grounding-review` passes. Anything claiming packaged/live behavior needs fresh build/runtime proof. No board item authorizes a HOLD-lane bleed into a LAND commit.

---

## Ranked board (top 8)

### 🟢 SAFE NOW — land as clean signed commits

#### 1. Settings-nav dead-control fix + regression test
- **Lane:** Frontend (dead-button fix). Adjacent: "Hold Lane - Frontend Shell Settings Proof".
- **Disposition:** **SAFE_NOW** — the fix already exists in the dirty tree; lock it with a test.
- **Files in:** `tauri/ui/src/shell/app.ts` (the `wireSettingsNav` hunk only) + a new `tauri/ui/tests/shell/*settings-nav*.spec.ts`.
- **Files out:** `tauri/ui/src/session/components/{picker,rocker,group}.ts`, `tauri/ui/src/shell/shell.css` (CSS polish → Frontend Shell Settings Proof HOLD lane, needs visual proof).
- **Product value:** fixes a real stuck control — closing the settings drawer via its ✕ only flipped Settings-nav state one way, leaving a dead control. Direct UX win.
- **Risk:** **low** — isolated, type-safe (`subscribeSettingsUI`), pure frontend, no speech path.
- **Tests/checks:** `npm --prefix tauri/ui run build`; `npm --prefix tauri/ui test -- tests/shell/*settings-nav*` (new) + adjacent `tests/settings/drawer.spec.ts`.
- **Evidence:** `tauri/ui/src/shell/app.ts::wireSettingsNav` (dirty fix, verified by source-read; NO unit test references `wireSettingsNav` today — that's the gap to close).

#### 2. Cue-export GUI button — surface the CLI-only moat
- **Lane:** Frontend + Rust (net-new). Engine already shipped via `302d747d`/`8105b04f`.
- **Disposition:** **SAFE_NOW** for source+tests. Must claim only "export triggered", NOT "cues render in Serato" (that stays a human eye-check).
- **Files in:** `tauri/src-tauri/src/library_cmds.rs` (new `#[tauri::command]` wrapping `library cue …` / `export_cued_folder` / `tag_folder_serato`), `tauri/src-tauri/src/main.rs` (register in `invoke_handler`), `tauri/ui/src/ipc/messages.schema.json` (+ `npm run codegen:ipc`), `tauri/ui/src/library/` (button + api wrapper), a tauri vitest.
- **Files out:** the Python cue engine itself (already landed — do not re-touch `cue_folder.py`/`export_serato.py`).
- **Product value:** **high** — the auto-cue + Serato/Rekordbox/M3U8 export is the documented product **moat** and currently has **zero app surface** (`rg serato|cue-export|export-cued|cue_folder` in `tauri/ui` = NOT-FOUND; no cue `#[tauri::command]` in `library_cmds.rs`). This is the single highest-value "make the moat visible" slice.
- **Risk:** **med** — new IPC type (run `ipc-wiring-checker` — both ends must wire) + new Rust command + opt-in tag-write must stay opt-in in the UI (default no `--write-tags`).
- **Tests/checks:** `cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds`; `npm --prefix tauri/ui run check:ipc`; `npm --prefix tauri/ui test -- <new cue spec>`; `ipc-wiring-checker`.
- **Evidence:** `main.rs:104-113` (9 `library_*` commands both-wired pattern to mirror); `cue_folder.py:export_cued_folder` / `tag_folder_serato`; frontend NOT-FOUND for any cue surface.

#### 3. Glanceable library-freshness badge
- **Lane:** Frontend (net-new). Complements landed 5C/5E/5F.
- **Disposition:** **SAFE_NOW** — data already exists; this is a small read-only surface.
- **Files in:** `tauri/ui/src/shell/` (Crate/Library nav badge) reading `stats.library_freshness_status`, a tauri vitest.
- **Files out:** any change to the staleness computation (`staleness.py` is landed/clean — read-only consume).
- **Product value:** **med** — freshness exists today only as footer text + a settings banner; a prominent amber badge on the Crate/Library nav makes "your set-prep pool is stale" glanceable. Pairs with the watcher (#5).
- **Risk:** **low** — read-only display; no new backend.
- **Tests/checks:** `npm --prefix tauri/ui run build` + new vitest; visual-proof eye-check before any screenshot/launch claim.
- **Evidence:** `stats.library_freshness_status` → `library_freshness` (`__main__.py:6694-6711`, `staleness.py:88-212`); freshness currently buried (frontend lane: "surfaced as text, not a badge").

#### 4. Real-audio auto-cue eval gate
- **Lane:** Library (offline eval). Pattern mirrors "Hold Lane - Real CLAP Retrieval Eval Gate".
- **Disposition:** **SAFE_NOW** as an offline regression gate (committed fixtures, no live ONNX in CI).
- **Files in:** `scripts/eval/cue_detect.py` (new), `tests/library/fixtures/cue_real_corpus/` (small committed anchor fixtures), `tests/library/test_cue_detect_eval.py` (new).
- **Files out:** the runtime cue engine (`detect_cues_auto`) — eval only, do not modify the producer.
- **Product value:** **med** — closes `302d747d`/`8105b04f`'s biggest does-not-prove: every current cue test injects a **fake** detect fn, so the real CUE-DETR ONNX anchor quality on actual audio is unproven. This de-risks the moat before it gets a GUI (#2).
- **Risk:** **med** — needs a small, license-clean audio/anchor fixture; keep ONNX out of CI (load committed embeddings/anchors, like the CLAP eval).
- **Tests/checks:** `uv run python scripts/eval/cue_detect.py`; `uv run pytest -q tests/library/test_cue_detect_eval.py`.
- **Evidence:** `302d747d` does-not-prove ("every cue_folder test injects a fake detect; real-audio path not exercised"); existing pattern at "Hold Lane - Real CLAP Retrieval Eval Gate" (`scripts/eval/clap_retrieval.py`).

### 🟡 SOURCE-SAFE / PACKAGED-PROOF-GATED

#### 5. True event-driven library fs-watcher (P0 freshness gap)
- **Lane:** "P0 Gap - Viber Library Freshness Watcher" (checklist:2610) — REQUIRED capability, **no dirty code path yet**.
- **Disposition:** **SAFE_NOW** for the source slice + tests; **NEEDS_LIVE_PROOF** for packaged (frozen-.dmg) behavior.
- **Files in:** `src/vibemix/library/watcher.py` (new — best-effort, off-loop, debounced, degrade-to-poll), `src/vibemix/__main__.py` (wire on boot — hunk-stage), `pyproject.toml` (add `watchfiles` to an extra), the PyInstaller specs (`vibemix-core.{macos,windows}.spec` — add the watchfiles native ext), `tests/library/test_watcher.py` (new — XML mtime/content change, moved/missing tracks, cue change, debounce, stale-status propagation, Viber refusing stale set-gen).
- **Files out:** the landed poll path (`staleness.py`) — augment, don't rip out (watcher should fall back to the 10s poll if unavailable).
- **Product value:** **high** — today a DJ who re-exports Rekordbox XML or drops tracks mid-session waits up to the poll interval; `discover_pool`/`sequence_set`/`create_playlist`/`smart_hot_cues`/Viber chat are only as fresh as the index they read. This is the standout P0 from the Viber correction.
- **Risk:** **med** — must be best-effort/off-loop/never wedge live audio; degrade to poll. Packaged risk: `watchfiles` ships a **Rust native extension** that must survive PyInstaller freeze (NEEDS_LIVE_PROOF).
- **Tests/checks:** `uv run pytest -q tests/library/test_watcher.py`; then packaged proof: fresh `build_sidecar.py` + frozen-bundle smoke that the watcher loads (not just source).
- **Evidence:** checklist:2610-2658 (acceptance sketch); `staleness.py:236` (poll), `mcp_server.py:108` (tool guard), `__main__.py:1629` (boot nudge); `rg watchfiles pyproject.toml` = NOT-FOUND (must declare it).

### 🔴 HOLD — do NOT land without the named gate

#### 6. MOSS-only no-paid-fallback TTS chain — ⚠️ LANDED as `440fcd56` (source); packaged gate now a hard ship blocker
- **Lane:** "Hold Lane - Local MOSS TTS ONNX Runtime Spike" → now committed.
- **Disposition update (post-pin):** the source rewrite **landed during this pass as `440fcd56` (Kaan signed-off, 61 tests pass).** MOSS is now the **single** provider in **every** mode; the no-speech failure mode is `raise LocalTTSUnavailable` (no cloud fallback). **The HOLD did not disappear — it moved to packaging:** `sentencepiece` is STILL absent from both PyInstaller specs, so a frozen build with MOSS-only would go **silent** (`LocalTTSUnavailable`). This is now a hard ship blocker, not a "verify later".
- **Files in (when unblocked):** `agent/tts_chain.py`, `agent/local_tts.py`, `agent/proxy_client.py`, `agent/line_voice.py`, `tests/agent/test_tts_chain.py` + `sentencepiece` into BOTH PyInstaller specs.
- **Files out / blockers:** do not land while default-on-MOSS-only is unproven by ear; `sentencepiece` is **missing from both PyInstaller specs** (`rg sentencepiece vibemix-core.*.spec` = NOT-FOUND) → frozen bundle cannot synthesize; no Windows packaging proof.
- **Product value:** **high** strategically (free, never-mute, ~-76% cost — see `project_local_tts_moss_nano_benched`), but it is a *voice quality + reliability* change that only Kaan's ear can sign off.
- **Risk:** **high** — changes what the co-host sounds like live; a bad fallback = silent co-host.
- **Tests/checks (source slice only):** `uv run pytest -q tests/agent/test_tts_chain.py tests/agent/test_local_tts.py tests/agent/test_proxy_client.py`. **Then required before product claim:** `VIBEMIX_LOCAL_TTS=1 uv run --extra ai-local python -m vibemix` live ear-pass + frozen-bundle build with `sentencepiece` bundled.
- **Note:** `e5c0e34e` already safely landed the *opt-in* half ("keep the explicit local voice when chosen"). The MOSS-only-**always** behavior is the part on hold.

#### 7. DROP-call live hype line
- **Lane:** "Hold Lane - Mix Timing Oracle" / live drop timing. Dirty across `coach.py` + `event_detector.py` + `drop_predict.py`.
- **Disposition:** **HOLD — HARD.** This is net-new SPEECH: a fixed-text hype line the co-host speaks the instant the predicted-drop countdown crosses a 2s arm window. `vibemix-grounding-review` has NOT been run.
- **Why HARD hold:** `drop_predict.py` defines WHEN (the 2s `DROP_ARM_WINDOW_S`); `event_detector.py` fires a new **ceiling-priority** DROP event (WHEN it speaks); `coach.py:696-718` is the spoken surface (`mastered_speak(reaction_line(drop_cue))` then `continue`, skipping the LLM — WHAT it says). **Aggravating:** `__main__.py:803 setdefault('VIBEMIX_DROP_CALL','1')` makes it **ON BY DEFAULT** in the packaged app, contradicting the code's own "dormant by default" comment. *(UPDATE 2026-06-01 — `DRIFT-current-head.md`: commit `baeac434` flipped this OFF; at HEAD `dc4702eb` no `VIBEMIX_DROP_CALL` setdefault exists. The DROP speech block stays dirty-only, so the HARD hold still stands pending grounding-review.)*
- **Gate before any land:** (1) run `vibemix-grounding-review` (5 cardinal invariants); (2) **flip the default to OFF** or get explicit Kaan sign-off on on-by-default; (3) live-rig proof the 2s window + TTS latency actually lands the line ON the drop (not late); (4) measure `predicted_drop_in_sec` false-positive rate on real sets (a predicted drop that never lands → ungrounded "here it comes").
- **Landable sub-hunk now:** the `coach.py` docstring/comment-only hunks (`:195` reformat, `:222-241` Earned-Wall docstring, `:628` comment) are pure prose (Package 9) → SAFE_NOW if cleanly separated from the DROP speech block.
- **Product value:** high if it lands ON beat and grounded; catastrophic slop if it fires on a phantom drop. This is exactly the "real DJ friend, no AI slop" release gate.
- **Risk:** **high** (speech + timing + on-by-default).

#### 8. `BEATMATCH_GRADED` production producer
- **Lane:** "Hold Lane - Learn Beatmatch Producer Moat Plan" / Package 8 boundary.
- **Disposition:** **NEEDS_LIVE_PROOF_FIRST.** Beatmatch "Mastered" is intentionally **uncreditable** today — no production `BEATMATCH_GRADED` emitter exists (by design, masked + reality-pinned). This slice builds the owned-deck beatmatch practice loop that emits the event.
- **Files in (when built):** the engine already exists (`beatmatch_judge.grade_beatmatch` / `grade_to_event_extra`) + recognizer consumer; the missing piece is a real-time producer wired to owned-deck audio/MIDI in a practice loop, plus live proof.
- **Files out:** do not unmask stored Beatmatch mastery without the real producer (the honesty boundary in Package 8 must hold).
- **Product value:** **high** — completes the Learn/Earned "Mastered" moat for the headline competency.
- **Risk:** **high** — requires live owned-deck grading + a Mastered vocal (speech → grounding-review if the vocal changes).
- **Tests/checks:** existing `tests/learn/test_judge_credits_beatmatch.py`, `test_creditability_drift.py`; new producer tests; then live owned-deck proof.

---

## Special-attention lane summaries

| Lane | HOLD? | State | Next |
|---|---|---|---|
| **Local MOSS / no-paid-fallback TTS** | **YES** | Opt-in half landed (`e5c0e34e`). Dirty tree makes MOSS the only provider in all modes; `sentencepiece` missing from both specs; no ear-pass; no Windows proof. | Board #6 — Kaan ear-pass + spec bundling. |
| **Viber / library freshness / watch / action** | NO | **5C/5D/5E/5F + replay-on-connect all landed clean at HEAD.** 13 guarded tools. Real gaps: true watcher, cue GUI, freshness badge. | Board #5 (watcher), #2 (cue GUI), #3 (badge); + live-prove the 5F banner repaint. |
| **Runtime coach speech / slop / drop** | **YES (HARD)** | DROP-call feature = net-new speech on a 2s window; `__main__.py:803` makes it on-by-default. grounding-review not run. | Board #7 — gate hard. Only the coach.py prose hunks are SAFE_NOW. |
| **Learn / Earned Wall** | backend NO / live YES | **Live-credit spine (Packages 7/8/9) already landed + clean** (cited events credit/persist progress, emit `ipc.learn.progress_state`, fire Mastered-vocal-once, SkillWall repaints). 50 tests. | No new backend slice. Live desktop repaint proof + Board #8 (Beatmatch producer). |
| **Frontend dead buttons / Viber surface / cue-export app surface** | NO | Viber/Crate **wired** (9 `library_*` Tauri commands). Real gaps: NO cue-export GUI, NO freshness badge, NO `wireSettingsNav` test. | Board #1, #2, #3. |
| **File watcher for Viber/set-gen freshness** | NO | No event-driven watcher exists; freshness is poll/stat-based (3 committed mechanisms). `watchfiles` not a declared dep. | Board #5 (the P0). |

---

## HOLD gate register (must clear before the named item lands)

1. **DROP-call** → `vibemix-grounding-review` PASS + default flipped OFF (or Kaan sign-off) + live on-beat proof + false-positive rate.
2. **MOSS-only-always** (LANDED `440fcd56`) → **`sentencepiece` MUST be bundled in both PyInstaller specs before ANY packaged build** (else MOSS-only = silent co-host) + Kaan live ear-pass + Windows path + MOSS model present-or-degrade-gracefully.
3. **Cue-export "works in Serato"** → human eye-check in a real Serato/Mixxx/Rekordbox build (the code already refuses to claim this).
4. **fs-watcher packaged behavior** → frozen-bundle proof the `watchfiles` native ext loads.
5. **Beatmatch Mastered** → real `BEATMATCH_GRADED` producer + live owned-deck proof.
6. **Any packaged claim** → rebuild/re-sign (latest signed artifact predates the staleness-replay fix).
