---
phase: 61-actionable-not-hype-coach-persona
verified: 2026-05-21T22:10:00Z
status: human_needed
score: 4/4 must-haves verified (engineering) — 2 carry an inherent live-ear human gate
overrides_applied: 0
re_verification:
  previous_status: none
  note: "Initial verification — no prior VERIFICATION.md existed."
human_verification:
  - test: "Run a real DJ session in coach mode (any/all skill levels) and listen to ~10-20 coach turns through headphones."
    expected: "Roughly half the turns are fresh positive callouts (props/credit), not nothing-but-faults. Notes are prescriptive (observed → impact → prescribe with a real DJ verb), NOT narration/cheerleading. Tone stays warm 'friend in your ear', not robotic/cold. Cooldown/pacing means it does not nag (no constant stream of corrections)."
    why_human: "COACH-01 success criterion explicitly says 'verifiable on a real session trace'; the warm-not-cold / fresh-positive-callout-balance / non-nagging qualities are perceptual ear-judgments the executor flagged. Code/tests prove the prompt CARRIES the contract; only a live ear can confirm the model's actual delivery lands."
  - test: "During the same live session, watch for the lifted EQ/control-naming ban (REVIEW WR-01). Confirm coach mode does not invent a specific EQ-band / physical control move (e.g. 'you killed the deck-B lows') that the recent_moves[8s] evidence did not actually supply."
    expected: "Any control-naming the coach does is tied to a move the evidence packet actually carried; the model does not fabricate a specific fader/EQ-band action. (Bare prose control claims are NOT caught by the [key:]/[ev:] CitationLinter — only emitted citation atoms are linted.)"
    why_human: "The MIX_MOVE clause + COACH_CLOSING_BLOCK deliberately lift the old hard ban on naming faders/EQ/knobs (Kaan-directed product decision). The CitationLinter only validates bracketed atoms, so a bare prose control claim is not structurally caught. This is the hallucination-gate concern flagged in REVIEW WR-01 and must clear on the live ear-pass."
---

# Phase 61: Actionable-Not-Hype Coach Persona Verification Report

**Phase Goal:** The feedback (coach) voice becomes a real DJ mentor — concrete, prescriptive notes a DJ can act on (observed → impact → prescribe, real DJ verbs: kill/swap/cut/filter/wait/tighten/ride), wired to the deck-state + harmonic events, while staying warm, cited, and never nagging. It EXTENDS the in-flight `live-tuning-or-brain` work — no new mode — and cannot silently break or cold-ify the validated hype voice.
**Verified:** 2026-05-21T22:10:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (Success Criterion) | Status | Evidence |
| --- | --- | --- | --- |
| 1 (COACH-01) | Coach mode delivers concrete prescriptive DJ notes (observed→impact→prescribe, real DJ verbs) instead of narration/cheerleading | ✓ VERIFIED (engineering) — live-ear gate deferred to human | All 7 canonical DJ verbs (`kill/swap/cut/filter/wait/tighten/ride`) present DIRECTLY in each of `COACH_BEGINNER`/`COACH_INTERMEDIATE`/`COACH_PRO` cell constants (not just the assembled substrate). `OBSERVED → IMPACT → PRESCRIBE` + same-line/same-breath prescribe-clause in all three cells (matrix.py:437,482, PRO:517-518 via DESERVED-CRITIQUE+FIX). 12/12 `test_prompt_61_coach_*` asserts GREEN (verb vocab + prescribe same-line + positive-callout balance + calm-tag routing × 3 skills). COACH-01 SC also says "verifiable on a real session trace" → live-ear item (human #1). |
| 2 (COACH-02) | Refactor EXTENDS the COACH cells + task_for_event — NO new mode (`_VALID_MODES=={"hype","coach"}`), flows through BOTH genai and OpenRouter paths | ✓ VERIFIED | `_VALID_MODES = frozenset({"hype","coach"})` unchanged (matrix.py:694; invalid mode raises, dispatch tests 07/08). Single `prompt_body` (dj_cohost.py:366) feeds genai path `_gen_cfg.system_instruction=prompt_body` (:447) AND OpenRouter `stream_or(system_instruction=self._prompt_body)` (:816) — same object, no path-specific persona code. `test_dispatch_61_coach_prompt_body_feeds_both_paths` builds a real coach-mode agent and asserts `agent._gen_cfg.system_instruction == agent._prompt_body` (genuine equality, not a tautology) — GREEN. Edit is cell-prose only (`+ _ANTI_SLOP_FOOTER` / `{mood_persona}` grammar intact). |
| 3 (COACH-03) | Hype mode is regression-fenced with goldens — Phase-54 hype voice byte-stable; no hype golden changed | ✓ VERIFIED | Phase-61 commits (`1e35bea`..HEAD) touched ZERO `HYPE` lines in matrix.py (git diff confirmed). 40/40 hype/persona/anchor/byte tests GREEN (`HYPE_INTERMEDIATE` byte-identity, persona `SYSTEM_INSTRUCTION` byte-identical, all hype anchors stable). Coach `ANCHOR_PHRASES` updated in-lockstep with cell edits in the same commit (`f35e9bc`) — deliberate, Phase-61-noted, hype frozen. |
| 4 (COACH-04) | Every prescriptive note stays anti-slop/cited — ties to observed deck/event, warm tone preserved, harmonic fragments injected only when the tier supplies them (fabricated key strips whole turn) | ✓ VERIFIED (engineering) — warm-tone live-ear gate deferred to human | `test_coach_grounding_61_fabricated_key_strips`: a fabricated `[key:A:12B]` against a snapshot that observed no key → existence-only `CitationLinter` strips the WHOLE turn (`valid is False`, `("key","A:12B") in result.missing`, `reason=="invalid_atoms"`). Linter NOT modified. Positive-callout BALANCE marker present in all three cells (BEGINNER `ENCOURAGING`, INTERMEDIATE `POSITIVE-CALLOUT BALANCE`/`credit it`, PRO `PROPS`). Harmonic grounded-only: `coach.py` KEY_CLASH/TRANSITION arms hand pre-decided keys + pre-computed semitone count, "Do NOT invent a key", "Do NOT compute intervals", PAST-TENSE-only for transitions — fragment injected only when the event fires + decks resolved (coach.py:267-316). Warm-not-cold / non-nagging delivery → live-ear item (human #1). |

**Score:** 4/4 truths verified at the engineering layer (prompt contract + dual-path wiring + hype fence + structural anti-slop all proven in code/tests). Two of the four (COACH-01, COACH-04) carry an inherent live-ear human gate the executor honestly flagged — see Human Verification.

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `src/vibemix/prompts/matrix.py` | Sharpened COACH_BEGINNER/INTERMEDIATE/PRO cells (verbs + prescribe-clause + balance + beginner impact + beginner harmonic path) | ✓ VERIFIED | `DJ-VERB REGISTER`, `OBSERVED → IMPACT → PRESCRIBE`, `POSITIVE-CALLOUT BALANCE`, `GENTLE HARMONIC PATH (grounded only)` all present (lines 437-441, 482-488, 517-529). All 7 verbs in each cell constant. ~38-line diff, COACH-cells only, no control-flow/dispatcher change. Wired: imported via `build_system_instruction` in dj_cohost.py:66,272. |
| `src/vibemix/state/coach.py` | KEY_CLASH / TRANSITION_OPPORTUNITY task_for_event arms (grounded harmonic voice) | ✓ VERIFIED | `task_for_event` arms at 267-316: both keys cited exactly, "confirmed by the system (you do NOT decide this)", DJ-verb move, "Do NOT invent a key", "Do NOT compute intervals", pre-computed semitones, PAST-TENSE transition framing. Phase-61 did NOT edit coach.py (it verb-aligned cell prose TO it) — arms are Phase-60-shipped and Phase-61-fenced GREEN. Wired into matrix `[ev:]`/`[key:]` grammar. |
| `tests/prompts/test_matrix.py` | 12 `test_prompt_61_coach_*` contract asserts + lockstep coach ANCHOR_PHRASES | ✓ VERIFIED | 12 asserts GREEN; beginner-coach `ANCHOR_PHRASES` updated with a Phase-61 comment. |
| `tests/state/test_coach.py` | KEY_CLASH + TRANSITION coach-voice fence | ✓ VERIFIED | `test_task_key_clash_*` + `test_task_transition_opportunity_*` GREEN. |
| `tests/agent/test_dj_cohost_matrix_dispatch.py` | Dual-path `_prompt_body` equality + no-new-mode invariant | ✓ VERIFIED | `test_dispatch_61_coach_prompt_body_feeds_both_paths` GREEN. |
| `tests/agent/test_coach_prompt_grounding.py` | Coach-context fabricated-key strip proof | ✓ VERIFIED | `test_coach_grounding_61_fabricated_key_strips` GREEN. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `matrix.py` COACH cells | dj_cohost.py `_prompt_body` / `_gen_cfg.system_instruction` | `build_system_instruction(skill,mode,mood)` → `prompt_body` (one object) | ✓ WIRED | dj_cohost.py:272,366,447 — single body. |
| dj_cohost.py `_prompt_body` | OpenRouter `stream_or` | `stream_or(system_instruction=self._prompt_body)` | ✓ WIRED | dj_cohost.py:813-816 — same body to OR path. |
| `matrix.py` COACH cells DJ-verb register | `coach.py` KEY_CLASH arm verbs | shared `kill/cut/filter/ride` register so a harmonic turn reads like a mix-move turn | ✓ WIRED | Verb-aligned; harmonic arm uses same verbs (coach.py:284). |
| `coach.py` harmonic fragment | response-level anti-slop | existence-only `CitationLinter` strips fabricated `[key:...]` | ✓ WIRED | Proven by fabricated-key-strip test. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| 61_coach contract asserts | `pytest -q tests/prompts/test_matrix.py -k 61_coach` | 12 passed, 79 deselected | ✓ PASS |
| Harmonic + dispatch dual-path | `pytest -q tests/state/test_coach.py -k "key_clash or transition" tests/agent/test_dj_cohost_matrix_dispatch.py -k "61 or key_clash or transition"` | 6 passed | ✓ PASS |
| Dual-path COACH-02 + fabricated-key strip (by name) | `pytest -v ...test_dispatch_61_coach_prompt_body_feeds_both_paths ...test_coach_grounding_61_fabricated_key_strips` | 2 passed | ✓ PASS |
| Hype golden / persona byte-identity fence | `pytest -q tests/agent/test_persona.py tests/agent/test_hype_prompt_grounding.py tests/prompts/test_matrix.py -k "hype or persona or anchor or byte"` | 40 passed | ✓ PASS |
| All 7 DJ verbs in each cell CONSTANT (not assembled) | python token-set check on `COACH_BEGINNER/INTERMEDIATE/PRO` | all 7 present in all 3 cells | ✓ PASS |
| Full suite baseline invariant | `pytest -q` (full) | **7 failed, 4085 passed, 26 skipped** | ✓ PASS (matches documented WIP baseline) |

### Probe Execution

Not applicable — Phase 61 is a prompt-template + test-fence phase, not a migration/CLI/tooling phase. No `scripts/*/tests/probe-*.sh` declared in PLAN/SUMMARY. (Verification ran the pytest contract suite instead, which is the authoritative gate per `61-VALIDATION.md`.)

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| COACH-01 | 61-01, 61-02 | Coach delivers concrete prescriptive DJ notes (observed→impact→prescribe, real verbs) not narration | ✓ SATISFIED (engineering) — live-ear gate human #1 | 12 contract asserts GREEN; verbs + prescribe-clause in all cells. SC "verifiable on a real session trace" → human. |
| COACH-02 | 61-01 | Extends COACH cells + task_for_event, no new mode, flows through both genai + OpenRouter paths | ✓ SATISFIED | Dual-path equality test GREEN; `_VALID_MODES=={"hype","coach"}`. (Note: REQUIREMENTS.md still marks COACH-02 "Pending"/`[ ]` — a docs-sync artifact the orchestrator owns; the CODE/TEST evidence fully satisfies it.) |
| COACH-03 | 61-02 | Hype regression-fenced with goldens | ✓ SATISFIED | 40 hype/persona/byte tests GREEN; zero HYPE lines touched. |
| COACH-04 | 61-01, 61-02 | Every prescriptive note anti-slop/cited; warm; non-nagging | ✓ SATISFIED (engineering) — warm/non-nag live-ear gate human #1 | Fabricated-key strip GREEN; balance markers in all cells; harmonic grounded-only arms. |

No ORPHANED requirements — all four COACH IDs are claimed across the two plans (`requirements:` frontmatter).

### Data-Flow Trace (Level 4)

Not applicable in the rendering sense — this phase produces prompt-template prose + grounding fences, not a dynamic-data UI artifact. The data-flow that IS load-bearing (harmonic fragment → coach prompt → linter strip) is covered under Key Link Verification and is GREEN: the harmonic arm only emits a fragment when the event fires with resolved+cited decks, and any uncited `[key:...]` strips the whole turn.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| (none) | — | No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER in `matrix.py` or `coach.py` | — | Clean. Working tree clean (all Phase-61 work committed). No stubs. |

REVIEW.md observations (carried forward, none blocking):
- **WR-01** (warning) — coach prose lifts the EQ/control-naming ban; bare prose control claims are not caught by the CitationLinter (it lints only bracketed atoms). This is a Kaan-directed product decision, NOT a code bug. Routed to the live-ear hallucination gate as human verification item #2.
- **WR-02 / IN-01 / IN-02 / IN-03** (warning/info) — test-fence robustness/wording observations (broad balance-marker list, literal-substring couplings, assembled-vs-cell tokenization, "byte-pinned" overstatement in a comment). I independently re-verified the cells genuinely carry the intended markers in the cell CONSTANTS (all 7 verbs, balance markers, prescribe-clause), so the contracts hold today. These are fence-strictness suggestions, not gaps.

### Human Verification Required

#### 1. Live coach-mode ear-pass (Kaan's DJ ear — post-merge phase gate)

**Test:** Run a real DJ session in coach mode (across skill levels) and listen to ~10-20 coach turns through headphones.
**Expected:** ~half the turns are fresh positive callouts (props/credit), not nothing-but-faults; notes are prescriptive (observed → impact → prescribe + a real DJ verb), not narration/cheerleading; tone stays warm "friend in your ear", not robotic/cold; pacing means it does not nag.
**Why human:** COACH-01 SC explicitly requires "verifiable on a real session trace"; warm-not-cold, fresh-positive-balance, and non-nagging are perceptual ear-judgments. Code/tests prove the prompt CARRIES the contract; only the live ear confirms the model's actual delivery lands. (Aligns with MEMORY: "Phase 16 = Kaan's DJ ear, not formal suite".)

#### 2. Lifted EQ/control-naming ban — hallucination-gate check (REVIEW WR-01)

**Test:** During the same live session, confirm coach mode does not invent a specific EQ-band/physical control move (e.g. "you killed the deck-B lows") that `recent_moves[8s]` did not actually supply.
**Expected:** Any control-naming is tied to a move the evidence packet carried; no fabricated fader/EQ action.
**Why human:** The MIX_MOVE clause + `COACH_CLOSING_BLOCK` deliberately lifted the hard ban; the `CitationLinter` validates only bracketed atoms, so a bare prose control claim is not structurally caught. Must clear on the live ear-pass before the hard hallucination gate.

### Gaps Summary

No engineering gaps. All four success criteria are proven at the code/test layer: the COACH cells carry the full actionable-not-hype contract (all 7 DJ verbs in each cell constant, observed→impact→prescribe + same-line prescribe-clause, positive-callout balance) with 12/12 contract asserts GREEN; the dual-path COACH-02 wiring is a genuine same-object equality (genai `_gen_cfg.system_instruction` AND OpenRouter `stream_or` both consume the one `prompt_body`) with no new mode (`_VALID_MODES=={"hype","coach"}`); the hype voice is byte-frozen (zero HYPE lines touched, 40 byte-identity/persona tests GREEN); and the anti-slop guarantee is structural (fabricated `[key:...]` strips the whole turn via the unmodified existence-only CitationLinter, harmonic fragments injected only when the grounded event fires). Full suite is at the documented WIP baseline (7 failed / 4085 passed / 26 skipped) — the 7 failures are pre-existing `live-tuning-or-brain` items (anti-slop-wiring, cut_release tag/preflight, readme-feature-matrix ×2, main-smoke) that do NOT touch coach/matrix/prompt/harmonic; the readme-matrix failures are about phases 55-60 doc-sync + COACH-02 still flagged Pending in REQUIREMENTS.md (an orchestrator-owned docs artifact), not a Phase-61 code regression.

Status is `human_needed` (not `passed`) because COACH-01 and COACH-04 carry an inherent live-ear component the executor honestly flagged — the "real session trace" / warm-not-cold / non-nagging delivery and the lifted-control-naming hallucination-gate check are perceptual judgments only Kaan's DJ ear can make. The engineering scope is complete and green; the phase awaits the live ear-pass.

---

_Verified: 2026-05-21T22:10:00Z_
_Verifier: Claude (gsd-verifier)_
