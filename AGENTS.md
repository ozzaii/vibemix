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
- `uv run python -m vibemix library gig-check <path>` / `library export-guard
  <usb> --rig <id>`: the read-only preflight verdict CLIs (2026-06-12 wedge;
  public noun is "Gig Check", never "Library Doctor"). Contracts + commit list:
  `.planning/handoffs/2026-06-12-HANDOFF-GIG-CHECK-EXPORT-GUARD.md`.

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
Product naming is load-bearing: **Viber is the library/set-prep agent/operator**;
**Sven is the live co-host voice**. Do not describe Viber as the co-host, and do
not describe live speech as Gemini/cloud TTS; the product voice source is local MOSS.

## Supercharge Tooling (shared by Claude Code + Codex)

Three project skills live in `.claude/skills/`. Codex does not auto-load Claude
skills, so use their bundled scripts and checklists directly:

- **drive-vibemix** — prove a runtime change works LIVE; green tests do not (the
  frozen sidecar + Tauri runtime hide real failures). Launch current source with
  `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix`, attach a ws client to
  `127.0.0.1:8765` (client only — Invariant #4), drive a control or fire a reaction,
  then read `~/Library/Application Support/world.bravoh.vibemix/vibemix/logs/ui.log`
  and the session `events.jsonl`. Brain-mute signature = `citation_count:0` + empty
  `transcript_delta` (cause: missing `GEMINI_API_KEY`, not a bug). Helper:
  `.claude/skills/drive-vibemix/scripts/ws_probe.py`.
- **ipc-wiring-checker** — before and after any `messages.schema.json` or handler
  edit, run `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`;
  it flags one-ended (dead) IPC types and stale `codegen:ipc`, exiting nonzero on a
  dead type.
- **vibemix-grounding-review** — before shipping any change to what the co-host SAYS
  (`state/coach.py`, `agent/dj_cohost.py`, `prompts/*`, `state/event_detector.py`),
  walk `.claude/skills/vibemix-grounding-review/references/invariant-checks.md`.

Shared MCP servers in Codex `~/.codex/config.toml` `[mcp_servers.*]`: `vibemix_library`
(existing) and `agentmemory` (persistent cross-session memory; LLM compression is off
by default — do NOT set `AGENTMEMORY_ALLOW_AGENT_SDK`, it recurses inside agents). LSP
(pyright + rust-analyzer + ts-language-server) gives both agents compiler-grade nav.

## Full-Surface Wiring Sweep Notes

When continuing the May 2026 full-app wiring sweep, keep the user's boundary:
do not run GSD or the Learn beginner path unless explicitly asked. Avoid the
beginner-path suites such as `tests/learn/test_ws_beginner_path.py`,
`tests/learn/test_lesson_flow_contract.py`,
`tauri/ui/tests/learn/test_beginner_path_contract.spec.ts`, and
`tauri/ui/tests/learn/browser-python-beginner-path.pw.ts`.

The durable handoff for the completed non-GSD, non-beginner sweep is
`.planning/handoffs/2026-05-28-full-surface-wiring-sweep.md`. Read it before
moving Claude/mock HTML into production or changing Viber, settings, research,
ANLZ parsing, pill, or mock-transfer contracts.

Mockup transfer is pinned through `tauri/ui/src/mock-transfer/contract.ts` and
`tauri/ui/tests/mock-transfer-contract.spec.ts`. Any production `data-wire`
anchor, static or runtime-created, must be contracted there before visual work
from `mocks/iterations/` is moved into the live app. Keep Tauri IPC/event
channels and Rust commands listed in the contract too, including session tray
quit/mood events.

For Viber/library work, preserve the grounded tool spine: `fetch_url` may only
read URLs issued by `web_search` in the same run, empty fetched pages return an
error, and non-finite search scores degrade to `0.0`. Viber clarification and
tool-starvation stop reasons must propagate from Python through Rust commands
and the library UI, including chat artifacts.

For settings/session IPC, maintain parity across
`src/vibemix/ui_bus/messages.py`, `tauri/ui/src/ipc/messages.schema.json`,
generated TS/validator files, `src/vibemix/runtime/session_loop.py`, and
`tauri/ui/src/session/ws-bridge.ts`. The current top-level IPC count is 72
(`SessionSetMode` and `WizardSetSkill` included); validate with
`uv run python scripts/check_ipc_schema.py`.

Useful non-GSD, non-beginner verification from the sweep:

- `npm --prefix tauri/ui test -- tests/mock-transfer-contract.spec.ts`
- `npm --prefix tauri/ui test -- tests/session/quit-guard.spec.ts tests/session/tray-mood.spec.ts tests/session/router-teardown.spec.ts`
- `npm --prefix tauri/ui run build`
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml`
- `uv run pytest -q tests/library tests/intel tests/ipc tests/ui_bus tests/prompts/test_filter.py tests/prompts/test_negative_dict.py tests/state/test_refresh.py`

## Commit & Pull Request Guidelines

Git history uses scoped Conventional Commit-style messages such as
`feat(library-ui): ...`, `fix(rebuild): ...`, and `docs(v8.2): ...`. Every commit must
be DCO signed with `git commit -s`. PRs should explain the change, link issues, list
local checks, and include screenshots or recordings for UI-visible changes.

## Security & Configuration Tips

Do not commit secrets, private keys, sensitive recordings, or local `.env` files. Use
`proxy/.env.example` and `docs/byo-key.md` for configuration guidance. Report security
issues via `SECURITY.md`.
