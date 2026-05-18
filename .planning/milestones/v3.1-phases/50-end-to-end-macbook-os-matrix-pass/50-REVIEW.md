---
phase: 50-end-to-end-macbook-os-matrix-pass
status: clean
reviewer: gsd-code-review (in-orchestrator standard depth)
date: 2026-05-18
scope:
  - tests/e2e/macbook/ (16 new files)
  - scripts/audit/check_no_slop_e2e.py + test
  - scripts/e2e/ (3 new bash scripts + 1 test)
  - scripts/launch/cut_release.sh (Gate 6b insertion)
  - tauri/ui/package.json (devDeps + script)
  - .github/workflows/check-slop-e2e.yml
findings:
  critical: 0
  warning: 0
  info: 3
---

# Phase 50 Code Review

## Status: clean

Reviewed all source files changed during Phase 50 across the 6 plans. **Zero critical / zero warning findings.** Three Info-tier observations recorded below — none block release-cut. All Python syntactic checks pass; all bash scripts pass `bash -n`; full test sweep is 16 passed + 5 SKIPPED (each with explanatory reason per CI-tolerant fallback policy).

## Verification

```
.venv/bin/python -m py_compile tests/e2e/macbook/*.py scripts/audit/check_no_slop_e2e.py scripts/audit/test_check_no_slop_e2e.py
# → silent OK

bash -n scripts/e2e/*.sh scripts/launch/cut_release.sh
# → all bash scripts syntactically valid

.venv/bin/python -m pytest tests/e2e/macbook/ scripts/audit/test_check_no_slop_e2e.py -q
# → 16 passed, 5 skipped in 5.18s

bash scripts/e2e/test_check_e2e_report.sh
# → all 4 test cases passed
```

## Security Sweep

- Grep for `(api[_-]?key|secret|password|token) = '...'` literal patterns → zero matches
- Grep for `gemini-N` SKU literals in `tests/e2e/macbook/` → zero matches (ModelRouter seam preserved)
- Grep for `mascot.html` references in `tests/e2e/macbook/` (excluding the documentation-of-ban comment in persona_smoke.spec.ts) → no spec-level references (POC immutability preserved)
- Grep for `shell=True` in subprocess calls → zero matches
- Grep for `bare except` → zero matches
- Grep for `eval(` / `exec(` → zero matches in Python files

## Privacy Invariant Sweep

- `_privacy_guard` session-autouse fixture asserts on every test session (memory `feedback_privacy_scope_narrow`)
- Self-test confirms fixture fires on intentional write + passes on clean run (via tmp_path + env override)
- No off-limits paths (`~/.hermes/`, `~/hermes-rig/logs/`, `~/.lmstudio/`) referenced for read OR write anywhere in new code
- Mock-redirection in `test_privacy_fixture.py` uses `tmp_path` subdirs only — real off-limits paths never touched

## Findings

### Info-1: `audio_loopback_fixture._model_router_seam_ok()` could be promoted to a shared helper

**File:** `tests/e2e/macbook/audio_loopback_fixture.py:75-110`

The AST-based literal-scrubbing helper is currently scoped to the audio-loopback module. The same pattern would help any future test file that needs to assert "no gemini-N literals in executable code". Suggest hoisting to `tests/e2e/macbook/_seam_check.py` (or `src/vibemix/llm/_seam_check.py`) for reuse in v3.2+.

**Severity:** Info — no functional issue. **Action:** defer to backlog.

### Info-2: `record_50a_walk.sh` writes raw `.mov` to `$(pwd)` rather than a controlled temp path

**File:** `scripts/e2e/record_50a_walk.sh:31`

`raw_path="$(pwd)/50a-raw-$(date -u +%Y-%m-%dT%H-%M-%SZ).mov"` writes into whatever the current working dir is at invocation time. Acceptable for the Kaan-walk discharge (Kaan picks his cwd consciously), but a more conservative path would be `${TMPDIR:-/tmp}/50a-raw-…` so accidental invocation from inside the repo doesn't pollute the working tree.

**Severity:** Info — cosmetic / hygiene. **Action:** defer; Kaan can `cd ~/Downloads` before running, which is the typical workflow.

### Info-3: `os_matrix_smoke._config_reachable` returns False for Win configs on every macOS host

**File:** `tests/e2e/macbook/os_matrix_smoke.py:91-108`

By design (engineering scaffold satisfies dry-run wire-check) — but the test suite never exercises the macOS host's CURRENT major-version line vs other-major. If Kaan's MacBook is Sonoma (14), Sequoia (15) will SKIP unreachable — which is correct, but means we never get a positive "macos-15-as PASS" without a real Sequoia box. The 50b real-VM execution at §INSTALL-VM-RUN downstream closes this; documented in REQ E2E-02 annotation.

**Severity:** Info — correctly scoped to engineering scaffold. **Action:** none; tracked under §INSTALL-VM-RUN downstream Kaan-action surface.

## Invariants Preserved

| Invariant | Status | Evidence |
|-----------|--------|----------|
| Privacy rule | ✓ | Session-autouse `_privacy_guard` + self-test |
| Anti-slop blocklist | ✓ | Sibling script imports canonical via `importlib`; word-boundary token match; CI workflow wired |
| POC immutability (`mascot.html` / `cohost*.py`) | ✓ | Zero spec-level references; existing Phase 47 grep gate covers source-level |
| IPC schema parity | ✓ | Zero new IPC messages introduced |
| ModelRouter seam | ✓ | AST-based literal check in fixture; grep confirms zero `gemini-N` literals |
| Worktree Step-0 invariant | ✓ | No worktree-isolated subagents spawned; commit messages document compliance |

## Conclusion

`status: clean`. Three Info-tier observations are deferral-track items, not release blockers. Phase 50 is release-cut-ready pending §E2E-50A-WALK + §INSTALL-VM-RUN downstream Kaan discharges.
