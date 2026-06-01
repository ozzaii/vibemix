# CODEX_READY: Live TTS Shutdown Hygiene

Date: 2026-06-01
Verifier: Codex
Status: LAND packet, runtime cleanup slice
Package: 14 - Live TTS Shutdown Hygiene
Suggested commit: `fix(runtime): close nested live tts providers`

## Decision

LAND this slice as runtime shutdown hygiene.

The live TTS adapter can own nested provider/session objects. The shutdown path
now closes the adapter, recursively closes nested provider objects, and closes
common nested client-session attributes once, without double-closing shared
sessions.

## Scope

Include:

- `src/vibemix/__main__.py`
- `tests/test_main_smoke.py`
- `.planning/packets/2026-06-01/CODEX_READY-live-tts-shutdown-hygiene.md`

Keep out:

- Live-stack budget CLI/parser/reporting hunks from the same `__main__.py`
  file. Those belong to Package 10.
- Packaged-app release proof.

Shared-file caution:

- `src/vibemix/__main__.py` is shared by multiple packages. If Package 14 lands
  independently, stage only `_close_tts_chain()` and the shutdown cleanup call.

## Source Evidence

- `build_tts_chain` is a lazily resolved live dependency
  (`src/vibemix/__main__.py:170-179`).
- `_close_tts_chain()` deduplicates provider objects and nested closeable
  sessions, calls async `aclose()` on providers, recurses through
  `_tts_instances`, and closes `_session`, `_http_session`, and
  `_client_session` if present (`__main__.py:210-241`).
- Direct mode and proxy mode both assign the live TTS adapter to `tts_inst`
  (`__main__.py:1239-1267`).
- The main cleanup path now calls `await _close_tts_chain(tts_inst)` after
  `session.aclose()`, and logs rather than crashes if TTS cleanup itself fails
  (`__main__.py:2514-2521`).
- The test constructs a parent provider, a duplicated child provider, and a
  shared owned session, then proves every unique object closes once
  (`tests/test_main_smoke.py:674-704`).

## Verification

Focused close helper:

```text
uv run pytest -q tests/test_main_smoke.py -k close_tts_chain
```

Result:

```text
1 passed, 29 deselected in 0.48s
```

Helper plus cleanup smoke:

```text
uv run pytest -q tests/test_main_smoke.py::test_close_tts_chain_closes_nested_providers_once tests/test_main_smoke.py::test_smoke_05_cleanup_closes_all_streams
```

Result:

```text
2 passed in 1.94s
```

Full main smoke file:

```text
uv run pytest -q tests/test_main_smoke.py
```

Result:

```text
30 passed in 2.34s
```

Lint:

```text
uv run ruff check src/vibemix/__main__.py tests/test_main_smoke.py
```

Result:

```text
All checks passed!
```

Whitespace:

```text
git diff --check -- src/vibemix/__main__.py tests/test_main_smoke.py
```

Result: clean.

Source-run proof:

```text
VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix
```

Observed:

- recording session `20260601-072348`
- `DDJ-FLX4` detected
- `tts: Cartesia Sonic (primary) -> gemini-3.1-flash-tts-preview -> gemini-2.5-flash-preview-tts`
- mascot bus reached `ws://127.0.0.1:8765`
- MCP `ws_observe(seconds=2, type_filter="ipc.session.snapshot")` captured 26
  snapshot frames
- Ctrl-C shutdown printed `-> stopping...`, session cost, then `-> bye`
- no `Unclosed client session` warning appeared in the captured shutdown output
- follow-up MCP `sidecar_status` reported `ws_reachable: false`

## Boundaries

- No broad staging, no commit, and no product-release claim.
- This packet proves source-run shutdown hygiene, not packaged-app release
  hygiene.
- A final release still needs a rebuilt fresh sidecar, signed/notarized DMG, and
  clean install/launch proof from the final artifact.
