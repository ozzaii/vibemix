# D — Hallucination Gate v3 + Visual Identity Lock

**Bucket:** v3 / D · **Authored:** 2026-05-16 · **For:** v3 milestone scoping — pick a hallucination gate strategy + lock the visual identity before public RC publish.

---

## TL;DR

**Gate — Option C (hybrid).** Keep Phase 27's autonomous proxy as a PR fast-lane (must stay green to merge), but reinstate a formalized **Kaan-ear release-cut veto** as the ship gate. Crisp cut-line: proxy-pass + ear-pass = SHIP; proxy-pass alone = HOLD-FOR-EAR; proxy-fail = HOLD (no override). Cost ≈ 1 v3 phase (eval hardening + ear-test protocol + cut-criteria doc) + ~6–8 Kaan-hours per release + 5 €/mo API headroom. The autonomous-only override (P85) expired with v2.1; v3 must not silently extend it.

**Visual — one combined phase.** "Visual Ship Lock" — CDJ Whisper UI polish + Neon Rebel mascot hardening + 30s hero demo prep — as ONE phase, three internal waves, critique→execute loop spanning the whole phase. Two phases would split a single design-system feedback loop and force premature token freeze; the UI hosts the mascot overlay and the hero demo records against both, so the shared dependency makes one phase cheaper to plan and verify.

---

## Part 1: Hallucination Gate v3

### 1.1 Current state

Phase 27 (9 plans, 140 tests) is the biggest hallucination defense in the repo:

- **`scripts/eval/replay_harness.py`** — pure-Python deterministic replay of `recordings/<session>/{events.jsonl, input.wav, voice.wav}` through the shipped detector + EvidenceRegistry + ack-bank + linter chain. No Tauri, no sidecar, runs in CI.
- **2-judge cross-check** (`scripts/eval/judge.py`) — Gemini 3 Pro (6-axis structured JSON: groundedness, timing, substance, tone, relevance, brevity) + Gemini 3 Flash (binary pass/fail). Final F1 = `min(pro_f1, flash_f1)` per Pitfall P42 collusion mitigation, hard-pinned by `test_call_judges_aggregates_min_not_mean`.
- **`eval/THRESHOLD-LOCK.md`** — autonomous-signed (`kaan_signed: autonomous_phase27`) with F1 ≥ 0.80, substance ≥ 0.65, cited-cosine ≥ 0.40, bypass ≤ 0.15, per-genre F1 ≥ 0.70. **Crucially unvalidated against real corpus** — values are research-grounded but not measured.
- **CI:** `.github/workflows/eval.yml` runs Flash on every PR ($0 cassettes); Pro+Flash nightly canary refreshes cassettes + commits scorecards.
- **`EvidenceRegistry`** (`src/vibemix/state/evidence_registry.py`) — 7-source EBNF grammar (`ev`/`aud`/`midi`/`track`/`screen`/`mix`/`tend`), single-lock-guarded, `register_library` wired in `__main__.py` for `[track:<id>]` citations against Rekordbox.
- **40-OPUS ack-bank (v2.0 P19)** — only **20/40 Achird OPUS files generated** today; Phase 27 Plan 08 hit Gemini free-tier daily quota. The uncited-reaction fallback covers half its intended response pool.

Three deferred items shape v3 scope: corpus is a skeleton (no WAVs), ack-bank is 20/40, VCR cassettes are empty. P85 (override expiry) says the proxy-substitutes-for-Kaan-ear license was **v2.1-only** — v3 must re-decide the gate stance; silence defaults to Kaan-ear-only Phase 16.

### 1.2 Option A — Restore Kaan-ear-only Phase 16

**Shape:** Treat Phase 16 verbatim per `[[project_phase_16_kaan_dj_testing]]` — Kaan plays real sets, his lived experience is the sole veto. Mothball the proxy CI gate (keep code).

**v3 cost:** 0 new phases. ~5 Kaan-hours/release.

**Strengths:** Zero false confidence; cheapest €/mo; aligned with `[[feedback_no_scope_creep_clean_utility]]`; no "green proxy + slop ear" contradiction.

**Weaknesses:** Regression detection collapses — any post-launch PR (third-party detector, prompt tweak, model swap) has no automated hallucination signal before merge. Doesn't scale to OSS contributors. Throws away 140 tests of v2.1 work. Reads weak to discerning DJ devs evaluating the repo (the audience most likely to fork and cite).

### 1.3 Option B — Harden autonomous proxy permanently

**Shape:** Lean fully into proxy. Add a 3rd judge (human-curated golden-response retrieval), expand corpus to 10+ sets across 5+ genres, Francesco-rotation human spot-check, confidence-weighted F1, per-detector regression baselines.

**v3 cost:** 2 phases (~18 plans) — (a) corpus expansion + judge diversity + per-detector baselines, (b) human-in-the-loop spot-check + scorecard reviewer UI. +15 €/mo API. ~3–4 Kaan-hours/month for audit reviews.

**Strengths:** Scales to OSS contributors; compounds the v2.1 Phase 27 investment; catches drift across model swaps; "every release passes F1 ≥ 0.80 on 10+ public-domain DJ sets" is a credible marketing-grade claim.

**Weaknesses:** **Goodhart risk** — optimizing F1 + substance + cited-cosine can produce reactions that pass the proxy but feel scripted to a real DJ, the exact failure mode the product is designed to avoid. Kaan named this concern explicitly in `[[project_phase_16_kaan_dj_testing]]`. Cost creep — 3 judges × nightly canary breaks the €50/mo budget. Francesco human-rotation is fragile (he's cofounder with marketing bandwidth, not a QA reviewer). Thresholds still unvalidated — hardening before first-corpus run is fortifying a number that may be wrong by ±0.15 F1.

### 1.4 Option C — Hybrid (proxy fast-lane + Kaan-ear release veto) [recommended]

**Shape:** Two-tier gate with crisp criteria.

| Trigger | Gate | Outcome |
|---|---|---|
| PR merge | Proxy (Flash, cassettes) | red = block; green = proceed |
| Nightly canary | Proxy (Pro + Flash, real API) | red = file regression issue; green = healthy baseline |
| Release-cut | Proxy green ≥ 7 consecutive nights AND Kaan-ear pass on ≥ 2 real sets / ≥ 2 genres | both pass = SHIP; proxy alone = HOLD-FOR-EAR; proxy fails = HOLD (no override) |
| Post-launch contributor PR | Proxy fast-lane only | green proxy = engineering-approve |

**Cut-line invariants:**
- Proxy-pass alone is **never** sufficient to ship — necessary but not sufficient.
- Kaan-ear veto trumps proxy-pass; a green proxy + Kaan "feels slop" = HOLD, documented as a normal outcome.
- Proxy-fail blocks Kaan-ear — no "Kaan said it's fine so ignore F1" path; that would silently re-create Option A.

**v3 phases needed:** 1 phase, ~6–8 plans:
1. Discharge `KAAN-ACTION-LEGAL.md` items 1–4 (cassettes, ack-bank 20/40, 6 corpus WAVs, threshold first-canary calibration).
2. Validate locked thresholds against real corpus; recalibrate if measured F1 lands outside locked ±0.10.
3. Codify ear-test protocol — 30min minimum, ≥ 2 genres, structured "what felt slop?" capture template in `eval/ear-test-logs/`.
4. Cut-criteria doc + `scripts/release/check_gate.sh` reading last 7 nightly scorecards + signed ear-test log within last 14 days.
5. Wire post-session debrief window (Phase 29) to expose ear-test capture surface — Kaan ends a session, debrief offers "rate this session for release-gate" toggle writing to `eval/ear-test-logs/`.
6. Expand corpus to 8 sessions (+ melodic techno + DnB) — buys regression sensitivity in genres Bravoh's DJ network plays.
7. P85 override-expiry audit — explicit Decision Log entry that v2.1's autonomous-only override has terminated.
8. (Optional) `eval/README.md` for public — credible OSS-grade transparency without leaking ear-test logs.

**Hallucination class coverage:**

| Class | A (ear) | B (proxy hard) | C (hybrid) |
|---|---|---|---|
| Made-up track ID | partial | yes (cited-cosine) | yes |
| Made-up event timing | partial | yes (timing axis) | yes |
| "Energy is high right now!" generic slop | yes | partial (substance is floor, not ceiling) | yes |
| Drift after model swap | no | yes (canary) | yes |
| OSS contributor regresses ack-bank | no | yes | yes |
| Cited-but-irrelevant | no | yes (cosine) | yes |
| "Feels scripted not friend-like" | yes | no (Goodhart) | yes |

C is the only column with zero "no" entries.

**Cost:** ~6–8 Kaan-hours/release (2 ear-test sessions × 30min + 1hr scorecard review + 30min protocol fill). +5 €/mo for corpus expansion. ~1 v3 phase of engineering.

### 1.5 Recommendation + rationale

**Pick Option C.** The product thesis (`[[project_anti_slop_grounded_gemini_thesis]]`) treats hallucination as a *data problem* solved by grounding — not a *measurement problem* solved by F1. That makes the proxy a regression-detector, never a ship-gate. Pretending proxy is enough (B) imports Goodhart risk into the exact perception the product exists to deliver. Pretending proxy is worthless (A) wastes 140 working tests and leaves OSS contributors with no signal.

Hybrid also reads defensible publicly: "every PR is checked against a 2-judge eval suite; every release is also ear-tested by the founder in real DJ sessions" is serious engineering, not LARP-y synthetic-only or hand-wavy ear-only. Best posture for `[[project_github_star_goal]]`. And it threads P85 cleanly — the v2.1-only license expired by default; v3 explicitly redefines the regime instead of silently extending it.

**Open question for Kaan:** Plan 5 (debrief surface for ear-test capture) is the only UI work — should capture live in the debrief window or a separate CLI prompt? Recommendation: debrief window — natural moment of reflection, already has WaveSurfer.js for evidence playback.

---

## Part 2: Visual Identity Lock

### 2.1 Current state inventory

**Mocks (design contract):** `mocks/vibemix-direction-final.html` is CDJ Whisper v5 — 5-tier void stack, single amber accent (4 intensities), glass + animated border, Saira + JetBrains Mono. `mocks/vibemix-app-ui.html` + `mocks/vibemix-settings-drawer.html` are older FL-Studio-tactile mocks (superseded by v5 but still in repo). `mocks/vibemix-cinematic-storyboard.html` is the 45s / 10-frame hero cut storyboard, still on older Workbench/DSEG7/paper-grain vocabulary — **vocabulary mismatch with the shipped UI.**

**UI code (Tauri vanilla TS, Phases 11–14 + 31):** `tauri/ui/src/tokens.css` (587 lines, v5 system + backward-compat shim) · `session/` (11 components: cohost, drop-chip, event-ribbon, meter, panel, phase-tape, picker, rocker, shortcuts-overlay, status-bar, timecode, titlebar) · `wizard/` (6 onboarding steps + telemetry/profile consent) · `settings/` · `debrief/` (chapter-list, citation-tooltip, drills-panel, timeline (WaveSurfer.js), tldr-player on port 8766) · `mascot/` (4-layer additive state machine: base/emotion/anticipation/reaction, priority stack, crossfade policy, particle-puff, ws-client, renderer) · `overlay/` (Phase 24 djay Pro amber ring).

**Mascot assets:** `tauri/ui/assets/mascot/character.glb` is 21 MB Draco-compressed Neon Rebel (Meshy-generated 2026-05-12). 20 animation GLBs, mesh-stripped, 30–185 KB each. Total bundle: 22.4 / 25 MB (89.7% utilized). Manifest maps each clip to vibemix state labels (`idle_breathe_slow`, `dance_a..hard`, `react_drop`, `react_glitch`, `talk_loop_calm/energetic`, `point_explain`, `gesture_wide`).

**Gap to ship-ready:**

1. CDJ Whisper v5 tokens shipped to `tokens.css`, but **`gsd-ui-checker` + `gsd-ui-auditor` retrospective audit hasn't run end-to-end against every shipped surface.** Performance toggle `data-blur-perf` exists for low-GPU machines; no test confirms every panel honors it.
2. Hero-demo storyboard still uses Workbench + DSEG7 + paper-grain — UI uses Saira + glass. Either re-skin or treat the paper-on-glass as deliberate diptych.
3. Memory drift: `[[project_mascot_as_vtuber_personality_surface]]` says character codename = "DJ bat"; the actual shipped GLB is "Neon Rebel."
4. 20 animations are bundled but **mood→animation pool runtime selection logic (`mascot/mood.ts`) hasn't been audit-passed** against Hype-man / Teacher / Coach personas.
5. **No 30s hero demo MP4 exists yet** — Phase 35 covered storyboard; live shoot is `KAAN-ACTION-LEGAL` (Francesco shoots Kaan).

### 2.2 Mascot production pipeline 2026

**Pick: ship Neon Rebel as-is.** The GLB is in the bundle, at 89.7% of cap, byte-identical regen verified. No v3 reason to regenerate.

For any future refresh, 2026 landscape:

| Tool | Lic | Strengths | Vibemix fit |
|---|---|---|---|
| **Hunyuan3D** | FOSS (Apache 2.0) | Best for stylized characters; 4K PBR; runs local | First-choice for regen; aligns with OSS license |
| **Tripo v3** | Commercial | "Sculpture-level precision" | Backup |
| **Meshy** | Commercial (~$20/mo) | 97% 3D-print pass; in Kaan's workflow | Source-of-truth — keep |
| **Rodin Gen-2** | Commercial | 10B-param photorealism | Overkill — CDJ Whisper silhouette doesn't need it |
| **TRELLIS** | FOSS (research) | Best mesh accuracy from t-pose | Photorealism use case, not silhouette |

**Auto-rig:** Mixamo development has stalled (no meaningful updates in years per CG Channel + Reallusion 2026 reports). Still works, and the current 20-clip bundle was retargeted via Mixamo. For v3 future-proofing, **AccuRIG 2** (Reallusion, free, actively maintained) is the recommended next pick — handles non-humanoid (Neon Rebel has wings) better than Mixamo's strict biped. **Cascadeur** is keyframe physics-assist for ~5 custom DJ moves (head bop, fist pump, vinyl scratch), not the primary pipeline.

**Recommendation:** ship Neon Rebel + the existing 20-clip Mixamo bundle as-is for v3. If post-launch a refresh is wanted, Hunyuan3D + AccuRIG 2. Don't burn v3 cycles on a re-roll.

### 2.3 FL-Studio-quality UI polish surface

PROJECT.md Active section names "Dedicated polish phase — FL-Studio-quality UI bar" as a hard requirement. Critical surface for v3:

**Tier 1 (must ship FL-Studio-grade):** Session window, mascot overlay, wizard surfaces, calibration / first-run.

**Tier 2 (important, tolerable rough edges):** Settings drawer, debrief window, recording browser.

**Tier 3 (defer):** djay Pro amber-ring (works), tray popover (utility).

**Critical FL-Studio-vocabulary pivots:**
- **Hover states everywhere** — every interactive element gets `--glow-faint` outer halo on hover, no transform, no scale. FL Studio's secret is *every* knob/button/slider has a visible hover. Vibemix today likely misses hover on phase tape segments, drop-chip pips, status bar LEDs.
- **Knob/fader physics** — no real knobs in vibemix (it's a viewer, not a mixer), but volume/pan/mood-selector dials in wizard should feel like Pioneer rotary encoders: amber backlight bleed on active, recessed shadow on press, hairline glass edges.
- **Spectrum realism** — `session/components/meter.ts` renders live RMS bands. If it reads as a generic web-app gradient, the product looks AI-toolish. If it reads as a hardware analog meter (faint LED-strip texture, amber peak hold, silk-12 minor grid lines), it reads pro audio. **Biggest "pro vs AI" pivot point on the session screen.**
- **Typography hierarchy** — Saira variable wdth (85–95 labels, 100 body) + JetBrains Mono tabular-nums for numerics. Audit every surface for system-font fallback leaks.
- **Animation discipline** — 80–200ms ease, no springs, no overshoots. `borderSweep` 22s is the only idle-animated chrome; everything else state-driven.

**v3 polish deliverable:** every Tier-1 surface passes paired `gsd-ui-checker` + `gsd-ui-auditor` runs with zero HIGH findings. Critique → execute → critique loop until both green.

### 2.4 Hero demo (30s) — storyboard + timeline

**Current storyboard** (`mocks/vibemix-cinematic-storyboard.html`): 45s / 10 frames, mascot cameos in 3 frames (silent), vibemix UI appears as a real chip floating in frame. Vocabulary mismatch (Workbench + DSEG7 + paper-grain vs Saira + glass). Recommendation: keep paper-on-glass as the *storyboard* format (paper IS the director's notes), but mock a v5-accurate UI chip overlay so the in-shot product matches the downloaded app.

**Length:** PROJECT.md says 30–45s. Shoot 45s, edit 30s + 15s + 5s for IG/TikTok/README slots. README hero autoplays the 30s.

**Realistic timeline (Francesco shoots Kaan):**

| Stage | Duration | Owner | Outcome |
|---|---|---|---|
| Storyboard v5 alignment | 0.5d | Claude (mocks) | v5-accurate UI overlay frames + cut script + shot list |
| Pre-production | 1d | Francesco + Kaan | Location (Kaan's studio), gear sourcing, controller setup |
| Live shoot | 1d | Francesco + Kaan | Real DJ session, vibemix on Kaan's machine, separate audio capture (Gemini voice + ambient + headphone return) |
| Edit | 2–3d | Francesco + Kaan checkpoint | 45s + 30s + 15s cuts; color grade to v5 (warm blacks, amber pop); on-screen UI overlay composited from live screen-grab |
| Polish + delivery | 0.5d | Francesco | Audio ducking, subtitles, OG-preview frame extraction |
| **Total** | **~5–7d** | Mixed | MP4 + GIF + still for OG |

**This is not a v3 engineering blocker** — live shoot is `KAAN-ACTION-LEGAL` per Phase 35 deferred items + `[[project_v0_1_0_rc1_open_bugs]]`. v3 engineering ships the visual surfaces while the cinematic ships in parallel. Fallback: README launches with a static screenshot, replaced with cinematic in v3.0.1.

### 2.5 Phase scope — 1 phase, three waves

**"v3 Visual Ship Lock" — ~9–11 plans, three waves, critique→execute loop across the whole phase.**

**Wave A — UI Polish (4 plans):**
- A1: Tier-1 surface audit — every shipped session component, mascot overlay, wizard step, calibration surface gets a `gsd-ui-checker` pass; capture HIGH/MEDIUM findings.
- A2: Hover-state coverage sweep — every interactive element gets `--glow-faint` on hover; pin via visual-regression test.
- A3: Spectrum-meter rebuild — `session/components/meter.ts` from gradient to hardware-LED-strip aesthetic with amber peak hold.
- A4: Tier-1 critique → execute loop until paired `gsd-ui-checker` + `gsd-ui-auditor` both green.

**Wave B — Mascot Production Hardening (3 plans):**
- B1: Mood→animation pool runtime validation — Hype-man/Teacher/Coach pools wired to manifest clips; smoke test 30s per persona with crossfades.
- B2: Mascot overlay perf — `data-blur-perf` honored on integrated GPU; `backdrop-filter` fallback ladder tested on Intel UHD + M1 base.
- B3: Memory drift cleanup — `[[project_mascot_as_vtuber_personality_surface]]` says "DJ bat"; shipped character is "Neon Rebel." Update memory + any doc drift.

**Wave C — Hero Demo Prep (2–4 plans; rest = KAAN-ACTION):**
- C1: Storyboard v5 alignment — re-mock UI chip overlay frames; finalize cut script + shot list.
- C2: Pre-production package — shot list, audio capture plan, vibemix demo-mode config (deterministic event sequence for repeatable takes).
- C3 (KAAN-ACTION): Live shoot — Francesco + Kaan, 1d.
- C4 (KAAN-ACTION): Edit + grade + deliver — Francesco, 2–3d.

**Why one phase, not two:**

1. **Shared design-system feedback loop.** UI polish surfaces mascot overlay perf cost. Mascot polish surfaces UI tokens (amber-eye exact hue must match `--amber: #ff8a3d` — if UI polish redefines the amber stack, mascot follows). Splitting forces premature token freeze + a `tokens.css` v5→v6 churn.
2. **Critique→execute loop benefit.** A single phase running paired UI auditors catches inter-component issues a per-phase audit misses (e.g. glass alpha consistent on session but blowing out on mascot overlay).
3. **Hero demo planning needs the polished UI.** Storyboard v5 alignment (C1) requires the final v5 contract — exactly what Wave A delivers. Splitting means C1 uses placeholder UI or blocks on a separate phase.
4. **Plan-budget efficiency.** ~9–11 plans in one phase with amortized critique loop is cheaper than 2 × ~6 plans with full discuss/plan/verify cycles.

**Counter-argument:** split only if mascot hardening becomes scope-heavy (e.g. character regen). Risk is low — `/hatch` user-gen is explicitly v2.x stretch per `[[project_v2_open_candidates]]`, not v3.

**v3 phase budget contribution:** one phase ≈ size of v2.1 Phase 31 (4-layer mascot, 8 plans, 17 tests, 21.67 MB GLB bundle) — a well-understood envelope.

---

## Sources

- Phase 27 spec: `.planning/milestones/v2.1-phases/27-eval-harness-v2-0-carry-forward-close-out/{27-CONTEXT.md, 27-VERIFICATION.md}`
- Eval surface: `eval/THRESHOLD-LOCK.md`, `scripts/eval/judge.py`, `scripts/eval/replay_harness.py`
- Evidence anchor: `src/vibemix/state/evidence_registry.py`
- Visual contract: `mocks/vibemix-direction-final.html`
- Migration plan: `.planning/HANDOFF-cdj-whisper-v5-ui-migration.md`
- Mascot bundle: `tauri/ui/assets/mascot/MANIFEST.md`
- Tauri UI tree: `tauri/ui/src/{session,mascot,wizard,settings,debrief,overlay}/`
- PROJECT.md REQUIREMENTS + Key Decisions; ROADMAP.md v2.1 archive
- Memory: `project_anti_slop_grounded_gemini_thesis`, `project_phase_16_kaan_dj_testing`, `project_mascot_as_vtuber_personality_surface`, `project_visual_direction_cdj_whisper`, `feedback_autonomous_no_grey_area_pause`, `project_github_star_goal`, `project_v2_open_candidates`
- Web: [Best AI 3D Model Generators 2026](https://trellis2.app/blog/best-ai-3d-model-generator); [Hunyuan3D vs Meshy](https://hunyuan3dai.com/posts/hunyuan3d-vs-meshy/); [Glassenberg AI image-to-3D head-to-head](https://medium.com/@Glassenberg/head-to-head-ai-image-to-3d-comparison-hunyuan-vs-meshy-vs-f99cb38faa39); [AccuRIG 2 vs Mixamo](https://magazine.reallusion.com/2025/07/30/accurig-2-vs-mixamo-smarter-auto-rigging-for-3d-animators/); [Mixamo alternatives 2026](https://mocaponline.com/blogs/mocap-news/mixamo-alternatives)
