---
phase: 41-gemini-sku-upgrade-latency-stack-v2
plan: 03
subsystem: llm
tags: [latency, runtime-gate, anti-regression, defense-in-depth, lat-08, pitfall-3]
requirements_complete: [LAT-08]
dependency_graph:
  requires:
    - "google-genai==2.0.1 (ThinkingLevel + ServiceTier enums)"
    - "Plan 41-01 ModelRouter (load-bearing seam — already merged)"
  provides:
    - "src/vibemix/llm/thinking_gate.validate_live_config — pure callable validator"
    - "LiveCoachConfigError — ValueError subclass for boot-time failure"
  affects:
    - "src/vibemix/agent/llm_factory.py — direct + proxy paths run the gate"
    - "src/vibemix/agent/dj_cohost.py — __init__ runs the gate on _gen_cfg"
tech_stack:
  added: []
  patterns:
    - "boot-time invariant validator (single seam, defense in depth)"
key_files:
  created:
    - "src/vibemix/llm/thinking_gate.py"
    - "tests/llm/test_thinking_gate.py"
  modified:
    - "src/vibemix/agent/llm_factory.py"
    - "src/vibemix/agent/dj_cohost.py"
decisions:
  - "Aggregated violation message (not first-found) — single boot surfaces full problem set"
  - "Validator accepts both enum and free-form string forms — matches SDK case-insensitive acceptance"
  - "thinking_config=None is a PASS — only EXPLICIT non-MINIMAL overrides are blocked"
  - "Two call sites (factory + agent) for defense in depth, but zero per-turn overhead"
metrics:
  duration: "~25 min"
  completed: "2026-05-16"
  tasks: "2/2"
  tests: "18 new (13 unit + 5 wiring); 275/276 regression-clean in tests/llm + tests/agent"
---

# Phase 41 Plan 03: thinking_level=MINIMAL Runtime Gate + FLEX-on-Live Defense Summary

Landed the `validate_live_config` validator in `src/vibemix/llm/thinking_gate.py` and wired it into both `llm_factory.build_llm` and `DJCoHostAgent.__init__`. Closes LAT-08 (CONTEXT D-LAT-08 invariant — live coach thinking_level must be MINIMAL) and Pitfall 3 (FLEX service_tier on the live path = unacceptable SLA).

## What Shipped

### `src/vibemix/llm/thinking_gate.py` (107 lines)

- `LiveCoachConfigError(ValueError)` — boot-time exception surfaces every offending field at once.
- `validate_live_config(cfg: GenerateContentConfig) -> None` — pure callable, zero side effects, zero I/O.
- Two private normalizers (`_normalize_thinking`, `_normalize_tier`) handle the enum-vs-string acceptance ambiguity introduced by `google.genai.types.CaseInSensitiveEnum`.

Allow / deny rules:

| Field | Allow | Deny | Absent (None) |
|---|---|---|---|
| `thinking_level` | `MINIMAL` (enum or string) | `LOW` / `MEDIUM` / `HIGH` | PASS (defensive — Gemini default) |
| `service_tier` | `STANDARD` / `PRIORITY` / absent | `FLEX` (enum or string) | PASS (SDK default = STANDARD) |

When both fields violate, the error message names BOTH (not just the first found), so a single boot surfaces the full problem set.

### Validator Call Sites (final)

| File | Line | Context |
|---|---|---|
| `src/vibemix/agent/llm_factory.py` | 32 | `_build_direct` — Phase 4 default path |
| `src/vibemix/agent/llm_factory.py` | 60 | `_build_proxy` — Phase 5 proxy mode |
| `src/vibemix/agent/dj_cohost.py` | 294 | `DJCoHostAgent.__init__` — defense in depth, runs against the actual `_gen_cfg` used per turn |

Three total. Each runs exactly ONCE per agent boot (verified by `test_validate_not_called_per_turn`).

### `tests/llm/test_thinking_gate.py` (333 lines, 18 tests, all green)

**Unit tests (13):**

| Test | Assertion |
|---|---|
| `test_minimal_thinking_passes` | `ThinkingLevel.MINIMAL` → ok |
| `test_minimal_string_lowercase_passes` | `"minimal"` → ok |
| `test_minimal_string_uppercase_passes` | `"MINIMAL"` → ok |
| `test_standard_tier_passes` | `ServiceTier.STANDARD` → ok |
| `test_priority_tier_passes` | `ServiceTier.PRIORITY` → ok |
| `test_no_service_tier_passes` | `service_tier=None` → ok |
| `test_no_thinking_config_passes` | `thinking_config=None` → ok (defensive) |
| `test_low_thinking_raises` | `LOW` → LiveCoachConfigError matching "thinking_level.*MINIMAL" |
| `test_medium_thinking_raises` | `MEDIUM` → raises |
| `test_high_thinking_raises` | `HIGH` → raises |
| `test_flex_tier_raises` | `ServiceTier.FLEX` → raises matching "service_tier.*Flex SLA" |
| `test_flex_tier_string_raises` | `"flex"` → raises (string form caught) |
| `test_both_violations_reports_both` | HIGH + FLEX → message names BOTH fields |

**Wiring tests (5):**

| Test | Assertion |
|---|---|
| `test_llm_factory_passes_with_default_config` | `build_llm("k")` succeeds; spy `call_count == 1`; cfg carries `minimal` |
| `test_llm_factory_raises_on_bad_thinking_override` | Monkeypatched `types.ThinkingConfig` → HIGH → factory raises BEFORE constructing `google_plugin.LLM` |
| `test_dj_cohost_init_passes_with_default_config` | Agent ctor spy `call_count == 1`; cfg carries `minimal` |
| `test_dj_cohost_init_raises_on_flex_tier` | Monkeypatched `types.GenerateContentConfig` to inject FLEX → ctor raises before returning |
| `test_validate_not_called_per_turn` | Spy registered AFTER ctor; 5 `llm_node` turns → `spy.call_count == 0` |

## Per-Turn-Spy Test Result

`test_validate_not_called_per_turn` confirms the zero-per-turn-overhead invariant:

```
spy = mocker.spy(agent_mod, "validate_live_config")  # registered AFTER agent.__init__
# ... 5 turns through llm_node ...
assert spy.call_count == 0
```

Result: **PASSED**. The validator never runs in the hot path. Cost = single boot-time function call per agent (~microseconds).

## New Fields Added to Live Coach Config

**None.** The factory + agent already assembled `GenerateContentConfig` with `thinking_level="minimal"` (hardcoded Phase 4 v4-port literal). Plan 41-03 adds NO new fields — it only validates the existing assembly point.

The factory refactor moved the `temperature` / `thinking_config` / `max_output_tokens` literals into a single `gen_cfg` object (so the validator has something to inspect), then passes them through to `google_plugin.LLM` as kwargs read off the validated cfg. Byte-for-byte equivalent payload at the SDK boundary — verified by `test_llm_01_build_llm_direct_kwargs_match_v4` still passing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree base sync via local `main` (origin/main is stale)**
- **Found during:** Step 0 / mandatory pre-execution sync
- **Issue:** `git fetch origin main` showed `d7accba` (stale); ModelRouter file missing.
- **Fix:** Merged local `main` (`206389e merge: plan 41-05`) which already had Phase 41 plans 41-01 + 41-05 merged. Fast-forward succeeded, ModelRouter present.
- **Commit:** (no separate commit — pre-execution sync)

**2. [Rule 3 - Blocking] Stash-pop recovery for LFS pointer conflicts**
- **Found during:** Regression baseline check
- **Issue:** A `git stash` to verify baseline failures triggered an LFS pointer-vs-real-file conflict on `tauri/ui/assets/mascot/*.glb` files (existing repo state, not caused by Plan 41-03). `git stash pop` was blocked.
- **Fix:** Used `git checkout stash@{0} -- <only the three relevant files>` to restore Task 2 work without disturbing LFS state. The mascot/.glb local changes were reverted via `git checkout --` first; those are gitignored/LFS bookkeeping outside Plan 41-03 scope.
- **Commit:** Task 2 commit `5101a10`.

### Deferred (out of scope per SCOPE_BOUNDARY rule)

**`tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4`** — pre-existing failure. Depends on `cohost_v4.py` at the repo root, which is untracked POC reference per `project_v3_poc_reference.md`. Stash-baseline confirmed the failure exists WITHOUT Plan 41-03 changes. Will be resolved when the v4 persona string is canonicalized into the package (separate phase).

**Smoke + readme + grey-area test failures (~17 total)** — same scope-boundary disposition; all pre-existing on the worktree base, all confirmed via `git stash` baseline. None touch the llm/agent paths Plan 41-03 modifies.

Logged to `deferred-items.md` in the phase directory if not already tracked.

## Threat Model Compliance

| Threat ID | Disposition | Status |
|---|---|---|
| T-41-03-01 (Tampering — env-var forcing THINKING_LEVEL=HIGH) | mitigate | DONE — no env-var bypass surface; validator runs at construction |
| T-41-03-02 (DoS — Flex tier leak onto live coach) | mitigate | DONE — validator rejects FLEX; defense in depth via 2nd gate in agent |
| T-41-03-03 (Info disclosure via error message) | accept | DONE — error names field+value, no secrets |
| T-41-03-04 (Monkey-patching validator at runtime) | accept | DONE — out of scope; CI grep gate (41-01) catches model literal regressions |

## Success Criteria Status

- [x] `src/vibemix/llm/thinking_gate.py` exposes `validate_live_config(cfg) -> None` and `LiveCoachConfigError`
- [x] Validator rejects `thinking_level != MINIMAL` AND `service_tier == FLEX`
- [x] Validator runs exactly once per agent boot (zero per-turn overhead — `test_validate_not_called_per_turn` confirms)
- [x] `llm_factory.py` + `DJCoHostAgent.__init__` both invoke the validator (defense in depth)
- [x] 18+ tests cover pass cases + failure cases + per-turn-not-called invariant
- [x] Phase 40 baseline regression-clean in tests/llm + tests/agent (275/276 — lone failure is pre-existing scope-boundary)

## Self-Check: PASSED

- `src/vibemix/llm/thinking_gate.py` — FOUND
- `tests/llm/test_thinking_gate.py` — FOUND
- `src/vibemix/agent/llm_factory.py` validator import — FOUND (line 18)
- `src/vibemix/agent/dj_cohost.py` validator call — FOUND (line 294)
- Commit `2074b5b` (RED test) — FOUND
- Commit `58c0532` (GREEN validator) — FOUND
- Commit `5101a10` (Task 2 wiring) — FOUND
