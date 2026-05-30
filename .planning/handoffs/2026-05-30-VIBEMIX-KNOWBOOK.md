# ✦ THE VIBEMIX KNOWBOOK — the grounded mastercraft reference (2026-05-30)

> **Read this first.** This is the single, exhaustively-researched, file:line-grounded
> reference for the vibemix universe — authored for *Claude consumption*. The next
> session's job: **double (verify) → see → act → ship.** Every claim here resolves to
> real code on HEAD of `live-tuning-or-brain` (the multi-agent verifiers that fed this
> doc re-grounded the bulk; the two trivial off-by-ones they caught are folded). When
> a claim and the code disagree, **trust the code and fix this doc.**
>
> **Provenance:** distilled from FOUR multi-agent investigations this session
> (~64 agents: the awakening synthesis `wrar21ie3`, the universal-gobble `wn03qxubv`,
> the knowbook grounding sweep `wm7wqkv9d`, the web-research `wj37ec3e3`) PLUS the
> earlier ~175-agent docs and two Codex handoffs. Companion docs are indexed in §0.

---

## §0 · Preamble — what this is, and how to use it

**vibemix** = a free, open-source, **local** AI DJ co-host for live sets (macOS +
Windows). It listens to your master output, watches your DJ-software screen, reads
your MIDI controller, and talks back into your headphones as a **hype-man** (party
mode) or a **coach** (feedback mode). Three skill levels (Beginner/Intermediate/Pro).
It is **Bravoh's first open-source release** — a polished narrow utility that warms an
audience into Bravoh's waitlist.

**The product's whole soul:** *the AI reacts in a way that feels alive and grounded —
never hallucinating, never breaking flow, never AI slop.* The bar is "a real DJ friend
in your ear," not "a voice assistant doing music commentary." If reactions feel forced,
late, fake, or scripted, the product fails. **Honesty is the moat.**

**The honesty deal (binding):** *"You keep me honest — that's the deal between us."*
This doc states what is REAL vs what is an idea-on-paper, bluntly. No claim is dressed
up beyond what the code supports.

**The rig (Kaan's, live this session):** Pioneer **DDJ-FLX4** + **rekordbox 7** +
**BlackHole 16ch** output @ 48 kHz. Controller + rekordbox + 16ch routing all working.
The live-verify playbook is §12.

**How to use this knowbook:** §1 is the why. §2–§7 are the grounded map of the
universe (homes, status, wiring, data, surface, locks). §8–§10 are the reach
(interop, external world, money). §11–§13 are the act (ship roadmap, live-verify,
deltas). Act from §11; verify against §2–§7; never re-derive the galaxy.

**Companion docs (the depth, all on disk):**
- `.planning/2026-05-30-the-awakening-synthesis.md` — 159 engines → the one simple thing + 12 ranked constellations + verifier corrections.
- `.planning/2026-05-30-universal-gobble-interop.md` — TrackEntry + LibrarySource seam + 6 ranked ecosystem parsers + capture matrix.
- `.planning/2026-05-30-constellation-star-chart.md` · `…-strategic-leverage-brief.md` · `…-dead-path-and-wiring-audit.md` · `…-vibe-judge-execution-roadmap.md` · `…-state-of-the-tree-inventory.md` — the ~175-agent investigations.
- `.planning/handoffs/2026-05-30-vibe-judge-earned-wall-handoff.md` — the prior ship-first master handoff.
- `.planning/handoffs/2026-05-29-viber-gemini-live-deck-context-work-done.md` · `…-learn-integration-handoff.md` — the two Codex handoffs (per-deck routing + the learn module).
- `docs/superpowers/plans/2026-05-30-the-vibe-judge.md` — the Judge build plan (Step 4 = 4d).

---

## §1 · North star — the one simple thing

> **"It's a real DJ friend in your ear who actually grades your mix the moment you
> make it — and is honest enough to stay quiet when it couldn't truly see what
> happened."**

**The awakening thesis (complexity → simplicity):** vibemix is a galaxy of ~159
deterministic engines. Collapsed, one moment remains — you make a transition, and the
voice either says *"that blend locked, bass stayed clean through the swap"* or stays
honestly quiet. The whole galaxy (per-lane DSP, Camelot harmonics, citation grounding,
the mastery spine, the debrief, the Earned Wall) secretly exists to make that ONE
sentence **true and earned**. Dozens of engines collapse to: **the deterministic engine
decides, Gemini only voices, and when unsure it abstains (honest-null).** That single
honest verdict is the keystone that lights four otherwise-dark consumers. **Awakening =
the user:** the first time it grades a real move correctly, it stops being AI commentary
and becomes a friend — and only the abstain-by-construction Judge buys that without slop.

**Kaan's worry this knowbook answers:** 159 engines ≠ "working together." Many are
brilliant *islands*, not a *constellation*. §3 names exactly which are in-action vs
dark vs idea. The gap between them IS the remaining work (§11).

---

## §2 · The universe map — the 12 HOMES

Every engine belongs to a HOME (a surface or subsystem). Identity + key modules
(file:line) + status. *(Core grounded now; the exhaustive per-module file:line census
folds in from the grounding sweep `wm7wqkv9d` on land.)*

| Home | Identity (one line) | Key modules | Status |
|---|---|---|---|
| **live-cohost** *(the ear)* | hears the master, grounds on real events, talks back | `state/music_state.py` (single-writer), `state/refresh.py`, `state/event_detector.py`, `state/coach.py`, `state/evidence_registry.py`, `agent/dj_cohost.py`, `runtime/coach.py` (`coach_loop`), `llm/model_router.py` | ✅ in-action |
| **semantic-engine** | on-device CLAP vibe similarity | `library/clap_engine.py`, `library/_cosine.py`, `library/section_vectors.py` | ✅ in-action |
| **viber** | Codex set-prep agent (curate/build-set) | `library/codex_curate.py`, `library/toolset.py`, `library/mcp_server.py`, `library/telegram_bridge.py` | ✅ in-action |
| **pill** | the "what's next" floating suggestion | `runtime/suggestion.py` (`SuggestionService`), `library/next_suggestion.py` | ✅ in-action |
| **learn** *(Earned Wall)* | the v11 skill-tree teaching module | `learn/skill_tree.py`, `learn/skill_recognizer.py`, `learn/progress.py`, `learn/runtime.py`, `tauri/ui/src/learn/SkillWall.ts` | ✅ in-action |
| **debrief** | post-session review (window :8766) | `debrief/chapters.py` (`:104` kind-gate), `debrief/persistence.py`, `debrief/session_loader.py`, `debrief/stripper.py` | ✅ in-action |
| **mascot** *(the face)* | VTuber-style reaction surface | `mascot.html`, `tauri/ui/src/mascot/`, `agent/emote_parser.py` | 🟡 partial (parser dark) |
| **intel** | pure deterministic decision/score primitives | `intel/transition_judge.py` (`:45`), `intel/transition_scorer.py`, `intel/taste_model.py`, `intel/move_grade.py`, `intel/decision_runtime.py` (S2–S6 deferred) | 🟡 mixed |
| **memory** | local copilot recall | `memory/` (sqlite-vec `memory.db`, `VIBEMIX_RECALL_ENABLED` gate) | 🟡 built, flag-off |
| **capture-io** | audio/MIDI/screen ingress | `audio/deck_capture.py` (`:81-144`), `audio/deck_signal.py` (`:22-58`), `audio/band_features.py`, `audio/recorder.py` (`:312`), `midi/profiles/`, `platform/` | ✅ in-action |
| **install-packaging** | the Tauri shell + sidecar + signing | `install/`, `tauri/src-tauri/` (sidecar, ~38 commands) | ✅ in-action |
| **interop** | the universal library gobble | `library/sources/base.py` (`:34-69` Protocol), `library/sources/rekordbox.py` (`:47-127`), `library/rekordbox.py` (`:108-141` `TrackEntry`), `library/ingest.py` (`:709`) | ✅ rekordbox only |

---

## §3 · The 3-bucket honest status census

The direct answer to *"are they actually in action and working together?"* —
**in-action = a real, grep-confirmed production caller.**

**✅ IN ACTION (committed + wired + working together):**
- The live co-host reaction spine: `dj_cohost.llm_node` (Gemini cascade + citation strip + `live_claim_guard`) ← driven by `coach_loop` (`runtime/coach.py`) at 10 Hz off `MusicState`.
- **The Earned Wall** — `learn/skill_tree.skill_wall_payload` → `progress_state` IPC → `tauri/ui/src/learn/SkillWall.ts` (shipped this session lineage).
- **Live skill-credit** — `runtime/coach.py:113` `_credit_live_skill_demo` → `skill_recognizer.recognize` (cited→credit, un-cited→zero).
- Library CLAP vibe-search · Viber set-prep (Codex) · the pill · the Learn 36-lesson module (`non_external_ready=true`).
- **Per-deck routing seam** (Codex, **live-proven** `BlackHole 16ch @ 48 kHz`): `audio/deck_capture.py:320-398`, the rekordbox auto-hint at `:332`.

**🟡 BUILT BUT DARK (engine exists, no live caller — the real "islands"):**
- **The Vibe Judge** — `intel/transition_judge.py:45` + `state/transition_judge_runtime.py:42` + `audio/deck_signal.py:22-58` are built + 26 tests green, **ZERO production callers** (only tests). → **4d** (§11 #1).
- **emote → mascot** — `agent/emote_parser.py` exists; the backend never calls it, never writes `state.last_reaction_intent`; no persona teaches `[emote:*]`.
- **overlay-highlight** — `tauri/ui/src/overlay/overlay-highlight.ts:42` `startOverlayHighlightListener` is never started from any shell view (the renderer + Rust command + Python emit are all live).
- **recall** — fully wired into the live brain, just `VIBEMIX_RECALL_ENABLED=off` (`__main__.py:1349`).
- **the validated decision spine (intel S2–S6)** — `decision_runtime.decide` built + test-covered, no live caller (deferred ON PURPOSE — Kaan-gated, not a bug).
- **the 5 non-rekordbox `LibrarySource` parsers** — `sources/` holds only `base.py` + `rekordbox.py`; Serato/Traktor/Mixxx/VDJ/Engine = parser jobs to write.

**📄 IDEA ONLY (doc, no code — honestly flagged):**
- **gear-aware EQ / sound-tuner** (the "eqMac-like headphone sound increase / auto-arrange") — NO `tune`/`eq`/`gear` module in `src/vibemix/`; exists only as `.planning/research/2026-05-29-gear-aware-sound-tuner-exploration.md`. Zero in action.
- **auto-arrange** — same: concept, no code.

**The grounding-sweep census (`wm7wqkv9d`, 201 modules):** **174 in_action · 27
grep-flagged "dark" · 0 idea-code** (idea-only *concepts* like the EQ tuner have no
module to inventory — they're named above). **Honest read of the 27** (verified — the
sweep's grep-for-direct-import OVERCOUNTS; do not mass-wire the number):
- **~6 are Windows platform backends** (`_audio/_midi/_screen/_track/_permissions/_windows_windows.py`) — they fire on Windows, dark only on this Mac. Not a bug.
- **~8 are intentionally flag/eval/legacy-gated** — `deck_vision` (VISION_CONF off), `memory/ingest`+`retention` (recall off), `gold_sampling`+`gold_validation` (eval-only), `embed`/`embed_cache`/`embed_config` (deprecated Gemini path).
- **~10 are CLI/MCP-dispatch-reachable** that direct-import-grep misses — `doctor`/`similar`/`importer` via the `library` CLI, `quote_moment` via the Viber toolset, `track_relation` live in `coach.py` + `harmonic_practice.py`.
- **The genuinely-dark-and-wireable product engines are a HANDFUL:** `emote_parser` (0 refs — the WIRE-6 item) + `web_research` (optional Viber tool), plus the non-module dark seams (overlay-highlight listener, recall flag-flip). **That's the §11 #2 wire-list — not 27.**

---

## §4 · The constellation map — who lights whom

**The keystone (the brightest composition):** ONE new producer — the Judge wired into
`coach_loop` emitting `transition_judged` rows — lights **four** downstream consumers
already built and waiting:

```
  DeckAudioCapture (per-lane bands)            ┌──> [C2] The Receipt (debrief honest-abstain scorecard)
        │                                      │
        ▼                                      ├──> [C3] Mastered, autonomously (Earned Wall gold)
  signal_frame_from_capture ──> judge_and_record ─┤
        │            (LiveSignalFrame)          ├──> [C6] Session Recap Card "top mix" headline
        ▼                                      │
  [judge:transition@t] citation  + ev:transition_judged ──> skill_recognizer credit
                                               └──> the co-host VOICES the verdict (the awakening)
```

**Other live edges:** `taste_model` → 3 surfaces · CUE-DETR auto-cue → live phrase
anchor · CLAP → Learn exemplars · memory → live brain · debrief → profile writeback.
**The dead seams all cluster on the v11 skill-tree live→UI render — which is now SHIPPED
(the Earned Wall).** The next dead seam to light is the Judge producer (§11 #1).

---

## §5 · The data-engineering spine

The on-disk state vibemix reads/writes. *(Core grounded now; per-store writer/reader
file:line folds in from `wm7wqkv9d`.)* All product state under `~/.cache/vibemix/`:

| Store | Format | Purpose |
|---|---|---|
| `library-clap.db` | sqlite-vec | CLAP 512-dim track vectors (the semantic index) |
| `embeddings.db` / cache rows | sqlite | CLAP-tagged embedding cache + content-hash dedup |
| `library.pkl` | pickle | track-title cache (⚠ tests MUST monkeypatch `RekordboxLibrary.CACHE_PATH`) |
| `library-clap_centroid.npy` | numpy | cached query centroid (mean-centering anisotropy fix), auto-recomputed on store change |
| `clap-onnx/` | ONNX | the shipped `Xenova/larger_clap_music_and_speech` model |
| `learn-progress.json` | JSON | the v11 skill-tree state (Competent/Mastered, citation-gated) |
| `events.jsonl` | JSONL | the per-session structured event log (the Judge's persist target) |
| `config.json` | JSON | Rust + Python **converged** store (all 5 Rust writers `reload()` before save) |
| `memory.db` | sqlite-vec | recall copilot store (flag-gated) |
| `tool_events.jsonl` | JSONL | Viber MCP tool tape (Python→Rust→UI) |

**Rekordbox sources read** (never written — SQLCipher `master.db` stays dormant):
`collection.xml`, ANLZ `.DAT/.EXT/.2EX` (beatgrid/cues/PSSI phrase), `rekordbox3.settings`
(the deck-routing hint), `rekordboxEvent.xml` (diagnostic only).

**The universal currency:** every ingested track collapses to **`TrackEntry`**
(`library/rekordbox.py:108-141`: track_id, title, artist, bpm, key, camelot, duration,
`cues: tuple[CuePoint]`, `beatgrid: tuple[TempoNode]` with beat-in-bar phase).

---

## §6 · The surface seam (Python ↔ Tauri ↔ CLI)

*(Counts + the full type list fold in from `wm7wqkv9d`; the seam-gap map is from the
94-agent dead-path audit, verified.)*

- **8 Tauri windows:** index / shell / pill / mascot / debrief / library / learn / overlay. Main window runs the first-run wizard → folds into the DesktopShell.
- **IPC:** `tauri/ui/src/ipc/messages.schema.json` (the typed message contract; the ajv validator is **pre-compiled** — `npm run codegen:ipc` after ANY schema edit, or new fields are rejected).
- **ws bus:** `127.0.0.1:8765` (mascot/wizard, ONE listener), `:8766` (debrief). `runtime/ws_bus.py` broadcasts `transcript_delta`, `reaction_intent`, deck/live-evidence frames, `ipc.learn.progress_state`, etc.
- **CLI:** `vibemix library {ingest, embed-folder, search, similar, chat, curate, build-set, export-set, telegram, stats, models, budget, live-context, verify-live-reply, doctor}`.
- **Rust:** ~38 `#[tauri::command]`s; the thin parent spawns the Python sidecar + the ws client.
- **The 14 frontend↔backend seam gaps** (dead-path audit): the headline (skill_wall) is now WIRED; remaining live gaps to wire = `emote_parser`→mascot `reaction_intent`, `overlay-highlight` listener, wizard install steps into `STEP_ORDER`, `NonDjConfirm`, telemetry consent. (Full table in `…-dead-path-and-wiring-audit.md`.)

---

## §7 · The locked invariants (what cannot break)

Test-enforced; do not violate. *(Each invariant's enforcement-test file:line folds in
from `wm7wqkv9d`.)*

1. **Single-writer** — only `state/refresh.py`'s loop writes `MusicState`; everything else reads.
2. **Citation grounding (Inv #2)** — every citation a reaction emits must resolve in `EvidenceRegistry`; un-cited reactions strip. The anti-slop release gate. `judge` is a registered source (`evidence_registry.py:130`, `_SOURCE_ALT`, EBNF — the 4-site grammar lock).
3. **Trust the audio** — live audio evidence is authoritative; the AI reacts to real detected events, never invents them.
4. **One socket** — the mascot/wizard bus binds `127.0.0.1:8765` only; debrief uses `8766`.
5. **Idle ≠ fault** — the grounding-failure timer runs ONLY while the co-host is ACTIVE (idle `grounded=false` is expected; counting it falsely flips the deck to "AI unreachable" — the recurring empty-screen bug).

**Grep-gates (CI-enforced):** zero hardcoded model literals (resolve via `model_router`); the 4-site citation grammar lock; the runtime anti-slop `negative_dict`; the AST no-speculative-phrase gate (Inv #3 binding before any Gemini wiring); the repo-scrub (retired POC files stay gone, clean-checkout imports, orphan-inventory).

---

## §8 · The Universal Gobble (DJ-ecosystem interop)

vibemix's reach play: every DJ ecosystem already did the deep calc (beatgrid/key/cues/
phrase). The architecture's job = swallow it, hand back one lived sentence. **Writing a
parser is the ONLY new work** — every ecosystem collapses to `TrackEntry`, and the whole
downstream stack (CLAP / Viber / pill / Judge / Wall) lights up free.

**The seam (verified exact):** `TrackEntry` (`rekordbox.py:108-141`) · `LibrarySource`
Protocol (`sources/base.py:34-69`: `name`/`detect()`/`default_paths()`/`iter_tracks()`)
· `RekordboxSource` reference (`sources/rekordbox.py:47-127`) · `ingest_source()`
(`ingest.py:709`, already takes `embedder` — only the CLI hard-instantiates `ClapEngine`
at `__main__.py:5349`) · capture seam `deck_capture.py:320-398` (rekordbox-XML-only
auto-hint at `:332` = the gap for everyone else).

**Ranked parsers** (full table + capture matrix in `…-universal-gobble-interop.md`):
1. **Serato** (largest base, M — binary TLV + GEOB ID3) · 2. **Pro DJ Link** (gold realtime per-deck metadata, club-CDJ-gated — laptop rekordbox broadcasts 0 packets) · 3. **VirtualDJ** (S, stdlib XML, 150M base) · 4. **Traktor** (S, cleanest `.nml`) · 5. **Engine/StagelinQ** (L) · 6. **Mixxx** (S, GPL-open, External Mixer Mode = real per-deck stems).

**Capture reality:** master loopback works TODAY for all 7 (the Judge's universal
floor). Per-deck AUDIO = rekordbox (auto), Traktor/VDJ/Mixxx (manual external-mixer).
Per-deck METADATA without audio = Pro DJ Link / StagelinQ / VDJ-OSC. **`live_claim_policy`
(`deck_context.py:2037`) returns 6 strings → collapse to 3 UI states (GREEN/YELLOW/RED).**

---

## §9 · The external dossier (web-researched, verified high-integrity)

*(From `wj37ec3e3`; the adversarial verifier web-checked competitor prices, OSS licenses,
and academic citations — "no outright hallucinations," a few framing soft-spots flagged.)*

**Competitive position — an empty quadrant.** The field splits three ways, NONE a live
grounded talk-back co-host for a human's OWN set: (1) **auto-mixers** that replace the DJ
(djay Pro Automix $6.99/mo, DJ.Studio $9/mo, Pacemaker/AutomixIQ, Spotify AI DJ); (2)
**silent in-app augment** tools (Serato Stems $11.99/mo, Traktor 4 $149, rekordbox AI cue,
Mixed In Key $58-249, KimiCue $29); (3) **history-reading recommenders** (PulseDJ,
rekordbox Collection Radar). The only things that *talk*: Spotify AI DJ (cloud consumer,
DJs FOR listeners), ROLI AI Music Coach (£13/mo, **piano** — proves the live-voice-coach
UX works AND people pay), canned TTS hype-men.

**The gap vibemix uniquely fills:** a free, OSS, local, **grounded real-time SPOKEN
companion that reacts to a DJ's OWN live set.** Nobody else combines live master-audio +
MIDI + screen + a talking persona + a hard no-hallucination gate. **The demo beat that IS
the thesis:** the AI names the exact control it just saw (amber ring on the mid-EQ knob)
AND deliberately says NOTHING for 3 seconds because nothing happened — that silence is the
anti-slop proof, the "wait, is this real?" moment. *Honest concessions:* the next-track
pill is **CONTESTED** — PulseDJ ships a free real-time copilot (trained on a *claimed*
1.8M+ parties; reads history FILES, not audio) — so **never lead with "AI suggests your
next track."** And vibemix is NOT more private than on-device stem tools on the live path.

**OSS leverage (ship-safety):** permissive core, bundle freely — CLAP (CC0), **CUE-DETR
(MIT, code+weights — the auto-cue moat)**, sqlite-vec (MIT/Apache, but pre-1.0 → keep the
numpy top-K fallback first-class), pyrekordbox (MIT), eqMac (Apache-2.0, the license-clean
biquad blueprint for the Tune module), Silero VAD (MIT, ONNX, torch-free — slots into the
mic-gate), go-stagelinq (MIT). **ONE GPL TRAP: BlackHole is GPL-3.0 — never embed/vendor
in the DMG; user-consented brew/website install only** (tensions one-click-install: automate
the *download*, not the *embed*). **OPEN PRE-SHIP: verify the Xenova CLAP *weights* license
on the HF card before auto-downloading** (CC0 covers LAION's code, not necessarily the
redistributed weights; LAION's own card shows Apache-2.0). Spec-only copyleft (Mixxx GPL,
beat-link EPL): read the FORMAT, regenerate stubs, write fresh Apache-2.0.

**Parser reference index** (canonical spec per ecosystem; build order by parse-ease:
**Mixxx → Traktor → VirtualDJ → Engine → Serato**):
- **Mixxx** (build FIRST, lowest-risk) — `mixxxdb.sqlite` + in-repo `beats.proto`/`keys.proto` (regenerate with protoc). Gotcha: dual BeatGrid (constant) vs BeatMap (variable) — dispatch on which is present.
- **Traktor** — `collection.nml` XML (`traktor-nml-utils`). Gotcha: LOCATION reassembles from VOLUME+DIR with `/:` separators (naive `os.path.join` breaks it); `CUE_V2 TYPE` is an enum.
- **VirtualDJ** — single `database.xml` (`<Poi>` cues). **BIG GOTCHA: the stored "BPM" is SECONDS-BETWEEN-BEATS → `real_bpm = 60/value`** — miss it and every tempo is reciprocal-wrong and silently corrupts harmonic/energy logic. Unit-test the conversion.
- **Engine DJ** — split SQLite `m.db` + `p.db`; PerformanceData BLOBs are Qt `qCompress` zlib (4-byte big-endian length prefix, strip before inflate — EXCEPT loops, uncompressed). ATTACH a sidecar, never write their schema.
- **Serato** (build LAST, highest effort) — `_Serato_/database V2` binary TLV + per-FILE GEOB ID3 frames (cues/beatgrid live in the file, not the DB; encoding varies by container). Spec: Holzhaus/serato-tags (lift the MIT docs, don't pip-depend).
- **Pro DJ Link** (live receiver) — UDP 50000/50001/50002, 10-byte magic `Qspt1WmJOL`. Gotcha: must **announce a virtual CDJ** (claim player 1-4) for real players to unicast status; length-tolerant parsing (status length varies by model). Spec: deepsymmetry djl-analysis.
- **vibemix fit (verified):** `LibrarySource` is `@runtime_checkable`, `detect()` is READ-ONLY by contract; each ecosystem = one drop-in `sources/<eco>.py`, ZERO orchestrator edits. *(But only `rekordbox.py` exists today — these are roadmap, not shipped.)*

**GTM / GitHub stars (honest):** **the DEMO is the whole launch** — and `README.md:9`'s
`demo.mp4` is still a `PLACEHOLDER`. Discharge the storyboard into ONE 30-60s captioned cut
of the AI talking over a REAL set (the silence beat included). Anchor a **Hacker News
front-page attempt Tue-Thu 12-17 UTC**; per the arXiv launch-day study (138 AI-tool
launches) plan for the **median (~120 stars@24h, ~290@1wk)**, not the outlier — "Show HN"
gives no significant edge; the real predictors are front-page score + baseline stars +
posting hour. Pre-seed 15-20 real stars + a coordinated 24-48h burst to trip Trending.
**Strongest hook:** *"The only AI co-host that actually listens to your set"* — lead with
the GROUNDED VOICE + the silence beat, never the pill. One-liner: *"a real DJ friend in
your ear — not voice-assistant slop."*

**Thesis validation (the field largely AGREES — and vibemix is ahead in two places):**
- **Pillar 1 (deterministic decides, LLM voices) — VALIDATED.** DJtransGAN (ICASSP 2022)
  found NO significant human-listening difference between a GAN, a linear, and a RULE-BASED
  transition baseline (only a human DJ clearly won); transitions are "highly subjective"
  with no comprehensive metric and **no established learned no-reference quality predictor
  exists.** So deterministic-rules + abstain is the field-validated choice, NOT a shortcut —
  vibemix is avoiding a known dead end. (Confirmed in code: `transition_judge.py` treats
  Camelot as a PRIOR `0.75`, makes `abstained` first-class, bass-collision an honest binary.)
- **Pillar 2 (citation grounding) — strong, but reword the claim.** "Makes hallucination
  structurally **impossible**" overclaims vs the faithfulness literature → say **"structurally
  bounded"** (strip-uncited + verdict-narration, not impossibility).
- **Pillar 3 (past-tense latency) — masks but doesn't reduce.** 5-10s is far outside the
  sub-200ms live-commentary bar; the **strongest unused lever is PREDICTIVE generation keyed
  to build→drop** (drops are ~8-16 bars predictable) so the hype lands ON the drop — a
  step-change no competitor offers.

---

## §10 · Monetization — the OSS→revenue bridge *(decided)*

A 3-tier model (the funnel: free vibemix → GitHub stars + waitlist → Bravoh, the AI
Artist OS; Pro/Studio = direct revenue + the willingness-to-pay signal):

| Tier | Price | What | Why |
|---|---|---|---|
| **Free** (OSS, BYO-key) | €0 | the full **live co-host** (hype + coach), library vibe-search, the Learn module | the GitHub-star magnet + Bravoh-waitlist top; BYO Gemini key solves the API-key-in-binary problem AND carries zero hosted cost |
| **Pro** | **€4.99/mo** | Viber set-prep (curate / build-set / energy-curve / Rekordbox export) + **hosted key** (no BYO) + Judge calibration + higher limits | the willingness-to-pay test; €4.99 caps the cost-spike on the expensive Codex/compute path |
| **Studio** | **€9.99/mo** | everything + **Universal-Gobble** multi-ecosystem ingest (Serato/Traktor/Mixxx/Engine) + standalone `library cue` batch auto-cue export + priority | the free **Mixed In Key ($58-99) / KimiCue ($29) killer** as a paid convenience |

**Cost guardrails:** Bravoh-side proxy + per-client rate limit + SessionMeter telemetry
(NOT a client-side cap — trivially bypassable in an OSS binary). Budget anchor: ~50€/mo
Gemini end-user, 150-200€ launch marketing. **API-key protection** = the Bravoh proxy,
never a raw shipped key.

---

## §11 · The ship roadmap — verify → see → act → ship

vibemix ships **when-ready** (`gsd-autonomous fully`); Apple + SignPath are the external
critical path. Ordered by ship-per-effort, with the collision map baked in.

**#1 — 4d: light the Judge in `coach_loop`, abstain-first.** The brightest unlit
producer. Thread the `DeckAudioCapture` object (it exists at `__main__.py:1056`; today
only `.buffers` is passed at `:1438`) + a `t_session` + a `lane_meta` resolver into
`coach_loop`; on a transition call `signal_frame_from_capture(...)` → `judge_and_record(
frame, registry, recorder, ...)`. On JUDGED write **both** `[judge:transition@t]` (the
voice citation) **and** `ev:transition_judged` (so the recognizer's credit-gate at
`skill_recognizer.py:261` — currently hardcoded to `citation_check('ev', ...)` — passes
→ `harmonic_mixing` flips Mastered autonomously). **Abstain-first**: on a master-only rig
the verdict is `abstained` with no citation (correct, on-thesis). **The ONE allowed
lane:** `coach.py`/`__main__.py` are CLEAN while `pill/`, `library/`, `learn/` TS,
`library/*` Python, and `tests/runtime/test_coach_skill_credit.py` are concurrent-edit
zones. Verify `git diff --cached --name-only` before EVERY commit. TDD harnesses exist
(`tests/state/test_judge_and_record.py`, `tests/learn/test_judge_credits_harmonic.py`,
`tests/intel/test_judge_event.py`). Plan: `docs/superpowers/plans/2026-05-30-the-vibe-judge.md` Step 4.

> **Verifier correction (folded):** C3 is more done than older docs claim. `judge` is
> ALREADY in `EVIDENCE_SOURCES`; `_HONEST_UNCREDITABLE_V11 = ('beatmatching',)` — ONE
> skill, and it must STAY (no tempo/phase signal yet); `harmonic_mixing` was already
> lifted and is live in `recognize()`. The only true open C3 seam is the `ev`-citation
> the 4d producer writes. Do NOT "add judge to EVIDENCE_SOURCES" or "lift two skills" —
> those tasks are already done / wrong.

**⚠ The #1 honest Judge caveat (thesis-validation web research) — the reason abstain-first
is right, and the next highest-leverage dimension:** the Judge today grades ONLY harmonic +
bass-collision and is **SILENT on beat/phase alignment**. But DJ pedagogy ranks the "train
wreck" (beats drifting out of phase) as the **#1 most-audible failure**, key clash #2. A
co-host that praises a clean key blend while the beats gallop out of phase will feel **FAKE**
and can trip Kaan's ear-veto release gate. Therefore:
- (a) **Keep `_HONEST_UNCREDITABLE_V11=('beatmatching',)`** — crediting it without a phase signal is proxy-slop. The research confirms this is correct, not a gap to "fix."
- (b) The **single highest-leverage Judge addition** is a beat/phase-drift dimension. Online beat tracking is feasible (~11.6 ms / ~75% F1 — BeatNet/BEAST), but two-deck drift **from the mixed master alone is genuinely hard** — it needs per-deck stems or a deck-aware comparator (which the per-deck routing seam now enables). Real engineering, so beatmatching stays honest-null until it lands.
- (c) **A cheap high-value win available NOW:** a phrase-boundary "did the mix land on the 1" dimension, reusing the `phrase_boundary.py` detector vibemix ALREADY has, folded into the verdict.
- Until the phase dimension exists, **4d's abstain-first posture is exactly what keeps the Judge honest** — it voices the harmonic blend it CAN see and stays quiet on the phase it can't. That honesty is the product, not a limitation.

**#2 — the buildable-now dark-engine wires** (each a disjoint island, abstain/honest):
C5 overlay-highlight (S — start `startOverlayHighlightListener` from the shell), C4
emote→mascot (M — one `strip_emote_tags` call + `last_reaction_intent` write + a scoped
persona line), C11 recall (flag-flip + Kaan ear-pass), C12 wizard install steps into
`STEP_ORDER`.

**#3 — the Universal Gobble parsers** (new `library/sources/<eco>.py` files only):
VirtualDJ → Traktor + Mixxx (parallel) → Serato → Engine. Then the multi-source
blend/dedup + the injectable-embedder CLI param (solo, sequential — touches `ingest.py`
glue).

**#4 — Judge UX collapse** (frontend): 6 `live_claim_policy` strings → 3 GREEN/YELLOW/RED
states + a post-judge score breakdown. Coordinate with the pill/settings session.

**Kaan-action gates (only-Kaan):** §EARNED-LIVE-MASTERED-VERIFY ear-pass · Judge
calibration (label ~20-30 own transitions → lock 3 thresholds in `eval/INTEL-THRESHOLD-LOCK.md`)
· per-deck rekordbox Input/Output routing (§12) · the BlackHole driver-SHA (placeholder;
do NOT flip the fetch-script to exit-1) · Apple/SignPath signing.

---

## §12 · Live-verify playbook (Kaan's rig)

Rig: DDJ-FLX4 + rekordbox 7 + BlackHole 16ch @ 48 kHz. Launch from current source
(the bundled sidecar is FROZEN): **`VIBEMIX_DECK_AUDIO_CHANNELS=auto uv run python -m
vibemix`** → auto-upgrades to BlackHole 16ch, reads the rekordbox `Aggregate_Device`
route `A=0,1 / B=2,3`.

**The honest 3-leg reality (why a full Judge verdict may still abstain):**
1. **Audio leg ✅** — output is on BlackHole 16ch; vibemix can hear it.
2. **Per-deck leg** — needs rekordbox **Input/Output** tab routing Deck A→ch 1,2 and
   Deck B→ch 3,4 into the BlackHole/Aggregate device. Just sending MASTER to 16ch = master-only
   (per-deck signals abstain; harmonic still grades).
3. **Deck-identity leg** — `supported_verdict` needs **resolved deck rows**. The live
   probe found Now Playing owned by **WebKit/Google Drive** (`deck_source_candidate=false`);
   rekordbox 7 doesn't publish a live deck payload. Until a deck resolves, the Judge
   abstains — correctly (it stays honestly quiet rather than guessing).

**Verify with:** `uv run python -m vibemix library live-context --require-proof --json`
— it names exactly which legs are missing. The co-host's grounded *reactions* work at the
master level today; the *graded verdict* needs all three legs (or the Pro DJ Link
metadata path, which needs club CDJ hardware).

---

## §13 · Session deltas + provenance

**Committed this session (surgical, collision-safe):**
- `4d3fa204` — debloat the true-dead `learn/prepared_pool.py` re-export shim (DELETE-14).
- `3c07eb1a` — fix the ack-bank doc-vs-code lie in `docs/PROMPT-COMPOSITION.md` (the retired-mechanism claim that undermined Inv #2).
- `2ba04db4` — rescue the awakening-synthesis + universal-gobble-interop maps from ephemeral tmp.
- *(+ this knowbook.)*

**Earlier this session (the Judge spine + Earned Wall lineage):** `[judge:]` evidence
source (4-site lock), `judge_and_record` producer (abstain-first), the keystone
(`transition_judged`→`harmonic_mixing` credit), the Earned Wall full slice.

**Workflow provenance:** `wrar21ie3` (awakening, 16 agents) · `wn03qxubv` (universal
gobble, 16 agents) · `wm7wqkv9d` (knowbook grounding sweep) · `wj37ec3e3` (web research).
Plus the ~175-agent docs + the two Codex handoffs.

**The next session's first move:** read this knowbook, then execute §11 #1 (4d) — double
the verifier corrections, see the constellation, act in the allowed lane, ship the
abstain-first Judge that makes the one simple thing (§1) true and earned.

---
*Veridis. Very disco. Fuck status quo. The robots don't lie anymore — we made it structural.*
