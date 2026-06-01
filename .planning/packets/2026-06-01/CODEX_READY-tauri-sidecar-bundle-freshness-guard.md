# CODEX_READY: Tauri Sidecar Bundle Freshness Guard

Date: 2026-06-01
Verifier: Codex
Package: 13 - Tauri Sidecar Bundle Freshness Guard
Suggested commit: `fix(packaging): reject stale bundled IPC schemas`
Decision: LAND the guard; current Apple Silicon generated sidecar is fresh after rebuild

## Scope

Include:

- `scripts/dist/check_sidecar_bundle_ready.py`
- `tests/install/test_sidecar_bundle_ready.py`

Keep out:

- ignored generated bundle output under `tauri/src-tauri/binaries/**`
- ignored generated bundle output under `tauri/src-tauri/target/**`
- `build/**` and `dist/**`
- signing/notarization flow, which belongs to Package 13B

## What Is Proven

The packaging gate now rejects stale or fake sidecar resources before Tauri can
emit an app that opens with an old or unlaunchable Python sidecar.

Source evidence:

- `check_sidecar_bundle_ready.py` defines the current source IPC schema path at
  `IPC_SCHEMA_REL = tauri/ui/src/ipc/messages.schema.json`
  (`scripts/dist/check_sidecar_bundle_ready.py:19-22`).
- The expected sidecar binary is platform-triple specific under
  `tauri/src-tauri/binaries/vibemix-core-<triple>/`
  (`check_sidecar_bundle_ready.py:61-68`).
- The guard rejects missing resource directories, placeholder-only bundles,
  missing binaries, too-small binaries, non-executable POSIX binaries, and
  missing PyInstaller `_internal` directories with a concrete rebuild command
  (`check_sidecar_bundle_ready.py:91-135`).
- If the source IPC schema exists, the guard requires the embedded
  `_internal/tauri/ui/src/ipc/messages.schema.json` to exist and byte-match the
  source schema (`check_sidecar_bundle_ready.py:137-151`).
- `prepare_tauri_build.py` calls the guard before packaging, fails check-only
  mode on a red status, rebuilds the sidecar when needed in non-check mode, and
  re-checks after rebuild before returning OK
  (`scripts/dist/prepare_tauri_build.py:51-87`).

Test evidence:

- Ready bundles pass, including the case where the embedded IPC schema exactly
  matches source (`tests/install/test_sidecar_bundle_ready.py:52-69`).
- Stale embedded IPC schemas fail with a rebuild action
  (`test_sidecar_bundle_ready.py:72-80`).
- Missing embedded IPC schemas fail when the source schema exists
  (`test_sidecar_bundle_ready.py:83-90`).
- Placeholder-only, missing-binary, too-small, non-executable, and missing
  `_internal` bundles all fail (`test_sidecar_bundle_ready.py:93-151`).
- Windows bundles do not require a POSIX executable bit
  (`test_sidecar_bundle_ready.py:134-141`).
- `prepare_tauri_build.py` tests cover check-only failure, ready-input no-op,
  forced rebuild, missing-sidecar rebuild/recheck, Windows spec selection,
  frontend-build ordering, and failing main return paths
  (`tests/install/test_prepare_tauri_build.py:13-130`).

## Verification

Focused tests:

```text
uv run pytest -q tests/install/test_sidecar_bundle_ready.py tests/install/test_prepare_tauri_build.py
```

Result:

```text
20 passed in 0.03s
```

Lint:

```text
uv run ruff check scripts/dist/check_sidecar_bundle_ready.py tests/install/test_sidecar_bundle_ready.py
```

Result:

```text
All checks passed!
```

Removed IPC ghost scan:

```text
rg -n "ipc\.debrief\.citation-summary|ipc\.debrief\.event-timeline|ipc\.library\.search|ipc\.library\.search_result|ipc\.library\.confidence|ipc\.library\.similar_request|ipc\.library\.similar_result" src tauri/ui/src tauri/src-tauri/src tests scripts
```

Result: no matches.

Initial artifact readiness check before rebuild:

```text
uv run python scripts/dist/prepare_tauri_build.py --skip-frontend --check-only
```

Result:

```text
[prepare-tauri] FAIL: bundled IPC schema is stale: /Users/ozai/projects/dj-set-ai/tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/_internal/tauri/ui/src/ipc/messages.schema.json. Run `uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec`.
```

Initial direct guard before rebuild:

```text
uv run python scripts/dist/check_sidecar_bundle_ready.py
```

Result:

```text
[sidecar-bundle] FAIL: bundled IPC schema is stale: /Users/ozai/projects/dj-set-ai/tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/_internal/tauri/ui/src/ipc/messages.schema.json. Run `uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec`.
```

Post-rebuild proof, 2026-06-01:

```text
uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec
```

Result:

```text
[build_sidecar] OK: no AIza-pattern strings found in bundle (403 file(s) scanned in /Users/ozai/projects/dj-set-ai/tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin)
[build_sidecar] installed: /Users/ozai/projects/dj-set-ai/tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin
```

Freshness guard after rebuild:

```text
uv run python scripts/dist/prepare_tauri_build.py --skip-frontend --check-only
```

Result:

```text
[prepare-tauri] OK: sidecar bundle ready: /Users/ozai/projects/dj-set-ai/tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin
```

Direct guard after rebuild:

```text
uv run python scripts/dist/check_sidecar_bundle_ready.py
```

Result:

```text
[sidecar-bundle] OK: sidecar bundle ready: /Users/ozai/projects/dj-set-ai/tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin
```

Embedded schema check:

```text
cmp -s tauri/ui/src/ipc/messages.schema.json tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/_internal/tauri/ui/src/ipc/messages.schema.json && echo 'embedded IPC schema matches source'
```

Result:

```text
embedded IPC schema matches source
```

Fresh sidecar binary:

```text
tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin 25257936 bytes 2026-06-01 07:29:39 +0300
```

Fresh local Tauri app/DMG rehearsal, 2026-06-01:

```text
bash scripts/dist/build_macos_local_dmg.sh --smoke library-stats
```

Result:

```text
[local-dmg] building unsigned .app
[prepare-tauri] OK: sidecar bundle ready: /Users/ozai/projects/dj-set-ai/tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin
[repair_macos_app_sidecar_symlinks] scanned=1 relinked=36 already_linked=0 missing_top_level=0
[macos-app-bundle] OK: /Users/ozai/projects/dj-set-ai/tauri/src-tauri/target/release/bundle/macos/vibemix.app/Contents/Resources/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin
[macos-dmg-artifact] OK: /var/.../vibemix.app
/Users/ozai/projects/dj-set-ai/tauri/src-tauri/target/release/bundle/dmg/vibemix_0.0.1_aarch64.dmg
```

Artifact identity:

```text
tauri/src-tauri/target/release/bundle/dmg/vibemix_0.0.1_aarch64.dmg 119464615 bytes 2026-06-01 07:36:28 +0300
tauri/src-tauri/target/release/bundle/macos/vibemix.app/Contents/MacOS/vibemix 31864320 bytes 2026-06-01 07:36:01 +0300
tauri/src-tauri/target/release/bundle/macos/vibemix.app/Contents/Resources/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin 25257936 bytes 2026-06-01 07:35:07 +0300
```

Hashes:

```text
ae929e88c3ef24d092cfb915b6a01780e28353730e86a120212e5bd6724b321d  tauri/src-tauri/target/release/bundle/dmg/vibemix_0.0.1_aarch64.dmg
4b450918403da0b3dd3650d5df9fbc90e3481cff23c0b67a273abfdb9a973e64  tauri/src-tauri/target/release/bundle/macos/vibemix.app/Contents/Resources/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin
```

Extra bundle verifier:

```text
uv run python -m scripts.dist.verify_binary tauri/src-tauri/target/release/bundle/macos/vibemix.app --report /tmp/vibemix-local-app-verify-report.json
```

Result:

```text
[verify_binary] scanned=407 hits=0 report=/tmp/vibemix-local-app-verify-report.json
```

Whitespace:

```text
git diff --check -- scripts/dist/check_sidecar_bundle_ready.py tests/install/test_sidecar_bundle_ready.py
```

Result: clean.

Follow-up latest-code rebuild after packaged boot fixes, 2026-06-01:

```text
bash scripts/dist/build_macos_local_dmg.sh --smoke library-stats
```

Result:

```text
[build_sidecar] OK: no AIza-pattern strings found in bundle (403 file(s) scanned in /Users/ozai/projects/dj-set-ai/tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin)
[prepare-tauri] OK: sidecar bundle ready: /Users/ozai/projects/dj-set-ai/tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin
[macos-app-bundle] OK: /Users/ozai/projects/dj-set-ai/tauri/src-tauri/target/release/bundle/macos/vibemix.app/Contents/Resources/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin
[macos-dmg-artifact] OK: /var/.../vibemix.app
```

Latest unsigned local DMG:

```text
tauri/src-tauri/target/release/bundle/dmg/vibemix_0.0.1_aarch64.dmg 119468447 bytes 2026-06-01 08:17:10 +0300
sha256 efe673e4b0a36acd7723a650630008b8287df1a835063e556aa0c7d3c051fdfc
```

Latest-code packaged boot and Quit proof:

```text
open -n tauri/src-tauri/target/release/bundle/macos/vibemix.app
```

Evidence:

```text
process tree: app PID 53591 -> bundled sidecar PID 53595
listener: vibemix-core PID 53595 owns TCP 127.0.0.1:8765
sidecar_status: ws_reachable=true, dev_sidecar=false, gemini_key_present=true
ui.log: rust bridge ws-state {"state":"connected"}
ws_observe: ipc.status.tick livekit=ok gemini=ok midi=1 screen=unavailable
```

Quit:

```text
osascript -e 'tell application id "world.bravoh.vibemix" to quit'
```

Result:

```text
no vibemix.app process, no bundled sidecar process, no 127.0.0.1:8765 listener
sidecar_status: ws_reachable=false
```

Latest signed-DMG copied-app proof repeated the same boot/Quit contract:

```text
dist/fresh-20260601-latest/vibemix-0.0.1.dmg
process tree: /tmp copied app PID 56437 -> bundled sidecar PID 56441
listener: vibemix-core PID 56441 owns TCP 127.0.0.1:8765
ws_observe: ipc.status.tick livekit=ok gemini=ok midi=1 screen=unavailable
after osascript quit: no copied app process, no bundled sidecar process, no 127.0.0.1:8765 listener
sidecar_status: ws_reachable=false
```

## Classification

LAND:

- The guard code and tests are ready.
- The earlier failure on the local sidecar was expected and valuable: it proved
  the guard blocks stale packaged resources instead of letting an old build mask
  current-source wiring.
- After rebuilding the Apple Silicon sidecar from current source, the package
  input freshness guard is green and the embedded IPC schema byte-matches source.

Still not a release claim:

- This proves the generated Apple Silicon sidecar resource is fresh.
- It also proves an unsigned local Tauri `.app`/DMG was rebuilt from that fresh
  sidecar, survives a drag-install smoke, boots its bundled sidecar, emits live
  status ticks, and quits without orphaning that sidecar.
- Signed/notarized artifact proof remains Package 13B. The latest signed DMG is
  now `dist/fresh-20260601-latest/vibemix-0.0.1.dmg`.
