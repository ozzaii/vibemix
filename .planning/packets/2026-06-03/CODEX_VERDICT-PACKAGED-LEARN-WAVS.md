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
