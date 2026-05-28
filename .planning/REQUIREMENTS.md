# vibemix — Requirements

**Milestone:** v11.0 "Earned"
**Status:** Defining (roadmap pending)
**Last updated:** 2026-05-29

> Scope rule (anti-creep, LOCKED): a v11.0 phase must add the **felt reward of progression** on top of the existing v9.0 Lesson One module **without** a new AI provider, ws port, IPC envelope family, heavy dep, lesson content, or live event detector — and without regressing any of the four cardinal invariants. Acid test: *"Does this make an existing learning/playing capability feel earned and progressed — grounded in real lesson outcomes and real cited live events — without growing the product surface or writing to `profile.json`?"* If not, defer.

---

## v11.0 Requirements

### SKILL — Skill-tree mastery model
- [ ] **SKILL-01**: User's 36 lessons / 3 courses map to ~6 named DJ skills (Deck Control · Beatmatching · EQ Mixing · Harmonic Mixing · Transitions · Phrasing & Performance), each with a two-stage mastery bar (Locked → Competent → Mastered).
- [ ] **SKILL-02**: A pure-logic `SkillTree` / `SkillProgress` engine (`src/vibemix/learn/skill_tree.py`) computes each skill's stage and fill from lesson/recital outcomes + live demonstrations; it is the sole writer of skill state and never mutates `MusicState` (Invariant #1, AST-gated).
- [ ] **SKILL-03**: The skill→lesson→live-event mapping (which lessons feed which skill, each skill's Competent threshold + Mastered requirement) is declared in one readable manifest, so a contributor can understand the tree without reverse-engineering the engine.

### COMP — Competent stage (Learn-grounded fill)
- [ ] **COMP-01**: Completing a lesson advances its skill's Competent-stage fill, weighted by quality — a recital pass and a first-try (0-strikes) completion fill more than a click-through.
- [ ] **COMP-02**: A skill reaches "Competent" only after the user passes that skill's recital honest-score gate; pure click-through can never reach Competent.

### MAST — Mastered stage (Live-grounded, anti-slop heart)
- [ ] **MAST-01**: A skill's Competent→Mastered segment stays locked until the skill reaches Competent.
- [ ] **MAST-02**: Once Competent, a skill's Mastered fill advances only when the live co-host detects the user performing that skill in a real session, mapped from existing EvidenceRegistry event types (MIX_MOVE / LAYER_ARRIVAL / harmonic / EQ-band MIDI / beatmatch) — no new detectors are invented.
- [ ] **MAST-03**: Every live mastery credit must resolve a valid citation in `EvidenceRegistry`; an un-cited or fabricated event grants zero credit (Invariants #2 + #3, test-pinned).
- [ ] **MAST-04**: A skill flips to "Mastered" after a declared number of grounded live demonstrations; the count and a `first_mastered_at` timestamp persist across sessions.

### DATA — Persistence & migration
- [ ] **DATA-01**: Skill-tree state persists in a `skills` block inside `~/.cache/vibemix/learn-progress.json` via the existing atomic write; skill data is never written to `profile.json` (the 5-field privacy contract stays intact).
- [ ] **DATA-02**: `learn-progress.json` migrates schema v1→v2 by deterministically back-filling each skill's Competent-stage fill from existing lesson/course completions; a corrupt or older file recovers gracefully (mirrors the existing corrupt-read recovery).
- [ ] **DATA-03**: User can reset skill-tree progress (mirrors the existing lesson-progress reset path).

### SURF — Skill-tree surface & celebration *(exact surface resolved in the UI phase, per Kaan)*
- [ ] **SURF-01**: User can view their skill tree from the Learn module — all ~6 skills, each bar's stage, current fill, and what remains to advance.
- [ ] **SURF-02**: Competent-stage fills render with a quiet, satisfying progression cue — no slop, no spam, no constant celebration.
- [ ] **SURF-03**: A live "Mastered" unlock triggers a single, rare, earned grounded co-host vocal acknowledgment, tone-gated against the anti-slop blocklist (final tone subject to KAAN-ACTION ear-pass).
- [ ] **SURF-04**: The skill-tree surface honors v9.0 accessibility (dual color+shape cue, keyboard-nav, no time-pressure on advancement).

---

## Future Requirements (deferred — not this milestone)

- Per-skill sub-skills / finer-grained competency breakdown.
- Intermediate / Pro skill-tree branches (depend on the deferred Intermediate/Pro courses).
- Skill-tree state feeding the live co-host's persona/lens (a "you've mastered EQ swaps" prior) — possible v11.x once the tree is proven.
- Exportable / shareable skill cards → Bravoh.

---

## Out of Scope (explicit exclusions, with reasoning)

- **Streaks / leaderboards / cohort / social / shared progress** — deferred to Bravoh per the v9.0 defer list; v11.0 is single-user local only.
- **Cross-device progress sync** — Bravoh (CLAUDE.md platform constraint).
- **New AI provider / model** — Gemini Flash (live) + local Codex (Viber) unchanged; the grounded vocal reuses the existing co-host path.
- **New ws port / new IPC envelope family** — skill-tree state rides the existing `learn.*` envelopes on `127.0.0.1:8765` (Invariant #4); any `messages.schema.json` edit runs `npm run codegen:ipc`.
- **New heavy dependency** — engine is pure-Python on existing primitives.
- **New lesson content** — skills map onto the existing 36 hand-authored lessons; zero new transcripts.
- **New live event detectors** — Mastered grounding reuses the existing event taxonomy only.
- **Writing to `profile.json`** — privacy contract is 5 named fields, `additionalProperties:false`; skill data lives in `learn-progress.json`.

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| _(filled by roadmap)_ | | |
