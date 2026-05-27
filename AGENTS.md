# Repository Guidelines

## Project Structure & Module Organization

`src/vibemix/` contains the Python app package: live audio/state, co-host
agent code, library/CLAP search, local Codex Viber tooling, prompts, runtime
services, and platform backends. Package data lives beside code, such as
`src/vibemix/state/genre/profiles/`. `tests/` mirrors these areas. `tauri/ui/`
is the Vite/TypeScript webview; `tauri/src-tauri/` is the Rust desktop shell and
sidecar bridge. Supporting material lives in
`docs/`, `assets/`, `eval/`, `installer/`, `packaging/`, `mocks/`, and `scripts/`.

## Build, Test, and Development Commands

- `uv sync --group dev --extra ai-local`: install Python 3.12 dev dependencies
  plus local CLAP/CUE runtime dependencies.
- `uv run pytest -q`: run the default Python test suite from `tests/`.
- `uv run ruff check src tests` and `uv run ruff format src tests`: lint and format Python.
- `npm --prefix tauri/ui test`: run Vitest UI tests.
- `npm --prefix tauri/ui run build`: type-check and build the webview.
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml`: validate Rust changes.
- `uv run python -m vibemix`: run the local co-host session loop.

## Coding Style & Naming Conventions

Python targets 3.12 and uses Ruff lint/format from `pyproject.toml`: 100-character
lines, double quotes, import sorting, pyupgrade, and bugbear.
Use `snake_case` for modules, functions, variables, and tests; `PascalCase` for
classes; `UPPER_SNAKE_CASE` for constants. TypeScript follows
`tauri/ui/src/` patterns. Format Rust with `cargo fmt`. Avoid new Python, npm,
or Cargo dependencies unless discussed.

## Testing Guidelines

Place Python tests under `tests/<area>/test_*.py`. Prefer deterministic unit tests.
Reserve declared pytest markers for hardware, live audio, network, slow, CLI, and
end-to-end coverage. Docs-only changes generally do not need tests.

## Architecture & Agent-Specific Notes

Keep `vibemix.__main__:main()` as the orchestration entry point. Preserve invariants:
only state refresh writes `MusicState`; AI reactions must resolve through
`EvidenceRegistry`; live audio is authoritative; the main UI socket is
`127.0.0.1:8765` and debrief uses `8766`. Do not hardcode model names; resolve through
`vibemix.llm.model_router` or the existing library agent backend seams. For broad
agent work, read `CLAUDE.md` and the active `.planning/research/` sweep notes first.

## Commit & Pull Request Guidelines

Git history uses scoped Conventional Commit-style messages such as
`feat(library-ui): ...`, `fix(rebuild): ...`, and `docs(v8.2): ...`. Every commit must
be DCO signed with `git commit -s`. PRs should explain the change, link issues, list
local checks, and include screenshots or recordings for UI-visible changes.

## Security & Configuration Tips

Do not commit secrets, private keys, sensitive recordings, or local `.env` files. Use
`proxy/.env.example` and `docs/byo-key.md` for configuration guidance. Report security
issues via `SECURITY.md`.
