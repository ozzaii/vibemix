# vibemix — Requirements

**Milestone:** v5.0 "The Useful Cut" — Deck-Aware, Actionable, Unobtrusive
**Started:** 2026-05-21
**Mode:** `gsd-autonomous fully` (recommended grey-area answers + defer blockers to KAAN-ACTION; only privacy rule + destructive risk pause)

## Goal

Turn the co-host from a vibe-narrator into a genuinely **useful** DJ tool: it understands the whole deck (every loaded track + key/BPM), gives feedback a DJ can actually act on (transition mechanics + harmonic key-clash, never hype), and lives in an unobtrusive draggable pill instead of a full-screen mascot.

Everything is held to the project's hard line: **grounded, never hallucinating, no AI slop.** The headline harmonic feature is the strongest anti-slop play in the product — a Camelot key clash is *deterministically verifiable*, so the AI can be *proven* right. The dominant risk is hallucination tripping Kaan's release gate; the milestone is sequenced as an ordered anti-slop chain (citable key source → deterministic verdict → percussive suppression → conservative confidence gate → Kaan-ear veto).

Research-resolved foundations (`.planning/research/SUMMARY.md`, 4 convergent agents):
- **Deck data-source ladder:** pyrekordbox **XML** import primary (carries key/BPM, unencrypted — dodges the post-6.6.5 SQLCipher wall + the `master.db` write-corruption landmine) → **Gemini-vision** reading the deck screenshot we already capture (universal fallback for Serato/djay/Traktor) → in-house **numpy Krumhansl-Temperley** key estimator last-resort. Graceful degradation to `unknown`.
- **Stale-stack correction:** Essentia/librosa are NOT installed; key fallback is in-house numpy, not a heavy C++ dep. CLAP/MERT/OpenL3 stay permanently banned.
- **Pill:** clone `mascot_window.rs` → `pill_window.rs`, same ws:8765 frames, tri-state `primary_surface` config; `tauri-nspanel` + `window-vibrancy` crates; the drag-on-unfocused-window bug is the load-bearing spike.

---

## v5.0 Requirements

### Full Deck Awareness (DECK) — Phase 59

- [ ] **DECK-01**: The co-host maintains a session-wide **deck-state** — every track loaded across the decks (title, key, BPM, energy where available), not just the one currently audible — exposed to the coach the same grounded way `phase`/`bpm`/`mood` are.
- [ ] **DECK-02**: Deck-state is populated from a real data-source ladder: pyrekordbox **XML** primary, **Gemini-vision** deck-screenshot read as universal fallback, in-house **numpy** key estimator last-resort. When no source can resolve a track/key, it is surfaced honestly as `unknown` — never a false-confident guess.
- [ ] **DECK-03**: A new `key:` **evidence source** + citation-linter rule lands so harmonic/transition claims are *citable* — un-cited harmonic feedback is stripped by the existing `CitationLinter`. (Gates the harmonic feature; must land before any harmonic prompt is written.)
- [ ] **DECK-04**: Deck-state integrates into `MusicState` under the **single-writer rule** (read-only poller → `_tick_once` is the only copier), with new event types `KEY_CLASH` + `TRANSITION_OPPORTUNITY` added to the priority/cooldown maps.
- [ ] **DECK-05**: The integration is **strictly read-only** — never writes to any DJ-software database (the `master.db` write-corruption landmine is respected); cross-deck claims are suppressed when the second deck cannot be independently resolved.

### Harmonic + Transition Feedback (HARMONIC) — Phase 60

- [ ] **HARMONIC-01**: Camelot-wheel key relationships are encoded as a **deterministic Python lookup table**; the LLM only narrates a clash the **code already confirmed** — it never computes key intervals itself (the anti-slop guarantee).
- [ ] **HARMONIC-02**: A real key clash fires **only on simultaneous melodic overlap** in clashing keys. A percussive/atonal + breakdown **suppression gate** runs *before* any clash note fires (no clash calls on two drum/tool tracks or during a breakdown/acapella).
- [ ] **HARMONIC-03**: The clash detector is **conservative by default** — suppresses one-step-off-Camelot pairs (adjacent = safe), low-confidence keys, and ambiguous deck-resolution; tuning accounts for the ~57–70% library key-tag accuracy band. Gated behind a **Kaan-ear veto** before it can ship.
- [ ] **HARMONIC-04**: Transition-execution feedback gives **concrete, actionable blend notes** (e.g. EQ bass-swap, phrase alignment, where to start/end the blend) — scoped strictly to what is grounded in deck-state; no advice is emitted when the underlying signals are not available.

### Actionable-Not-Hype Coach Persona (COACH) — Phase 61

- [ ] **COACH-01**: Feedback (coach) mode delivers **concrete, prescriptive DJ notes** (observed → impact → prescribe, using real DJ verbs: kill, swap, cut, filter, wait, tighten) — not narration or cheerleading.
- [ ] **COACH-02**: The persona refactor **extends the in-flight `live-tuning-or-brain` work** (`prompts/matrix.py` COACH cells + `state/coach.py` `task_for_event`) — it does **not** add a new mode (preserves the `_CELLS`/`_VALID_MODES` env-var contract) and flows through both the genai and OpenRouter paths.
- [ ] **COACH-03**: **Hype mode is regression-fenced** with goldens so shared-prompt edits for the coach persona cannot silently break or cold-ify the hype voice.
- [ ] **COACH-04**: Every prescriptive note stays **anti-slop / cited** — it ties to an observed deck-state or event; the warm "friend in your ear" tone is preserved while becoming actionable (no robotic over-correction, cooldown/pacing prevents nagging).

### Floating Pill UI (PILL) — Phase 62

- [ ] **PILL-01**: A small, **always-on-top, transparent, draggable** Super-Whisper-style pill is positionable anywhere on screen and multi-monitor safe.
- [ ] **PILL-02**: The pill is the **primary** live surface via a tri-state `primary_surface` config (`pill` default | `mascot` opt-in/secondary | `none`); the existing Three.js mascot overlay keeps working and does not regress (`mascot-audit` CI fence held).
- [ ] **PILL-03**: The pill **consumes the existing ws:8765 frames** (`ipc.session.snapshot` + `ipc.session.cohost-reaction`) — no new port, no Python delivery change — and shows idle / listening / speaking / expand-on-event states with the real TTS waveform (`Levels.update_voice`) + the citation strip.
- [ ] **PILL-04**: The pill **never steals keyboard focus** mid-set and never covers critical deck info; the drag-on-unfocused-window mechanism is resolved (spike on the built app per tauri#11605/#10767), with mac+win transparency parity.

---

## Future Requirements (deferred — next milestone)

- **ProDJ Link / StagelinQ hardware deck telemetry** (`prolink-connect`) — real per-deck loaded-track + play-state over the network; hardware-gated, deferred from the v5.0 data-source ladder.
- **Live audio key-detection as a primary source** — only the numpy estimator fallback ships in v5.0; promoting audio key-detection to primary (with cross-check) is future.
- **Per-deck low-band/bass-clash DSP** — depends on dual-deck audio separation from a single master stream; bass-clash note stays P2 until feasible.
- **Vibe Mix prep module** — separate commercial BRAVOH product, its own milestone (unchanged from v4.0 deferral).
- **Mixxx OSC adapter + controller-map transpiler** — v3.x candidate, unchanged.

## Out of Scope (this milestone)

- **Next-track recommendation** — the co-host reacts to what's loaded; it does not pick the next song (would invite hallucinated suggestions; out of the grounded-reaction thesis).
- **Transition scoring (1–10 ratings)** — gamified scores are slop-prone and not actionable; feedback is prescriptive notes, not grades.
- **Headphone-cue / pre-listen analysis** — Gemini conflates cue vs master from a single stream; explicitly excluded.
- **Writing to any DJ-software database** — `master.db` write path is unsafe (banned); v5.0 is read-only.
- **Notch-locked / Dynamic-Island-only pill** — would exclude Windows; the pill is a free-floating window on both platforms.
- **The v4.0 signed public binary publish** — still gated on Apple Dev + SignPath (KAAN-ACTION); v5.0 does not change that external clock.
- **New AI providers / new heavy audio deps** — Gemini-only + no-CLAP + no-Essentia held; no scope creep (`feedback_no_scope_creep_clean_utility`).

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| DECK-01 | Phase 59 | Pending |
| DECK-02 | Phase 59 | Pending |
| DECK-03 | Phase 59 | Pending |
| DECK-04 | Phase 59 | Pending |
| DECK-05 | Phase 59 | Pending |
| HARMONIC-01 | Phase 60 | Pending |
| HARMONIC-02 | Phase 60 | Pending |
| HARMONIC-03 | Phase 60 | Pending |
| HARMONIC-04 | Phase 60 | Pending |
| COACH-01 | Phase 61 | Pending |
| COACH-02 | Phase 61 | Pending |
| COACH-03 | Phase 61 | Pending |
| COACH-04 | Phase 61 | Pending |
| PILL-01 | Phase 62 | Pending |
| PILL-02 | Phase 62 | Pending |
| PILL-03 | Phase 62 | Pending |
| PILL-04 | Phase 62 | Pending |

**Coverage:** 17 / 17 v5.0 requirements mapped to exactly one phase ✓ (no orphans, no duplicates)

**Per-phase counts:** P59=5 (DECK-01..05) · P60=4 (HARMONIC-01..04) · P61=4 (COACH-01..04) · P62=4 (PILL-01..04) = 17.
