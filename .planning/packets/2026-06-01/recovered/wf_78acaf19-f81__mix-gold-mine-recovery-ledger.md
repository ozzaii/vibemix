# MIX GOLD-MINE RECOVERY LEDGER

**Repo HEAD:** `0e7bdc1c` (branch `live-tuning-or-brain`) · **Date:** 2026-05-31
**Purpose:** Reconcile what the planning docs *claimed* shipped/wired against what static reality-check actually found on disk, so we capture moat-grade work sitting one wire away from live and stop redoing what's already done.

**Counts:** 45 ideas total.

| code_status | count | ids |
|---|---|---|
| WIRED_LIVE | 27 | g1, g2, g4, g5, g6, g7, g9, g10, g11, g13, g15, g16, g17, g18, g19, g21, g30, g31, g32, g33, g35, g36, g37, g38, g39, g41(seam) |
| PARTIAL | 14 | g3, g8, g12, g14, g22, g23, g24, g25, g26(orphan-half), g27, g34, g40, g42, g43, g44, g45 |
| PRESENT_ORPHANED | 1 | g20 |
| CLAIMED_BUT_ABSENT | 1 | g28 |

(Note: a handful of ids carry a PARTIAL verdict where the *engine* is live but one named sub-piece is orphaned/unbuilt — counted by their primary code_status above; g26 and g41 are WIRED_LIVE engines with one orphaned helper.)

---

## 2. THE GOLD WE ARE ABOUT TO MISS

Moat/high-value ideas that are NOT fully wired (PRESENT_ORPHANED, CLAIMED_BUT_ABSENT, or PARTIAL). Ranked by leverage: how close to live × how much it unlocks.

### g8 — judge_voice.verdict_evidence_line: the co-host SPEAKS the Judge verdict (moat · PARTIAL · WIRE_IT)
- **Brings:** The literal payoff of the whole Vibe-Judge moat — "engine decides, Gemini only voices." The deterministic verdict exists and is grounded; this is the last mile that makes the co-host actually *say* it.
- **Gap (claimed "wired" vs real PARTIAL):** Engine half runs live and stashes the verdict in `_last_verdict`, but `verdict_evidence_line` has **zero callers** and `_last_verdict` is **write-only**. TODO names the gap verbatim.
- **Evidence:** `verdict_evidence_line` def `src/vibemix/intel/judge_voice.py:32`; `codegraph_callers` → 0 runtime. `_last_verdict` assigned, never read (grep). TODO at `coach.py:793-794`. `judge:` not in citation grammar (grep `dj_cohost.py`/`evidence_registry.py`/`citation_linter.py`).
- **Smallest action:** 3 steps — (1) call `verdict_evidence_line(self._last_verdict, t=event.t)` into the dj_cohost prompt path; (2) register `judge:` as an EVIDENCE_SOURCE + resolvable citation so `[judge:transition@t]` survives Invariant #2; (3) coach-loop integration test. Run `vibemix-grounding-review` + `drive-vibemix` before merge.
- *(Cross-ref: g9 reports the live judge call already passes `judge_voice_lines=None` "until the persona voice-line wiring (next slice)" at `coach.py:822` — same gap, confirmed from the producer side.)*

### g12 — Live-guard verdict-vs-adjective strip rule (moat · PARTIAL · WIRE_IT)
- **Brings:** The Invariant #2 release gate for spoken quality adjectives — a "tight/clean/mud/clash" claim with no `[judge:]` citation strips to ack-bank, and Gemini cannot upgrade the Judge's grade (mid→bomb blocked). This is the anti-slop gate the project calls its release blocker.
- **Gap (claimed "deferred" — accurate):** `apply_live_claim_guard` is live and the Judge grounds/credits, but the guard has **no branch** comparing a spoken adjective against the Judge grade.
- **Evidence:** `apply_live_claim_guard` `state/deck_context.py:2219`; full-body read shows mixer/causality branches only. `grep judge_transition|[judge: deck_context.py` → EXIT 1 (zero). Deferral documented `docs/superpowers/plans/2026-05-30-the-vibe-judge.md:1020-1022`.
- **Smallest action:** Add the verdict-vs-adjective branch to `apply_live_claim_guard` (substrate ready: `supported_verdict` policy branch at `deck_context.py:2151`, Judge importable, `EvidenceRegistry.write` at `:267`). Run `vibemix-grounding-review` before shipping. Unlocks the g10 keystone fully.

### g20 — claim_validator → live brain (S1 dark edge) (high · PRESENT_ORPHANED · WIRE_IT/INVESTIGATE)
- **Brings:** The perception-singularity end-state — route EVERY spoken line (not just Judge verdicts) through a deterministic decision + real evidence check.
- **Gap (claimed "deferred" — accurate):** Full chain exists and is test-covered but has **zero production callers**; the entire `intel/` package has **zero runtime importers**.
- **Evidence:** `validate_claim` `intel/claim_validator.py:60`, `DecisionRuntime` `decision_runtime.py:44`; `codegraph_callers` → only tests/siblings. `grep -rln "vibemix.intel" src/vibemix --include=*.py | grep -v intel/` = EMPTY. Live brain grounds via the *separate* EvidenceRegistry path.
- **Caveat:** Cited source doc `.planning/singularity/2026-05-31-singularity-map.md` does **not exist** at HEAD; deferral corroborated by `one_mind` memory. This is the single highest-stakes wiring in the tree — two grounding systems would coexist.
- **Smallest action:** INVESTIGATE the design contract first (how `DecisionResult` maps to the existing citation-linter/ack-bank fallback) — this is a Kaan-call architecture decision, NOT a routine orphan-to-wire.

### g23 — CUE-DETR ONNX auto-cue producer / THE MOAT (moat · PARTIAL · WIRE_IT)
- **Brings:** Trustworthy hot-cue positions the AI never guesses — explicitly tagged THE MOAT. The pure-numpy heuristic *failed* on hardtechno, so CUE-DETR was adopted.
- **Gap (claimed "wired" — overstated):** Producer is real and reached LIVE via the Viber/Codex `smart_hot_cues` MCP tool, but (a) the headline `library cue <folder>` engine is **orphaned** (no CLI subparser), (b) the ONNX model is **not bundled** so default ship silently runs the weak heuristic, (c) live co-host loop never consumes it.
- **Evidence:** `detect_cue_positions` `library/cue_detr.py:287`; reached via `cue_engine.detect_cues_auto` ← `toolset.py:88` ← MCP `smart_hot_cues mcp_server.py:211`. `grep add_parser("cue" __main__.py` → EXIT 1. `DEFAULT_CUE_ONNX_PATH` referenced, never auto-populated. *(codegraph_callers + grep)*
- **Smallest action:** (1) Add `library cue <folder>` subparser calling the ready `export_cued_folder`; (2) confirm the cue-detr asset registry has a real download URL+sha (overlaps g24).

### g24 — Host the CUE-DETR model (the one true ship blocker for good one-click cues) (high · PARTIAL · RESURFACE)
- **Brings:** Flips the default cue path from weak-heuristic to the real DETR model on every clean machine — a shippable free auto-cue tool that beats Mixed-In-Key.
- **Gap (claimed "deferred" — accurate):** Download/verify/install machinery is **built and CLI-wired**; the ONE missing piece is a hosted artifact URL — no default ships, so clean-machine users silently fall to the heuristic.
- **Evidence:** `_CUE_URL_ENV`/`_CUE_SHA_ENV`/`_CUE_SIZE_ENV` `model_assets.py:26-28`; raise-with-message at `:453-455`; installer wired `__main__.py:5873/5897`. *(codegraph_search + Read)*
- **Smallest action:** OPS decision — host the 167MB file (CDN/HF/Bravoh), pin the three env defaults. No new engineering. Optional follow-on: add lazy inference-time autofetch (today fetch is CLI-only).

### g14 — Beatmatch dimension: producer is the only missing wire (high · PARTIAL · WIRE_IT)
- **Brings:** Unlocks the v11.0 Earned Wall "Mastered" stage for **beatmatching** — the headline DJ skill.
- **Gap (claimed "deferred" — accurate):** Engine (`grade_beatmatch`) + consumer (`skill_recognizer` BEATMATCH_GRADED branch) both shipped; **no production emitter** exists, so crediting can never fire live.
- **Evidence:** `grade_beatmatch` `learn/beatmatch_judge.py:83`; consumer `skill_recognizer.py:153→169`. `grep BEATMATCH_GRADED src/ tauri/` → tests only. Deferral pinned `tests/repo/test_live_reality_pins.py:126/144`. *(codegraph + grep)*
- **Smallest action:** Build the producer — a live loop on an OWNED-deck MiniDeck mix that grabs two BeatGrids + DeckState → `grade_beatmatch` → `grade_to_event_extra`, fires the event AND registers the `("ev","BEATMATCH_GRADED",t)` citation. (Learn-module/MiniDeck feature, not a live BlackHole-monitor set.)

### g27 — Live drop fusion: cited DROP_HIT on prior×live-edge agreement (high · PARTIAL · WIRE_IT)
- **Brings:** The AI calling a real drop without inventing one — the prior is the precision filter that promotes a genuine kick-return over a routine filter sweep.
- **Gap (claimed "wired" — partly false):** Prior leg shipped+tested+single-writer; live confirm leg (kill→reentry) shipped+live; but the **fusion gate** (cited DROP_HIT on ±1-bar agreement) is genuinely unbuilt. Correction: `predicted_drop_in_sec` is NOT read only by the debug logger — it also feeds a UI drop-chip (`ws_bus.py:627`).
- **Evidence:** `predict_drop_in_sec` `state/drop_predict.py:25`, written `refresh.py:957-982`. `grep DROP_HIT src/` → only debrief parse-example strings, no runtime event type. `BreakdownKickKill`+`ReentryKickLand` live in `events/genres/techno.py:59-60`. *(grep + Read + codegraph_search)*
- **Smallest action:** 5 scoped steps (map sec.6): bench prior signed-error → latch `predicted_drop_in_sec` at `last_kill_at` → add DROP_HIT event + EVIDENCE_SOURCES join + `[ev:]` citation + linter **in one commit** → wire agreement gate → live ear-verify. HARD GATE: Kaan's ear on ±1-bar timing; keep flag-gated until measured.

### g3 — Section-vector centering (the open half of the anisotropy fix) (moat · PARTIAL · WIRE_IT-later)
- **Brings:** Keeps the anisotropy fix consistent at section granularity.
- **Gap (claimed "shipped" — overstated as a gap):** Whole-track centering is DONE, factored, cached, default-on, regression-gated. Section vectors ARE built and stored, just consumed RAW in `transition_scorer._semantic_score` — and that scorer has **no live runtime caller** surfaced today, so centering them changes nothing a user hears yet.
- **Evidence:** `centering.py` (compute_centroid `:61`, center_and_renorm `:75`); live on search `search.py:130-134`, pill `next_suggestion`/`SuggestionService __main__.py:1610`. Raw section cosine `transition_scorer.py:325-327`. *(Read + codegraph)*
- **Smallest action:** Route `_semantic_score` source/dest section vectors through `centering.center_and_renorm` — but only WHEN the transition scorer goes live. Also fix the doc: `excerpt.py::CUE_WINDOW_SECONDS=80` does not exist (real windowing is bar-relative `_WINDOW_BARS`/`_MAX_WINDOW_S` in `cue_engine.py`/`cue_detect.py`).

### g22 — Universal Serato Markers2 cue carrier (moat · PARTIAL · WIRE_IT)
- **Brings:** Cleanest OSS cue-export thesis — one ID3 GEOB write read natively by Serato + Mixxx + Rekordbox, no live-DB corruption risk.
- **Gap (claimed "shipped" — overstated):** Module real + tested + `serato`/mutagen extra pinned, but (a) orphaned at the top — `tag_folder_serato` has **no CLI/Tauri trigger**; (b) claim of tri-container (ID3+FLAC+MP4) is FALSE — only ID3 GEOB ships, FLAC/MP4 are stubs returning `written=False`; (c) write-BACK absent.
- **Evidence:** `write_serato_cues` `export_serato.py:224` ← `tag_folder_serato cue_folder.py:238` ← NOTHING in src/tauri. `_ID3_SUFFIXES=(".mp3",".aif",".aiff")` `:179`; FLAC/MP4 follow-up at `:245-250`. *(codegraph_callers + Read)*
- **Smallest action:** Add `library cue-folder <dir> --write-tags` calling `tag_folder_serato(allow_write=True)` + surface in Tauri. Follow-on frontiers: FLAC base64 Vorbis + MP4 atom carriers; true write-back.

### g40 — Proxy-default flip (keyless zero-config) (moat · PARTIAL · WIRE_IT)
- **Brings:** A fresh user with no GEMINI_API_KEY actually hears the co-host — the headline ship-blocker for keyless onboarding.
- **Gap (claimed "deferred" — accurate):** Keyless self-provision machinery (`ProxyClient.register` → install_uuid+JWT) is **built AND call-wired** into `main()`. The only missing piece is the default: empty mode resolves to `"direct"` → `sys.exit(4)`.
- **Evidence:** `__main__.py:776-777` default `direct`; `:802-810` fatal exit without key; `register` `proxy_client.py:118`, `_request_jwt:160`, default base `api.altidus.world`. *(Read + codegraph_context)*
- **Smallest action:** One-literal flip of the default arm (or wizard sets `llm_mode="proxy"` for keyless users) — but SEQUENCE: provision a live proxy Gemini key + TTS provider FIRST (memory: both Bravoh keys reported DEAD), else the flip replaces `sys.exit(4)` with a silent-mute brain.

### g38 — Local MOSS-TTS never-mute voice: proxy-parity gap (high · WIRED_LIVE core, one PARTIAL follow-up)
- **Brings:** Free on-device never-mute voice (71ms TTFT / 0.18 RTF), -76% cost, no key — the fix for "co-host never speaks (Gemini TTS fails→mute)."
- **Gap:** Core is WIRED_LIVE (`local_tts_enabled`, `MossLocalTTS`, real `moss_tts/ort_cpu_runtime.py` backend, prepend in `_build_direct_chain tts_chain.py:118-123`, reaches `AgentSession(tts=tts_inst) __main__.py:1646`). The one real code TODO: the MOSS prepend lives ONLY in the direct builder — **proxy/keyless mode does NOT get the local voice**.
- **Evidence:** `tts_chain.py:78/116-123`; `build_proxy_tts_chain proxy_client.py:61` (no MOSS prepend). *(codegraph_search + grep + Read)*
- **Smallest action:** Mirror the MOSS prepend into `build_proxy_tts_chain` so the never-mute guarantee covers proxy users. (Plus Kaan ear-verdict + Windows path + tier shape — product gates.)

### g37 — Earned Wall render seam (moat · WIRED_LIVE — claim STALE)
- **Status:** Claimed "deferred/dark"; reality = **the render seam is wired end-to-end**. `which_handler('ipc.learn.progress_state')` = WIRED both ends; `SkillWall.ts:188` reads `progress.skill_wall` and repaints; mounted via `shell/app.ts:73-74`. The claim's premise (frontend reads `.skills/mastered/competent`) is even wrong on the field name. Residual = a live `drive-vibemix` eyeball, not wiring.

### g43 — Two dead seams: emote→mascot + overlay-highlight listener (high · PARTIAL · WIRE_IT)
- **Brings:** "Overlay highlights the cue the co-host names" (highest-scored buildable constellation) + mascot reaction emotes.
- **Gap (claimed "deferred" — accurate):** Both halves built on both ends; the connecting call is missing.
- **Evidence:** `emote_parser.py:65/80` has ZERO runtime callers (grep); `last_reaction_intent` set as dataclass default only (`music_state.py:171`), read in broadcast (`ws_bus.py:959`) — always ships None. `startOverlayHighlightListener overlay-highlight.ts:42` never started; Python emits live (`dj_cohost.py:979/1143/2988`). *(codegraph_callers + grep)*
- **Smallest action:** Seam 1 — `strip_emote_tags(reply)`→TTS, assign intent to `state.last_reaction_intent`, teach persona `[emote:*]`. Seam 2 — start `startOverlayHighlightListener` on the session window. ANTI-SLOP CAVEAT: gate the overlay highlight on the same evidence the reaction cited (Inv #2/#3). dj_cohost.py is dirty — verify against current source.

### g44 — Orphaned one-click install chain (high · PARTIAL · WIRE_IT)
- **Brings:** Zero-touch install (driver fetch / 48k probe / BlackHole) so every audio gap is handled by the wizard, not the user — Kaan's "install→wizard→works" bar.
- **Gap (claimed "deferred" — accurate):** TS steps + Rust `run_companion_fetch` + `fetch_drivers.sh` built on both ends; steps **absent from STEP_ORDER and rendered nowhere** (dead code). Driver SHA is still a **PLACEHOLDER**.
- **Evidence:** `STEP_ORDER router.ts:168-176` lacks the 3 steps; no render-switch case `:350-595`; `driver_manifest.json:10/20` literal `PLACEHOLDER_REAL_SHA256...`. *(Read full router.ts + grep)*
- **Smallest action:** Finish plan-49-04 (add to STEP_ORDER + render switch + back() + wire to `run_companion_fetch`/48k probe). GATE: populate real SHA256s (Kaan/SignPath external clock). Caveat: sibling audit argues the 48k probe should become *advisory* (since native-rate capture now works — see g39) rather than load-bearing.

### g45 — Debrief → shareable cited recap PNG (the viral flywheel) (high · PARTIAL · WIRE_IT)
- **Brings:** GitHub-star/waitlist flywheel — a cited recap card ("9 TRACKS · 1H 12M IN THE MIX").
- **Gap (claimed "deferred" — accurate):** Full debrief substrate built (TL;DR, drills, `citation_event_id` threaded, `buildVerdictText` headline already in `tldr-player.ts`, profile writeback). Genuinely absent (grep zero): the **Canvas→PNG card** and the **session-recap aggregate producer**.
- **Evidence:** `drills.py:225`/`tldr.py:137`; `grep canvas|todataurl|toblob debrief/` → 2 non-functional hits (placeholder string `debrief-window.ts:351` + CSS). *(codegraph + grep)*
- **Smallest action:** (a) build the session-recap aggregate producer over the existing debrief ws bus; (b) a debrief-window Canvas→PNG card re-applying `stripper.py` cited-only gate. Ships the TRUE subset now; "top mix" headline inherits later from the Judge→recorder wire.

---

## 3. CLAIMED-BUT-NOT-WIRED (anti-hallucination recovery)

Where a prior doc/workflow asserted more than reality-check found. The reality-check ITSELF caught and retracted many premature mid-session verdicts; those self-corrections are noted because they are the recovery.

| id | The false/overstated claim | Source of claim | The truth at HEAD 0e7bdc1c |
|---|---|---|---|
| **g28** | "make the AI SPEAK the drop" = clean-room 15Hz transition clock + spoken reel, files exist (PRESENT_ORPHANED, "17 tests"). | `.planning/singularity/2026-05-31/census-cue-detection.md:116-148` | **CLAIMED_BUT_ABSENT.** None of the 4 files exist on disk (`transition_clock.py`, `drop_reaction.py`, `automix_demo.py`, `automix_demo_smoke.py`) AND both cited source docs are absent. Likely on a different branch/uncommitted tree (this is `live-tuning-or-brain`, not the singularity worktree). Verdict: INVESTIGATE via `git log --all` before WIRE_IT/DROP. *(Read negatives in a verified-working window; codegraph+LSP were down.)* |
| **g20** | Cited source `.planning/singularity/2026-05-31-singularity-map.md` | doc path | Source doc **does not exist** at HEAD; the `.planning/singularity/` dir is absent. Deferral is real but corroborated by the `one_mind` memory, not the cited doc. |
| **g17** | "taste_model NOT wired into the pill, which ranks vibe-only; joining taste→next_suggestion is the single biggest remaining lever." | `.planning/singularity/2026-05-31-whats-next.md:21-22`; `constellation-map.md:44` | **FALSE.** `taste_scores` is a first-class param on `next_suggestion` (`:120`); live `SuggestionService` passes `self._taste_scores` into every ranking call (`suggestion.py:976/1192/1228/1276`) with `update_taste_scores()` hot-swap (`:413`). S2 persona half also wired. Already-done (One-Mind S2+S3). Correct the source docs. |
| **g39** | Zero-config audit: `open_capture` still hard-asserts 48000 on both OSes, crashes on factory 44.1k (mis-grounds every event ~8.8%). | `.planning/2026-05-30-zero-config-ship-blockers.md:19-35` | **STALE/FALSE at HEAD.** Master+mic on both OSes open at device `default_samplerate` and resample in-callback; no 48000 assert. Audit predates commits #19/#25/#91. `_audio_macos.py:123-213`, `_audio_windows.py:45-125`, `__main__.py:400-424`. |
| **g37** | "no learn view reads `.skills/mastered/competent`; the trophy wall is computed, persisted, and invisible." | `.planning/2026-05-30-constellation-star-chart.md:48-68`; `dead-path-and-wiring-audit.md:30-36` | **STALE.** SkillWall.ts built + mounted (`shell/app.ts:73`) AFTER those audits; reads `progress.skill_wall` (not `.skills`). Render seam WIRED both ends. |
| **g8/g25/g29/g38** (sibling-harvester disagreements) | Multiple harvesters claimed `judge_voice.py` / `cue_folder.py` / `cue_agreement` comparator do NOT exist on disk; or claimed `_moss_onnx.py` is the TTS backend. | intra-session harvest | All **exist** (source-grounded harvest correct): `judge_voice.py` (4821B), `cue_folder.py` (11k, 2026-05-31), `cue_agreement.py` (comparator shipped), real TTS backend is `moss_tts/ort_cpu_runtime.py` (the named `_moss_onnx.py` is absent). Likely-stale-index or pre-untracked-drop reads. |
| **g13** | "CUE/CLAP never runs in CI; INTEL-THRESHOLD-LOCK.md needs authoring; tracers built-but-unwired." | `.planning/singularity/2026-05-31/ROADMAP-SINGULARITY.md:29-33` | **STALE.** `eval/INTEL-THRESHOLD-LOCK.md` + `threshold_lock.py` + tests exist; `.github/workflows/eval.yml` exists; `tests/library/test_clap_real_retrieval.py` exists; `SessionTracer`/`StrippedRateTracker` live-instantiated in `__main__`. (Residual: verify eval.yml actually invokes the real-CLAP test + recall@k assertion + replay-grader seam.) |
| **g9/g11** (memory note) | Memory: "coach.py:813 live-wiring deferred (dirty HARD-HOLD)." | `project_codex_inbox_coordination` memory | **STALE** — the live judge call is present at `coach.py:812-823` / `:819-831` today. |

**Self-corrected reality-check verdicts (recovery in action):** g5, g6, g7, g9, g10, g11, g15, g16, g19, g30, g31, g32, g33, g36, g41, g42 each began as a premature PRESENT_ORPHANED/INVESTIGATE/tool-failure call and were **retracted** after tools recovered or after searching the correct symbol name (e.g. `judge_transition` not `grade_transition`; `verdict_evidence_line` not `voice_judge_verdict`; `load_taste_model`/`build_taste_model` not bare `TasteModel`). Lesson logged in-row: trust the codegraph/repo-wide token scan over a hand-picked symbol list.

---

## 4. RESURFACE CANDIDATES (valuable, dropped/never-built, worth reviving — ranked)

1. **g24 — Host the CUE-DETR model** (high). One ops decision (host 167MB + pin 3 env defaults) flips the default cue path from weak-heuristic to real DETR. All download/verify/install code already built. The single blocker to a free auto-cue tool that beats Mixed-In-Key.
2. **g42-A — Off-the-wire deck identity (Pro DJ Link UDP 50000-2 / StagelinQ 51337 / VDJ-OSC)** (high · NEVER_BUILT). The only path to a `supported_verdict` tight-blend grade on rigs where audio can't be split (Denon/StagelinQ, pro-VirtualDJ, CDJ-hardware rekordbox). Collision-safe new-file work; well-documented protocols; no audio split needed. `grep prolink|stagelinq|50000|51337 src/` → ZERO.
3. **g41 — Universal Gobble: VirtualDJ/Traktor/Mixxx/Serato parsers** (high · NEVER_BUILT against a WIRED_LIVE seam). The `TrackEntry` currency + `@runtime_checkable LibrarySource` Protocol + `ingest_source` orchestrator are built; only `RekordboxSource` exists. Each new parser is an S-effort collision-free island (`library/sources/<eco>.py`) and the whole CLAP/Viber/pill/Earned stack lights up for free. Order: VirtualDJ → Traktor+Mixxx → Serato. *(base.py:35, ingest.py:710, sources/rekordbox.py:47 — codegraph_search)*
4. **g29 — Cue-agreement flywheel** (high · PARTIAL). The comparator `cue_agreement.py` is already SHIPPED (auto-vs-dj/anlz weak labels, honest-null) — the source claim "nothing compares the sources" is stale. Remaining = small wiring: persist `{label,auto_start,dj_start,delta_bars,agreed}`, aggregate consent-gated over ≥2 ingests into INTEL-THRESHOLD-LOCK.md (never auto-apply), raise per-user CUE-DETR confidence floor. Lowest-risk learning loop. First confirm whether `cue_agreement` is yet called in the ingest path.
5. **g42-B — live_claim_policy 6→3 GREEN/YELLOW/RED UX collapse** (high · WIRE_IT). Verdict engine already WIRED_LIVE (3 prod call-sites); its 6 internal strings just aren't surfaced as a 3-state status light. Cheap frontend job (map 6→3 + ipc field + chip). Guard: do NOT touch the policy call-sites (`coach.py` is concurrent-session-owned).
6. **g34 — Discovery-first hero ("DJs forget tracks they own")** (high · RESURFACE). The resurface ENGINE is fully live (`suggest_next`→pill, `find_similar`); what's NEVER_BUILT is the positioning/IA — a hero surface framing "you forgot tracks you own, here they are by vibe." Product/copy, not engine. Caveat: needs a recency/last-played signal to bias toward dormant crate items (absent today). Scope not committed.
7. **g22-frontiers — FLAC Vorbis + MP4 atom cue carriers, and write-BACK** (moat). Extends the universal cue claim to lossless/AAC libraries and bidirectional sync. After the basic `library cue-folder --write-tags` CLI lands (g22).

---

## 5. ALREADY DONE (confirmed WIRED_LIVE — do NOT redo)

- **g1** Grounded perception loop (capture→fuse→detect→cite→speak/strip) — the moat, single-writer + citation gate both test-enforced.
- **g2** Citation grounding anti-slop gate (Invariant #2), EVIDENCE_SOURCES incl. `[judge:]`, dual-grammar linter, DI'd registry.
- **g4** Deterministic Camelot/BPM table — LLM never computes keys; wired into 5 consumers.
- **g5** Vibe Judge pattern — engine decides, Gemini voices, abstains (deck_context guard + threshold calibration deferred = g12 + Kaan).
- **g6** Honest-null abstain-by-construction; full live call chain `judge_transition→judge_and_record→_run_live_judge→coach_loop`.
- **g7** `_run_live_judge` fires on TRACK_CHANGE → grounding+persistence+harmonic_mixing skill-credit.
- **g9** Two-citation dance + abstain-row persistence + 4-site grammar lock (voice line itself deferred = g8).
- **g10** Keystone — `_HONEST_UNCREDITABLE_V11` dropped to `("beatmatching",)`; harmonic_mixing now creditable via Judge.
- **g11** Judge's two DSP signals (harmonic + bass-collision), honest about coarseness.
- **g13** Eval/observability — threshold-lock doc, eval.yml, real-CLAP CI test, live tracers (claim stale; residual verifies only).
- **g15** Mixer-grounding gap CAUGHT — "you brought the faders up" with `recent_moves=[]` strips via `apply_live_claim_guard`.
- **g16** Slop = wiring bug, not Gemini — grounding enforced on model OUTPUT in live `llm_node`; do-not-regress.
- **g17** Taste model → pill re-rank (One-Mind S2+S3) — claim of "not wired" is false.
- **g18** The pill — CLAP mean-centered next-track engine, full ws→frontend chain (taste/energy/phrase moat filters deferred).
- **g19** Cue-anchored directional embeddings — per-section asymmetric (outro→intro) scoring live (literal "hot cue 2" per-slot retrieval = remaining seam).
- **g21** Energy-trajectory build-set on a real curve from the user's library — CLI+MCP+Tauri.
- **g26** Cue producer stack (drop heuristic + smart_cues A-H + ANLZ/PSSI floor) — all 3 legs live (`cue_folder()` batch helper is the lone orphan = g25).
- **g30** Codex-backed Viber agent, zero Gemini fallback (structurally enforced).
- **g31** `toolset.py` shared grounded tool core — seen-set closes 3 hallucination classes at the tool layer.
- **g32** Five grounded MCP tools (web_search/fetch_url/quote_moment/dj_knowledge/cue_export) — needs only TAVILY_API_KEY + corpus to be useful.
- **g33** Telegram bridge — fail-closed allow-list, path-scrub, 90s timeout, lazy dep.
- **g35** Cost guardrails — SessionMeter live on the LLM stream, BudgetTelemetry, `library budget` CLI (proxy caps + pricing ladder correctly external).
- **g36** Earned skill-tree — two-stage mastery, `skill_recognizer` wired live in `coach_loop` (cited→credit/un-cited→zero); Kaan ear/hardware gates only.
- **g37** Earned Wall render seam — wired both ends (claim stale).
- **g38** (core) Local MOSS-TTS prepend → live AgentSession (proxy-parity prepend = small follow-up).
- **g39** Per-deck awareness + native-rate 44.1k capture (master+mic, both OSes).
- **g41** (seam) `LibrarySource` Protocol + `ingest_source` + `TrackEntry` currency, live via `library ingest`.

---

## 6. FULL LEDGER

| id | idea | theme | value | claimed | code_status | rec | evidence (file:line · tool) | source |
|---|---|---|---|---|---|---|---|---|
| g1 | Grounded perception loop = the moat | grounding | moat | shipped | WIRED_LIVE | ALREADY_DONE | `state_refresh_loop refresh.py:1083`←`main __main__.py:738`; `_build_citation_strip dj_cohost.py:665` · codegraph_node/callers+grep | KNOWBOOK §1 |
| g2 | Citation grounding anti-slop gate (Inv #2) | grounding | moat | shipped | WIRED_LIVE | ALREADY_DONE | `EVIDENCE_SOURCES evidence_registry.py:18`; `filter_reaction←coach.py:503` · codegraph_callers+Read | KNOWBOOK §7 |
| g3 | Mean-centering CLAP; section vectors raw | embeddings | moat | shipped | PARTIAL | WIRE_IT-later | `centering.py:61/75`; raw `transition_scorer.py:325-327` · Read+codegraph | singularity-map:15 |
| g4 | Deterministic Camelot/BPM table | grounding | moat | shipped | WIRED_LIVE | ALREADY_DONE | `is_clash harmonics.py:278`; `transition_judge.py:139` · codegraph_search+grep | constellation:37 |
| g5 | Vibe Judge pattern | judge | moat | shipped | WIRED_LIVE | ALREADY_DONE | `judge_transition transition_judge.py:45`; `coach.py:303/359` · codegraph+Read | the-vibe-judge.md:20 |
| g6 | Honest-null abstain-by-construction | judge | moat | shipped | WIRED_LIVE | ALREADY_DONE | `_abstain transition_judge.py:88-91`; chain→`coach_loop coach.py:405` · codegraph_callers+Read | transition_judge.py:45 |
| g7 | `_run_live_judge` on TRACK_CHANGE | judge | moat | wired | WIRED_LIVE | ALREADY_DONE | gate `coach.py:913`; `record_demonstration skill_recognizer.py:247` · codegraph+LSP | coach.py:813/327 |
| g8 | judge_voice voice bridge | judge | moat | wired | PARTIAL | **WIRE_IT** | `verdict_evidence_line judge_voice.py:32` 0 callers; TODO `coach.py:793` · codegraph_callers+grep | judge_voice.py:32 |
| g9 | Two-citation dance + 4-site grammar lock | judge | high | shipped | WIRED_LIVE | ALREADY_DONE | `JUDGE_CITATION_SOURCE transition_judge_runtime.py:29`; lock test `:20-57` · codegraph+Read | runtime.py:29 |
| g10 | Keystone: Judge retires harmonic from wall | learn | high | shipped | WIRED_LIVE | ALREADY_DONE | `_HONEST_UNCREDITABLE_V11=("beatmatching",) skill_recognizer.py:104` · Read+codegraph_callers | skill_recognizer.py:104 |
| g11 | Two trustworthy DSP signals | judge | high | shipped | WIRED_LIVE | ALREADY_DONE | `_harmonic_signal/_bass_collision transition_judge.py:128-168` · Read+grep | transition_judge.py:128 |
| g12 | Live-guard verdict-vs-adjective strip | grounding | moat | deferred | PARTIAL | **WIRE_IT** | `apply_live_claim_guard deck_context.py:2219` no judge branch; grep EXIT 1 · codegraph_node+grep | the-vibe-judge.md:1022 |
| g13 | Eval/observability buildout | observability | high | deferred | WIRED_LIVE | ALREADY_DONE | `eval/INTEL-THRESHOLD-LOCK.md`; `eval.yml`; tracers `__main__.py:926/1362` · find+grep | ROADMAP-SING:29 |
| g14 | Beatmatch dimension scaffolded | learn | high | deferred | PARTIAL | **WIRE_IT** | `grade_beatmatch beatmatch_judge.py:83`; no emitter (grep tests only) · codegraph+grep | beatmatch_judge.py |
| g15 | Mixer-grounding #1 live slop bug | grounding | high | wired | WIRED_LIVE | ALREADY_DONE | guard `deck_context.py:2256`; emit `dj_cohost.py:2738-2755` · Read | KNOWBOOK §8 |
| g16 | Slop = wiring bug not Gemini | grounding | moat | wired | WIRED_LIVE | ALREADY_DONE | `llm_node dj_cohost.py:1869`→registry drop; `recent_moves[8s]:NONE coach.py:512` · codegraph+Read | KNOWBOOK |
| g17 | Taste model → pill re-rank | engine | high | proposed | WIRED_LIVE | ALREADY_DONE | `taste_scores next_suggestion.py:120`; `suggestion.py:976` · codegraph_search+grep | whats-next:21 |
| g18 | The pill next-suggestion engine | pill | high | shipped | WIRED_LIVE | ALREADY_DONE | `SuggestionService suggestion.py:34`→`_suggestion_loop session_loop.py:340`→`pill/index.ts:69` · codegraph | whats-next:19 |
| g19 | Cue-anchored directional embeddings | embeddings | moat | wired | WIRED_LIVE | ALREADY_DONE | `_ensure_section_vectors ingest.py:635`; asym `transition_scorer.py:515` · codegraph_callers+Read | research-similarity:6 |
| g20 | claim_validator → live brain (S1) | grounding | high | deferred | PRESENT_ORPHANED | **WIRE_IT/INVESTIGATE** | `validate_claim claim_validator.py:60` 0 prod callers; intel 0 importers · codegraph_callers+grep | singularity-map:24 (absent) |
| g21 | Energy-trajectory build-set | set-prep | high | shipped | WIRED_LIVE | ALREADY_DONE | `build_set_with_codex codex_curate.py:1072`; `sequence_set←mcp_server.py:333` · codegraph+Read | research-energy:6 |
| g22 | Universal Serato Markers2 carrier | cue-export | moat | shipped | PARTIAL | **WIRE_IT** | `write_serato_cues export_serato.py:224`←`tag_folder_serato cue_folder.py:238`←NOTHING · codegraph_callers+grep | map-export:41 |
| g23 | CUE-DETR ONNX producer (THE MOAT) | cue-engine | moat | wired | PARTIAL | **WIRE_IT** | `detect_cue_positions cue_detr.py:287`; no `cue` subparser (grep EXIT 1) · codegraph+grep | census-cue:49 |
| g24 | Host the CUE-DETR model | cue-engine | high | deferred | PARTIAL | **RESURFACE** | env vars `model_assets.py:26-28`; raise `:453`; no URL · codegraph_search+Read | PLAN-CUE-EXPORT:113 |
| g25 | `library cue <folder>` standalone CLI | cue-export | high | proposed | PARTIAL | **WIRE_IT** | `cue_folder.py` exists (11k, ls); subparser unconfirmed/missing · ls (tools degraded) | PLAN-CUE-EXPORT:61 |
| g26 | Cue producer stack (drop+A-H+ANLZ) | cue-engine | high | shipped | WIRED_LIVE | ALREADY_DONE | `detect_cues cue_detect.py`; `propose_smart_cues toolset.py:406`; ANLZ `excerpt.py:71` · grep+codegraph | census-cue:64 |
| g27 | Live drop fusion (cited DROP_HIT) | live-drop | high | wired | PARTIAL | **WIRE_IT** | `predict_drop_in_sec drop_predict.py:25`; no DROP_HIT runtime event (grep) · grep+Read+codegraph | map-live-fusion:9 |
| g28 | AI-speaks-the-drop transition_clock | content-gen | medium | dropped | CLAIMED_BUT_ABSENT | **INVESTIGATE** | 4 files + 2 docs absent (Read negatives, working window); codegraph/LSP down · Read | census-cue:116 (absent) |
| g29 | Cue-agreement flywheel | learning-loop | high | proposed | PARTIAL | **WIRE_IT** | `cue_agreement cue_agreement.py:116` SHIPPED; aggregation half missing · codegraph_search+grep | research-cue-boost:156 |
| g30 | Codex-backed Viber (no Gemini) | viber | moat | shipped | WIRED_LIVE | ALREADY_DONE | `library short-circuit __main__.py:17`; `_build_codex_cmd codex_curate.py:254`; gemini grep=0 · Read+grep | KNOWBOOK Viber |
| g31 | toolset.py shared grounded core | viber | moat | shipped | WIRED_LIVE | ALREADY_DONE | `self.seen toolset.py:113`; reject `:464-472` · Read (codegraph name-search blind for src) | research-grounding:6 |
| g32 | Five grounded MCP tools | viber | high | shipped | WIRED_LIVE | ALREADY_DONE | `build_server mcp_server.py:137`; 5 `@mcp.tool` `:352-401` · codegraph_search+Read | mcp_server.py |
| g33 | Telegram bridge fail-closed | viber | high | shipped | WIRED_LIVE | ALREADY_DONE | `parse_allowed_chats telegram_bridge.py:77`; timeout `:199-206` · codegraph_search+Read | telegram_bridge.py |
| g34 | Discovery-first hero | product | high | proposed | PARTIAL | **RESURFACE** | engine live `suggest_next next_suggestion.py:71`→`suggestion.py:518`; no UI framing (grep 0) · LSP+grep | discovery-wedge memory |
| g35 | Cost guardrails + €4.99 ladder | cost | high | wired | WIRED_LIVE | ALREADY_DONE | `get_session_meter().record dj_cohost.py:2615`; `library budget __main__.py:5685` · codegraph_callers+Read | budget.py |
| g36 | Earned skill-tree (2-stage mastery) | learn | moat | shipped | WIRED_LIVE | ALREADY_DONE | `recognize skill_recognizer.py:198`←`_credit_live_skill_demo coach.py:123/177` · codegraph_callees+git | v11_earned memory |
| g37 | Earned Wall render seam | learn | moat | deferred | WIRED_LIVE | ALREADY_DONE | `which_handler ipc.learn.progress_state`=both ends; `SkillWall.ts:188`; `app.ts:73` · which_handler+grep | star-chart:48 (stale) |
| g38 | Local MOSS-TTS never-mute voice | tts | high | wired | WIRED_LIVE(+1 PARTIAL) | ALREADY_DONE(+proxy-parity WIRE_IT) | `tts_chain.py:116-123`→`AgentSession __main__.py:1646`; proxy builder lacks prepend `proxy_client.py:61` · codegraph+grep | local_tts memory |
| g39 | Per-deck + native-rate 44.1k | audio | high | shipped | WIRED_LIVE | ALREADY_DONE | `_audio_macos.py:123-213` no 48k assert; `DeckRouter __main__.py:380` · Read+codegraph_callers | zero-config:19 (audit stale) |
| g40 | Proxy-default flip (keyless) | onboarding | moat | deferred | PARTIAL | **WIRE_IT** | default `direct __main__.py:776`; exit4 `:810`; `register proxy_client.py:118` built+called · Read+codegraph | zero-config:13 |
| g41 | Universal Gobble (N parsers, 1 Protocol) | interop | high | proposed | WIRED_LIVE(seam)/NEVER_BUILT(parsers) | **WIRE_IT/RESURFACE** | `LibrarySource base.py:35`; `ingest_source ingest.py:710`; only `RekordboxSource sources/rekordbox.py:47` · codegraph_search+grep | universal-gobble:9 |
| g42 | Live deck identity off-the-wire + 6→3 UX | interop | high | proposed | PARTIAL | **RESURFACE(A)/WIRE_IT(B)** | `live_claim_policy deck_context.py:2106` live; listeners grep=0; UX collapse unbuilt · codegraph_search+grep | universal-gobble:39 |
| g43 | Dead seams: emote→mascot + overlay listener | wiring | high | deferred | PARTIAL | **WIRE_IT** | `parse_emote emote_parser.py:65` 0 callers; `startOverlayHighlightListener:42` never started · codegraph_callers+grep | dead-path-audit:71 |
| g44 | Orphaned one-click install chain | install | high | deferred | PARTIAL | **WIRE_IT** | steps absent `STEP_ORDER router.ts:168`; SHA `driver_manifest.json:10` PLACEHOLDER · Read+grep | zero-config:49 |
| g45 | Debrief → cited recap PNG flywheel | debrief | high | deferred | PARTIAL | **WIRE_IT** | `drills.py:225`/`tldr.py:137` built; Canvas/PNG grep=0 (`debrief-window.ts:351` placeholder) · codegraph+grep | leverage-brief:47 |
