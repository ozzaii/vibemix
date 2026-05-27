---
phase: 79-lens-three-grounded-modes
verified: 2026-05-26T00:00:00Z
status: human_needed
score: 3/3 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Switch the co-host through hype / critique / tutor on a live or recorded set and listen to each lens"
    expected: "Each lens FEELS like a distinct grounded voice — hype = party energy, critique = says what to fix, tutor = teaches DJing from who-you-are + semantics + reality. None hallucinate; all stay tied to real detected events. The tutor lens in particular should actually TEACH, not just narrate."
    why_human: "Voice-fidelity / 'does the tutor teach well' is a subjective ear judgment. Per the phase charter this is the Phase-81 BENCH lens dimension + Kaan's ear (parked, KAAN-ACTION) — provably distinct prompts is automated (verified), but feel is not."
  - test: "Set the lens once (e.g. tutor) via the settings bus, then run BOTH the live co-host and a curator request in the same session"
    expected: "The single selection drives both surfaces' voice — choose tutor once, the co-host coaches in the teacher persona AND the curator builds the tutor voice, with no per-surface re-selection."
    why_human: "End-to-end cross-surface flow with a real Gemini key + live audio + a curator run cannot be exercised without an API key / live hardware. The shared-read seam is unit-verified; the full live round-trip is a human runtime check."
---

# Phase 79: LENS — Three Grounded Modes Verification Report

**Phase Goal:** Make hype/critique/tutor three real grounded lenses over the SAME structured state (not three brains), lens selection shared across co-host + curator, each lens still passing the citation-grounding gate.
**Verified:** 2026-05-26
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (Success Criterion) | Status | Evidence |
|---|---------------------------|--------|----------|
| 1 | hype/critique/tutor are three grounded prompt lenses over the SAME structured state — switching lens changes voice/intent, not the grounded facts (LENS-01) | ✓ VERIFIED | `matrix.py:911` `LENS_TO_MODE_MOOD = {hype→(hype,hype-man), critique→(coach,coach), tutor→(coach,teacher)}`; `build_lens_instruction` (matrix.py:925) validates+delegates to the UNTOUCHED `build_system_instruction`. Runtime spot-check: 3 distinct prompts, `build_lens_instruction("hype") == build_system_instruction("intermediate","hype")` byte-identical, `bogus` raises ValueError. v4 golden (`test_matrix.py`) stays green. |
| 2 | Lens selection is shared across co-host + curator — choosing "tutor" once flows to both (LENS-02) | ✓ VERIFIED | `read_shared_lens(store, default)` (settings.py:68) is the ONE read; `_apply_lens` (settings.py:474) persists `ConfigStore.extra["lens"]` only (no env, no schema). Co-host `_resolve_prompt_cell` (dj_cohost.py:341-353) reads it → `LENS_TO_MODE_MOOD` cell. Both curator seams (agent.py:106-149, codex_curate.py:90-113) read it, hardcoded "tutor" removed. Runtime spot-check: setting `extra["lens"]="critique"` returns "critique" to both surfaces; per-surface cold-path defaults (co-host→None/hype, curator→tutor) preserved. |
| 3 | Each lens still passes the citation-grounding gate — un-cited output strips regardless of lens (invariant #2) | ✓ VERIFIED | `CitationLinter.check` (citation_linter.py:94) takes only `registry_snapshot` + a `mode` arg (live/debrief tolerance band, NOT persona); it never reads the lens/prompt cell → lens-blind by construction. `test_lens.py::test_three_lenses_pass_the_same_gate` (now real-green) pins the strip decision identical across all three lenses for cited + un-cited cases. |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/vibemix/prompts/matrix.py` | `LENS_TO_MODE_MOOD` + `build_lens_instruction` over untouched builder | ✓ VERIFIED | Map at :911, wrapper at :925, drift-guard assert at :920. `build_system_instruction`/`_CELLS`/`MOOD_PERSONAS`/`_CURATOR_LENS_TO_MOOD` untouched. |
| `src/vibemix/runtime/settings.py` | `_apply_lens` + `_VALID_LENSES` + `read_shared_lens` + dispatch | ✓ VERIFIED | `_VALID_LENSES` :65, `read_shared_lens` :68, dispatch case :223, `_apply_lens` :474 (validate→persist extra→save_config; no env). |
| `src/vibemix/agent/dj_cohost.py` | `_resolve_prompt_cell` reads shared lens; cold path unchanged | ✓ VERIFIED | :341-353 lazy+guarded shared-lens read; explicit mood arg precedence preserved; cold path falls through to env/DEFAULT. |
| `src/vibemix/library/agent.py` | curator seam reads shared lens; cache invalidated on change | ✓ VERIFIED | `_shared_lens()` :106 (default "tutor"); both lazy seams lens-keyed (`_SYSTEM_INSTRUCTION_LENS`, `_INTERACTIVE_SYSTEM_INSTRUCTION_LENS`) rebuild on change. |
| `src/vibemix/library/codex_curate.py` | codex seam reads shared lens | ✓ VERIFIED | `_shared_lens()` :90 (default "tutor"); `_SYSTEM_PROMPT_LENS` :87 keyed cache invalidation. |
| `tests/prompts/test_lens.py` | LENS scaffolds + v4 anchor | ✓ VERIFIED | All LENS-01/02 scaffolds flipped to real-green; v4 anchor real-green; no xfail/xpass remaining. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `build_lens_instruction` | `build_system_instruction` | `LENS_TO_MODE_MOOD[lens]→(mode,mood)→delegate` | ✓ WIRED | matrix.py:965 `return build_system_instruction(skill, mode, mood, **kw)` |
| `_apply_lens` | `ConfigStore.extra["lens"]` | validate enum → persist → save_config | ✓ WIRED | settings.py:500-501 |
| `_resolve_prompt_cell` | `LENS_TO_MODE_MOOD` | shared lens read → (mode,mood) | ✓ WIRED | dj_cohost.py:346-353 |
| `library/agent.py::_system_instruction` | `ConfigStore.extra["lens"]` | `_shared_lens()` → `build_curator_instruction(lens)` | ✓ WIRED | agent.py:124-131 |
| `codex_curate.py::_system_prompt` | `ConfigStore.extra["lens"]` | `_shared_lens()` → `build_curator_instruction(lens)` | ✓ WIRED | codex_curate.py:107-112 |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Default hype byte-identical to co-host default | python build_lens_instruction("hype")==build_system_instruction("intermediate","hype") | True | ✓ PASS |
| Three lenses produce distinct prompts | len({hype,crit,tutor})==3 | True | ✓ PASS |
| Lens vocabulary shared co-host↔curator | set(LENS_TO_MODE_MOOD)==set(_CURATOR_LENS_TO_MOOD) | True | ✓ PASS |
| Unknown lens fails loud | build_lens_instruction("bogus") | ValueError | ✓ PASS |
| One selection flows to both surfaces | read_shared_lens(store,None)==read_shared_lens(store,"tutor")=="critique" | True | ✓ PASS |
| Per-surface cold-path defaults preserved | co-host→None, curator→"tutor" when unset | True | ✓ PASS |
| Full suite | pytest -q | 4501 passed, 26 skipped, 1 xfailed, 4 xpassed, 0 failed | ✓ PASS |

The 1 xfailed = pre-existing budget cost gate; 4 xpassed = pre-existing live-hardware markers (wizard port-bind + macOS BlackHole kext). NOT regressions.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| LENS-01 | 79-01, 79-02 | hype/critique/tutor as three grounded prompt lenses over the same structured state | ✓ SATISFIED | `LENS_TO_MODE_MOOD` + `build_lens_instruction`; truth #1 verified |
| LENS-02 | 79-01, 79-03 | Lens selection shared across co-host + curator surfaces | ✓ SATISFIED | `read_shared_lens` + `_apply_lens` + both surfaces wired; truth #2 verified |

No orphaned requirements: REQUIREMENTS.md maps only LENS-01 + LENS-02 to Phase 79, both claimed in plan frontmatter.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| dj_cohost.py | 828 | "not yet implemented" | ℹ️ Info | In unrelated Bravoh proxy /health comment, NOT lens code, pre-existing. No impact. |
| agent.py | 110 | `build_curator_instruction("tutor")` | ℹ️ Info | Inside a docstring describing the OLD behavior; live code uses `_shared_lens()`. Not a stub. |

No blocker anti-patterns. No debt markers (TBD/FIXME/XXX) in any modified lens code. `lens` confirmed ABSENT from `messages.schema.json` and `ui_bus/messages.py` (invariant #4 holds — one socket, zero new envelope, no codegen:ipc).

### Human Verification Required

#### 1. Per-lens voice fidelity (the "no AI slop" bar)

**Test:** Switch the co-host through hype / critique / tutor on a live or recorded set and listen to each lens.
**Expected:** Each lens FEELS like a distinct grounded voice — hype = party energy, critique = says what to fix, tutor = actually teaches DJing from who-you-are + semantics + reality. None hallucinate.
**Why human:** Voice-fidelity / "does the tutor teach well" is a subjective ear judgment. Per the charter this is the Phase-81 BENCH lens dimension + Kaan's ear (parked, KAAN-ACTION). Provably-distinct-prompts is automated and verified; feel is not.

#### 2. End-to-end cross-surface shared lens (live)

**Test:** Set the lens once (e.g. tutor) via the settings bus, then run BOTH the live co-host and a curator request in the same session.
**Expected:** The single selection drives both surfaces' voice — no per-surface re-selection.
**Why human:** Full live round-trip needs a real Gemini key + live audio + a curator run. The shared-read seam is unit-verified; the live round-trip is a runtime check.

### Gaps Summary

No gaps. All three roadmap success criteria are observably true in the shipped code:
- **SC1/LENS-01** — three lenses are a validated-enum selector over the UNTOUCHED `build_system_instruction`; default hype byte-identical (v4 golden green), three prompts distinct, unknown lens fails loud.
- **SC2/LENS-02** — `ConfigStore.extra["lens"]` is the ONE shared selection read by both the co-host (`_resolve_prompt_cell`) and both curator seams; persisted via `_apply_lens`, no IPC/schema bump (invariant #4 intact), per-surface cold-path defaults preserve byte-identity, curator caches lens-keyed.
- **SC3** — the citation gate is lens-blind by construction (`CitationLinter.check` never reads the lens); strip decision pinned identical across lenses.

Full suite 4501 passed / 0 failed, all phase commits present. Status is `human_needed` (not `passed`) ONLY because the subjective voice-fidelity verdict is intentionally deferred to Phase-81 BENCH + Kaan's ear — this is the expected disposition per the phase charter, not a defect.

---

_Verified: 2026-05-26_
_Verifier: Claude (gsd-verifier)_
