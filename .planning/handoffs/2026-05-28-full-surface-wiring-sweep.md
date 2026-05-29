# Handoff: Full Surface Wiring Sweep

**Date:** 2026-05-28  
**Status:** complete for the requested non-GSD, non-beginner scope  
**Scope:** live app wiring across session, Viber/Vibe Engine, parsing, research,
settings, Debrief, pill, mascot, recordings, IPC contracts, and Claude mockup
transfer rules.

## Explicit exclusions

- GSD was not run.
- The Learn beginner path was not run or audited.
- Avoid these suites unless the user explicitly asks for beginner-path work:
  `tests/learn/test_ws_beginner_path.py`,
  `tests/learn/test_lesson_flow_contract.py`,
  `tauri/ui/tests/learn/test_beginner_path_contract.spec.ts`, and
  `tauri/ui/tests/learn/browser-python-beginner-path.pw.ts`.

## Final state

The app has a live wiring spine from Python runtime -> Rust commands/events ->
TypeScript renderers for the non-beginner surfaces. The important cross-surface
contracts are now explicit and covered:

- Viber stop reasons propagate as first-class UI state.
- Settings IPC/schema fields round-trip with parity checks.
- Research parsing fails closed for empty pages and non-finite scores.
- ANLZ structure anchors are materialized into cached cue data.
- Pill hover/expand state is unified under a production `data-open` contract.
- Mockup transfer is pinned by stable `data-wire`, IPC, command, and event
  contracts before Claude/HTML mockups are moved into production.

## Surface map

| Surface | State | Notes |
|---|---|---|
| Live session | Wired | Session mode, reactions, recordings state, settings echoes, tray quit, and mood changes are covered by runtime/static anchors. |
| Settings | Wired | `lens`, `learn.headphone_device_index`, and `session.mode` are in schema/codegen parity. Persona, mode, genre, skill, and lens controls expose `data-wire` anchors. |
| Vibe Engine / Viber | Wired | Clarification and tool-starvation stop reasons flow from Python to Rust/UI. Library chat can render clarification artifacts instead of flattening them into generic errors. |
| Research | Hardened | `fetch_url` only reads URLs issued by `web_search` in the same run; empty fetched pages return an error; non-finite Tavily scores normalize to `0.0`. |
| Parsing / library engines | Wired | Rekordbox cache schema is v3. ANLZ cues now enter `TrackEntry.cues` with `source="anlz"` and confidence, then survive excerpt and section building. DJ cues still take precedence. |
| Debrief | Wired | Existing latest-session fallback and deep-link path remain part of the wiring sweep. |
| Pill | Wired and redesigned | Production pill keeps the 280x44 native collapsed contract, clamps expanded height, and uses `data-open` to make hover peek and expand read as one continuous glass body. |
| Mascot | Wired | Mock-transfer contract includes mascot shell/state/status anchors and settings-driven surfaces. |
| Recordings | Wired | Browser/list/delete/usage and latest-session Debrief fallback remain in the covered surface set. |
| Mock transfer | Wired | `tauri/ui/src/mock-transfer/contract.ts` and `tauri/ui/tests/mock-transfer-contract.spec.ts` pin live anchors, runtime-created anchors, IPC producers, Rust commands, and Tauri events. |

## Durable contracts

1. **Stop reasons**
   - `clarification_needed` and `tool_starvation` are meaningful outcomes, not
     generic failures.
   - UI should preserve their artifacts and copy.

2. **Settings parity**
   - Keep Python dataclasses, JSON schema, generated TypeScript, validator, Rust
     config commands, and session bridge in sync.
   - Current top-level IPC count is 78.
   - Validate with `uv run python scripts/check_ipc_schema.py`.

3. **Research grounding**
   - `fetch_url` must not fetch arbitrary URLs. It may read only URLs issued by
     `web_search` in the same run.
   - Empty page text is an error, not a successful blank source.
   - Non-finite search scores degrade to `0.0`.

4. **Library cue provenance**
   - `CuePoint` carries `source` and `confidence`.
   - Cache schema v3 preserves cue provenance.
   - DJ cues win over ANLZ; ANLZ wins over auto fallback when no DJ cues exist.

5. **Pill geometry**
   - Native collapsed height remains 44.
   - Native width remains owned by `pill_window.rs`.
   - Renderer height requests are finite and clamped.
   - `data-open=true` means visual body open for either hover peek or event
     expand.

6. **Mockup transfer**
   - Do not move dynamic Claude mock HTML into production unless every
     interactive or runtime-created element maps to a `data-wire` in
     `tauri/ui/src/mock-transfer/contract.ts`.
   - Contract tests must include static anchors, runtime anchors, IPC/event
     producers, and Tauri command names.

## Primary files

- `AGENTS.md`
- `scripts/check_ipc_schema.py`
- `src/vibemix/library/rekordbox.py`
- `src/vibemix/library/ingest.py`
- `src/vibemix/library/excerpt.py`
- `src/vibemix/library/section_builder.py`
- `src/vibemix/library/web_research.py`
- `tauri/ui/src/mock-transfer/contract.ts`
- `tauri/ui/tests/mock-transfer-contract.spec.ts`
- `tauri/ui/pill.html`
- `tauri/ui/src/pill/index.ts`
- `tauri/ui/src/pill/pill.css`
- `tauri/ui/src/pill/next-suggestion.ts`
- `tauri/ui/src/pill/waveform.ts`
- `tests/library/test_ingest.py`
- `tests/library/test_excerpt.py`

## Verification run

- `npm --prefix tauri/ui test -- src/pill/index.test.ts src/pill/next-suggestion.test.ts src/pill/waveform.test.ts`
  - 79 passed.
- `npm --prefix tauri/ui test -- tests/mock-transfer-contract.spec.ts`
  - 18 passed.
- `uv run python scripts/check_ipc_schema.py`
  - 78 dataclasses validate against schema.
  - 78 oneOf entries match 78 wrapper dataclasses.
  - Settings field/payload parity passed.
- `npm --prefix tauri/ui run build`
  - TypeScript and Vite production build passed.
- `git diff --check -- tauri/ui/pill.html tauri/ui/src/pill/index.ts tauri/ui/src/pill/index.test.ts tauri/ui/src/pill/pill.css tauri/ui/src/mock-transfer/contract.ts tauri/ui/tests/mock-transfer-contract.spec.ts`
  - Clean.
- `uv run pytest -q tests/library/test_anlz_ingest.py tests/library/test_excerpt.py tests/library/test_ingest.py tests/library/test_next_suggestion.py tests/intel/test_transition_scorer.py`
  - 94 passed.
- `uv run pytest -q tests/runtime/test_suggestion.py tests/library/test_toolset.py tests/library/test_setprep_tools.py`
  - 85 passed.
- `uv run ruff check src/vibemix/library/rekordbox.py src/vibemix/library/excerpt.py src/vibemix/library/section_builder.py src/vibemix/library/ingest.py tests/library/test_ingest.py tests/library/test_excerpt.py`
  - Passed.

## Residual risks

- A browser screenshot pass was not run for the final pill visual slice; build
  and component/contract tests passed.
- The full Rust suite was not rerun in the final pill slice.
- Learn beginner and GSD remain intentionally outside this handoff.
- The repository had many pre-existing modified/untracked files during the
  sweep. Do not assume every dirty file belongs to this pass.
- Broader live cohost use of `intel/` claim validation remains a future product
  integration surface.

## Next safe continuation

Start with the contracts, not the mock visuals:

1. Run `npm --prefix tauri/ui test -- tests/mock-transfer-contract.spec.ts`.
2. If importing a Claude mockup, add or confirm `data-wire` anchors first.
3. Preserve pill native geometry and `data-open`.
4. Run pill tests, mock-transfer tests, IPC schema check, and UI build.
5. Keep GSD and beginner-path suites out of the run unless explicitly requested.
