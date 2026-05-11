# Phase 1: Platform Protocol Firewall - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up the unified `vibemix` Python package skeleton with the `platform/` Protocol firewall surface in place, so all downstream phases import OS abstractions (`AudioBackend`, `ScreenBackend`, `MidiBackend`, `TrackInfoBackend`) instead of OS-specific symbols (BlackHole, Quartz, mss, mido, nowplaying-cli). Lockfile + license + public repo land this phase. SignPath Foundation OSS code-signing application is filed by Kaan on day 1 (3-week approval lead time aligns with Phase 18 installer signing).

**In scope:** package layout (`src/vibemix/...`), `pyproject.toml` + `uv.lock`, Protocol-only definitions in `src/vibemix/platform/`, `LICENSE` (Apache 2.0), SPDX headers, public GitHub repo creation, prefilled SignPath application checklist.

**Out of scope:** any platform-specific implementations (`_audio_macos.py` etc. are Phase 2-3 / 7-8), CI, full OSS hygiene files (CONTRIBUTING/SECURITY/CODE_OF_CONDUCT defer to Phase 19), PyPI publication (vibemix ships as installer, not pip-installable), end-user installer/Tauri shell (Phase 11+18).

</domain>

<decisions>
## Implementation Decisions

### Python Tooling & Package Layout
- **Package layout:** `src/vibemix/` (PEP 621 src-layout). Prevents accidental sibling imports during dev.
- **Dependency / lockfile tooling:** `uv` — produces `uv.lock` and replaces pip+venv+pip-tools+pyenv. `requirements.txt` is NOT used.
- **Python version:** 3.12.x (already locked in STATE.md; drop from POC's 3.14 for PyInstaller / PyAudioWPatch / scipy wheel availability).
- **Build backend:** `hatchling` — declared in `pyproject.toml [build-system]`.

### Protocol Surface Scope
- **Protocols to define this phase:** all four — `AudioBackend`, `ScreenBackend`, `MidiBackend`, `TrackInfoBackend`. Full firewall surface so Phase 2-9 implementations have a stable target.
- **Mechanism:** `typing.Protocol` with `@runtime_checkable` decorator. No `abc.ABC` / `@abstractmethod`.
- **File layout:** one file per protocol under `src/vibemix/platform/` — `audio.py`, `screen.py`, `midi.py`, `track.py`. `src/vibemix/platform/__init__.py` re-exports the four Protocols.
- **No stub implementations this phase.** Concrete impls (`_audio_macos.py`, `_screen_macos.py`, etc.) land in their respective dependent phases. Phase 1 ships protocol *definitions* only.

### Package Identity & SignPath
- **PyPI publication:** NOT publishing to PyPI. vibemix ships as a signed installer (Phase 18), not `pip install vibemix`. Avoids name-squatting concerns and the Bravoh-internal-use complication.
- **License files this phase:** `LICENSE` (Apache 2.0 text) at repo root + SPDX header `# SPDX-License-Identifier: Apache-2.0` in `src/vibemix/__init__.py`. `NOTICE`, `CONTRIBUTING`, `SECURITY`, `CODE_OF_CONDUCT` defer to Phase 19.
- **GitHub repo:** create public repo `github.com/ozzaii/vibemix` (Kaan's personal account) **during this phase**, before SignPath application. Public-but-minimal is acceptable. Required because SignPath OSS approval needs a public repo URL. Bravoh Enterprise exists but has zero orgs and a billing flag — the repo lives under Kaan's personal account for now and can be transferred via `gh repo transfer` once a proper `bravoh` org is stood up; SignPath survives a rename without re-approval.
- **SignPath OSS application workflow:** Phase 1 produces a prefilled checklist `.planning/signpath-application.md` with all required fields (repo URL, maintainer name/email, build system, project description, OSS license confirmation, expected build artifacts). **Kaan files the form himself** at signpath.org/foundation — Claude cannot submit forms with personal/business info.

### Claude's Discretion
- Exact `pyproject.toml` metadata phrasing (description, keywords, classifiers) — pick reasonable values consistent with PROJECT.md vision.
- Exact docstring style for Protocol methods — Google or NumPy style, pick one and apply uniformly.
- Whether to add `py.typed` marker file (recommended yes — Protocols are pure typing artifacts).
- `.gitignore` contents — copy a reasonable Python/macOS/Windows default; ensure `.env`, `.venv/`, `recordings/`, `__pycache__/`, `dist/`, `build/`, `.uv/` are covered.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- POC files at repo root (`cohost.py`, `cohost_v2.py`, `cohost_lk.py`, `cohost_v3.py`, `cohost.streaming.py.bak`) are reference material — DO NOT move or modify them in Phase 1. They get devoured progressively in Phases 2-13.
- `.planning/codebase/STACK.md` lists every dependency currently used by the POC variants — Phase 1's `pyproject.toml` declares this exact list (pinned versions from STACK.md).
- `mascot.html` + `sprite-*.png` stay at root for Phase 13 (mascot port).

### Established Patterns
- POC uses `from __future__ import annotations` in `cohost_v2.py` (line 18) for PEP 604 union syntax — match this in new code.
- POC convention: `snake_case.py`, leading underscore for private modules (`_HAS_VISION`, `_HAS_WS`, `_HAS_QUARTZ` feature flags). Carry the underscore convention to `_audio_macos.py` etc. in Phase 2-3.
- POC has no formatter/linter config. Phase 1 introduces `ruff` (lint + format) via `[tool.ruff]` in `pyproject.toml` — single tool replaces black + flake8 + isort.

### Integration Points
- Phase 2 (audio port) imports `from vibemix.platform import AudioBackend` and provides `_audio_macos.py` as the concrete impl.
- Phase 3 (sensing/state port) imports `ScreenBackend`, `TrackInfoBackend`, `MidiBackend` and provides macOS impls.
- Phase 7 (Windows port) provides `_audio_windows.py` + `_screen_windows.py`.
- Phase 11 (Tauri shell) consumes the package via PyInstaller `--onedir` against the `src/vibemix/` tree.
- Phase 18 (signing) consumes the SignPath approval that this phase's application initiates.

</code_context>

<specifics>
## Specific Ideas

- Repo URL for SignPath checklist: `https://github.com/ozzaii/vibemix` (Kaan's personal account; transfer to bravoh-org later when org exists).
- Maintainer email for SignPath: oozzxaaii@gmail.com (Kaan's email per memory).
- Expected build artifacts for SignPath checklist: Windows MSI (Inno Setup wrapping PyInstaller `--onedir` payload), eventually `vibemix-setup-{version}.msi`.
- pyproject.toml `[project]` name = `vibemix`, version = `0.1.0-dev0` (PEP 440 pre-release).
- Pin Python to `requires-python = ">=3.12,<3.13"` to keep PyInstaller wheel availability tight.

</specifics>

<deferred>
## Deferred Ideas

- Reserve `vibemix` name on PyPI for squatting defense — not done this phase; reassess if a third party publishes a competing package before Phase 19.
- `NOTICE`, `CONTRIBUTING.md` (with DCO), `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue templates, OG image — all Phase 19 (GitHub Launch Presence).
- CI matrix (GitHub Actions building signed binaries on tag push) — Phase 20 (Day-Zero Operations).
- `mypy` / `pyright` config — Phase 1 ships type hints but doesn't gate CI on them. Strict type checking enabled in a later phase if it pays off.

</deferred>
