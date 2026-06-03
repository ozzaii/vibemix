# CODEX VERDICT — PACKAGED-LEARN-WAVS

- Item: package the committed Learn EQ exemplar WAV bank into the PyInstaller sidecar.
- SHA: `00eca14f` (`fix(packaging): bundle Learn exemplar wavs`).
- User value: a fresh installed app can carry the L1.14 EQ-as-tutor exemplar audio bank instead of losing the `.wav` files during sidecar freezing.

## By-Eye / Source Artifact

- Current source before the fix had both PyInstaller specs collecting only `**/*.json` and `**/*.txt` from the `vibemix` package.
- Current source contains four committed internal exemplar WAVs:
  - `src/vibemix/learn/assets/band_exemplars/high/vibemix_internal_high_hat_air.wav`
  - `src/vibemix/learn/assets/band_exemplars/low/vibemix_internal_low_bass_gate.wav`
  - `src/vibemix/learn/assets/band_exemplars/mid/vibemix_internal_mid_chord_body.wav`
  - `src/vibemix/learn/assets/band_exemplars/sub/vibemix_internal_sub_pulse.wav`
- Both `vibemix-core.macos.spec` and `vibemix-core.windows.spec` now include `**/*.wav` while keeping the existing secret excludes.
- PyInstaller hook check:
  - `collect_data_files("vibemix", includes=["**/*.json", "**/*.txt", "**/*.wav"], excludes=[...])` returned `wav_count=4`.
  - All four files mapped to `vibemix/learn/assets/band_exemplars/<band>`.

## Gates

- `uv run pytest -q tests/sidecar/test_build_sidecar_rename.py::test_pyinstaller_specs_collect_learn_exemplar_wavs tests/sidecar/test_build_sidecar_rename.py::test_pyinstaller_specs_collect_sqlite_vec_extension tests/sidecar/test_build_sidecar_rename.py::test_pyinstaller_specs_filter_test_submodules` -> `6 passed`.
- `uv run pytest -q tests/sidecar/test_build_sidecar_rename.py` -> `38 passed`.
- `uv run ruff check tests/sidecar/test_build_sidecar_rename.py` -> pass.
- `git diff --cached --check` -> pass.
- `uv run python scripts/check_dirty_package_plan.py --summary` -> pass; strict assignment remains noisy on pre-existing packet drift outside this slice.

## Notes

- No live app, TTS, sounddevice stream, or DMG rebuild was run in this loop.
- This proves the next PyInstaller sidecar build will collect the committed WAV bank. It does not prove an already-built DMG in `dist/` contains the files; that requires rebuilding and inspecting the artifact TOC.

---

## Increment 2 — Artifact Verifier Guard

- Item: make packaged artifact readiness checks fail when the Learn exemplar WAV bank is missing.
- SHA: `fc78b685` (`fix(release): require Learn exemplar wavs in artifacts`).
- User value: a stale DMG, copied `.app`, or Windows payload can no longer look release-ready while the tutor audio bank is absent.

## By-Eye / Source Artifact

- `scripts/dist/check_sidecar_bundle_ready.py` now declares the four required `vibemix/learn/assets/band_exemplars/.../*.wav` paths and checks them under the frozen sidecar `_internal` tree.
- The sidecar gate returns a rebuild action when the bank is missing.
- `scripts/dist/check_macos_app_bundle_ready.py` and `scripts/dist/check_windows_app_payload_ready.py` call the same helper, so copied app bundles and staged Windows payloads fail the same release condition.
- The macOS, Windows, and raw sidecar test fixtures now include fake Learn WAVs by default, and each platform has an explicit missing-WAV failure test.

## Gates

- `uv run pytest -q tests/install/test_sidecar_bundle_ready.py tests/install/test_macos_app_bundle_ready.py tests/install/test_windows_app_payload_ready.py` -> `36 passed`.
- `uv run ruff check scripts/dist/check_sidecar_bundle_ready.py scripts/dist/check_macos_app_bundle_ready.py scripts/dist/check_windows_app_payload_ready.py tests/install/test_sidecar_bundle_ready.py tests/install/test_macos_app_bundle_ready.py tests/install/test_windows_app_payload_ready.py` -> pass.
- `git diff --check -- scripts/dist/check_sidecar_bundle_ready.py scripts/dist/check_macos_app_bundle_ready.py scripts/dist/check_windows_app_payload_ready.py tests/install/test_sidecar_bundle_ready.py tests/install/test_macos_app_bundle_ready.py tests/install/test_windows_app_payload_ready.py` -> pass.

## Notes

- No live app, TTS, sounddevice stream, DMG mount, or artifact rebuild was run in this increment.
- `DDJ-FLX4` was visible on the machine during the loop, but this packaging verifier change did not require routing audio or touching the controller.
