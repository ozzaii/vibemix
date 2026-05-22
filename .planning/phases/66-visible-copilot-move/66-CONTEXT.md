# Phase 66: Visible Copilot Move - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning
**Mode:** Smart-discuss (autonomous mode, grey area recommendations auto-accepted; Kaan-ear veto rides forward to KAAN-ACTION)

<domain>
## Phase Boundary

Phase 66 ships the **visible, end-user-noticeable copilot moves** that prove the v6.0 retrieval seam (Phase 65) is firing — the felt "it remembers me" proof. Two specific moves:

1. **Transition-shape callback** ("last time you ran this blend you killed the bass two bars earlier") — an in-bar recall reaction that compares the DJ's current move to a registered past moment.
2. **Vocabulary/register callback** — the coach reuses phrasing/moves the DJ has made before, cited and warm.

Both must:
- Resolve to a **real registered** `[recall:<id>]` past moment — a fabricated callback strips the whole turn (anti-poisoning gate inherited from Phase 65 is the hard floor).
- Surface a **recall chip on the existing** `SessionCohostReaction.citation_strip` — no new socket, no new port; rides the existing `ipc.session.cohost-reaction` envelope (per ROADMAP §UI hint).
- Be **rare-and-earned** — long cooldowns, single-recall-per-turn cap, never nagging.
- Carry **no anti-features** — no next-track recommendation, no LLM-extracted "tendencies" presented as fact, no settings-screen personalization, no continuous audio embedding (enforced by static gate / review).
- Pass Kaan's ear (KAAN-ACTION carry-forward — engineering ships regardless, like the harmonic-clash veto in Phase 60).

**Boundary line:** this phase is the *prompt surface + chip wire-up* on top of the Phase 65 seam. It does NOT change retrieval scoring, the embedding pipeline, the ingest path, or the recall registration handshake — those are locked from Phase 65 (which closed all 4 BLOCKER findings on the anti-slop release gate). It also does NOT touch the live-relevance veto flip — `VIBEMIX_RECALL_ENABLED` stays default OFF in engineering; Kaan flips it on his real corpus.

</domain>

<decisions>
## Implementation Decisions

### Area 1: Coach Move Triggers (when each callback fires)

**Q1: What events gate the transition-shape callback?**
→ **TRACK_CHANGE, MIX_MOVE, LAYER_ARRIVAL** — the same `RECALL_EVENT_GATE` set Phase 65 uses (TRACK_CHANGE, PHASE, LAYER_ARRIVAL) PLUS MIX_MOVE for transition-specific callbacks. NEVER HEARTBEAT (Phase 65 invariant). Rationale: a transition-shape comparison only makes sense at events where the DJ is *doing* a transition.

**Q2: What events gate the vocabulary callback?**
→ **PHASE, TRACK_CHANGE** — phrasing reuse is a *narrative* move, not a transition move; fires at moments where the coach would naturally make a stylistic remark. Reuses the v5.0 PHASE event gate from `coach_persona` (consistent with the actionable-not-hype discipline).

**Q3: What is the rare-and-earned cooldown?**
→ **≥120s between any two recall callbacks, max 1 recall per turn.** Mirrors Phase 65 RESEARCH.md cooldown intuition + v5.0 cooldown discipline. Two recall moves in a single set are the ceiling — not a floor. (Phase 65 emitted RECALL_DEADLINE_S=0.5 budget on the off-loop path; the cooldown is at the higher coach-decision tier.)

**Q4: Does an empty-survivor turn ever produce a callback?**
→ **No.** If `recall_moments == []` after the deadline + floor, the coach prompt sees no `recall[…]` block (Phase 65 byte-identity invariant) — no past-tense ground means no past-tense callback. This is the structural guarantee.

### Area 2: Anti-Slop / Anti-Feature Guards

**Q1: How is "fabricated callback strips the turn" enforced?**
→ **Phase 65's existing linter gate carries forward.** The poisoning test (`test_fabricated_recall_strips_turn` + cross-turn `test_fabricated_recall_strips_turn_n_plus_1_with_empty_recall`) already covers the BL case: a `[recall:<unregistered_id>]` token strips the whole turn. Phase 66 adds tests that the *coach prompt-engineering* doesn't accidentally produce ungrounded callbacks (e.g., the prompt never instructs Gemini to "make up a past moment if you don't have one").

**Q2: How are anti-features prevented from creeping in?**
→ **Static repo-scrub test in `tests/repo/`** mirroring Phase 65's `no-live-path`/`no-extraction` gates. Search the prompt matrix + coach persona files for forbidden patterns:
- No "tendency" / "you always" / "you usually" phrases (LLM-extracted personality claims)
- No "next track" / "you should play" phrases (recommendation surface)
- No new settings-screen entry points (file gate on `src/vibemix/settings/` or equivalent — Phase 65 already keeps memory out of settings)
- No continuous audio embedding (Phase 65 INGEST is batch/post-session only — already guarded)

**Q3: What enforces "warm and non-nagging" tone?**
→ **Reuse v5.0 `coach_persona` discipline + actionable-not-hype tests** (Phase 61). The recall callbacks plug into the same persona — the cooldown + cap prevent nagging; the persona prevents hype. No new tone-validator needed.

**Q4: Is there a "your DJ history is being remembered" disclosure surface?**
→ **No new surface.** The recall chip on `citation_strip` is the disclosure — the user *sees* the chip when a callback fires. If Kaan's ear-pass wants more (e.g., a settings toggle to disable recall), that's a follow-up phase; do NOT pre-build it.

### Area 3: Citation Strip Recall Chip (Tier-1 visible surface)

**Q1: How does `recall` get added to the chip allow-list?**
→ **Add `"recall"` to the source allow-list in `_build_citation_strip` at `src/vibemix/agent/dj_cohost.py:215`.** Currently `("ev", "mix", "midi", "key")`; becomes `("ev", "mix", "midi", "key", "recall")`. (Phase 65 deliberately deferred this — the comment at `dj_cohost.py:215` already calls it out: "do NOT add `recall`… the recall chip is Phase 66".)

**Q2: What verb does the recall chip carry?**
→ **Fixed verb `"recall"` — single token, letters-only.** Mirrors the `key` precedent (Phase 59) where the verb is a fixed `"key"` label (not derived from the body). Rationale: the recall payload (`record_id`) is opaque; deriving a verb from it would leak embedding internals to the UI. Fixed `"recall"` is honest and clean.

**Q3: What timestamp does the chip render?**
→ **The current session's reaction timestamp** (when the callback *fired*), NOT the past moment's original timestamp. The chip surface is "the coach made a recall move just now"; the past moment is the *evidence*, not the visible event. (Phase 65 registration uses `t` = current turn's snapshot time; reuse that.)

**Q4: Does the chip render even when LLM emits no `[recall:<id>]` token?**
→ **No.** The chip is gated on the linter SEEING a `[recall:<id>]` in the reaction. If the coach decides not to use the past moment, no chip — same discipline as every other source. (`citation_strip` is observation, not advertisement.)

### Area 4: Kaan-Ear Release Gate

**Q1: Does Phase 66 ship with `VIBEMIX_RECALL_ENABLED=0` (Phase 65 default)?**
→ **Yes.** Phase 66 ships the engineering — code, tests, chip — and the env var stays default OFF. Kaan flips it on his real corpus. (Same pattern as Phase 60 harmonic veto, which Phase 65 already inherits.)

**Q2: What is the KAAN-ACTION discharge surface?**
→ **`KAAN-ACTION-LEGAL.md` (or equivalent project file) gets a v6.0 §RECALL-EAR entry** — "Flip `VIBEMIX_RECALL_ENABLED=1` after live-set listen confirms transition + vocabulary callbacks land grounded (not scripted, not nagging, not hallucinated)". Plus the `66-HUMAN-UAT.md` file gets the per-callback ear-test items.

**Q3: Does engineering-green close Phase 66?**
→ **Yes** — autonomous-`fully` mode. Engineering passes verification + code-review when the gates above are green. Kaan-ear is carry-forward, not a release blocker on the engineering side. (Project mode: `gsd-autonomous fully`; only privacy + destructive + legal-capacity carveouts still pause.)

### Claude's Discretion

- **Exact prompt wording** for the transition-shape callback and vocabulary callback templates — research-phase will surface 2-3 candidate prompt fragments; planner picks one, executor implements, Kaan's ear can iterate post-engineering-green.
- **Number of recall examples surfaced in the prompt** — Phase 65 top-k is 2-3 with floor ~0.7; whether Phase 66 lets the coach see all surviving moments or just the strongest is a prompt-engineering question for research.
- **Whether the vocabulary callback needs its own retrieval query vs. reusing transition-shape survivors** — research-phase should answer; Phase 65's `MemoryRecall.on_event(query_text)` is generic.
- **Chip visual treatment** — the `frontend-enforcement` skill governs CDJ-Whisper material/typography; UI-SPEC if needed (see `gsd-ui-phase` chain below).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (from Phase 65)

- **`src/vibemix/memory/retrieval.py::MemoryRecall`** — the retrieval enrichment service. `on_event(event_type, query_text, current_session_id)` is generic; Phase 66 reuses it as-is (no new retrieval seam).
- **`src/vibemix/agent/dj_cohost.py::DJCoHostAgent`** — already threads `recall_moments` into `build_prompt` and registers survivors via `_registry.write("recall", record_id, t)` BEFORE the LLM snapshot. The clear-after-turn (`_recall.clear()`) discipline is already in place. Phase 66 hooks into the same wire.
- **`src/vibemix/state/coach.py::evidence_line`** — already emits the gated PAST-tense `recall[…]` block (RECALL-02). Phase 66 does NOT change `evidence_line`; it changes the *coach persona* prompt fragments that USE the block.
- **`src/vibemix/state/evidence_registry.py::EvidenceRegistry`** — `clear_source("recall")` is the per-turn rescope mechanism (added in Phase 65 fix iter-3). Phase 66 inherits this — no new registry surface.
- **`src/vibemix/ui_bus/messages.py::SessionCohostReaction` + `CitationChipPayload`** — the wire format is fixed. Adding `recall` to the allow-list is a single-character source-set edit; the chip flows through the existing envelope.

### Established Patterns

- **Verb pattern (`key` precedent at `_build_citation_strip:230`)** — when the body is opaque/structured (not a free verb-like KEY), the chip uses a fixed lowercase letters-only verb. `recall` follows the same shape.
- **Source allow-list at `_build_citation_strip:215`** — gate is a single `if source not in (...)` check; this is the exact site Phase 65 told the comment to skip. Adding `recall` requires the matching test update.
- **Linter discipline (existence-only)** — `recall` is in `EVIDENCE_SOURCES` and absent from `_TIME_KEYED_SOURCES` (Phase 65 65-02). The linter ALREADY validates `[recall:<id>]` exists in the registry. Phase 66 does NOT add new linter code — same "schema-mirror, zero new linter logic" precedent.
- **v5.0 coach persona (`coach_persona` in `state/coach.py`)** — actionable-not-hype tone + cooldown/pacing. Phase 66 adds two callback templates that plug into the same persona — same tests, same cooldown wiring.
- **KAAN-ACTION carry-forward (Phase 60 harmonic veto, Phase 65 recall flag)** — default OFF, ship engineering, Kaan-ear discharge to the LEGAL/UAT files. Phase 66 follows the same pattern.

### Integration Points

- **Coach prompt assembly** — `src/vibemix/state/coach.py::build_prompt` (or `coach_persona` siblings). Add the two callback templates that:
  - Gate on event type (transition vs phase) + non-empty `recall_moments`
  - Wrap survivor evidence in the existing PAST-tense fence (already there from Phase 65)
  - Emit guidance like "if a survivor matches what's happening NOW, you may call back with one warm line using `[recall:<id>]`"
- **Citation chip wire** — `src/vibemix/agent/dj_cohost.py::_build_citation_strip:215` (source allow-list) + `:230` (verb derivation). Add `recall` to the allow-list and the fixed-verb branch (mirroring the `key` precedent at `:236`).
- **Repo-scrub static gate** — `tests/repo/` (existing static gates for Phase 65 live in this dir). Add a Phase 66 test that grep-scans coach persona files for forbidden phrases (tendencies, recommendations, settings personalization).
- **HUMAN-UAT** — `66-HUMAN-UAT.md` for Kaan-ear items; cross-listed in `KAAN-ACTION-LEGAL.md §RECALL-EAR`.

### Canonical Refs (MANDATORY — downstream agents MUST read)

- `.planning/ROADMAP.md` — Phase 66 §Visible Copilot Move (4 success criteria, UI hint)
- `.planning/REQUIREMENTS.md` — COPILOT-01..03
- `.planning/PROJECT.md` — v6.0 thesis + anti-slop principles + "no LLM-extracted tendencies" non-negotiable
- `.planning/phases/65-memory-retrieval-seam/65-CONTEXT.md` — Phase 65 decisions (anti-poisoning grammar, registration discipline, KAAN-ACTION pattern)
- `.planning/phases/65-memory-retrieval-seam/65-RESEARCH.md` — retrieval seam research (cooldown intuition, blend, top-k floor)
- `.planning/phases/65-memory-retrieval-seam/65-VERIFICATION.md` — 14/14 must-haves verified (the floor Phase 66 stands on)
- `.planning/phases/65-memory-retrieval-seam/65-REVIEW.md` + `65-REVIEW-FIX.md` — code-review hardening (anti-poisoning gate + cross-turn fix)
- `src/vibemix/memory/retrieval.py` — `MemoryRecall` service (consumed unchanged)
- `src/vibemix/agent/dj_cohost.py:148-260` — `_build_citation_strip` (source allow-list edit site)
- `src/vibemix/state/coach.py::build_prompt + evidence_line` — coach persona seam
- `src/vibemix/state/evidence_registry.py::clear_source` — per-turn rescope mechanism
- `src/vibemix/ui_bus/messages.py::SessionCohostReaction + CitationChipPayload` — wire format
- `.claude/skills/frontend-enforcement/SKILL.md` — CDJ-Whisper visual discipline (governs chip styling if UI-SPEC is generated)
- `mocks/vibemix-app-ui.html` + `mocks/vibemix-cinematic-storyboard.html` — Tier-1 live-session UI reference

</code_context>

<specifics>
## Specific Ideas

- The headline transition-shape callback example from the ROADMAP — "last time you ran this blend you killed the bass two bars earlier" — is the canonical shape the planner should design toward. Two-clause form: comparison anchor ("last time you ran this blend") + concrete delta ("you killed the bass two bars earlier"). Warm, specific, in-bar.
- The vocabulary callback should *quote the DJ's own past phrasing/move* — not a Gemini paraphrase. Phase 64 INGEST already captures `ai_text` and citation_strip-silenced lines; the survivors carry signature text the coach can echo back.
- "Felt 'it remembers me' proof" is the success bar. If two real sessions yield zero callbacks because cooldowns/floors are too tight, that's a tuning problem (KAAN-ACTION ear pass), NOT a code change.

</specifics>

<deferred>
## Deferred Ideas

- **Recall-history settings screen** — explicit user-facing surface to inspect/delete past moments. Out of scope (would be a settings personalization anti-feature for v6.0). Note for post-v6.0 if Kaan's ear demands transparency.
- **Cross-session "you tend to" summarizer** — explicit LLM-extracted tendency surface. Permanently out of scope per v6.0 anti-features lock (PROJECT.md §v6.0 thesis: "personalization is emergent from the retrieval seam, NOT an LLM-extraction layer").
- **Next-track recommendation** — out of scope per the same anti-feature lock.
- **Mascot recall reaction** (mascot mood/animation reflecting a callback) — could be a v6.1+ touch, but Phase 62 demoted the mascot to opt-in/secondary; the pill is the primary surface. Defer unless Kaan asks.
- **Multi-modal recall** (image/audio callback in addition to text) — out of scope for v6.0; Gemini Embedding 2's multimodal capability is reserved for v7+.

</deferred>
