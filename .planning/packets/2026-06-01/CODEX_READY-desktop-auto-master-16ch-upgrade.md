# CODEX_READY: Desktop Auto-Master 16ch Upgrade

Date: 2026-06-01
Verifier: Codex
Status: LAND packet, macOS audio routing slice
Package: 15 - Desktop Auto-Master 16ch Upgrade
Suggested commit: `fix(audio): honor explicit blackhole variants in auto-master mode`

## Decision

LAND this slice as `fix(audio): honor explicit blackhole variants in auto-master mode`.

This package fixes a Tauri/source-run routing trap: `VIBEMIX_AUTO_MASTER_INPUT=1`
may upgrade generic BlackHole auto-master requests, but it must not rewrite an
explicit `BlackHole 16ch` input request back through the silent auto-master
fallback.

## Files

- `src/vibemix/platform/_audio_macos.py`
- `tests/test_audio_macos.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/packets/2026-06-01/INDEX.md`
- `.planning/packets/2026-06-01/CODEX_READY-desktop-auto-master-16ch-upgrade.md`

## What Changed

- Auto-master selection now intercepts only generic auto-master requests plus
  generic `BlackHole` / `BlackHole 2ch` when `VIBEMIX_AUTO_MASTER_INPUT=1`.
- Explicit `BlackHole 16ch` requests remain exact BlackHole variant lookups.
- Regression coverage proves the 16ch request is not probed/rewritten by the
  auto-master signal selector.

## Source Evidence

- The `AudioMacOS.find_device()` docstring now states the intended split:
  auto-master can sample loopbacks for `"auto"`/generic master requests, but
  explicit variants such as `"BlackHole 16ch"` are honored exactly
  (`src/vibemix/platform/_audio_macos.py:586-590`).
- The actual branch only routes to `select_active_master_input()` for
  `_AUTO_MASTER_REQUESTS` or for generic `BlackHole` / `BlackHole 2ch` while
  `VIBEMIX_AUTO_MASTER_INPUT` is enabled (`_audio_macos.py:598-604`).
- Explicit non-generic BlackHole variants use `find_device_index()` directly
  (`_audio_macos.py:605-607`).
- `test_find_device_auto_master_input_honors_explicit_blackhole_variant()` proves
  `BlackHole 16ch` resolves to the 16ch device and never calls `sd.rec()` even
  when `VIBEMIX_AUTO_MASTER_INPUT=1` (`tests/test_audio_macos.py:383-412`).
- Main-smoke tests prove the zero-config/default 2ch BlackHole path still
  upgrades to `BlackHole 16ch` when deck routing reports
  `capture_device_too_few_channels` (`tests/test_main_smoke.py:191-238`,
  `tests/test_main_smoke.py:271-319`).

## Evidence

Focused routing tests:

```text
uv run pytest -q tests/test_audio_macos.py::test_find_device_auto_master_input_honors_explicit_blackhole_variant tests/test_audio_macos.py::test_find_device_auto_master_input_chooses_live_48k_variant tests/test_audio_macos.py::test_find_device_auto_master_input_falls_back_to_48k_variant_when_silent tests/test_main_smoke.py::test_deck_audio_auto_upgrades_default_blackhole_input tests/test_main_smoke.py::test_deck_audio_global_default_upgrades_blackhole_without_env
5 passed in 0.39s
```

Full macOS audio backend test file:

```text
uv run pytest -q tests/test_audio_macos.py
23 passed in 0.28s
```

Lint:

```text
uv run ruff check src/vibemix/platform/_audio_macos.py tests/test_audio_macos.py src/vibemix/__main__.py tests/test_main_smoke.py
All checks passed!
```

Whitespace:

```text
git diff --check -- src/vibemix/platform/_audio_macos.py tests/test_audio_macos.py
```

Historical Tauri dev proof from the checklist:

- `VIBEMIX_DEV_SIDECAR=1 cargo tauri dev --no-watch` brought up renderer/Rust
  bridge/pill path.
- `ws_probe.py --ipc ipc.status.recheck --payload-json '{"component":"midi"}'`
  returned `livekit=ok gemini=ok midi=1`.
- Session `20260531-103122` recorded `requested_device=BlackHole_16ch`,
  `input_channels=16`, `opened_channels=4`, `mode=deck_pair_capture_configured`,
  plus real jog-wheel MIDI evidence.

## Boundaries

- No broad staging, no commit, and no product-release claim.
- This proves route/capture/controller/UI plumbing, not musical grounding.
- The current turn did not launch Tauri or run audible deck proof.

## Next Required Proof

Run a fresh source or packaged live proof with audible deck audio and a cited
co-host moment before claiming the desktop audio setup is release-complete.
