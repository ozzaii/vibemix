---
phase: 41-gemini-sku-upgrade-latency-stack-v2
plan: 01
subsystem: llm
tags: [router, ci-gate, gemini, service-tier, lat-01, lat-07]
requires: []
provides:
  - vibemix.llm.model_router.resolve
  - vibemix.llm.ROUTER_PATHS
  - vibemix.llm.RouterPathError
  - scripts/release/check_no_hardcoded_model.sh
  - .github/workflows/model-literal-check.yml
affects:
  - vibemix.agent.config
  - vibemix.agent.tts_chain
  - vibemix.agent.proxy_client
  - vibemix.debrief.tldr
  - vibemix.debrief.drills
  - vibemix.library.embed
  - vibemix.library.grounding
tech_stack_added: []
patterns_used:
  - "single-source-of-truth routing table (_ROUTES dict)"
  - "frozen tuple defensively-public path keys"
  - "bash truth + Python mirror parity gate"
key_files_created:
  - src/vibemix/llm/__init__.py
  - src/vibemix/llm/_router_config.py
  - src/vibemix/llm/model_router.py
  - scripts/release/check_no_hardcoded_model.sh
  - .github/workflows/model-literal-check.yml
  - tests/llm/__init__.py
  - tests/llm/test_model_router.py
  - tests/debrief/test_tldr_model_dispatch.py
  - tests/debrief/test_drills_model_dispatch.py
  - tests/library/test_embed_router_dispatch.py
  - tests/library/test_grounding_router_dispatch.py
  - tests/repo/test_model_literal_gate.py
key_files_modified:
  - src/vibemix/agent/config.py
  - src/vibemix/agent/tts_chain.py
  - src/vibemix/agent/proxy_client.py
  - src/vibemix/debrief/tldr.py
  - src/vibemix/debrief/drills.py
  - src/vibemix/library/embed.py
  - src/vibemix/library/grounding.py
  - tests/agent/test_config.py
key_decisions:
  - "router exposes ServiceTier from google.genai.types directly (no wrapper enum)"
  - "OpenRouter TTS path uses sentinel None tier (non-Gemini-API surface)"
  - "RouterPathError subclasses KeyError for backward-compat caller patterns"
  - "library_auto_tag path reserved now (Phase 28 auto-tagger consumes later)"
  - "cache-key SHA256 frozen-golden test pins A1 invariant explicitly"
  - "bash gate counts comments as violations — docstrings must reference router path"
metrics:
  duration: "~50 min"
  completed: "2026-05-16"
  tasks: 3
  commits: 3
requirements:
  - LAT-01
  - LAT-07
---

# Phase 41 Plan 01: ModelRouter seam + CI grep gate Summary

ModelRouter seam landed — every Gemini model literal in `src/vibemix/`
now flows through `vibemix.llm.model_router.resolve(path)`, with a CI
grep gate that fails any PR re-introducing a hardcoded literal outside
the single allowlisted config file. Foundation seam for Plans 41-02..06.

## What shipped

### Task 1 — `vibemix.llm` package + tests (commit `2f6c04b`)

- `src/vibemix/llm/__init__.py` — re-exports `resolve`, `ROUTER_PATHS`,
  `RouterPathError`, `ServiceTier`.
- `src/vibemix/llm/_router_config.py` — sole literal-bearing file in
  `src/vibemix/`. Holds the locked 8-path `_ROUTES` table.
- `src/vibemix/llm/model_router.py` — `resolve(path) -> (model_id, ServiceTier | None)`.
  `RouterPathError` (KeyError subclass) on unknown path lists every
  valid key for caller diagnosability. `ROUTER_PATHS` is a frozen tuple.
- `tests/llm/test_model_router.py` — 12 tests (parametrized GA-path ×
  tier, OpenRouter sentinel, unknown-path error, frozen-tuple shape,
  non-Gemini-model guard, fallback dispatch).

### Task 2 — call-site migration (commit `e2db81f`)

9 literal sites replaced with `resolve()`-derived constants. Constant
*names* preserved for backward-compat — `LLM_MODEL`, `TTS_MODEL`,
`OPENROUTER_TTS_MODEL`, `DEBRIEF_TLDR_MODEL`, `DEBRIEF_TTS_MODEL`,
`DEBRIEF_DRILLS_MODEL`, `GEMINI_EMBEDDING_MODEL` all keep working for
existing consumers.

| Site                                 | Before                              | After                                            |
| ------------------------------------ | ----------------------------------- | ------------------------------------------------ |
| agent/config.py LLM_MODEL            | `"gemini-3-flash-preview"`          | `resolve("live_coach")[0]`                       |
| agent/config.py TTS_MODEL            | `"gemini-3.1-flash-tts-preview"`    | `resolve("live_coach_tts")[0]`                   |
| agent/config.py TTS_FALLBACK_MODEL   | `"gemini-2.5-flash-preview-tts"`    | `resolve("live_coach_tts_fallback")[0]`          |
| agent/config.py OPENROUTER_TTS_MODEL | `"google/gemini-3.1-flash-tts-…"`   | `resolve("live_coach_tts_openrouter")[0]`        |
| agent/tts_chain.py monkey-patch arg  | inline `"google/gemini-3.1-…"`      | `OPENROUTER_TTS_MODEL` (router-derived)          |
| debrief/tldr.py DEBRIEF_TLDR_MODEL   | `"gemini-3-pro-preview"`            | `resolve("debrief")[0]`                          |
| debrief/tldr.py DEBRIEF_TTS_MODEL    | `"gemini-3-flash-tts-preview"`      | `resolve("debrief_tts")[0]`                      |
| debrief/drills.py DEBRIEF_DRILLS_MODEL | `"gemini-3-pro-preview"`          | `resolve("debrief")[0]`                          |
| library/embed.py GEMINI_EMBEDDING_MODEL | `"gemini-embedding-2"`           | `resolve("embedding")[0]`                        |
| library/grounding.py:122 inline arg  | `model="gemini-embedding-2"`        | `model=GEMINI_EMBEDDING_MODEL` (router-derived)  |

Plus: new `LIVE_COACH_SERVICE_TIER = resolve("live_coach")[1]` in
`agent/config.py` so the coach loop can read the Standard-tier ServiceTier
without a second `resolve()` call.

Two docstring/comment mentions of model ids also cleaned (`debrief/tldr.py`,
`library/embed.py`, `agent/proxy_client.py`) so the grep gate stays
unconditional — no "comments are exempt" carve-out needed.

### Task 3 — CI grep gate (commit `e8f737b`)

- `scripts/release/check_no_hardcoded_model.sh` — bash truth. POSIX
  extended regex matches every banned pattern; allowlists only
  `src/vibemix/llm/_router_config.py`; emits `::error file=…,line=…::`
  GitHub annotations.
- `.github/workflows/model-literal-check.yml` — runs the bash gate on
  every PR touching `src/vibemix/**`, plus the Python mirror for
  cross-platform parity.
- `tests/repo/test_model_literal_gate.py` — 10 tests covering: clean
  tree, allowlist honored, synthetic violations fail with named file,
  tests/ + scripts/ out of scope, legacy `gemini-embedding-001` caught,
  bash subprocess parity (skipped on hosts without bash), YAML parse.

## Router-path table actually shipped

The router-paths table from `41-01-PLAN.md` shipped verbatim. No tuning
during implementation. Locked entries:

| Path                       | Model                              | Tier     | Consumer                                |
| -------------------------- | ---------------------------------- | -------- | --------------------------------------- |
| live_coach                 | gemini-3-flash-preview             | STANDARD | agent.config.LLM_MODEL                  |
| live_coach_tts             | gemini-3.1-flash-tts-preview       | STANDARD | agent.config.TTS_MODEL                  |
| live_coach_tts_fallback    | gemini-2.5-flash-preview-tts       | STANDARD | agent.config.TTS_FALLBACK_MODEL         |
| live_coach_tts_openrouter  | google/gemini-3.1-flash-tts-preview | None    | agent.tts_chain monkey-patch + factory  |
| debrief                    | gemini-3-pro-preview               | FLEX     | debrief.tldr + debrief.drills           |
| debrief_tts                | gemini-3-flash-tts-preview         | FLEX     | debrief.tldr                            |
| library_auto_tag           | gemini-3-flash-preview             | FLEX     | (reserved for Phase 28 auto-tagger)     |
| embedding                  | gemini-embedding-2                 | FLEX     | library.embed + library.grounding       |

## Literal-count grep proof

Pre-migration (post-Task-1, before Task-2):

```
$ grep -rn "gemini-3-flash\|gemini-3-pro\|gemini-embedding-\|gemini-3.1-flash\|gemini-2.5-flash" src/vibemix/
src/vibemix/debrief/tldr.py:16:Wave 0 A1 verdict: model id is ``gemini-3-pro-preview`` …
src/vibemix/debrief/tldr.py:44:# Wave 0 A1: full preview id is required. Bare 'gemini-3-pro' → 404.
src/vibemix/debrief/tldr.py:45:DEBRIEF_TLDR_MODEL = "gemini-3-pro-preview"
src/vibemix/debrief/tldr.py:46:DEBRIEF_TTS_MODEL = "gemini-3-flash-tts-preview"
src/vibemix/debrief/drills.py:39:DEBRIEF_DRILLS_MODEL = "gemini-3-pro-preview"
src/vibemix/library/embed.py:32:- Model ID is ``gemini-embedding-2`` …
src/vibemix/library/embed.py:63:GEMINI_EMBEDDING_MODEL = "gemini-embedding-2"
src/vibemix/library/grounding.py:122:            model="gemini-embedding-2",
src/vibemix/agent/config.py:16:LLM_MODEL: str = "gemini-3-flash-preview"
src/vibemix/agent/config.py:17:TTS_MODEL: str = "gemini-3.1-flash-tts-preview"
src/vibemix/agent/config.py:18:TTS_FALLBACK_MODEL: str = "gemini-2.5-flash-preview-tts"
src/vibemix/agent/config.py:23:OPENROUTER_TTS_MODEL: str = "google/gemini-3.1-flash-tts-preview"
src/vibemix/agent/proxy_client.py:19:# "google/gemini-3.1-flash-tts-preview".
src/vibemix/agent/tts_chain.py:29:_openai_tts_mod.AUDIO_STREAM_MODELS.add("google/gemini-3.1-flash-tts-preview")
```

Post-migration (post-Task-2, current tree):

```
$ grep -rn "gemini-3-flash\|gemini-3-pro\|gemini-embedding-\|gemini-3.1-flash\|gemini-2.5-flash" src/vibemix/ | grep -v "_router_config.py" | wc -l
0
```

Bash gate exit code:

```
$ bash scripts/release/check_no_hardcoded_model.sh
Plan 41-01 gate: clean — no hardcoded Gemini model literals in src/vibemix/ outside src/vibemix/llm/_router_config.py.
$ echo $?
0
```

## Test counts + regression status

| Suite                                                            | Tests | Status |
| ---------------------------------------------------------------- | ----- | ------ |
| tests/llm/test_model_router.py                                   | 12    | green  |
| tests/repo/test_model_literal_gate.py                            | 10    | green  |
| tests/agent/test_config.py (extended)                            | 8     | green  |
| tests/agent/test_tts_chain.py (regression)                       | 9     | green  |
| tests/debrief/test_tldr_model_dispatch.py                        | 4     | green  |
| tests/debrief/test_drills_model_dispatch.py                      | 2     | green  |
| tests/library/test_embed_router_dispatch.py                      | 4     | green  |
| tests/library/test_grounding_router_dispatch.py                  | 3     | green  |
| **Plan-level verification command total**                        | **57**| green |

Wider regression: `uv run pytest tests/agent/ tests/debrief/ tests/library/
tests/llm/ --ignore=tests/agent/test_persona.py` → **443 / 443 green**.

The one excluded test (`test_persona_02_byte_identical_to_v4`) is
pre-existing and unrelated — it looks for `cohost_v4.py`, which is an
untracked POC reference file (per memory `project_v3_poc_reference`
and `project_v4_canonical_baseline`). It fails on `main` HEAD as well;
this plan did not regress it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Critical functionality] Cleaned 3 docstring/comment
mentions of model ids so the grep gate stays unconditional.**

- **Found during:** Task 2 / Task 3
- **Issue:** The plan called for "Excludes: docstrings? NO — docstrings
  carrying example model strings are also a regression risk. … Comment
  containing the literal counts as a violation." Two docstrings
  (`debrief/tldr.py:16`, `library/embed.py:32`) and one comment
  (`agent/proxy_client.py:18-19`) referenced model ids by name.
- **Fix:** Rewrote each to reference the router path / config file by
  name instead. No semantic loss.
- **Files modified:** `src/vibemix/debrief/tldr.py`,
  `src/vibemix/library/embed.py`, `src/vibemix/agent/proxy_client.py`
- **Commit:** `e2db81f` (folded into Task 2 migration commit since they
  are part of the same logical change — making the call sites
  router-clean for the gate).

### Assumption verdicts surfaced

- **A1 (cache-key invariant):** Held. The frozen-golden SHA256 test
  (`test_library_embed_cache_key_unchanged`) pins
  `SHA256("canary-bytes-41-01-task-2" || "gemini-embedding-2" ||
  "v1-3excerpt-mean") == 26f69c90…d6ead42`. Migration is byte-identical
  to pre-migration on the hash side.
- **A7 (backward-compat re-exports):** Held. All eight migrated constant
  names (`LLM_MODEL`, `TTS_MODEL`, `TTS_FALLBACK_MODEL`,
  `OPENROUTER_TTS_MODEL`, `DEBRIEF_TLDR_MODEL`, `DEBRIEF_TTS_MODEL`,
  `DEBRIEF_DRILLS_MODEL`, `GEMINI_EMBEDDING_MODEL`) preserved.
  `__main__.py`, `agent/cache.py`, and all consumer tests run unchanged.
- **A8 (OpenRouter TTS as separate router key):** Held. The
  `live_coach_tts_openrouter` path uses a sentinel `None` tier; the
  monkey-patch in `tts_chain.py` now consumes `OPENROUTER_TTS_MODEL`
  (router-derived) instead of an inline literal. Test
  `test_41_01_openrouter_tts_model_matches_router` confirms the
  AUDIO_STREAM_MODELS set still contains the same string post-migration.

### One incidental quirk worth noting

`git stash` during regression-debugging captured the LFS-pointer-bytes-vs-
real-bytes mismatch on the existing mascot GLBs (`tauri/ui/assets/...`).
Recovered by `git checkout stash@{0} -- <my-files-only>` — no LFS objects
were perturbed and no Task 2 work was lost.

## Self-Check: PASSED

Files exist:

- `src/vibemix/llm/__init__.py` — FOUND
- `src/vibemix/llm/_router_config.py` — FOUND
- `src/vibemix/llm/model_router.py` — FOUND
- `scripts/release/check_no_hardcoded_model.sh` — FOUND (executable)
- `.github/workflows/model-literal-check.yml` — FOUND
- `tests/llm/test_model_router.py` — FOUND
- `tests/repo/test_model_literal_gate.py` — FOUND
- 4 dispatch test files — FOUND

Commits:

- `2f6c04b` Task 1 — FOUND in `git log`
- `e2db81f` Task 2 — FOUND in `git log`
- `e8f737b` Task 3 — FOUND in `git log`
