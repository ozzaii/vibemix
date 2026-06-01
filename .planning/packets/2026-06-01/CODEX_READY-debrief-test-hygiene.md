# CODEX_READY: Debrief Test Hygiene

Date: 2026-06-01
Author: Codex
Status: LAND packet, test hygiene slice
Package: Package 1B - Debrief Test Hygiene

## Decision

LAND this slice as `test(debrief): clean lint hygiene`.

This package is intentionally mechanical. It removes old lint from debrief test
files so the final broad lint gate does not fail on unrelated test hygiene.

## Files

- `tests/debrief/conftest.py`
- `tests/debrief/test_ear_test_capture.py`
- `tests/debrief/test_main_dispatch.py`
- `tests/debrief/test_no_uncited_critique_in_debrief_e2e.py`
- `tests/debrief/test_stripper_integration_with_drills.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/packets/2026-06-01/INDEX.md`
- `.planning/packets/2026-06-01/CODEX_READY-debrief-test-hygiene.md`

## What Changed

- Removed unused imports from debrief tests.
- Sorted one debrief import block.
- Removed f-string prefixes from strings with no interpolation.
- Left product runtime code untouched.

## Evidence

Lint:

```text
uv run ruff check tests/debrief
All checks passed!
```

Debrief tests:

```text
uv run pytest -q tests/debrief
111 passed in 1.10s
```

Whitespace:

```text
git diff --check -- tests/debrief/conftest.py tests/debrief/test_ear_test_capture.py tests/debrief/test_main_dispatch.py tests/debrief/test_no_uncited_critique_in_debrief_e2e.py tests/debrief/test_stripper_integration_with_drills.py
```

## Boundaries

- No broad staging, no commit, and no product-release claim.
- This is test hygiene only. Do not mix it with runtime debrief/observability
  hunks unless the reviewer explicitly wants one debrief batch.
