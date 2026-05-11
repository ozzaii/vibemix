---
phase: 01-platform-protocol-firewall
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - uv.lock
  - .gitignore
  - .python-version
  - LICENSE
  - README.md
  - src/vibemix/__init__.py
  - src/vibemix/py.typed
  - src/vibemix/platform/__init__.py
  - src/vibemix/platform/audio.py
  - src/vibemix/platform/screen.py
  - src/vibemix/platform/midi.py
  - src/vibemix/platform/track.py
  - tests/__init__.py
  - tests/conftest.py
  - tests/test_package.py
  - tests/test_platform.py
  - tests/test_license.py
  - tests/test_signpath_checklist.py
  - .planning/signpath-application.md
  - docs/setup-github-repo.md
  - .planning/phases/01-platform-protocol-firewall/01-SUMMARY.md
autonomous: false
requirements:
  - ARCH-01
  - ARCH-02
  - DIST-04
user_setup:
  - service: github
    why: "Create the public OSS repo at github.com/ozzaii/vibemix. Required as the SignPath application's repo URL."
    dashboard_config:
      - task: "Run `gh repo create ozzaii/vibemix --public ...` (see docs/setup-github-repo.md) and push initial Phase 1 commits"
        location: "Local terminal authenticated to gh as ozzaii"
  - service: signpath-foundation
    why: "OSS code-signing cert for the eventual Windows MSI (Phase 18). ~1 week approval; filed day 1 of Phase 1."
    dashboard_config:
      - task: "Submit the 9-section OSS application using .planning/signpath-application.md as the field reference"
        location: "https://signpath.io/solutions/open-source-community"

must_haves:
  truths:
    - "Running `uv sync` on a clean checkout (Python 3.12) materialises `.venv/` and produces a valid `uv.lock`."
    - "`uv run python -c 'import vibemix; print(vibemix.__version__)'` prints `0.1.0-dev0` without error."
    - "`uv run python -c 'from vibemix.platform import AudioBackend, ScreenBackend, MidiBackend, TrackInfoBackend'` succeeds with zero OS-specific module import side effects (no `sounddevice`, `mss`, `Quartz`, `mido` loaded by the import)."
    - "Each of the four Protocols is `@runtime_checkable`: `runtime_checkable(AudioBackend) is AudioBackend` and `isinstance(object(), AudioBackend) is False`."
    - "`uv run ruff check src/` and `uv run ruff format --check src/` both exit 0."
    - "`.planning/signpath-application.md` contains all 9 SignPath form sections fully prefilled and clearly tags Kaan-only submission steps."
    - "`docs/setup-github-repo.md` contains the exact gh CLI commands Kaan runs to create `github.com/ozzaii/vibemix` and push the initial commits."
    - "POC files at repo root (`cohost*.py`, `run*.sh`, `mascot.html`, `sprite-*.png`, `generate_bat.py`, `_test_*.py`, `test_voice.py`, `fillers/`) are untouched — `git diff --name-only main..HEAD` excludes them."
  artifacts:
    - path: "pyproject.toml"
      provides: "PEP 621 project metadata + hatchling build backend + ruff config + pinned dependency list (sys_platform markers for darwin) + dev group with ruff/pytest"
      contains: "build-backend = \"hatchling.build\""
    - path: "uv.lock"
      provides: "Reproducible cross-platform lockfile (committed) — `uv sync --frozen` works after fresh clone"
    - path: ".python-version"
      provides: "Pins Python interpreter to 3.12 for uv-managed toolchain"
    - path: "LICENSE"
      provides: "Verbatim Apache License 2.0 text with appendix copyright `Copyright 2026 Bravoh / Kaan Özkan`"
      contains: "Apache License"
    - path: "README.md"
      provides: "Minimal pre-release README — tagline + Bravoh link + Apache 2.0 mention + platforms (macOS+Windows); expanded in Phase 19"
    - path: ".gitignore"
      provides: "Python + macOS + Windows + uv + vibemix-specific patterns; `.env`, `.env.*` excluded; `!.env.example` carve-out; `recordings/`, `*.wav`, `*.jsonl` excluded"
      contains: ".env"
    - path: "src/vibemix/__init__.py"
      provides: "Package entry point with SPDX header + `__version__ = '0.1.0-dev0'`"
      contains: "__version__"
    - path: "src/vibemix/py.typed"
      provides: "PEP 561 marker — empty file, exists in built wheel"
    - path: "src/vibemix/platform/__init__.py"
      provides: "Re-exports all four Protocols + value dataclasses; module docstring describing the firewall"
      exports: ["AudioBackend", "ScreenBackend", "MidiBackend", "TrackInfoBackend", "WindowBounds", "CapturedFrame", "NowPlayingSnapshot", "MidiPort", "MidiMessage", "AudioStream", "AudioCallback", "Kind"]
    - path: "src/vibemix/platform/audio.py"
      provides: "AudioBackend Protocol + AudioStream Protocol + AudioCallback type alias + Kind literal; zero OS imports"
      contains: "class AudioBackend"
    - path: "src/vibemix/platform/screen.py"
      provides: "ScreenBackend Protocol + WindowBounds + CapturedFrame frozen dataclasses; zero OS imports"
      contains: "class ScreenBackend"
    - path: "src/vibemix/platform/midi.py"
      provides: "MidiBackend Protocol + MidiPort Protocol + MidiMessage Protocol; zero OS imports"
      contains: "class MidiBackend"
    - path: "src/vibemix/platform/track.py"
      provides: "TrackInfoBackend Protocol + NowPlayingSnapshot frozen dataclass; zero OS imports"
      contains: "class TrackInfoBackend"
    - path: "tests/test_platform.py"
      provides: "Protocol introspection tests + OS-leak AST guard (fails if `Quartz`/`mss`/`mido`/`sounddevice`/`subprocess`/`winreg` appear in `src/vibemix/platform/*.py`)"
    - path: "tests/test_package.py"
      provides: "Import + version smoke tests"
    - path: "tests/test_license.py"
      provides: "LICENSE presence + Apache header check + SPDX-in-__init__ check"
    - path: "tests/test_signpath_checklist.py"
      provides: "Greps `.planning/signpath-application.md` for all 9 section headers"
    - path: ".planning/signpath-application.md"
      provides: "All 9 SignPath form sections prefilled with project data; KAAN-ONLY submission banner at top"
      contains: "KAAN-ONLY"
    - path: "docs/setup-github-repo.md"
      provides: "Exact `gh repo create ozzaii/vibemix --public ...` command + remote add + push instructions; KAAN-ONLY banner"
      contains: "ozzaii/vibemix"
  key_links:
    - from: "src/vibemix/platform/__init__.py"
      to: "src/vibemix/platform/{audio,screen,midi,track}.py"
      via: "from vibemix.platform.audio import AudioBackend, ..."
      pattern: "from vibemix\\.platform\\.(audio|screen|midi|track) import"
    - from: "pyproject.toml"
      to: "src/vibemix/"
      via: "[tool.hatch.build.targets.wheel] packages = [\"src/vibemix\"]"
      pattern: "packages = \\[\"src/vibemix\"\\]"
    - from: "tests/test_platform.py"
      to: "src/vibemix/platform/*.py"
      via: "AST scan for forbidden OS imports"
      pattern: "ast\\.parse"
    - from: ".planning/signpath-application.md"
      to: "github.com/ozzaii/vibemix"
      via: "Repository URL field references the public OSS repo Kaan creates this phase"
      pattern: "github\\.com/ozzaii/vibemix"
---

<objective>
Stand up the unified `vibemix` Python package skeleton with the four `platform/` Protocol firewall surfaces, Apache 2.0 license, `uv` + `hatchling` lockfile, and a prefilled SignPath OSS application checklist. Phase 1 is purely additive — POC files at the repo root stay untouched and continue to run via `run*.sh`.

Purpose:
- ARCH-01: gives all downstream phases (2-13) a stable `src/vibemix/` target to port POC logic into.
- ARCH-02: locks the OS-firewall shape so `_audio_macos.py` (Phase 2), `_screen_macos.py` (Phase 3), `_audio_windows.py` (Phase 7) etc. implement against four pre-defined Protocols rather than each phase reinventing the boundary.
- DIST-04: gets the SignPath Foundation OSS application filed on day 1 (~1 week approval) so the cert is ready by Phase 18 (installer signing).

Output: 14 files under version control (pyproject, lockfile, license, readme, gitignore, python-version, 5 package files, 4 protocol files, 5 test files, signpath checklist, repo-setup doc), public GitHub repo `ozzaii/vibemix` created (Kaan-only), SignPath OSS application filed (Kaan-only). All POC files untouched.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/codebase/CONVENTIONS.md
@.planning/codebase/STACK.md
@.planning/codebase/STRUCTURE.md
@.planning/research/PITFALLS.md
@.planning/phases/01-platform-protocol-firewall/01-CONTEXT.md
@.planning/phases/01-platform-protocol-firewall/01-RESEARCH.md
@.planning/phases/01-platform-protocol-firewall/01-PATTERNS.md

<key_corrections>
- **Repo URL is `https://github.com/ozzaii/vibemix`** (Kaan's personal account). RESEARCH.md and CONTEXT.md reference `bravoh/vibemix` in places — that is stale. Bravoh Enterprise has 0 orgs + a billing alert; org transfer deferred. Every artifact (signpath checklist, README, pyproject `[project.urls]`, docs/setup-github-repo.md) MUST use `ozzaii/vibemix`.
- **SignPath SLA is ~1 week** (verified by researcher via amd/gaia#732, April 2026). CONTEXT's "3 weeks" buffer is conservative — keep the day-1 application discipline.
- **POC files are off-limits** for Phase 1: `cohost.py`, `cohost_v2.py`, `cohost_lk.py`, `cohost_v3.py`, `cohost_v4.py`, `cohost.streaming.py.bak`, `run.sh`, `run_v2.sh`, `run_lk.sh`, `run_v3.sh`, `run_v4.sh`, `mascot.html`, `sprite-*.png`, `generate_bat.py`, `_test_*.py`, `test_voice.py`, `fillers/`. Do not modify, move, or rename any of these.
</key_corrections>

<interfaces>
<!-- Lifted from .planning/phases/01-platform-protocol-firewall/01-PATTERNS.md.
     The natural Protocol shape extracted from 21 POC call sites across cohost_v3.py / cohost_v2.py / cohost.py.
     PATTERNS.md is the load-bearing reference. Executor uses the shape below directly. -->

## AudioBackend (src/vibemix/platform/audio.py)
Imports allowed: `from __future__ import annotations`, `from typing import Callable, Literal, Protocol, runtime_checkable`. NOTHING ELSE.

- `Kind = Literal["input", "output"]`
- `AudioCallback = Callable[..., None]`  — sounddevice-shaped (indata, frames, time_info, status)
- `class AudioStream(Protocol)` — handle with `start()`, `stop()`, `close()`, `latency_ms` property
- `@runtime_checkable class AudioBackend(Protocol)`:
  - `find_device(self, name_substring: str, kind: Kind) -> int`
  - `open_capture(self, device_index: int, *, sample_rate: int, channels: int, block_size: int, callback: AudioCallback) -> AudioStream`
  - `open_passthrough_output(self, device_index: int, *, sample_rate: int, channels: int, block_size: int, callback: AudioCallback) -> AudioStream`
  - `open_voice_output(self, device_index: int, *, sample_rate: int, block_size: int, callback: AudioCallback) -> AudioStream`

Method bodies are `...`. Module docstring describes contract and references PATTERNS.md.

## ScreenBackend (src/vibemix/platform/screen.py)
Imports allowed: `__future__`, `dataclasses.dataclass`, `typing.Protocol`, `typing.runtime_checkable`.

- `@dataclass(frozen=True) class WindowBounds: x: int; y: int; width: int; height: int`
- `@dataclass(frozen=True) class CapturedFrame: jpeg: bytes; width: int; height: int`
- `@runtime_checkable class ScreenBackend(Protocol)`:
  - `is_available(self) -> bool`
  - `find_window_bounds(self, app_name_substring: str) -> WindowBounds | None`
  - `capture(self, bounds: WindowBounds | None, *, max_width: int = 1280, max_height: int = 800, jpeg_quality: int = 82) -> CapturedFrame`

## MidiBackend (src/vibemix/platform/midi.py)
Imports allowed: `__future__`, `typing.Protocol`, `typing.runtime_checkable`.

- `@runtime_checkable class MidiMessage(Protocol)` — structural: `type: str`, `channel: int`. Docstring notes mido-compatible attribute names (control/value or note/velocity per type) so POC decoders port wholesale.
- `@runtime_checkable class MidiPort(Protocol)`:
  - `name: str`
  - `poll(self) -> MidiMessage | None`
  - `close(self) -> None`
- `@runtime_checkable class MidiBackend(Protocol)`:
  - `list_input_ports(self) -> list[str]`
  - `open_input(self, port_name: str) -> MidiPort`

Docstring explicitly states: hot-plug re-enum is the caller's loop concern (2s cadence per POC); the Protocol does NOT push events.

## TrackInfoBackend (src/vibemix/platform/track.py)
Imports allowed: `__future__`, `dataclasses.dataclass`, `typing.Protocol`, `typing.runtime_checkable`.

- `@dataclass(frozen=True) class NowPlayingSnapshot: title: str | None; artist: str | None; album: str | None; duration_sec: float | None; position_sec: float | None`
- `@runtime_checkable class TrackInfoBackend(Protocol)`:
  - `is_available(self) -> bool`
  - `poll(self) -> NowPlayingSnapshot | None`

Docstring explicitly notes: macOS impl wraps nowplaying-cli; Windows impl wraps SMTC. `poll()` is sync/blocking — caller offloads to executor (POC pattern at cohost_v3.py:548).

## Forbidden inside Protocol files (`src/vibemix/platform/*.py`)
- `import sounddevice`
- `import mss`
- `from PIL import ...`
- `import mido`, `import python_rtmidi`, `import rtmidi`
- `import Quartz`, `import objc`, `from Foundation import ...`, `from AppKit import ...`
- `import subprocess`
- `import winreg`, `import win32*`
- `import numpy`, `import scipy` (Protocols are typing-only — leave numpy types out of Phase 1; Phase 2+ impls own those)
- Any side-effect-at-import (file I/O, network, subprocess.run)

The OS-leak test in `tests/test_platform.py` enforces this via AST scan.

## Naming + style
- `snake_case.py` filenames
- `PascalCase` Protocol class names — no `I*` or `*Interface` suffix
- `from __future__ import annotations` first
- Short prose docstrings, no Google/NumPy/Sphinx structure
- Method bodies are `...` (NOT `raise NotImplementedError` — idiomatic Protocol style per PEP 544)
- SPDX header `# SPDX-License-Identifier: Apache-2.0` first line of every `.py` in `src/vibemix/`
</interfaces>
</context>

<tasks>

<!-- ============================================================
     WAVE 1: Package skeleton + tooling foundation
     Outcome: `uv sync` succeeds, `uv run python -c "import vibemix"` works, LICENSE in place, .gitignore prevents the .env leak.
     Atomic commit at end: `feat(01): wave 1 — package skeleton + uv lockfile + license`
     ============================================================ -->

<task type="auto">
  <name>Task 1.1: Repo-root tooling files (.gitignore, LICENSE, .python-version, README, pyproject.toml)</name>
  <files>.gitignore, LICENSE, .python-version, README.md, pyproject.toml</files>
  <action>
Create the five repo-root tooling files. POC files at root MUST remain untouched throughout this task — only create new files; do not edit existing ones except `.gitignore` (overwrite the current 5-line one).

1. `.gitignore` — overwrite the existing file. Use the full Python + macOS + Windows + uv + vibemix-specific template from RESEARCH.md "Concrete Snippets / .gitignore" (the ~50-line block ending with `recordings/`, `*.wav`, `*.jsonl`). Critical lines: `.env`, `.env.*`, `!.env.example`, `.venv/`, `__pycache__/`, `*.pyc`, `dist/`, `build/`, `*.egg-info/`, `.uv/`, `.ruff_cache/`, `.pytest_cache/`, `.DS_Store`, `Thumbs.db`, `recordings/`, `*.wav`, `*.jsonl`. This implements Pitfall P3 mitigation (API key leakage).

2. `LICENSE` — verbatim Apache License 2.0 text. Download from https://www.apache.org/licenses/LICENSE-2.0.txt OR copy the canonical text. After the standard appendix, include the copyright line:
   ```
      Copyright 2026 Bravoh / Kaan Özkan
   ```
   File must start with `                                 Apache License` (the standard heading).

3. `.python-version` — single line: `3.12`. This is uv's interpreter pin per RESEARCH.md decision (Open Question 5 recommendation — `uv python install 3.12` auto-fetches).

4. `README.md` — minimal placeholder per RESEARCH.md "Concrete Snippets / README.md". Five sections, ~150 words: title, one-line tagline, "Status: Pre-release. Building toward early-June 2026 launch alongside [Bravoh](https://altidus.world).", License line linking `./LICENSE`, Platforms line ("macOS + Windows. Linux not supported."), "More to come." Expanded in Phase 19; do NOT add hero banner, demo GIF, install buttons, FAQ, or controller grid here.

5. `pyproject.toml` — full block from RESEARCH.md "Concrete Snippets / pyproject.toml". Use these exact values:
   - `[project] name = "vibemix"`, `version = "0.1.0-dev0"`, `requires-python = ">=3.12,<3.13"`
   - `description = "Open-source AI DJ co-host. Listens, watches, talks back."`
   - `authors = [{ name = "Kaan Özkan", email = "oozzxaaii@gmail.com" }]`
   - `license = { file = "LICENSE" }`
   - `[project.urls]` Homepage / Repository / Issues ALL pointing at `https://github.com/ozzaii/vibemix` (NOT `bravoh/vibemix` — CONTEXT/RESEARCH stale on this; user correction is binding)
   - `[project] dependencies` — full STACK.md list pinned per RESEARCH.md (google-genai>=2.0.1, livekit-agents>=1.5.8, livekit-plugins-google>=1.5.8, livekit>=1.1.7, numpy>=2.4.4, scipy>=1.17.1, sounddevice>=0.5.5, mido>=1.3.3, python-rtmidi>=1.5.8, mss>=10.2.0, pillow>=12.2.0, websockets>=16.0, python-dotenv>=1.2.2, pyobjc-core/Cocoa/Quartz>=12.1 with `sys_platform == 'darwin'` markers)
   - `[dependency-groups] dev = ["ruff>=0.7", "pytest>=8.0"]`
   - `[build-system] requires = ["hatchling"]`, `build-backend = "hatchling.build"`
   - `[tool.hatch.build.targets.wheel] packages = ["src/vibemix"]`
   - `[tool.ruff]` with `target-version = "py312"`, `line-length = 100`, `src = ["src"]`
   - `[tool.ruff.lint] select = ["E4", "E7", "E9", "F", "B", "I", "UP", "RUF"]`, `ignore = ["E501"]`
   - `[tool.ruff.lint.per-file-ignores]` exempting `cohost*.py`, `_test_*.py`, `test_voice.py` from all rules (POC files are reference, not ported yet)
   - `[tool.ruff.format] quote-style = "double"`, `indent-style = "space"`, `docstring-code-format = true`
   - `[tool.pytest.ini_options] testpaths = ["tests"]`, `addopts = "-ra --strict-markers"`

Do NOT execute `uv sync` or `uv lock` in this task — that's Task 1.3. This task is purely file creation.
  </action>
  <verify>
    <automated>test -f .gitignore && test -f LICENSE && test -f .python-version && test -f README.md && test -f pyproject.toml && grep -q "ozzaii/vibemix" pyproject.toml && grep -q "Apache License" LICENSE && grep -q "^3.12" .python-version && grep -q "0.1.0-dev0" pyproject.toml && grep -qE "^\.env$" .gitignore && grep -q "^!\.env\.example" .gitignore</automated>
  </verify>
  <done>Five files exist with the specified content. pyproject.toml uses `ozzaii/vibemix` everywhere. LICENSE is full Apache 2.0 text. .gitignore excludes `.env` with the `!.env.example` carve-out. No POC file modified.</done>
</task>

<task type="auto">
  <name>Task 1.2: Package source files (src/vibemix/__init__.py + py.typed)</name>
  <files>src/vibemix/__init__.py, src/vibemix/py.typed</files>
  <action>
Create the src-layout root.

1. `src/vibemix/__init__.py`:
   ```
   # SPDX-License-Identifier: Apache-2.0
   """vibemix — open-source AI DJ co-host.

   Listens to your master output, watches your DJ software, ingests controller actions,
   and talks back. macOS + Windows. Apache 2.0.
   """

   __version__ = "0.1.0-dev0"
   ```
   First line is the SPDX header. Module docstring is short prose (no Google/NumPy structure) per CONVENTIONS.md. Single export: `__version__`.

2. `src/vibemix/py.typed` — EMPTY file (zero bytes). PEP 561 marker. Hatchling auto-includes any file under the package tree in the wheel, so no extra config needed (per RESEARCH.md P0-2).

Do NOT add any imports beyond what's shown. Do NOT add a `platform/` re-export from `__init__.py` — that's Task 2.1's `platform/__init__.py` job, and `__init__.py` should stay zero-import to keep `import vibemix` cheap.
  </action>
  <verify>
    <automated>test -f src/vibemix/__init__.py && test -f src/vibemix/py.typed && [ ! -s src/vibemix/py.typed ] && head -1 src/vibemix/__init__.py | grep -q "SPDX-License-Identifier: Apache-2.0" && grep -q '__version__ = "0.1.0-dev0"' src/vibemix/__init__.py</automated>
  </verify>
  <done>`src/vibemix/__init__.py` exists with SPDX header + version. `src/vibemix/py.typed` is an empty file.</done>
</task>

<task type="auto">
  <name>Task 1.3: Materialise uv environment + lockfile + smoke-test import</name>
  <files>uv.lock, .venv/ (regenerated)</files>
  <action>
Run uv to install Python 3.12 + the declared deps + generate the committed lockfile.

Pre-flight: delete the existing `.venv/` if present (it was created on Python 3.14 per CLAUDE.md; we're switching to 3.12 per CONTEXT decision). Run:

```bash
rm -rf .venv
uv python install 3.12       # idempotent; no-op if 3.12 already installed
uv sync                      # materialises .venv on 3.12, generates uv.lock from pyproject.toml deps
```

If `uv sync` fails with a wheel-availability error on any pinned dep, capture the failing package + version from stderr, note it in the SUMMARY draft for Kaan, and bump the pin to the closest version that has a Python 3.12 wheel (RESEARCH.md Assumption A4/A5 flagged this risk for `pyobjc-framework-Quartz>=12.1` and `livekit-agents>=1.5.8`). If multiple deps need bumping, prefer rolling back the minimum version rather than dropping the dep.

After `uv sync` succeeds, run the import smoke-test:

```bash
uv run python -c "import vibemix; print(vibemix.__version__)"
```

Expected output: `0.1.0-dev0` exactly.

Commit `uv.lock` to git. Do NOT commit `.venv/` (it's in `.gitignore`).
  </action>
  <verify>
    <automated>uv sync --frozen && uv run python -c "import vibemix; assert vibemix.__version__ == '0.1.0-dev0', vibemix.__version__; print('OK')" | grep -q "OK"</automated>
  </verify>
  <done>`.venv/` exists on Python 3.12; `uv.lock` committed; `import vibemix` prints `0.1.0-dev0`.</done>
</task>

<!-- ============================================================
     WAVE 2: Platform Protocol definitions
     Outcome: `from vibemix.platform import AudioBackend, ScreenBackend, MidiBackend, TrackInfoBackend` succeeds; every Protocol is `@runtime_checkable`; zero OS-specific imports in the platform/ tree.
     Atomic commit at end: `feat(01): wave 2 — typing.Protocol firewall (AudioBackend / ScreenBackend / MidiBackend / TrackInfoBackend)`
     ============================================================ -->

<task type="auto">
  <name>Task 2.1: Four Protocol modules + platform/__init__.py re-exports</name>
  <files>src/vibemix/platform/__init__.py, src/vibemix/platform/audio.py, src/vibemix/platform/screen.py, src/vibemix/platform/midi.py, src/vibemix/platform/track.py</files>
  <action>
Create the four Protocol files plus the package re-export hub. Every file MUST start with the SPDX header `# SPDX-License-Identifier: Apache-2.0` and `from __future__ import annotations`. Use the natural shape from `<interfaces>` above (lifted verbatim from PATTERNS.md). Method bodies are `...` — NOT `raise NotImplementedError`, NOT `pass`. Docstrings are short prose (no Google/NumPy/Sphinx structure) per CONVENTIONS.md.

1. `src/vibemix/platform/audio.py`:
   - SPDX header + `from __future__ import annotations` + module docstring
   - Imports: ONLY `from typing import Callable, Literal, Protocol, runtime_checkable`
   - `Kind = Literal["input", "output"]`
   - `AudioCallback = Callable[..., None]` with comment line above explaining it mirrors sounddevice signature `(indata, frames, time_info, status)`
   - `class AudioStream(Protocol):` with methods `start()`, `stop()`, `close()` returning `None` and `latency_ms: float` as a `@property`. NOT `@runtime_checkable` (AudioStream is a return-value handle; only the top-level backend needs runtime checking)
   - `@runtime_checkable class AudioBackend(Protocol):` with `find_device`, `open_capture`, `open_passthrough_output`, `open_voice_output` exactly as in `<interfaces>` (kwarg-only after `device_index` for sample_rate/channels/block_size/callback)
   - Module docstring references PATTERNS.md call sites: "Lifted from cohost_v3.py:873-927 (start_input_capture) / cohost.py:479-528 (passthrough + playback) / cohost.py:139-148 (find_device). Phase 2 macOS impl + Phase 7 Windows impl satisfy this Protocol."

2. `src/vibemix/platform/screen.py`:
   - SPDX header + `from __future__ import annotations` + module docstring referencing `cohost_v3.py:194-216` (Quartz find_djay_window_bounds) and `cohost_v3.py:947-965` (mss grab + PIL crop)
   - Imports: ONLY `from dataclasses import dataclass` + `from typing import Protocol, runtime_checkable`
   - `@dataclass(frozen=True) class WindowBounds: x: int; y: int; width: int; height: int`
   - `@dataclass(frozen=True) class CapturedFrame: jpeg: bytes; width: int; height: int`
   - `@runtime_checkable class ScreenBackend(Protocol):` with `is_available()`, `find_window_bounds(app_name_substring)`, `capture(bounds, *, max_width=1280, max_height=800, jpeg_quality=82)`. Return types: `bool`, `WindowBounds | None`, `CapturedFrame`
   - `is_available()` docstring: "Replaces the POC's module-level `_HAS_VISION` / `_HAS_QUARTZ` flags (cohost_v3.py:47-62). Callers branch on this, never on imported module state."

3. `src/vibemix/platform/midi.py`:
   - SPDX header + `from __future__ import annotations` + module docstring referencing `cohost_v3.py:704-730` (midi_listener_thread) and PITFALLS P11 (hot-plug)
   - Imports: ONLY `from typing import Protocol, runtime_checkable`
   - `@runtime_checkable class MidiMessage(Protocol):` with `type: str` and `channel: int` as attribute annotations. Docstring: "Structural minimum of a MIDI message; mido.Message satisfies this. Backends MUST emit messages whose attribute names match mido (`control`/`value` for type=='control_change', `note`/`velocity` for type in {'note_on','note_off'}) so POC decoders port wholesale."
   - `@runtime_checkable class MidiPort(Protocol):` with `name: str` attribute, `poll() -> MidiMessage | None`, `close() -> None`
   - `@runtime_checkable class MidiBackend(Protocol):` with `list_input_ports() -> list[str]` and `open_input(port_name: str) -> MidiPort`
   - Class docstring on `MidiBackend`: "Hot-plug rescan is the caller's concern — the caller re-invokes `list_input_ports()` on a ~2s cadence (POC pattern at cohost_v3.py:720-728). The backend does NOT push events."
   - Explicit anti-pattern note in module docstring: "`ControllerState`, `deck_snapshot()`, `moves_since()`, and DDJ-specific CC/Note maps belong to the controller-profile abstraction in Phase 9, NOT this Protocol."

4. `src/vibemix/platform/track.py`:
   - SPDX header + `from __future__ import annotations` + module docstring referencing `cohost_v3.py:518-541` (nowplaying-cli subprocess poll) and `cohost_v3.py:1112-1133` (derive_audible_track sensing logic, explicitly NOT on this Protocol)
   - Imports: ONLY `from dataclasses import dataclass` + `from typing import Protocol, runtime_checkable`
   - `@dataclass(frozen=True) class NowPlayingSnapshot:` with five `| None` fields: `title: str | None`, `artist: str | None`, `album: str | None`, `duration_sec: float | None`, `position_sec: float | None`. Docstring: "All fields best-effort; backends MUST set unknown fields to None (not empty string) so callers can distinguish 'no track' from 'track with no title'."
   - `@runtime_checkable class TrackInfoBackend(Protocol):` with `is_available() -> bool` and `poll() -> NowPlayingSnapshot | None`
   - Method docstring on `poll`: "Synchronous + blocking. Caller offloads to executor (POC pattern at cohost_v3.py:548). Returns None when no track is currently reported by the OS now-playing surface."

5. `src/vibemix/platform/__init__.py`:
   - SPDX header + module docstring describing the firewall (lift from RESEARCH.md "Concrete Snippets / src/vibemix/platform/__init__.py")
   - Imports: re-export from each sibling module
     - `from vibemix.platform.audio import AudioBackend, AudioStream, AudioCallback, Kind`
     - `from vibemix.platform.screen import ScreenBackend, WindowBounds, CapturedFrame`
     - `from vibemix.platform.midi import MidiBackend, MidiPort, MidiMessage`
     - `from vibemix.platform.track import TrackInfoBackend, NowPlayingSnapshot`
   - `__all__` listing every name exported (12 total: 4 backends, AudioStream, AudioCallback, Kind, WindowBounds, CapturedFrame, MidiPort, MidiMessage, NowPlayingSnapshot)

Use `<interfaces>` block above as the authoritative shape — do not paraphrase the method names or argument order. After writing, run `uv run ruff format src/vibemix/platform/` to normalise quote style + indent.

**Forbidden imports in any of these five files** (test_platform.py enforces): `sounddevice`, `mss`, `PIL`, `Pillow`, `mido`, `rtmidi`, `python_rtmidi`, `Quartz`, `objc`, `Foundation`, `AppKit`, `subprocess`, `winreg`, any `win32*` module, `numpy`, `scipy`. These are concrete-impl concerns (Phase 2+).
  </action>
  <verify>
    <automated>uv run python -c "from vibemix.platform import AudioBackend, ScreenBackend, MidiBackend, TrackInfoBackend, WindowBounds, CapturedFrame, NowPlayingSnapshot, MidiPort, MidiMessage, AudioStream, AudioCallback, Kind; from typing import runtime_checkable; assert runtime_checkable(AudioBackend) is AudioBackend; assert runtime_checkable(ScreenBackend) is ScreenBackend; assert runtime_checkable(MidiBackend) is MidiBackend; assert runtime_checkable(TrackInfoBackend) is TrackInfoBackend; assert isinstance(object(), AudioBackend) is False; print('OK')" | grep -q "OK"</automated>
  </verify>
  <done>All five files exist. The 12 public names import successfully. Each of the four top-level Backend Protocols is `@runtime_checkable`. `isinstance(object(), AudioBackend) is False` (Protocol enforces structural shape — bare object fails). No OS-specific module gets pulled in by `import vibemix.platform`.</done>
</task>

<!-- ============================================================
     WAVE 3: Test scaffold + OS-leak guard + SignPath checklist + repo setup doc
     Outcome: Test suite enforces the must-haves; SignPath application is ready for Kaan to submit; Kaan has a recipe for creating the GitHub repo.
     Atomic commit at end: `feat(01): wave 3 — tests + signpath checklist + repo setup doc`
     ============================================================ -->

<task type="auto">
  <name>Task 3.1: Test scaffold (tests/__init__.py, conftest.py, test_package.py, test_platform.py, test_license.py, test_signpath_checklist.py)</name>
  <files>tests/__init__.py, tests/conftest.py, tests/test_package.py, tests/test_platform.py, tests/test_license.py, tests/test_signpath_checklist.py</files>
  <action>
Create the pytest scaffold. `pytest>=8.0` was added to `[dependency-groups] dev` in Task 1.1 and installed in Task 1.3. Tests run via `uv run pytest`.

1. `tests/__init__.py` — EMPTY file (signals to pytest that tests/ is a package).

2. `tests/conftest.py` — single line module docstring `"""Shared pytest fixtures for vibemix Phase 1 smoke tests."""` and nothing else. Fixtures land in later phases.

3. `tests/test_package.py` — two tests:
   - `def test_import_succeeds():` — `import vibemix; assert vibemix is not None`
   - `def test_version():` — `import vibemix; assert vibemix.__version__ == "0.1.0-dev0"`

4. `tests/test_platform.py` — four tests, the OS-leak guard is the critical one:
   - `def test_protocols_exported():` — `from vibemix.platform import AudioBackend, ScreenBackend, MidiBackend, TrackInfoBackend` succeeds (one import line, no asserts needed — ImportError fails the test).
   - `def test_value_dataclasses_exported():` — same for `WindowBounds`, `CapturedFrame`, `NowPlayingSnapshot`, `MidiPort`, `MidiMessage`, `AudioStream`, `AudioCallback`, `Kind`.
   - `def test_runtime_checkable():` — for each of the 4 top-level Backend Protocols, assert `isinstance(object(), Backend) is False` AND `runtime_checkable(Backend) is Backend`. Imports from `typing` and `vibemix.platform`.
   - `def test_protocol_surface():` — introspect that each Backend Protocol has the required method names as class-level attributes. For `AudioBackend`: `{"find_device", "open_capture", "open_passthrough_output", "open_voice_output"}` ⊆ `set(dir(AudioBackend))`. For `ScreenBackend`: `{"is_available", "find_window_bounds", "capture"}`. For `MidiBackend`: `{"list_input_ports", "open_input"}`. For `TrackInfoBackend`: `{"is_available", "poll"}`.
   - `def test_no_os_leaks():` — THE LOAD-BEARING TEST. AST-parse every `.py` file under `src/vibemix/platform/`, walk every `ast.Import` / `ast.ImportFrom` node, fail if any imports a forbidden module. Forbidden module set (case-sensitive top-level names):
     ```python
     FORBIDDEN = {
         "sounddevice", "mss", "PIL", "Pillow",
         "mido", "rtmidi", "python_rtmidi",
         "Quartz", "objc", "Foundation", "AppKit",
         "subprocess", "winreg",
         "numpy", "scipy",
     }
     # Plus any module starting with "win32"
     ```
     For `ast.ImportFrom`, check `node.module.split(".")[0]`. For `ast.Import`, iterate `node.names` and check each `alias.name.split(".")[0]`. Plus `if name.startswith("win32"): fail`. Use `pathlib.Path("src/vibemix/platform").glob("*.py")`. Assert with helpful failure message: `f"{file}:{node.lineno}: forbidden import {name}"`.

5. `tests/test_license.py` — two tests:
   - `def test_license_apache_2_0():` — assert `Path("LICENSE").exists()`, then `"Apache License" in Path("LICENSE").read_text()` and `"Version 2.0" in Path("LICENSE").read_text()`.
   - `def test_spdx_header_in_init():` — first line of `src/vibemix/__init__.py` is `# SPDX-License-Identifier: Apache-2.0`.

6. `tests/test_signpath_checklist.py` — one test:
   - `def test_signpath_checklist_complete():` — read `.planning/signpath-application.md`, assert all 9 section headers are present. Section markers (case-insensitive substring match): `"1. Basic"`, `"2. Repo"`, `"3. Distribution"`, `"4. Privacy"`, `"5. Wikipedia"`, `"6. Trust"` (or `"Verification"`), `"7. Technical"`, `"8. Contact"`, `"9. Terms"`. Also assert `"ozzaii/vibemix"` appears in the file (sanity check: repo URL correctly threaded through).

After writing, run `uv run pytest -x` and confirm green. Then run `uv run ruff check src/ tests/` and `uv run ruff format --check src/ tests/`. If ruff complains, run `uv run ruff format src/ tests/` to normalise.
  </action>
  <verify>
    <automated>uv run pytest -x -q && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/</automated>
  </verify>
  <done>Six test files exist. `uv run pytest -x` passes all tests (8 total: 2 package, 5 platform including no_os_leaks AST scan, 2 license, 1 signpath). Ruff lint and format check both clean on src/ + tests/.</done>
</task>

<task type="auto">
  <name>Task 3.2: SignPath application checklist + GitHub repo setup doc</name>
  <files>.planning/signpath-application.md, docs/setup-github-repo.md</files>
  <action>
Produce the two Kaan-facing documentation artifacts. Both are reference material — the actual submission (SignPath form) and the actual `gh repo create` invocation are Kaan-only manual steps flagged in Wave 4.

**1. `.planning/signpath-application.md`** — full SignPath OSS application reference. Structure:

```markdown
# SignPath Foundation OSS Application — vibemix

> **KAAN-ONLY:** This file is the field-by-field reference for the SignPath OSS application form.
> Submission URL: https://signpath.io/solutions/open-source-community
> SLA: ~1 week approval (per amd/gaia#732, April 2026 — single recent data point; CONTEXT.md's 3-week buffer is conservative).
> Apply on day 1 of Phase 1 so the cert is ready by Phase 18 (installer signing).
> **Claude cannot submit forms with personal/business info — Kaan files this manually.**
```

Then nine `##` sections matching the form. Use the table from RESEARCH.md "SignPath OSS application checklist" as authoritative values. **Critical: every URL/repo reference uses `https://github.com/ozzaii/vibemix`, NEVER `bravoh/vibemix`.** Substitute throughout.

Sections (use the exact field values from the RESEARCH.md table):
- `## 1. Basic Information` — project name `vibemix`, short name `vibemix`, homepage `https://github.com/ozzaii/vibemix`, brief description, detailed description (1 paragraph from PROJECT.md describing the AI DJ co-host), license `Apache 2.0`, license URL `https://github.com/ozzaii/vibemix/blob/main/LICENSE`, languages `Python, JavaScript, HTML/CSS`.
- `## 2. Repository Information` — repo type Git, URL `https://github.com/ozzaii/vibemix`, contributor count 1 (Kaan; note Bravoh team joining post-launch), commit count "(fill at submission time)", project age `< 1 week at submission`, dev status `Alpha / pre-release`.
- `## 3. Distribution & Downloads` — download page `https://github.com/ozzaii/vibemix/releases` (will exist post-Phase 18), formats `Windows MSI installer, macOS DMG`, distribution `Direct download from GitHub Releases`, total downloads `0 — pre-release, signed binaries pending SignPath approval`, monthly downloads `0`. **Add explicit framing paragraph:** "Section 3 candor — vibemix is pre-release. The application is filed referencing **expected** future artifacts. If SignPath defers approval until binaries exist, we resubmit at Phase 11–13 once a usable pre-release binary is in `dist/`. The 3-week CONTEXT buffer absorbs this risk."
- `## 4. Privacy Policy` — Yes data is transmitted (DJ-window screenshot, master-audio PCM snapshots, MIDI events, OS now-playing track title), destination Google Gemini API via Bravoh-side proxy (Phase 5 — raw key never leaves server), privacy policy URL "Phase 19 deliverable — link to README privacy section as placeholder until then".
- `## 5. Wikipedia Article` — N/A; justification "Pre-release project < 1 month from launch — Wikipedia notability not yet established."
- `## 6. Verification & Trust Evidence` — Maintainer is founder of Bravoh (https://altidus.world), Bravoh closed-beta launching March 2026, team (Musa senior dev, Yasin dev) joining as contributors post-launch. Media/blog: "Launch coverage planned via IG ads + DJ network outreach (Francesco cofounder driving)." GitHub insights: "Fill star/fork counts at submission." Trademark: "Bravoh trademark owned by founding entity."
- `## 7. Technical Details` — What will be signed: Windows MSI wrapping PyInstaller `--onedir` payload + macOS DMG (notarized .app bundle). File types: `.msi`, `.exe` (PyInstaller bootstrap inside MSI), `.dmg`, `.app`. Signing frequency: per release — initial v1.0 + ~monthly patch releases. Build process: GitHub Actions on tag push (Phase 20) — artifact uploaded to SignPath, signed binary returned, attached to GitHub Release. CI/CD: GitHub Actions via SignPath's official action.
- `## 8. Contact Information` — Primary name `Kaan Özkan`, email `oozzxaaii@gmail.com`, maintainers `Kaan Özkan (primary); Musa, Yasin (Bravoh — post-launch)`, GitHub org/user `ozzaii (personal account; transfer to bravoh org deferred — see note below)`, additional contacts `Francesco — Bravoh cofounder, marketing/product`.
- `## 9. Terms & Conditions` — Three checkboxes for Kaan to confirm at submission. Note: "Apache 2.0 is OSI-approved and qualifies. No commercial dual-licensing."

End with a `## Submission Notes for Kaan` section listing the three sharp edges: Section 3 weak point, Section 6 needs Bravoh footprint leading, Section 4 privacy policy URL placeholder. Plus the `bravoh` org transfer note: "Bravoh Enterprise has 0 orgs and a billing flag. Repo lives at `ozzaii/vibemix` for now; can be transferred via `gh repo transfer` once a proper `bravoh` org is stood up. SignPath survives a rename without re-approval."

**2. `docs/setup-github-repo.md`** — repo creation recipe. Structure:

```markdown
# Setup: GitHub Repo Creation (Phase 1, Kaan-only)

> **KAAN-ONLY:** Creating the public repo requires `gh` auth as Kaan and cannot be automated.
> This file is the recipe to run from the repo root after Phase 1's Wave 3 commit lands locally.

## Preconditions
- `gh auth status` shows authenticated as `ozzaii`.
- `git status` is clean (Phase 1 commits already exist locally).
- `pwd` is `/Users/ozai/projects/dj-set-ai`.

## Commands

\`\`\`bash
# 1. Verify current state
gh auth status
git log --oneline -10

# 2. Create the public repo + push initial Phase 1 commits in one shot
gh repo create ozzaii/vibemix \
    --public \
    --source=. \
    --remote=origin \
    --push \
    --description "Open-source AI DJ co-host. Listens, watches, talks back."

# 3. Verify it landed
gh repo view ozzaii/vibemix --web
\`\`\`

## What this does
- `--source=.` uses local files as the seed (LICENSE, README.md, pyproject.toml, src/, etc. — all already committed locally).
- `--public` is required by SignPath OSS eligibility (Apache 2.0 license + public repo).
- `--push` automatically pushes all local commits to the new remote.
- Skips `--add-readme` / `--license` / `--gitignore` because those generate files on the GitHub side, conflicting with `--source=.`.

## Bravoh-org transfer (deferred — NOT done in Phase 1)
Bravoh Enterprise has 0 orgs and a billing alert. Once a proper `bravoh` GitHub org is stood up:
\`\`\`bash
gh api repos/ozzaii/vibemix/transfer -F new_owner=bravoh
\`\`\`
SignPath survives a rename/transfer without re-approval (per their terms).

## Next steps after repo creation
- File the SignPath OSS application (see `.planning/signpath-application.md`).
- Verify the LICENSE displays correctly on GitHub.
- Add the repo URL to the SignPath form's Section 2 (Repository).
\`\`\`

Use backticks-and-backslash-escapes inside the markdown so the file is itself valid. After writing, run `cat docs/setup-github-repo.md | grep -c "ozzaii/vibemix"` and confirm at least 4 hits.
  </action>
  <verify>
    <automated>test -f .planning/signpath-application.md && test -f docs/setup-github-repo.md && grep -c "ozzaii/vibemix" .planning/signpath-application.md | awk '$1>=5{exit 0} {exit 1}' && grep -q "KAAN-ONLY" .planning/signpath-application.md && grep -q "KAAN-ONLY" docs/setup-github-repo.md && grep -q "gh repo create ozzaii/vibemix" docs/setup-github-repo.md && uv run pytest tests/test_signpath_checklist.py -x -q</automated>
  </verify>
  <done>Both files exist. SignPath checklist contains all 9 sections, every github URL is `ozzaii/vibemix`, and has the KAAN-ONLY banner. Repo setup doc contains the exact `gh repo create ozzaii/vibemix` command with the KAAN-ONLY banner. `test_signpath_checklist.py` passes.</done>
</task>

<!-- ============================================================
     WAVE 4: Verification gates + Kaan-only manual steps + phase summary + commit
     One human-verify checkpoint surfaces the two Kaan-only tasks (repo create + SignPath submit).
     ============================================================ -->

<task type="auto">
  <name>Task 4.1: Run full Phase 1 verification gate</name>
  <files>(no files modified — verification only)</files>
  <action>
Run every must-have verification check sequentially. If any fails, stop and surface the failure. All must pass before the human-verify checkpoint in Task 4.2.

Checks (run each, capture pass/fail):

1. **Files exist count:** `find src/vibemix -name "*.py" -not -path "*/__pycache__/*" | wc -l` returns >= 6 (init.py, py.typed isn't .py but counts via separate check, platform/__init__.py, audio.py, screen.py, midi.py, track.py = 6). Run also `test -f src/vibemix/py.typed`.

2. **Lockfile reproducibility:** `uv lock --check` exits 0 (lockfile matches pyproject.toml).

3. **Linter:** `uv run ruff check src/ tests/` exits 0. POC files at root are excluded via `[tool.ruff.lint.per-file-ignores]` — confirm they don't trigger errors either by running `uv run ruff check .` and verifying only no errors or only ignored categories surface.

4. **Formatter:** `uv run ruff format --check src/ tests/` exits 0.

5. **Test suite:** `uv run pytest -x -q` exits 0 with all 8 tests passing.

6. **Protocol introspection (positive):** `uv run python -c "from typing import runtime_checkable; from vibemix.platform import AudioBackend, ScreenBackend, MidiBackend, TrackInfoBackend; assert all(runtime_checkable(p) is p for p in [AudioBackend, ScreenBackend, MidiBackend, TrackInfoBackend]); print('runtime_checkable: OK')"`.

7. **OS-leak guard (defence-in-depth, beyond the AST test):** `grep -v '^#' src/vibemix/platform/*.py | grep -Ev '^[^:]+:[[:space:]]*$' | grep -E "import (sounddevice|mss|PIL|mido|rtmidi|Quartz|objc|Foundation|AppKit|subprocess|winreg|win32|numpy|scipy)" | grep -v "from typing import" | grep -c "" | awk '$1==0{exit 0} {exit 1}'` — count must be 0. (The leading `grep -v '^#'` strips comments so docstring/header prose mentioning forbidden module names does not self-invalidate the gate.)

8. **POC untouched:** `git diff --name-only main..HEAD 2>/dev/null | grep -E "^(cohost.*\\.py|run.*\\.sh|mascot\\.html|sprite-.*\\.png|generate_bat\\.py|_test_.*\\.py|test_voice\\.py)$"` returns empty (no POC files in Phase 1 diff). Note: this depends on whether `main` is HEAD at start — adapt to compare against the pre-Phase-1 baseline.

9. **SignPath checklist completeness:** `uv run pytest tests/test_signpath_checklist.py -x -q` exits 0.

10. **Reproducibility from scratch (capstone):** Run in a temp shell:
    ```bash
    rm -rf .venv
    uv sync --frozen
    uv run python -c "import vibemix; from vibemix.platform import AudioBackend, ScreenBackend, MidiBackend, TrackInfoBackend; print('reproducible:', vibemix.__version__)"
    ```
    Expected: prints `reproducible: 0.1.0-dev0`. If this fails, the lockfile is broken — fix before proceeding.

Capture each result in a brief running tally for the SUMMARY.md draft (Task 4.3 consumes this). If any check fails, halt and surface the failure to the orchestrator with the specific check number and error output.
  </action>
  <verify>
    <automated>uv lock --check && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run pytest -x -q && uv run python -c "from typing import runtime_checkable; from vibemix.platform import AudioBackend, ScreenBackend, MidiBackend, TrackInfoBackend; assert all(runtime_checkable(p) is p for p in [AudioBackend, ScreenBackend, MidiBackend, TrackInfoBackend])" && [ $(find src/vibemix -name "*.py" -not -path "*/__pycache__/*" | wc -l) -ge 6 ] && test -f src/vibemix/py.typed && (rm -rf .venv && uv sync --frozen && uv run python -c "import vibemix; assert vibemix.__version__ == '0.1.0-dev0'")</automated>
  </verify>
  <done>All 10 verification checks pass. Phase 1's automatable scope is fully green.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 4.2: Kaan-only — create public repo + file SignPath application</name>
  <files>(no files modified by Claude — Kaan-only manual steps; reference artifacts: docs/setup-github-repo.md, .planning/signpath-application.md)</files>
  <action>
Pause for Kaan to complete two manual steps that Claude cannot automate (gh auth + SignPath form submission). Surface the prefilled artifacts (`docs/setup-github-repo.md` and `.planning/signpath-application.md`) and the verification steps below to Kaan, then wait for the resume signal before proceeding to Task 4.3.

Do NOT skip ahead. Do NOT attempt to create the repo or submit the SignPath form yourself — both require Kaan's credentials and personal judgment.
  </action>
  <what-built>
Phase 1 is automatable-complete. Two Kaan-only manual steps remain before Phase 1 ships fully:

1. **Public GitHub repo creation** — `gh` is authenticated as `ozzaii`, and creating the repo cannot be automated by Claude (it would require Kaan's credentials and judgment on the repo description / settings).
2. **SignPath OSS application submission** — the form at signpath.io/solutions/open-source-community requires personal info + checkbox confirmations; Claude cannot submit forms on Kaan's behalf.

All field references for both steps are prefilled in artifacts:
- `docs/setup-github-repo.md` — exact `gh repo create` command.
- `.planning/signpath-application.md` — all 9 SignPath form sections prefilled.
  </what-built>
  <how-to-verify>
Step A — Create the public repo:
1. Open a terminal at `/Users/ozai/projects/dj-set-ai`.
2. Read `docs/setup-github-repo.md` and run the `gh repo create ozzaii/vibemix --public --source=. --remote=origin --push --description "Open-source AI DJ co-host. Listens, watches, talks back."` command.
3. Verify with `gh repo view ozzaii/vibemix --web` — the repo loads, shows LICENSE + README + pyproject.toml.
4. Confirm the `origin` remote is set: `git remote -v` shows `git@github.com:ozzaii/vibemix.git` (or https equivalent).

Step B — File the SignPath application:
1. Open `.planning/signpath-application.md` in an editor or markdown viewer.
2. Navigate to https://signpath.io/solutions/open-source-community.
3. Copy each section's prefilled values into the corresponding form fields. Pay extra attention to:
   - **Section 3 (Distribution)** — be candid about pre-release status; flag in the cover note that signed binaries are expected ~3 weeks out (Phase 18).
   - **Section 4 (Privacy)** — the privacy policy URL is a placeholder (Phase 19 deliverable). Use the README link until then.
   - **Section 6 (Trust)** — lead with Bravoh's existing footprint (altidus.world, closed beta, founding team) as the strongest day-1 signal.
4. Submit the form.
5. Confirm the confirmation email arrives in `oozzxaaii@gmail.com`.

Step C — Optional (deferred to a later milestone; NOT a Phase 1 blocker):
1. Sort out Bravoh Enterprise billing.
2. Create a proper `bravoh` GitHub org.
3. Run `gh api repos/ozzaii/vibemix/transfer -F new_owner=bravoh` (SignPath survives the rename).

After Steps A and B are both done, type `approved`. If anything fails — auth issue, SignPath rejection on Section 3, etc. — paste the error and we'll iterate. Step C can wait.
  </how-to-verify>
  <verify>
    <automated>MISSING — this is a checkpoint:human-verify task; verification is the human steps A + B in &lt;how-to-verify&gt; above. Resumption is gated on Kaan typing "approved".</automated>
  </verify>
  <done>Kaan has typed `approved` (or equivalent). `gh repo view ozzaii/vibemix --web` shows the public repo with LICENSE + README + pyproject.toml. SignPath confirmation email present in oozzxaaii@gmail.com.</done>
  <resume-signal>Type "approved" once Steps A + B are complete, or describe what blocked.</resume-signal>
</task>

<task type="auto">
  <name>Task 4.3: Write phase SUMMARY.md + final commit</name>
  <files>.planning/phases/01-platform-protocol-firewall/01-SUMMARY.md</files>
  <action>
Write the phase SUMMARY using the GSD summary template structure. Include:

- **Phase:** 01-platform-protocol-firewall
- **Plan:** 01
- **Requirements covered:** ARCH-01, ARCH-02, DIST-04 — mark each with a brief "how it was satisfied" line (ARCH-01: src/vibemix/ skeleton + uv lockfile shipped; ARCH-02: four `@runtime_checkable` Protocols + AST OS-leak guard; DIST-04: SignPath OSS application submitted by Kaan in Task 4.2).
- **Files created (count):** 18 (5 root tooling + 5 source + 6 test + 2 docs).
- **Files modified (count):** 1 (`.gitignore` overwritten from the existing 5-line stub).
- **POC files touched:** 0.
- **Architectural decisions locked:**
  - PEP 621 src-layout under `src/vibemix/`.
  - `uv` + `hatchling`; `uv.lock` committed; no `requirements.txt`.
  - Python 3.12 (`requires-python = ">=3.12,<3.13"`) — POC's 3.14 dropped for PyInstaller / pyobjc / scipy wheel coverage.
  - Apache 2.0 license; SPDX header on every `src/vibemix/*.py` file.
  - Four `typing.Protocol` Backends + `@runtime_checkable`; shape lifted verbatim from PATTERNS.md.
  - Repo at `github.com/ozzaii/vibemix` (personal account; transfer to bravoh org deferred — see `.planning/signpath-application.md` Submission Notes).
- **Dependent phases unlocked:**
  - Phase 2 (Audio Core Port) — `_audio_macos.py` implements `AudioBackend`.
  - Phase 3 (Sensing & State Port) — `_screen_macos.py`, `_midi_macos.py`, `_track_macos.py` implement their Protocols.
  - Phase 7 (Windows Port) — `_audio_windows.py`, `_screen_windows.py` implement against the same surface.
  - Phase 8 (ScreenCaptureKit migration) — drops in as a sibling impl of `ScreenBackend`.
  - Phase 9 (MIDI Controller Library) — sits on top of `MidiBackend` + adds a controller-profile abstraction layer.
  - Phase 18 (Distribution / Signing) — consumes the SignPath cert from this phase's application.
- **Open items (deferred):**
  - `vibemix` PyPI name reservation (CONTEXT-deferred; reassess if a third party publishes a competing package before Phase 19).
  - NOTICE, CONTRIBUTING (with DCO), SECURITY, CODE_OF_CONDUCT, issue templates, OG image — Phase 19.
  - CI matrix on macos-14 + windows-latest — Phase 20.
  - Bravoh GitHub org transfer — deferred until org is stood up; SignPath survives the rename.
  - `mypy` / `pyright` strict-mode config — Phase 1 ships hints, doesn't gate CI.
- **Pitfall mitigations landed this phase:**
  - P3 (API key leakage): `.gitignore` excludes `.env` + `.env.*` with `!.env.example` carve-out.
  - P11 (MIDI hot-plug): `MidiBackend` doc states hot-plug rescan is caller's concern at 2s cadence (per POC); impls in Phase 3/8 cannot skip it because the Protocol exposes `list_input_ports()` for rescanning.
  - P13 (Screen privacy): `ScreenBackend.find_window_bounds()` + `capture(bounds | None)` plus the recommended UX of always passing concrete bounds means the impl can't accidentally ship a default-fullscreen capture path through this surface.
  - P14 (License confusion / Bravoh dual-use): Apache 2.0 permissive license, explicit patent grant, SPDX-tagged on every source file.
- **Anything weird / surprising:** If `uv sync` had to bump any pinned dep in Task 1.3, note it here verbatim with the failing wheel and the bumped version, plus a one-line rationale.
- **Verification snapshot:** Final results of Task 4.1's 10 checks (all green).
- **Kaan-only completion proof:** `git remote -v` output (confirms `github.com/ozzaii/vibemix` is now origin) + SignPath confirmation email subject line / received timestamp.

After writing, stage + commit all Phase 1 artifacts in a single atomic commit:

```bash
git add LICENSE README.md .gitignore .python-version pyproject.toml uv.lock \
    src/vibemix/ tests/ \
    .planning/phases/01-platform-protocol-firewall/01-PLAN.md \
    .planning/phases/01-platform-protocol-firewall/01-SUMMARY.md \
    .planning/signpath-application.md docs/setup-github-repo.md

git commit -m "feat(01): platform protocol firewall — package skeleton + four Protocols + signpath checklist

Phase 1 of the vibemix open-source build. Ships:
- src/vibemix/ PEP 621 src-layout with __version__ 0.1.0-dev0 + py.typed
- four typing.Protocol firewall surfaces: AudioBackend / ScreenBackend / MidiBackend / TrackInfoBackend
- uv + hatchling toolchain, Python 3.12, uv.lock committed
- Apache 2.0 LICENSE + SPDX headers
- ruff lint + format config (POC files at root exempted)
- pytest scaffold with OS-leak AST guard (no sounddevice/mss/Quartz/mido/etc. inside src/vibemix/platform)
- SignPath Foundation OSS application checklist (.planning/signpath-application.md, filed by Kaan)
- docs/setup-github-repo.md recipe (Kaan-only repo creation at ozzaii/vibemix)

Closes: ARCH-01, ARCH-02, DIST-04"
```

If commit hooks fail, fix the underlying issue and create a new commit (never amend).
  </action>
  <verify>
    <automated>test -f .planning/phases/01-platform-protocol-firewall/01-SUMMARY.md && git log -1 --pretty=%B | grep -q "feat(01): platform protocol firewall" && git log -1 --pretty=%B | grep -q "ARCH-01" && git log -1 --pretty=%B | grep -q "ARCH-02" && git log -1 --pretty=%B | grep -q "DIST-04"</automated>
  </verify>
  <done>`01-SUMMARY.md` exists in the phase dir with all sections filled. A single atomic phase commit references ARCH-01 / ARCH-02 / DIST-04 in its message. `git status` is clean.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| git working tree → public GitHub repo | `.env` / `GEMINI_API_KEY` must not cross. This phase creates the firewall (`.gitignore` rules) before the repo is published. |
| Python imports (`from vibemix.platform import ...`) → OS-specific code | Phase 1's whole purpose is this boundary. Tests AST-guard against OS imports leaking into `src/vibemix/platform/`. |
| Source repo → SignPath signing infrastructure (Phase 18) | Phase 1 only files the application; the trust contract is the Apache 2.0 license + public repo at `ozzaii/vibemix`. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01-01 | Information disclosure | `.env` containing `GEMINI_API_KEY` | mitigate | `.gitignore` excludes `.env` + `.env.*` with `!.env.example` carve-out; `git status` will not stage `.env` files; verified before Task 4.3 commit. |
| T-01-02 | Tampering | `uv` dependency resolution | mitigate | `uv.lock` committed with version pins + wheel hashes; `uv sync --frozen` enforces lockfile in Task 4.1 check 10. |
| T-01-03 | Information disclosure | OS-specific symbols leaking through `vibemix.platform` | mitigate | `tests/test_platform.py::test_no_os_leaks` AST-scans every `src/vibemix/platform/*.py` for forbidden imports (sounddevice/mss/Quartz/mido/etc.); test fails the build if a future PR introduces a leak. |
| T-01-04 | Spoofing | Repo URL drift between SignPath checklist and reality | mitigate | `tests/test_signpath_checklist.py` greps for `ozzaii/vibemix` in the checklist; pyproject.toml `[project.urls]` uses the same URL; test fails if they diverge. |
| T-01-05 | Repudiation | License ambiguity blocking Bravoh internal use | mitigate | Apache 2.0 chosen (per CONTEXT decision) — permissive + explicit patent grant; SPDX header on every source file; CONTRIBUTING with DCO deferred to Phase 19 but flagged in SUMMARY's open-items. |
| T-01-06 | Information disclosure | SignPath form submission containing personal info | accept | Submitting personal info to SignPath is the intended trust transfer; the only mitigation is having Kaan review `.planning/signpath-application.md` before submit (Task 4.2 step B does this). |
| T-01-07 | Denial of service | uv resolver fetching from PyPI during `uv sync` | accept | First-time `uv sync` needs PyPI; subsequent `uv sync --frozen` is offline-capable. Lockfile mitigates supply-chain DoS by pinning versions. |
| T-01-08 | Elevation of privilege | `gh repo create` on Kaan's account | mitigate | Repo creation is gated behind the human-verify checkpoint (Task 4.2) — only Kaan with his gh auth can run it; `docs/setup-github-repo.md` provides the exact command but does not execute it. |
</threat_model>

<verification>
**Per task:** `<verify>` block runs the relevant subset (lint + tests + imports).

**Per wave merge:**
- Wave 1: `uv sync --frozen && uv run python -c "import vibemix; print(vibemix.__version__)"` → `0.1.0-dev0`.
- Wave 2: `uv run python -c "from vibemix.platform import AudioBackend, ScreenBackend, MidiBackend, TrackInfoBackend"` succeeds; `runtime_checkable` confirmed on all four.
- Wave 3: `uv run pytest -x` green (8 tests); both Kaan-facing docs (`.planning/signpath-application.md`, `docs/setup-github-repo.md`) exist with `KAAN-ONLY` banner and `ozzaii/vibemix` URL.
- Wave 4: All 10 checks in Task 4.1 pass; human-verify checkpoint in Task 4.2 approved; Task 4.3 commit exists with ARCH-01/02 + DIST-04 in the message.

**Phase gate (manual after Kaan-only steps complete):**
1. `gh repo view ozzaii/vibemix --web` resolves to a public repo.
2. SignPath confirmation email present in Kaan's inbox.
3. `git remote -v` shows `origin` pointing at `github.com/ozzaii/vibemix`.
4. `.planning/phases/01-platform-protocol-firewall/01-SUMMARY.md` exists.
5. Re-running `uv sync --frozen` on a fresh `.venv/` succeeds — lockfile is reproducible.
</verification>

<success_criteria>
- [ ] `uv sync --frozen` materialises `.venv/` (Python 3.12) and `import vibemix` prints `0.1.0-dev0`.
- [ ] Four Protocols importable from `vibemix.platform`; each is `@runtime_checkable`.
- [ ] `tests/test_platform.py::test_no_os_leaks` passes — zero OS-specific imports in `src/vibemix/platform/*.py`.
- [ ] `uv run ruff check src/ tests/` and `uv run ruff format --check src/ tests/` both green.
- [ ] `uv run pytest -x -q` green (8 tests).
- [ ] `.planning/signpath-application.md` has all 9 form sections prefilled + `KAAN-ONLY` banner.
- [ ] `docs/setup-github-repo.md` has the exact `gh repo create ozzaii/vibemix` recipe + `KAAN-ONLY` banner.
- [ ] No POC file modified (`cohost*.py`, `run*.sh`, `mascot.html`, `sprite-*.png`, `_test_*.py`, `test_voice.py`, `generate_bat.py`, `fillers/`).
- [ ] Public repo created at `github.com/ozzaii/vibemix` (Kaan-only, Task 4.2 step A).
- [ ] SignPath OSS application submitted; confirmation email received by `oozzxaaii@gmail.com` (Kaan-only, Task 4.2 step B).
- [ ] `01-SUMMARY.md` committed; phase commit references ARCH-01 / ARCH-02 / DIST-04.
</success_criteria>

<output>
After completion, create `.planning/phases/01-platform-protocol-firewall/01-SUMMARY.md` per Task 4.3. The summary IS the phase handoff to Phase 2 (Audio Core Port).
</output>
