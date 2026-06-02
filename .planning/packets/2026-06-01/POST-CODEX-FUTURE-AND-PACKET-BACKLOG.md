# POST-CODEX FUTURE & PACKET BACKLOG

**Role:** Future Synthesizer (read-only). **Repo HEAD at write time:** `6150c80d` ("feat(viber): discover local library setup candidates") — the tree has moved past every pin in the source packets (`769e32a3` → `b98dd885` → `6150c80d`). Re-pin before routing.
**Inputs synthesized:** the POST-CODEX projection (analyst 1), the NEW-PACKET-BACKLOG shopping list (analyst 2), `CRITIQUE-LOST-AND-MISSING.md`, `WIRING-GAP-MAP-CODEGRAPH.md`, `LICENSE-STRATEGY-APACHE-VS-GPL.md` summaries, and the LAND_QUEUE board.
**Ground-truth re-verification at `6150c80d`:** EQ keystone `eq_move_model.py` present (8KB, commit `970e165b`) ✓. Voice default `"kore"` at `config_store.py:169` + docstring `:25` ✓. `audio/lufs.py` + `state/loop_geometry.py` → NOT-FOUND (os error 2) ✓. `audio/xfade.py` present but not wired into `state/` ✓. `library/sources/` = `base.py` + `rekordbox.py` only ✓.

---

## 1. POST-CODEX PRODUCT WALKTHROUGH — what we have when the queue clears

The current 39-item queue is **~90% release hygiene + one offensive engine** (the EQ keystone, already SRC-landed at `970e165b`). When it fully lands, surface by surface:

- **Co-host (live brain) — strongest surface, becomes a *thin* coach.** The spine (single-writer `MusicState`, EventDetector, EvidenceRegistry, CitationLinter, 63-phrase slop filter, English guard, 8 genre detectors, 2-signal Vibe Judge) is BUILT+WIRED+tested. The keystone crosses the named line: it can say *"your low-cut thinned the bass — sub cratered 18 dB"* and **refuse** that line on a breakdown where the bass wasn't there (`_licensed_move_effect` double-gates predicted∧measured at `deck_context.py`). Plus S1 (delete dead cloud-TTS seams → MOSS-only by absence), S3 (delete `demo_mode`), S4/S7 (green suite, un-shadow `coach.py`), H3 (HEARTBEAT idle-speak grounding-audited). **Net: perceives audio+MIDI, refuses to slop (proven LIVE 2026-06-01), licenses *one* class of cause-and-effect (EQ/filter).**
- **Viber / Crate (set-prep) — fully wired, finally proven.** FE → Tauri `invoke` → CLI subprocess → renderers, 9 `library_*` commands, seen-set anti-hallucination, Codex backend. Queue adds H4 (`ipc-wiring-checker` both-ends proof), S5 (delete 5 dead `ipc.library.*` ws types), freshness lane. **Residual: no captured real `codex exec` run — correctness stays SRC-proven, never LIVE-proven.**
- **Library (embed/search/ingest) — real engine, gains freshness skin.** CLAP + centered-cosine is REAL-proven (raw 0.85 → centered −0.15 on committed vectors). Queue lands file-watcher (live at `__main__.py:2300`), staleness handlers, S8 (surface auto-cue export as first-class Crate action — the named MOAT, `label_recall=1.0` on 6 mp3s, currently undiscoverable), H8 (folder re-index). **Residual: `search`/`similar` stay CLI-only — no GUI raw-text-search consumer.**
- **Learn / Earned — wired, headline skill stays capped.** Recognizer→credit→Earned Wall→Mastered vocal is BUILT+WIRED. But beatmatching stays masked (`_HONEST_UNCREDITABLE_V11=("beatmatching",)` at `skill_recognizer.py:105`) because the `BEATMATCH_GRADED` producer is absent — R1, RESEARCH_ONLY, explicitly NOT in the queue. **Net: credits exactly ONE skill live (`harmonic_mixing`). The headline competency can never reach Mastered.**
- **Cue / hot-cue export — already shipped, gets discoverable.** Real Cue tab → `invoke library_cue_folder` ships Rekordbox/M3U8/Serato today; S8 surfaces it. CUE-DETR ONNX producer stays orphaned (model not hosted); proven path is the heuristic.
- **Debrief — wired, one boundary never run live.** GUI-spawned 2nd window :8766, cited-critique gate, e2e-tested. **Residual: Rust↔Python debrief boundary never captured live; no recap/share artifact.**
- **Release blockers (B-1…B-6) clear the kill-shots.** B-1 (host/bundle MOSS, pin URL/SHA, first-run download), B-2 (first-run voice-status surface), B-4 (rebuild+sign from clean HEAD — **DMG currently 177 commits stale, arm64-only, born mute**), B-3 (proxy round-trip live key), B-5/B-6 (live-rig FLX4, deck-pair identity). **B-3/B-5/B-6 are Kaan/infra/hardware, not Codex lanes.**

**Net product:** a grounded, anti-slop, voice-working co-host that **coaches on EQ/filter moves and narrates everything else**; a complete set-prep agent; a fresh-aware library with discoverable cue export; a one-skill-creditable learn module; a signed DMG a stranger can run. **A real, shippable, honest v1 — an order of magnitude beyond today's voice-muted stale build.** It is *ship-able*, not yet *deep*.

---

## 2. THE RESIDUAL GAP — what's still missing after the whole queue lands

Every item grep-verified absent at `6150c80d`:

- **A. The voice picker is a live BUG no queue item touches (ship-blocking, packets missed it).** Default `"kore"` (`config_store.py:169`, docstring `:25`) does **not exist in MOSS**; `local_tts.py:276` falls through `next((v...), voices[0])` so all 8 picker options resolve to **one wrong voice**. First thing a DJ does does nothing. The partner brief promises "six distinct voices." `<1d`, a bug not copy, invisible in the queue.
- **B. The co-host coaches on EXACTLY ONE axis — everything else is still narration.** After the keystone it still cannot: **speak a next-track recommendation** (`coach.py:644` computes only the silent pill — the single most valuable spoken DJ act is never voiced, ~0.5–1d wiring); **see the prepped set** (`built_set`/`set_plan`/`planned_curve` absent from `state/`+`runtime/coach.py`+`agent/` — prep→live amnesia, never attempted); **use the 10-dim `transition_scorer`** (absent from both coach loops; only shallow 2-signal `transition_judge` is live, ~0.5d); **hear the DJ talk to it** (`KAAN_SPOKE` is a bare RMS duck, "the mic-STT placeholder" — no ASR, the gap that most separates *friend* from *commentator*); **coach beatmatching** (needs live per-deck beatgrid M5 + absent `BEATMATCH_GRADED` R1, both deferred).
- **C. The cheap grounding siblings that widen "coach" past one axis don't exist.** `audio/lufs.py` + `state/loop_geometry.py` → NOT-FOUND; `xfade.py` exists but is **not imported into `state/`**. Each ~½–1d numpy-only. The double-gate pattern is *proven viable* (keystone landed) — the queue just stops at one filter family. Every axis you don't add is an axis where the co-host keeps narrating.
- **D. Market reach is structurally narrow and the queue doesn't widen it.** Techno-only (all 9 structure detectors techno-shaped; `GenreRouter` → `"unknown"` chain for house/DnB/disco/hip-hop = most of the paying market). Rekordbox-only library parsing (`library/sources/` = `base.py`+`rekordbox.py`; the `LibrarySource` Protocol + `ingest_source` orchestrator are wired — each new parser is a collision-free island lighting the whole CLAP/Viber/pill/Earned stack for free). Per-deck identity needs a rig 90% won't build (Pro DJ Link/StagelinQ = zero code; honest v1 = master+MIDI).
- **E. Nothing makes it feel like *YOUR* friend, or shareable.** `taste_model` built (`intel/taste_model.py`) but absent from coach loops — no live FeedbackEvent on accept/reject, weight stuck at `0.05`. No count-based personal-habit recognition. No debrief recap PNG / shareable scorecard — the viral flywheel where "the moat *is* the marketing." All deterministic, offline, low-cost, scored ★★+ in the creative forge; none queued.

**Honest verdict:** the queue gets you to *honest and alive*; it does not get you to *deep and personal and viral*. The residual gap is **not invention** — it's the 2nd–6th grounding axes plus the recommendation/personalization/share layer, all **wiring of already-built engines** (`next_suggestion`, `transition_scorer`, `taste_model`, the `LibrarySource` parsers) plus a handful of ~1d numpy producers (lufs, loop_geometry, genre detectors).

---

## 3. NEW PACKET BACKLOG (ranked)

| # | Packet | Gap closed | Wire/Build | Proof tier | Gate | Effort | $-leverage |
|---|--------|-----------|-----------|-----------|------|--------|-----------|
| W1 | Spoken next-track + transition verdict | M1+L2+D2 — voice reads `SuggestionService`+`score_transition` into a `[track:]`/risk-cited line | WIRE | SRC→LIVE | grounding-review | 0.5–1d | ★★★★★ |
| B1a | Traktor `.nml` ingest (Universal-Ingest seam proof) | M-reach — opens Francesco's base, proves the dormant `sources/` seam | BUILD | SRC (parser unit-test) | clean-checkout | ~0.5d | ★★★★★ |
| X1 | Voice-picker bug fix (`VOICE_OPTIONS`←MOSS, re-default) | live ship-blocker | WIRE/BUILD | SRC→LIVE | ipc-wiring + grounding | <1d | ★★★★ |
| B2 | Practice-deck loop → emit `BEATMATCH_GRADED` | M5+R1 — unlocks Mastered beatmatching, lights own-player cluster | BUILD | SRC→LIVE | grounding-review | 2–3d | ★★★★ |
| W2 | Prep→live set awareness (Viber set JSON → `MusicState`) | M2 — kills prep/live amnesia | WIRE | SRC→LIVE | grounding-review | ~1d | ★★★★ |
| B1b | Serato `.crate`/DB ingest (inverts owned `export_serato.py`) | M-reach — biggest installed base | BUILD | SRC | clean-checkout | ~2d | ★★★★ |
| B3 | R-SLOP grounding siblings (`lufs.py`+`loop_geometry.py`+wire `xfade.py`) | C — 3 new coach axes | BUILD+WIRE | SRC→LIVE | grounding-review | ½–1d each | ★★★ |
| W3 | Live taste learning (accept/reject → `taste_model` FeedbackEvent) | M4+D3 — off the 0.05 floor | WIRE | SRC→LIVE | privacy + grounding | ~1d | ★★★ |
| B1c | Engine DJ `m.db` ingest (plain SQLite) | M-reach | BUILD | SRC | clean-checkout | ~1.5d | ★★★ |
| B1d | Rekordbox `master.db` policy flip (pyrekordbox MIT dep) | M-reach — kills manual-XML friction | BUILD | SRC | clean-checkout | ~1d | ★★★ |
| W-TS | Wire 10-dim `transition_scorer` into coach loop | B — richer transition voice | WIRE | SRC→LIVE | grounding-review | ~0.5d | ★★★ |
| B5 | Debrief recap PNG (Canvas→share card) | E — viral flywheel | BUILD | SRC→LIVE | frontend-enforcement | 1–2d | ★★ |
| B4 | Controller-map catalog harvest (Mixxx device maps → `midi/profiles/`) | M-reach (data not code) | BUILD | SRC | clean-checkout | ~30min/device | ★★ |
| W4 | Cut/feed dead `[tend:]` slot (offered+grammar, never written) | honesty cleanup | WIRE/cut | SRC | grounding-review | 5min–0.5d | ★★ |
| B6 | Off-the-wire deck identity (Pro DJ Link/StagelinQ) | D — per-deck ceiling | RESEARCH-spike | n/a | hardware-gated | deferred | ★ |
| W5 | `grade_move`/`calculate_transition` consumer decision | UI-only-by-design vs add coach consumer | DECISION | n/a | — | 0.25d | ★ |

---

## 4. RECOMMENDED TOP 5 PACKETS TO WRITE TODAY

Chosen for collision-free islands, fastest payback, and the sharpest founder-decisions:

1. **W1 — Spoken next-track + transition verdict** (★★★★★). The single sharpest move: the voice is disconnected from BOTH the recommendation AND the best transition engine, both already running silently. `score_transition` callers = pill (`next_suggestion.py:657`) + Viber (`toolset.py:313`) only — zero coach. Pure wiring on tested engines.
2. **B1a — Traktor `.nml` ingest** (★★★★★ for reach). The cheapest Universal-Ingest packet, Francesco's base, and the seam proof that opens B1b/B1c/B1d as a ~5-day parallel milestone. The only build that *gets new users*. Own island, Apache-clean (clean-room from public specs).
3. **X1 — Voice-picker bug fix** (★★★★). A live ship-blocker neither source doc framed as a packet: 8 picks → one wrong voice. Repopulate `VOICE_OPTIONS` from MOSS `builtin_voices` + re-default off `"kore"`. A real fix, not copy.
4. **B2 — Practice-deck loop → `BEATMATCH_GRADED`** (★★★★). Lights the whole own-player cluster (grade_beatmatch, BeatGrid, xfade, cue judge) and unlocks Mastered beatmatching — the headline DJ competency the queue deliberately leaves capped. Consumer at `skill_recognizer.py:154` is waiting; emitter is NOT-FOUND.
5. **W2 — Prep→live set awareness** (★★★★). Kills the prep/live amnesia: thread the Viber-built set JSON into `MusicState` so coach can cite "ahead of your curve." `built_set`/`set_plan` absent from runtime/state/agent — never attempted. ~1d wiring.

**Sequencing note:** write W1 + B1a + X1 first (collide with nothing, pay back fastest), then the Universal-Ingest body (B1b/B1c/B1d) as a fully-parallel ~5-day milestone, then B2/W2 as the depth lane. The next *queue* after the current one should be this D-tier deepening + M1/M2/L2/L4 wiring — because that, not more hygiene, is where "real DJ friend" actually lives.
