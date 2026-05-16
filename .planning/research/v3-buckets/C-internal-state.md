# C — Internal State: Severity-Classified Inventory for v3 Clean Ship

**Audit date:** 2026-05-16
**Auditor:** read-only Claude (gsd-quick agent — no file modifications)
**Scope:** v2.1 shipped 2026-05-16 with `status: tech_debt`. This audit surfaces every owed item that blocks a clean public OSS v3 ship — carveouts, fragile surfaces, unshipped POC IP, expired overrides, visual gaps, and stability surfaces v3 must not touch.
**Sources read:** STATE.md, PROJECT.md, both KAAN-ACTION-LEGAL.md files (root + .planning), KAAN-ACTION-PROXY.md, v2.1-MILESTONE-AUDIT.md, HANDOFF-cdj-whisper-v5-ui-migration.md, signpath-application.md, 5 memory files (v4 canonical, v3 POC, mic-as-Part, v4_tr lookahead, v0.1.0-rc1 bugs), 4 flagged Phase SUMMARYs (33/35/38/39), the 3 untracked POC files (cohost_v3.py, cohost_v4.py, cohost_v4_tr.py), shipped `src/vibemix/` modules (constants, prompts, dj_cohost, tts_chain, coach), POC immutability gate, GLB asset bundle, mascot animations dir, demo asset surface, tokens.css.

---

## TL;DR — Top 10 Issues Blocking Clean v3 Ship

| # | Severity | Issue | Surface |
|---|----------|-------|---------|
| 1 | **P0** | Apple Developer Program Agreement update (DIST-09 / Francesco) — gates every signed macOS build | external clock |
| 2 | **P0** | SignPath OSS Foundation approval (DIST-11 / Kaan, ~1-week SLA) — gates every signed Windows build | external clock |
| 3 | **P0** | Mic-as-2nd-Gemini-Part NOT shipped (rule: `feedback_mic_audio_as_multimodal_part`) — shipped `dj_cohost.py:335` sends ONE Part labelled "mix + mic" instead of v4's TWO separate Parts | `src/vibemix/agent/dj_cohost.py:332-340` vs `cohost_v4.py:1791-1813` |
| 4 | **P0** | 5 `prep_*.glb` mascot animations are stub placeholders (~56KB each vs Mixamo's 400KB-1.2MB); `PLACEHOLDER_NOTE.md` lives next to them; first impression on launch hero is degraded | `tauri/ui/assets/mascot/animations/prep_*.glb` |
| 5 | **P0** | `docs/assets/demo.mp4` does NOT exist; README hero hash sentinel `sha256=PLACEHOLDER` is shipping; OSS launch needs a real hero video before tweet/IG drops | `docs/assets/` (missing) + ASSETS-PROD-DEMO |
| 6 | **P1** | 3s file-based lookahead pipeline (LookaheadProvider — nowplaying-cli + mdfind + ffmpeg → 3rd audio Part) is in `cohost_v4_tr.py:624-779` but NOT ported — offsets the 5-10s LLM+TTS staleness | `cohost_v4_tr.py:624` vs no shipped equivalent |
| 7 | **P1** | Real PGP key for `security@bravoh.com` (SEC-06-PGP) — placeholder shipped; SECURITY.md will point at a non-existent key when public | `KAAN-ACTION-LEGAL.md §1` |
| 8 | **P1** | Real Tauri ed25519 updater key (TAURI-UPDATER-KEY) — placeholder shipped Phase 18; auto-update will fail on first signed release without rotation | `KAAN-ACTION-LEGAL.md §4` |
| 9 | **P1** | Phase 16 ear-test memory override EXPIRES post-v2.1 (P85); v3 has no hallucination-gate strategy chosen yet — restore Kaan-ear-only OR permanently adopt 2-judge proxy | `.planning/STATE.md:69` + `cut_release.sh:159` |
| 10 | **P2** | Sidecar bundle at `tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/` is from BEFORE the line-buffer + parent-watchdog fixes (per `project_v0_1_0_rc1_open_bugs`); needs `scripts/build_sidecar.py` re-run before next artifact | `tauri/src-tauri/binaries/` |

**All P0s except #3 are by-design Kaan-action.** #3 is the only engineering-side anti-slop gap large enough to risk the launch quality bar; the others are mechanical / external-clock items.

---

## 1. KAAN-ACTION-LEGAL — 15 Carveouts Discharge Readiness Table

Source: `/Users/ozai/projects/dj-set-ai/KAAN-ACTION-LEGAL.md` (578 lines, the root authoritative copy — note `.planning/KAAN-ACTION-LEGAL.md` is a phase-scoped subset from Phase 29 only and is stale relative to root).

Categories per `gsd-autonomous fully` mode at v2.1 close:

| # | ID | Category | Blocked-by-External-Clock? | v3 Pre-Stage Opportunity | One-Line Discharge Plan |
|---|-----|----------|---------------------------|--------------------------|------------------------|
| 1 | **DIST-09** | legal_capacity (P46) | YES — Apple Dev Program | Francesco signs the updated Agreement at App Store Connect; populate `APPLE_DEVELOPER_ID_*` secrets in GH | Francesco: log in → Account → review + accept → confirm via Kaan |
| 2 | **DIST-11** | legal_capacity (P46) | YES — SignPath OSS (~1wk SLA) | Submit form per `signpath-application.md` Day 1 of v3; field-by-field already written | Kaan: signpath.io/solutions/open-source-community → paste verbatim → wait |
| 3 | **DIST-19** | post_approval_mechanical | Cascades from #1 + #2 | Build first signed binary in v3 → run `scripts/verify_signed.py --require-signed` smoke | Auto-fires once `dist/*.dmg` + `*.msi` exist; verifier already wired |
| 4 | **SEC-06-PGP** | post_approval_mechanical | NO — pure Kaan-action | **Pre-stage opportunity:** generate gpg key + publish to `keys.openpgp.org` BEFORE first public push | `gpg --gen-key` → ascii export → commit to SECURITY.md → upload to keyserver |
| 5 | **TAURI-UPDATER-KEY** | post_approval_mechanical | NO — pure Kaan-action | **Pre-stage opportunity:** rotate ed25519 keypair, update `tauri.conf.json5` + GH secret before first signed release | `tauri signer generate` → commit pubkey → GH secret `TAURI_PRIVATE_KEY` |
| 6 | **INSTALL-VM-RUN** | real_hardware | Cascades from #1 (need signed bin) | Once #1+#2 land, run `tart` macOS 12.3/14/15 + Win 10/11 matrix per `scripts/install_rehearsal/` | Spin VMs → install signed bin → walk wizard → screenshot |
| 7 | **INSTALL-60S-CHECK** | real_hardware | Cascades from #6 | Stopwatch `onboarding-flow.ts` total time on each VM | Visual: `onboarding-stopwatch.ts` already emits per-step timings |
| 8 | **INSTALL-BLACKHOLE-PROBE** | real_hardware | Independent | **Pre-stage opportunity:** fresh-Mac probe today; `vibemix.install.blackhole_probe` already builds the install-affordance | Kaan: fresh user account → run wizard → confirm BlackHole CTA fires |
| 9 | **INSTALL-DEFENDER** | real_hardware (external) | YES — 1-2 wk after SignPath chain | None — propagation is outside direct control | Wait 1-2 wk post-#2 + signed builds; monitor Defender reputation |
| 10 | **SHIP-CUT** | customer_facing_publish | YES — gated on #1+#2 secrets | Engineering: run `cut_release.sh` Gates 1+3+4+5+6 every CI commit (already green; Gate 2 = signed-binary gate flips when secrets land) | `gh release create v3.0.0-rc1 --draft` once `cut_release.sh` prints command |
| 11 | **SHIP-TWEET** | customer_facing_publish | Cascades from #10 | **Pre-stage opportunity:** draft + review 5-channel copy NOW; `scripts/dayzero/launch_copy/{twitter,instagram,linkedin,reddit}.txt` already exist | Kaan + Francesco review → sign-off on copy file → ship on launch day |
| 12 | **SHIP-DISCORD** | customer_facing_publish | Cascades from #10 | Run `scripts/dayzero/discord_provision.py --dry-run` BEFORE launch; provision OPS-09 first | Need: Discord bot token; provision then post via `--real` + `LAUNCH_REAL=1` |
| 13 | **SHIP-TRANSFER** | customer_facing_publish | YES — bravoh GH org standup needed | **Pre-stage opportunity:** stand up `bravoh` GH org NOW (Bravoh Enterprise had 0 orgs + billing flag per signpath-application.md) — independent of vibemix | `gh api repos/ozzaii/vibemix/transfer -F new_owner=bravoh` (when org exists) |
| 14 | **SHIP-ROTATE** | customer_facing_publish | Cascades from #10 | Read `docs/launch-rotation.md` (24h hourly schedule); confirm Bravoh team availability | Schedule via team comms; existing doc is the SOP |
| 15 | **SHIP-V1-DECISION** | customer_facing_publish | ~2-week bake after #10 | None — by-design bake window | Kaan signs off after RC1 metrics: cut v1.0.0 / cycle RC2 / pause |

**+ASSETS-PROD-GLB (counted as legal but actually real-asset-production):** 5 real Meshy v6 / Hunyuan3D Mixamo-rigged GLBs. Memory `project_mascot_as_vtuber_personality_surface` notes Kaan has the "Neon Rebel" Meshy bundle in hand at `/Users/ozai/Downloads/Meshy_AI_Neon_Rebel_biped/` (base GLB + 20 separate skinned animations) — **the bottleneck here is Mixamo retargeting + glb_optimize.py compression, NOT generation.** Per-clip 600 KB / total 25 MB CI gate enforces.

**+ASSETS-PROD-DEMO:** 30s demo.mp4 cut from 3min+ raw DJ session. Memory `project_v4_canonical_baseline` confirms Kaan is actively DJing real sessions with v4; recording protocol is `scripts/demo_film/recording_protocol.md` (3-beat structure ≤8 cuts).

**Discharge readiness verdict:**
- **2 hard external blockers** (DIST-09 + DIST-11) gate the entire signed-binary path. Submit applications Day 1 of v3.
- **5 pre-stage opportunities** are immediately discharge-able without external dependencies: SEC-06-PGP (#4), TAURI-UPDATER-KEY (#5), INSTALL-BLACKHOLE-PROBE (#8), SHIP-TWEET copy review (#11), SHIP-TRANSFER bravoh org standup (#13).
- **3 cascading items** auto-fire once the 2 hard blockers land (DIST-19, INSTALL-VM-RUN, INSTALL-60S-CHECK).
- **5 items wait on the customer-facing launch slot** itself (SHIP-CUT, SHIP-TWEET, SHIP-DISCORD, SHIP-ROTATE, SHIP-V1-DECISION).

---

## 2. v2.1 Tech_Debt by Phase — Fragility Map (P27–P39)

Per `v2.1-MILESTONE-AUDIT.md` §8.4 categories. P0 = blocks ship, P1 = degrades UX, P2 = polish, P3 = nice-to-have.

### Phase 27 — Eval Harness + v2.0 Carry-Forward (passed, 140 tests)

| Item | Severity | What works | What's fragile |
|------|----------|-----------|----------------|
| 20 of 40 Achird OPUS ack-bank files | **P2** | 20 generated; ack-bank picks from those | Gemini TTS quota; ~$0.10 to fill remaining; failure: ack pool smaller than intended → slightly more repeats |
| VCR cassettes | **P2** | Tests mock | One-time `VCR_RECORD_MODE=new_episodes` run; failure: CI runs spend real Gemini cost on first PR |
| EVAL-CORPUS-WAVS (6 × 30min public-domain WAVs, 200MB git-LFS) | **P2** | Synthetic fixtures cover CI | Real-corpus F1 numbers unmeasured outside synthetic |
| 2-judge cross-check (Pro + Flash, different rubrics) — **the autonomous hallucination gate that substitutes for Phase 16** | **P0 if override expires** | Wired into `eval.yml` CI; 3/3 e2e tests pass on the integration seam | P85 expires post-v2.1; v3 must explicitly decide: restored Kaan-ear-only OR permanent autonomous adoption (see §4 below) |

### Phase 28 — Library Intelligence v1 (passed, 258 tests)

| Item | Severity | Status |
|------|----------|--------|
| Bravoh proxy production probe (BRAVOH-PROXY-PROBE) | **P1** | `MOCK_PROXY_FOR_DEV=1` in dev — real-host probe deferred. Failure mode: first prod request from a real client could 401 / schema-mismatch undetected. |
| `responseSchema` proxy passthrough (A7) | **P1** | KAAN-ACTION-PROXY entry — debrief drills have Pydantic JSON post-hoc fallback, so non-blocking. |
| €50/month CI cost gate | **P2** | `test_monthly_projection_under_50_eur` has only ~€0.5 headroom per Phase 28-08 review. If call-rate constants drift, CI flaps. |

### Phase 29 — Post-Session Debrief MVP UI (passed)

| Item | Severity | Status |
|------|----------|--------|
| Achird voice quality at 60-90s (A5-VOICE-LISTEN) | **P2** | Single-line swap to `Kore` voice if FAIL per `src/vibemix/debrief/tldr.py`; e2e tests assert MP3 plays, not voice quality. |
| MAC-SMOKE-001 (19-step macOS smoke) | **P2** | Engineering green; manual checklist deferred. |
| WIN-SMOKE-001 (Windows VM smoke) | **P2** | Same as above. |
| WaveSurfer.js real timeline (POLISH-OPT-001) | **P3** | Placeholder regions meets DEBRIEF-05 functionally; visual upgrade only. |

### Phase 30 — 2 Hard Tek Detectors (passed, 45 tests)

| Item | Severity | Status |
|------|----------|--------|
| HARDTEK-CORPUS-001 — 5 CC-licensed Hard Tek anchor tracks | **P2** | Synthetic fixtures cover CI; real-track F1 unmeasured. Failure mode: detectors may misfire on real Hard Tek if synthetic distortion profile drifted. |

### Phase 31 — 4-Layer Mascot Additive (passed, 17 tests, GLB bundle 21.67/25 MB)

No deferred items. Engineering green. **GLB bundle is THE main mascot assets are real**, but the 5 `prep_*.glb` files inside are placeholders (see Phase 35 below).

### Phase 32 — Long-Term DJ Profile (passed, 67 tests)

No deferred items. P51 / P53 / P60 privacy gates enforced. Engineering green.

### Phase 33 — One-Click Install Hardening (human_needed, 50 tests)

| Item | Severity | Status |
|------|----------|--------|
| INSTALL-VM-RUN (fresh-VM matrix) | **P0** | Engineering scaffold double-gated; real `tart` runs require Mac + signed bin |
| INSTALL-60S-CHECK (stopwatch onboarding ≤60s) | **P1** | Cascades from INSTALL-VM-RUN |
| INSTALL-BLACKHOLE-PROBE (fresh-Mac probe) | **P1** | Independent of external clock — pre-stage opportunity |
| INSTALL-DEFENDER (SmartScreen reputation propagation) | **P1** | External, 1-2 wk post-SignPath chain |

### Phase 34 — Open-Source Security Pass (passed, no VERIFICATION.md, 63 tests)

| Item | Severity | Status |
|------|----------|--------|
| Missing VERIFICATION.md | **P3** | SUMMARY.md confirms status; planning-discipline gap, not engineering |
| SEC-06-PGP real key | **P1** | Placeholder shipped — security@bravoh.com PGP cert needs real-key generation before public release |
| TAURI-UPDATER-KEY real ed25519 | **P1** | Placeholder shipped Phase 18; auto-update mechanism non-functional until rotated |

### Phase 35 — Real GLBs + Demo Film (human_needed, 35 tests)

| Item | Severity | Status |
|------|----------|--------|
| 5 `prep_*.glb` placeholders (~56KB each) | **P0** | Stub-sized; visible degradation in mascot anticipation moments; replace via Meshy + Mixamo + glb_optimize.py |
| ASSETS-SESSION-RECORD (3min+ raw DJ recording) | **P1** | Kaan already DJing real sessions — recording is mechanical |
| ASSETS-DEMO-CUT (30s demo.mp4 via ffmpeg) | **P0** | `docs/assets/demo.mp4` MISSING; README hero hash is `sha256=PLACEHOLDER` sentinel |
| ASSETS-VO (NO VO is default per `vo_policy.md` — captions carry narrative) | **P3** | Policy locked; AI-VO grep gate prevents accidental synthesized narration |

### Phase 36 — Day-Zero Operations (passed, no VERIFICATION.md, 36 tests)

| Item | Severity | Status |
|------|----------|--------|
| OPS-09-RUN (Discord server provision) | **P1** | Run `discord_provision.py --live` once bot token in hand |
| OPS-10-RUN (100 RPS prod load test) | **P1** | Coordinate with Bravoh team — could DDOS prod if mistimed; needs Bravoh proxy rate-limit headroom confirmation first |
| OPS-11-CRON (healthz watchdog cron) | **P1** | Bravoh sysadmin installs `*/5 * * * *` cron entry |
| OPS-12-OUTREACH (15+ aligned-community star sourcing) | **P2** | Manual outreach across 4 pools; no random friend-favors (P59) |
| OPS-13-EXECUTE (launch_trigger.sh --publish on launch day) | **P1** | 4-stage T-30/T+0/T+5/T+24h sequence |
| OPS-14-SERVER (Bravoh ops endpoints) | **P0** | Bravoh team must deploy `POST /vibemix/updates/upload` + `GET /vibemix/updates/latest.json` + `GET /vibemix/healthz` — auto-update + healthz monitoring non-functional until live |

### Phase 37 — Integration Audit Gate (passed, 42 tests, 5/5 seams WIRED)

| Item | Severity | Status |
|------|----------|--------|
| AUDIT-VM (integration_audit on fresh VM) | **P2** | Depends on Phase 33 + Phase 38 external clock |
| AUDIT-SIGN-VERIFY (signed-binary verifier on real artifacts) | **P2** | Depends on Phase 38 secrets |

### Phase 38 — Signing Pipeline Real Execution (human_needed, 58 tests)

| Item | Severity | Status |
|------|----------|--------|
| DIST-09 (Apple Dev Program Agreement) | **P0** | Francesco-action, hard external |
| DIST-11 (SignPath OSS Foundation) | **P0** | Kaan-action, ~1wk SLA, hard external |
| `release.yml` empty-secret skip annotation | **P3** | Working as designed — annotation prints; pipeline waits for secrets |

### Phase 39 — Public RC Cut + Ship (human_needed, 91 tests)

| Item | Severity | Status |
|------|----------|--------|
| SHIP-CUT (gh release create) | **P0** | Cascades from DIST-09 + DIST-11 |
| SHIP-TWEET / DISCORD / TRANSFER / ROTATE / V1-DECISION | **P1** | Each tied to launch slot; copy + protocol already drafted |
| Phase 16 override expiry (P85) | **P0** | Override expires post-v2.1; v3 must choose a replacement gate (see §4) |
| `cut_release.sh` Gate 2 (signed-binary check) | **P0** | Currently fails ("no .dmg/.pkg/.msi/.exe artifacts in dist/"); flips green when DIST-09+11 land |

**Aggregate v2.1 tech_debt count:** 30 items (audit §8.4). 24 routed to KAAN-ACTION-LEGAL, 6 accepted in-scope post-RC cleanup. **P0 items that gate v3 ship: 7** (DIST-09, DIST-11, SHIP-CUT, OPS-14-SERVER, mic-as-2nd-Part shipped gap, demo.mp4 missing, P85 strategy).

---

## 3. POC v3/v4 Unshipped IP — Drift Table

The 3 untracked POC files (`cohost_v3.py` 1946 lines, `cohost_v4.py` 2422 lines, `cohost_v4_tr.py` 2426 lines) are live reference per memories `project_v3_poc_reference` and `project_v4_canonical_baseline`. v4 is the canonical baseline; v4_tr is v4 + lookahead. Both are untracked, so the POC immutability gate (Phase 37-06 / `tests/repo/test_g5_poc_files_untouched.py`) only protects `cohost.py / cohost_v2.py / cohost_lk.py / mascot.html / cohost.streaming.py.bak` — v3 + v4 + v4_tr are NOT byte-locked. They've been edited as recently as 2026-05-15 (v3, v4) and 2026-05-16 (v4_tr).

### Key IP-drift checks

| Capability | v4 / v4_tr file:line | Shipped vibemix file:line | Status | Severity |
|------------|----------------------|---------------------------|--------|----------|
| **Mic as separate 2nd audio Part** | `cohost_v4.py:1791-1813` (`if mic_wav: contents.append(...)`) | `src/vibemix/agent/dj_cohost.py:332-340` — SINGLE Part labelled "mix + mic" | **NOT shipped** | **P0** |
| **`mic_audio_buf` separate ring (12s)** | `cohost_v4.py:2257` + 1693 (`mic_audio_buf = AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)`) | `src/vibemix/audio/buffers.py:197` has `MicBuffer` but it's a 200ms mute-gate ring, NOT a 12s audio-content ring | **NOT shipped** | **P0** |
| **3s file-based lookahead (LookaheadProvider)** | `cohost_v4_tr.py:624-779` — full class; `cohost_v4.py:619` has placeholder reference | No shipped equivalent (grep `LookaheadProvider`, `lookahead`, `mdfind`, `ffmpeg` in `src/vibemix/` → 0 hits) | **NOT shipped** | **P1** |
| **3rd audio Part for lookahead** | `cohost_v4_tr.py:1762-1813` (3-Part contents when lookahead present) | n/a | **NOT shipped** | **P1** |
| **"Trust your EARS" anti-hallucination rule** | `cohost_v4.py:170` (HARD ANTI-HALLUCINATION RULES) | `src/vibemix/prompts/matrix.py:174` (verbatim port) | **Shipped** ✓ | — |
| **SILENT_RMS = 0.012 / LOW_RMS = 0.040 / PEAK_RMS = 0.110** | `cohost_v4.py:127-129` | `src/vibemix/audio/constants.py:44-46` | **Shipped** ✓ | — |
| **EVENT_GLOBAL_MIN_GAP** | v4:132 — `7.0` per memory, `10.0` actual in v4 | `audio/constants.py:49` — `10.0` (memory note "retuned post-chat-log" matches) | **Shipped** ✓ | — |
| **HEARTBEAT_SEC** | v4:133 — memory says `45.0`, actual v4 `45.0`; shipped `70.0` "retuned post-chat-log" | `audio/constants.py:52` — `70.0` | **Drifted** — shipped value is HIGHER than v4 (less frequent heartbeats). Documented via "retuned post-chat-log" comment but worth a sanity-check against real DJ sessions | P2 |
| **MIN_EVENT_GAP_PER_TYPE.TRACK_CHANGE** | v4 — `5.0` per memory | `audio/constants.py:55` — `6.0` (1s slower) | Drift | P3 |
| **MIN_EVENT_GAP_PER_TYPE.PHASE** | v4 — `10.0` per memory | `audio/constants.py:56` — `18.0` (8s slower) | **Drift** | P2 |
| **MIN_EVENT_GAP_PER_TYPE.LAYER_ARRIVAL** | v4 — `10.0` per memory | `audio/constants.py:57` — `16.0` (6s slower) | **Drift** | P2 |
| **MIN_EVENT_GAP_PER_TYPE.MIX_MOVE** | v4 — `14.0` per memory | `audio/constants.py:58` — `20.0` (6s slower) | **Drift** | P2 |
| **MIN_EVENT_GAP_PER_TYPE.MIC** | v4 — `3.0` per memory | `audio/constants.py:60` — `3.0` | **Shipped** ✓ | — |
| **MUSIC_PRESENCE_MIN_SECONDS** | v4:1178 — `4.0` | `audio/constants.py:96` — `4.0` | **Shipped** ✓ | — |
| **TRACK_CHANGE_MIN_CONFIDENCE** | v4:143 — memory says `0.4`, v4 actual `0.5` | `audio/constants.py:92` — `0.5` | **Shipped** ✓ | — |
| **BlackHole 48kHz format enforcement** | v4 (no programmatic set — config-only guidance) | `src/vibemix/platform/_audio_macos.py:50` (`set_device_nominal_sample_rate(...)`) + `:75` impl; sanity guard at `:9` | **Shipped + IMPROVED on v4** ✓ | — |
| **OpenRouter-primary TTS chain (monkey-patch)** | v4:1917-1944 | `src/vibemix/agent/tts_chain.py:44-80`; `agent/config.py:23` (`OPENROUTER_TTS_MODEL`); `__main__.py:547` | **Shipped** ✓ | — |
| **"trust the audio" comment in detectors** | v4 implicit | `src/vibemix/audio/constants.py:103` ("per 'trust the audio' — don't force-classify") | **Shipped** ✓ | — |
| **Stale-evidence past-tense rule** | v4:163-166 (`LATENCY IS REAL — your reply reaches Kaan 5-10 seconds later`) | `src/vibemix/prompts/matrix.py:167-170` (verbatim port) | **Shipped** ✓ | — |

### Per-event-cooldown drift — root cause and risk

The shipped `MIN_EVENT_GAP_PER_TYPE` is LONGER than v4 for PHASE / LAYER_ARRIVAL / MIX_MOVE by 6-8s each. The shipped constants.py comment block at `:54` calls this "Phase 17 SENSE-12 extension" — Phase 17 added 5 new kick-side detectors (KICK_SWAP / SUB_LAYER_ARRIVAL / KICK_DENSITY_SHIFT / BREAKDOWN_KICK_KILL / REENTRY_KICK_LAND), and the existing legacy cooldowns were lengthened to "let the music breathe" while sharing wall-clock with the new detectors. This is documented but means:
- **The v4 chat-tested intuition of TRACK_CHANGE=5, PHASE=10, LAYER_ARRIVAL=10, MIX_MOVE=14, HEARTBEAT=45 was NOT preserved verbatim.** v4 felt like a chatty studio friend; shipped feels more reserved.
- **Risk:** if v3 ear-test reveals the shipped pacing is too slow, the fix is one-line per constant; risk is "too quiet" not "too noisy".

### Aggregate POC-IP gap verdict

- **2 major P0 unshipped capabilities** — mic-as-2nd-Part + 12s mic_audio_buf. The shipped code TELLS Gemini "mix + mic" is one Part (`dj_cohost.py:335`), but the buffer it draws from (`clean_audio_buf`) contains only the BlackHole stream; the MicBuffer at `:197` is a 200ms mute-decision ring, not the 12s content ring v4 attaches as Part 2. **Net effect:** shipped vibemix never sends Kaan's mic audio to Gemini — KAAN_SPOKE events fire as signals but Gemini doesn't hear his words. This is exactly the regression `feedback_mic_audio_as_multimodal_part` warns against, and was validated in v4 ("harikaydı, bu muhteşem bir yazılım").
- **1 major P1 unshipped capability** — 3s file-based lookahead. Offsets the 5-10s LLM+TTS staleness. v4_tr proves the pipeline works with graceful fallback for streaming-only tracks.
- **5 minor P2-P3 cooldown drifts** documented; not breakage but worth a v3 ear-test re-validation.

---

## 4. Phase 16 P85 Expiry — Dependency Surface

Per `STATE.md:69` and `cut_release.sh:159-161`, the Phase 16 ear-test memory override "EXPIRES post-v2.1 (P85 enforced in Phase 39-08). v2.2 must re-route hallucination-gate strategy."

The memory itself (`feedback_autonomous_no_grey_area_pause` per Plan 39-08) is the override that allowed v2.1 to ship without a Kaan-ear-only gate. The Phase 27 autonomous 2-judge proxy (Gemini Pro + Flash, different rubrics, F1 ≥ 0.80 per detector slice) was the v2.1 substitute.

### Code/spec dependencies on Phase 16

| File | Line(s) | What depends |
|------|---------|-------------|
| `scripts/launch/cut_release.sh` | 159-161 | Prints "Phase 16 override cleanup reminder" on every successful pre-flight — printed in front of Kaan every time he runs the cutter |
| `tests/repo/test_phase_16_override_expiry.py` | full | Asserts STATE.md still carries the override line for traceability + cut_release.sh prints the reminder. **This test enforces the reminder, not the resolution.** |
| `scripts/spike_gemini_text_ordering.py` | 27, 279 | Comment-only reference ("Phase 16 DJ ear-test sessions") |
| `scripts/tune_detectors.py` | 9, 25, 334, 341, 417 | Detector-tuning CSV format consumed by "Kaan's Phase 16 ear-audit" — STATE.md outstanding to-do |
| `scripts/replay_linter.py` | 10, 11, 27, 176 | "Phase 16 ear-test feeds this real Kaan sessions; the synthetic fixture under [...] for shell-pipe consumption (used by Phase 16 audit scripts)" |
| `.planning/STATE.md` | 69, 134, 148 | Decisions Locked: override expires; Risks: P85 tracked for v2.2; Next Session: "choose either restored Kaan-ear-only gate OR permanent autonomous proxy adoption" |
| `.planning/PROJECT.md` | 30 | v2.1 highlight: "Substitutes for Kaan's Phase 16 ear-test for v2.1 only (override expires post-v2.1 per P85)" |
| `.planning/ROADMAP.md` | 29 | v2.0 narrative: "Phase 16 ear-test gate" deferred |
| `KAAN-ACTION-LEGAL.md` | §POST-RC-CLEANUP §1 | "Phase 16 ear-test memory override expiry (P85)" — POST-RC-CLEANUP action |
| `eval/THRESHOLD-LOCK.md` | (per allowlist Phase 27) | F1 thresholds locked for the 2-judge gate; downstream of Phase 16 substitution |
| `.github/workflows/eval.yml` | seam:64 | CI gate calls `replay_harness.py` 2-judge cross-check; alive whether Kaan-ear or autonomous wins in v3 |

### What v3 owes (do NOT design here — separate agent owns strategy)

The hallucination-gate strategy choice is a v3 architectural decision. This audit only surfaces the dependencies:
- 2-judge autonomous gate is wired AND tested (5 e2e tests pass per Phase 37); removing it = breaking the seam.
- Kaan-ear-only validation infrastructure exists (`scripts/tune_detectors.py`, `scripts/replay_linter.py`) but no recurring schedule.
- The `cut_release.sh` reminder + `test_phase_16_override_expiry.py` will keep firing until STATE.md `Phase 16 ear-test memory override` line is removed.

---

## 5. Visual Ship-State Inventory

### CDJ Whisper v5 design system status

| Surface | File | Status |
|---------|------|--------|
| `tokens.css` v5 migration | `tauri/ui/src/tokens.css:3-125` | **Shipped** — v5 CDJ Whisper direction (2026-05-12); backward-compat shim deleted 2026-05-13. All 5 token families present: void / glass / silk / amber / rave + glass blurs + glow primitives |
| Animated amber border (`.border-anim` 22s conic-gradient sweep) | `tokens.css:22-24` (referenced) | **Shipped** — "deck only (one CDJ, one breathing light). Wizard primary-panel + ..." |
| Session window | `tauri/ui/src/session/SessionLayout.ts` | Present; impeccable polish pass `fac4c4a` + `2927e04` shipped 2026-05-14 |
| Wizard | `tauri/ui/src/wizard/` (12 files) | 4-step onboarding flow shipped Phase 33 |
| Debrief window | `tauri/ui/src/debrief/` | Shipped Phase 29 with WaveSurfer.js placeholder timeline (`POLISH-OPT-001` defers real waveform) |
| Mascot overlay | `tauri/ui/src/mascot/priority-stack.ts` + 4 layers | 4-layer additive shipped Phase 31; idle-zero contract bone-level tested |
| Settings drawer | `tauri/ui/src/settings/` | Shipped |
| Crash banner | `tauri/ui/src/crash-banner.ts` | Reads last `[FATAL]` line; recovery from `sidecar-crashed` per fix `8b810a6` |

### Mocks vs shipped

| Mock | Path | Coverage in shipped |
|------|------|---------------------|
| `vibemix-direction-final.html` (CDJ Whisper v5) | `mocks/` | **Direction baseline** — tokens.css ports the design system verbatim |
| `vibemix-app-ui.html` | `mocks/` | Session UI shape — implemented |
| `vibemix-cinematic-storyboard.html` | `mocks/` | Hero demo storyboard — drives `scripts/demo_film/3beat_structure.md` (≤8 cuts gate); demo.mp4 itself still missing |
| `vibemix-direction-explorations.html` | `mocks/` | Historical only — 4-direction explorations; superseded by v5 |
| `vibemix-settings-drawer.html` | `mocks/` | Settings drawer mock — implemented |

### GLB asset inventory

| Asset | Path | Size | Status |
|-------|------|------|--------|
| Character mascot (Neon Rebel) | `tauri/ui/assets/mascot/character.glb` | 20.7 MB | **REAL** — Meshy AI generated, per memory `project_mascot_as_vtuber_personality_surface` |
| `prep_head_turn_left.glb` | mascot/animations/ | ~56 KB | **PLACEHOLDER** (per `PLACEHOLDER_NOTE.md` in same dir; Mixamo retargets would be 400KB-1.2MB) |
| `prep_head_turn_right.glb` | mascot/animations/ | ~56 KB | **PLACEHOLDER** |
| `prep_lean_in_hyped.glb` | mascot/animations/ | ~56 KB | **PLACEHOLDER** |
| `prep_lean_in_neutral.glb` | mascot/animations/ | ~56 KB | **PLACEHOLDER** |
| `prep_settle.glb` | mascot/animations/ | ~44 KB | **PLACEHOLDER** |
| 22 other animations (walking / dance / wave / etc.) | mascot/animations/ | 39-184 KB | **REAL** — Mixamo clips landed 2026-05-12 per file mtimes |
| `tauri/ui/dist/assets/mascot/` mirror | dist/ | matches | Built copy |

**Total mascot bundle:** 21.67 MB / 25 MB ceiling (per Phase 31 audit).

### Demo film asset

| Asset | Path | Status |
|-------|------|--------|
| `docs/assets/demo.mp4` | (would-be) | **MISSING** — README hero hash = `sha256=PLACEHOLDER` sentinel |
| `scripts/demo_film/cuts.json` | scripts/ | Schema validated; ≤8 cuts gate enforced |
| `scripts/demo_film/cut.sh` driver | scripts/ | Manual ffmpeg wrapper — `--dry-run` validates `cuts.json` |
| `scripts/demo_film/recording_protocol.md` | scripts/ | 3-beat structure; 1080p+ 60fps 48kHz spec |

### Visual P0/P1 verdict

- **P0:** 5 `prep_*.glb` stubs + missing `demo.mp4` — both are mascot/hero impressions on launch day.
- **P1:** WaveSurfer.js real timeline (POLISH-OPT-001) — functional today via placeholder regions.

---

## 6. What v3 SHOULDN'T Touch (Explicit Stable Surfaces)

### POC immutability gate (Phase 37-06 / AUDIT-06)

These 5 files MUST stay byte-identical to v2.0 tag — enforced by `tests/repo/test_g5_poc_files_untouched.py`:
- `cohost.py`
- `cohost_v2.py`
- `cohost_lk.py`
- `cohost.streaming.py.bak`
- `mascot.html`

**Untracked POC files** (v3 / v4 / v4_tr / run_*.sh / fillers/) are NOT byte-locked but are Kaan's live reference per `project_v3_poc_reference` + `project_v4_canonical_baseline` + `project_v4_tr_lookahead` memories. **DO NOT modify them.** Port FROM them into `src/vibemix/`.

### Bundle ID locked (Pitfall P63)

`world.bravoh.vibemix` grep-gated against every JSON/JSON5/plist/TOML; `bundle-id-lock.yml` workflow blocks divergent IDs on PR.

### Stable cross-phase seams (5 WIRED per Phase 37)

| Seam | Source | Sink | Tests | Rule |
|------|--------|------|-------|------|
| EvidenceRegistry → CitationLinter | `src/vibemix/state/evidence_registry.py:2` | `src/vibemix/coach/citation_linter.py:2` | 2/2 pass | Live-mode citation enforce — don't break the lint path |
| GeminiContextCache → DJCoHostAgent.llm_node | `src/vibemix/agent/cache.py:2` | `src/vibemix/agent/dj_cohost.py:2` | 3/3 pass | Cache + system_instruction mutually exclusive (P60); cache name swap is atomic |
| RekordboxLibrary → EvidenceRegistry.register_library | `src/vibemix/library/rekordbox.py:2` | `src/vibemix/state/evidence_registry.py:44` | 2/2 pass | P48 final-mile; library priors register at session boot |
| replay_harness → eval.yml CI gate (2-judge) | `scripts/eval/replay_harness.py:305` | `.github/workflows/eval.yml:64` | 3/3 pass | Phase 27 hallucination-proxy substitute — DON'T break unless v3 explicitly retires it |
| 4-layer mascot priority-stack → ws_bus IPC frame | `tauri/ui/src/mascot/priority-stack.ts:1` | `src/vibemix/runtime/ws_bus.py:2` | 3/3 pass | 30 fps mascot frame; v2.0 mascot tests port verbatim (P47) |

### Stable invariants

- **Gemini-only AI** — no Anthropic / OpenAI / Ollama / CLAP / OpenL3 / MERT / sentence-transformers / torch (gitleaks Phase 34-01 + memory `feedback_no_clap_use_gemini_embedding`).
- **Three.js single 3D engine** — no Babylon, no react-three-fiber.
- **Vanilla TS in `tauri/ui/src/`** — NOT React. Avoid framework drift.
- **WaveSurfer.js** — Phase 29 debrief timeline; the placeholder regions surface meets DEBRIEF-05 functionally.
- **Bravoh-managed Gemini API key** via `api.altidus.world/vibemix` proxy — never ship raw key (P63 grep gate + `test_no_api_key_surface.py`).
- **macOS 12.3+ / Windows 10/11** — Linux excluded.
- **3-process architecture** — Tauri shell + Python sidecar + FastAPI proxy. Don't collapse into 2.
- **Apache 2.0 + DCO** — single-license; no commercial dual-license drift.
- **Track-to-track similarity USER-ASKED-only** (LIBRARY-14 anti-feature guard) — physically gated to CLI + `ipc.library.similar_request`; never auto-surfaces.
- **DJ profile never per-turn prompt prefix** (P60) — lives in `GeminiContextCache`; `additionalProperties: false`; default-OFF consent.

### Mature shipped surfaces (don't redesign without strong reason)

- `EvidenceRegistry` — anti-slop foundation
- `GeminiContextCache` — 1024-token floor / 4-min refresh
- `AckBank` — 40-OPUS Achird ack bank (20 missing — quota cleanup)
- `CancelGate` — 8s hard / 30s soft
- `TTFTMeter` — first-token latency telemetry
- `GenreRouter` MappingProxyType atomic-swap (8 readers × 1000 swaps regression-tested)
- `MidiMapLoader` — 10-SKU MIDI library
- 6 cross-genre event detectors (KICK_SWAP / SUB_LAYER_ARRIVAL / BREAKDOWN_KICK_KILL / REENTRY_KICK_LAND / KICK_DENSITY_SHIFT / PHRASE_BOUNDARY) + 2 Hard Tek (DISTORTION_CLIMB / ACID_LINE_ENTRY)
- `WASAPI IMMNotificationClient` subscription — mid-session default-device-change handling
- Universal2 sidecar target-triple convention (research-corrected Phase 27-06; eliminates Rosetta prompt)

---

## Appendix — All P0 Items Consolidated

These are the items that **block clean v3 ship** with no graceful workaround:

1. **DIST-09** — Apple Developer Program Agreement update (Francesco, P46 hard rule). External clock. KAAN-ACTION-LEGAL §6.
2. **DIST-11** — SignPath OSS Foundation application (Kaan, ~1-week SLA, P46 hard rule). External clock. KAAN-ACTION-LEGAL §7.
3. **Mic-as-2nd-Gemini-Part** — Shipped `src/vibemix/agent/dj_cohost.py:332-340` sends ONE Part with mix only, labelled "mix + mic". v4 (`cohost_v4.py:1791-1813`) attaches mic as a separate Part 2 with explicit prompt language. **Net effect:** vibemix never hears Kaan's voice; KAAN_SPOKE fires as signal but Gemini answers blind. Engineering fix — no external dependency.
4. **5 `prep_*.glb` placeholders** — `tauri/ui/assets/mascot/animations/prep_*.glb` are ~56 KB stubs vs Mixamo retargets (400 KB-1.2 MB). Anticipation moments degrade. Discharge: ASSETS-MESHY-A/B + ASSETS-MIXAMO-RIG + ASSETS-PREP-REPLACE per KAAN-ACTION-LEGAL.md §35.
5. **`docs/assets/demo.mp4` missing** — README hero hash is `sha256=PLACEHOLDER` sentinel. OSS launch tweet/IG drops without a hero video. Discharge: ASSETS-SESSION-RECORD + ASSETS-DEMO-CUT per KAAN-ACTION-LEGAL.md §35.
6. **Phase 16 ear-test memory override expiry (P85)** — v3 must explicitly choose: restored Kaan-ear-only gate OR permanent autonomous 2-judge proxy adoption. STATE.md "Phase 16 ear-test memory override" line + `cut_release.sh:159` reminder + `test_phase_16_override_expiry.py` enforce until resolved. Strategy choice deferred to separate agent.
7. **OPS-14-SERVER** — Bravoh team must deploy `POST /vibemix/updates/upload` + `GET /vibemix/updates/latest.json` + `GET /vibemix/healthz`. Auto-update + healthz monitoring non-functional until live. Bravoh-team dependency.
8. **SHIP-CUT** — Gate-2 of `cut_release.sh` currently fails ("no .dmg/.pkg/.msi/.exe artifacts in dist/"); cascades from DIST-09 + DIST-11.

**Critical path:** items 1+2 unlock 7-of-8 P0s. Item 3 is the only standalone engineering P0 — no external blocker, can ship Day 1 of v3. Items 4+5 need Kaan asset-production time but no external clock.

---

*Audit complete. Read-only — no files modified. Strategy and fix proposals are out-of-scope per task spec; this surface is for the v3 milestone scoping agent to consume.*
