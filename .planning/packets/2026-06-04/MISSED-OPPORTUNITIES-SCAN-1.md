# MISSED-OPPORTUNITIES SCAN 1 (2026-06-04)

Filtered, HEAD-verified synthesis of four scans (dark-gold, dead-wire, quick-wins, missed-integrations). Every claim below was checked against HEAD; numbers come from the inputs, not estimates.

## Did we miss anything ship-blocking?

A few. Three real misses, all small, all verified, all already feed a Codex lane. No hidden engine surface was missed and the tree is well-wired. The three are honesty/first-impression copy on the public face plus one grounded backend wire that the offline twin already proves.

**SHIP-BLOCKING-MISS**

1. **README ships legacy `altidus.world` brand at OSS launch** — QUICK-WIN #1
   - What: the public README of the Apache repo points its marketing links at the retired `altidus.world` brand, contradicting the locked `bravoh.ai` decision (`user_bravoh_email_domain.md`).
   - Where: `README.md:59` `[Bravoh](https://altidus.world)`, `README.md:303` same, `README.md:307` `altidus.world/vibemix` CTA.
   - Value: this is the first thing a stranger reads when the repo goes public. Wrong brand on the front door reads as abandoned.
   - Lane: **A (frontend/docs).**
   - Effort: swap the 3 marketing links only. Leave the `api.altidus.world` proxy/updater refs (`README.md:39`, `:241`, `:259`) — they are true to the live endpoint; migrating the proxy host is a Kaan call, not a copy fix.

2. **Settings -> About shows a hand-drifted wrong version** — QUICK-WIN #2
   - What: the About panel hardcodes a version and build date that disagree with every real source and is built ~104 commits stale.
   - Where: `help-group.ts:37` `VIBEMIX_VERSION="0.1.0-rc1"` + `help-group.ts:40` `BUILD_DATE="2026-05-14"`, vs `tauri.conf.json5:13` / `Cargo.toml:9` `0.0.1` and `pyproject.toml:7` `0.1.0-dev0`.
   - Value: a commercial app showing a fabricated version in its own About panel is the "nobody's home" slop tell.
   - Lane: **A (frontend), ride the DMG-rebuild lane.**
   - Effort: one-line reconcile to a single source.

3. **Live `active_genre` not threaded into the pill's transition scorer** — MISSED-INTEGRATION #1
   - What: the offline Viber path passes `genre_profile`, but the live "what mixes next" engine never receives genre, so the real per-genre scoring tables are dead live. Offline twin is genre-aware; live twin is genre-blind.
   - Where: offline passes it at `toolset.py:470`; live `next_suggestion()` (`next_suggestion.py:100`) has no genre param and builds `TransitionScoringInput` without it (`next_suggestion.py:754`), so `role_pair_score`'s per-genre tables (`musical_ontology.py:194-202`, `GENRE_ROLE_ADJUSTMENTS:50`) never fire. The signal is real audio-derived: `active_genre` is written at `refresh.py:1232` and degrades to `"unknown"`, so it stays grounded.
   - Value: the live "what mixes next" pill is the exact "feels generic" surface the quality bar blocks. Genre-blind here is the failure mode.
   - Lane: **B (backend).**
   - Effort: ~10-line plumb. Ship with a test asserting the `"unknown"` path is byte-identical to today.

## Post-ship backlog

- `library/auto_tags.py` (DARK-GOLD #1) — already on the board; gated by missing owner-labeled truth. Lighting it now is an anti-slop regression.
- Mid-session chatterbox TTS has no MOSS floor (QUICK-WIN #3) — `chatterbox_tts.py:262` is single-provider, but `mlx_audio` is absent from the venv, so it is dark today and not v1-blocking. Append MOSS as a 2nd provider the moment the mlx extra lands.
- `devtools` Cargo feature compiled into ship build (QUICK-WIN #4) — `Cargo.toml:29`; inert today (no `open_devtools()` caller) but leaves Inspect reachable. Gate behind `debug_assertions`. Hardening, not an honesty blocker.
- Live `detected_genre`/`genre_confidence` -> timecode genre slot (DEAD-WIRE #1) — on the wire at `ws_bus.py:1202-1203` with zero FE consumers; cheap wire but needs a `genre_confidence` floor (owner abstain-policy decision).
- Grounded virtual track playhead (DEAD-WIRE #2) — a real BUILD (schema + IPC + layout), not a wire.
- `phase`/`phase_history` -> phase-tape (DEAD-WIRE #3) — unmounted UI plus empty feed; a layout call mid-ship.
- Cross-deck harmonic verdict -> co-host prompt (MISSED-INTEGRATION #2) — small wire, but it changes what Sven says, so it must route through `vibemix-grounding-review`.
- Debrief drills -> Learn skill-tree (MISSED-INTEGRATION #3) — a genuine BUILD (drill-to-skill mapping). LEARN-ARMY gold; do not pull into endgame.

## Killed (not real / duplicate)

- `learn/course_pack.py` (DARK-GOLD #2) — dev/content authoring tooling, zero end-user surface by design.
- `SuggestionService.decision_for_state` / `decision_payload_for_state` (DARK-GOLD #3) — test-only redundant API, no user value.
- `latency_ms` snapshot wire (DEAD-WIRE #4) — deliberately retired readout (`cohost.ts:13`), not a missed opportunity.
- All "Cleared" / "already-correct" / "not a miss" items across the four scans — verified wired or correct, do not re-investigate: transition_verdict_voice, multi-source importers, cue_folder, sequencer, judge_voice, decision_runtime, taste/profile loop, mastered_marker_writer, learn judges, detectors/genres, debrief modules, MemoryRecall, track_relation, cue_detect `source="fallback"`, provenance stamp, estimated-key null, GitHub-button allowlist, README CLAP/retention claims, proxy/recall defaults.

## Scan coverage

This scan swept four axes — dark-gold (built-but-unsurfaced modules), dead-wire (one-ended IPC/ws types), quick-wins (cheap honesty/hardening fixes), and missed-integrations (offline-vs-live capability asymmetry) — and HEAD-verified every load-bearing claim. The engine surface came back clean (no orphaned brain), so the next scan should go deeper on live-runtime behavior under real audio (drive-vibemix perception loop) and on the Learn teaching loop's audio/grade wiring, where these axes do not reach.
