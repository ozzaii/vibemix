# Phase 1: Platform Protocol Firewall — Research

**Date:** 2026-05-11
**Researcher:** gsd-phase-researcher
**Domain:** Python packaging / `uv` + `hatchling`, `typing.Protocol` API design, OSS licensing & SignPath Foundation onboarding, GitHub repo bootstrap
**Confidence:** HIGH on tooling (uv, hatchling, Protocol, ruff, gh, gitignore); MEDIUM on SignPath SLA (single recent data point); MEDIUM on bravoh GitHub org status (probed — does not exist yet)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Python tooling & package layout:**
- Package layout: `src/vibemix/` (PEP 621 src-layout). No flat layout.
- Dependency / lockfile tooling: `uv` produces `uv.lock`. **No `requirements.txt`.**
- Python version: 3.12.x. `requires-python = ">=3.12,<3.13"`. POC's 3.14 is dropped for PyInstaller / PyAudioWPatch / scipy wheel coverage.
- Build backend: `hatchling` declared in `pyproject.toml [build-system]`.

**Protocol surface:**
- Define all four protocols this phase: `AudioBackend`, `ScreenBackend`, `MidiBackend`, `TrackInfoBackend`.
- Mechanism: `typing.Protocol` + `@runtime_checkable`. **No `abc.ABC` / `@abstractmethod`.**
- File layout: one file per protocol under `src/vibemix/platform/` — `audio.py`, `screen.py`, `midi.py`, `track.py`. `src/vibemix/platform/__init__.py` re-exports the four Protocols.
- **No stub implementations this phase.** Phase 1 ships protocol *definitions* only.

**Package identity & licensing:**
- **Not** publishing to PyPI. Ships as signed installer (Phase 18).
- License: Apache 2.0. `LICENSE` at repo root + SPDX header `# SPDX-License-Identifier: Apache-2.0` in `src/vibemix/__init__.py`.
- `NOTICE`, `CONTRIBUTING`, `SECURITY`, `CODE_OF_CONDUCT` defer to Phase 19.
- Public GitHub repo `github.com/bravoh/vibemix` created **during this phase**, before SignPath application.
- SignPath OSS application: Phase 1 produces prefilled checklist `.planning/signpath-application.md`. **Kaan submits the form himself** at signpath.io/solutions/open-source-community — Claude cannot submit forms with personal info.

### Claude's Discretion
- Exact `pyproject.toml` metadata phrasing (description, keywords, classifiers).
- Docstring style for Protocol methods — pick one and apply uniformly (recommendation below: Google style).
- `py.typed` marker file (recommended yes — Protocols are pure typing artifacts).
- `.gitignore` contents — Python/macOS/Windows default; must include `.env`, `.venv/`, `recordings/`, `__pycache__/`, `dist/`, `build/`, `.uv/`.

### Deferred Ideas (OUT OF SCOPE)
- Reserving `vibemix` on PyPI for squat-defense.
- `NOTICE`, `CONTRIBUTING.md` (with DCO), `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue templates, OG image — Phase 19.
- CI matrix (GitHub Actions building signed binaries) — Phase 20.
- `mypy` / `pyright` strict-mode config — Phase 1 ships hints, doesn't gate CI.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ARCH-01 | Consolidate three POC variants into a single shipping `vibemix` Python package | This phase only ships the **skeleton**; consolidation work itself is Phases 2–13. Research below covers the `src/vibemix/` layout, `pyproject.toml`, and `uv.lock` workflow that ARCH-01 depends on. |
| ARCH-02 | `platform/` protocol firewall — no OS-specific imports leak past the abstraction boundary | `typing.Protocol` + `@runtime_checkable` pattern documented below. Method signatures extracted from POC `start_input_stream()` / `ScreenBuffer` / `ControllerState` / `TrackInfo` so impls in Phase 2/3/7/8 have a stable target. |
| DIST-04 | SignPath Foundation OSS application filed on day 1 of Phase 1 (3-week lead time) | SignPath docs confirm: free for OSS, OSI-approved license required (Apache 2.0 qualifies), repo must be public, **approval is now ~1 week, not 3 weeks** (per April 2026 GitHub issue from the `amd/gaia` project). The 3-week buffer in CONTEXT.md is conservative — good margin remains for Phase 18 installer signing. |
</phase_requirements>

## Executive Summary

- **`uv` + `hatchling` is the canonical 2026 stack.** `uv init --build-backend hatchling` scaffolds a src-layout project. `pyproject.toml` declares `requires = ["hatchling"]` / `build-backend = "hatchling.build"`. `[tool.hatch.build.targets.wheel] packages = ["src/vibemix"]` is the standard src-layout incantation. `uv.lock` is the cross-platform lockfile, checked into git.
- **All four Protocols defined as `typing.Protocol` + `@runtime_checkable` in one file each.** Use `...` bodies (not `raise NotImplementedError`) — clearer, idiomatic, and the typing spec accepts both. Document the **`isinstance(x, AudioBackend)` slowness** caveat (real, per CPython docs) — Phase 2/3 impls should rely on structural typing, not runtime isinstance checks in hot paths.
- **SignPath Foundation OSS approval is currently ~1 week** (data point: `amd/gaia` issue #732, April 2026), not the conservative 3 weeks in CONTEXT.md. Phase 1 checklist gathers all nine application sections (project basics, repo, downloads, privacy, Wikipedia/trust, technical, contact, T&Cs). Apache 2.0 is OSI-approved → qualifies. **Repo must be released "in the form to be signed"** — at Phase 1 we have only a Python skeleton, so the application is filed referencing **expected** future artifacts (Windows MSI, macOS DMG) per the prefilled checklist's "Technical Details / What will be signed" section.
- **`bravoh` GitHub organization does not exist yet** (verified via `gh api orgs/bravoh` → 404). Local `gh` is authenticated as user `ozzaii`, not as a `bravoh` org member. **Open question for planner:** does Kaan create the `bravoh` org first, or does the repo live at `ozzaii/vibemix` / `kaanozai/vibemix` and get transferred? Either flow takes ~1 minute via `gh` — but the SignPath checklist's "Source Code Repository URL" must point at the final URL, so the org needs to exist before the application is filed.
- **`ruff` replaces black + flake8 + isort** — configure in `[tool.ruff]` with `target-version = "py312"` and conservative starter ruleset `select = ["E4", "E7", "E9", "F", "B", "I", "UP", "RUF"]`. Defer `mypy` / `pyright` per CONTEXT — ruff catches enough at Phase 1.
- **Platform-specific deps use environment markers, not extras.** `pyobjc-framework-Quartz>=12.1 ; sys_platform == "darwin"` and `pyaudiowpatch>=0.2 ; sys_platform == "win32"` live in `[project.dependencies]` with markers. **No need for `[project.optional-dependencies]`** at Phase 1 — vibemix isn't published as a library, it's an installer, so `uv sync` on the correct OS just resolves to the right set. Reassess at Phase 7/8 if a contributor needs to cross-develop.

**Primary recommendation:** Lift the exact `pyproject.toml` + Protocol skeletons from the "Concrete Snippets" section below directly into the executor's hands. The SignPath checklist is the one item that needs Kaan's eyes — everything else is mechanically deterministic.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Audio capture & playback abstraction | Protocol (`vibemix.platform.audio`) | OS impl (Phase 2/3/7) | Protocols define the API contract; `_audio_macos.py` / `_audio_windows.py` implement it. No code in this phase. |
| Screen capture abstraction | Protocol (`vibemix.platform.screen`) | OS impl (Phase 3/8) | Same pattern — define `ScreenBackend` here, implement in dependent phases. |
| MIDI controller abstraction | Protocol (`vibemix.platform.midi`) | OS impl + controller lib (Phase 3/8 + Phase 9) | `MidiBackend` covers enumeration + hot-plug + event subscription. Controller mapping library is separate (Phase 9). |
| Track-info abstraction | Protocol (`vibemix.platform.track`) | OS impl (Phase 3/7) | macOS: `nowplaying-cli`; Windows: GlobalSystemMediaTransportControlsSessionManager. Both behind one Protocol. |
| Package skeleton & build | Repo root + `src/vibemix/` | — | `pyproject.toml`, `uv.lock`, `LICENSE`, `.gitignore`, `src/vibemix/__init__.py`. Pure tooling tier. |
| OSS hygiene & code signing | Repo root + `.planning/` | — | `LICENSE` lives in repo; SignPath application is a `.planning/` artifact for Kaan to submit. |

## Approaches Considered & Recommendations

### P0-1: `uv` + `hatchling` integration pattern

**Chosen approach:** Use `uv init --build-backend hatchling` to scaffold; commit the generated `pyproject.toml` and `uv.lock`. Lockfile lives in repo, `uv sync` is the only dev command anyone needs.

**Workflow per uv docs:**
- `uv sync` — install deps from `uv.lock` into `.venv/`. Creates `.venv/` if missing.
- `uv lock` — recompute the lockfile from `pyproject.toml` without installing.
- `uv add <pkg>` — add a dep to `pyproject.toml` + update `uv.lock` + install. (e.g., `uv add 'pyobjc-framework-Quartz ; sys_platform == "darwin"'`)
- `uv add --dev <pkg>` — add to dependency groups (dev-only, not in built wheel).
- `uv run python -m vibemix` — run inside the project env without manually activating.

**Alternative considered:** `uv_build` (uv's own backend). Rejected because CONTEXT locks `hatchling`. Hatchling is the more widely understood backend in 2026 and has the richest src-layout config.

**Alternative considered:** `poetry`. Rejected — uv is faster, has a stable lockfile format (`uv.lock`), and the project explicitly chose it.

**Rationale:** uv 0.10.6 is installed locally (verified). Hatchling is shipped by `pip install hatchling` and is the PEP 517 reference backend recommended in the Python Packaging Authority guide.

**Source:** [Creating projects | uv](https://docs.astral.sh/uv/concepts/projects/init/) [VERIFIED: docs.astral.sh], [uv project layout](https://docs.astral.sh/uv/concepts/projects/layout/) [VERIFIED: docs.astral.sh].

### P0-2: PEP 621 src-layout for `src/vibemix/`

**Chosen approach:** Standard hatchling src-layout incantation.

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/vibemix"]
```

This tells hatch to collapse `src/vibemix/file.py` to `vibemix/file.py` in the built wheel. Equivalent (more explicit) form:

```toml
[tool.hatch.build.targets.wheel]
only-include = ["src/vibemix"]
sources = ["src"]
```

**`py.typed` placement:** create empty file `src/vibemix/py.typed`. PEP 561 marker. Tells downstream type checkers "this package ships types". Required because the entire purpose of Phase 1 is the Protocol typing surface — without `py.typed`, consumers don't get the type info even though we ship hints.

**`py.typed` inclusion in wheel:** with `packages = ["src/vibemix"]`, hatchling includes any `py.typed` file inside. No extra config needed.

**Discovery test:** `uv sync` followed by `uv run python -c "import vibemix.platform; print(vibemix.platform.AudioBackend)"` — passes when layout is correct.

**Source:** [Hatch build configuration / src-layout](https://hatch.pypa.io/latest/config/build/) [VERIFIED: hatch.pypa.io], [PEP 561](https://peps.python.org/pep-0561/) [CITED].

### P0-3: `typing.Protocol` + `@runtime_checkable` 2026 best practices

**Chosen approach:**
- Use `@runtime_checkable` on all four protocols so impl classes can be validated at smoke-test time (e.g., `assert isinstance(_audio_macos.MacOSAudio(), AudioBackend)` in Phase 2 sanity checks).
- Use `...` (ellipsis) bodies for all Protocol methods. Idiomatic, terse, and the official typing spec accepts both `...` and `raise NotImplementedError`.
- **Avoid `isinstance(x, ProtocolClass)` in hot paths.** Per CPython docs: *"An `isinstance()` check against a runtime-checkable protocol can be surprisingly slow compared to an `isinstance()` check against a non-protocol class."* `@runtime_checkable` also only checks **attribute presence**, not signatures or types.
- Docstring style: **Google style** (consistent with the readable docstrings already in `cohost_v2.py` and the wider Python ecosystem). Apply uniformly across the four protocol files.
- Include both sync and async methods where appropriate (the POC's `start_input_stream` is sync-callback-style; async `start()` / `stop()` lifecycle methods read more naturally for the upper layer).

**Protocol vs `abc.ABC`:**
- Protocol = structural subtyping (duck-typing with type checking). A class implementing all methods passes type-check without inheriting.
- ABC = nominal subtyping. Class must `class MacOSAudio(AudioBackend):` to satisfy.
- **Why Protocol wins for vibemix:** the POC's macOS impl already exists as plain functions/classes (`start_input_stream` etc.). Phase 2 ports those into a class. With Protocol, the port doesn't need to inherit from a base — it just needs to expose the right methods. Less coupling, simpler refactor.

**Source:** [Python 3.12 typing docs — Protocol](https://docs.python.org/3.12/library/typing.html#typing.Protocol) [VERIFIED: docs.python.org], [PEP 544](https://peps.python.org/pep-0544/) [CITED], [typing.python.org Protocols spec](https://typing.python.org/en/latest/spec/protocol.html) [VERIFIED].

### P0-4: SignPath Foundation OSS application process

**Chosen approach:** Produce `.planning/signpath-application.md` with answers for all 9 sections of the SignPath OSS application form (per the prefilled answers template at `sysmanage.org/SignPath/application-form-answers.html`, which mirrors the live form). Kaan submits via the link at signpath.io/solutions/open-source-community.

**Approval lead time:** **~1 week** (per `amd/gaia` issue #732, dated April 2026). CONTEXT.md says 3 weeks, which is the historical figure — the current SLA is faster. Decision: keep the 3-week buffer in CONTEXT for safety, but tell Kaan the realistic expectation is 1 week so he can plan Phase 18 (installer signing) accordingly. [CITED: amd/gaia#732]

**License compatibility:** SignPath requires *"OSI-approved Open Source license without commercial dual-licensing for all components"*. Apache 2.0 is OSI-approved → qualifies. [VERIFIED: signpath.org/terms.html]

**Form sections (full enumeration):**

1. **Basic Information** — project name, short name/identifier, homepage, brief + detailed description, license, license URL, programming languages.
2. **Repository Information** — repo type (Git), repo URL, contributor count, commit count, project age, dev status.
3. **Distribution & Downloads** — download page URL, package formats, distribution method, total + monthly downloads.
4. **Privacy Policy** — does the software collect/transmit user data? what? where? privacy policy URL.
5. **Wikipedia Article** — Wikipedia article URL OR "why no article" justification.
6. **Verification & Trust Evidence** — how can SignPath verify the project is used/trusted? media reports, blog articles, GitHub insights, usage data, trademark proof.
7. **Technical Details** — what will be signed? file types, signing frequency, build process, CI/CD integration.
8. **Contact Information** — primary contact name + email, project maintainer(s), GitHub org/user, additional contacts.
9. **Terms & Conditions** — acknowledgment, open-source confirmation, legitimacy declaration (checkboxes).

**Phase 1 challenge for section 3 (Distribution & Downloads):** Phase 1 has zero downloads — vibemix isn't released yet. SignPath terms say *"The project must already be released in the form that should be signed."* This is the **one real risk for the day-1 submission**. Mitigation: file the application referencing the **expected future artifacts** (Windows MSI, macOS DMG signed via Phase 18), and explicitly note in the cover that Phase 1 is the OSS skeleton with binary release planned in ~3 weeks (Phase 18 timeline). If SignPath rejects on this basis, the fallback is to delay the application to Phase 11–13 when a usable pre-release binary exists. Either way, the 3-week CONTEXT buffer absorbs this risk.

**Phase 1 challenge for section 6 (Verification & Trust):** Zero stars on day 1. Acknowledge in the application: "Project is launching alongside Bravoh AI Artist Operating System, a closed-beta product with established team and developer track record. Maintainer GitHub profile and Bravoh team links provided as verification proxy." Include Kaan's existing GitHub profile and any Bravoh public footprint as evidence.

**Source:** [SignPath Foundation conditions](https://signpath.org/terms.html) [VERIFIED], [SysManage prefilled application](https://sysmanage.org/SignPath/application-form-answers.html) [VERIFIED — mirrors form fields], [amd/gaia#732 — reported 1-week approval](https://github.com/amd/gaia/issues/732) [CITED — single recent data point, MEDIUM confidence].

### P0-5: GitHub repo creation via gh CLI

**Chosen approach (if `bravoh` org exists):**

```bash
# from repo root — directory already has files (POC, .planning, etc.)
git add LICENSE README.md pyproject.toml uv.lock .gitignore src/
git commit -m "feat: vibemix skeleton — package layout, protocols, license"
gh repo create bravoh/vibemix --public --source=. --remote=origin --push \
    --description "Open-source AI DJ co-host. Listens, watches, talks back."
```

**Chosen approach (if `bravoh` org does NOT exist — current state, verified):**

Two paths — flag for planner decision:

1. **Create org first, then repo.** Kaan visits github.com/organizations/new, creates `bravoh` org (free plan is fine; ~30 seconds). Then run the `gh repo create bravoh/vibemix` command. SignPath application references `github.com/bravoh/vibemix` from day 1.

2. **Stage under personal account, transfer later.** `gh repo create ozzaii/vibemix --public ...`. Later `gh api repos/ozzaii/vibemix/transfer -F new_owner=bravoh`. **Risk:** the SignPath application's "Source Code Repository URL" field would need to be updated post-transfer — they may reject or delay re-review on URL change. **Not recommended.**

**Recommendation: option 1.** Create the `bravoh` GitHub org *before* this phase's executor starts the repo-creation task. Add as a Phase 1 prerequisite (manual, ~1 min, Kaan-only).

**Required `gh` flags:**
- `--public` — non-interactive public repo.
- `--source=.` — point at current dir (which has files to push).
- `--remote=origin` — set the remote name.
- `--push` — push the initial commit.
- `--description` — short tagline (under 350 chars).
- **Do NOT** use `--add-readme`, `--license`, `--gitignore` — those generate files on GitHub side, which conflicts with `--source=.` (local files already exist). We'll write `README.md`, `LICENSE`, `.gitignore` locally first.

**Org scope check:** local `gh` is authenticated as `ozzaii` with scopes `'gist', 'read:org', 'repo', 'workflow'`. The `admin:org` scope is **missing** — needed only if Kaan wants to create the org via `gh`. Manual org creation in the GitHub UI avoids the scope refresh.

**Source:** [gh repo create](https://cli.github.com/manual/gh_repo_create) [VERIFIED], local `gh --version` 2.86.0 [VERIFIED — `gh --version` output].

### P1-6: Protocol method signatures (derived from POC)

**Approach:** lift signatures from `cohost_v2.py` and `cohost.py` patterns. The POC's behavior is the contract — don't reinvent.

**`AudioBackend`** — derived from `start_input_stream`, `start_passthrough_stream`, `start_playback_stream`, `Levels`, `PlaybackQueue`:

```python
from __future__ import annotations
from typing import Protocol, runtime_checkable, Callable
import numpy as np

PcmCallback = Callable[[np.ndarray, int], None]  # (pcm_int16_chunk, sample_rate)

@runtime_checkable
class AudioBackend(Protocol):
    """OS audio I/O surface — capture master output, output AI voice, route passthrough.

    Implementations live in vibemix.platform._audio_macos / _audio_windows.
    See cohost_v2.py for the reference behavior; mic gating + sample-rate negotiation
    are part of the contract.
    """

    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    def enumerate_inputs(self) -> list[dict]: ...
    def enumerate_outputs(self) -> list[dict]: ...

    def select_master_input(self, device_id: int | str) -> None: ...
    def select_voice_output(self, device_id: int | str) -> None: ...
    def select_passthrough_output(self, device_id: int | str | None) -> None: ...
    def select_mic_input(self, device_id: int | str | None) -> None: ...

    def on_master_pcm(self, callback: PcmCallback) -> None:
        """Register a callback fired with int16 PCM from the master/loopback input."""
        ...

    def on_mic_pcm(self, callback: PcmCallback) -> None: ...

    def push_voice_pcm(self, pcm: bytes, sample_rate: int) -> None:
        """Enqueue AI-voice PCM bytes for playback to the selected voice output."""
        ...

    def set_passthrough_gain(self, gain: float) -> None: ...

    @property
    def is_running(self) -> bool: ...
```

**`ScreenBackend`** — derived from `ScreenBuffer` + `mss.grab` + Quartz `find_djay_window_bounds`:

```python
@runtime_checkable
class ScreenBackend(Protocol):
    """Per-window screen capture surface. Privacy-critical — see Pitfall 13."""

    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    def list_windows(self) -> list[dict]:
        """Return [{'window_id', 'app_name', 'title', 'bounds'}, ...]."""
        ...

    def select_window(self, window_id: int | str) -> None: ...

    def grab_jpeg(self, max_width: int = 1280, quality: int = 80) -> bytes | None:
        """Return latest JPEG of selected window, or None if window is unavailable."""
        ...

    @property
    def selected_window_visible(self) -> bool: ...
```

**`MidiBackend`** — derived from `ControllerState` + `mido.get_input_names` + DDJ-FLX4 decode loop:

```python
from typing import Awaitable

MidiCallback = Callable[[dict], None]  # event dict: {ts, port, type, channel, ...}

@runtime_checkable
class MidiBackend(Protocol):
    """MIDI controller enumeration + event subscription with hot-plug support.

    Implementations poll-rescan every 2s for hot-plug detection (mido / python-rtmidi
    do not expose hot-plug events). See Pitfall 11.
    """

    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    def enumerate_controllers(self) -> list[dict]:
        """Return [{'port_name', 'vendor_hint', 'matched_profile'}, ...]."""
        ...

    def on_event(self, callback: MidiCallback) -> None: ...
    def on_controller_attached(self, callback: Callable[[dict], None]) -> None: ...
    def on_controller_detached(self, callback: Callable[[dict], None]) -> None: ...

    @property
    def attached_controllers(self) -> list[dict]: ...
```

**`TrackInfoBackend`** — derived from `TrackInfo` polling `nowplaying-cli`:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class TrackSnapshot:
    title: str | None
    artist: str | None
    duration_s: float | None
    position_s: float | None
    is_playing: bool
    source_app: str | None

@runtime_checkable
class TrackInfoBackend(Protocol):
    """Current-track metadata from the OS now-playing API.

    macOS: nowplaying-cli (subprocess). Windows: GlobalSystemMediaTransportControlsSessionManager.
    """

    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    def snapshot(self) -> TrackSnapshot: ...

    def on_track_change(self, callback: Callable[[TrackSnapshot, TrackSnapshot], None]) -> None: ...
```

**Rationale notes:**
- All four use `async def start() / stop()` lifecycle — matches the upper-layer asyncio orchestration in `cohost_v2.py`.
- Callback registration (`on_*`) over async iterators — matches the POC's existing pattern and is easier to bridge from sounddevice/mido sync callbacks.
- `enumerate_*` returns `list[dict]` (not typed records) to keep the Protocol surface stable while impls evolve. Phase 2/3 can introduce typed records as needed.
- `TrackSnapshot` is a frozen dataclass exported from `track.py` — a typed value object (not a Protocol) because it's pure data.

**Source:** lifted from `cohost_v2.py` lines 200-900 (verified by reading the POC during research). [VERIFIED: cohost_v2.py]

### P1-7: `ruff` config in pyproject.toml

**Chosen approach:**

```toml
[tool.ruff]
target-version = "py312"
line-length = 100  # POC uses 79-100 informal — 100 is the modern default
src = ["src"]

[tool.ruff.lint]
# Conservative starter set — won't churn through the existing POC ports
select = [
    "E4",   # imports (pycodestyle)
    "E7",   # statement issues
    "E9",   # runtime errors
    "F",    # pyflakes
    "B",    # bugbear (high-value catches)
    "I",    # isort (import ordering)
    "UP",   # pyupgrade — keep idioms current for py312
    "RUF",  # ruff-native rules
]
ignore = [
    "E501",  # line-too-long handled by formatter, don't double-error
]

[tool.ruff.lint.per-file-ignores]
# POC files at root are reference material, not yet ported — exempt during Phases 1-13
"cohost*.py" = ["E", "F", "B", "I", "UP", "RUF"]
"_test_*.py" = ["E", "F", "B", "I", "UP", "RUF"]
"test_voice.py" = ["E", "F", "B", "I", "UP", "RUF"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
docstring-code-format = true
```

**Defer `mypy` / `pyright` per CONTEXT.** Ruff catches enough at Phase 1. Type checkers can be added in a later phase once impls land and the typing surface stabilizes.

**Alternative considered:** Enabling `D` (pydocstyle) rules. Rejected — would require docstrings on every public function and create churn for the POC ports.

**Source:** [Ruff configuration docs](https://docs.astral.sh/ruff/configuration/) [VERIFIED].

### P1-8: `uv` workspace vs single project vs extras

**Chosen approach:** Single project, no workspace, **no `[project.optional-dependencies]`**. Use environment markers for platform-specific deps.

```toml
[project]
dependencies = [
    "google-genai>=2.0.1",
    "livekit-agents>=1.5.8",
    "livekit-plugins-google>=1.5.8",
    "livekit>=1.1.7",
    "numpy>=2.4.4",
    "scipy>=1.17.1",
    "sounddevice>=0.5.5",
    "mido>=1.3.3",
    "python-rtmidi>=1.5.8",
    "mss>=10.2.0",
    "pillow>=12.2.0",
    "websockets>=16.0",
    "python-dotenv>=1.2.2",
    # macOS-only
    "pyobjc-core>=12.1 ; sys_platform == 'darwin'",
    "pyobjc-framework-Cocoa>=12.1 ; sys_platform == 'darwin'",
    "pyobjc-framework-Quartz>=12.1 ; sys_platform == 'darwin'",
    # Windows-only (added in Phase 7 — keep commented for now or include with marker that resolves to no-op on macOS)
    # "pyaudiowpatch>=0.2 ; sys_platform == 'win32'",
]
```

**Rationale:**
- vibemix is **not** a library distributed via PyPI — it's an installer payload (PyInstaller `--onedir`). Extras (`pip install vibemix[macos]`) are a library pattern. There's no user-facing reason to expose them.
- `sys_platform` markers do the right thing: `uv sync` on macOS resolves the `darwin`-marked deps, skips them on Windows, and vice versa. `uv.lock` records both resolutions universally.
- Workspace mode (multi-package monorepo) is over-engineered for a single package.

**Dev dependencies use `[dependency-groups]`** (not `[project.optional-dependencies]`):

```toml
[dependency-groups]
dev = [
    "ruff>=0.7",
    "pytest>=8.0",
]
```

Add via `uv add --dev ruff pytest`. Per uv docs: dev groups are local-only, not in the built wheel.

**Source:** [uv managing dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/) [VERIFIED].

### P2-9: `.gitignore` for Python + macOS + Windows + uv

**Chosen approach:** start from GitHub's official Python template, append macOS + uv + project-specific lines.

See "Concrete Snippets" for the full file. Current `.gitignore` (verified — 5 lines: `.env`, `.venv/`, `__pycache__/`, `*.pyc`, `recordings/`) is incomplete. Phase 1 overwrites it.

**Source:** [github/gitignore Python template](https://github.com/github/gitignore/blob/main/Python.gitignore) [VERIFIED].

### P2-10: Apache 2.0 LICENSE + NOTICE pattern

**Chosen approach:** `LICENSE` at repo root = verbatim Apache 2.0 text from apache.org/licenses/LICENSE-2.0.txt. **No `NOTICE` file this phase.**

**Why no NOTICE in Phase 1:**
- ASF's strict rule "NOTICE required even for single-file repos" applies to **ASF-hosted projects**, not to all Apache-2.0-licensed projects. vibemix is not an ASF project — it just uses the license.
- For non-ASF Apache 2.0 projects, NOTICE is only **required** when the codebase includes third-party content that carries its own NOTICE entries. Phase 1 has no bundled third-party code (deps are installed, not vendored).
- SignPath does not list NOTICE as a requirement — only "OSI-approved license without commercial dual-licensing".
- CONTEXT defers NOTICE to Phase 19 — that aligns with when third-party attribution will actually matter (after PyInstaller bundles the deps).

**SPDX header in `src/vibemix/__init__.py`:**

```python
# SPDX-License-Identifier: Apache-2.0
"""vibemix — open-source AI DJ co-host."""

__version__ = "0.1.0-dev0"
```

**LICENSE format note:** download the canonical text from apache.org. Substitute the copyright line:

```
Copyright 2026 Bravoh / Kaan Özkan
```

at the bottom of the LICENSE file (Apache's instructions). Or use the standalone "APPENDIX: How to apply the Apache License to your work" copyright block.

**Source:** [Applying the Apache License 2.0](https://www.apache.org/legal/apply-license.html) [VERIFIED], [choosealicense.com — Apache 2.0](https://choosealicense.com/licenses/apache-2.0/) [VERIFIED].

## Concrete Snippets

### `pyproject.toml` (canonical Phase 1 skeleton)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "vibemix"
version = "0.1.0-dev0"
description = "Open-source AI DJ co-host. Listens, watches, talks back."
readme = "README.md"
requires-python = ">=3.12,<3.13"
license = { file = "LICENSE" }
authors = [
    { name = "Kaan Özkan", email = "oozzxaaii@gmail.com" },
]
keywords = ["dj", "ai", "audio", "midi", "live-performance", "gemini", "livekit"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: MacOS X",
    "Environment :: Win32 (MS Windows)",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: MacOS :: MacOS X",
    "Operating System :: Microsoft :: Windows",
    "Programming Language :: Python :: 3.12",
    "Topic :: Multimedia :: Sound/Audio",
    "Topic :: Artistic Software",
]
dependencies = [
    "google-genai>=2.0.1",
    "livekit-agents>=1.5.8",
    "livekit-plugins-google>=1.5.8",
    "livekit>=1.1.7",
    "numpy>=2.4.4",
    "scipy>=1.17.1",
    "sounddevice>=0.5.5",
    "mido>=1.3.3",
    "python-rtmidi>=1.5.8",
    "mss>=10.2.0",
    "pillow>=12.2.0",
    "websockets>=16.0",
    "python-dotenv>=1.2.2",
    "pyobjc-core>=12.1 ; sys_platform == 'darwin'",
    "pyobjc-framework-Cocoa>=12.1 ; sys_platform == 'darwin'",
    "pyobjc-framework-Quartz>=12.1 ; sys_platform == 'darwin'",
]

[project.urls]
Homepage = "https://github.com/bravoh/vibemix"
Repository = "https://github.com/bravoh/vibemix"
Issues = "https://github.com/bravoh/vibemix/issues"

[dependency-groups]
dev = [
    "ruff>=0.7",
]

[tool.hatch.build.targets.wheel]
packages = ["src/vibemix"]

[tool.ruff]
target-version = "py312"
line-length = 100
src = ["src"]

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "B", "I", "UP", "RUF"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"cohost*.py" = ["E", "F", "B", "I", "UP", "RUF"]
"_test_*.py" = ["E", "F", "B", "I", "UP", "RUF"]
"test_voice.py" = ["E", "F", "B", "I", "UP", "RUF"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
docstring-code-format = true
```

### `src/vibemix/__init__.py`

```python
# SPDX-License-Identifier: Apache-2.0
"""vibemix — open-source AI DJ co-host.

Listens to your master output, watches your DJ software, ingests controller actions,
and talks back. macOS + Windows. Apache 2.0.
"""

__version__ = "0.1.0-dev0"
```

### `src/vibemix/platform/__init__.py`

```python
# SPDX-License-Identifier: Apache-2.0
"""Cross-platform OS abstraction layer.

All four protocols (AudioBackend, ScreenBackend, MidiBackend, TrackInfoBackend) are
defined here. No OS-specific imports leak past this boundary — concrete impls live in
sibling modules (_audio_macos.py, _audio_windows.py, etc.) and are imported through a
factory pattern in Phase 2+.
"""

from vibemix.platform.audio import AudioBackend, PcmCallback
from vibemix.platform.midi import MidiBackend, MidiCallback
from vibemix.platform.screen import ScreenBackend
from vibemix.platform.track import TrackInfoBackend, TrackSnapshot

__all__ = [
    "AudioBackend",
    "MidiBackend",
    "MidiCallback",
    "PcmCallback",
    "ScreenBackend",
    "TrackInfoBackend",
    "TrackSnapshot",
]
```

### `src/vibemix/platform/audio.py`

```python
# SPDX-License-Identifier: Apache-2.0
"""AudioBackend protocol — OS audio I/O surface.

Captures the master output (for AI grounding), routes a passthrough copy to speakers if
the user chose that path, and plays back AI voice PCM to the selected output. Mic input
is optional and gated when the AI is talking (see cohost_v2.py MicBuffer pattern).

Implementations:
    - vibemix.platform._audio_macos.MacOSAudio (Phase 2/3) — sounddevice + BlackHole
    - vibemix.platform._audio_windows.WindowsAudio (Phase 7) — sounddevice + WASAPI loopback

The protocol is `@runtime_checkable` so smoke tests can assert isinstance(impl, AudioBackend),
but avoid isinstance() in hot paths — it's slow per Python typing docs.
"""

from __future__ import annotations

from typing import Callable, Protocol, runtime_checkable

import numpy as np

PcmCallback = Callable[[np.ndarray, int], None]
"""Callback signature: (pcm_int16_chunk, sample_rate) -> None.

Called from the audio backend's capture thread. Callbacks MUST NOT block — push to a
queue and return. See Pitfall 5 (PITFALLS.md).
"""


@runtime_checkable
class AudioBackend(Protocol):
    """OS audio I/O — capture master output, route passthrough, play back AI voice.

    Lifecycle:
        Construct with no required args. Call `await start()` to open streams,
        `await stop()` to release them. `is_running` reflects current state.

    Threading:
        on_master_pcm / on_mic_pcm callbacks fire on the audio backend's capture
        thread. Implementations are responsible for not blocking that thread (see
        Pitfall 5 in PITFALLS.md). Consumers must not perform heavy work in the
        callback.
    """

    async def start(self) -> None:
        """Open all selected streams. Idempotent — second call is a no-op."""
        ...

    async def stop(self) -> None:
        """Close all streams. Idempotent. Drains pending playback before returning."""
        ...

    def enumerate_inputs(self) -> list[dict]:
        """Return available input devices.

        Returns:
            List of dicts with keys: 'id', 'name', 'channels', 'default_samplerate',
            'is_loopback' (bool — True for BlackHole / WASAPI loopback variants).
        """
        ...

    def enumerate_outputs(self) -> list[dict]:
        """Return available output devices. Same shape as enumerate_inputs."""
        ...

    def select_master_input(self, device_id: int | str) -> None:
        """Choose the input device that captures the DJ software's master output."""
        ...

    def select_voice_output(self, device_id: int | str) -> None:
        """Choose where AI voice PCM plays (headphones in private mode, speakers in PA mode)."""
        ...

    def select_passthrough_output(self, device_id: int | str | None) -> None:
        """Route a passthrough copy of master to a separate output, or None to disable."""
        ...

    def select_mic_input(self, device_id: int | str | None) -> None:
        """Mic input for Kaan-speaks trigger. None disables (required in speakers mode — Pitfall 12)."""
        ...

    def on_master_pcm(self, callback: PcmCallback) -> None:
        """Register callback fired with int16 PCM chunks from the selected master input."""
        ...

    def on_mic_pcm(self, callback: PcmCallback) -> None:
        """Register callback fired with int16 PCM from the mic, when mic is enabled and ungated."""
        ...

    def push_voice_pcm(self, pcm: bytes, sample_rate: int) -> None:
        """Enqueue AI-voice PCM bytes for playback on the selected voice output.

        Args:
            pcm: Raw int16 little-endian PCM bytes. Mono.
            sample_rate: Sample rate of the PCM (typically 24000 from Gemini TTS).
        """
        ...

    def set_passthrough_gain(self, gain: float) -> None:
        """Set passthrough gain 0.0..1.0. 0.0 disables the passthrough callback entirely."""
        ...

    @property
    def is_running(self) -> bool:
        """True between successful start() and stop()."""
        ...
```

### `src/vibemix/platform/screen.py`, `midi.py`, `track.py`

Follow the signatures listed in P1-6. Each file mirrors the structure of `audio.py`: SPDX header, module docstring describing the OS impls, type aliases, the `@runtime_checkable` Protocol with Google-style docstrings.

### `src/vibemix/py.typed`

Empty file. PEP 561 marker.

### `LICENSE`

Verbatim Apache License 2.0 text from <https://www.apache.org/licenses/LICENSE-2.0.txt>, with the appendix copyright block filled in:

```
   Copyright 2026 Bravoh / Kaan Özkan

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
```

### `README.md` (minimal Phase 1 placeholder)

```markdown
# vibemix

Open-source AI DJ co-host. Listens to your master output, watches your DJ software, talks back.

**Status:** Pre-release. Building toward early-June 2026 launch alongside [Bravoh](https://altidus.world).

**License:** [Apache 2.0](./LICENSE)

**Platforms:** macOS + Windows. Linux not supported.

More to come.
```

### `.gitignore` (Python + macOS + Windows + uv)

```
# Byte-compiled / optimized
__pycache__/
*.py[cod]
*$py.class
*.so

# Distribution / packaging
build/
dist/
*.egg-info/
*.egg
.eggs/

# Virtual environments
.venv/
venv/
ENV/
env/

# uv
.uv/

# Environment
.env
.env.*
!.env.example

# Testing & coverage
.pytest_cache/
.coverage
.coverage.*
htmlcov/
.tox/
.nox/

# Type checking
.mypy_cache/
.pyright/
.ruff_cache/

# IDE
.vscode/
.idea/
*.swp
*.swo

# macOS
.DS_Store
.AppleDouble
.LSOverride
._*

# Windows
Thumbs.db
ehthumbs.db
Desktop.ini
$RECYCLE.BIN/

# vibemix-specific
recordings/
*.wav
*.jsonl
```

### `gh` commands for repo creation

```bash
# Prereq: bravoh org exists on GitHub (manual one-time step by Kaan).
# Verify auth: gh auth status
# Verify org access: gh api orgs/bravoh

cd /Users/ozai/projects/dj-set-ai

# Stage Phase 1 artifacts
git add LICENSE README.md pyproject.toml uv.lock .gitignore src/

# Initial commit — POC files are already committed
git commit -m "feat: vibemix skeleton — package layout, protocols, license, uv lockfile

Phase 1 of the vibemix open-source build. Establishes:
- src/vibemix/ PEP 621 src-layout package
- typing.Protocol firewall for audio / screen / MIDI / track-info
- uv + hatchling toolchain
- Apache 2.0 license
- ruff lint+format config"

# Create remote and push
gh repo create bravoh/vibemix \
    --public \
    --source=. \
    --remote=origin \
    --push \
    --description "Open-source AI DJ co-host. Listens, watches, talks back."

# Verify
gh repo view bravoh/vibemix --web
```

### SignPath OSS application checklist (write to `.planning/signpath-application.md`)

The checklist should mirror the 9-section form. Pre-filled values where Kaan-data is already known (per CONTEXT specifics):

| Section | Field | Phase 1 value |
|---------|-------|---------------|
| 1. Basic | Project name | vibemix |
| 1. Basic | Short name | vibemix |
| 1. Basic | Homepage | https://github.com/bravoh/vibemix |
| 1. Basic | Brief description | Open-source AI DJ co-host. Listens to master audio, watches DJ software, talks back. |
| 1. Basic | Detailed description | (1-paragraph product summary — derive from PROJECT.md) |
| 1. Basic | License | Apache 2.0 |
| 1. Basic | License URL | https://github.com/bravoh/vibemix/blob/main/LICENSE |
| 1. Basic | Programming languages | Python, JavaScript, HTML/CSS |
| 2. Repo | Repo type | Git |
| 2. Repo | Repo URL | https://github.com/bravoh/vibemix |
| 2. Repo | Contributor count | 1 (Kaan) — note Bravoh team members joining post-launch |
| 2. Repo | Commit count | (current commit count at submission) |
| 2. Repo | Project age | < 1 week at Phase 1 — flag honestly, reference Bravoh team's track record |
| 2. Repo | Dev status | Alpha / pre-release |
| 3. Distribution | Download page URL | https://github.com/bravoh/vibemix/releases (will exist post-Phase 18) |
| 3. Distribution | Package formats | Windows MSI installer, macOS DMG |
| 3. Distribution | Distribution method | Direct download from GitHub Releases |
| 3. Distribution | Total downloads (all time) | 0 — note: pre-release, signed binaries pending SignPath approval |
| 3. Distribution | Downloads per month | 0 — see above |
| 4. Privacy | Collects/transmits user data? | Yes — audio + screenshots + MIDI events sent to Google Gemini API for AI reactions. No telemetry to Bravoh. |
| 4. Privacy | What is collected? | DJ-window screenshot (user-picked), master-audio PCM snapshots, MIDI controller events, current track title from OS now-playing API. |
| 4. Privacy | Where transmitted? | Google Gemini API via Bravoh-side proxy (Phase 5). Raw API key never leaves the server. |
| 4. Privacy | Privacy policy URL | (Phase 19 — create privacy policy page; for Phase 1 application, link to README privacy section as placeholder) |
| 5. Wikipedia | Wikipedia article URL | N/A |
| 5. Wikipedia | Why no article? | Pre-release project, < 1 month from launch — Wikipedia notability not yet established. |
| 6. Trust | Verification | Maintainer is founder of Bravoh (https://altidus.world). Bravoh team (Musa, Yasin) joining as contributors post-launch. Bravoh closed-beta launching March 2026. |
| 6. Trust | Media/blog | (none on day 1 — note "launch coverage planned via IG ads + DJ network outreach") |
| 6. Trust | GitHub insights | (Star/fork counts at submission time) |
| 6. Trust | Trademark proof | Bravoh trademark owned by founding entity (link if registered) |
| 7. Technical | What will be signed? | Windows MSI installer wrapping PyInstaller `--onedir` payload; macOS DMG containing notarized .app bundle. |
| 7. Technical | File types | .msi (Windows installer), .exe (PyInstaller bootstrap inside MSI), .dmg (macOS disk image), .app bundle (macOS) |
| 7. Technical | Signing frequency | Per release — initial v1.0 + patch releases (~monthly post-launch) |
| 7. Technical | Build process | GitHub Actions on tag push (Phase 20) — build artifact uploaded to SignPath, signed binary returned, attached to GitHub Release |
| 7. Technical | CI/CD integration | GitHub Actions — SignPath has an official action |
| 8. Contact | Primary contact name | Kaan Özkan |
| 8. Contact | Primary contact email | oozzxaaii@gmail.com |
| 8. Contact | Project maintainer(s) | Kaan Özkan (primary); Musa, Yasin (Bravoh team — joining post-launch) |
| 8. Contact | GitHub org/user | bravoh (org); ozzaii (personal — current gh auth) |
| 8. Contact | Additional contacts | (Francesco — Bravoh cofounder, marketing/product) |
| 9. T&C | Acknowledgment | (checkbox — Kaan confirms) |
| 9. T&C | OSS confirmation | (checkbox — Apache 2.0 confirmed) |
| 9. T&C | Legitimacy declaration | (checkbox — Kaan confirms) |

**Critical notes for Kaan when filling the form:**
- Section 3 ("already released in the form to be signed") is the **one weak point**. If SignPath asks, the truthful answer is "pre-release, alpha, binary release targeted for late May / early June 2026". Submit anyway — at worst they say wait until binaries exist. If they reject, refile at Phase 11-13 when a usable pre-release binary is in `dist/`.
- Section 6: Bravoh's existing footprint (altidus.world, closed beta, team) is the strongest trust signal on day 1. Lead with it.
- Section 4 privacy policy must exist somewhere — even a brief README section pointed at by the application is better than "TBD".

## Pitfalls & Mitigations

| Pitfall | Severity | Phase 1 mitigation |
|---------|----------|--------------------|
| **P3** API key leakage | Critical | `.gitignore` includes `.env` and `.env.*` (with `!.env.example` carve-out so we can ship a key-less template). Phase 1 ships NO `.env` file — only the gitignore rule. README explicitly says key is server-side via Bravoh proxy (deferred to Phase 5). Architecture firewall (this phase) prevents the proxy ever needing to share the key with the client. |
| **P6** Day-one installer broken | Critical | Pin Python to 3.12 (CONTEXT decision) — confirmed: PyInstaller 6.20.0 (latest, April 2026) supports 3.8–3.14 including 3.12. Phase 1 doesn't ship a binary; this is a constraint for Phase 18, recorded here for traceability. |
| **P11** MIDI hot-plug | High | `MidiBackend` protocol's `on_controller_attached` / `on_controller_detached` are explicit in the interface so Phase 3/8 impls cannot skip hot-plug support. Docstring references PITFALLS.md P11 directly. |
| **P14** License confusion / Bravoh dual-use | High | Apache 2.0 chosen (CONTEXT decision) — permissive, explicit patent grant, Bravoh internal use unblocked. SPDX header in `__init__.py` + LICENSE at repo root. CONTRIBUTING (with DCO) defers to Phase 19. **CLA decision not needed at Phase 1** because Phase 1 has only Kaan committing. As soon as the first external PR lands (likely Phase 13+ once mascot is in repo), Phase 19's CONTRIBUTING.md with DCO must be in place. |
| **P13** Screen privacy | High | `ScreenBackend.select_window()` + `selected_window_visible` property exposed in the Phase 1 protocol — impls **cannot** ship a full-screen capture path through this interface. The protocol shape enforces window-only capture. Per-window OS APIs (ScreenCaptureKit, Windows.Graphics.Capture) implementable in Phase 3/8. |
| **P4** Hardcoded device names | Critical | `AudioBackend.enumerate_inputs()` / `select_master_input(device_id)` make device names a calibration concern, not a constant. Phase 1 protocol shape prevents Phase 2/3 impls from re-introducing hardcoded names. |

## Runtime State Inventory

Phase 1 is a **greenfield package skeleton** — no existing service config, no databases, no OS-registered state, no installed packages with the new name yet. The only relevant items:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no databases or persisted state in the project | None — verified by reading STACK.md and inspecting `.planning/` |
| Live service config | None — no external services configured yet (Bravoh proxy is Phase 5) | None |
| OS-registered state | None — no installed binaries, no launchd / Task Scheduler entries | None |
| Secrets/env vars | `GEMINI_API_KEY` in `.env` at root — used by POC, **must not** be removed from `.gitignore` during refactoring | Verify `.env` stays gitignored after `.gitignore` rewrite |
| Build artifacts | `.venv/` exists at root with Python 3.14 — **will be recreated** by `uv sync` on Python 3.12 | Delete `.venv/` before `uv sync` to avoid 3.14/3.12 mismatch confusion. Re-`uv sync` recreates against pinned 3.12. |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | All Phase 1 tasks | yes | 0.10.6 (2026-02-24) | none — required |
| Python 3.12 | Project runtime (CONTEXT decision) | yes | 3.12.12 at `/opt/homebrew/bin/python3.12` | uv can auto-install via `uv python install 3.12` |
| `gh` CLI | Repo creation | yes | 2.86.0 (2026-01-21) | none — required for `gh repo create` |
| `gh` auth — user `ozzaii` | Local push | yes | scopes: gist, read:org, repo, workflow | refresh required if org creation via CLI needed |
| `git` | Commit history | yes | 2.50.1 | none |
| GitHub org `bravoh` | Repo URL `bravoh/vibemix` | **no** — verified 404 via `gh api orgs/bravoh` | **Kaan must create the org manually before repo creation task runs.** |
| `bravoh/vibemix` repo | SignPath checklist | no — to be created this phase | created by `gh repo create` |

**Missing dependencies with no fallback:**
- `bravoh` GitHub org — blocking. Manual one-time step (Kaan, ~1 min) before the repo-creation task.

**Missing dependencies with fallback:**
- None.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 (added to `dev` dependency group) |
| Config file | none yet — add minimal `[tool.pytest.ini_options]` in `pyproject.toml` |
| Quick run command | `uv run pytest -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARCH-01 | `import vibemix` succeeds | unit (import) | `uv run python -c "import vibemix; print(vibemix.__version__)"` | Wave 0 |
| ARCH-01 | `vibemix.__version__ == "0.1.0-dev0"` | unit | `uv run pytest tests/test_package.py::test_version -x` | Wave 0 |
| ARCH-02 | All four protocols importable from `vibemix.platform` | unit | `uv run pytest tests/test_platform.py::test_protocols_exported -x` | Wave 0 |
| ARCH-02 | Each protocol is `@runtime_checkable` | unit | `uv run pytest tests/test_platform.py::test_runtime_checkable -x` | Wave 0 |
| ARCH-02 | Each protocol has required method names (introspection) | unit | `uv run pytest tests/test_platform.py::test_protocol_surface -x` | Wave 0 |
| ARCH-02 | No OS-specific module imported from `vibemix.platform.*` | unit | `uv run pytest tests/test_platform.py::test_no_os_leaks -x` (parse AST, fail if `pyobjc`, `Quartz`, `mss`, `mido`, `winreg` etc. appear in `platform/*.py`) | Wave 0 |
| ARCH-02 | `py.typed` marker exists in built wheel | integration | `uv run python -c "import importlib.resources, vibemix; assert (importlib.resources.files('vibemix') / 'py.typed').exists()"` | Wave 0 |
| DIST-04 | `LICENSE` exists at repo root + is Apache 2.0 | unit | `uv run pytest tests/test_license.py::test_apache_2_0 -x` (check file presence + first line matches Apache LICENSE header) | Wave 0 |
| DIST-04 | SPDX header in `src/vibemix/__init__.py` | unit | `uv run pytest tests/test_license.py::test_spdx_header -x` | Wave 0 |
| DIST-04 | `.planning/signpath-application.md` exists with all 9 sections filled | docs | `uv run pytest tests/test_signpath_checklist.py -x` (greps for section markers) | Wave 0 |
| (tooling) | `ruff check .` passes on `src/` | lint | `uv run ruff check src/` | Wave 0 |
| (tooling) | `ruff format --check .` passes on `src/` | format | `uv run ruff format --check src/` | Wave 0 |
| (tooling) | `uv sync` is reproducible from `uv.lock` | integration | manual: `rm -rf .venv && uv sync && uv run python -c "import vibemix"` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest -x` + `uv run ruff check src/`
- **Per wave merge:** `uv run pytest` + `uv run ruff check src/` + `uv run ruff format --check src/`
- **Phase gate:** Full suite green + manual `uv sync` reproducibility check before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/` directory — does not exist (POC has no tests). Create per task `01-task-tests-scaffold` or similar.
- [ ] `tests/__init__.py` — empty.
- [ ] `tests/conftest.py` — shared fixtures (probably empty for Phase 1).
- [ ] `tests/test_package.py` — version + import tests.
- [ ] `tests/test_platform.py` — protocol introspection + OS-leak guard.
- [ ] `tests/test_license.py` — LICENSE + SPDX guards.
- [ ] `tests/test_signpath_checklist.py` — checklist completeness.
- [ ] `[tool.pytest.ini_options]` block in `pyproject.toml`: `testpaths = ["tests"]`, `addopts = "-ra --strict-markers"`.
- [ ] Add `pytest>=8.0` to `[dependency-groups] dev` via `uv add --dev pytest`.

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 1 has no auth surface. |
| V3 Session Management | no | No sessions. |
| V4 Access Control | no | Local-only package skeleton. |
| V5 Input Validation | no | No external inputs at this phase — Protocol bodies are `...`. |
| V6 Cryptography | partial | `LICENSE` content is plain text. `.gitignore` is the only cryptographic-adjacent control — prevent `.env` (with `GEMINI_API_KEY`) from ever entering the repo. |
| V14 Configuration | yes | `pyproject.toml` declares no secrets; `.gitignore` covers `.env*` patterns. |

### Known Threat Patterns for the Phase 1 stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key in committed `.env` | Information disclosure | `.gitignore` excludes `.env` + `.env.*` with `!.env.example` carve-out. Phase 1 doesn't commit a `.env`. |
| Supply-chain attack via uv-resolved deps | Tampering | `uv.lock` pins exact versions + hashes. `uv sync --frozen` in CI (Phase 20). |
| License-violation by transitive dep | Repudiation | Apache 2.0 is compatible with all the runtime deps used (MIT, BSD, LGPL all compatible). Validate via `uv tree --format json` in Phase 19 when assembling NOTICE. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | SignPath OSS approval is ~1 week in 2026 (single GitHub-issue data point from `amd/gaia#732`, April 2026) | P0-4 | If actual SLA is back to 3 weeks, CONTEXT's buffer absorbs it — no impact. |
| A2 | Section 3 ("already released") of the SignPath form is non-blocking when applying with pre-release status, as long as expected artifacts are described in Section 7 | P0-4 | If SignPath rejects with "come back when you have a release", refile at Phase 11–13 — costs ~1 week of buffer. |
| A3 | `bravoh` GitHub org is fine on free plan for hosting one public OSS repo | P0-5 | If Kaan wants paid plan for SSO/SAML etc., that's a separate decision. Free plan is sufficient for OSS. |
| A4 | `pyobjc-framework-Quartz>=12.1` and friends have Python 3.12 wheels on PyPI in 2026 | P1-8 | Verify with `uv add` during executor's first task. POC uses 12.1 on Python 3.14 — strong signal 3.12 wheels also exist. |
| A5 | `livekit-agents 1.5.8` supports Python 3.12 (POC uses 3.14) | P1-8 | Verify with `uv sync` on the executor's first task. If 1.5.8 dropped 3.12, pin to whichever version supports both. |
| A6 | Apache 2.0 NOTICE file is not required when not vendoring third-party Apache-2.0 code | P2-10 | If a contributor adds vendored Apache-licensed code, NOTICE becomes mandatory — already deferred to Phase 19. |

## Open Questions for Planner

1. **`bravoh` GitHub org does not exist yet.**
   - What we know: `gh api orgs/bravoh` returns 404 (verified 2026-05-11). `gh` auth is to user `ozzaii`.
   - What's unclear: does Kaan create the org now, or use `ozzaii/vibemix` and transfer later?
   - Recommendation: Add a Phase 1 prerequisite — "Kaan creates `bravoh` GitHub org" — before the repo-creation task. Manual, ~1 minute. Avoids the SignPath URL-change risk.

2. **SignPath Section 3 "already released" gate.**
   - What we know: Phase 1 has no binaries; SignPath terms say project must be "released in the form that should be signed".
   - What's unclear: does pre-release status block approval, or just delay it?
   - Recommendation: Submit anyway with honest "alpha, binaries pending Phase 18 (~3 weeks)" framing. Worst case = wait until Phase 11-13 binary exists before resubmitting. Either way, 3-week buffer absorbs the risk.

3. **DCO / CLA timing for first external contributor.**
   - What we know: CONTEXT defers CONTRIBUTING (with DCO) to Phase 19.
   - What's unclear: if Phase 13 (mascot port) or Phase 14 (UI polish) accidentally attracts an external PR before Phase 19, the IP situation is ambiguous (PITFALLS P14).
   - Recommendation: Add a one-line `CONTRIBUTING.md` placeholder to Phase 1 that says "vibemix is currently in pre-release; we are not yet accepting external PRs. CONTRIBUTING with DCO arrives at Phase 19 / launch." Disables ambiguity until Phase 19 lands.

4. **README content depth at Phase 1.**
   - What we know: CONTEXT lists README as part of repo bootstrap but doesn't specify depth.
   - What's unclear: SignPath Section 1 ("Detailed description") needs a real product description — should we mirror that into README at Phase 1, or keep README terse and elaborate in the SignPath checklist alone?
   - Recommendation: Terse README at Phase 1 (snippet above). SignPath checklist has full description. README upgraded at Phase 19.

5. **Python 3.12 install for new contributors.**
   - What we know: macOS dev machine has Python 3.12.12 via Homebrew. `uv python install 3.12` works on any platform.
   - What's unclear: should README say "install Python 3.12 manually" or rely on `uv python install 3.12` auto-fetch?
   - Recommendation: Document `uv python install 3.12` as the canonical step. uv's managed Pythons are reproducible across contributors.

## Sources

### Primary (HIGH confidence — official docs, verified directly)
- [Creating projects | uv](https://docs.astral.sh/uv/concepts/projects/init/) — uv project scaffolding.
- [Structure and files | uv](https://docs.astral.sh/uv/concepts/projects/layout/) — uv.lock semantics.
- [Managing dependencies | uv](https://docs.astral.sh/uv/concepts/projects/dependencies/) — markers, optional deps, dep groups.
- [Hatch build configuration](https://hatch.pypa.io/latest/config/build/) — `packages` directive for src-layout.
- [Python 3.12 typing docs — Protocol](https://docs.python.org/3.12/library/typing.html#typing.Protocol) — Protocol semantics + `@runtime_checkable` slowness warning.
- [typing.python.org Protocols spec](https://typing.python.org/en/latest/spec/protocol.html) — current best-practice spec.
- [Ruff configuration docs](https://docs.astral.sh/ruff/configuration/) — pyproject.toml `[tool.ruff]` patterns.
- [gh repo create manual](https://cli.github.com/manual/gh_repo_create) — flag reference.
- [SignPath Foundation terms](https://signpath.org/terms.html) — OSS eligibility criteria.
- [SignPath community page](https://signpath.io/solutions/open-source-community) — application entry point.
- [Apache 2.0 — how to apply](https://www.apache.org/legal/apply-license.html) — LICENSE + appendix copyright block.
- [github/gitignore Python template](https://github.com/github/gitignore/blob/main/Python.gitignore) — base gitignore patterns.
- [PEP 561](https://peps.python.org/pep-0561/) — `py.typed` marker.
- [PEP 544](https://peps.python.org/pep-0544/) — Protocols / structural subtyping.

### Secondary (MEDIUM confidence — community sources, single-source data points)
- [SysManage SignPath prefilled application](https://sysmanage.org/SignPath/application-form-answers.html) — mirrors the live form's 9 sections.
- [amd/gaia issue #732](https://github.com/amd/gaia/issues/732) — single 2026 data point that approval takes ~1 week.

### Local verification
- `uv 0.10.6 (a91bcf268 2026-02-24)` — `uv --version`.
- `gh version 2.86.0` — `gh --version`.
- `python3.12 — 3.12.12 at /opt/homebrew/bin/python3.12` — `python3.12 --version`.
- `gh auth status` — authenticated as `ozzaii`, no `admin:org` scope.
- `gh api orgs/bravoh` — 404, org does not exist.
- `gh repo view bravoh/vibemix` — 404, repo does not exist.

## Metadata

**Confidence breakdown:**
- `uv` + `hatchling` toolchain: HIGH — verified against official docs and local `uv 0.10.6`.
- Protocol design: HIGH — verified against Python 3.12 typing docs + PEP 544 + lifted from existing POC behavior.
- SignPath application: MEDIUM — 9-section form structure mirrored from a community pre-fill resource (sysmanage.org); SLA data point is single-source (amd/gaia#732, April 2026).
- `bravoh` org / repo state: HIGH — verified directly with `gh api`.
- Pitfall mitigations: HIGH — all references map to existing entries in `.planning/research/PITFALLS.md`.

**Research date:** 2026-05-11
**Valid until:** ~2026-06-10 (uv / hatchling / ruff are fast-moving; 30-day half-life). SignPath data has higher half-life unless they change their program.
