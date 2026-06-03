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

---

## Increment 3 — Current Artifact Reality Check

- Item: run the release guards against current macOS artifacts and fix the guard crash exposed by `--require-moss-source`.
- SHA: `86d2e535` (`fix(release): inspect bundled MOSS without runtime imports`).
- User value: the artifact checker now produces a truthful package verdict on a plain inspection machine instead of crashing because LiveKit is not installed in the verifier environment.

## By-Eye / Artifact Evidence

- `scripts/dist/check_sidecar_bundle_ready.py` now validates bundled MOSS source by reading `browser_poc_manifest.json`, the TTS/codec meta JSON, ONNX files, and external data files directly. It no longer imports `vibemix.agent.local_tts` or LiveKit for release inspection.
- Regression test `test_bundled_moss_model_check_does_not_import_tts_runtime` fails if the verifier imports `vibemix.agent.local_tts` or `livekit`.
- Checked these current macOS artifacts with `--smoke none --require-moss-source`:
  - `dist/fresh-20260603-bpm/vibemix-0.0.1.dmg`
  - `dist/fresh-20260603-head/vibemix-0.0.1.dmg`
  - `dist/vibemix-0.0.1.dmg`
  - `dist/signed-local/vibemix-0.0.1.dmg`
  - `tauri/src-tauri/target/release/bundle/macos/vibemix.app`
- Result: all five artifacts had bundled MOSS source ready, but all five failed readiness because the four Learn exemplar WAVs were missing from the frozen sidecar.

## Gates

- `uv run pytest -q tests/install/test_sidecar_bundle_ready.py tests/install/test_macos_app_bundle_ready.py tests/install/test_windows_app_payload_ready.py` -> `37 passed`.
- `uv run ruff check scripts/dist/check_sidecar_bundle_ready.py tests/install/test_sidecar_bundle_ready.py` -> pass.
- `git diff --cached --check` -> pass.
- Current-artifact checks reached a real verdict instead of raising `ModuleNotFoundError: No module named 'livekit'`.

## Notes

- No live app, TTS, sounddevice stream, or sidecar smoke command was run; the artifact checks mounted/copied DMGs only.
- Answer to the BPM package question from current evidence: the `fresh-20260603-bpm` DMG exists, but it is not release-ready under the current guard. The package needs a fresh sidecar/app/DMG rebuild from `00eca14f` or later so the WAV bank is actually present.

---

## Increment 4 — Fresh Local DMG With WAV Bank

- Item: rebuild the macOS sidecar and local unsigned DMG from the fixed spec, then prove the package carries the Learn WAV bank.
- Artifact: `dist/fresh-20260604-wav/vibemix-0.0.1.dmg` (`486,977,797` bytes, unsigned local rehearsal DMG).
- User value: a local drag-install package now contains both bundled MOSS and the Learn EQ exemplar WAVs instead of only detecting the stale package failure.

## By-Eye / Artifact Evidence

- Rebuilt the macOS sidecar via `uv run python scripts/dist/prepare_tauri_build.py --skip-frontend --force-sidecar --require-moss-source`.
- Sidecar build output:
  - `[moss_bundle] bundled 16 MOSS model file(s)`
  - `OK: no AIza-pattern strings found in bundle (406 file(s) scanned)`
  - `OK: sidecar bundle ready`
- Verified the rebuilt sidecar contains all four Learn WAVs under:
  - `tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/_internal/vibemix/learn/assets/band_exemplars/high/vibemix_internal_high_hat_air.wav`
  - `.../low/vibemix_internal_low_bass_gate.wav`
  - `.../mid/vibemix_internal_mid_chord_body.wav`
  - `.../sub/vibemix_internal_sub_pulse.wav`
- Rebuilt unsigned Tauri `.app` with `VIBEMIX_REQUIRE_MOSS_SOURCE=1 cargo tauri build --bundles app --no-sign --ci`.
- Repaired app-side PyInstaller symlinks:
  - `scanned=1 relinked=36 already_linked=0 missing_top_level=0`
- App readiness passed:
  - `ok=true`
  - `moss_source=bundled MOSS model ready`
  - `errors=[]`
- Created fresh local DMG from the repaired app and checked drag-install readiness twice:
  - `--smoke none --require-moss-source` -> `ok=true`
  - `--smoke version --require-moss-source` -> `ok=true`, `smoke_stdout="vibemix 0.1.0-dev0"`

## Gates

- `python3 scripts/dist/check_sidecar_bundle_ready.py --triple aarch64-apple-darwin --require-moss-source --quiet` -> pass.
- `python3 scripts/dist/check_macos_app_bundle_ready.py tauri/src-tauri/target/release/bundle/macos/vibemix.app --triple aarch64-apple-darwin --smoke none --require-moss-source --json` -> `ok=true`.
- `python3 scripts/dist/check_macos_dmg_artifact_ready.py dist/fresh-20260604-wav/vibemix-0.0.1.dmg --triple aarch64-apple-darwin --smoke version --require-moss-source --json` -> `ok=true`.

## Notes

- No live app, TTS, sounddevice stream, or co-host speech was run. The sidecar smoke was `--version` only.
- This is a local unsigned rehearsal DMG. Signing/notarization/stapling remain separate release gates.

---

## Increment 5 — Signed + Notarized DMG

- Item: run the real macOS signing/notarization chain on the fresh WAV/MOSS package and fix the signer gate that assessed the wrong artifact.
- SHA: `cdd24e5c` (`fix(signing): assess notarized DMG and assert Developer ID seal`).
- Artifact: `dist/fresh-20260604-wav-signed-v2/vibemix-0.0.1.dmg`.
- User value: the macOS package now clears Apple notarization, stapling, Gatekeeper, drag-install sidecar readiness, MOSS source, Learn WAV bank, and secret scanning.

## By-Eye / Artifact Evidence

- First signing attempt notarized and stapled the DMG, but Stage 7 checked the unstapled source `.app` and failed. It also lacked an immediate Developer ID resource-seal assertion.
- `scripts/dist/sign_macos.sh` now:
  - asserts the `.app` is signed by `Developer ID Application`, has the expected `TeamIdentifier`, and has `Contents/_CodeSignature/CodeResources`;
  - asserts the DMG is signed by `Developer ID Application`;
  - runs Gatekeeper against the stapled DMG with `spctl --assess --type open --context context:primary-signature`.
- Patched signer run completed:
  - `Developer ID signature OK: .app bundle`
  - `Developer ID signature OK: DMG`
  - Notary submission `1625dae0-06b0-442d-ba64-4840775bb6e7`
  - Stapler: `The validate action worked!`
  - `spctl`: `accepted`, `source=Notarized Developer ID`
  - `verify_binary`: `scanned=414 hits=0`
- Final drag-install package check:
  - `python3 scripts/dist/check_macos_dmg_artifact_ready.py dist/fresh-20260604-wav-signed-v2/vibemix-0.0.1.dmg --triple aarch64-apple-darwin --smoke version --require-moss-source --json`
  - Result: `ok=true`, `errors=[]`, `smoke_stdout="vibemix 0.1.0-dev0"`, `moss_source=bundled MOSS model ready`.

## Gates

- `bash -n scripts/dist/sign_macos.sh` -> pass.
- `uv run pytest -q tests/security/test_release_yml_signing_skips.py` -> `18 passed`.
- `spctl --assess --type open --context context:primary-signature -vvv dist/fresh-20260604-wav-signed-v2/vibemix-0.0.1.dmg` -> `accepted`, `source=Notarized Developer ID`.
- `xcrun stapler validate dist/fresh-20260604-wav-signed-v2/vibemix-0.0.1.dmg` -> `The validate action worked!`.
- Notary detail: `status=Accepted`, `issues=0`.
- `verify-report.json`: `status=clean`, `scanned=414`, `hits=[]`.

## Notes

- No live app, TTS, sounddevice stream, or co-host speech was run. The only sidecar execution was `--version` from the copied DMG app.
- This is the current strongest macOS package artifact from this loop. It still needs whatever external release-channel upload/update-manifest steps the release process requires; those were not performed here.

---

## Increment 6 — macOS Arm64 Updater Artifact

- Item: create and verify the Tauri updater archive for the signed macOS arm64 app.
- Artifact: `dist/fresh-20260604-wav-signed-v2/vibemix-0.0.1-arm64.app.tar.gz`.
- Signature sidecar: `dist/fresh-20260604-wav-signed-v2/vibemix-0.0.1-arm64.app.tar.gz.sig`.
- User value: the release now has the macOS arm64 updater payload shape that `latest.json` must point at; the DMG is not misused as the updater artifact.

## By-Eye / Artifact Evidence

- Created archive via:
  - `scripts/dist/create_macos_updater_artifact.sh --arch arm64 --output-dir dist/fresh-20260604-wav-signed-v2 tauri/src-tauri/target/release/bundle/macos/vibemix.app`
- The local updater keypair exists under `~/.tauri/vibemix_updater.key{,.pub}`; exported it to the script environment and produced `.sig`.
- Artifact sizes:
  - archive: `481M`
  - signature: `684B`
- Archive TOC contains:
  - `vibemix.app/Contents/_CodeSignature/CodeResources`
  - bundled MOSS manifest
  - all four Learn exemplar WAVs.
- Extracted archive readiness:
  - `ok=true`
  - `errors=[]`
  - `moss_source=bundled MOSS model ready`
  - `smoke_stdout="vibemix 0.1.0-dev0"`

## Gates

- `python3 scripts/dist/check_macos_updater_artifact_ready.py dist/fresh-20260604-wav-signed-v2/vibemix-0.0.1-arm64.app.tar.gz --triple aarch64-apple-darwin --smoke version --require-moss-source --json` -> `ok=true`.
- `tar -tzf ... | rg 'band_exemplars/.+\\.wav$|_CodeSignature/CodeResources|MOSS-TTS-Nano-100M-ONNX/browser_poc_manifest.json'` -> expected seal, MOSS manifest, and four WAV entries present.

## Notes

- No live app, TTS, sounddevice stream, or co-host speech was run. The only sidecar execution was `--version` from the extracted updater app.
- Full signed `latest.json` still requires the release workflow's remaining platform artifacts (`darwin-x86_64` updater archive and Windows Tauri NSIS updater installer). Those were not produced on this arm64 macOS loop.
