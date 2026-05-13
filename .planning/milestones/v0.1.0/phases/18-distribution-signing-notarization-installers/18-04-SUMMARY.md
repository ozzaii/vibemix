---
phase: 18-distribution-signing-notarization-installers
plan: 04
subsystem: dist
tags: [dist, updater, tauri, opt-out, manifest, minisign]
wave: 2
requirements:
  - DIST-06
dependency_graph:
  requires:
    - 11-tauri-shell (tauri-plugin-updater 2.10 pinned in Cargo.toml, `updater:default` capability granted)
    - 12-settings-state (config.json schema preservation via _PHASE12_FIELDS round-trip)
    - 18-01-binary-attack-verification
    - 18-02-macos-signing-bench
    - 18-03-windows-installer-inno-setup
  provides:
    - "Live signed-manifest updater endpoint wired to api.altidus.world/vibemix/updates"
    - "update_check_on_launch default-ON opt-out plumbed via tauri-plugin-store"
    - "TAURI_UPDATER_PLACEHOLDER sentinel for Plan 18-05's release.yml grep-gate"
  affects:
    - 18-05-release-workflow (consumes placeholder sentinel + GitHub secrets contract)
    - 19-polish (Settings UI surface for update_check_on_launch toggle — deferred)
    - "Bravoh ops (out-of-scope): api.altidus.world /vibemix/updates/{target}/{arch}/{version} endpoint"
tech_stack:
  added: []
  patterns:
    - "tauri::async_runtime::spawn fire-and-forget (mirrors sidecar/ws_client boot pattern)"
    - "Default-ON invariant for security flags (key absent / read error / non-bool all return true)"
    - "Top-level config.json key owned by Rust, preserved by Python sidecar round-trip"
key_files:
  created:
    - tauri/src-tauri/src/updater.rs
    - tauri/src-tauri/keys/.gitkeep
    - tauri/src-tauri/keys/README.md
    - docs/updater.md
    - .planning/phases/18-distribution-signing-notarization-installers/18-04-SUMMARY.md
  modified:
    - tauri/src-tauri/tauri.conf.json5
    - tauri/src-tauri/src/main.rs
    - tauri/src-tauri/src/config.rs
    - .gitignore
decisions:
  - "Pubkey placeholder sentinel: base64('untrusted comment: TAURI_UPDATER_PLACEHOLDER') — syntactically valid base64 that is NEVER a real minisign pubkey (real keys are 56 bytes after the comment block). Plan 18-05 grep-gates the literal `TAURI_UPDATER_PLACEHOLDER` substring."
  - "No new IPC schema field for update_check_on_launch — Rust owns the key directly via tauri-plugin-store; Python sidecar preserves unknown top-level keys per config_store.py header (avoids codegen rerun + drift-gate regeneration for a single bool)."
  - "Default-ON invariant: check_on_launch_enabled returns true on absent / read-error / non-bool. Only an explicit `false` disables checking — a corrupt config must not silently suppress security updates."
  - "Boot-time updater spawn is the LOWEST-priority boot task — runs AFTER sidecar, ws_client, hotkey, mascot, tray. Failures log at WARN but NEVER bail setup."
metrics:
  duration_minutes: 13
  completed_date: 2026-05-13
  tasks_total: 3
  tasks_completed: 3
  files_total: 9
---

# Phase 18 Plan 18-04: Tauri Auto-Updater Wiring — Summary

Lifts the Phase 11 W2 updater STUB to a fully-wired signed-manifest
auto-updater. `tauri.conf.json5` flips from `active:false` to a live
config pointing at `api.altidus.world/vibemix/updates/{{target}}/{{arch}}/{{current_version}}`,
ships a placeholder pubkey gated by Plan 18-05's release.yml, and
plumbs a Rust-side `update_check_on_launch` default-ON opt-out without
adding a new IPC schema field. The Python sidecar is untouched —
`_PHASE12_FIELDS` round-trip preserves the Rust-owned top-level key.

## What shipped

### Task 1 — tauri.conf.json5 live updater + keys/README + .gitignore (`e030cf0`)
- `tauri.conf.json5` `plugins.updater` stanza: STUB (`active:false`,
  `endpoints:[]`, `pubkey:""`, `dialog:false`) → live config:
  - `active: true`
  - `endpoints: ["https://api.altidus.world/vibemix/updates/{{target}}/{{arch}}/{{current_version}}"]`
  - `pubkey: "dW50cnVzdGVkIGNvbW1lbnQ6IFRBVVJJX1VQREFURVJfUExBQ0VIT0xERVI="`
    (base64 of `untrusted comment: TAURI_UPDATER_PLACEHOLDER` — sentinel
    for Plan 18-05's release.yml grep-gate; Kaan replaces with real
    minisign pubkey pre-v0.1.0 per `tauri/src-tauri/keys/README.md`)
  - `dialog: true`
- `tauri/src-tauri/keys/.gitkeep` + `README.md` (79 lines): one-time
  key-generation playbook — `npx @tauri-apps/cli signer generate -w
  ~/.tauri/vibemix_updater.key`, GitHub secret names
  (`TAURI_UPDATER_PRIVATE_KEY` + `TAURI_UPDATER_KEY_PASSWORD`), key
  rotation procedure, minisign rationale.
- `.gitignore` appended with `tauri/src-tauri/keys/*.key` +
  `tauri/src-tauri/keys/*.key.pub` (defense-in-depth — keys live OUTSIDE
  the repo at `~/.tauri/`, but if a keypair is ever accidentally
  dropped into the directory, git refuses to track it).
- Validation: JSON5 parses cleanly via Python comment-stripper.
  `git diff --stat`: exactly 2 modified files (tauri.conf.json5,
  .gitignore) + 2 new files (keys/.gitkeep, keys/README.md).

### Task 2 — Rust updater.rs module + main.rs hook + config.rs key (`f2b8824`)
- `tauri/src-tauri/src/updater.rs` (159 lines):
  - `pub fn check_on_launch_enabled(app: &AppHandle) -> bool` — reads
    `update_check_on_launch` from `tauri-plugin-store`'s `config.json`.
    Default-ON invariant: returns `true` on key absent (first launch),
    store read error (corrupt config), or non-bool value. Only an
    explicit `false` disables the check.
  - `pub async fn run_update_check_if_enabled(app: AppHandle)` — boot-time
    fire-and-forget. Honours opt-out; on enabled, calls
    `app.updater()?.check().await`. On `Some(update)`: dispatches
    `download_and_install` with no-op progress callbacks (the plugin's
    `dialog: true` config owns the UX). On `Ok(None)`: logs "no update
    available". On `Err`: logs WARN (common in dev / offline / manifest
    server not yet deployed — see `docs/updater.md`). **NEVER bails boot.**
- `tauri/src-tauri/src/main.rs`:
  - `mod updater;` declaration in lexical order alongside `mod tray;`.
  - Boot-time spawn via `tauri::async_runtime::spawn` AFTER
    `tray::install_tray_state_listener(&app_handle)` — lowest-priority
    boot task (sidecar + ws_client + hotkey + mascot + tray come up
    first; updater is fire-and-forget on the side).
- `tauri/src-tauri/src/config.rs`:
  - `pub const KEY_UPDATE_CHECK_ON_LAUNCH: &str = "update_check_on_launch"`
    — single source of truth for the config.json top-level key. No new
    `pub fn read_*`/`write_*` wrappers (future Settings UI uses
    `tauri-plugin-store`'s built-in `set` command via the existing
    `store:default` capability — no new app command needed).
- `cargo check` exits 0 (only pre-existing `permissions.rs` deprecation
  warnings remain — scope-boundary, not introduced by this plan).
- **Zero new dependencies**: `tauri-plugin-updater 2.10` + `tauri-plugin-store 2.4`
  were already pinned in `Cargo.toml` from Phase 11 W2; `updater:default`
  + `store:default` permissions already granted in `capabilities/default.json`.

### Task 3 — docs/updater.md manifest contract + rollback recipe (`3bb4387`)
- `docs/updater.md` (196 lines): canonical end-user + Kaan reference.
- Sections:
  1. **How it works (user perspective)** — boot-time fire timing,
     `204`/`200` response handling, dialog UX, fail-silent rule.
  2. **Opt-out** — config.json path on macOS + Windows, JSON snippet,
     Phase 19 Settings UI deferral note.
  3. **Manifest Contract** — GET endpoint shape (target / arch /
     current_version path params), `204 No Content` vs `200 OK +
     signed JSON envelope` (version / url / signature / notes /
     pub_date), signature verification semantics.
  4. **Key Setup** — summary referencing `tauri/src-tauri/keys/README.md`
     for the full playbook.
  5. **Publishing a release (Plan 18-05)** — release.yml flow
     (build → sign → notarize → upload → POST manifest), Bravoh-proxy
     endpoint hand-off boundary called out (not implemented in Phase 18).
  6. **Rollback** — `gh release delete v0.1.4 --yes`, tag deletion +
     remote tag deletion, manifest republish on api.altidus.world
     (Bravoh ops procedure). Full automation v2-deferred per
     18-CONTEXT §deferred.
  7. **Why minisign?** — Ed25519 rationale, 32-byte pubkey / 64-byte sig.
  8. **Day-1 reputation** — SmartScreen/Gatekeeper warm-up
     cross-reference to signing-windows.md.
  9. **Troubleshooting** — table of symptom → cause → fix.
  10. **Related Docs** — links to signing-macos.md, signing-windows.md,
      keys/README.md, updater.rs, tauri.conf.json5, release.yml.

## Cross-plan hand-offs

| Hand-off target | What this plan delivered | What they need to do |
|----|----|----|
| **Plan 18-05 (release.yml)** | `TAURI_UPDATER_PLACEHOLDER` sentinel + GitHub secret names (`TAURI_UPDATER_PRIVATE_KEY`, `TAURI_UPDATER_KEY_PASSWORD`) | Grep-gate the sentinel; refuse to build any tagged release while present. Sign manifests with the secret keypair. |
| **Bravoh ops (out-of-scope)** | Manifest endpoint contract in `docs/updater.md` §"Manifest Contract" | Implement `/vibemix/updates/{target}/{arch}/{current_version}` on `api.altidus.world` (Postgres-backed cache, 204/200 logic, manifest POST endpoint for release.yml). |
| **Phase 19 polish** | `update_check_on_launch` config-store key + `KEY_UPDATE_CHECK_ON_LAUNCH` constant in `config.rs` | One Settings drawer row (PerformanceGroup or new UpdateGroup) that calls `tauri-plugin-store`'s `set` command via existing `store:default` capability. |
| **Kaan (pre-v0.1.0 prep)** | Key-generation playbook in `tauri/src-tauri/keys/README.md` | Run `npx @tauri-apps/cli signer generate -w ~/.tauri/vibemix_updater.key`, paste the .key.pub base64 into `tauri.conf.json5`, set GitHub secrets. |
| **Phase 20 (fresh-machine rehearsal)** | All shipped here is in place | End-to-end rehearsal: fresh M-series Mac + fresh Win 11 → install signed installer → tag v0.1.1 → confirm updater prompt fires → confirm signature verification passes. |

## Threat surface

The plan's `<threat_model>` block ships unchanged from the spec:

- **T-18-09 (Tampering, manifest server compromise)** — mitigated by
  minisign signature verification against the locally-baked pubkey
  (independent of TLS).
- **T-18-10 (Tampering, placeholder remains in v0.1.0 build)** —
  mitigated by Plan 18-05's grep-gate on the `TAURI_UPDATER_PLACEHOLDER`
  sentinel.
- **T-18-11 (Information Disclosure, private key in repo)** — mitigated
  by `.gitignore` + procedure-driven OUTSIDE-the-repo storage + GitHub
  Actions secret-masking.
- **T-18-12 (DoS, manifest endpoint unreachable)** — accepted: single
  fail-silent check per launch, no retry storm.
- **T-18-13 (Repudiation, bad release pushed to all users)** —
  mitigated (manual) via the rollback recipe in `docs/updater.md`.

## Verification

| Gate | Result |
|------|--------|
| `tauri.conf.json5` JSON5 parses cleanly | ✅ |
| `plugins.updater.active === true` | ✅ |
| `plugins.updater.endpoints[0]` matches `api.altidus.world/vibemix/updates` | ✅ |
| `plugins.updater.pubkey` non-empty + matches `TAURI_UPDATER_PLACEHOLDER` sentinel | ✅ |
| `plugins.updater.dialog === true` | ✅ |
| `tauri/src-tauri/keys/.gitkeep` exists | ✅ |
| `tauri/src-tauri/keys/README.md` ≥25 lines (got 79) | ✅ |
| `keys/README.md` contains `npx @tauri-apps/cli signer generate` | ✅ |
| `keys/README.md` contains `TAURI_UPDATER_PRIVATE_KEY` + `TAURI_UPDATER_KEY_PASSWORD` | ✅ |
| `.gitignore` blocks `tauri/src-tauri/keys/*.key` + `*.key.pub` | ✅ |
| `tauri/src-tauri/src/updater.rs` exists, ≥80 lines (got 159) | ✅ |
| `updater.rs` defines `pub fn check_on_launch_enabled` + `pub async fn run_update_check_if_enabled` | ✅ |
| `updater.rs` uses `UpdaterExt` + `tauri_plugin_store::StoreExt` | ✅ |
| `main.rs` contains `mod updater;` + `updater::run_update_check_if_enabled` spawn | ✅ |
| `config.rs` contains `pub const KEY_UPDATE_CHECK_ON_LAUNCH` | ✅ |
| `cargo check` exits 0 (only pre-existing permissions.rs warnings) | ✅ |
| No new entries in `Cargo.toml` `[dependencies]` | ✅ |
| No new entries in `capabilities/default.json` | ✅ |
| `docs/updater.md` ≥100 lines (got 196) | ✅ |
| `docs/updater.md` contains endpoint URL + manifest shape + rollback + opt-out + keys cross-ref | ✅ |
| POC files (cohost*.py, mascot.html, mocks/) diff-untouched | ✅ |
| pytest `tests/runtime/` + `tests/ui_bus/` green (171 passed) | ✅ |

## Deviations from Plan

**None — plan executed exactly as written.**

The plan's `requirements: [DIST-06]` field references a phase-level
requirement covered fully by this plan. The plan's executor context
suggested adding `update_check_on_launch` to `ConfigStore`
(`src/vibemix/runtime/config_store.py`) — the **plan body itself**
explicitly rejected that approach (lines 72-81: "The plan does NOT add
a new IPC settings field… instead, the Rust shell reads/writes
`update_check_on_launch` DIRECTLY via `tauri-plugin-store` to the same
`config.json` file the Python sidecar reads"). Plan precedence applies
— Python sidecar `_PHASE12_FIELDS` round-trip already preserves the
Rust-owned top-level key per `config_store.py` header lines 14-22. No
Python changes were made and the existing test suite (171 tests)
passes without modification, confirming the round-trip behavior is
intact.

## Known Stubs

**None** — the `TAURI_UPDATER_PLACEHOLDER` pubkey is intentional and
documented as the pre-v0.1.0 prep handoff (per the executor context
explicit decision: "Plan 18-05 release.yml gates this placeholder;
Kaan replaces with real signer pubkey pre-v0.1.0 ship"). The Bravoh-side
`api.altidus.world/vibemix/updates/*` endpoint is also intentionally
out-of-scope per `18-CONTEXT.md` §domain "What CAN be shipped
autonomously" — the updater silently no-ops on 404 until the proxy
ships.

## Open Follow-ups (parked, not blockers)

1. **Phase 19 polish** — Settings drawer row for `update_check_on_launch`
   toggle (one row in `PerformanceGroup` or a new `UpdateGroup`); uses
   the existing `store:default` capability.
2. **Phase 20 fresh-machine rehearsal** — end-to-end install + updater
   prompt verification on a fresh M-series Mac + fresh Win 11.
3. **Bravoh ops hand-off** — implement
   `/vibemix/updates/{target}/{arch}/{current_version}` on
   `api.altidus.world` (separate Bravoh-side deliverable).
4. **Pre-v0.1.0 key generation** — Kaan runs the `tauri signer generate`
   procedure documented in `tauri/src-tauri/keys/README.md`, replaces
   the placeholder pubkey in `tauri.conf.json5`, sets GitHub secrets.

## Commits

- `e030cf0` — feat(18-04): Task 1 — live updater stanza + keys/README + .gitignore
- `f2b8824` — feat(18-04): Task 2 — updater.rs boot-time fire-and-forget + config.rs key
- `3bb4387` — docs(18-04): Task 3 — docs/updater.md manifest contract + rollback recipe

## Self-Check: PASSED
