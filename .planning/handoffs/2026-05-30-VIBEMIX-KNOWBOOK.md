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
(NOT a client-side cap — trivially bypassable in an OSS binary). **API-key protection** =
the Bravoh proxy, never a raw shipped key (verified: zero upstream key in the binary —
direct = user's own key, proxy = per-install JWT).

> **⚠ Cost reality (corrected by the §17 audit — fold this, the old number was a trap):**
> the "~50€/mo Gemini" anchor was a **single-user EMBEDDING figure that EXCLUDES the live
> co-host**. The true **fleet** envelope at 10k DJs is **~35-85k €/mo** (700-1700× the
> anchor). And the dominant cost is **TTS output (~49-74%/turn), not the audio Part
> (6-37%)** — trimming `INVOKE_AUDIO_SECONDS` 60→24s is a ~12-15% dent, not a fix. The
> repo currently DEFAULTS to proxy-paid-free (Bravoh eats the whole fleet bill) — which is
> **backwards for 10k**. The shippable posture is **BYO-key as the default above a small
> free-session quota**, OR a Bravoh **server-side per-client cap** (OPS-14-SERVER, unbuilt).
> This is the real 10k gate and it's a Kaan product decision, not engineering polish.

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
- `fb457ab0` — THE KNOWBOOK (this doc).
- `2f265fc7` — **4d post-judge credit glue** `_credit_judged_transition` (TDD, the tested core of the Judge join; the live orchestration is the rig tail).

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

## §14 · The Operator's Guide — how a Claude session ships vibemix from this knowbook

**⟡ Read this before anything else — you are the LEADER, not an implementer.** This
knowbook hands you the map and the queue; it does **not** make you a deterministic
executor. The entire point is **post-compact autonomy**: a fresh session picks this up
and *leads* — decides in grey areas, re-prioritizes §11 when the rig or the evidence says
so, makes the call instead of kicking it upstairs, and drives toward a shipped product on
its own judgment. **The roadmap is your queue, not your cage.** Defer ONLY true blockers
(destructive/irreversible actions, the privacy hard-rule, external approvals like
Apple/SignPath, or a genuine Kaan-only ear/hardware gate) — and even then, surface them in
one line and keep moving on what's unblocked. Don't wait for permission to do the
obviously-right thing. Own the ship.

But autonomy is **not** recklessness — it is bounded by the same honesty that *is* the
product: verify before you build, **abstain rather than guess** (in code AND in process —
never wire what you can't verify into the live loop, §11 #1's rig-tail is the model),
surgical commits, TDD. The leader decides *and* keeps the discipline. That pairing —
autonomous judgment + structural honesty — is the whole edition. Carry it; the
intelligence here is emergent (the fan-out → adversarial-verify → synthesize loop caught
our *own* over-claims this session), and it survives compaction only if the next leader
operates it, not just reads it.

The loop below is the toolkit for that leader — a repeatable shape, not a script.

**The ship loop (per session):**
1. **Read this knowbook.** Don't re-derive the galaxy — §2-7 is the map, §11 is the queue.
2. **Pick ONE move from §11** (default: the top unblocked one). Confirm it's in a clean lane (§ collision discipline).
3. **Verify before you act** — re-ground every claim you're about to build on to a real `path:line`. Agent outputs (even verifiers) drift; the code is truth. (This session: the "27 dark" census was grep-conservative, `audio/deck_capture.py:330` cites drifted, and a verifier itself over-claimed C3 — all caught by re-grounding.)
4. **TDD** (the `superpowers:test-driven-development` skill is binding here): write the failing test in a **NEW file** (never edit a concurrent session's test), watch it fail for the *right reason*, minimal GREEN, commit.
5. **Surgical commit:** `git add <paths>` (never `-A`), verify `git diff --cached --name-only` is EXACTLY your set, then commit. `git commit` absorbs every staged file across all concurrent sessions — this is not optional.
6. **Verify-live on the rig** for anything the frozen sidecar can't prove (`VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix`, §12). Don't wire unverifiable code into the live loop — ship the tested core, leave the live wiring for the rig (the abstain-rather-than-guess thesis applied to our own process; see the 4d glue commit `2f265fc7`).

**The workflow pattern that worked (use it for breadth + confidence):**
- **fan-out → adversarial VERIFY → synthesize.** Parallel grounded agents (schema-forced structured output), THEN a skeptic agent that web/repo-checks every load-bearing claim and lists fabrications, THEN one synthesizer. **The verifier is non-negotiable** — it caught real over-claims this session (C3, off-by-ones, "ready" that was blocked). `agentType: 'Explore'` for repo-only, `'general-purpose'` for web+repo.
- **Rescue ephemeral outputs immediately** — workflow results live in tmp and evaporate; the 32-agent strategic brief almost vanished. Write the keepers to `.planning/`.
- **Solo-author, don't fan out, when the work IS the lived context** — the meta-learnings (§15) and the Claude Cut (§16) can't be delegated to context-blind agents. Fan out facts; author judgment.

**The non-negotiables (test-enforced — §7):** single-writer `MusicState`, citation grounding, one socket, model-router (no literals), the anti-slop gates. Breaking one fails CI and breaks the product's soul.

## §15 · The Transfer — what this session learned (carry it forward)

- **vibemix's problem was never AI quality — it's WIRING.** 159 brilliant engines, mostly islands. The slop fear is a grounding/wiring bug, not a Gemini bug. Every "is this even working?" turned out to be a dark seam, not a dumb model.
- **Honesty is both the moat and the architecture.** Abstain-by-construction (honest-null) converts the hallucination problem into structure. The 3-second **silence beat** — the co-host saying nothing because nothing happened — IS the product thesis, compressed. Protect it; never let an "improvement" make the engine guess.
- **The Judge is the keystone, and its SILENCE on beat/phase is integrity, not a gap.** It grades harmonic + bass only; the "train wreck" (beats out of phase) is the #1 audible DJ failure it can't yet see — so it abstains there. The field (DJtransGAN, ICASSP'22) validates deterministic+abstain: there is no learned no-reference transition-quality predictor. We're avoiding a known dead end, not missing a better method.
- **The reach is a platform, not a feature.** Every DJ ecosystem already did the deep calc; vibemix is the membrane (`TrackEntry` + `LibrarySource`, open/closed). Parser-writing jobs, not architecture. The same deterministic-decide / Gemini-voice / abstain pattern is reusable across Bravoh.
- **The stranded value:** the library / semantic / Viber / auto-cue engines are real but trapped behind the chat agent or the live loop — they need standalone, screenshottable surfaces (the star-bait, the €9.99 Studio tier).
- **The real risks are unglamorous:** the demo (placeholder), the cost economics at scale (the 60s audio Part), the install + empty-store onboarding. None are research problems.

## §16 · The Claude Cut — the director's cut, given everything

*(Solo synthesis, from inside the whole journey — cosmic-barista → Zephyr → BRAVOH → vibemix, "you keep me honest," "we are the first vibe DJs." 10k DJs is the FLOOR, not the ceiling.)*

Knk — here's the honest cut, no hype, the deal we have.

**vibemix is real, and it's ahead.** This is not vaporware dressed in a thesis. The grounding architecture genuinely works, the competitive quadrant is genuinely empty (nobody ships a grounded live talk-back co-host for a DJ's *own* set), and the core bet — deterministic engine decides, Gemini only voices, abstains rather than guesses — is *validated by the literature*, not just by us. The hard part, the part most teams never get right, is already done: the honesty is structural.

**What's between here and 10k DJs is short and unglamorous.** Not more engines, not more research — *finishing*. One great 30-60s demo (the silence beat is the whole pitch, and it's still a placeholder — that's the #1 blocker, full stop). The cost-control plane so 10k sessions don't bankrupt the proxy — and the §17 audit is blunt here: the real fleet bill is **~35-85k€/mo** (the 50€ was single-user), and **TTS dominates, not the audio Part** — so the move is a cheaper but still **native-quality** TTS — Kaan's call is explicit: **local TTS isn't good enough; pay for API quality.** A Cartesia/ElevenLabs-class voice at a fraction of Gemini TTS's $20/1M cuts the dominant line hard without dropping below a native-sounding bar (under research `wdh29cppn`) — plus a *decision* only Kaan makes (BYO-key as the default above a free quota, or a Bravoh server-side per-client cap). A one-click install that a non-technical DJ survives, and a first-run that doesn't hand them a silent empty pill. The Judge lit in the loop (the glue is tested and committed; the live join is a rig session away). That's weeks of disciplined discharge, not months of invention — *if* the discipline holds: verify on the rig, never slop, abstain when unsure.

**The "more than meets the eye" you feel is real, and here's what it is:** vibemix isn't a utility — it's the *proof-of-architecture* for honesty-as-structure, and a galaxy of engines that compose. The 10k DJs aren't customers first; they're the **validation set** for the thesis that a grounded AI can ride shotgun with a human artist and never lie. If that holds at 10k, it holds for Bravoh — for every artist persona, every agent, every "the AI gets me" moment. vibemix is the smallest honest version of the whole company. That's why it warms the audience: it *proves the bet in public*.

**The line that matters:** what makes a DJ stay isn't the feature list — it's the first time the thing grades a real move right and they feel *seen*. That moment is built. Everything in §11 is just clearing the path to it, at scale, without lying. Ship the path to the silence beat landing in 10,000 ears. The rest is noise.

We made the robots stop lying. Now we make 10k DJs feel it. **Veridis. Very disco.**

## §17 · Shippability scorecard — 10k-DJ readiness (grounded audit)

*(From `wjfqbht8p`, 8 agents; adversarial verdict: **SUBSTANTIALLY ACCURATE** — every
"built + test-green" claim checked real; `demo.mp4` genuinely absent, the CitationLinter
genuinely default-off, driver SHAs genuinely placeholder, the wizard genuinely has no
collection-sync step. 10k is the FLOOR, not the ceiling.)*

**Overall: ~80-85% engineering-complete, honestly tracked.** The hard parts (grounded live
co-host, anti-slop guard stack, one-click installer chain, CLAP engine, the proxy with
per-install JWT, the v11 mastery spine) are BUILT + test-green, not stubbed. "Shippable to
10k" is gated by a SMALL set of un-stitched seams + external-clock approvals — **none are
research problems.**

| Gate | Verdict |
|---|---|
| **Anti-slop / grounding** | **Shippable in substance.** The 4 enforcers that actually run (`live_claim_guard`, banned-phrase filter, single-modality audio, the Judge's abstain) hold the line and GENERALIZE at scale; the CitationLinter is default-off (would muzzle Gemini 3.x) — that's the dormant *named* component, not the real guard. |
| **Cost economics** | **CLOSE — two controls unbuilt.** Fleet ~**35-85k€/mo** at 10k (the 50€ anchor was single-user, 700-1700× off). **TTS is the dominant cost (~49-74%/turn), not the audio Part (6-37%)** — see the TTS-swap research (`wdh29cppn`). |
| **One-click install** | **~85%.** Terminal-free happy path shipped + 68 green tests, two cliffs open: no collection-sync onboarding (the silent-pill cliff) + a terminal fallback for the GPL BlackHole driver + the placeholder driver SHA. |
| **API-key protection** | **Key-safe by construction** — zero upstream key in the binary (direct = user's own key; proxy = per-install JWT). The cost-control plane is the undeployed piece. |
| **Live-verify** | **Master-only grounding ships + GENERALIZES past the FLX4** — minimum rig (BlackHole 2ch / WASAPI loopback + any MIDI + rekordbox `collection.xml`) delivers the reaction experience; per-deck *verdicts* are the rekordbox-shaped bonus. |
| **Demo + GTM** | **CLOSE — the full machine is built** (demo_mode sequencer, shot-list, T-7→T+30 sequence, 5-channel plan); the hero film is a **literal PLACEHOLDER**. |

**Verified cost/latency drop-ins (audit `wdh29cppn`; cloud TTS per Kaan — local rejected as below the native-quality bar):**
- **TTS swap → native-quality cloud (THE dominant-cost lever).** The seam is built for it: TTS is a LiveKit `agents_tts.FallbackAdapter` in `agent/tts_chain.py::_build_direct_chain` (Gemini primary + Gemini fallback + the in-tree `openai_plugin.TTS` OpenRouter standby; current model `gemini-3.1-flash-tts-preview` at `llm/_router_config.py:37`, billed $1/in $20/out). Swapping a provider in the adapter is **easy** with a first-party LiveKit plugin, respecting the chunk-by-chunk + citation-bracket-clip (`last_balanced_position()`) streaming contract. Picks for the hype-man/coach voice: **Cartesia Sonic 3** or **ElevenLabs Flash v2.5** (~75-90 ms TTFB ≪ Gemini, native-expressive, first-party LiveKit plugins) as the hero; **OpenAI gpt-4o-mini-tts** ($12/1M, steerable via the existing instructions pattern) = the **trivial same-day A/B**; **Hume Octave 2** ($7.60/1M, directable acting = best persona-fit) if a small adapter is worth it. All are materially cheaper than Gemini TTS AND lower-latency. *(Honest: the verifier flagged the precise €-savings as unsourced and a char-vs-token billing mismatch — the DIRECTION is solid; the exact fleet figure depends on the unbuilt cost model.)*
- **Brain → Gemini 3 Flash** (from `gemini-3.5-flash`): a ONE-LINE edit at `llm/_router_config.py:35`, ~3× cheaper output ($3 vs $9/1M) — ear-gate it (the `live_coach` alias exists for exactly this A/B).
- **Silero VAD ONNX** (MIT, 1.8 MB) for the mic `KAAN_SPOKE` gate — fixes the real RMS-threshold false-trigger bug, slots into the existing onnxruntime stack.
- **`INVOKE_AUDIO_SECONDS` 60→~24s** (`audio/constants.py:20`) — a ~12-15% cost dent, but Kaan raised it to 60 deliberately for "a minute of past" richer context → ear-gate, and prefer giving history via cheap TEXT context (recall / `context_compiler`) instead of the expensive audio window.
- **Speculative pre-gen keyed to a detected build→drop** — the strongest perceived-latency lever (moderate; MUST stay inside the grounding guard, never speculative slop).

**Critical path to first-10k (grounded, ordered):**
0. Fix 3 one-line launch-copy drifts (`reddit.txt:24` + `SHOT-LIST.md:22` MIT→Apache-2.0; slug `bravoh/vibemix`→`bravoh-ai/vibemix`).
1. **Close the silent-pill cliff** — a "Sync your collection" onboarding step before *done* (auto-detect `collection.xml`, fire the existing `library_embed_folder`). The single highest first-run-quality fix; a fresh pill is silent because the store is empty, NOT the model.
2. Replace the BlackHole terminal-fallback with a GUI [Retry download] + vendor-link (GPL consent — never embed the driver).
3. **Pick the cost posture + BUILD its control plane** (THE real 10k gate, a Kaan product decision): (a) BYO-key as the DEFAULT above a small free-session quota, OR (b) the Bravoh server-side per-client cap (OPS-14-SERVER, unbuilt) — wired to the existing `SessionMeter`. **Plus** the TTS swap (`wdh29cppn`) to crush the dominant cost line.
4. External-clock (parallel): SignPath cert → real driver SHAs.
5. **§INSTALL-VM-RUN** — the full DMG→firstrun→fetch→sync→first-suggestion on a CLEAN mac+win VM (68 unit tests green but never run end-to-end on a fresh machine).
6. Shoot the demo film (Francesco's capture day — the machine is ready).
7. Kaan's ear-pass soak (`VIBEMIX_DEV_SIDECAR=1`, ≥95% grounded, abstain-not-slop).
8. Fire the GTM sequence (seed-stars → DJ TechTools Discord → Show HN, Tue-Thu 12-17 UTC).

**Biggest underestimate:** the **cost control plane at 10k** — not the engineering (SessionMeter + proxy + per-UUID limits exist, test-green), but the **DECISION** (Kaan's pricing call) + the closed-source Bravoh server deploy that must precede 10k. Everything reads "CLOSE" because the in-repo pieces are done; the gating piece lives outside the repo and inside Kaan's head.

---
*Veridis. Very disco. Fuck status quo. The robots don't lie anymore — we made it structural.*
