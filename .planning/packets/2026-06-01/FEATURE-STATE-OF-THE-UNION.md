# FEATURE-STATE-OF-THE-UNION.md

> vibemix — the founder's honest map of his own product. HEAD `ed081570` (`docs(product): separate viber agent from sven cohost`), branch `live-tuning-or-brain`. Read-only survey, every tag carries file:line / codegraph / packet-path / explicit NOT-FOUND. Verified against the 282-cap inventory + GOLD-WIRING-MAP — **and corrects two stale claims in those very docs** (see callouts).
>
> Provenance: dynamic workflow `wrjri13dx` (8 agents — 7 per-cluster surveyors + 1 union synthesizer, codegraph-verified, ~809k tokens, 7m34s). Raw surveyor cards: `_feature-state-raw-wf_wrjri13dx.json` (`.result.cards[0..6]` = viber / learn / cue+hotkeys / co-host-brain / library / watcher+cue-gui / memory+side-features; `.result.union` = this doc). Read-only — 0 product files touched.

---

## 1. ONE-SCREEN SUMMARY

| Feature | Works for a user today? | One-line state |
|---|---|---|
| **Co-host (live brain)** | **partial** | Perception→event→grounded-prompt→reaction spine is the strongest, most-tested part; reaches the GUI live. But it **narrates, not coaches** (move→sound physics orphaned), and **boots voice-MUTED on any machine but Kaan's** (MOSS not bundled/hostable). |
| **Viber / Crate (set-prep)** | **yes (wire), live-correctness unverified** | search/similar/curate/build-set/chat/cue all wired GUI→Tauri invoke→CLI subprocess→renderers; Codex-only backend, seen-set grounded. No captured real `codex exec` run. |
| **Library (embed/search/ingest)** | **partial** | CLAP engine + centered-cosine retrieval real-proven; ingest/embed/search work but `search`/`similar` are **CLI-only** (no GUI for raw text-search), the rest reachable via Crate. |
| **File-watcher (freshness)** | **yes** | **CORRECTS the inventory/GOLD-MAP "no watcher" claim** — `watch_library_freshness` runs live (`__main__.py:2300`), emits staleness nudges, handler wired. |
| **Cue / Hot-cue export** | **yes** | **CORRECTS the CORRECTION's "cue is CLI-only" claim** — a real `Cue` tab (`library.html:47`) → `invoke library_cue_folder` ships auto-cued Rekordbox/M3U8/Serato. |
| **Controllers / Hotkeys** | **partial** | FLX4 (Kaan's unit) golden-proven; 10 other profiles unverified (decode-only); push-to-mute hotkey wired. MIDI is **READ-only** (no outbound write). |
| **Memory / Recall** | **no (opt-in, dark)** | Full ingest→store→recall path built + wired, but `VIBEMIX_RECALL_ENABLED` default OFF and **no GUI toggle exists**. |
| **Debrief (post-session)** | **partial** | GUI-spawned 2nd window on :8766, cited-critique anti-slop gate, e2e-tested; Rust↔Python boundary never run together live. |
| **Mascot (VTuber)** | **partial (opt-in)** | Real 3D window + ~25 modules + CI fence, but DEMOTED to opt-in (default surface = Pill); off the default path. |
| **Learn / Earned (skill-tree)** | **partial** | v11 skill-tree wired end-to-end (recognizer→credit→Earned Wall→Mastered vocal), folds into shell sidebar; but **every "live demo credits a skill" path is synthetic-proven only**, and **beatmatching can never reach Mastered** (producer absent). |
| **Tune (gear-aware EQ tuner)** | **no** | **PLANNED-ONLY** — design packet only, zero code in `src/` or Tauri. |

---

## 2. PER FEATURE

### Co-host (live brain)
**BUILT+WIRED**

| Capability | Tag | Evidence |
|---|---|---|
| MusicState single-writer source of truth | BUILT+WIRED | `state/music_state.py:23-207`; single-writer test `test_refresh.py:880` |
| EventDetector typed events + per-type cooldowns | BUILT+WIRED | `event_detector.py:244-510`; cooldowns `audio/constants.py:77-120` |
| EvidenceRegistry (append-only, citation grounding) | BUILT+WIRED | `evidence_registry.py:222-542`; chokepoint `dj_cohost.py:3088` |
| CitationLinter — binary grounding gate (Invariant #2) | BUILT+WIRED | `coach/citation_linter.py:94-213`; un-cited → silence `dj_cohost.py:3161-3191` |
| Slop filter (63 NEGATIVE_PHRASES → whole-turn silence) | BUILT+WIRED | `prompts/filter.py:21-41` + `negative_dict.py:32-116` |
| English-only language guard | BUILT+WIRED | `agent/language_guard.py:73`; integration test passes |
| 8 genre-chain detectors + atomic GenreRouter swap | BUILT+WIRED | `state/detectors/*.py` + `genre_router.py:66-122` (140 tests) |
| The live Vibe Judge — TRACK_CHANGE blend verdict, `[judge:]` cite | BUILT+WIRED | producer `transition_judge_runtime.py:48`, call-site `runtime/coach.py:812-831` |
| skill_recognizer mastery credit (cited→credit, un-cited→zero) | BUILT+WIRED | `runtime/coach.py:156-213` |
| MOSS = the only TTS, no cloud/fake fallback; boots muted if absent | BUILT+WIRED | `agent/tts_chain.py:33-72`; `__main__.py:212` (default `VIBEMIX_LOCAL_TTS=1` @ `__main__.py:837`) |
| cohost-reaction citation chip (receipts) | BUILT+WIRED | producer `dj_cohost.py:3307`; FE `debug-log-ws.ts:30` + pill (live-fire pair never captured) |

**CLI-ONLY / FLAG-GATED (built, runs, but dark by default)**

| Capability | Tag | Evidence |
|---|---|---|
| KEY_CLASH harmonic-clash event + cited fragment | BUILT+ORPHANED (flag-dark) | `event_detector.py:383-422` gated by `_harmonic_clash_enabled=False`; logic tested, never fires |
| TRANSITION_OPPORTUNITY retrospective blend note | BUILT+ORPHANED (flag-dark) | `event_detector.py:424-482`, same gate |
| DROP event fixed-text reaction-bank say | BUILT+ORPHANED (flag-dark) | detector `event_detector.py:283`, gated `VIBEMIX_DROP_CALL` default OFF; say path `runtime/coach.py:704` |
| Recall block (past-session `[recall:]` cites) | BUILT+ORPHANED (flag-dark) | `coach.py:612-618` gated `VIBEMIX_RECALL_ENABLED` default OFF |
| Screen-vision deck reading | BUILT+ORPHANED (flag-dark) | `VIBEMIX_DECK_VISION` default OFF (`__main__.py:684`) |

**PLANNED-ONLY (the narrator→coach gap)**

| Capability | Tag | Evidence | Packet ref |
|---|---|---|---|
| **EQ-move physics resolver** (`intel/eq_move_model.py`) — the keystone that licenses cause-and-effect ("your low-kill thinned the bass") | PLANNED-ONLY | `ls intel/eq_move_model.py` → NOT-FOUND; grep `mixer_physics`/`expected_move_effect` = NOT-FOUND | `GOLD-WIRING-MAP.md` Card 1 + `CODEX_READY-eq-move-physics-keystone.md` + `recovered/wf_d9ddbeed-f5f__ALT1__mixxx-eq-filter-dsp...md` |
| Spectral/LUFS loudness receipt in coach loop | PLANNED-ONLY | only `library/energy.py::_loudness_dbfs:321` (library-only, not coach) | `GOLD-WIRING-MAP.md` Card 2 |

---

### Viber / Crate (set-prep)
> **CORRECTION applied:** the recovered Viber packet's #1 finding ("entire Crate IPC backend orphaned, every control dead") is **FALSE** — the UI reaches the backend via Tauri `invoke()`, not the dead `ipc.library.*` ws-bus (`viber-capability-CORRECTION.md`). Verified this session.

**BUILT+WIRED**

| Capability | Tag | Evidence |
|---|---|---|
| Full-stack wiring FE → Rust → Python CLI (9 `library_*` commands) | BUILT+WIRED | registered `main.rs:105-114`; commands `library_cmds.rs:503+`; invokes `library/api.ts:2354-2546` |
| search / similar / curate / build-set / chat / embed / stats / models (Crate tabs) | BUILT+WIRED | renderers `library/index.ts` (`renderBuildSet:498`, `renderChatSide:1259`); mode-switch `index.ts:2036-2043` |
| Live `[viber-tool]` tool-trace tape | BUILT+WIRED | `onViberTool` `index.ts:2065`→`appendLiveToolRow:1169`; Rust formats `library_cmds.rs:333` |
| Seen-set anti-hallucination gate (Invariant #2 at tool boundary) | BUILT+WIRED | `toolset.py:326/465/545/739/847` |
| Freshness guard (fail-closed) + Factor-7 clarification + tool-starvation stop | BUILT+WIRED | `toolset.py:170-222`, `:1143-1305`, `:1090-1141` |
| Codex backend auto-config from GUI (no env by hand) | BUILT+WIRED | `library_cmds.rs:121,130` force-sets `VIBEMIX_LIBRARY_AGENT_BACKEND=codex` (+`ALLOW_SHELL=1` on `--backend codex`); Codex-absence → actionable `codex_not_installed`/`codex_auth_required` rationale (`codex_curate.py:720-845`, mapped `library_cmds.rs:1584`) — **not a dead button** |

**CLI-ONLY**

| Capability | Tag | Evidence |
|---|---|---|
| web_search / fetch_url (Tavily) | CLI-ONLY (key-gated) | `toolset.py:1531-1532`, `web_research.py:86,165`; needs `TAVILY_API_KEY` (unprovisioned) → honest `_NO_KEY_ERR`, reachable in GUI chat but inert |
| retrieve_dj_knowledge (RAG) | CLI-ONLY (empty-corpus) | `toolset.py:1535`, `dj_knowledge.py:256-278`; ships EMPTY → honest-null `{"results":[],"note":"knowledge base empty"}` |
| Telegram mobile Viber surface | CLI-ONLY (`telegram` extra + token) | `__main__.py:3262`; needs `VIBEMIX_TELEGRAM_TOKEN` + `VIBEMIX_TELEGRAM_ALLOWED_CHATS`; ZERO `tauri/` references |
| `export-set` (standalone built-set → Rekordbox XML) | CLI-ONLY | `__main__.py:3249`; **no** `library_export_set` invoke reg (`main.rs:104-117`); GUI Rekordbox export only via build-set `--export rekordbox` |

**BUILT+ORPHANED**

| Capability | Tag | Evidence |
|---|---|---|
| `quote_moment` (grounded [start,end] ref) | BUILT+ORPHANED | `toolset.py:1533,1029` — callable inside any GUI Viber run but no dedicated UI control; the agent must elect it |
| raw `cue_export` MCP tool | BUILT+ORPHANED (guard-excluded) | `toolset.py:99` guard `test_shared_toolset_does_not_dispatch_raw_cue_export_tool`; cue export reaches users only via the separate `library_cue_folder` cmd |
| codex_curate backend (real `codex exec`) | BUILT+ORPHANED (subprocess mocked) | `codex_curate.py:673-973`; `test_codex_curate.py` mocks the subprocess — no captured real run |

**PLANNED-ONLY (built then deleted, guard-tested OUT)**

| Capability | Tag | Evidence | Packet ref |
|---|---|---|---|
| YouTube ingest (`ingest_youtube`) | PLANNED-ONLY (deliberate non-feature) | module deleted `4664ae9c`; dispatch returns `unknown tool 'ingest_youtube'` (`toolset.py:1539`); guards `test_toolset.py:54,90`. Re-adding breaks keyless-local-first | `.planning/research/youtube-ingestion-gemini.md`; memory `project_viber_capability_expansion.md` (2026-05-29 ⛔) |

---

### Library (embed / search / ingest)
**BUILT+WIRED**

| Capability | Tag | Evidence |
|---|---|---|
| Mean-centering / anisotropy fix (REAL-proven) | BUILT+WIRED | `library/centering.py`; `test_clap_real_retrieval.py` raw 0.85→centered −0.15 over committed real vectors |
| Centered-cosine vibe ranking (production search path) | BUILT+WIRED | `_cosine.cosine_topk`; recall@1 0.5 / recall@5 0.83 over 6 real tracks |
| Evidence-registry library registration (`[track:<id>]`) | BUILT+WIRED | `__main__.py:1638` `register_library(lib)` (live citation resolve unverified) |
| next_suggestion pill engine ("what's next") | BUILT+WIRED | `library/next_suggestion.py` → `runtime/suggestion.py`, ws-merged `ws_bus.py:875-907` |

**CLI-ONLY**

| Capability | Tag | Evidence |
|---|---|---|
| `library search` (text→tracks) | CLI-ONLY | `__main__.py:2733`; no GUI consumer for raw text-search |
| `library similar` (track→similar) | CLI-ONLY | `__main__.py:2745`; CLI-only |
| `library ingest` / `embed-folder` / `stats` / `models` / `budget` / `doctor` | CLI-ONLY (ingest/models also via Crate "models" button) | `__main__.py:3213/2760/3127/3163/3120/3176` |

**BUILT+ORPHANED**

| Capability | Tag | Evidence |
|---|---|---|
| CUE-DETR ONNX producer | BUILT+ORPHANED (model not hosted) | `library/cue_detr.py`; proven cue path uses the *heuristic*; model "not hosted by default" `model_assets.py:458` |
| `audio_decode` transformers branch | BUILT+ORPHANED (dead) | `test_audio_decode.py:81` SKIPPED (no transformers); ship path is PyAV/FFmpeg |
| `library budget` under-€50 gate | BUILT+ORPHANED (XFAIL) | `test_monthly_projection_under_50_eur` is XFAIL — free-at-scale claim unproven |

---

### File-watcher (library freshness)
> **CORRECTS BOTH the inventory ("No library/file watcher — STANDS") AND the CORRECTION ("no watcher").** At HEAD `ed081570` it exists and is live-wired (refactor-split `b8d19ba2`, 2026-06-01).

| Capability | Tag | Evidence |
|---|---|---|
| `watch_library_freshness` event-driven watcher loop | BUILT+WIRED | `library/watcher.py` (uses `watchfiles.awatch`); started as `_freshness_watch_task` `__main__.py:2300-2301` |
| `ipc.library.staleness_nudge` emit (sticky/replayed) | BUILT+WIRED | `__main__.py:2276` `_watcher_staleness_emit`; schema type present |
| `ipc.library.staleness_action` handler (refresh/snooze) | BUILT+WIRED | `__main__.py:2236-2251` `_on_library_staleness_action`, clears retained nudge |

---

### Cue / Hot-cue export
> **CORRECTS the CORRECTION's "No cue-export GUI — CLI-only — STANDS / true highest-value UI gap".** It IS wired to the GUI at HEAD.

| Capability | Tag | Evidence |
|---|---|---|
| Cue tab → auto-cued folder → Rekordbox/M3U8/Serato export | BUILT+WIRED | `<button role="tab" data-mode="cue">Cue</button>` `library.html:47` → `index.ts:2036` → `runCueExport:1975` → `invoke("library_cue_folder")` `api.ts:2546`; cmd `library_cmds.rs:820`; reg `main.rs:109` |
| Serato Markers2 (UNIVERSAL carrier, merge-preserving) | BUILT+WIRED (via Cue tab; eye-check owed) | `library/export_serato.py` (GEOB merge :201) |
| Cue heuristic engine (REAL-audio proven) | BUILT+WIRED | `library/cue_detect.py`; `test_cue_detect_eval.py` label_recall 1.0 over 6 real mp3s |

---

### Controllers / Hotkeys
**BUILT+WIRED**

| Capability | Tag | Evidence |
|---|---|---|
| FLX4 MIDI decode + golden profile (Kaan's owned unit) | BUILT+WIRED | `midi/state.py:299-420`; byte-pinned `test_profile_flx4_golden.py` |
| find_mapping (port→profile) + generic-MIDI fallback | BUILT+WIRED | `midi/registry.py:23-70`; `midi/generic.py` |
| MIDI hot-plug watcher + cross-platform listener thread | BUILT+WIRED | `__main__.py:1880` `start_port_watcher` (hardware-unproven) |
| Push-to-mute global hotkey (Cmd+Shift+M) + rebind | BUILT+WIRED | `hotkey.rs:register_default` `main.rs:168`; `rebind_hotkey` cmd |

**BUILT+ORPHANED / ABSENT**

| Capability | Tag | Evidence |
|---|---|---|
| 10 non-FLX4 controller profiles | BUILT+WIRED but HARDWARE-UNVERIFIED | 11 JSONs in `midi/profiles/`; `notes` flag "unverified" (only FLX4 physically owned) |
| Outbound MIDI write (AI takes the deck) | ABSENT | grep = READ/decode only; no write path |
| Windows per-deck audio capture | PLANNED-ONLY / ABSENT | `_audio_windows.py` is master-loopback stereo only; no `DeckAudioCapture` (deck-pair grounding is macOS-only) |

---

### Memory / Recall
| Capability | Tag | Evidence |
|---|---|---|
| MemoryStore + MemoryRecall + ingest pipeline | BUILT+ORPHANED (opt-in, dark) | `memory/store.py`, `retrieval.py:262`, `ingest.py:411`; all gated `recall_enabled` default OFF |
| Recall live dispatch in agent | BUILT+ORPHANED (flag-dark) | `dj_cohost.py:1734`, constructed `__main__.py:1558` behind default-OFF flag |
| **GUI toggle for recall consent** | ABSENT | grep `recall`/`memory` in `SettingsDrawer.ts` = **empty**; no surfaced control to enable it |

---

### Debrief (post-session review)
| Capability | Tag | Evidence |
|---|---|---|
| Debrief GUI launch (Rust spawns `--debrief` sidecar, 2nd window :8766) | BUILT+WIRED | `debrief_window.rs` + `__main__.py:533`; opened via `open_debrief_window` cmd (Rust↔Python live boundary untested together) |
| Cited-critique builder + uncited-stripper (anti-slop gate) | BUILT+WIRED | `debrief/main.py:142-174`; `test_no_uncited_critique_in_debrief.py` |
| Debrief→profile writeback (consent-gated) | BUILT+WIRED | `debrief/main.py:396`; `profile_writeback.py` |
| Chapter / TLDR-mp3 / drills generation | BUILT+WIRED (mock-client tested) | `debrief/{chapters,tldr,drills}.py` |
| Ear-test capture writer (Python) | BUILT+ORPHANED (dead) | `debrief/ear_test_capture.py:299` has NO importer; live path is Rust `ear_test_cmds.rs` |

---

### Mascot (VTuber)
| Capability | Tag | Evidence |
|---|---|---|
| 3D mascot overlay window (ws :8765, ~25 modules) | BUILT+WIRED but OPT-IN | `mascot.html:218`; built only if `primary_surface=mascot` (`main.rs:200`); default = Pill (`config.rs:47`) |
| mascot.mood_change push (drives expression) | BUILT+WIRED | emitted `__main__.py:1862`; `test_mood_change_envelope.py` |

---

### Learn / Earned (skill-tree)
**BUILT+WIRED**

| Capability | Tag | Evidence |
|---|---|---|
| Learn surface folds into DesktopShell sidebar | BUILT+WIRED | `shell/surface-mounts.ts:110` mountLearn; `open_learn_window` cmd `main.rs:115` |
| SkillTree pure stage derivation + 6-skill manifest + anti-drift gate | BUILT+WIRED | `learn/skill_tree.py:291`, `:129/:190` |
| Curriculum (3 courses, 37 lessons) + recital/graduation runtimes | BUILT+WIRED | `curriculum.py:240`; wired `__main__.py:2302-2366` |
| Lesson FSM (load→begin→ack→advance→complete, 45s anti-speedrun dwell) | BUILT+WIRED | `LessonRuntime` (`runtime.py`); 5 inbound `ipc.learn.*` handlers `learn/ipc_handlers.py:153` (live `__main__.py:2523`) |
| 10 `ipc.learn.*` both-ends channels | BUILT+WIRED | FE `learn/ws-client.ts:71`; Python `learn/ipc_handlers.py:524` |
| HONESTY BOUNDARY: beatmatching capped at Competent | BUILT+WIRED (correct anti-slop design) | `skill_tree.py:150`, `skill_recognizer.py:105` `_HONEST_UNCREDITABLE_V11=("beatmatching",)` |

**BUILT+ORPHANED**

| Capability | Tag | Evidence |
|---|---|---|
| Beatmatch Judge math engine ("the moat") | BUILT+ORPHANED | `learn/beatmatch_judge.py:83`; only consumer is the mapping in `skill_recognizer.py` — never fired by a producer |
| `_credit_live_skill_demo` / Earned-Wall refresh / Mastered vocal | BUILT+ORPHANED (synthetic-proven only) | `runtime/coach.py:123/220/256`; no live perception-loop capture |

**PLANNED-ONLY / ABSENT**

| Capability | Tag | Evidence | Packet ref |
|---|---|---|---|
| **BEATMATCH_GRADED producer** (so beatmatching can reach Mastered) | ABSENT (consumer exists, emitter doesn't) | grep `BEATMATCH_GRADED` fire = NOT-FOUND; consumer `skill_recognizer.py:154` | `recovered/wf_c297207c-6ae__the-mixxx-goldmine-map.md` (H1) |
| **H1 Practice-Deck Loop** (the keystone producer) | PLANNED-ONLY | `learn/practice_loop.py` / `practice_runtime.py` → NOT-FOUND | `recovered/wf_c297207c-6ae__...goldmine-map.md` |

---

### Tune (gear-aware EQ tuner)
| Capability | Tag | Evidence | Packet ref |
|---|---|---|---|
| Gear-aware sound tuner (agent researches gear → emits EQ host config) | PLANNED-ONLY | `find src -iname '*tune*'` = NOT-FOUND; no Tauri surface | memory `project_gear_aware_sound_tuner.md` (doc uncommitted, exploration→spec) |

---

## 3. THE IDEA GRAVEYARD (planned-but-unbuilt, ranked)

| Idea | Packet | Status | Worth-it |
|---|---|---|---|
| **EQ-move physics keystone** (`eq_move_model.py`) — flips live brain from narrator→coach | GOLD-WIRING-MAP Card 1 / `CODEX_READY-eq-move-physics-keystone.md` / `wf_d9ddbeed-f5f__ALT1` | PLANNED-ONLY, spec fully written, ~1d pure numpy | **★★★ HIGHEST** — the single line between narrator and coach; works on the master-only rig everyone runs |
| **H1 Practice-Deck Loop** + BEATMATCH_GRADED emitter | mixxx-goldmine (H1) | PLANNED-ONLY, consumer ready | **★★★** — lights up the orphaned beatmatch_judge/xfade/transition_clock ports; unlocks Mastered beatmatching |
| **Master-only Vibe Judge** (single-stream mix inference) | GOLD-WIRING-MAP Card 3 | BUILT but abstains on 1-deck rigs | **★★★** — depends on the keystone; makes the one live engine actually speak |
| Why-It-Worked debrief receipts (replayable verdicts) | Creative Forge #6 (f5) | PLANNED-ONLY, highest feasibility | **★★** — post-session, deterministic, no TTS pressure; coverage-sparsity risk |
| Mastered-Moment Capture (auto hot-cue on Mastered unlock) | Creative Forge #5 | PLANNED-ONLY | **★★** — offline-provable, writes proof into user's own library |
| Learning Your Tells (count-based personal habits) | Creative Forge #2 | PLANNED-ONLY | **★★** — safe on counts, slop-risk on phrase-relative timing |
| Drop-On-Cue Pilot (pill names the cue + blend window) | Creative Forge #1 | PLANNED-ONLY | **★★** — groundable per-region; "exact bar" must abstain |
| H2-H8 Mixxx ports (from_anlz, grade_cue_placement, sync_adjustment, grade_blend, phase_align, detect_key) | mixxx-goldmine | PLANNED-ONLY (all grep NOT-FOUND) | ★ mixed — most are small once H1 lands; detect_key needs a DSP spike |
| Tune (gear-aware EQ config generator) | `project_gear_aware_sound_tuner.md` | PLANNED-ONLY (doc uncommitted) | ★ — adjacent product; pending Kaan/Francesco scope |
| B2B auto-drive (AI takes the deck via MIDI) | Creative Forge #9 | PLANNED-ONLY | ✗ MOONSHOT — blocked on absent outbound-MIDI + live latency; ship verbal half only |
| M4 mixxxdb writer / M5 Mixxx OSC grounding | mixxx-goldmine | PLANNED-ONLY (deferred) | ✗ — stock Mixxx has no OSC read path; "works with Mixxx" before fork = dishonest |

---

## 4. THE HONEST TAKE

1. **Reachability split:** roughly **two-thirds of the product is reachable by a user today** (co-host spine, full Crate/Viber, library search via CLI+Crate, cue export, learn shell, debrief, hotkeys) — but most "live" paths are **source/unit-proven only, never captured on a real rig**. About a sixth is **built-but-unplugged** (recall has no toggle, beatmatch_judge has no producer, demo_mode/ear_test_capture orphans, drop/clash flag-dark). The remaining sixth is **pure idea** (Tune, H1-H8, the EQ keystone, the creative forge).

2. **The biggest "built it and forgot to wire it" surprise:** not what the docs say. The audit + GOLD-MAP + CORRECTION all chorus "no file-watcher, cue is CLI-only" — **both are STALE**: at HEAD `ed081570` the library watcher runs live (`__main__.py:2300`) and a real **Cue tab** ships export to the GUI (`library.html:47`). The founder's own map under-credits two shipped features. The *genuine* orphans are quieter: the **beatmatch "moat" engine with no producer**, and **recall with no UI switch**.

3. **The 3 highest-leverage WIRE moves** (tie to GOLD-WIRING-MAP): (a) **build `intel/eq_move_model.py` + wire into `apply_live_claim_guard:2342`** — the keystone that turns the live brain from narrator to coach; (b) **finish the master-only Vibe Judge** (GOLD Card 3) so the one live engine speaks on the rig people run; (c) **bundle-or-host MOSS** — without it the co-host **cannot speak on any machine but Kaan's** (model not in the DMG, no hosted URL), which gates every "a stranger hears it" claim.

4. **The 3 best graveyard ideas worth reviving:** the **EQ-move physics keystone** (spec written, ~1d, highest moat leverage), **H1 Practice-Deck Loop** (lights up three already-built-and-tested ports and unlocks Mastered beatmatching), and **Why-It-Worked debrief receipts** (highest feasibility, deterministic, no TTS/cost pressure).

5. **Verdict: this is a RICH product hiding behind bad wiring and a stale package — not a thin one.** The intelligence (single-writer state, citation grounding, slop filter, Vibe Judge, intel scorers, CLAP retrieval, skill-tree) is clean-room-built and broadly tested; the gaps are **last-mile connections** (the move→sound keystone) and **a stale, voice-muted DMG** — execution and packaging, not invention.

---
*One stale-claim caveat against my own prior packets: the default voice flag. `VIBEMIX_LOCAL_TTS` defaults to `"1"` via `setdefault` (`__main__.py:837`) — MOSS is the default voice in SOURCE, not opt-in as the old CLAUDE.md banner says. That does NOT contradict kill-shot ①: the flag being on-by-default still produces a MUTE co-host on a fresh machine because the MOSS model file is neither bundled in the DMG nor hostable for auto-download (`model_assets.py:624` "not hosted by default"). Flag-on + model-absent = silent. See `RED-TEAM-SHIP-REALITY.md` ①.*
