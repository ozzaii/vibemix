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
Stop it when vibemix plays its first AI reaction at you. Target: under
10 minutes total (per ROADMAP Phase 20 success criterion 2).

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
| 6 | BlackHole auto-install completes (admin password once) | <60s | _____ | ☐ |
| 7 | Audio routing wizard step (record + verify chime in headphones) | <60s | _____ | ☐ |
| 8 | MIDI controller detected (Pioneer DDJ-FLX4 or fallback) | <30s | _____ | ☐ |
| 9 | Mode picker (Hype-Man / Coach) — pick Hype-Man | <10s | _____ | ☐ |
| 10 | Skill picker (Beginner / Intermediate / Pro) — pick Intermediate | <10s | _____ | ☐ |
| 11 | "Start session" → first AI reaction within 30s of music playing | <60s | _____ | ☐ |

**Total target:** under 10 minutes.

## Windows rehearsal checklist

| # | Step | Target | Actual | Pass? |
|---|------|--------|--------|-------|
| 1 | Click "Download for Windows" on GitHub Release page | <30s | _____ | ☐ |
| 2 | `.msi` downloads | <30s | _____ | ☐ |
| 3 | SmartScreen dialog — `More info` → `Run anyway` | <15s | _____ | ☐ |
| 4 | MSI installer launches, accepts defaults | <60s | _____ | ☐ |
| 5 | Per-machine install completes (admin elevation) | <60s | _____ | ☐ |
| 6 | VC++ runtime check passes (auto-installs if needed) | <60s | _____ | ☐ |
| 7 | First launch — wizard appears | <15s | _____ | ☐ |
| 8 | WASAPI loopback configured automatically | <30s | _____ | ☐ |
| 9 | MIDI device detected | <30s | _____ | ☐ |
| 10 | Mode + skill picker | <20s | _____ | ☐ |
| 11 | First AI reaction within 30s of music | <60s | _____ | ☐ |

**Total target:** under 10 minutes.

## Failure-class taxonomy

If a step fails, label the failure with one of these classes so we
know where to fix:

| Class | Meaning | Fix owner |
|-------|---------|-----------|
| `signing` | OS refused the binary (Gatekeeper / SmartScreen) | Phase 18 sign chain |
| `notarization` | macOS notarization stapler missing | Phase 18 sign chain |
| `dep-install` | BlackHole / VC++ / runtime missing or stuck | Phase 7 (Win) / Phase 8 (Mac) install flow |
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
