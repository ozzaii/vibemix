# CODEX_READY: IPC Contract Cleanup

Date: 2026-06-01
Author: Codex
Status: LAND packet, IPC contract cleanup slice
Package: Package 3 - IPC Contract Cleanup

## Decision

LAND this slice as `fix(ipc): prune stale bus contracts`.

The top-level IPC schema is intentionally at 72 message types. The package
removes stale schema-only or wrong-transport contracts instead of preserving
dead promises: five library search/similar/confidence bus wrappers and two
debrief placeholder wrappers are gone. Real behavior remains available through
the correct transports: library search/similar use Tauri commands, import and
staleness stay on `ipc.library.*`, and debrief keeps only wrappers with a real
producer/consumer path.

## Files

- `AGENTS.md`
- `scripts/check_ipc_schema.py`
- `.claude/skills/ipc-wiring-checker/SKILL.md`
- `.claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`
- `src/vibemix/ui_bus/messages.py`
- `src/vibemix/ui_bus/__init__.py`
- `src/vibemix/ui_bus/schemas/debrief.py`
- `src/vibemix/ui_bus/schemas/library.py`
- `src/vibemix/library/search.py`
- `src/vibemix/library/similar.py`
- `tauri/src-tauri/src/library_cmds.rs`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tests/ipc/test_library_schemas.py`
- `tests/ipc/test_learn_envelope_parity.py`
- `tests/ui_bus/test_citation_schema.py`
- `tests/ui_bus/fixtures/debrief_schema_v2_1_baseline.json`
- `tests/ui_bus/test_debrief_schema_additive_only.py`
- `tests/ui_bus/test_debrief_new_wrappers_roundtrip.py`
- `tests/ui_bus/test_debrief_schemas.py`
- `tests/ui_bus/test_messages_schema.py`
- `tests/ui_bus/test_mood_change_envelope.py`
- `tests/ui_bus/test_overlay_schema.py`
- `tests/ui_bus/test_recordings_messages.py`

## What Changed

- `AGENTS.md` now records the current top-level IPC count as 72.
- `scripts/check_ipc_schema.py` no longer builds examples for stale
  `DebriefCitationSummary`, `DebriefEventTimeline`,
  `LibrarySearchRequest/Result`, `LibraryConfidence`, or
  `LibrarySimilarRequest/Result`.
- `ui_bus/messages.py`, `ui_bus/__init__.py`, and the payload schema modules
  remove those wrappers/payloads from the public bus contract.
- `library/search.py` and `library/similar.py` document the real transport:
  the library window calls `library_search` / `library_similar` Tauri commands.
- `library_cmds.rs` still maps the real search/similar/stats command results
  into UI-facing JSON, including freshness fields on stats.
- Count/parity tests now assert the 72-message contract and explicitly guard
  against reintroducing debrief placeholders without a producer/consumer.

## Source Evidence

- `src/vibemix/ui_bus/schemas/library.py:14` states search/similar run through
  the Tauri command bridge, not the live `ipc.*` bus.
- `src/vibemix/ui_bus/schemas/debrief.py:4` states debrief keeps only payloads
  with real producer and consumer paths; old placeholders were pruned.
- `tests/ui_bus/test_debrief_schema_additive_only.py:136` asserts
  `DebriefCitationSummary` and `DebriefEventTimeline` are absent.
- `tests/ui_bus/test_messages_schema.py:601` pins examples/schema count at 72.
- `tests/ui_bus/test_recordings_messages.py:325` asserts schema `oneOf` count
  is 72 and wrappers also count to 72.
- `src/vibemix/library/search.py:95` documents the Tauri `library_search`
  command bridge.
- `src/vibemix/library/similar.py:6` documents CLI or `library_similar` as the
  user-asked transport.
- `tauri/src-tauri/src/main.rs:105` registers `library_search` and
  `library_similar`; `tauri/src-tauri/src/library_cmds.rs:499` and
  `tauri/src-tauri/src/library_cmds.rs:523` implement them.

Search proof:

```text
rg -n "ipc\\.library\\.(search|search_result|confidence|similar|similar_result)|ipc\\.debrief\\.(citation-summary|event-timeline)|LibrarySearch|LibrarySimilar|LibraryConfidence|DebriefCitationSummary|DebriefEventTimeline" src/vibemix tauri/ui/src tauri/src-tauri/src tests scripts AGENTS.md
```

Only negative-assertion test references remained for the debrief placeholders.

## Verification

Schema and wiring:

```text
uv run python scripts/check_ipc_schema.py
OK: 72 dataclasses validate against schema
OK: count parity - 72 oneOf entries == 72 wrapper dataclasses
OK: SettingsSet field enum parity
OK: SettingsState payload parity

uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py
OK - every type has both a shell and a sidecar reference.

npm --prefix tauri/ui run check:ipc
codegen:ipc wrote messages.ts and validator.generated.mjs; tsc --noEmit passed.
```

Python IPC/debrief tests:

```text
uv run pytest -q tests/ipc/test_learn_envelope_parity.py tests/ipc/test_library_schemas.py tests/ui_bus/test_citation_schema.py tests/ui_bus/test_overlay_schema.py tests/ui_bus/test_debrief_new_wrappers_roundtrip.py tests/ui_bus/test_debrief_schema_additive_only.py tests/ui_bus/test_debrief_schemas.py tests/ui_bus/test_messages_schema.py tests/ui_bus/test_mood_change_envelope.py tests/ui_bus/test_recordings_messages.py
185 passed in 3.20s
```

Rust command bridge:

```text
cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds
30 passed; 86 filtered out
```

Lint/whitespace:

```text
uv run ruff check scripts/check_ipc_schema.py src/vibemix/ui_bus src/vibemix/library/search.py src/vibemix/library/similar.py tests/ipc tests/ui_bus
All checks passed!

git diff --check -- <Package 3 files>
```

## Boundaries

- No broad staging, no commit, and no product-release claim.
- Package 3 should normally land with Package 2 because both touch
  `messages.schema.json`, generated TypeScript, Python wrappers, and count
  tests. Splitting is allowed only after rerunning schema, wiring, and
  `check:ipc` on the exact staged diff.
- This package removes dead bus contracts; it does not remove the real library
  Tauri commands or their UI surfaces.
- This package does not implement future debrief citation summary or event
  timeline surfaces. Re-add those only with a real producer, consumer, schema,
  generated types, and tests.

## Next Required Proof

Before staging, rerun the same schema/codegen/wiring gates on the staged diff.
If any checker reports a count other than 72, either widen the staged IPC bundle
or deliberately document the new count in a later package.
