# Testing Patterns

**Analysis Date:** 2026-06-08

Two test suites, both authoritative gates:
- **Python** — pytest over `tests/` (824 `*.py` test files). The authoritative dev workflow per `CONTRIBUTING.md`.
- **Frontend** — vitest over `tauri/ui/src/**` + `tauri/ui/tests/**` (168 `*.test.ts`/`*.spec.ts` files; ~886 cases). Run after ANY `tauri/ui/` change.

A large class of tests are **invariant gates** (repo-scrub, model-literal, grounding-failure, no-silent-skips) — static or behavioral assertions that lock a project rule so a future commit can't silently break it. Treat them as the contract, not as coverage filler.

## Test Framework

**Python runner:**
- pytest `>=8.0` + `pytest-mock>=3.15.1` (the `mocker` fixture). Config block: `[tool.pytest.ini_options]` in `pyproject.toml`.
- `testpaths = ["tests"]`, `addopts = "-ra --strict-markers -m 'not network'"`. `--strict-markers` means an unregistered marker is a hard error; `network` tests are excluded by default.
- VCR.py (`vcrpy>=8.0`) + `pytest-recording>=0.13` cache Gemini API calls so PR CI runs at $0 (cassettes under `tests/eval/cassettes/`).

**Frontend runner:**
- vitest `^4.1`, jsdom `^29` for DOM specs, ajv for IPC validation, `@playwright/test` for the separate e2e lane.
- Config: `tauri/ui/vitest.config.ts` uses the vitest-4 `test.projects` idiom — a `node` project and a `jsdom` project. The `jsdom` project's `include` is the explicit `DOM_GLOBS` list; the `node` project includes everything and EXCLUDES `DOM_GLOBS`, so each file runs exactly once in the right environment. `tests/visual/*.spec.ts` are Playwright scaffolds and are excluded from vitest.

**Run commands:**
```bash
# Python (authoritative dev loop)
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q
uv run pytest -q                                  # equivalent, no activation

# Frontend (authoritative gate after any tauri/ui/ change)
cd tauri/ui && npm run build && npm test           # build = tsc --noEmit && vite build; test = vitest run
npm run codegen:ipc                                # REQUIRED after editing src/ipc/messages.schema.json
```

## Opt-In Markers

Default `pytest` run excludes `network` and skips every opt-in marker. The registered set (`[tool.pytest.ini_options]` markers, `--strict-markers`):

| Marker | Meaning | Run with |
|--------|---------|----------|
| `macos_audio` | Requires BlackHole 2ch present (CoreAudio smoke) | `pytest -m macos_audio` |
| `windows_only` | `sys.platform == 'win32'` — Windows-port live tests | `pytest -m windows_only` |
| `integration` | End-to-end: spins up real WS servers/clients | `pytest -m integration` |
| `slow` | 60-min soak test | `pytest -m slow` |
| `parity` | Mac/Win bit-identity gate for the library backend | `pytest -m parity` |
| `cli` | Subprocess CLI integration tests | `pytest -m cli` |
| `e2e` | End-to-end debrief lifecycle | `pytest -m e2e` |
| `network` | Live-network smoke (e.g. GitHub org poller) — excluded by default | `pytest -m network` |
| `real_model_status` | Bypass patched model-status fixtures, exercise local asset validation directly | `pytest -m real_model_status` |
| `flaky` | Quarantined non-deterministic test; MUST carry a `# issue: https://…` link (gate-enforced) | n/a |

Adding a new marker requires registering it in `pyproject.toml` or `--strict-markers` fails the run.

## Test File Organization

**Python — separate `tests/` tree mirroring `src/vibemix/` subpackages:**
```
tests/
├── conftest.py              # shared fixtures (currently minimal)
├── test_*.py                # platform/main smoke (audio/midi/screen/track × macos/windows)
├── repo/                    # invariant & hygiene gates (scrub, model-literal, no-silent-skips/flakes)
├── agent/                   # co-host session, TTS chain, citation emit
├── state/                   # MusicState, event detector, deck, harmonics, detectors/
├── library/                 # CLAP embed, rekordbox, codex curate, vibe search
├── intel/ llm/ learn/ coach/ prompts/ profile/ memory/ debrief/ midi/ runtime/
├── eval/                    # Gemini judge cross-checks (VCR cassettes)
├── bench/ sim/ e2e/ integration/ launch/ release/ dist/ security/ sidecar/ ...
└── fixtures/                # shared test data
```
- Per-area `conftest.py` files (15 of them: `tests/eval/`, `tests/agent/`, `tests/state/`, `tests/learn/`, `tests/runtime/`, `tests/wizard/`, …) hold area-scoped fixtures.
- Live/hardware variants are suffixed `*_live.py` and marker-gated (`test_audio_macos_live.py`, `test_midi_macos_live.py`).

**Frontend — co-located + a parallel `tests/` tree:**
- `*.test.ts` co-located with source (`src/session/state.test.ts` style) for unit logic.
- `*.spec.ts` under `tauri/ui/tests/<area>/` for DOM/integration (`tests/session/grounding-failure.spec.ts`, `tests/learn/test_ws_client_tauri_bridge.spec.ts`).
- `*.dom.spec.ts` forces the jsdom project explicitly.
- Playwright e2e configs live per-surface (`tests/learn/playwright.config.ts`, `tests/pill/`, `tests/mascot/`) and run via dedicated `test:e2e:*` scripts, NOT vitest.

## Test Structure

**Python — module constants at top, `_`-prefixed helpers, one assertion-rich `def test_*`:**
```python
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
REPO_ROOT = Path(__file__).resolve().parents[2]

def _python_gate_check(repo_root: Path) -> list[tuple[Path, int, str]]:
    ...                                  # private helper does the work

def test_gate_passes_clean_tree() -> None:
    assert _python_gate_check(REPO_ROOT) == []   # offender-list assertion
```
The static-gate idiom (`tests/repo/test_repo_scrub.py`, `test_no_silent_skips.py`) is the house template: collect offenders into a list, assert it's empty, and put the actionable fix in the assertion message.

**Frontend — vitest BDD `describe`/`it` with jsdom hosts and fake timers:**
```typescript
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

function host(): HTMLElement {
  const div = document.createElement("div");
  document.body.append(div);
  return div;
}
beforeEach(() => { vi.useRealTimers(); });
afterEach(() => { document.body.replaceChildren(); vi.useRealTimers(); });

describe("SessionLayout grounding-failure → fault state (H9)", () => {
  it("after >= 5s of grounded=false on an ACTIVE co-host the deck flips to fault", () => {
    vi.useFakeTimers(); vi.setSystemTime(t0);
    ...
  });
});
```
Time-dependent specs use `vi.useFakeTimers()` + `vi.setSystemTime()`; cleanup resets timers and clears `document.body` in `afterEach`.

## Mocking

**Python — `pytest-mock` `mocker` (65 files) + `monkeypatch` (202 files):**
- Dependency injection beats patching: `codex_curate` accepts an injected `_runner` so `tests/library/test_codex_curate.py` exercises spawn→timeout→parse→degrade without the `codex` binary. Prefer a seam over a deep patch.
- **CACHE_PATH monkeypatch gotcha (mandatory for library/rekordbox tests):** any test touching `RekordboxLibrary` MUST repoint its cache or it overwrites the real `~/.cache/vibemix/library.pkl`:
  ```python
  monkeypatch.setattr(RekordboxLibrary, "CACHE_PATH", tmp_path / "library.pkl", raising=False)
  ```
  Applied across `tests/library/test_ingest.py`, `test_folder_ingest.py`, `test_stats_cli.py`, `test_rekordbox.py`, `test_genre_prototypes.py`, `test_staleness.py`, and ~10 more. When the CLI re-imports the class, patch it on the CLI module too (`main_mod.RekordboxLibrary` in `test_live_context_cli.py`).
- Subprocess-dormancy idiom: spawn a fresh interpreter with `subprocess.run([sys.executable, "-c", script], env={..., "PYTHONPATH": .../src})` and assert no forbidden module landed in `sys.modules` (SQLCipher dormancy in `test_repo_scrub.py::test_deck_path_sqlcipher_dormant`).

**Frontend — vitest `vi.fn`/`vi.mock`/`vi.spyOn` (69 files):**
- State singletons reset between cases via the module's own `_resetSessionStateForTests()` (`tauri/ui/src/session/state.ts`).
- DOM is built fresh per test via a `host()` factory; no shared mount.

**What to mock:** the `codex` binary, the Gemini network call (VCR cassettes), the OS audio/MIDI/screen backends, the filesystem cache path.
**What NOT to mock:** the pure intel/scoring primitives (`intel/` is dependency-free by design — test it directly), the grounding/citation logic, the ring-cap/diff math.

## Fixtures and Factories

- Python: small inline factory helpers (`_track(tid) -> TrackEntry` in `test_codex_curate.py`) build domain objects; shared data under `tests/fixtures/`. `tmp_path` is the standard scratch dir.
- Frontend: `defaultState()` / `makeDefault()` produce a fully-populated `SessionState` (every field present so the renderer never reads `undefined`); specs clone-and-override (`{ ...active.cohost, status: "LISTENING", grounded: false }`).

## Invariant-Enforcing Tests (the gates that matter)

| Gate | File / Workflow | Locks |
|------|-----------------|-------|
| Retired POC scrub | `tests/repo/test_repo_scrub.py::test_retired_poc_files_stay_gone` | `cohost*.py`/`run_*.sh`/`test_voice.py` stay deleted; `mascot.html` + `mocks/` survive |
| Model-literal grep | `tests/repo/test_model_literal_gate.py` + `.github/workflows/model-literal-check.yml` + `scripts/release/check_no_hardcoded_model.sh` | No `gemini-*` literal in `src/vibemix/` outside `_router_config.py` |
| Grounding-failure / idle-not-fault (Invariant #5) | `tauri/ui/tests/session/grounding-failure.spec.ts` | Grounding-failure timer runs only while co-host ACTIVE; idle `grounded=false` never faults the deck (empty-screen regression) |
| Single-socket (Invariant #4) | live/readiness tests reference `127.0.0.1:8765` (mascot/wizard) / `8766` (debrief) | Never two listeners on the bus |
| No silent skips | `tests/repo/test_no_silent_skips.py` | Every `@pytest.mark.skip/skipif/xfail` carries `reason=` or a `# reason:` comment (AST-walked) |
| No silent flakes | `tests/repo/test_no_silent_flakes.py` | Every `@pytest.mark.flaky` carries a `# issue: https://github.com/.../issues/N` link |
| Deck read-only (DECK-05) | `tests/repo/test_repo_scrub.py::test_deck_readonly` | No write-mode / SQLCipher DJ-DB path in the deck source (master.db landmine) |
| Repo hygiene | `tests/repo/test_repo_scrub.py` | No tracked `.env`/`.bak`, >1 MB files, scratch files at root |
| Mascot audit | `.github/workflows/mascot-audit.yml` | Bundle size bands, manifest completeness, anti-slop grep, `mascot.html` absent from test surfaces, 4-layer × 15-event coverage matrix |

## CI Gates

- **Full Test Matrix** (`.github/workflows/full-test-matrix.yml`): every push to `main` + every PR. `uv sync --frozen --group dev`, then the default suite plus each opt-in marker as an isolated job across `[macos-13, macos-14, windows-latest]` (OS-incompatible combos excluded — Windows skips `macos_audio`, Mac skips `windows_only`). One job per marker so a failure is attributable. `on: pull_request` (NOT `pull_request_target`) — no secret exposure to fork PRs; all `uses:` SHA-pinned; `permissions.contents: read`.
- **Model Literal Check** — the grep gate above, path-filtered to `src/vibemix/**` + the gate scripts.
- **Mascot audit** — the multi-job aggregate above (bundle gate is `continue-on-error` until VIS-04 discharge).
- Plus per-domain security/packaging workflows: `secret-scan.yml`, `dep-audit.yml`, `python-cve.yml`, `rust-cve.yml`, `sbom.yml`, `verify-signed.yml`, `no-api-key-surface.yml`, `capabilities-lint.yml`, `install-rehearsal.yml`, `eval.yml`.

## Common Patterns

**Subprocess gate (cross-platform parity):**
```python
proc = subprocess.run([str(GATE_SCRIPT)], cwd=str(REPO_ROOT), capture_output=True, text=True)
assert proc.returncode == 0, f"...\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
```
Bash gates are mirrored by a pure-Python `_python_gate_check()` so Windows runners (no guaranteed bash) still enforce the rule; the bash subprocess assertions `@pytest.mark.skipif(_BASH is None, ...)` on hosts without bash.

**Synthetic-violation positive control:** gates write a canary file under `src/vibemix/`, assert the gate trips, and clean up in `finally` (`test_model_literal_gate.py::test_gate_fails_on_synthetic_violation_in_src`) — proves the gate isn't vacuously green.

## Coverage Gaps

- No coverage threshold is enforced (no `--cov-fail-under`); coverage is breadth-of-gates, not a percentage.
- Hardware-dependent paths (`macos_audio`, `windows_only`, live capture) are opt-in and amber on hosted CI (BlackHole can't load on GitHub macOS runners — Tier-B `§V7-LIVE` xfails keep `macos_audio` amber not red). Real-device behavior is validated by-ear/by-eye, not in CI.
- No mypy/pyright gate — type hints are unchecked documentation.
- Frozen-bundle drift: the PyInstaller sidecar bundled in `cargo tauri dev` lags edited `src/` and produces false negatives; verify backend wiring by running `main()` on current source, not the bundled binary.
- The single in-flight Gemini gate (`in_flight` flag) and the audio-thread → asyncio handoff are concurrency-sensitive and only partially exercisable in unit tests.

---

*Testing analysis: 2026-06-08*
