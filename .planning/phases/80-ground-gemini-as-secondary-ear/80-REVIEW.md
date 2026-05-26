---
phase: 80-ground-gemini-as-secondary-ear
reviewed: 2026-05-26T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/vibemix/__main__.py
  - src/vibemix/agent/dj_cohost.py
  - src/vibemix/llm/_router_config.py
  - src/vibemix/prompts/matrix.py
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 80: Code Review Report

**Reviewed:** 2026-05-26
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase 80 adds a default-OFF `secondary_ear` framing flag (`VIBEMIX_GROUND_SECONDARY_EAR`) threaded env → `__main__.py` → `DJCoHostAgent.__init__` → `llm_node` → `build_parts_description`, plus a comment-only doc note in `_router_config.py`. The change is small, disciplined, and matches the Phase-79 lessons. I verified all seven focus areas; most pass cleanly. No BLOCKER-class defects.

**The flag reaches the live path — confirmed (the Phase-79 dead-flag failure mode is NOT present here).** Full trace verified by code reading + grep: `os.environ.get("VIBEMIX_GROUND_SECONDARY_EAR", ...)` (`__main__.py:1043`) → `secondary_ear=ground_secondary_ear` at the `DJCoHostAgent(...)` call (`__main__.py:1117`) → `self._secondary_ear = secondary_ear` (`dj_cohost.py:605`) → `secondary_ear=self._secondary_ear` at the live `build_parts_description` call inside `llm_node` (`dj_cohost.py:1526`). There is exactly ONE `build_parts_description` call site in the codebase (grep-confirmed), and it is on the production reaction path. The clause lands in `contents[0]`, consumed by BOTH brain paths (genai via `contents[0]`, OpenRouter via `full_prompt = contents[0]` at `dj_cohost.py:1573`). No gap.

**Cold-path byte-identity — confirmed empirically.** I ran all 4 branches of `build_parts_description` with `secondary_ear` default vs explicit `False` vs `True`: default == `False` for every branch (byte-identical, no trailing whitespace), and `True` appends exactly the clause and nothing else. Strictly additive across all branches via `return base + secondary_clause`.

**Part-1 audio attach is UNCONDITIONAL — confirmed.** `contents` (`dj_cohost.py:1529-1532`) always appends the Part-1 `audio_wav`; the flag only touches `parts_clause` text. Not gated.

**Env parsing is robust.** Mirrors `VIBEMIX_RECALL_ENABLED` (truthy-by-exclusion: `not in ("0","off","false","no","")`), with `.strip().lower()`. Unset/empty/whitespace → OFF. Slightly more permissive than recall (adds `"no"`), which is an improvement.

**No hardcoded model literal introduced; no `genai.Client`/API key on any new path** — both grep-confirmed. The `_router_config.py` change is comment-only above the pre-existing `gemini-3.5-flash` route.

The two WARNINGs below are about the *content* of the framing clause (a semantic conflict with the existing live prompt) and a minor cold-path stdout difference. Both are real, neither blocks ship.

## Warnings

### WR-01: Secondary-ear framing clause directly contradicts the live prompt's "EARS WIN" / Invariant #3 ("Trust the audio")

**File:** `src/vibemix/prompts/matrix.py:665-669` (clause text); contradiction surfaces against `src/vibemix/prompts/matrix.py:295` and `:333`

**Issue:** When the flag is ON, the appended clause reads:

> "The live audio is a secondary grounding signal — the structured evidence above is authoritative; never claim an event the evidence does not list."

This is appended to `contents[0]` AFTER the system instruction (HYPE_INTERMEDIATE on the default live cell), which repeatedly and emphatically asserts the opposite:

- `matrix.py:295`: "If your evidence and your ears disagree, your **EARS WIN**. The evidence packet can be stale; the audio is now."
- `matrix.py:333` (PRINCIPLES #1): "EARS over numbers. hearing[] is guardrails, not source of truth."
- `matrix.py:284`: "the live audio is the truth ... Trigger is the seed; ears are the referee."

The refrain that immediately precedes the new clause even says: "Your ears are the referee — the evidence above is grounded context." Then the new clause says the evidence is *authoritative* and the audio is *secondary*. CLAUDE.md Cardinal Invariant #3 is "Trust the audio — live audio evidence is authoritative." The new framing inverts that priority.

This is not a dead-flag or byte-identity defect (it's correctly gated, default-OFF). It is a **semantic correctness risk**: with the flag ON, Gemini receives two mutually contradictory authority instructions in the same prompt, with the new clause holding strongest recency (appended last in the parts suffix). The likely behavior is the model down-weighting its own audio perception in favor of the structured `MusicState` evidence — which is exactly the "react late / miss the real drop" failure mode the prompt's latency section was built to defeat, AND a partial reversal of Invariant #3. This is presumably the intended Phase-81 BENCH hypothesis (does grounding the model in structured evidence reduce hallucination at the cost of liveness), so it may be deliberate — but it should be called out explicitly in the phase artifacts as an *intentional* invariant-#3 tension, not shipped silently. If the BENCH judgment is parked, the clause should not phrase the conflict as flatly as "the structured evidence above is authoritative" while the body says ears win.

**Fix:** Either (a) soften the clause so it reinforces rather than overrides "ears win" — e.g. "The structured evidence above is your grounding ledger: never claim an event it does not list. But your ears remain the referee on *what is happening now* — the evidence can be stale." This keeps the never-invent guard (the actual GROUND-01 intent) without inverting Invariant #3; or (b) explicitly document in the phase CONTEXT/PLAN that flag-ON deliberately overrides Invariant #3 for the BENCH and gate the BENCH conclusion before this can be the live default. The never-claim-an-unlisted-event half is sound and should stay; only the "audio is secondary / evidence is authoritative" framing is the conflict.

### WR-02: Flag-ON vs cold-path stdout differs — the `-> secondary-ear:` startup line prints unconditionally

**File:** `src/vibemix/__main__.py:1046-1051`

**Issue:** The byte-identity contract in the comments (`__main__.py:1040`, `dj_cohost.py:603-604`, `matrix.py:622-625`) is scoped to the *reaction request / prompt* — and that holds. But the new unconditional `print("-> secondary-ear: ON" if ... else "-> secondary-ear: OFF ...")` at `__main__.py:1046` emits a NEW startup line on every run, including the default-OFF path. This is not a prompt byte-identity break, but it is a v8.0 stdout-surface change on the cold path. If any test or harness asserts on the startup banner exact text (the repo has `runtime/soak`, `ttft`, and startup-line conventions per CLAUDE.md "startup lines `-> ...`"), this adds a line that wasn't there in v8.0. Low risk, but it contradicts the "omitting the env var = v8.0 byte-identical behavior" comment at `__main__.py:1115` if "behavior" is read to include startup output.

**Fix:** This is acceptable as-is if no startup-banner snapshot test exists (consistent with the existing `-> recall:` and `-> brain via OpenRouter:` lines, which also print conditionally). If you want strict cold-path stdout parity, print the line only when ON: `if ground_secondary_ear: print("-> secondary-ear: ON")`. Confirm no test asserts the full banner; otherwise this is informational. Leaving it matches the established `-> recall: wired but disabled` pattern, so WARNING not BLOCKER.

## Info

### IN-01: `build_parts_description` refactor from early-`return` to `if/elif/else + return base + clause` is correct but worth a regression pin

**File:** `src/vibemix/prompts/matrix.py:671-705`

**Issue:** The diff restructured four early `return` statements into an `if/elif/else` assigning `base`, then a single `return base + secondary_clause`. This is the correct shape for appending the clause uniformly to all branches, and I verified byte-identity. One latent footgun: the `else` branch (`matrix.py:694`) now implicitly handles the "both True" case rather than the explicit `if has_mic_part and has_lookahead_part`. The four boolean combinations are exhaustive over two bools so `else` is provably the both-True case — but a future fifth branch (e.g. a third part type) would silently fall into `else` and get the both-True wording. The existing test (`tests/prompts/test_matrix_3part_labeling.py`, referenced in the docstring) pins the "NOT YET HEARD" substrings; confirm it also has a case asserting the both-True branch emits "P3" and the lookahead-only branch emits "P2" so the implicit-`else` collapse can't regress.

**Fix:** No code change required. Add/verify a test asserting the secondary clause is appended in all 4 branches (`secondary_ear=True` → clause present for each of the 4 `(mic, lookahead)` combos), and that the `else` branch is the both-True case specifically. This locks the refactor and the additivity contract.

---

_Reviewed: 2026-05-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
