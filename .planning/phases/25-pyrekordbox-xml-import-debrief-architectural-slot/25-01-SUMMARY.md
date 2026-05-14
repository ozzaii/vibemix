---
phase: 25-pyrekordbox-xml-import-debrief-architectural-slot
plan: 01
subsystem: library
tags: [pyrekordbox, deps, sqlcipher-exclusion, spike]
requires: []
provides: [pyrekordbox-install-path-locked, xml-parser-available, sqlcipher-dormant-gate]
affects: [pyproject.toml, uv.lock, tests/library/]
tech_stack:
  added: [pyrekordbox==0.4.4, bidict==0.23.1, construct==2.10.70, SQLAlchemy==2.0.49, psutil==7.2.2, python-dateutil==2.9.0.post0]
  patterns: ["uv override-dependencies marker to exclude transitive binary blob"]
key_files:
  created:
    - .planning/phases/25-pyrekordbox-xml-import-debrief-architectural-slot/WAVE-0-DEPS-SPIKE.md
    - tests/library/__init__.py
    - tests/library/test_pyrekordbox_install.py
  modified:
    - pyproject.toml
    - uv.lock
decisions:
  - "INSTALL_PATH: --no-deps via [tool.uv] override-dependencies marker — sqlcipher3-wheels=='0.5.7' tagged sys_platform == 'never_real_platform_vbm25' (never matches)"
  - "Sqlite-vec architectural slot reserved in pyproject comment only — dep NOT shipped in v2.0 (LIBRARY-08, deferred to v2.1)"
metrics:
  duration_minutes: 22
  completed: 2026-05-14
---

# Phase 25 Plan 01: Pyrekordbox Install Path Locked + SQLCipher Dormancy Gate Summary

Locked the `pyrekordbox==0.4.4` install recipe with `uv override-dependencies` so `sqlcipher3-wheels` (3.2 MB binary blob, install_requires of pyrekordbox) stays out of the resolved venv — Plan 25-02's `RekordboxLibrary` XML parser can consume `from pyrekordbox import RekordboxXml` without a single SQLCipher byte landing in the PyInstaller bundle.

## Tasks Executed

### Task 1: pyrekordbox dep-tree spike + WAVE-0-DEPS-SPIKE.md verdict

**Commit:** `626c087`

- Reproduced `pip install --dry-run --report` against a fresh CPython 3.12 tempdir venv; confirmed `sqlcipher3-wheels==0.5.7` is in pyrekordbox 0.4.4's `setup.py` install_requires (NOT extras), so plain pip install always pulls it.
- Ran two parallel installs: plain (`pip install pyrekordbox==0.4.4`) and `--no-deps + manual transitives` (bidict, construct, numpy, psutil, SQLAlchemy, python-dateutil, packaging).
- Verified `import pyrekordbox` and `from pyrekordbox import RekordboxXml` both succeed under the `--no-deps + manual` recipe — `pyrekordbox.db6.database` has a try/except guard at `database.py:28-34` that falls back to stdlib `sqlite3` and sets `_sqlcipher_available = False` when `sqlcipher3` is absent.
- Wrote `WAVE-0-DEPS-SPIKE.md` with verdict line `INSTALL_PATH: --no-deps`, dep-tree evidence dump, manual transitive list with exact pins, and `SQLCIPHER_DORMANT_CONFIRMED` block — zero modules matching `*sqlcipher*` in `sys.modules` after `import pyrekordbox`.

### Task 2: pyproject.toml + uv.lock + 3 smoke tests

**Commit:** `314c98d`

- Added `pyrekordbox==0.4.4` and 5 of the 7 manual transitives to `[project].dependencies` (numpy already explicit; packaging / typing_extensions / six pulled transitively).
- Encoded the `--no-deps` semantics via `[tool.uv] override-dependencies` with marker `sys_platform == 'never_real_platform_vbm25'` on `sqlcipher3-wheels==0.5.7`. uv keeps it in the resolution graph (no resolver error) but skips it at install time on every real platform. Confirmed via `uv sync` post-state: `ls .venv/lib/python3.12/site-packages/ | grep sqlcipher` returns nothing.
- Added LIBRARY-08 architectural slot comment for sqlite-vec — slot reserved in commentary, dep NOT shipped in v2.0 (deferred to v2.1 per CONTEXT D-08).
- `tests/library/test_pyrekordbox_install.py`: 3 import-only smoke tests — top-level `import pyrekordbox`, `from pyrekordbox import RekordboxXml`, and a fresh-interpreter subprocess gate that asserts no `*sqlcipher*` modules leak into `sys.modules`. All 3 pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] uv's pip override pattern**

- **Found during:** Task 2 (pyproject.toml authoring).
- **Issue:** The plan's verify step ran `uv sync --quiet` after adding `pyrekordbox==0.4.4` to `[project].dependencies`. uv resolves transitives from the package metadata, which would re-pull `sqlcipher3-wheels` no matter what `[project].dependencies` says — `--no-deps` is a pip flag, not a uv-sync flag.
- **Fix:** Used `[tool.uv] override-dependencies` (documented uv feature for resolution overrides) with a never-matching `sys_platform` marker on `sqlcipher3-wheels==0.5.7`. uv keeps the package in the lock as marker-conditional and silently skips it on every real platform. The verify gate (`uv sync` + smoke tests) passes cleanly.
- **Files modified:** `pyproject.toml` (`[tool.uv]` block added), `uv.lock` (manifest overrides recorded).
- **Commit:** `314c98d`

## Authentication Gates

None required — all install operations were against PyPI public packages.

## Self-Check: PASSED

| Claim                                                                                | Verified                                                                                                                                                                                                                            |
| ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `WAVE-0-DEPS-SPIKE.md` exists with verdict `INSTALL_PATH: --no-deps`                 | ✅ FOUND — `.planning/phases/25-pyrekordbox-xml-import-debrief-architectural-slot/WAVE-0-DEPS-SPIKE.md` (line 1)                                                                                                                       |
| `WAVE-0-DEPS-SPIKE.md` contains `SQLCIPHER_DORMANT_CONFIRMED`                        | ✅ FOUND                                                                                                                                                                                                                              |
| `pyproject.toml` declares `pyrekordbox==0.4.4`                                       | ✅ FOUND in `[project].dependencies`                                                                                                                                                                                                  |
| `[tool.uv].override-dependencies` excludes `sqlcipher3-wheels`                       | ✅ FOUND — `sqlcipher3-wheels; sys_platform == 'never_real_platform_vbm25'`                                                                                                                                                            |
| `tests/library/test_pyrekordbox_install.py` exists with 3 tests                      | ✅ FOUND — 3 tests pass (`pytest tests/library/test_pyrekordbox_install.py` → 3 passed)                                                                                                                                                |
| `.venv/lib/python3.12/site-packages/` contains no `sqlcipher*` directory             | ✅ CONFIRMED (post-`uv sync`)                                                                                                                                                                                                          |
| Both commits exist (`626c087`, `314c98d`)                                            | ✅ FOUND in `git log`                                                                                                                                                                                                                 |
