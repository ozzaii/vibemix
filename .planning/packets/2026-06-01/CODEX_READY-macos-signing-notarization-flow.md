# CODEX_READY: macOS Signing And Notarization Flow

Date: 2026-06-01
Verifier: Codex
Package: 13B - macOS Signing And Notarization Flow
Suggested commit: `fix(packaging): support local notarization fallback`
Decision: LAND signing/notarization support and fresh signed DMG proof; do not claim product release

## Scope

Include:

- `docs/signing-macos.md`
- `scripts/dist/sign_macos.sh`
- `tauri/src-tauri/tauri.conf.json5`
- `tests/security/test_release_yml_signing_skips.py`

Keep out:

- Package 13 sidecar freshness rebuild/output
- local certificate dumps (`codesign0`, `codesign1`, `codesign2`)
- final clean-machine install proof
- DDJ/FLX4 product proof

## What Is Proven

The macOS signing flow now has a documented local fallback and keeps CI signing
material handling in one script.

Source evidence:

- The manual signing doc keeps ASC API-key signing as the preferred one-liner,
  then adds a local Apple-ID app-specific-password fallback using
  `APPLE_SIGNING_IDENTITY`, `APPLE_TEAM_ID`, `APPLE_ID`, and `APPLE_PASSWORD`
  (`docs/signing-macos.md:6-29`).
- The doc states CI mode imports the P12 and API key into temporary material,
  while local mode prefers `.p8` credentials and falls back to Apple-ID
  app-specific-password notarization (`docs/signing-macos.md:150-167`).
- The script header declares one notarization credential set and the
  `APPLE_SIGNING_IDENTITY` compatibility alias
  (`scripts/dist/sign_macos.sh:31-52`).
- Runtime parsing resolves `APPLE_DEVELOPER_ID` from
  `APPLE_SIGNING_IDENTITY` when needed (`sign_macos.sh:101-107`).
- The environment validator requires CI API-key material in CI, accepts a full
  local API-key tuple, or accepts a local Apple-ID/password tuple; partial auth
  sets fail fast without echoing secrets (`sign_macos.sh:198-253`).
- CI signing material is decoded/imported into a temporary keychain and verified
  before signing (`sign_macos.sh:255-298`).
- Shared `NOTARY_AUTH_ARGS` are built once for either API-key or Apple-ID auth
  and reused for both `notarytool submit` and `notarytool log`
  (`sign_macos.sh:300-325`, `sign_macos.sh:489-521`).
- Local identity verification remains fast-fail through
  `security find-identity -p codesigning -v`, and dry-run stops after
  prerequisites (`sign_macos.sh:338-352`).
- Stapling remains idempotent, Gatekeeper `spctl` acceptance is a hard gate, and
  `verify_binary.py` remains a release-blocking secret scan
  (`sign_macos.sh:528-585`).
- Tauri's `beforeBuildCommand` is now relative to the `tauri/` cwd, so direct
  local `cargo tauri build` runs the repo-root preparation script instead of a
  wrong path (`tauri/src-tauri/tauri.conf.json5:23-28`).
- The signing test keeps the sidecar symlink repair before the nested Mach-O
  force-sign stage (`tests/security/test_release_yml_signing_skips.py:107-113`).

## Verification

Shell syntax:

```text
bash -n scripts/dist/sign_macos.sh
```

Result: clean.

Focused tests:

```text
uv run pytest -q tests/security/test_release_yml_signing_skips.py tests/dist/test_verify_binary.py tests/install/test_sidecar_bundle_ready.py tests/install/test_prepare_tauri_build.py
```

Result:

```text
60 passed in 0.81s
```

Lint:

```text
uv run ruff check scripts/dist/check_sidecar_bundle_ready.py tests/install/test_sidecar_bundle_ready.py tests/security/test_release_yml_signing_skips.py
```

Result:

```text
All checks passed!
```

Rust config check:

```text
cargo check --manifest-path tauri/src-tauri/Cargo.toml
```

Result:

```text
Finished `dev` profile [unoptimized + debuginfo] target(s) in 4.48s
```

Existing signed DMG evidence:

```text
stat -f '%N %z bytes %Sm' -t '%Y-%m-%d %H:%M:%S %z' dist/vibemix-0.0.1.dmg
```

Result:

```text
dist/vibemix-0.0.1.dmg 119812586 bytes 2026-05-31 19:02:20 +0300
```

```text
shasum -a 256 dist/vibemix-0.0.1.dmg
```

Result:

```text
d3cbdeebd55aff6fcc37d1e3e499c57380fb0dfc57982119aa05fcd6b5300100  dist/vibemix-0.0.1.dmg
```

```text
codesign -dv --verbose=4 dist/vibemix-0.0.1.dmg
```

Observed:

- `Authority=Developer ID Application: Francesco Fasanella (UK7DYFK6F8)`
- `TeamIdentifier=UK7DYFK6F8`
- `Timestamp=31 May 2026 at 18:58:51`
- `Notarization Ticket=stapled`

```text
xcrun stapler validate dist/vibemix-0.0.1.dmg
```

Result:

```text
The validate action worked!
```

```text
spctl -a -vvv -t install dist/vibemix-0.0.1.dmg
```

Result:

```text
dist/vibemix-0.0.1.dmg: accepted
source=Notarized Developer ID
origin=Developer ID Application: Francesco Fasanella (UK7DYFK6F8)
```

Inner app evidence:

```text
codesign --verify --deep --strict --verbose=2 tauri/src-tauri/target/release/bundle/macos/vibemix.app
```

Result:

```text
tauri/src-tauri/target/release/bundle/macos/vibemix.app: valid on disk
tauri/src-tauri/target/release/bundle/macos/vibemix.app: satisfies its Designated Requirement
```

```text
spctl --assess --type execute --verbose=4 tauri/src-tauri/target/release/bundle/macos/vibemix.app
```

Result:

```text
tauri/src-tauri/target/release/bundle/macos/vibemix.app: accepted
source=Notarized Developer ID
```

Verifier/notary reports:

```text
rg -n '"status": "clean"|"scanned": 407|"hits": \[\]|"status": "Accepted"' dist/verify-report.json dist/notarytool-detail.json
```

Result:

```text
dist/verify-report.json:4:  "hits": [],
dist/verify-report.json:5:  "scanned": 407,
dist/verify-report.json:6:  "status": "clean"
dist/notarytool-detail.json:4:  "status": "Accepted",
```

Whitespace:

```text
git diff --check -- docs/signing-macos.md scripts/dist/sign_macos.sh tauri/src-tauri/tauri.conf.json5 tests/security/test_release_yml_signing_skips.py
```

Result: clean.

## Boundary

This packet proves the signing/notarization flow and a fresh accepted artifact.
It still does not prove product release acceptance, because live install/use
acceptance and launch-collateral cleanup remain open.

Package 13 previously detected the generated bundled sidecar IPC schema as
stale:

```text
uv run python scripts/dist/prepare_tauri_build.py --skip-frontend --check-only
```

Result:

```text
[prepare-tauri] FAIL: bundled IPC schema is stale: /Users/ozai/projects/dj-set-ai/tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/_internal/tauri/ui/src/ipc/messages.schema.json. Run `uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec`.
```

That sidecar freshness blocker was cleared later on 2026-06-01:

```text
uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec
uv run python scripts/dist/prepare_tauri_build.py --skip-frontend --check-only
```

Result:

```text
[prepare-tauri] OK: sidecar bundle ready: /Users/ozai/projects/dj-set-ai/tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin
```

A fresh unsigned local app/DMG was then rebuilt and smoked:

```text
bash scripts/dist/build_macos_local_dmg.sh --smoke library-stats
```

Result:

```text
[macos-app-bundle] OK: /Users/ozai/projects/dj-set-ai/tauri/src-tauri/target/release/bundle/macos/vibemix.app/Contents/Resources/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin
[macos-dmg-artifact] OK: /var/.../vibemix.app
```

Fresh unsigned local DMG:

```text
tauri/src-tauri/target/release/bundle/dmg/vibemix_0.0.1_aarch64.dmg
119464615 bytes
mtime 2026-06-01 07:36:28 +0300
sha256 ae929e88c3ef24d092cfb915b6a01780e28353730e86a120212e5bd6724b321d
```

Extra app secret scan:

```text
uv run python -m scripts.dist.verify_binary tauri/src-tauri/target/release/bundle/macos/vibemix.app --report /tmp/vibemix-local-app-verify-report.json
[verify_binary] scanned=407 hits=0 report=/tmp/vibemix-local-app-verify-report.json
```

Fresh signing/notarization pass:

```text
./scripts/dist/sign_macos.sh --dry-run --output-dir dist/fresh-20260601 tauri/src-tauri/target/release/bundle/macos/vibemix.app
```

Result:

```text
[sign_macos] prerequisites OK: app=tauri/src-tauri/target/release/bundle/macos/vibemix.app entitlements=/Users/ozai/projects/dj-set-ai/tauri/src-tauri/entitlements.macos.plist notary_auth=apple-id
[sign_macos] DRY-RUN: stopping after Stage 1; no codesign / notarytool / staple invoked
```

```text
./scripts/dist/sign_macos.sh --output-dir dist/fresh-20260601 tauri/src-tauri/target/release/bundle/macos/vibemix.app
```

Result:

```text
[repair_macos_app_sidecar_symlinks] scanned=1 relinked=0 already_linked=36 missing_top_level=0
[sign_macos]   force-signed 167 nested Mach-O binaries (deepest-first)
tauri/src-tauri/target/release/bundle/macos/vibemix.app: valid on disk
tauri/src-tauri/target/release/bundle/macos/vibemix.app: satisfies its Designated Requirement
[sign_macos] fetching notarization log for submission ff556162-a08d-4fb8-acfd-78664d8d8465
The staple and validate action worked!
tauri/src-tauri/target/release/bundle/macos/vibemix.app: accepted
source=Notarized Developer ID
[verify_binary] scanned=407 hits=0 report=dist/fresh-20260601/verify-report.json
[sign_macos] DONE: vibemix-0.0.1.dmg notarized + stapled + verified
dist/fresh-20260601/vibemix-0.0.1.dmg
```

Fresh signed/notarized DMG:

```text
dist/fresh-20260601/vibemix-0.0.1.dmg 119953279 bytes 2026-06-01 07:42:22 +0300
sha256 8f52423c7bdaf6a4bb9657606951532675f97239ecc857466c9721a39b26820b
```

Signature identity:

```text
Authority=Developer ID Application: Francesco Fasanella (UK7DYFK6F8)
Authority=Developer ID Certification Authority
Authority=Apple Root CA
Timestamp=1 Jun 2026 at 07:40:19
Notarization Ticket=stapled
TeamIdentifier=UK7DYFK6F8
```

Independent fresh-DMG checks:

```text
xcrun stapler validate dist/fresh-20260601/vibemix-0.0.1.dmg
spctl -a -vvv -t install dist/fresh-20260601/vibemix-0.0.1.dmg
uv run python scripts/dist/check_macos_dmg_artifact_ready.py dist/fresh-20260601/vibemix-0.0.1.dmg --smoke library-stats --json
codesign --verify --deep --strict --verbose=2 tauri/src-tauri/target/release/bundle/macos/vibemix.app
spctl --assess --type execute --verbose=4 tauri/src-tauri/target/release/bundle/macos/vibemix.app
```

Results:

```text
The validate action worked!
dist/fresh-20260601/vibemix-0.0.1.dmg: accepted
source=Notarized Developer ID
origin=Developer ID Application: Francesco Fasanella (UK7DYFK6F8)
check_macos_dmg_artifact_ready.py: ok=true, mounted_app=/Volumes/vibemix/vibemix.app, copied app smoke library-stats ok
tauri/src-tauri/target/release/bundle/macos/vibemix.app: valid on disk
tauri/src-tauri/target/release/bundle/macos/vibemix.app: satisfies its Designated Requirement
tauri/src-tauri/target/release/bundle/macos/vibemix.app: accepted
source=Notarized Developer ID
```

Fresh reports:

```text
dist/fresh-20260601/verify-report.json: hits=[], scanned=407, status=clean
dist/fresh-20260601/notarytool-detail.json: status=Accepted
```

Packaged launch smoke from the freshly signed app:

```text
VIBEMIX_INPUT_DEVICE='BlackHole 16ch' VIBEMIX_DECK_AUDIO_CHANNELS=auto VIBEMIX_DROP_DEBUG=1 tauri/src-tauri/target/release/bundle/macos/vibemix.app/Contents/MacOS/vibemix
```

Evidence:

```text
sidecar_status: ws_reachable=true, dev_sidecar=false, gemini_key_present=true
process tree: app PID 41324 -> bundled sidecar PID 41328
session_dir: 20260601-074500
ws_observe: 100 ipc.session.snapshot frames
ui.log: rust bridge ws-state {"state":"connected"}
ipc.status.tick: gemini=ok, livekit=ok, midi=1, screen=unavailable
```

Boundary:

- This proves the signed packaged app can launch its bundled sidecar and bring
  the UI/ws transport online.
- It does not prove live DJ acceptance: music meters remained `0`, no MIDI move
  events were captured during the short observe window, and no cited co-host
  speech was produced.
- Directly terminating the app process left the bundled sidecar orphaned; it was
  killed manually.

Normal Quit proof:

```text
open -n tauri/src-tauri/target/release/bundle/macos/vibemix.app
osascript -e 'tell application id "world.bravoh.vibemix" to quit'
```

Result:

```text
sidecar_status after open: ws_reachable=true, dev_sidecar=false
ui.log: rust bridge ws-state {"state":"connected"}
ipc.status.tick: gemini=ok, livekit=ok, midi=1, screen=unavailable
after osascript quit: app process exited, bundled sidecar PID 41742 remained alive as PPID 1
sidecar_status after quit: ws_reachable=true
manual cleanup: kill -KILL 41742, then sidecar_status ws_reachable=false
```

This was a real packaged shutdown blocker. It was reproduced on the signed
artifact above, then fixed in current source and reproved against a later
unsigned local package.

Latest-code unsigned local package proof after the shutdown/boot fixes:

```text
bash scripts/dist/build_macos_local_dmg.sh --smoke library-stats
[macos-app-bundle] OK: /Users/ozai/projects/dj-set-ai/tauri/src-tauri/target/release/bundle/macos/vibemix.app/Contents/Resources/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin
[macos-dmg-artifact] OK: /var/.../vibemix.app
```

Latest unsigned local DMG:

```text
tauri/src-tauri/target/release/bundle/dmg/vibemix_0.0.1_aarch64.dmg
119468447 bytes
mtime 2026-06-01 08:17:10 +0300
sha256 efe673e4b0a36acd7723a650630008b8287df1a835063e556aa0c7d3c051fdfc
```

Latest-code normal packaged launch:

```text
open -n tauri/src-tauri/target/release/bundle/macos/vibemix.app
```

Evidence:

```text
process tree: app PID 53591 -> bundled sidecar PID 53595
listener: vibemix-core PID 53595 owns TCP 127.0.0.1:8765
sidecar_status after open: ws_reachable=true, dev_sidecar=false, gemini_key_present=true
ui.log: rust bridge ws-state {"state":"connected"}
ws_observe: ipc.status.tick livekit=ok gemini=ok midi=1 screen=unavailable
```

Latest-code normal Quit:

```text
osascript -e 'tell application id "world.bravoh.vibemix" to quit'
```

Result:

```text
after osascript quit: no vibemix.app process, no bundled sidecar process
listener after quit: no 127.0.0.1:8765 listener
sidecar_status after quit: ws_reachable=false
```

Important artifact boundary: `dist/fresh-20260601/vibemix-0.0.1.dmg` is now
stale relative to the current source fixes. It remains valid proof that the
signing/notarization flow worked earlier, not the latest-code release artifact.

Latest-code signing/notarization re-run, 2026-06-01:

```text
./scripts/dist/sign_macos.sh --dry-run --output-dir dist/fresh-20260601-latest tauri/src-tauri/target/release/bundle/macos/vibemix.app
[sign_macos] prerequisites OK: app=tauri/src-tauri/target/release/bundle/macos/vibemix.app entitlements=/Users/ozai/projects/dj-set-ai/tauri/src-tauri/entitlements.macos.plist notary_auth=apple-id
[sign_macos] DRY-RUN: stopping after Stage 1; no codesign / notarytool / staple invoked
```

```text
./scripts/dist/sign_macos.sh --output-dir dist/fresh-20260601-latest tauri/src-tauri/target/release/bundle/macos/vibemix.app
[repair_macos_app_sidecar_symlinks] scanned=1 relinked=0 already_linked=36 missing_top_level=0
[sign_macos]   force-signed 167 nested Mach-O binaries (deepest-first)
tauri/src-tauri/target/release/bundle/macos/vibemix.app: valid on disk
tauri/src-tauri/target/release/bundle/macos/vibemix.app: satisfies its Designated Requirement
[sign_macos] fetching notarization log for submission 8975c0c9-053b-4d95-94d0-ffa5e9044162
The staple and validate action worked!
tauri/src-tauri/target/release/bundle/macos/vibemix.app: accepted
source=Notarized Developer ID
[verify_binary] scanned=407 hits=0 report=dist/fresh-20260601-latest/verify-report.json
[sign_macos] DONE: vibemix-0.0.1.dmg notarized + stapled + verified
dist/fresh-20260601-latest/vibemix-0.0.1.dmg
```

Latest signed/notarized DMG:

```text
dist/fresh-20260601-latest/vibemix-0.0.1.dmg 119957189 bytes 2026-06-01 08:32:00 +0300
sha256 a5b56658595bbdae11e5558cdac35f266244192c5b37a51ff6361587e4566b29
```

Signature identity:

```text
Authority=Developer ID Application: Francesco Fasanella (UK7DYFK6F8)
Authority=Developer ID Certification Authority
Authority=Apple Root CA
Timestamp=1 Jun 2026 at 08:29:59
Notarization Ticket=stapled
TeamIdentifier=UK7DYFK6F8
```

Independent latest-DMG checks:

```text
xcrun stapler validate dist/fresh-20260601-latest/vibemix-0.0.1.dmg
spctl -a -vvv -t install dist/fresh-20260601-latest/vibemix-0.0.1.dmg
uv run python scripts/dist/check_macos_dmg_artifact_ready.py dist/fresh-20260601-latest/vibemix-0.0.1.dmg --smoke library-stats --json
codesign --verify --deep --strict --verbose=2 tauri/src-tauri/target/release/bundle/macos/vibemix.app
spctl --assess --type execute --verbose=4 tauri/src-tauri/target/release/bundle/macos/vibemix.app
```

Results:

```text
The validate action worked!
dist/fresh-20260601-latest/vibemix-0.0.1.dmg: accepted
source=Notarized Developer ID
origin=Developer ID Application: Francesco Fasanella (UK7DYFK6F8)
check_macos_dmg_artifact_ready.py: ok=true, copied app smoke library-stats ok
tauri/src-tauri/target/release/bundle/macos/vibemix.app: valid on disk
tauri/src-tauri/target/release/bundle/macos/vibemix.app: satisfies its Designated Requirement
tauri/src-tauri/target/release/bundle/macos/vibemix.app: accepted
source=Notarized Developer ID
dist/fresh-20260601-latest/verify-report.json: hits=[], scanned=407, status=clean
dist/fresh-20260601-latest/notarytool-detail.json: status=Accepted
```

Latest signed-DMG copied-app launch proof:

```text
hdiutil attach dist/fresh-20260601-latest/vibemix-0.0.1.dmg -nobrowse -readonly
cp -R /Volumes/vibemix/vibemix.app /tmp/vibemix-signed-install.Tp4lk7/
open -n /tmp/vibemix-signed-install.Tp4lk7/vibemix.app
```

Evidence:

```text
process tree: app PID 56437 -> bundled sidecar PID 56441
listener: vibemix-core PID 56441 owns TCP 127.0.0.1:8765
sidecar_status after open: ws_reachable=true, dev_sidecar=false, gemini_key_present=true
ui.log: rust bridge ws-state {"state":"connected"}
ws_observe: ipc.status.tick livekit=ok gemini=ok midi=1 screen=unavailable
```

Latest signed-DMG copied-app Quit proof:

```text
osascript -e 'tell application id "world.bravoh.vibemix" to quit'
```

Result:

```text
after osascript quit: no copied vibemix.app process, no bundled sidecar process
listener after quit: no 127.0.0.1:8765 listener
sidecar_status after quit: ws_reachable=false
```

Before any public release claim:

1. Run a clean or quarantine-equivalent launch from the fresh signed DMG.
2. Run the final live acceptance pass with Rekordbox/BlackHole/DDJ-FLX4.
3. Keep launch collateral held until it matches the verified product reality.
