# KAAN-ACTION-LEGAL — Phase 29 Cross-Platform Smoke (NON-BLOCKING)

These items require Kaan-touch — Apple + Windows physical access in
particular — and were deferred from the autonomous Phase 29 execution
per `gsd-autonomous fully` mode. Phase 29 code-completion is unblocked;
release-gate verdict (SHIP/BLOCK/REWORK) requires these items closed.

## Source: Phase 29 Plan 29-08 Task 2 — Cross-platform manual smoke

**Plan:** `.planning/phases/29-post-session-debrief-mvp-ui/29-08-PLAN.md`
**Verdict template:** `.planning/phases/29-post-session-debrief-mvp-ui/29-CROSS-PLATFORM-VERDICT.md`

### Action items

1. **MAC-SMOKE-001 — macOS E2E debrief smoke checklist**
   - Run: `cd tauri && npm run tauri build --debug && ./target/debug/vibemix`
   - Walk: `tests/e2e/test_debrief_e2e_macos_smoke.md` (19 steps)
   - Save screenshot: `.planning/phases/29-post-session-debrief-mvp-ui/screenshots/macos-debrief-window.png`
   - Fill in PASS/FAIL per step in the checklist md
   - Mark `MAC-SMOKE-001` as `done` here when complete

2. **WIN-SMOKE-001 — Windows VM E2E debrief smoke checklist**
   - Boot Windows 11 VM (Parallels / UTM / VMware)
   - Build vibemix.exe via `cargo build` OR copy CI artifact
   - Walk: `tests/e2e/test_debrief_e2e_windows_smoke.md` (19 steps)
   - Save screenshot: `.planning/phases/29-post-session-debrief-mvp-ui/screenshots/windows-debrief-window.png`
   - Fill in PASS/FAIL per step
   - Mark `WIN-SMOKE-001` as `done` here when complete

3. **VERDICT-001 — Cross-platform verdict consolidation**
   - Open `.planning/phases/29-post-session-debrief-mvp-ui/29-CROSS-PLATFORM-VERDICT.md`
   - Fill in Pitfall 1 verdict (MP3 plays both WebViews)
   - Fill in Pitfall 5 verdict (WaveSurfer parity — DEFERRED is OK
     because the placeholder timeline meets DEBRIEF-05 functionally)
   - Final release decision: SHIP / BLOCK / REWORK
   - If REWORK, enumerate gaps and create gap-closure plan via
     `/gsd-plan-phase 29 --gaps`
   - Sign + date

4. **POLISH-OPT-001 — wavesurfer.js install (OPTIONAL, polish wave)**
   - `cd tauri/ui && npm install wavesurfer.js@^7.12.7`
   - Replace `mountTimelinePlaceholder` calls in
     `src/debrief/debrief-window.ts` with a real WaveSurfer instance
     mounting `voice.wav` via `convertFileSrc`. The placeholder div
     `#vmx-debrief-waveform` is already sized so the swap-in is
     drop-in (layout-stable).
   - The placeholder regions surface meets DEBRIEF-05 functionally;
     real waveform is a visual upgrade only.

## Non-blocking note (per gsd-autonomous fully)

Autonomous execution finished Plans 29-01 through 29-07 + Plan 29-08
Task 1 (3 automated e2e pytest files, 6 tests, all pass). Plan 29-08
Task 2 (manual smoke) is the only outstanding work for the phase.
Kaan can either:

- Run the smoke now (1-2 hours estimated) → Phase 29 ships
- Run the smoke at a less load-bearing moment → Phase 29 stays in
  "ready-to-ship-pending-smoke" state; subsequent phases proceed
  without dependency on this verdict

## Source: Phase 30 SENSE-20 — Hard Tek reference corpus

**Plan:** `.planning/phases/30-2-hard-tek-detectors-distortion-climb-acid-line-entry/30-04-PLAN.md`
**Status:** Non-blocking — synthetic fixtures cover both detectors in CI;
real-track F1 scoring waits on Kaan's curation pass.

### Action items

5. **HARDTEK-CORPUS-001 — Commit 5 CC-licensed Hard Tek anchor tracks**
   - Source per `eval/corpus/LICENSES.md` policy: archive.org / CCMixter /
     FMA (CC-BY / CC-BY-SA only).
   - Per-track WAV → `eval/corpus/hard_tek/audio/<slug>.wav` (16kHz mono
     resampled — `scripts/tune_detectors.py` does this on read).
   - Per-track sidecar JSON → `eval/corpus/hard_tek/<slug>.json` with
     `expected_fires: [{type, t_seconds_estimate}, ...]` for F1 scoring.
   - Update `eval/corpus/hard_tek/README.md` curated set table with
     real title / artist / BPM / length / license / why-included.
   - Unblocks the F1 ≥ 0.80-per-detector gate (Phase 27 EVAL-03 matrix)
     for the hard_tek genre slice. Until then the F1 number is reported
     against synthetic fixtures only.

## Source: Phase 35 ASSETS-01..07 — Real GLBs + 30s demo film

**Phase:** `.planning/phases/35-real-glb-animations-30s-viral-demo-film/`
**Plans:** 35-01 .. 35-06 (autonomous deliverables shipped; assets pending Kaan-action)
**Status:** Phase 35 pipeline + CI gates + docs landed. Real GLBs + demo.mp4 + VO
are the remaining work. Autonomous test surface uses synthetic fixtures.

### Action items

6. **ASSETS-MESHY-A/B — Generate Meshy v6 vs Hunyuan3D 3.0, pick winner**
   - Budget: ~$50 in credits across the two services.
   - Generate ONE shot from each per `docs/asset_pipeline.md` § 1.
   - Compare on silhouette readability @ 320×320, bone topology
     (Mixamo-friendly biped), texture density (KTX2 tolerance).
   - Pick winner. Stash raw GLB to `tauri/ui/assets/mascot/raw/`
     (gitignored — keeps per-iteration noise out of git history).
   - Mark `ASSETS-MESHY-A/B` as `done` here when winner is staged.

7. **ASSETS-MIXAMO-RIG — Mixamo auto-rig + 8-12 motion clip selection**
   - Mixamo (free with Adobe account): upload winner GLB, place rig
     markers, auto-rig (~30s server-side).
   - Per the 5 prep_* state map in `docs/asset_pipeline.md` § 2:
     pick the Mixamo motion clip that fits each state, trim to
     0.8-1.5s, "In Place" enabled.
   - SkeletonHelper QA per `docs/asset_pipeline.md` § 3: visually
     verify no bone drift / foot penetration / hand intersection /
     spine pop. If any fail → Rokoko Studio retargeting fallback
     ($5/mo, see Pitfall P61).
   - Mark `ASSETS-MIXAMO-RIG` as `done` here when all 5 prep_* +
     any new react_* clips pass SkeletonHelper QA.

8. **ASSETS-PREP-REPLACE — Replace 5 prep_*.glb placeholders with real GLBs**
   - Run `python scripts/glb_optimize.py --optimize tauri/ui/assets/mascot/raw/ tauri/ui/assets/mascot/animations/` to DRACO + KTX2 compress.
   - Verify gates:
     - `./scripts/check_mascot_glb_size.sh` (≤ 25 MB total).
     - `python scripts/glb_optimize.py --check tauri/ui/assets/mascot/` (≤ 600 KB per animation clip + total).
     - `cd tauri/ui && npm test -- additive-layer` (Phase 22-02 idle-zero contract — bone-level).
     - `pytest tests/repo/test_phase_22_02_prep_glb_contract.py` (structural).
   - Filenames MUST be drop-in same-name overwrite. The 5 prep_* names
     are the manifest contract surface.
   - Mark `ASSETS-PREP-REPLACE` as `done` here when all 4 gates pass.

9. **ASSETS-SESSION-RECORD — Record 3min+ raw DJ session**
   - Follow `scripts/demo_film/recording_protocol.md` checklist.
   - Setup: vibemix live, BlackHole 2ch, DDJ-FLX4 (or any v0.1
     supported controller), djay Pro / Mixxx, Quartz screen capture
     scoped to the DJ window.
   - 3 minutes minimum, 1080p+, 60fps preferred, 48kHz stereo direct
     from BlackHole (not mic).
   - Stash to `scripts/demo_film/raw/dj_session_<YYYY_MM_DD>.mov`
     (gitignored — kept locally, demo.mp4 is the shipped artifact).
   - Mark `ASSETS-SESSION-RECORD` as `done` here when raw is stashed
     + reviewed for "real DJ friend" energy.

10. **ASSETS-DEMO-CUT — Manual ffmpeg cut to 30s demo.mp4**
    - Plan cuts per `scripts/demo_film/3beat_structure.md` (Beat A
      overlay highlight → Beat B mascot lean-in BEFORE voice → Beat C
      cited reaction). Hard ceiling 8 cuts (Pitfall P57).
    - Populate `scripts/demo_film/cuts.json` with cut objects:
      `{id, start, end}`. Map each id to beat_a_* / beat_b_* / beat_c_*.
    - Validate: `bash scripts/demo_film/cut.sh --dry-run`.
    - Produce: `bash scripts/demo_film/cut.sh`.
    - Output: `docs/assets/demo.mp4`.
    - Update README hero block: replace `sha256=PLACEHOLDER` with
      `sha256=$(shasum -a 256 docs/assets/demo.mp4 | cut -d' ' -f1)`.
    - Verify: `python scripts/check_readme_hero_hash.py` exits 0.
    - Mark `ASSETS-DEMO-CUT` as `done` here when the hero hash gate
      passes locally + the README renders the new asset on GitHub.

11. **ASSETS-VO — Voiceover (Kaan/Francesco-written + recorded OR no-VO)**
    - Default per `scripts/demo_film/vo_policy.md`: NO VO (captions
      carry the narrative).
    - If a VO is added: Kaan or Francesco writes the copy (3 sentences
      max), Kaan or Francesco records it in one take. Imperfection is
      the feature.
    - NO ElevenLabs, NO OpenAI TTS, NO Gemini TTS, NO synthesized
      narration (Pitfall P58 — enforced by
      `tests/scripts/test_demo_film_no_ai_vo.py` grep gate).
    - If using VO: set `vo_track` in `cuts.json` to the local path
      (e.g. `scripts/demo_film/raw/vo_take_01.wav`).
    - Mark `ASSETS-VO` as `done` here when final decision is made +
      (if VO) committed to local raw/ + `vo_track` set in cuts.json.

---

## Phase 36 — Day-Zero Operations

Real-world execution items that vibemix autonomously scaffolded scripts for but
that Kaan / Francesco / Bravoh team must run themselves.

### OPS-09-RUN — Discord server creation
- Generate a Discord bot token at https://discord.com/developers/applications.
- Set `DISCORD_BOT_TOKEN` env locally.
- Dry-run first: `python scripts/dayzero/discord_provision.py --dry-run`.
- Live: `python scripts/dayzero/discord_provision.py --live`.
- Verify: roles (founder, contributor, DJ, lurker) + channels (#announcements,
  #help, #show-and-tell, #controllers, #ai-misbehavior, #dev) exist.
- Mark `done` here once Discord server is up + bot kicked-and-removed.

### OPS-10-RUN — Live 100 RPS proxy load test
- Coordinate with Bravoh team — could DDOS prod if mistimed.
- Pre-flight: confirm api.altidus.world/vibemix has rate-limit headroom.
- Run: `python scripts/dayzero/proxy_load_test.py --target https://api.altidus.world/vibemix --duration 300 --rps 100`.
- Verify: artifact under `.planning/eval-runs/loadtest_<ts>.json`; p99 < 500ms; error rate < 1%.
- Mark `done` here when verdict = PASS.

### OPS-11-CRON — Healthz watchdog cron install
- Bravoh sysadmin installs `*/5 * * * *` cron entry per
  `scripts/dayzero/healthz_cron.example` on the Bravoh server.
- Required env vars set in cron: `DISCORD_WEBHOOK_URL`, `HEALTHZ_URL`.
- First failure-mode test: temporarily stop the healthz endpoint → confirm
  Discord webhook fires within 5 minutes.
- Mark `done` here after Discord alert verified.

### OPS-12-OUTREACH — Aligned-community star sourcing
- Read `scripts/dayzero/seed_stars.md` protocol.
- Outreach manually across 4 pools (Bravoh team, DJ network, ARRAY OSS,
  contributor circle). NO random friend-favors (Pitfall P59).
- Log targets in `scripts/dayzero/seed_stars.log` (gitignored).
- Target: ≥15 confirmed Day-1 stars before launch.
- Mark `done` here when ≥15 names confirmed.

### OPS-13-EXECUTE — Launch trigger execution
- Recommended slot: 09:00 EST (Pitfall P78 timing).
- Required env: `GH_TOKEN`, `DISCORD_WEBHOOK_URL`, `RELEASE_TAG`, `REPO`.
- Dry-run preview: `bash scripts/dayzero/launch_trigger.sh` (no --publish).
- Live: `bash scripts/dayzero/launch_trigger.sh --publish`.
- 4 stages run in sequence: T-30 → T+0 → T+5 → T+24h.
- Cross-post copies from `scripts/dayzero/launch_copy/{twitter,instagram,linkedin,reddit}.txt`.
- Mark `done` here when T+24h recap posts successfully.

### OPS-14-SERVER — Bravoh ops endpoint deployment
- Bravoh team deploys `POST /vibemix/updates/upload` per
  `docs/bravoh-ops-endpoint.md`.
- Bravoh team deploys `GET /vibemix/updates/latest.json` feed.
- Bravoh team deploys `GET /vibemix/healthz` endpoint.
- Issue `BRAVOH_UPDATE_TOKEN` for CI → upload at one-token-per-release rotation.
- Mark `done` here when all 3 endpoints respond 200 OK on smoke check.
