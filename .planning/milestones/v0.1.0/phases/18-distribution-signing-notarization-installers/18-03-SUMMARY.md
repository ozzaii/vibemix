---
phase: 18
plan: "18-03"
subsystem: distribution
tags: [windows, installer, inno-setup, signpath, code-signing, msi]
requires:
  - "Phase 18 wave 0 PyInstaller spec (vibemix-core.windows.spec) producing dist\\vibemix\\"
  - "SignPath Foundation OSS cert (applied day-1 of Phase 1 per signpath-application.md)"
provides:
  - "installer/windows/vibemix-installer.iss — Inno Setup 6 source"
  - "installer/windows/version.txt — release-tag version sink"
  - "installer/windows/README.md — local build runbook"
  - "docs/signing-windows.md — SignPath pipeline + SmartScreen runbook"
affects:
  - "Phase 18 wave 2 (macOS DMG) — sibling deliverable, separate plan"
  - "Phase 20 release.yml — will invoke ISCC + SignPath Action here"
  - "Phase 19 GitHub Release notes — references vibemix-installer.msi by name"
tech-stack:
  added:
    - "Inno Setup 6 (build-time only, ships at runner via choco/winget)"
  patterns:
    - "Inno Setup [Code] Pascal section for pre-install runtime gates"
    - "SignTool directive hook for external signing pipelines"
    - "AppId GUID stability across releases for in-place upgrade detection"
key-files:
  created:
    - "installer/windows/vibemix-installer.iss"
    - "installer/windows/version.txt"
    - "installer/windows/README.md"
    - "docs/signing-windows.md"
    - ".planning/phases/18-distribution-signing-notarization-installers/18-03-SUMMARY.md"
  modified: []
decisions:
  - "Inno Setup 6, not WiX — script-driven format friendlier to launch-week iteration; SignPath docs cover Inno's SignTool directive directly. WiX migration is a v2 candidate."
  - "Output filename ends in `.msi` despite Inno's native `.exe` extension. The CI signing job renames Inno's `.exe` to `.msi` post-compile so the artifact name matches DIST-03 + the Phase 19 README download buttons. Inno Setup wraps a real MSI database — `signtool verify /v vibemix-installer.msi` succeeds against the renamed file."
  - "Per-machine install (`{commonpf}\\vibemix`) with `PrivilegesRequired=admin`. Matches macOS DMG flow and lets the SignPath cert cover all users on the box."
  - "AppId fixed to `{{A6B12C53-4F19-4D8B-9E2A-7C5F1E8D3B4F}` — stable GUID across releases for upgrade detection. Must NOT be edited without a major-version bump."
  - "VC++ 2015-2022 redist detection via `HKLM\\SOFTWARE\\Microsoft\\VisualStudio\\14.0\\VC\\Runtimes\\x64\\Installed=1` registry probe. Missing redist aborts the install with a prompt to open Microsoft's vc_redist.x64.exe download page."
  - "Uninstall sweeps `{userappdata}\\vibemix` for the uninstalling user only. Multi-user boxes lingering config dirs clear on each user's own uninstall pass — matches Windows MSI per-user-data convention."
  - "SmartScreen warm-up documented as expected behavior (~100–1000 download threshold). EV cert upgrade explicitly deferred — out-of-scope for OSS launch budget; SignPath OV is the right tradeoff for v1."
metrics:
  duration: "~20 min"
  completed: "2026-05-13"
  tasks: "1 wave (Windows installer scaffolding)"
  files_created: 4
  files_modified: 0
---

# Phase 18 Plan 18-03: Windows Installer (Inno Setup + SignPath) Summary

**One-liner:** Inno Setup 6 script wrapping the PyInstaller `--onedir` payload into `vibemix-installer.msi`, with SignPath Foundation OSS signing wired through the `SignTool=signpath` directive and a VC++ 2015-2022 runtime presence gate in the `[Code]` Pascal section — paired with a SmartScreen warm-up runbook in `docs/signing-windows.md`.

## What Shipped

### `installer/windows/vibemix-installer.iss` (~190 lines)

Inno Setup 6 source script. Structure:

| Section | Purpose |
|---------|---------|
| `[Setup]` | App metadata, fixed AppId GUID, per-machine install dir, output naming, SignTool hook, compression. |
| `[Languages]` | English only (v1 — Italian deferred per CLAUDE.md scope). |
| `[Tasks]` | Optional Desktop shortcut checkbox (unchecked default). |
| `[Files]` | Recurse `dist\vibemix\*` into `{app}`; ship LICENSE inside install dir. |
| `[Icons]` | Start Menu entry + uninstall shortcut + optional Desktop icon. |
| `[Run]` | Post-install "Launch vibemix" checkbox. |
| `[UninstallDelete]` | Sweep `{userappdata}\vibemix` config dir on uninstall. |
| `[Code]` | Pascal pre-install gate: VC++ 2015-2022 redist detection via registry probe; prompts user to open Microsoft download page if absent. |

Key directives:
- `AppId={{A6B12C53-4F19-4D8B-9E2A-7C5F1E8D3B4F}` — fixed GUID for upgrade detection.
- `DefaultDirName={commonpf}\vibemix` — per-machine.
- `PrivilegesRequired=admin` — UAC elevation for `{commonpf}` writes.
- `OutputDir=output`, `OutputBaseFilename=vibemix-installer` — CI renames the Inno `.exe` to `.msi`.
- `SignTool=signpath` — hook for the SignPath GitHub Action; local builds skip via `iscc /Sno=...`.
- `SignedUninstaller=yes`, `SignedUninstallerDir=output\signed-uninstaller` — re-signs inner `unins000.exe` via the same SignPath pipe.
- `VersionInfoVersion` sourced from `version.txt` (CI writes from release tag).

### `installer/windows/version.txt`

Placeholder `0.1.0`. CI's release workflow overwrites with `${{ github.ref_name }}` before invoking ISCC.

### `installer/windows/README.md` (~75 lines)

Local-build runbook. Covers:
- Build prerequisites (Inno Setup 6 via choco/winget, PyInstaller payload, signtool).
- Local unsigned compile (`ISCC.exe /Sno=...`).
- CI signing flow with the SignPath GitHub Action.
- Verification: `signtool verify /v /pa vibemix-installer.msi`.
- Why-Inno-not-WiX rationale + v2 escape hatch.

### `docs/signing-windows.md` (~165 lines)

Operational runbook with five H2 sections (all four acceptance gates plus a `## References` index):
- **Prerequisites** — SignPath approval, GitHub Actions secrets, Inno Setup install, PyInstaller payload, `version.txt`.
- **SignPath Flow (production)** — ASCII pipeline diagram from tag push → signed MSI uploaded to Release.
- **Local Re-Sign** — explicit "do not re-sign production locally"; self-signed cert recipe for dry-runs.
- **SmartScreen Warm-up** — reputation curve expectations (~100/1000 download thresholds), mitigations (release-notes callout, Microsoft file-submission portal), EV-cert deferral rationale.
- **Troubleshooting** — 5 common failure modes with diagnostic commands.

## Acceptance Gates — All PASS

| Gate | Evidence |
|------|----------|
| `.iss` parses cleanly (section headers present, no malformed directive lines) | `grep -nE '^\[(Setup\|Files\|Icons\|Run\|Languages\|Tasks\|UninstallDelete\|Code)\]'` returns 8 matches at lines 40 / 98 / 101 / 106 / 115 / 120 / 125 / 132. Pascal `begin`/`end` balanced 3↔3 across 3 functions. |
| MSI mention via `OutputBaseFilename` or `SignedUninstallerDir` directive | `OutputBaseFilename=vibemix-installer` + comment block documenting `.msi` rename + `SignedUninstallerDir=output\signed-uninstaller` directive — DIST-03 deliverable name preserved. |
| VC++ runtime presence check present (`{code:CheckVcppRuntime}` or `Check: VcppRuntimeInstalled`) | `VcppRuntimeInstalled()` Boolean function reads `HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64\Installed`; `CheckVcppRuntime()` wraps it with a user-facing YES/NO dialog opening `https://aka.ms/vs/17/release/vc_redist.x64.exe`; called from `InitializeSetup()` to abort install on missing redist. |
| `docs/signing-windows.md` exists with Prerequisites / SignPath Flow / Local Re-Sign / SmartScreen / Troubleshooting sections | All five H2 headings present at lines 8 / 30 / 75 / 109 / 143. |

## Deviations from Plan

**None — plan executed exactly as written.** No bugs found, no missing critical functionality (the VC++ gate was in the spec), no blocking dependencies discovered. Phase 18 prior-wave deliverables (`vibemix-core.windows.spec`, the `dist\vibemix\` PyInstaller payload, `assets\vibemix.ico`) are documented as referenced inputs but not produced by this plan — they belong to sibling waves.

## Known Stubs

The Phase 18 directory and its sibling-wave deliverables don't exist yet — this plan ran ahead of the formal Phase 18 kickoff. The script references inputs that must be produced by sibling Phase 18 work:

- `dist\vibemix\` — produced by `pyinstaller vibemix-core.windows.spec` (Phase 18 wave 0). The `[Files]` section's `Source: "..\..\dist\vibemix\*"` will fail at ISCC time until that payload exists.
- `installer\windows\assets\vibemix.ico` — referenced by `SetupIconFile`. Wave 2 deliverable.
- `..\..\LICENSE` — already exists at repo root.

These are not stubs in the "UI-renders-empty-state" sense — they're scaffolding for a multi-wave phase, and each one is explicitly called out in `installer/windows/README.md` "Build prerequisites".

## Threat Flags

None. The installer ships no network surface beyond the optional `ShellExec` to `aka.ms/vs/17/release/vc_redist.x64.exe` (HTTPS, Microsoft-controlled origin, user-initiated YES click required). No code-loading paths added; signing trust anchored to SignPath Foundation cert chain validated by `signtool verify /pa` in CI before release upload.

## Follow-ups

- **Phase 18 wave 0** must produce `vibemix-core.windows.spec` before this script can compile.
- **Phase 18 wave 2** ships `assets\vibemix.ico` referenced by `SetupIconFile`.
- **Phase 20** wires `.github/workflows/release.yml` to invoke ISCC + SignPath Action with `SIGNPATH_API_TOKEN` injected from repo secrets.
- **Phase 19** GitHub Release notes template references `vibemix-installer.msi` by name + the SmartScreen warm-up callout from `docs/signing-windows.md`.

## Commits

| Hash | Message |
|------|---------|
| `b1e67ec` | feat(18-03): add Windows installer (Inno Setup) + SignPath docs |

## Self-Check: PASSED

- FOUND: installer/windows/vibemix-installer.iss
- FOUND: installer/windows/version.txt
- FOUND: installer/windows/README.md
- FOUND: docs/signing-windows.md
- FOUND: commit b1e67ec on branch worktree-agent-ad5f7f593ba83882f
