# Phase 67: All Tests Pass — Research

**Researched:** 2026-05-23
**Domain:** Pytest test infrastructure · GitHub Actions matrix CI · Flake-hunt tooling · Static AST gates
**Confidence:** HIGH (every claim verified against the live repo state or official docs; CI-runner specifics verified against actions/runner-images issues)

## Summary

Phase 67 is **test infrastructure** — zero product code change. The work breaks into four orthogonal tracks: (a) **fix the 8 currently-red default tests** (TEST-01's *real* gate, see "Current State" below); (b) **triage the 65 opt-in tests** into Tier-A green / Tier-B `§V7-LIVE`-documented / Tier-C `flaky` (TEST-02); (c) **build two static gates** — `test_no_silent_skips.py` and `test_no_silent_flakes.py` — plus a 10× flake-hunt loop (TEST-03); (d) **ship `.github/workflows/full-test-matrix.yml`** with a `[OS × marker]` exclude-matrix and add a README badge (TEST-04).

The repo is in better shape than the CONTEXT made it sound — there are **zero `@pytest.mark.skip` decorators** (every skip is `skipif` with a reason already), **zero `@pytest.mark.xfail`** decorators in the wild, and **zero `@pytest.mark.flaky`** decorators (no quarantine to police yet — both gates are about *preventing* the rot, not cleaning up existing rot). However: **default `pytest -q` is RED today** (8 failures · 26 skipped · 4152 passed out of 4186 collected). TEST-01's success criterion #1 ("third-party engineer cloning `main` and running `pytest -q` sees exit code 0") cannot ship until those 8 are fixed.

**Primary recommendation:** Sequence the work as Wave 0 (fix the 8 reds + add `flaky` marker to `pyproject.toml`) → Wave 1 (build the two static gates + reason-tag audit) → Wave 2 (build `full-test-matrix.yml` with the OS × marker exclude grid + add badge) → Wave 3 (10× flake-hunt loop locally + on CI). Triage of the 65 opt-in tests happens *during* Wave 1 once we know the markers' real composition.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Test execution | Local dev (`uv run pytest`) | GitHub Actions runner | `uv` is the canonical runner per project CLAUDE.md; CI replicates the same invocation |
| Marker filter | `pyproject.toml [tool.pytest.ini_options]` | CI workflow `pytest -m "<marker>"` | Single source of truth (markers declared once, used everywhere) |
| Reason tagging | Test file (decorator-adjacent comments) | Static gate (`tests/repo/test_no_silent_skips.py`) | Source-adjacent for grep/audit; static gate enforces in CI |
| Flake quarantine | Test file (`@pytest.mark.flaky(reruns=N) # issue: https://…`) | Static gate (`tests/repo/test_no_silent_flakes.py`) | Same pattern as skip; flake decorator MUST carry an issue link or build fails |
| OS-specific test routing | `pytest.mark.skipif(sys.platform != …)` (already in use) | Workflow OS matrix (`runs-on: macos-13/macos-14/windows-latest`) | Test file declares intent; runner filters at the OS layer |
| External-clock blockers | `§V7-LIVE` section in `KAAN-ACTION-LEGAL.md` | `xfail(strict=False, reason=…)` adjacent to test | Decouples engineering-green from real-hardware-green; existing project pattern (§SHIP-V4, §RECALL-EAR, §ASSETS-DEMO-CUT) |
| Badge surfacing | README badges row (lines ~40-43) | GitHub Actions workflow status URL | Same pattern already used for `dep-audit.yml`, `sbom.yml` |

## Current State (verified 2026-05-23)

**Test collection:** 4186 collected · 65 deselected via opt-in marker filter · 4121 in default run.

**Default `pytest -q` (HEAD verified live):** 8 FAILED · 4152 PASSED · 26 SKIPPED · 13 warnings · 218 s.

| Failing test | File | Likely cause |
|--------------|------|--------------|
| `test_wire13_anti_slop_disabled_path_passes_none_kwargs` | `tests/coach/test_main_anti_slop_wiring.py` | Anti-slop wiring kwarg drift |
| `test_tag_regex_unchanged_in_this_plan` | `tests/repo/test_cut_release_invokes_bravoh_server.py` | Release script regex pin drift |
| `test_state_md_phase_16_line_is_annotated_retired` | `tests/repo/test_gate_42_hybrid_in_force.py` | STATE.md update drift (v7.0 rewrote the file) |
| `test_readme_feature_matrix_in_sync` | `tests/repo/test_readme_feature_matrix_sync.py` | README feature matrix lags milestone progress |
| `test_feature_matrix_includes_all_completed_phases` | `tests/repo/test_readme_feature_matrix_sync.py` | Same — needs phases 67-70 added or sentinel relaxed |
| `test_cut_release_accepts_valid_rc_tag_shape` | `tests/scripts/test_cut_release_preflight.py` | Likely sister of the regex pin drift above |
| `test_cut_release_blocks_on_missing_milestone_audit` | `tests/scripts/test_cut_release_preflight.py` | v6.0/v7.0 milestone audit path drift |
| `test_smoke_08_main_source_wires_cache_create_with_graceful_degradation` | `tests/test_main_smoke.py` | Smoke test against current `main()`; likely refactor drift |

**These 8 are the actual blocker for TEST-01 success criterion #1.** [VERIFIED: live `pytest -q` run 2026-05-23]

**Existing markers in repo (verified by grep):**

| Marker | Module-level (`pytestmark = …`) | Decorator-level | Total |
|--------|------|------|-------|
| `macos_audio` | 1 (`test_audio_macos_live.py`) | 4 | 5 |
| `windows_only` | 0 (uses `skipif(sys.platform != 'win32')`) | 6 | 6 |
| `integration` | 0 | 11 | 11 |
| `slow` | 0 | 4 | 4 |
| `e2e` | 3 | 19 | 22 |
| `cli` | 2 | 10 | 12 |
| `network` | 0 | 5 | 5 |
| `parity` (already declared) | varies | varies | not in opt-in grid |

[VERIFIED: `grep -rEn '@pytest.mark.(macos_audio|windows_only|integration|slow|e2e|cli|network)' tests/`]

**Existing skip/xfail patterns:**

- `@pytest.mark.skip` (unconditional): **0** — none in the repo. [VERIFIED]
- `@pytest.mark.skipif`: **28** — all carry `reason=` already. [VERIFIED]
- `@pytest.mark.xfail`: **0** — no xfail decorators exist. [VERIFIED]
- `@pytest.mark.flaky`: **0** — no quarantine decorators exist. [VERIFIED]
- `pytest.skip(...)` (runtime skip inside test body): at least 1 (`tests/llm/test_tts_3_1.py:183`). [VERIFIED]
- Module-level `pytestmark = pytest.mark.skipif(sys.platform != …)`: **6** files. [VERIFIED]

**Implication:** the "reason tagging" enforcement work for TEST-01 is mostly about *pinning the current state* (every existing skipif already has a reason) — the static gate is to prevent *future* drift, not to retroactively tag a sea of unmarked skips. **This is a smaller delta than CONTEXT.md implied.**

## Standard Stack

### Core (existing — reused, not added)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=8.0 (declared in dev group) | Test runner | Already canonical; markers declared in `[tool.pytest.ini_options]` |
| uv | 0.10.6 (verified local) | Python runner + lockfile | Project canonical runner per CLAUDE.md `Commands` section |
| pytest-mock | >=3.15.1 | Mocking | Already in dev group |
| `astral-sh/setup-uv@v3` | v3.2.4 SHA-pinned | CI uv installer | Existing project pattern (`eval.yml:44`, `release.yml:286`) |
| `actions/setup-python@v5` | v5.6.0 SHA-pinned | CI Python | Existing project pattern |
| `actions/checkout@v4` | v4.3.1 SHA-pinned | CI checkout | Existing project pattern |

### Supporting (NEW — add only if Wave 3 flake-hunt finds non-determinism)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest-repeat` | latest stable | Run a test N times to find flakes | TEST-03's 10× re-run loop — *only* if a shell loop isn't sufficient |

**Decision:** Default to a **plain shell loop** for the 10× flake-hunt (`for i in $(seq 1 10); do uv run pytest -q || break; done`) — no new dependency required. Only add `pytest-repeat` if Wave 3 reveals a flaky test that needs single-test-N-times stress. [CITED: pytest docs flaky-tests page] [CITED: pytest-repeat README, github.com/pytest-dev/pytest-repeat]

**Do NOT add `pytest-rerunfailures`.** Per CONTEXT.md "trust the audio (and the real hardware) more than retries" rule + Tier-B-over-Tier-C default: auto-retrying flakes in CI is the failure mode this phase is built to prevent, not the tool to adopt. If a flake exists, it becomes `@pytest.mark.flaky` with an issue link — not silently swallowed by reruns. [CITED: github.com/pytest-dev/pytest-rerunfailures]

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Shell loop for 10× | `pytest-repeat --count=10` | New dep adds 0 value over shell loop; Tier-B-over-C philosophy says detect-don't-paper-over |
| `pytest-rerunfailures` for `flaky` | Hand-rolled `@pytest.mark.flaky(reruns=N)` | Rerunfailures retries silently in CI; the phase is explicitly anti-retry. Use a *custom* `flaky` marker that does NOT auto-retry — it just tags + the static gate enforces the issue link |
| `pytest-randomly` (test-order shuffle) | Existing fixed order | Out of scope for P67; could be P68+ polish |

**Installation (Wave 0 only — if we choose `pytest-repeat`):**

```bash
uv add --group dev "pytest-repeat>=0.9"
```

**Recommendation:** SKIP this install. Use shell loop. Zero net-new deps fits the v7.0 milestone rule "Zero new dependencies."

**Version verification:** All existing deps already verified against `uv.lock`. No new packages proposed.

## Package Legitimacy Audit

**No new packages installed by this phase.** The only candidate (`pytest-repeat`) is rejected above. Audit table is empty by design.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (none) | — | — | — | — | — | No new packages |

**Packages removed due to slopcheck [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌──────────────────────────────────────────┐
                    │  Developer machine OR GitHub Actions     │
                    │  runner (macos-13/macos-14/win-latest)   │
                    └─────────────────┬────────────────────────┘
                                      │
                                      │ uv run pytest -m "<marker>"
                                      │
                ┌─────────────────────▼─────────────────────┐
                │   pyproject.toml [tool.pytest.ini_options] │
                │   - testpaths = ["tests"]                  │
                │   - markers = [macos_audio, windows_only,  │
                │                integration, slow, e2e,     │
                │                cli, network, flaky NEW]    │
                │   - addopts = "-ra --strict-markers"       │
                └─────────────────────┬─────────────────────┘
                                      │
                                      │ collect 4186 tests
                                      │
                ┌─────────────────────▼─────────────────────┐
                │   tests/ tree                              │
                │   - conftest.py (existing fixtures)        │
                │   - Per-test markers:                      │
                │       @pytest.mark.skipif(reason=…) [28]   │
                │       @pytest.mark.<opt-in> [65 deselected]│
                │       @pytest.mark.flaky [0 today; gated]  │
                └─────────────────────┬─────────────────────┘
                                      │
                ┌─────────────────────▼─────────────────────┐
                │   Static gates (tests/repo/)               │
                │   - test_no_silent_skips.py     NEW        │
                │     ↳ AST-scans for skip/skipif/xfail      │
                │       without an adjacent `# reason:`      │
                │   - test_no_silent_flakes.py    NEW        │
                │     ↳ AST-scans for @pytest.mark.flaky     │
                │       without `# issue: https://...`       │
                │   - test_repo_scrub.py (existing pattern)  │
                └─────────────────────┬─────────────────────┘
                                      │
                ┌─────────────────────▼─────────────────────┐
                │   .github/workflows/full-test-matrix.yml   │
                │   NEW                                       │
                │                                            │
                │   strategy.matrix:                         │
                │     os: [macos-13, macos-14, win-latest]   │
                │     marker: [default, macos_audio,         │
                │              windows_only, integration,    │
                │              slow, e2e, cli, network]      │
                │     exclude:                               │
                │       - {os: windows-latest, marker: macos_audio}  │
                │       - {os: macos-13/14, marker: windows_only}    │
                │                                            │
                │   Status badge → README badges row         │
                └─────────────────────┬─────────────────────┘
                                      │
                ┌─────────────────────▼─────────────────────┐
                │   Documented failure-modes for the 65      │
                │   opt-in tests that can't run in CI:       │
                │   KAAN-ACTION-LEGAL.md  §V7-LIVE  NEW      │
                │   (real-hardware-required entries with     │
                │    concrete fix-path)                      │
                └────────────────────────────────────────────┘
```

### Recommended Project Structure (delta only)

```
.github/workflows/
├── full-test-matrix.yml                   # NEW — TEST-04 deliverable
└── (existing 22 workflows unchanged)

tests/repo/
├── test_no_silent_skips.py                # NEW — TEST-01 reason-tag gate
├── test_no_silent_flakes.py               # NEW — TEST-03 flake-quarantine gate
└── (existing 26 repo-presence tests unchanged)

pyproject.toml
└── [tool.pytest.ini_options]
    └── markers += ["flaky: …"]            # NEW marker entry

KAAN-ACTION-LEGAL.md
└── §V7-LIVE                                # NEW section — Tier-B failure-mode entries

README.md
└── (badges row, ~line 43)
    └── [![Full Test Matrix](https://img.shields.io/github/actions/workflow/status/bravoh-ai/vibemix/full-test-matrix.yml?branch=main&label=tests&style=flat-square)](https://github.com/bravoh-ai/vibemix/actions/workflows/full-test-matrix.yml)  # NEW
```

### Pattern 1: Static AST gate (existing project idiom)

**What:** Use `pathlib` + tokenize/regex to walk tracked source and assert structural invariants.
**When to use:** Anytime you need "no future commit can silently introduce X."
**Example (from existing `tests/repo/test_repo_scrub.py`, abridged):**

```python
# Source: /Users/ozai/projects/dj-set-ai/tests/repo/test_repo_scrub.py (existing)
def _git_ls_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT,
                         capture_output=True, text=True, check=True)
    return [line for line in out.stdout.splitlines() if line]

def test_no_bak_files_are_tracked() -> None:
    bak_files = [p for p in _git_ls_files() if p.endswith(".bak")]
    unexpected = [p for p in bak_files if Path(p).name not in POC_EXEMPT]
    assert not unexpected, f"Unexpected tracked .bak files: {unexpected}. …"
```

**New gate template** (TEST-01 — `test_no_silent_skips.py`):

```python
# tests/repo/test_no_silent_skips.py
from __future__ import annotations
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TESTS_DIR = REPO_ROOT / "tests"

# Decorators we require an adjacent `# reason:` comment for.
# (skipif already requires reason= kwarg via pytest; this gate catches
# the bare @pytest.mark.skip / @pytest.mark.xfail forms that don't.)
SKIP_DECORATOR_PATTERN = re.compile(
    r"^\s*@pytest\.mark\.(skip|xfail)\b(?!\w)"
)

def _has_reason_nearby(lines: list[str], idx: int) -> bool:
    """A `# reason:` comment lives within 2 lines above or on the same line."""
    for offset in (-2, -1, 0):
        i = idx + offset
        if 0 <= i < len(lines) and "# reason:" in lines[i]:
            return True
    # Also accept reason= kwarg in the decorator argument list (multi-line)
    j = idx
    while j < min(idx + 4, len(lines)):
        if "reason=" in lines[j]:
            return True
        j += 1
    return False

def test_no_silent_skips() -> None:
    offenders: list[str] = []
    for py in TESTS_DIR.rglob("*.py"):
        lines = py.read_text(encoding="utf-8").splitlines()
        for i, ln in enumerate(lines):
            if SKIP_DECORATOR_PATTERN.match(ln) and not _has_reason_nearby(lines, i):
                offenders.append(f"{py.relative_to(REPO_ROOT)}:{i+1}: {ln.strip()}")
    assert not offenders, (
        "Silent skip/xfail decorators (no `# reason:` adjacent or `reason=` "
        f"kwarg within 4 lines):\n  " + "\n  ".join(offenders)
    )
```

**New gate template** (TEST-03 — `test_no_silent_flakes.py`):

```python
# tests/repo/test_no_silent_flakes.py
from __future__ import annotations
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TESTS_DIR = REPO_ROOT / "tests"

FLAKY_DECORATOR_PATTERN = re.compile(r"^\s*@pytest\.mark\.flaky\b")
ISSUE_LINK_PATTERN = re.compile(
    r"#\s*issue:\s*https://github\.com/[\w.\-]+/[\w.\-]+/issues/\d+"
)

def test_no_silent_flakes() -> None:
    offenders: list[str] = []
    for py in TESTS_DIR.rglob("*.py"):
        lines = py.read_text(encoding="utf-8").splitlines()
        for i, ln in enumerate(lines):
            if FLAKY_DECORATOR_PATTERN.match(ln):
                # Issue link must live within 3 lines above or below the decorator
                window = lines[max(0, i-3): i+4]
                if not any(ISSUE_LINK_PATTERN.search(w) for w in window):
                    offenders.append(
                        f"{py.relative_to(REPO_ROOT)}:{i+1}: "
                        f"@pytest.mark.flaky without `# issue: https://github.com/.../issues/N` comment within 3 lines"
                    )
    assert not offenders, (
        "Silent flaky decorators (every quarantine must link a tracking issue):\n  "
        + "\n  ".join(offenders)
    )
```

### Pattern 2: GitHub Actions matrix with exclude (industry standard)

**What:** Declare `os × marker` cartesian product, then `exclude` impossible combinations.
**When to use:** Cross-OS testing where some tests are OS-specific.
**Example:**

```yaml
# .github/workflows/full-test-matrix.yml (NEW — Phase 67 TEST-04 deliverable)
name: Full Test Matrix

on:
  push:
    branches: [main]
  pull_request:

concurrency:
  group: full-test-matrix-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  test:
    name: ${{ matrix.os }} · ${{ matrix.marker }}
    runs-on: ${{ matrix.os }}
    timeout-minutes: 30
    strategy:
      fail-fast: false   # one OS failing doesn't kill the rest
      matrix:
        os: [macos-13, macos-14, windows-latest]
        marker:
          - default
          - macos_audio
          - windows_only
          - integration
          - slow
          - e2e
          - cli
          - network
        exclude:
          # macos_audio requires BlackHole + CoreAudio — Windows can't run it
          - os: windows-latest
            marker: macos_audio
          # windows_only is sys.platform == 'win32' gated — Mac runners skip
          - os: macos-13
            marker: windows_only
          - os: macos-14
            marker: windows_only
    steps:
      - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1

      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0
        with:
          python-version: '3.12'

      - uses: astral-sh/setup-uv@caf0cab7a618c569241d31dcd442f54681755d39 # v3.2.4

      - name: Install deps
        run: uv sync --frozen --group dev

      - name: Run tests (default)
        if: matrix.marker == 'default'
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: uv run pytest -q --tb=short

      - name: Run tests (opt-in marker — ${{ matrix.marker }})
        if: matrix.marker != 'default'
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: uv run pytest -q --tb=short -m "${{ matrix.marker }}"
```

[CITED: oneuptime.com/blog/post/2025-12-20-github-actions-matrix-include-exclude/view, github.com/orgs/community/discussions/26253]

### Pattern 3: Tier-B `§V7-LIVE` entry (existing project idiom)

**What:** When a test can't pass in CI but explains itself with a real-hardware path, add an entry to `KAAN-ACTION-LEGAL.md §V7-LIVE` and `xfail(strict=False)` the test.
**When to use:** Tests that need BlackHole/FLX4/real-VM/etc. — i.e. environmental constraints CI can't satisfy.
**Example structure** (mirrors existing §SHIP-V4 / §RECALL-EAR / §ASSETS-DEMO-CUT):

```markdown
## §V7-LIVE — v7.0 Live-Hardware Discharge Surface

Each entry below documents a test (or group of tests) that cannot run on
GitHub-hosted CI runners and requires Kaan's real hardware to confirm.
Engineering side ships `xfail(strict=False)` with a `# reason:` adjacent;
this section is the fix-path for the live confirmation.

### §V7-LIVE-01 — `macos_audio` tests on `macos-13/14` hosted runners

**Tests:** `tests/test_audio_macos_live.py` (5 cases — module-level `pytestmark`)
**Why it can't ship green in CI:** Installing BlackHole 2ch on hosted macOS
runners requires a system reboot (actions/runner-images#11746). Hosted
runners don't reboot mid-job; the kext never loads; the input device never
appears in CoreAudio's device list.
**Fix path:** Kaan runs `uv run pytest -m macos_audio` on his own Mac (where
BlackHole is already installed). Record the run in this section with date +
SHA + result.
**Sign-off:** ☐ pending · ☐ done — date: ____ · SHA: ____ · result: ____

### §V7-LIVE-02 — `windows_only` tests on a Windows 11 VM

**Tests:** `tests/test_*_windows_live.py` (3 files — `test_audio` / `test_midi` / `test_screen` / `test_track`)
**Why it can't ship green in CI alone:** `windows-latest` (Win Server 2022)
covers some paths, but WASAPI loopback edge cases + SMTC + COM device-change
notifications need a real Win11 desktop OS (not Server). Hosted runners are
Server.
**Fix path:** Kaan runs `uv run pytest -m windows_only` on the Parallels/UTM
Win 11 VM.
**Sign-off:** ☐ pending · ☐ done — date: ____ · SHA: ____ · result: ____

[…etc per failure-mode discovered during plan execution…]
```

### Anti-Patterns to Avoid

- **Combining markers into one `pytest -m` run** (`-m "macos_audio or integration"`). CONTEXT.md decision: per-marker isolation is the point — a failure must be attributable to the marker, not lost in a soup. Use one job per marker. [CITED: 67-CONTEXT.md `### Marker Grid Coverage`]
- **Auto-retry as flake-handling** (`pytest-rerunfailures`). CONTEXT.md: "Default to Tier B over Tier C. Trust the audio (and the real hardware) more than retries." Reruns silently swallow real bugs.
- **Trying to install BlackHole on hosted macOS runners.** It requires a reboot (verified via actions/runner-images#11746). Use mocks in CI; `§V7-LIVE` the live path.
- **Treating `windows-latest` as Windows 11.** It's Windows Server 2022. Some tests genuinely need a desktop SKU — `§V7-LIVE` those.
- **Putting the `flaky` marker in `addopts` or hard-coding rerun counts in CI.** The marker is a *quarantine signal* with a tracking issue, not a magical auto-retry. Static gate enforces the issue link.
- **One giant job that runs everything.** CONTEXT decision: per-marker job. Failures isolate; CI minutes are spent where they matter.
- **`fail-fast: true`.** One OS dropping out shouldn't kill the others — we want to see all failure surfaces.
- **Skipping the existing CI workflows.** Don't conflate `full-test-matrix.yml` with `eval.yml` or any per-feature workflow — CONTEXT.md says "separate workflow from any existing test workflow."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-OS test orchestration | Custom shell scripts driving SSH to remote OS boxes | GitHub Actions `strategy.matrix` with `runs-on: ${{ matrix.os }}` | Standard, observable, free; gives a per-job badge target |
| Marker filtering | A custom `conftest.py` collection hook | `pytest -m "<marker>"` | Already declared in `pyproject.toml`; pytest handles it natively |
| Workflow status badge | Custom SVG generator | `img.shields.io/github/actions/workflow/status/...` | Project already uses this pattern (8+ existing badges in README); zero new infra |
| AST scanning for decorator presence | Custom `ast.NodeVisitor` walker | Regex + line context (existing `test_repo_scrub.py` pattern) | Project's existing repo-presence tests use regex over tokenize-stripped source; pattern works |
| Concurrency cancellation | Custom GH API calls | `concurrency.group` + `cancel-in-progress: true` | One-line YAML; already used in `dep-audit.yml:49-51` |

**Key insight:** Every component of P67 has an *exact* existing-repo template. `test_repo_scrub.py` is the static gate prior art. `dep-audit.yml` is the workflow shape prior art. The badges row in README has 8+ existing entries to copy. The phase is overwhelmingly about *applying known patterns at known seams*, not inventing new infrastructure.

## Runtime State Inventory

> Not a rename/refactor/migration phase — Phase 67 adds CI infrastructure + static gates + reason tagging. No databases, no service registrations, no installed artifacts to update beyond the `flaky` marker entry in `pyproject.toml`. **Section omitted as not applicable.**

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | Test runner (local + CI) | ✓ (local) | 0.10.6 | `python3 -m pytest` direct |
| Python 3.12 | Runtime | ✓ (`.venv` is 3.12.x) | 3.12.x | — |
| `gh` CLI | Optional — for opening the tracking issues for flaky markers | ✓ | 2.86.0 | Manual GH web UI |
| `git` | All static gates use `git ls-files` | ✓ | system | — |
| `actions/setup-uv@v3.2.4` (SHA `caf0cab…`) | CI uv install | n/a (CI-only) | pinned | — |
| `actions/setup-python@v5.6.0` (SHA `a26af69…`) | CI Python | n/a (CI-only) | pinned | — |
| `actions/checkout@v4.3.1` (SHA `34e1148…`) | CI checkout | n/a (CI-only) | pinned | — |
| BlackHole 2ch on hosted macOS runners | Live audio tests in CI | **✗** (requires reboot) | — | **Route to §V7-LIVE; xfail in CI** |
| Windows 11 desktop SKU on hosted runners | WASAPI edge-case + SMTC live tests | **✗** (`windows-latest` is Server 2022) | — | **Route to §V7-LIVE; xfail in CI** |
| Pioneer DDJ-FLX4 USB | MIDI live tests | **✗** (no hardware on runners) | — | **Route to §V7-LIVE; xfail in CI** |
| `nowplaying-cli` on macOS | Track-poll tests | likely ✗ on hosted (not in default image) | — | Install via brew in workflow, or mock |

**Missing dependencies with fallback:** all four hardware/audio gaps route to `§V7-LIVE` — engineering side ships green in CI with mocks; live confirmation rides Kaan-action clock per CONTEXT decision "Tier B" triage.

**Missing dependencies with no fallback:** none — the phase is engineering-shippable in CI under the autonomous-mode contingency baked into CONTEXT.md.

**`nowplaying-cli` on CI:** It's a Homebrew formula — can install via `brew install nowplaying-cli` step in the workflow. Verify availability during plan execution; if it works, great; if not, `§V7-LIVE` the affected tests.

## Common Pitfalls

### Pitfall 1: BlackHole reboot requirement
**What goes wrong:** Adding `brew install blackhole-2ch` to the CI workflow appears to succeed, but tests still fail with "no input device found".
**Why it happens:** BlackHole installs a kernel extension (kext) that requires a reboot to load. Hosted GH runners are ephemeral and don't reboot mid-job. The kext never loads.
**How to avoid:** Don't try to install BlackHole on hosted macOS runners. Use the in-repo mock pattern (sounddevice mocks already present in `tests/conftest.py` + per-test). Route real-BlackHole tests to `§V7-LIVE`.
**Warning signs:** A "skip-with-reboot-banner" log line in CI output. [CITED: github.com/actions/runner-images/issues/11746]

### Pitfall 2: `windows-latest` ≠ Windows 11
**What goes wrong:** Tests that assume Win 11 SKU (e.g. modern SMTC behavior, Win 11-only WASAPI surface) fail mysteriously on `windows-latest`.
**Why it happens:** `windows-latest` is Windows Server 2022. Some desktop-OS-only APIs behave differently.
**How to avoid:** Document each `windows_only` test's actual SKU dependency. If it truly needs Win 11 desktop, `§V7-LIVE` it. If it works on Server 2022, great — ship green in CI.
**Warning signs:** Test passes locally on Kaan's Win 11 VM but fails on `windows-latest` with COM/SMTC/WinRT errors.

### Pitfall 3: `--strict-markers` + new marker = collection error
**What goes wrong:** Adding `@pytest.mark.flaky` to a test before declaring `flaky` in `pyproject.toml` `markers = [...]` → pytest errors out with "PytestUnknownMarkWarning treated as error" because `addopts` already has `--strict-markers`.
**Why it happens:** Existing `pyproject.toml` already uses `--strict-markers` (verified line 198).
**How to avoid:** Wave 0 MUST add `"flaky: quarantined non-deterministic test; carries a `# issue: https://...` link enforced by tests/repo/test_no_silent_flakes.py"` to the markers list *before* any test uses the marker.

### Pitfall 4: Concurrency-group collisions across workflows
**What goes wrong:** Two workflows both define `group: ${{ github.ref }}` — runs from workflow A cancel runs from workflow B.
**Why it happens:** Concurrency groups are repo-wide, not per-workflow.
**How to avoid:** Use `group: full-test-matrix-${{ github.ref }}` (prefix with workflow name). Existing `dep-audit.yml:50` uses `dep-audit-${{ github.ref }}` for the same reason.

### Pitfall 5: Badge URL points at a non-existent default branch
**What goes wrong:** Badge URL has `?branch=main` but the workflow has never run on `main` yet → shields.io returns "no status" (gray).
**Why it happens:** The badge needs at least one workflow run on the named branch.
**How to avoid:** Ship the workflow YAML + push to `main` first; *then* add the README badge line in a separate commit (or accept a brief gray-badge window).

### Pitfall 6: `fail-fast: true` hides cross-OS failure patterns
**What goes wrong:** macOS-13 fails first, the whole matrix cancels, you never learn whether Windows would have failed too.
**Why it happens:** Default `strategy.fail-fast` is `true`.
**How to avoid:** Set `fail-fast: false` (matches the existing `release.yml:256` pattern).

### Pitfall 7: Triaging 65 opt-in tests *before* fixing the 8 reds
**What goes wrong:** Spending a wave on Tier-A/B/C triage while the default `pytest -q` is still red. TEST-01 SC#1 says "third-party engineer runs `pytest -q` and sees 0". That blocks before triage.
**How to avoid:** Wave 0 = fix the 8 reds. Wave 1+ = triage opt-in. Order matters.

### Pitfall 8: Counting "skips with `reason=`" as "covered by the gate"
**What goes wrong:** Writing the static gate to require a `# reason:` comment, then discovering that the existing 28 `skipif` markers all use the `reason=` *kwarg* (not a comment) → gate immediately fires red on existing tests.
**How to avoid:** Gate must accept *either* a `# reason:` comment within 2 lines *or* a `reason=` kwarg within ~4 lines of the decorator. The pattern in `tests/llm/test_tts_3_1.py:164-170` (multi-line skipif with reason= split across lines) must pass.

## Code Examples

### TEST-01 — Mark a Tier-B failure (xfail with §V7-LIVE pointer)

```python
# Pattern: when a test is engineering-correct but CI can't satisfy its env
# Source: project convention modeled on existing skipif-with-reason pattern

import pytest

# reason: BlackHole 2ch kext can't load on hosted macOS runners
#         (actions/runner-images#11746 — requires reboot).
#         Live confirmation rides KAAN-ACTION-LEGAL.md §V7-LIVE-01.
@pytest.mark.macos_audio
@pytest.mark.xfail(
    strict=False,
    reason="hosted-runner BlackHole kext load — see §V7-LIVE-01",
)
def test_blackhole_input_appears_in_coreaudio_device_list():
    ...
```

### TEST-03 — Mark a flaky test (issue link enforced)

```python
# Pattern: quarantine a non-deterministic test with a tracking issue
# Source: NEW marker introduced by P67 Wave 0

import pytest

# issue: https://github.com/bravoh-ai/vibemix/issues/123
@pytest.mark.flaky
def test_known_flaky_thing():
    ...
```

The static gate `tests/repo/test_no_silent_flakes.py` will fail the build if the `# issue: https://...` comment is missing within 3 lines of the decorator.

### TEST-04 — Add the badge to README badges row

```markdown
<!-- Insert after the existing badges row (around line 43) -->
<a href="https://github.com/bravoh-ai/vibemix/actions/workflows/full-test-matrix.yml"><img alt="full test matrix" src="https://img.shields.io/github/actions/workflow/status/bravoh-ai/vibemix/full-test-matrix.yml?label=tests&branch=main&style=flat-square" /></a>
```

This exactly matches the existing badge format in `README.md:40-43`.

### Wave 0 — Add the `flaky` marker to `pyproject.toml`

```toml
# pyproject.toml [tool.pytest.ini_options] markers list — append this line:
"flaky: quarantined non-deterministic test; carries a `# issue: https://...` link enforced by tests/repo/test_no_silent_flakes.py",
```

### Wave 3 — Local 10× flake-hunt loop

```bash
# Run the default test suite 10 times consecutively; bail on first failure.
# Total expected time: ~36 minutes (3.6 min per run × 10) — run overnight.

set -euo pipefail
for i in $(seq 1 10); do
    echo "=== Run $i/10 ==="
    uv run pytest -q --tb=line
done && echo "10× GREEN — flake-hunt clean"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@pytest.mark.skip("reason")` (positional) | `@pytest.mark.skipif(cond, reason="…")` | pytest 4.0+ (long-standing) | Already used; no change needed |
| Implicit markers (free-form strings) | `--strict-markers` + declared `markers = [...]` | pytest 6.0+ | Already declared in pyproject.toml line 198 |
| `pytest-rerunfailures` (auto-retry flakes) | Quarantine + issue link + fix | CONTEXT.md "Tier B over C" | We diverge from industry default — by design |
| Single CI job runs all tests | Per-marker job in matrix | This phase | Failures isolate; CI minutes only spent on real isolation |
| `macos-latest` (Apple Silicon since GitHub deprecation 2024-Q4) | `macos-13` (Intel) + `macos-14` (AS) explicit | CONTEXT decision | Both architectures matter for `sounddevice` / CoreAudio |

**Deprecated/outdated:**
- Bare `@pytest.mark.skip` without reason — never used in this repo; gate prevents future drift.
- BlackHole installation in hosted CI — known broken since 2024; route to `§V7-LIVE`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The 8 currently-failing default tests are fixable without changing product code | Current State table | If any is a real product regression that requires a coach/runtime change, that change is OUT OF SCOPE for v7.0 (zero product capability) — the test would need to xfail with a v7.1 issue, not the codepath fixed |
| A2 | `nowplaying-cli` can be installed on hosted `macos-13`/`macos-14` runners | Environment Availability | If `brew install nowplaying-cli` fails or the binary is sandbox-blocked, the affected tests route to §V7-LIVE — minor scope increase only |
| A3 | The `flaky` custom marker does NOT need to auto-retry (it's pure tagging) | Standard Stack — Alternatives | If Kaan wants flakes to auto-retry once in CI for human-friendly green badges, we'd need `pytest-rerunfailures` after all — but CONTEXT.md explicitly says "trust the audio more than retries" so the assumption holds |
| A4 | The README badge order/grouping is flexible (we can append anywhere in the badges row) | Architecture Patterns | None — visual taste decision; Kaan reviews on first PR |
| A5 | `GEMINI_API_KEY` is already a GitHub Secret (used by `eval.yml`) and is sufficient for the matrix workflow | Pattern 2 example YAML | Verified `eval.yml:61` references it. HIGH confidence |
| A6 | "macOS-only tests" can all be expressed via `sys.platform == 'darwin'` skipif (no test needs hardware-specific gating beyond platform string) | Pattern 2 example YAML | Most tests already use this idiom (6 module-level `skipif`s verified). Edge cases (e.g. Apple-Silicon-only) would need a `platform.machine()` check; flag if found during execution |
| A7 | `pytest-repeat` is not needed (shell loop suffices for Wave 3) | Standard Stack | If a flake only surfaces with internal pytest state reset (rare), shell loop won't catch it. Recommended: try shell loop first; add `pytest-repeat` only on actual evidence |
| A8 | `KAAN-ACTION-LEGAL.md §V7-LIVE` is a NEW section to create (it does not exist today; verified via grep) | Architecture Patterns Pattern 3 | Confirmed — no `§V7-LIVE` text in the file. Plan must include "create §V7-LIVE section" as a task |

## Open Questions

1. **Should `default` matrix job run on all three OSes or just one?**
   - What we know: CONTEXT says "per-marker × per-OS" matrix; running `default` on all three catches OS-specific regressions in the default suite (which is what TEST-01 is about).
   - What's unclear: nothing — recommend running `default` on all three; it's the cheapest job (~3.5 min × 3 OSes) and surfaces the most.
   - Recommendation: include `default` on all 3 OSes, no exclude entries.

2. **What's the `timeout-minutes` per job?**
   - What we know: existing workflows use 8-30 min depending on workload. Default `pytest -q` runs in ~3.5 min locally; with CI overhead, ~15 min ceiling is safe.
   - Recommendation: `timeout-minutes: 30` (matches `eval.yml:27`).

3. **Does `tests/repo/test_no_silent_skips.py` already exist somewhere I missed?**
   - What we know: `find tests -name "test_no_silent*"` returned 0 hits. Verified missing.
   - Recommendation: create both static gates from scratch. No conflict.

4. **How will the 65 opt-in tests sort into Tier A/B/C?**
   - What we know today (rough estimate from `pytestmark` distribution): the `_live.py` files (audio/midi/screen/track Mac + Win) are mostly Tier B (real hardware required); `e2e`/`cli`/`network`/`integration` are mostly Tier A (CI can run them with mocks or live API keys).
   - What's unclear: which of `e2e`/`integration` tests truly need real services vs. can be mocked.
   - Recommendation: defer triage to plan execution Wave 1 — run each marker grid one-by-one on Kaan's Mac, classify each failure.

5. **Should `tests/repo/test_no_silent_skips.py` also enforce `skipif` has `reason=`?**
   - What we know: pytest already enforces `reason=` for `skipif` at collection time (it's a required kwarg via `--strict-markers`-ish convention). All 28 existing skipif markers have a reason verified.
   - Recommendation: gate only `@pytest.mark.skip` and `@pytest.mark.xfail` (the ones pytest doesn't intrinsically force). Skipif is already covered by pytest itself.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8.0 (declared dev dep) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest -q` |
| Full suite command (default + all opt-in markers) | `uv run pytest -q && for m in macos_audio windows_only integration slow e2e cli network; do uv run pytest -q -m "$m"; done` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| TEST-01 | `pytest -q` exits 0 (default suite green) | suite | `uv run pytest -q` | ✓ (suite exists; currently 8 failing) |
| TEST-01 | Every skip/xfail/xpass carries `# reason:` or `reason=` | static | `uv run pytest tests/repo/test_no_silent_skips.py -v` | ❌ Wave 1 — NEW file |
| TEST-02 | Each opt-in marker exits green on Mac + Win | marker suite | `uv run pytest -q -m "<marker>"` × 7 markers × 2 OSes | partial (existing tests; some need triage) |
| TEST-02 | Each Tier-B failure has a §V7-LIVE entry | doc presence | `grep "§V7-LIVE" KAAN-ACTION-LEGAL.md` + per-test xfail reason | ❌ Wave 1 — NEW section |
| TEST-03 | 10× consecutive `pytest -q` is 100% green | meta-suite | `for i in $(seq 1 10); do uv run pytest -q || break; done` | ✓ (runnable today against current 8-red baseline; expected to pass after Wave 0) |
| TEST-03 | `@pytest.mark.flaky` decorators carry `# issue:` link | static | `uv run pytest tests/repo/test_no_silent_flakes.py -v` | ❌ Wave 1 — NEW file |
| TEST-03 | `flaky` marker declared in pyproject | static | `grep '"flaky:' pyproject.toml` | ❌ Wave 0 — NEW line in markers list |
| TEST-04 | `.github/workflows/full-test-matrix.yml` exists + runs on push to main + PR | workflow presence | `test -f .github/workflows/full-test-matrix.yml && yq '.on' .github/workflows/full-test-matrix.yml` | ❌ Wave 2 — NEW file |
| TEST-04 | Matrix covers `[macos-13, macos-14, windows-latest] × [default + 7 opt-in markers]` minus impossible exclusions | workflow shape | `yq '.jobs.test.strategy.matrix' .github/workflows/full-test-matrix.yml` | ❌ Wave 2 |
| TEST-04 | README badge exists + URL returns 200 | repo-presence | `grep 'full-test-matrix.yml' README.md` | ❌ Wave 2 |

### Sampling Rate
- **Per task commit:** `uv run pytest -q --tb=short` (quick; runs the default suite ~3.5 min)
- **Per wave merge:** `uv run pytest -q && uv run pytest -q -m macos_audio && uv run pytest -q -m integration` (covers the markers Kaan's Mac can actually run)
- **Phase gate:** Full marker grid (`uv run pytest -q` + each of 7 markers individually) on Kaan's Mac + Windows 11 VM; plus the CI matrix workflow green on `main` for at least one push.

### Wave 0 Gaps

- [ ] **Fix `tests/coach/test_main_anti_slop_wiring.py::test_wire13_anti_slop_disabled_path_passes_none_kwargs`** — kwarg drift, code-only fix.
- [ ] **Fix `tests/repo/test_cut_release_invokes_bravoh_server.py::test_tag_regex_unchanged_in_this_plan`** — regex pin needs update or sentinel relaxation.
- [ ] **Fix `tests/repo/test_gate_42_hybrid_in_force.py::test_state_md_phase_16_line_is_annotated_retired`** — STATE.md drift; v7.0 rewrote the file.
- [ ] **Fix `tests/repo/test_readme_feature_matrix_sync.py::test_readme_feature_matrix_in_sync`** — README matrix lags milestone progress.
- [ ] **Fix `tests/repo/test_readme_feature_matrix_sync.py::test_feature_matrix_includes_all_completed_phases`** — add phases 67-70 to feature matrix or extend sentinel.
- [ ] **Fix `tests/scripts/test_cut_release_preflight.py::test_cut_release_accepts_valid_rc_tag_shape`** — likely sibling of the regex drift.
- [ ] **Fix `tests/scripts/test_cut_release_preflight.py::test_cut_release_blocks_on_missing_milestone_audit`** — v6.0/v7.0 milestone audit path drift.
- [ ] **Fix `tests/test_main_smoke.py::test_smoke_08_main_source_wires_cache_create_with_graceful_degradation`** — smoke test refactor drift.
- [ ] **Add `"flaky: …"` line to `pyproject.toml [tool.pytest.ini_options].markers`** — Wave 0 must land before any test uses the marker.

### Wave 1 Gaps
- [ ] `tests/repo/test_no_silent_skips.py` — NEW static gate for skip/xfail reason tagging.
- [ ] `tests/repo/test_no_silent_flakes.py` — NEW static gate for flaky issue-link enforcement.
- [ ] `KAAN-ACTION-LEGAL.md` § V7-LIVE — NEW section with one entry per Tier-B failure mode.
- [ ] Triage spike: run each opt-in marker on Kaan's Mac, classify each test result as Tier A/B/C.

### Wave 2 Gaps
- [ ] `.github/workflows/full-test-matrix.yml` — NEW workflow per the Pattern 2 template.
- [ ] README badges row — NEW line per the Pattern 3 template.

### Wave 3 Gaps
- [ ] 10× consecutive `pytest -q` local loop on Kaan's Mac.
- [ ] If any flakes surface: quarantine each with `@pytest.mark.flaky` + GH issue + `# issue:` comment.

## Security Domain

Phase 67 is **test infrastructure only**. No new user-facing surface, no auth/session/access-control changes, no new external API consumers, no secrets handled beyond the existing `GEMINI_API_KEY` GitHub Secret (used by `eval.yml` today).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | n/a — phase touches no auth surface |
| V3 Session Management | no | n/a |
| V4 Access Control | no | n/a |
| V5 Input Validation | no | n/a — no new inputs |
| V6 Cryptography | no | n/a |
| V14 Configuration | yes | Workflow YAML pinned to action SHAs (project pattern, enforced by `dep-audit.yml` pinact-audit job) |

### Known Threat Patterns for CI/CD

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unpinned action versions (supply-chain hijack) | Tampering | SHA-pin every `uses:` line — existing project pattern (verified in `eval.yml`, `release.yml`, `dep-audit.yml`); enforced by `pinact-audit` job |
| Secret leakage in CI logs | Information Disclosure | Use `env:` from `secrets.*` (never echo); GitHub Actions auto-masks declared secrets |
| Apple/SignPath POST/PUT from CI (Pitfall P46) | Elevation of Privilege | Existing repo-wide grep audit in `verify-signed.yml`; the new workflow MUST NOT introduce any such calls — easy since it only runs `pytest` |
| GH Actions cache poisoning | Tampering | Cache only build artifacts, never the test outputs themselves; recommend NOT caching the .venv (uv resolves from lockfile fast) |
| `pull_request_target` privilege escalation | Elevation of Privilege | Use `pull_request` trigger (not `pull_request_target`) — secrets unavailable for fork PRs, which is the right posture for `GEMINI_API_KEY` |

**Recommendation:** Use `on: pull_request` (not `pull_request_target`). For fork PRs the `GEMINI_API_KEY` secret will be unavailable — tests that hard-require it must skip-with-reason (the `eval.yml` cassette pattern is the precedent).

## Sources

### Primary (HIGH confidence)
- **Live repo state verified 2026-05-23** — `pytest --collect-only -q` (4186 collected, 65 deselected) · `pytest -q` (8 failed/4152 passed/26 skipped) · grep counts of markers + skipif + xfail + flaky.
- **`/Users/ozai/projects/dj-set-ai/pyproject.toml`** — marker declarations, dev deps, `--strict-markers`, Python pin `>=3.12,<3.13`.
- **`/Users/ozai/projects/dj-set-ai/tests/repo/test_repo_scrub.py`** — static-gate prior art.
- **`/Users/ozai/projects/dj-set-ai/.github/workflows/eval.yml`** — uv + setup-python + matrix workflow shape prior art.
- **`/Users/ozai/projects/dj-set-ai/.github/workflows/release.yml:247-310`** — `[macos-13, macos-14]` matrix prior art.
- **`/Users/ozai/projects/dj-set-ai/.github/workflows/dep-audit.yml:49-51`** — concurrency-group prior art.
- **`/Users/ozai/projects/dj-set-ai/KAAN-ACTION-LEGAL.md`** — §SHIP-V4 / §POST-RC-CLEANUP / etc section structure to mirror for §V7-LIVE.
- **`/Users/ozai/projects/dj-set-ai/README.md:40-43`** — existing badges row pattern.
- **`/Users/ozai/projects/dj-set-ai/.planning/REQUIREMENTS.md`** — TEST-01..04 verbatim.
- **`/Users/ozai/projects/dj-set-ai/.planning/phases/67-all-tests-pass/67-CONTEXT.md`** — locked decisions.

### Secondary (MEDIUM confidence)
- [actions/runner-images#11746 — macOS image BlackHole reboot requirement](https://github.com/actions/runner-images/issues/11746) — confirms the BlackHole-can't-run-in-CI claim.
- [pytest-dev/pytest-rerunfailures README](https://github.com/pytest-dev/pytest-rerunfailures) — auto-retry behavior we're explicitly avoiding.
- [pytest-dev/pytest-repeat README](https://github.com/pytest-dev/pytest-repeat) — `--count=N` for stress-testing a single test (alternative to shell loop).
- [pytest flaky-tests explanation page](https://docs.pytest.org/en/stable/explanation/flaky.html) — official guidance on flake detection.
- [oneuptime.com Matrix Include/Exclude guide](https://oneuptime.com/blog/post/2025-12-20-github-actions-matrix-include-exclude/view) — exclude syntax reference.
- [github community discussion #26253](https://github.com/orgs/community/discussions/26253) — exclude-vs-include patterns.

### Tertiary (LOW confidence)
- Brave/exa not configured in `.planning/config.json` (`brave_search: false`, `exa_search: false`, `firecrawl: false`); standard WebSearch used as fallback. None of the search results inform load-bearing claims — they only corroborate confirmed-via-repo findings.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every tool already in the repo; zero net-new deps proposed.
- Architecture: HIGH — every pattern has an exact existing-repo template (test_repo_scrub.py, eval.yml, release.yml, dep-audit.yml).
- Pitfalls: HIGH — BlackHole reboot + windows-latest Server SKU + strict-markers gotcha + concurrency-group collision are all verified.
- Current state: HIGH — live pytest run captured the 8 reds + skip/xfail/flaky counts.
- Triage of 65 opt-in tests: MEDIUM — exact Tier A/B/C distribution requires per-marker test runs during plan execution; current numbers are estimates.

**Research date:** 2026-05-23
**Valid until:** 2026-06-23 (30 days — GitHub Actions and pytest are slow-moving; the live repo state is the load-bearing input and won't drift without commits)

## RESEARCH COMPLETE
