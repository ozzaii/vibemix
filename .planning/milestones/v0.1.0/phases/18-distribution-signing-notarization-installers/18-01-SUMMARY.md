---
phase: 18-distribution-signing-notarization-installers
plan: 01
subsystem: dist
tags: [dist, verify, security, anti-leak, stdlib-only, ci-gate]
requires: []
provides:
  - "scripts.dist.verify_binary.scan_bundle — public verifier API"
  - "scripts.dist.verify_binary.verify — alias matching the plan contract"
  - "scripts.dist.verify_binary.write_report — JSON report writer with redaction invariant"
  - "scripts.dist.verify_binary CLI — python -m scripts.dist.verify_binary <bundle>"
  - "scripts.dist._pyinstxtractor.PyInstArchive — in-house PyInstaller CArchive reader"
affects:
  - "Plan 18-05 release.yml — the post-sign verify step calls into this module"
tech-stack:
  added: []  # stdlib only — no new pip / npm deps
  patterns:
    - "Build-time leak gate (scripts.build_sidecar.assert_no_aiza_leak) lifted into a runtime twin that handles .app and .msi bundles plus PyInstaller archive recursion"
    - "Injection-seam pattern for platform / subprocess / shutil.which so unit tests exercise the .msi dispatch logic without spawning msiexec"
key-files:
  created:
    - scripts/dist/__init__.py
    - scripts/dist/_pyinstxtractor.py
    - scripts/dist/verify_binary.py
    - tests/dist/__init__.py
    - tests/dist/conftest.py
    - tests/dist/fixtures/README.md
    - tests/dist/test_verify_binary.py
  modified:
    - .gitignore  # whitelist scripts/dist/** + tests/dist/** under the generic dist/ ignore
decisions:
  - "Wrote an in-house PyInstaller CArchive reader (Apache-2.0) instead of vendoring extremecoders-re/pyinstxtractor (GPL v3). The plan assumed the upstream was Unlicense; it is not. License-clean rewrite covers the cookie + TOC + zlib payload surface the scanner needs."
  - "Hit dataclass exposes only source + pattern + binary_offset. No matched-bytes field exists (and the test test_hit_dataclass_has_no_value_field locks the invariant in)."
  - "JSON report serialises pattern names + bundle-relative source paths only; never the matched bytes (T-18-01)."
  - "Logging uses pattern + source + offset only; never the captured bytes (T-18-02, asserted via caplog test)."
  - ".msi dispatch: msiexec on Windows, 7z fallback on non-Windows, MsiInspectionUnavailable raise otherwise. Tested with subprocess injection, no real msiexec invocation."
metrics:
  duration_minutes: 35
  completed: 2026-05-13
  tasks: 2
  files_created: 7
  files_modified: 1
  tests_added: 21
  loc:
    verify_binary_py: 617
    _pyinstxtractor_py: 388
    test_verify_binary_py: 415
---

# Phase 18 Plan 01: Binary Attack Verification (VERIFY-04) Summary

Stdlib-only post-codesign / post-MSI scanner that walks the shipped vibemix bundle and flags any byte sequence matching the Google AI Studio / AWS / Google OAuth / OpenAI / generic-Google-key patterns. Zero new pip or npm dependencies. Hand-off ready for Plan 18-05's release workflow.

## What shipped

- **`scripts/dist/verify_binary.py`** (617 LOC, stdlib only)
  - Public API: `scan_bundle(bundle, *, allowlist_suffixes=..., platform=None, runner=None, which=None) -> VerifyResult`, alias `verify(...)`, `write_report(result, path)`.
  - CLI: `python -m scripts.dist.verify_binary <bundle> [--report PATH] [--allowlist-suffix SUFFIX] [--strict]`. Exit codes: 0 clean / 1 flagged / 2 usage-or-inspection-error.
  - Patterns (all module-level `re.Pattern[bytes]`):
    - `AIZA_PATTERN` — `AIza[A-Za-z0-9_-]{35}` (Gemini / Google AI Studio)
    - `AKIA_PATTERN` — `AKIA[A-Z0-9]{16}` (AWS access key id)
    - `YA29_PATTERN` — `ya29\.[A-Za-z0-9_-]{20,}` (Google OAuth bearer)
    - `SK_PATTERN` — `sk-[A-Za-z0-9_-]{20,}` (OpenAI keys)
    - `GENERIC_KEY_PATTERN` — `\b[A-Za-z0-9_-]{39}\b` (heuristic Google-API-key silhouette; suppressed on font/image/audio suffixes via the allowlist)
  - PyInstaller archive recursion via the in-house `_pyinstxtractor`. Nested hits surface as `archive.pyz!entry/path` to keep the source location forensically useful.
  - `.msi` dispatch handles Windows (`msiexec /a ... /qb TARGETDIR=...`), non-Windows fallback (`7z x`), and the no-inspector-available case (`MsiInspectionUnavailable`).
- **`scripts/dist/_pyinstxtractor.py`** (388 LOC, stdlib only) — minimal in-house CArchive reader. See "Vendoring decision" below.
- **`tests/dist/`** — 21 unit tests covering every behavior bullet from the plan + module-level invariants (Hit has no value-storing field; patterns are compiled bytes regexes; `verify` is an alias of `scan_bundle`).

## The two patterns + allowlist rationale

| Pattern family | Use | Trigger surface |
|----------------|-----|-----------------|
| Strict (AIza / AKIA / ya29 / sk-) | High-precision: a real leak in any of these prefixes is a release blocker. | Scanned on **every** scannable suffix. |
| `generic39` | Heuristic: catches Google-API-key shapes if a key was rotated through a less-typed format. | Scanned **except** on the font / image / audio / wasm allowlist (those trip the regex on natural high-entropy bytes). |

Allowlisted suffixes (generic-39 only — strict patterns always scan):
`.woff2 .woff .ttf .otf .wasm .png .jpg .jpeg .gif .ico .webp .mp3 .wav .ogg`

CLI users can extend the allowlist at runtime with `--allowlist-suffix .ext`.

## `.msi` dispatch decision

- **Windows (`sys.platform == "win32"`):** `msiexec /a <path> /qb TARGETDIR=<temp>` administrative install. Verified by `test_msi_dispatch_invokes_msiexec_on_windows`.
- **Non-Windows + `7z` on PATH:** `7z x -o<temp> -y <path>`. Verified by `test_msi_dispatch_falls_back_to_7z_on_non_windows`.
- **Otherwise:** `MsiInspectionUnavailable("MSI inspection requires Windows (msiexec) or 7z on PATH ...")`. Verified by `test_msi_inspection_raises_when_unavailable`.

The injection-seam pattern (`platform=`, `runner=`, `which=` keyword args to `scan_bundle` and `_inspect_msi`) keeps the unit suite hermetic — no test ever spawns a real msiexec or 7z process.

## Vendoring decision (architectural deviation, autonomous Rule 4)

**Found during Task 1.** The plan referenced upstream `extremecoders-re/pyinstxtractor` as "Unlicense / public-domain". Fetching the actual upstream confirmed it is **GPL v3** — incompatible with vibemix's intended Apache-2.0 / MIT distribution. Vendoring a GPL-v3 file into the tree would force the combined work to GPL-v3.

**Resolution:** Wrote an in-house minimal extractor (`scripts/dist/_pyinstxtractor.py`) under SPDX-License-Identifier: Apache-2.0. Covers the cookie + TOC + zlib-payload surface the scanner needs and nothing else:

- Format-only knowledge (PyInstaller 2.1+ cookie shape `!8sIIii64s` = magic + lengthofPackage + tocOffset + tocLen + pyver + pylibname[64]; v2.0 fallback at 24 bytes).
- TOC entry parse (`!IIIIBB` + variable-length name) with `..`/absolute-path sanitisation against zip-slip.
- zlib-decompress the per-entry payload; raw-byte fallback on decompress error so the scanner still sees the bytes.
- No reverse-engineering, no PyInstaller-internals reimplementation, no GPL-derived code.

This is captured per the autonomous-mode grey-area policy ("fully-autonomous = no grey-area pause"): the license mismatch is a hard correctness blocker (Rule 4 architectural decision), but the rewrite is small and license-safe, so it was made and documented rather than escalated. The test `test_pyinstaller_archive_extraction_round_trip` exercises the real extractor against a synthetic-but-valid archive that conftest builds in memory (not a mock), so the round-trip is end-to-end verified.

## Redaction invariants (T-18-01 + T-18-02)

Locked in **at the type level** and **at the test level**:

| Layer | Invariant | Locked by |
|-------|-----------|-----------|
| `Hit` dataclass | No field that could store the matched bytes (no `matched` / `value` / `bytes` / `string` / `key` / `secret` / `data`). | `test_hit_dataclass_has_no_value_field` (introspects `dataclasses.fields(Hit)`). |
| JSON report | Only `{status, scanned, binary_count, flagged_strings, hits[{source, pattern}]}`. No matched-bytes field on disk. | `test_report_redacts_matched_bytes` (asserts the sentinel byte string is absent from the serialized payload). |
| Logging | All log records reference pattern + source + offset. The actual bytes are never formatted into a message. | `test_log_output_does_not_leak_planted_key` (captures DEBUG-level records and asserts the sentinel never appears). |

## Twin to `build_sidecar.assert_no_aiza_leak` (Phase 11 W1)

These are deliberately separate functions:

| | `assert_no_aiza_leak` (Phase 11 W1) | `verify_binary.scan_bundle` (Phase 18 W1) |
|-|--------------------------------------|--------------------------------------------|
| Where it runs | Build-time, inside `scripts.build_sidecar` after PyInstaller `--onedir` | CI / release-time, after codesign / Inno Setup MSI |
| Input shape | `dist/vibemix-core/` directory tree | `.app` directory or `.msi` file (extracts MSI first) |
| Pattern surface | AIza-only (Gemini key — the immediate concern at packaging time) | AIza + AKIA + ya29 + sk- + generic-39 (broader release-time net) |
| PyInstaller archive recursion | No (operates on the unzipped onedir directly) | Yes (post-sign artifacts hide payload inside CArchives) |
| Threat surface owned | Phase 5 invariant — no key embedded at build time | VERIFY-04 — no key reaches the customer artifact |

They share **no code** by design: build_sidecar is run by the developer before signing; verify_binary is run by CI against the signed artifact. Any future cross-cutting change (e.g. pattern tuning) updates both in lock-step.

## Hand-off to Plan 18-05

The CI step in `.github/workflows/release.yml` (Plan 18-05) wires this in as:

```yaml
- name: Verify shipped bundle has no leaked API keys
  run: |
    source .venv/bin/activate
    python -m scripts.dist.verify_binary "${BUNDLE_PATH}" \
      --report verify-report.json
  env:
    BUNDLE_PATH: ${{ matrix.os == 'macos-14' && 'dist/vibemix.app' || 'dist/vibemix-installer.msi' }}
```

Exit 1 fails the release job. The `verify-report.json` is uploaded as a CI artifact for forensics.

## Deviations from Plan

### Architectural decisions handled autonomously (Rule 4)

**1. [Rule 4 - Architectural] In-house PyInstaller extractor instead of vendoring upstream**

- **Found during:** Task 1 (vendoring step)
- **Issue:** Plan referenced upstream `extremecoders-re/pyinstxtractor` as "Unlicense / public-domain". The actual upstream license header reads `Licensed under GNU General Public License (GPL) v3.` Vendoring would force the combined vibemix work to GPL-v3, which is incompatible with the Apache-2.0 / MIT distribution intent.
- **Resolution:** Wrote a minimal Apache-2.0-licensed CArchive reader covering only the cookie + TOC + payload-extract surface needed by the scanner. ~390 LOC, format-only knowledge from PyInstaller's own readers.py spec. Tests exercise the real extractor against a synthetic-but-valid CArchive built by conftest.
- **Files:** `scripts/dist/_pyinstxtractor.py` (388 LOC), `tests/dist/conftest.py` (synthetic-archive builder).
- **Commits:** `a43036e` (initial) + `d32593c` (cookie struct correction).
- **Autonomous mode policy:** Fully-autonomous mode says "no grey-area pause"; the license mismatch is a clear correctness blocker and the rewrite is small + license-safe, so the decision was made without surfacing a checkpoint.

### Auto-fixed issues (Rule 3)

**2. [Rule 3 - Blocking] `.gitignore` whitelisted `scripts/dist/` and `tests/dist/`**

- **Found during:** Task 1 commit
- **Issue:** The repo-level `dist/` ignore (line 9 of `.gitignore`) matches `scripts/dist/` and `tests/dist/` anywhere in the tree. `git add scripts/dist/...` refused with "paths are ignored".
- **Fix:** Added explicit `!scripts/dist/`, `!scripts/dist/**`, `!tests/dist/`, `!tests/dist/**` whitelist after the generic `dist/` rule.
- **Files:** `.gitignore`
- **Commit:** `a43036e`

**3. [Rule 1 - Bug] PyInstaller cookie struct correction**

- **Found during:** Task 2 RED phase — the round-trip test failed because `_parse_toc` parsed an empty TOC.
- **Issue:** Initial `_parse_cookie` decoded the cookie as `lengthHi + lengthLo + tocOffset + tocLen + pyver` (5 uint32s = 20 bytes after magic). The actual PyInstaller 2.1+ cookie is `lengthofPackage + tocOffset + tocLen + pyver` (4 ints = 16 bytes after magic) followed by `pylibname[64]`. The 4-byte misalignment broke archive_start computation and yielded a zero-length TOC read.
- **Fix:** Switched the struct format to `>8sIIii` for the cookie head; reworked `archive_start` resolution to try both v2.1 (88-byte) and v2.0 (24-byte) cookie sizes and pick the first that yields a plausible TOC bounds.
- **Files:** `scripts/dist/_pyinstxtractor.py`
- **Commit:** `d32593c`

### Plan-line clarifications (non-deviations)

**4. `from __future__ import annotations` and the stdlib-only verification regex**

The plan's verification line excludes the import list to: `re|argparse|subprocess|logging|pathlib|tempfile|json|dataclasses|enum|shutil|sys|os|contextlib|collections|typing|\\.` — but `from __future__ import annotations` is also present (it is Python language plumbing, not a third-party module). Treating `__future__` as stdlib (which it is — it ships with CPython) keeps the invariant intact.

## Verification

| Check | Status |
|-------|--------|
| `python -m scripts.dist.verify_binary --help` exits 0, mentions `--report`, `--allowlist-suffix`, `bundle` positional | PASS |
| `python -m pytest tests/dist/ -q` | 21 passed in 0.18s |
| `python -m pytest tests/dist/ tests/sidecar/ -q` (regression on neighbouring tests) | 42 passed in 11.17s |
| Stdlib-only invariant grep (excluding `__future__`) | 0 non-stdlib imports |
| `grep -RE "AIza[A-Za-z0-9_-]{35}" scripts/dist/ tests/dist/` | 0 string-literal matches; only `b"AIza" + b"A" * 35`-shape synthesis expressions in test bodies |
| POC files (cohost*.py / mascot.html / mocks/) untouched | `git log HEAD~2..HEAD --name-only` shows only `scripts/dist/*`, `tests/dist/*`, `.gitignore` |

## Known Stubs

None. Every artifact is wired end-to-end and covered by tests. The `--strict` CLI flag is currently a no-op (reserved for future tuning) and labelled as such in `--help`; this is documented behaviour, not a stub.

## Self-Check: PASSED

- Files created exist:
  - `scripts/dist/__init__.py` — FOUND
  - `scripts/dist/_pyinstxtractor.py` — FOUND
  - `scripts/dist/verify_binary.py` — FOUND
  - `tests/dist/__init__.py` — FOUND
  - `tests/dist/conftest.py` — FOUND
  - `tests/dist/test_verify_binary.py` — FOUND
  - `tests/dist/fixtures/README.md` — FOUND
- Commits exist:
  - `a43036e` (feat(18-01): verify_binary AIza-scan + in-house pyinstxtractor) — FOUND
  - `d32593c` (test(18-01): verify_binary suite — 21 tests, redaction invariants enforced) — FOUND
