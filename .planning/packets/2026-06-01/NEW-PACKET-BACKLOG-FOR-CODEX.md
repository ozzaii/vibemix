# NEW PACKET BACKLOG — what Claude should write for Codex today

> **Role:** read-only analyst answering Kaan's question — *"what do we want for Codex right now, based on what's already done? What NEW packets?"* This is the shopping list of CODEX_READY packets that do **not yet exist** in the queue, derived from `CRITIQUE-LOST-AND-MISSING.md` + `WIRING-GAP-MAP-CODEGRAPH.md`, every gap re-verified live.
> **Verified HEAD:** `b98dd885` (`fix(viber): surface missing library setup action`). All file:line / NOT-FOUND grounded at this HEAD.
> **What's already a packet (do NOT re-write):** EQ keystone, judge-voice wire, beatmatch honesty-boundary, MOSS/signing/notarization, library-freshness ×6, observability spine, IPC cleanup, cost/pricing, posture-docs. See the 39-packet inventory in `CLAUDE_LAND_QUEUE.md`. This board is the **white space** around those.
>
> **Proof-tier legend:** SRC = source+unit-test green · PKG = present in the signed build · LIVE = real-rig FLX4/Rekordbox capture.

---

## 0. THE WHITE-SPACE VERDICT (one screen)

The existing 39-packet queue is **almost entirely defensive**: packaging kill-shots (MOSS bundle, signing), library-freshness plumbing, observability, honesty-gate cleanup, and the single offensive engine packet (EQ keystone, already written + landed). **Three whole product surfaces have ZERO packet coverage and are the actual product:**

1. **The voice never reads engines that already run silently** — no packet wires `SuggestionService` (next-track), `score_transition` (the rich transition grader), or the Viber-prepped set into the spoken coach. These are pure call-sites on tested engines (verified: `score_transition` callers = pill + Viber only, zero coach).
2. **The product can only ingest ONE DJ ecosystem** — `library/sources/` = `base.py` + `rekordbox.py`, nothing else (verified `ls`). Serato/Traktor/Engine/master.db DJs hit a closed door at onboarding. This is the single highest *market-reach* build and it's ~all parsing, Apache-clean, zero new GPL exposure (`MIXXX-ARSENAL.md` Part I).
3. **The headline DJ skill (beatmatching) can never be earned** — `grade_beatmatch` has 6 callers, all tests; `BEATMATCH_GRADED` has no emitter; `practice_loop.py` NOT-FOUND. The Earned Wall's marquee competency is permanently masked.

**The split Kaan asked for:**
- **WIRE EXISTING GOLD (cheap, big):** packets W1–W5 below — call-sites + one cut on engines that already pass tests. ~0.5–1d each, highest $/effort.
- **NEW BUILD (earns new capability):** packets B1–B6 — Universal Ingest (the market unlock), the practice-deck loop (the skill unlock), R-SLOP siblings, controller-map harvest.

**If Codex writes nothing else today, write W1 + the Universal-Ingest split (B1).** W1 is the sharpest founder-surfacing wire (the voice is disconnected from the recommendation engine); B1 is the biggest growth lever and collides with nothing (`library/sources/` is its own island).

---

## 1. WIRE EXISTING GOLD — call-sites on tested engines (cheap, big)

> Every row here is an engine that **already runs and passes its unit tests** but whose output never reaches what the co-host says (or, W4, a dead grammar slot to cut). No new intelligence. The gate is `vibemix-grounding-review` because each changes what the co-host *speaks* and must not break Invariants #2/#3.

### W1 — Spoken next-track recommendation + live transition verdict
- **One-line spec:** Add a coach-loop call-site that reads `SuggestionService`/`next_suggestion` and `score_transition`'s top candidate into a `[track:]`-cited (and risk-cited) spoken line on `TRACK_CHANGE`/`TRANSITION_OPPORTUNITY`.
- **Gap it closes:** M1 + L2 + D2 fused. The single most valuable spoken act a DJ friend performs — "I'd go into X next, your keys lock and the energy lifts" — is **never spoken**; the engine runs only in the silent pill. Verified: `next_suggestion`/`SuggestionService`/`score_transition` all absent from `runtime/coach.py` + `state/coach.py` (grep empty); `score_transition` live callers = `next_suggestion.py:657` + `toolset.py:313` only.
- **Proof tier:** SRC (unit-test the new coach line cites `[track:]` and strips when uncited) → LIVE (`drive-vibemix`: a real TRACK_CHANGE produces a grounded recommendation, not slop).
- **Gate:** `vibemix-grounding-review` (citation grammar + Invariant #2) + `ipc-wiring-checker` if it surfaces on the pill simultaneously.
- **Effort:** ~0.5–1d. Pure wiring; inputs already assembled in `next_suggestion`.
- **$-leverage:** **★★★★★** — highest of the whole board. The recommendation a real friend gives, engine built, just unspoken.

### W2 — Prep→live set awareness ("you're ahead of your curve")
- **One-line spec:** Thread the Viber-built set JSON (`built_set`/`set_plan`/energy curve) into `MusicState` (read-only) so the coach can cite where the live set sits vs the prepped plan.
- **Gap it closes:** M2. The friend who planned the night with you forgets it the moment you go live. Verified: `built_set`/`set_plan`/`planned_curve`/`setlist` absent from `runtime/`, `state/`, `agent/` (grep empty). Both halves exist (built-set JSON producer in `library/`, live phase state in `state/`) — never joined.
- **Proof tier:** SRC (state carries the plan, coach cites it) → LIVE (loaded set + live phase → "two tracks ahead of your build" grounded line).
- **Gate:** `vibemix-grounding-review` (new evidence source must register in `EvidenceRegistry` or strip).
- **Effort:** ~1d (a new read-only `set_plan` field on `MusicState`, single-writer respected, + a coach evidence atom).
- **$-leverage:** **★★★★** — turns set-prep (a paid Pro feature) into a live differentiator; nobody else's co-host knows your plan.

### W3 — Live taste learning (suggestion accept/reject → `taste_model`)
- **One-line spec:** On a suggestion accept/reject outcome, append a `FeedbackEvent` to `taste_model` and re-weight off the live `0.05` floor so the co-host stops re-suggesting transitions you reject.
- **Gap it closes:** M4 + D3. `intel/taste_model.py` is built + 7 tests but absent from coach loops; no live `FeedbackEvent` emit. The "this thing KNOWS me" hit is unwired on the live side.
- **Proof tier:** SRC (a reject event lowers that candidate's score next call) → LIVE.
- **Gate:** `vibemix-grounding-review` + privacy note (it persists a taste signal — confirm against the opt-in posture; cross-ref H6 in the land queue).
- **Effort:** ~1d (`suggestion_service` already threaded into `coach_loop` — append on outcome + a re-weight path).
- **$-leverage:** **★★★** — personalization moat; gated by the privacy decision (Kaan), so sequence after W1/W2.

### W4 — Cut or feed the dead `[tend:]` grammar slot
- **One-line spec:** Either register `tend` atoms at profile-build (`profile/builder.py` → `("tend",fact,t)`) so `[tend:]` resolves, OR delete the slot from `matrix.py:126` + `EVIDENCE_SOURCES`.
- **Gap it closes:** Dead grammar. `[tend:<fact>]` is offered to the live model (`matrix.py:126`) and lives in the grammar (`evidence_registry.py:184`, one of 12 `EVIDENCE_SOURCES`) but **no `registry.write(…,"tend",…)` exists** — every `[tend:…]` the model emits is always stripped. Fail-safe but dishonest grammar (the model is invited to cite something that can never resolve).
- **Proof tier:** SRC.
- **Gate:** `vibemix-grounding-review` (touches the citation grammar / `EVIDENCE_SOURCES`).
- **Effort:** ~5min (cut) to ~0.5d (feed). **Recommend the cut** unless profile-tendency citations are wanted now.
- **$-leverage:** **★★** — honesty cleanup; small personalization upside if fed.

### W5 — Decision: `grade_move` / `calculate_transition` coach intent
- **One-line spec:** Two-part DECISION packet — (a) confirm `grade_move` is UI-only by design (only caller is `pill/index.ts:1955`) or add a coach consumer; (b) decide whether `calculate_transition` ("16 bars to bring B in", currently demo-only) earns a coach call-site (it needs a live beatgrid → rides B2).
- **Gap it closes:** Two orphan exports flagged in the wiring map with ambiguous intent. Verified: `grade_move` zero Python callers; `calculate_transition` callers = `automix_demo.py` only.
- **Proof tier:** SRC (decision doc + tests if wired).
- **Gate:** `vibemix-grounding-review` if either gets a coach line.
- **Effort:** low (decision); the `calculate_transition` wire is gated on B2's grid.
- **$-leverage:** **★** — clears two ambiguous orphans so they stop showing up in every audit; low product upside on its own.

---

## 2. NEW BUILD — earns capability that doesn't exist yet

### B1 — Universal Library Ingest (the market unlock) ★ TOP NEW BUILD
- **One-line spec:** Fill the `library/sources/` seam with three new `LibrarySource` parsers behind the existing `ingest_source` orchestrator — **Traktor `.nml` → Serato (crates+DB V2+GEOB) → Engine DJ `m.db`** — and flip the Rekordbox `master.db` policy as a fourth sub-task.
- **Gap it closes:** The product ingests exactly ONE ecosystem today. Verified: `library/sources/` = `base.py` + `rekordbox.py` only; `__init__.py` literally says *"Rekordbox collection.xml today; Serato / Traktor later"* — the seam was designed and never filled (`MIXXX-ARSENAL.md` I.0). Serato/Traktor/Engine/Denon DJs — the majority of the market after Rekordbox — hit a closed door at onboarding.
- **Why it's the highest-onboarding-leverage build (Kaan's explicit candidate):** it's the discovery/onboarding wedge the strategy memos call the hero, and it's **almost entirely parsing**, not DSP or ML — XML (`xml.etree`), plain SQLite (`sqlite3`), and a trivial TLV. **Apache-clean, zero new GPL exposure** (clean-room from public Mixxx-wiki specs; MIT/MPL Python ports as cross-checks only). Each reader simultaneously delivers beatgrids + cues + keys → it's also the cheapest beatgrid/key/cue source for the Earned skill-tree (one parsing milestone feeds three DSP gaps for free).
- **Recommended packet split (write as 4 small packets, not one mega):**
  - **B1a — Traktor `.nml`** ~0.5d. Cheapest reader; mirror `RekordboxLibrary.load_xml`'s shape, swap schema; CUE_V2 + 0–23 key → Camelot. **Francesco's DJ network base.** Write this packet FIRST — lowest-risk proof the seam works end-to-end.
  - **B1b — Serato** ~2d. Highest installed base after Rekordbox; clean-room TLV crate+DB V2 parser (~150 lines `struct.unpack`) + GEOB Markers2/BeatGrid decoder (the *inverse* of `export_serato.py` we already own).
  - **B1c — Engine DJ `m.db`** ~1.5d. Plain unencrypted SQLite; stdlib `sqlite3` + the documented `PerformanceData` blob layout. Denon Prime / standalone-hardware segment.
  - **B1d — Rekordbox `master.db` policy flip** ~1d. **Not even a build** — `pyrekordbox` (MIT) is already a pinned dep; flip the `sources/rekordbox.py` XML-only policy, add a `RekordboxDbSource`. Kills the #1 onboarding friction (the manual File→Export Collection step). **Caveat for the packet:** accepts the `sqlcipher3-wheels` native dep in `[ai-local]`/installer — must verify against the notarization flow before committing (cross-ref the signing packet).
- **Proof tier:** SRC (each parser unit-tested against a fixture library, top-K parity with the Rekordbox path) → LIVE (KAAN imports a real Serato/Traktor library, cues/grids land as `CueAnchor`s).
- **Gate:** `vibemix-grounding-review` (new evidence enters CLAP/Earned) + the `RekordboxLibrary.CACHE_PATH` monkeypatch trap (CLAUDE.md: library tests MUST monkeypatch or they clobber the real `library.pkl`).
- **Effort:** ~5 focused days total across the 4 sub-packets; collision-free (own island, zero edits to coach/agent/`__main__`).
- **$-leverage:** **★★★★★ for market reach** — the only build here that *gets new users* rather than improving the experience for users we already have.

### B2 — Practice-Deck Loop (the Mastered-beatmatching unlock)
- **One-line spec:** Build `learn/practice_loop.py` — a block-loop driving the owned `MiniDeck` (`audio/miniplayer.py`) → `grade_beatmatch` → emit `Event("BEATMATCH_GRADED")` + `registry.write((…,"BEATMATCH_GRADED",t))`, lighting the waiting consumer at `skill_recognizer.py:154`.
- **Gap it closes:** L1 + R1. The headline DJ skill can never be earned. Verified: `grade_beatmatch` 6 callers, ALL tests (codegraph); `BEATMATCH_GRADED` has no emitter (grep = docstrings + consumer only); `learn/practice_loop.py`/`practice_runtime.py` NOT-FOUND; `MiniDeck.seek()` NOT-FOUND. The honesty-cap `_HONEST_UNCREDITABLE_V11=("beatmatching",)` masks the gap (removing fix-pressure) — this packet is what lets the cap be lifted.
- **The cascade (why it's worth the multi-day cost):** it's the single producer that lights `grade_beatmatch`, `BeatGrid`, `xfade`, `cue_placement_judge`, AND `calculate_transition` at once — the entire own-player cluster. Build this before any cue-judge packet (L6) or that's just a second orphan.
- **Proof tier:** SRC (scripted rate-writer drives a LOCKED grade through to the registry) → LIVE (on-rig grade clears the honesty mask).
- **Gate:** `vibemix-grounding-review` (a new spoken-credit path) — credits must be earned by a real cited grade, never scripted (Invariant #3; do NOT reintroduce demo-mode patterns).
- **Effort:** ~2–3d (`MiniDeck.seek()` ~½d + `BeatGrid.from_anlz()` ~½d + the loop + emit). Hard math already ported in `beatmatch_judge.py`.
- **$-leverage:** **★★★★ (highest NEW-build for the existing user)** — converts 3 test-enforced dead engines into a shippable, citation-grounded Mastered competency; the only thing that lifts the Earned Wall past its single live-creditable skill.

### B3 — R-SLOP grounding siblings (the EQ-keystone's cheap fast-follows)
- **One-line spec:** A single PR-sized packet adding `audio/lufs.py` (short-term LUFS, energy-vs-fader disambiguation) + `state/loop_geometry.py` (deterministic loop/beatjump geometry past the 400ms dedup) and wiring the **existing** `audio/xfade.py` equal-power engine into the live R-SLOP guard in `deck_context.py`.
- **Gap it closes:** L3 + H1 + H2. The cheapest extensions of the just-proven EQ-keystone double-gate. Verified NOT-FOUND: `audio/lufs.py`, `state/loop_geometry.py`. Verified: `audio/xfade.py` EXISTS but is **not imported by the `state/` live guard** (the `xfader` refs in `deck_context.py:108/2288/3597` are the old 0–127 *label* path, not the equal-power engine — confirmed). The loop-geometry piece must route loop events past the 400ms dedup (`midi/state.py:226`) — a 1/16 roll re-triggers inside the window.
- **Proof tier:** SRC (predict-on-lane / measure-on-lane only — never master-sum; keep the `dsp_delta_not_causal_proof` humility).
- **Gate:** `vibemix-grounding-review` (each adds a causal-claim license; must not over-claim on the master-only rig).
- **Effort:** ~½–1d each, numpy-only, no new dep — whole cluster in one PR.
- **$-leverage:** **★★★ grounding-per-hour** — highest now that the EQ-keystone pattern proved viable; narrator→coach on more move types.

### B4 — Controller-map catalog harvest (10 → the controller everyone owns)
- **One-line spec:** Harvest Mixxx's `res/controllers/` mapping catalog (hundreds of community device maps) into our `midi/profiles/` format — a **data** transcription (CC/note layout per device), NOT a code port.
- **Gap it closes:** We ship ~10 hand-mapped controllers; only the FLX4 is hardware-verified (`MIXXX-ARSENAL.md` II.9; H9 in the critique). Richer MIDI maps feed the `recent_moves` evidence the EQ keystone grounds on — so this directly amplifies B3/the keystone.
- **Proof tier:** SRC (each new profile round-trips a synthetic MIDI stream into the move vocabulary) → LIVE (only verifiable per-device with the hardware; ship as "community-verified" until a DJ signs off, per H9's honest framing).
- **Gate:** `ipc-wiring-checker` not needed; just the MIDI profile schema test. No grounding-review (no spoken change).
- **Effort:** linear in devices we care about — ~30min transcription per device from Mixxx's `<control>`→`<status>/<midino>` maps.
- **$-leverage:** **★★** — market-reach (more DJs' gear works out-of-box) at near-zero per-device cost; honesty-bounded (don't claim "verified" for un-eared maps).

### B5 — Debrief → cited recap PNG (the viral flywheel)
- **One-line spec:** A Canvas→PNG share card off the built debrief substrate (TL;DR, drills, `citation_event_id`, `buildVerdictText`) — "the moat made shareable."
- **Gap it closes:** L5. Verified: no `toBlob`/`toDataURL`/canvas-png producer in `tauri/ui/src` or `debrief/`. The debrief data exists; the share artifact doesn't.
- **Proof tier:** SRC (deterministic PNG render from a fixture debrief) — offline, no TTS cost.
- **Gate:** `frontend-enforcement` (it's a visual artifact — must not be AI slop) + `vibemix-grounding-review` (the card cites real `citation_event_id`s, never invents a moment).
- **Effort:** ~1–2d, offline/deterministic.
- **$-leverage:** **★★ growth** (not engine) — the cheapest organic-acquisition lever; lower priority than the W-tier wiring but higher than most new copy.

### B6 — Off-the-wire deck identity (Pro DJ Link / StagelinQ) — RESEARCH-FIRST, do NOT packet yet
- **One-line spec:** (Flagged for completeness, NOT recommended as a near-term packet.) A network-protocol listener for real two-deck identity on rigs where audio can't be split.
- **Gap it closes:** L7 / RED-TEAM ④ / B-6 — the "deck B silent" wound on the common rig. Verified ZERO code (`grep prolink|stagelinq|51337` empty).
- **Proof tier:** LIVE-only — needs hardware to verify, multi-day protocol build.
- **Gate:** can't be SRC-proven; needs a hardware spike before any packet.
- **Effort:** multi-day, hardware-gated.
- **$-leverage:** **★★ structural but premature** — write a RESEARCH spike packet, not a CODEX_READY build packet. Listed so it's not forgotten, explicitly **deferred**.

---

## 3. ONE BONUS — a live BUG that needs a packet (not in either source doc as a packet)

### X1 — Voice picker resolves all 8 picks to ONE wrong MOSS voice
- **One-line spec:** Repopulate `SettingsDrawer.ts:545 VOICE_OPTIONS` from MOSS `list_builtin_voices()` and re-default off the non-existent `"kore"`, OR cut to one voice and delete "six voices" from the partner brief.
- **Gap it closes:** H1 — a **live code bug the read-first packets missed**, now verified at HEAD: UI `VOICE_OPTIONS` = 8 retired-Gemini names (`SettingsDrawer.ts:546-553`: kore/puck/charon/fenrir/aoede/leda/orus/zephyr); config default `voice: str = "kore"` (`config_store.py:169`) does not exist in MOSS (`local_tts.py:49 _DEFAULT_VOICE="Adam"`); `local_tts.py:276 next((v for v in voices if v.get("voice")==voice), voices[0])` → every pick falls through to `voices[0]`. **All 8 picks → one wrong voice.** First thing a DJ does is pick a voice; today it does nothing.
- **Proof tier:** SRC (the picker lists real MOSS voices; a non-default pick resolves to that voice, not `voices[0]`) → LIVE (`drive-vibemix`: two picks produce two audibly different voices).
- **Gate:** `ipc-wiring-checker` (voice flows UI→config→`local_tts`) + `npm run codegen:ipc` if the schema's voice enum changes.
- **Effort:** <1d.
- **$-leverage:** **★★★★** — trivially reproducible, ship-blocking first-impression bug, and it's a real fix not just copy. **Write this packet; it's cheaper than W2/W3 and higher-impact than most copy work.**

---

## 4. RANKED SHOPPING LIST (what to write today, in order)

| Rank | Packet | Class | Effort | Proof tier stuck-at | Gate | $-leverage |
|---|---|---|---|---|---|---|
| **1** | **W1** spoken next-track + transition verdict | WIRE | ~0.5–1d | SRC→LIVE | grounding-review | ★★★★★ |
| **2** | **B1a** Traktor `.nml` reader (Universal Ingest seed) | BUILD | ~0.5d | SRC | grounding-review | ★★★★★ (market) |
| **3** | **X1** voice-picker MOSS fix (live bug) | BUILD/FIX | <1d | SRC→LIVE | ipc-wiring-checker | ★★★★ |
| **4** | **W2** prep→live set awareness | WIRE | ~1d | SRC→LIVE | grounding-review | ★★★★ |
| **5** | **B1d** Rekordbox master.db policy flip | BUILD | ~1d | SRC→LIVE | grounding-review + notarization check | ★★★★ (kills XML friction) |
| **6** | **B1b** Serato reader | BUILD | ~2d | SRC | grounding-review | ★★★★ (biggest base) |
| **7** | **B2** practice-deck loop (Mastered beatmatching) | BUILD | ~2–3d | SRC→LIVE | grounding-review | ★★★★ (skill unlock) |
| **8** | **B3** R-SLOP siblings (lufs+loop_geo+xfade-wire) | BUILD | ~½–1d ea | SRC | grounding-review | ★★★ |
| **9** | **W3** live taste learning | WIRE+BUILD | ~1d | SRC→LIVE | grounding-review + privacy gate | ★★★ (Kaan-gated) |
| **10** | **B1c** Engine DJ `m.db` reader | BUILD | ~1.5d | SRC | grounding-review | ★★★ |
| **11** | **B4** controller-map catalog harvest | BUILD (data) | linear | SRC | profile schema test | ★★ |
| **12** | **B5** debrief recap PNG | BUILD | ~1–2d | SRC | frontend-enforcement + grounding-review | ★★ (growth) |
| **13** | **W4** cut/feed dead `[tend:]` slot | WIRE-or-CUT | 5min–0.5d | SRC | grounding-review | ★★ |
| **14** | **W5** grade_move / calculate_transition intent | DECISION | low | SRC | grounding-review | ★ |
| — | **B6** off-the-wire deck identity | RESEARCH | multi-day | LIVE-only | (spike first) | ★★ DEFERRED |

**Write-today recommendation (the three that pay back fastest and collide with nothing):**
1. **W1** — the sharpest founder-decision in the synthesis: the live voice is disconnected from both the recommendation engine and the best transition engine, both already running silently. Pure wiring, ~0.5–1d, grounds on metadata the deck already has.
2. **B1a** (Traktor) — the cheapest seed of the Universal-Ingest milestone Kaan flagged; proves the dormant `library/sources/` seam end-to-end and opens Francesco's DJ base. Own island, zero collision.
3. **X1** — the voice-picker bug; cheap, ship-blocking, and a real fix.

**Then the Universal-Ingest body (B1b/B1c/B1d) as a milestone** — ~5 days of Apache-clean parsing, the single highest market-reach move, fully parallel to all coach/agent work.

---

### Provenance
Source docs (all under `/Users/ozai/projects/dj-set-ai/.planning/packets/2026-06-01/`): `CRITIQUE-LOST-AND-MISSING.md`, `WIRING-GAP-MAP-CODEGRAPH.md`, `MIXXX-ARSENAL.md`, `CLAUDE_LAND_QUEUE.md`, the 39 existing `CODEX_READY-*.md`.
Live re-verification at HEAD `b98dd885`: `library/sources/` = base+rekordbox only (`ls`); `score_transition` callers = pill+Viber, zero coach (codegraph); `grade_beatmatch` 6 callers all tests (codegraph); `next_suggestion`/`built_set` absent from coach/state (grep); `practice_loop.py`/`lufs.py`/`loop_geometry.py` NOT-FOUND (`ls`); `xfade.py` exists, not imported by `state/` guard (grep); voice bug `SettingsDrawer.ts:545-553` + `config_store.py:169` `"kore"` + `local_tts.py:49,276` (read).
