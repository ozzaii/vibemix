# Phase 17: Reaction-Reel Slop Grading Gate - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous fully — recommended answers locked; no user pause)

<domain>
## Phase Boundary

Phase 17 is the **existential pre-release slop gate** — does vibemix's AI sound
like "a real DJ friend in your ear" or like AI slop? It is fundamentally a
**human-evaluation phase**, not a code phase. The autonomous deliverable is the
**evaluation harness**: tooling, rubric, capture protocol, and scoring archive
format. The actual grading (4 raters × 30-min reel × N reactions) is performed
off-loop by humans.

This phase delivers, in the repo, all the artifacts needed so that on the day
the reel is captured, the grading takes <30 minutes per rater with zero
ambiguity about what's being graded, on what scale, with what evidence.

Out of scope: actually capturing the reel (requires shipped binary + Kaan
running a live set). Phase 17 builds the bench; the user runs the experiment.

</domain>

<decisions>
## Implementation Decisions

### Area 1 — Grading Rubric (Success Criterion #4)
- One canonical document: `.planning/phases/17-reaction-reel-slop-grading-gate/17-RUBRIC.md`.
- 1-5 scale per reaction with concrete anchor descriptions per score:
  - **5 — "Real friend in my ear":** reaction is timely, grounded in audible/visible evidence, doesn't repeat itself, has personality consistent with persona (hype/coach), would survive a clip on Kaan's IG story.
  - **4 — Solid:** grounded, mostly timely, no slop, minor flavor issue (e.g. slightly generic phrasing) but a DJ wouldn't object.
  - **3 — Neutral:** correct but forgettable. No slop, no spark. The "voice assistant doing music commentary" failure mode is here.
  - **2 — Slop:** generic AI phrasing ("Wow, the energy in the room is electric!"), late by >4s, repeats prior reaction, hallucinates an event that didn't happen, or fakes hype on a transition that wasn't a drop. Single 2 = phase fails.
  - **1 — Embarrassing:** would make the DJ tear off their headphones. Cringe, condescending, breaks the fourth wall, or shows confusion about basic facts (wrong genre, wrong section). Single 1 = phase fails.
- Per-reaction grade fields (locked schema for the scoring tool):
  - `reaction_id` (string), `score` (1–5), `rater` (kaan/francesco/dj1/dj2),
    `grounded` (bool), `timely` (bool), `unique` (bool), `personality_fit` (bool),
    `slop_flag` (enum: none / late / generic / hallucination / repetition / cringe),
    `comment` (free text), `would_clip` (bool).
- Pass thresholds (verbatim from ROADMAP success criterion #3):
  - **Average ≥4.0 across all reactions × all raters.**
  - **Zero 1-2 ratings from any rater on any reaction.**
- Tie-breaker for borderline ≥4.0: if average == 4.00 ± 0.05 AND any 3-score
  appears in >25% of reactions, escalate to Kaan for "ship vs. one more
  Phase 10 cycle" decision.

### Area 2 — Reel Capture Protocol (Success Criterion #1)
- Document: `.planning/phases/17-reaction-reel-slop-grading-gate/17-CAPTURE-PROTOCOL.md`.
- 30 min total reel, structured as **5 × 6-minute segments** — one per genre:
  - techno / house / drum&bass / disco / pop.
- Each 6-min segment further splits 3 + 3 min:
  - First 3: **Hype-man** mode + skill level rotates (segment 1+3 = Intermediate, 2 = Beginner, 4+5 = Pro).
  - Last 3: **Coach** mode at the same skill level as that segment's hype-man.
- Across the 5 segments: **5 genres + 2 modes + 3 skill levels** all represented. (Beginner: 1 segment, Intermediate: 2, Pro: 2.)
- Recording medium: vibemix's own `recordings/` output (delivered in Phase 15) + a screen+audio recording of djay Pro via QuickTime so raters see the same context the AI saw.
- Reaction extraction: a script reads `events.jsonl` for `kind=="ai_text"` events, extracts each reaction + the surrounding ±15s context (music RMS + screen JPEG paths + MIDI events in window), assembles a per-reaction clip-card. ≥40 reactions expected over 30 min based on POC observation in Plan 15-02 deferred-items.

### Area 3 — Blind-Grading Tooling (Success Criterion #2)
- One CLI script: `scripts/reaction_reel/grade.py`.
  - Inputs: a `recordings/<session>/` dir + a rater name.
  - Behavior: walks reactions in shuffled order (deterministic per rater via seed
    so re-runs land in same order if abandoned mid-way), strips any persona/mode/genre/skill
    metadata from the on-screen UI, plays voice.wav for that reaction
    + shows context clip + waits for the rater to enter score+flags via terminal prompts.
  - Writes `recordings/<session>/grades/<rater>.jsonl` incrementally — resumable.
  - Anonymization: reaction filename is `<sha8>.wav`; the mapping is in a
    `grades.key.json` only the analyzer (Kaan post-grading) sees.
- Optional UI variant DEFERRED — terminal script is enough for v1.
- A complementary `scripts/reaction_reel/analyze.py` script aggregates all `<rater>.jsonl`
  files into a single report:
  - `report.md` — overall average, per-rater average, per-genre average, per-mode
    average, distribution histogram, all 1-2 scores called out with rater+comment,
    pass/fail verdict against the rubric.
  - `scores.csv` — flat row per (reaction × rater) for external spreadsheet review.

### Area 4 — Iteration Loop (Success Criterion #3 — when gate fails)
- If gate fails (`avg < 4.0` or `any 1-2`): re-enter Phase 10 (prompt template
  matrix) with a max **3-cycle budget**. Each cycle:
  1. analyze.py report identifies the worst persona × genre × mode cells
  2. Phase 10 prompt-template revision targets those cells specifically
  3. Re-record a focused reel covering only the regressed cells (~10 min, not 30)
  4. Re-grade by Kaan + 1 friend only (other 2 raters preserved for the final
     30-min re-grade to keep blindness honest)
- After 3 failed cycles → escalation per ROADMAP: consider **scope-cut to
  Hype-man-only** (drop Coach from v1).
- Document the loop in `.planning/phases/17-.../17-ITERATION-LOOP.md` so Phase 10
  re-entry has a clear trigger condition.

### Area 5 — Human-Verification Anchors
- Phase 17 verification status will be `human_needed` on completion of the
  autonomous deliverables. The autonomous gate covers:
  - Rubric document exists with anchored score descriptions
  - Capture protocol document exists with the 5×6 minute matrix
  - `grade.py` exists, parses recordings, anonymizes, writes grades JSONL
  - `analyze.py` exists, aggregates scores, writes report.md + scores.csv
  - Iteration loop document exists
  - Integration test: synthetic recordings dir + synthetic grades → analyze.py
    produces a pass/fail verdict matching expected
- Human task (outside Phase 17 close): record the actual 30-min reel, run 4
  raters through `grade.py`, run `analyze.py`, verify gate passes. Result
  attached to phase as `17-GATE-RESULT.md` when complete.

### Claude's Discretion
- Exact prompt phrasing inside `grade.py` (terminal UX text)
- File layout details inside the recordings/<session>/grades/ subtree
- Anchor copy on rubric 1-2-3-4-5 (within the locked semantics above)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/vibemix/audio/recorder.py` writes events.jsonl with `kind=="ai_text"` records.
- `src/vibemix/runtime/recordings_index.py` walks the recordings dir + reads events.
- Phase 15's `tests/recording/test_poc_compat.py` shows the exact reader shape for
  WAV + JSONL invariants.
- Phase 12 confirmDialog, retention slider, settings drawer (not needed here).

### Established Patterns
- `scripts/` already contains Python utilities; new scripts land under
  `scripts/reaction_reel/`.
- pytest-based integration tests already cover Phase 15 recordings flow — use
  same pattern for the grade.py / analyze.py integration test.

### Integration Points
- No frontend changes — Phase 17 is CLI-only (raters use terminal during grading).
- No IPC changes — Phase 17 reads recordings produced by the shipped binary.

</code_context>

<specifics>
## Specific Ideas

- Slop dictionary for grade.py's "generic" flag: explicit list of phrases that
  count as slop ("Wow", "energy", "vibes", "the room is electric", "stunning",
  "let's go", "absolute fire"). Imported from Phase 10's anti-slop dictionary.
- Per-rater seed: SHA1(rater_name + session_dir)[:8] → deterministic shuffle order
  so a rater that quits mid-grading can resume without re-grading already-graded
  reactions.

</specifics>

<deferred>
## Deferred Ideas

- **GUI grading tool** — terminal script is enough for v1. GUI is post-launch.
- **Inter-rater agreement statistics (Cohen's kappa)** — interesting but not
  required to pass the gate. Push to a v2 reliability analysis.
- **Streaming the reel via web app for remote graders** — Francesco may not be
  in Istanbul; defer to v2. v1 = local-only grading session.
- **Auto-grading via LLM-as-judge** — Phase 16's hallucination scorer already
  does grounding evaluation. Phase 17 is explicitly *human* taste evaluation.
  Don't conflate.

</deferred>
