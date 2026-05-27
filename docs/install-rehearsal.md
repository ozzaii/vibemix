# Fresh-Machine Install Rehearsal

> The pre-launch checklist for proving vibemix installs cleanly on
> machines that don't have any developer state.
> Phase 20 Plan 20 Task 3.

This is the final pre-tag gate. It must pass on **both** a fresh macOS
machine and a fresh Windows machine before `git tag v0.1.0`.

## Why this is non-negotiable

vibemix is a binary-distributed desktop app. The only way to know it
installs cleanly is to install it on a machine that has never seen
Xcode, Visual Studio, MinGW, or any Bravoh-internal config. Anything we
test on our dev machines has too much accumulated state.

## Setup

Pick one of these per platform:

| Platform | Option A (best) | Option B | Option C |
|----------|-----------------|----------|----------|
| macOS    | Borrowed non-dev MacBook (Sequoia, Apple Silicon) | Clean macOS VM via UTM | Wipe + restore on personal Mac |
| Windows  | Borrowed Win 11 laptop | Win 11 VM on Parallels/VMware | Fresh user account on personal Win box |

Avoid Option C if you can — leftover audio drivers, MIDI USB perms,
or installed DJ software pollute results.

## Stopwatch protocol

Start the timer when you click the download link in the GitHub Release.
Stop it after the live co-host speaks once **and** the Library/Viber surface
has completed the required local model setup smoke. Target: under 10 minutes
total (per ROADMAP Phase 20 success criterion 2).

Log each step's duration. We're not optimizing this — we're catching
the step that *secretly* takes 6 minutes and is going to make every
new user bounce.

## macOS rehearsal checklist

| # | Step | Target | Actual | Pass? |
|---|------|--------|--------|-------|
| 1 | Click "Download for macOS" on GitHub Release page | <30s | _____ | ☐ |
| 2 | `.dmg` downloads + double-clicks open | <30s | _____ | ☐ |
| 3 | Drag-to-Applications copy completes | <30s | _____ | ☐ |
| 4 | First launch — Gatekeeper accepts (no "unidentified developer") | <15s | _____ | ☐ |
| 5 | First-run wizard appears | <10s | _____ | ☐ |
| 6 | Required local model setup completes; Library shows `Required models ready` / `CLAP ready` | <5m | _____ | ☐ |
| 7 | Viber setup row is ready, or shows one exact action (`codex login`, BYO key, or proxy token) | <15s | _____ | ☐ |
| 8 | Library search returns real local-library results without Gemini key | <30s | _____ | ☐ |
| 9 | Library chat sends one Viber message; either returns a Codex reply or an actionable setup card, no generic engine error | <30s | _____ | ☐ |
| 10 | Build-a-set creates a grounded set or an actionable setup/no-library state, no crash | <60s | _____ | ☐ |
| 11 | BlackHole auto-install completes (admin password once) | <60s | _____ | ☐ |
| 12 | Audio routing wizard step (record + verify chime in headphones) | <60s | _____ | ☐ |
| 13 | MIDI controller detected (Pioneer DDJ-FLX4 or fallback) | <30s | _____ | ☐ |
| 14 | Mode picker (Hype-Man / Coach) — pick Hype-Man | <10s | _____ | ☐ |
| 15 | Skill picker (Beginner / Intermediate / Pro) — pick Intermediate | <10s | _____ | ☐ |
| 16 | "Start session" → first AI reaction within 30s of music playing | <60s | _____ | ☐ |

**Total target:** under 10 minutes.

## Local packaged first-run smoke

Before a real friend machine is available, run the local unsigned DMG rehearsal
and force the installed app's sidecar to use an empty CLAP cache. The wrapper
forces a fresh sidecar rebuild before packaging, so Python-side setup changes
are not hidden by an older frozen binary:

```bash
bash scripts/dist/build_macos_local_dmg.sh
rm -rf /tmp/vibemix-dmg-fresh-install /tmp/vibemix-empty-clap-cache
mkdir -p /tmp/vibemix-dmg-fresh-install /tmp/vibemix-empty-clap-cache
uv run python scripts/dist/check_macos_dmg_artifact_ready.py \
  tauri/src-tauri/target/release/bundle/dmg/vibemix_0.0.1_aarch64.dmg \
  --install-dir /tmp/vibemix-dmg-fresh-install --smoke none
SIDECAR=/tmp/vibemix-dmg-fresh-install/vibemix.app/Contents/Resources/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin
VIBEMIX_CLAP_ONNX_DIR=/tmp/vibemix-empty-clap-cache \
  "$SIDECAR" library models --install required --json --progress
```

Expected: `required_ready=true`, `install.ok=true`, and all six CLAP files show
`status: "downloaded"` or `status: "skipped"`. Stderr should contain
`VIBEMIX_MODEL_PROGRESS` frames for the model setup row. Follow with a unique
`library search ... --json`; `cache_hit=false` proves the freshly installed text
model loaded.

## Windows rehearsal checklist

| # | Step | Target | Actual | Pass? |
|---|------|--------|--------|-------|
| 1 | Click "Download for Windows" on GitHub Release page | <30s | _____ | ☐ |
| 2 | `.exe` installer downloads | <30s | _____ | ☐ |
| 3 | SmartScreen dialog — `More info` → `Run anyway` | <15s | _____ | ☐ |
| 4 | Inno installer launches, accepts defaults | <60s | _____ | ☐ |
| 5 | Per-machine install completes (admin elevation) | <60s | _____ | ☐ |
| 6 | VC++ runtime check passes (auto-installs if needed) | <60s | _____ | ☐ |
| 7 | First launch — wizard appears | <15s | _____ | ☐ |
| 8 | Required local model setup completes; Library shows `Required models ready` / `CLAP ready` | <5m | _____ | ☐ |
| 9 | Viber setup row is ready, or shows one exact action (`codex login`, BYO key, or proxy token) | <15s | _____ | ☐ |
| 10 | Library search returns real local-library results without Gemini key | <30s | _____ | ☐ |
| 11 | Library chat sends one Viber message; either returns a Codex reply or an actionable setup card, no generic engine error | <30s | _____ | ☐ |
| 12 | Build-a-set creates a grounded set or an actionable setup/no-library state, no crash | <60s | _____ | ☐ |
| 13 | WASAPI loopback configured automatically | <30s | _____ | ☐ |
| 14 | MIDI device detected | <30s | _____ | ☐ |
| 15 | Mode + skill picker | <20s | _____ | ☐ |
| 16 | First AI reaction within 30s of music | <60s | _____ | ☐ |

**Total target:** under 10 minutes.

## Failure-class taxonomy

If a step fails, label the failure with one of these classes so we
know where to fix:

| Class | Meaning | Fix owner |
|-------|---------|-----------|
| `signing` | OS refused the binary (Gatekeeper / SmartScreen) | Phase 18 sign chain |
| `notarization` | macOS notarization stapler missing | Phase 18 sign chain |
| `dep-install` | BlackHole / VC++ / runtime missing or stuck | Phase 7 (Win) / Phase 8 (Mac) install flow |
| `model-setup` | Required CLAP model install/checksum fails or is not surfaced | Library model installer |
| `viber-setup` | Codex/BYO-key/proxy setup is missing, vague, or crashes the Library window | Library agent setup UX |
| `library-agent` | Search/chat/build-set cannot return a result or actionable no-op state | Viber/Codex bridge |
| `audio-route` | Wizard can't detect or set audio routing | Phase 11 wizard |
| `midi-detect` | Controller doesn't show up | Phase 9 MIDI library |
| `proxy-auth` | First reaction fails because install-UUID JWT not minted | Phase 5 FastAPI proxy |
| `slop-on-first-reaction` | AI says something generic / wrong on the very first reply | Phase 10 anti-slop + Phase 16 ear-test |

## Where to log results

Append a section to `.planning/phases/20-day-zero-operations/20-VERIFICATION.md`:

```
## Rehearsal log

### macOS — <date>, <machine description>
| Step | Actual | Pass |
| 1    | 14s    | ☑    |
| ...  | ...    | ...  |
Total: M:SS
Failures: <list of classes>

### Windows — <date>, <machine description>
...
```

## Pass criterion

Both platforms: total under 10 minutes AND zero failure-class entries OR
all failure classes are documented as "wontfix for v0.1.0" with rationale
in Phase 20 verification.

If either fails, hold the v0.1.0 tag and open a follow-up plan against
the failing phase.
