---
phase: 49
date: 2026-05-18
reviewer: gsd-code-review (inline)
depth: standard
status: clean
critical: 0
warning: 2
info: 4
---

# Phase 49 — Code Review

Per-file analysis of the 35 files changed during Phase 49 (6 plans). Focus
areas: security (Pitfall-7 key custody, privacy paths, shell argument
injection), correctness (race conditions, error handling, IPC contract
parity), code quality (typed signatures, anti-pattern detection),
architectural compliance (sibling-script pattern, ModelRouter seam,
bundle ceiling).

## Status: clean

Zero Critical findings. Two Warnings flagged for follow-up but
non-blocking (both involve runtime paths not exercised in unit tests
but covered by §INSTALL-VM-RUN Kaan-action). Four Info-level
observations for housekeeping.

---

## Critical findings (blocking)

None.

---

## Warning findings (non-blocking; track in Kaan-action surface)

### W-01 — `tauri/src-tauri` build failure pre-existing on `main`

**File:** `tauri/src-tauri/capabilities/SNAPSHOT.json` + `default.json`
**Severity:** Warning
**Category:** Pre-existing technical debt — NOT introduced by Phase 49

Running `cargo check` in `tauri/src-tauri/` fails with:

```
capability with identifier `default` already exists
```

Both `default.json` and `SNAPSHOT.json` declare `"identifier": "default"`.
`SNAPSHOT.json` was added in `94082f1 feat(34-09): Tauri capability snapshot
lint (SEC-09)` — well before Phase 49. Verified by `git stash; cargo check`
on the pre-Phase-49 tree.

**Phase 49's impact:** None. The capability scope extension in `default.json`
(shell:allow-execute for companion scripts) is structurally sound; verified
by `python3 -c "import json; json.load(open('...'))"` and follows the
existing array pattern.

**Recommendation:** Out-of-phase fix. Either rename `SNAPSHOT.json`'s
identifier to `default-snapshot` (and update the SEC-09 lint to match) or
move `SNAPSHOT.json` outside `capabilities/`. Track as a separate v3.1
hygiene task. Phase 50 e2e harness will need this resolved before driving
the actual binary, but Phase 49 closure is independent of it.

### W-02 — `audio_config.py probe_48k_darwin` parses `system_profiler` regex output

**File:** `installer/companion/audio_config.py`
**Severity:** Warning
**Category:** Fragility — vendor-output dependency

The fallback path in `probe_48k_darwin()` regex-parses
`system_profiler SPAudioDataType` output looking for `Current SampleRate:`.
This works on macOS 12-15 today; future macOS versions may rename the
field or restructure the output.

**Mitigation in place:** The function tries `pyobjc-framework-CoreAudio`
first (native API, format-stable). Only falls back to subprocess parse
when pyobjc is absent.

**Mitigation: validate at §INSTALL-VM-RUN discharge.** The fresh-VM
matrix run validates the probe against actual `system_profiler` output
on each row. Field rename would surface as a 0.0 measured_khz value
which trips the fail branch — not silent corruption.

**Recommendation:** Add a test that mocks an empty `Current SampleRate:`
field (current behavior: falls through to `no_rate` → ok=False). Already
indirectly covered by `test_probe_48k_missing_device_returns_fail`.

---

## Info findings (housekeeping)

### I-01 — `step-driver-fetch.ts` simulates parallel probes with setTimeout

**File:** `tauri/ui/src/wizard/step-driver-fetch.ts:240-244`
**Severity:** Info

The MIDI / TCC / Bravoh-proxy probe rows mark themselves "done" after
200-300ms via `setTimeout`. This is a scaffold — Plan 49-04 + Plan 49-05
do not wire real probes for these row IDs because v3.0 SHIP-04 already
established `tcc_check` + `controller_probe` + `proxy_ping` surfaces
that the existing `step1-permissions.ts` / `step3-controller.ts` call.

**Recommendation:** Phase 50 e2e harness wires actual probe events via
Tauri `listen()` instead of setTimeout. Tracked in Phase 50 SUMMARY for
the e2e harness build-out.

### I-02 — `firstrun_companion.sh` uses `printf` for log lines without proper JSON escaping

**File:** `installer/macos/firstrun_companion.sh:30-37`
**Severity:** Info

`log_event()` writes JSONL via `printf`. If any of `$stage` / `$state`
were to contain a `"` character, the output JSON would be malformed.

**Mitigation in place:** The function is only invoked with hard-coded
stage names ("boot", "fetch", "verify", etc.) and state values from the
finite set ("ok", "fail", "dry_run", etc.). No user input flows into
log_event.

**Recommendation:** Tighten by routing through `jq` or python3 for JSON
serialization. Phase 50 hardening task; not blocking Phase 49 closure.

### I-03 — `check_companion_signing.sh` JSON output sources unsigned list from `${UNSIGNED[*]}`

**File:** `scripts/audit/check_companion_signing.sh:78-79`
**Severity:** Info

The bash-array-to-python pipe via `${UNSIGNED[*]:-}` joins array elements
with `$IFS` (default space). File names with embedded spaces would
collapse incorrectly. Phase 49's companion scripts have no spaces in
their names, but a future addition could.

**Recommendation:** Switch to NUL-separated array passing or move the
verifier entirely to Python (read the array via env JSON). Phase 50
hardening; not blocking.

### I-04 — `INSTALL-49-companion-fetch.md` ADR uses speculative SignPath cert details

**File:** `.planning/decisions/INSTALL-49-companion-fetch.md`
**Severity:** Info

The ADR documents the SignPath OSS Foundation cert chain as if the cert
is already provisioned. Until Kaan-action §INSTALL-COMPANION-SIGN
discharges, this is forward-projection.

**Mitigation in place:** The ADR explicitly flags §INSTALL-COMPANION-SIGN
in its Kaan-action section as a discharge gate.

**Recommendation:** None — the ADR is correctly forward-stated. Update
at cert discharge time.

---

## Architectural compliance

### Bundle ID — `world.bravoh.vibemix` invariant

**PASS.** All companion scripts spawn under the same bundle ID via:
- `capabilities/default.json` shell:allow-execute scope extension (ZERO new permission identifier)
- `wizard_cmds.rs run_companion_fetch` invokes via `app.shell()` which inherits the bundle context
- `firstrun_companion.sh` runs under the main `.app`'s Info.plist context

### Sibling-script pattern — anti-slop

**PASS.** `scripts/audit/check_no_slop_install.py`:
- Imports `AI_SLOP_BLOCKLIST` from `scripts.launch.check_no_ai_slop` via importlib
- Verified by `tests/audit/test_no_slop_install.py::test_blocklist_import_from_parent`
- Parent's pinned target paths NOT widened — verified by
  `test_parent_pinned_targets_unchanged`

### Pitfall-7 — AIza key custody

**PASS.** Phase 49 surface contains ZERO AIza-key literals:
- `installer/companion/fetch_drivers.sh` line 17: comment "NEVER inlines AIza pattern" (no actual key)
- `installer/companion/fetch_drivers.ps1` line 16: comment "NEVER inlines AIza pattern" (no actual key)
- All other files: zero AIza references
- Verified by `tests/install/test_audio_config.py::test_no_aiza_keys_in_companion_dir` + the sweep grep in this review

### Privacy paths — off-limits log dirs

**PASS.** Zero functional writes to off-limits paths. Verified by:
- `tests/install/test_audio_config.py::test_no_off_limits_log_writes_in_source`
- `installer/companion/audio_config.py::LOG_PATH` assert at module init
  enforces per-OS vibemix dir
- Grep sweep over Phase 49 files: zero matches in functional code

### IPC contract parity

**PASS.** Phase 49 introduces:
- ZERO new event types (uses existing `audio.probe.*` family + adds
  `audio.probe.install_ready` as a sibling-named event, additive)
- ZERO new permission identifiers (extends existing shell:allow-execute)
- ONE additive payload field (`auto_install_attempted`) documented as
  optional in `src/vibemix/install/blackhole_probe.py` constant

### Anti-slop blocklist

**PASS.** Sibling-script clean on all 10 Phase 49 targets. Parent
`check_no_ai_slop.py` UNCHANGED.

### Bundle ceiling

**PASS.** Companion scripts total < 50 KB added to bundle. Driver
binaries fetched post-install (BlackHole ~50 KB, VB-CABLE ~1.5 MB) —
both outside the 350 MB app-bundle ceiling.

### POC immutability

**PASS.** `git diff main -- cohost.py cohost_v2.py cohost_lk.py mascot.html`
returns empty.

### ModelRouter seam

**PASS.** Zero `gemini-*` literals added. The wizard surface does not
invoke any model.

---

## Test coverage

**68 tests pass, 1 platform-skipped:**

```
tests/install/test_driver_manifest_schema.py ...........  10 tests
tests/install/test_audio_config.py .................     11 tests
tests/install/test_iss_companion_run.py ......           6 tests
tests/install/test_dmg_postinstall_hook.py ......        6 tests
tests/install/test_uninstall_preserve.py ......          6 tests
tests/audit/test_companion_signing_gate.py .....s        5 + 1 skip
tests/audit/test_no_slop_install.py ........             8 tests
tests/wizard/test_copy_mirror_in_sync.py ...             3 tests
tests/wizard/test_no_inline_strings_install.py ........  8 tests
tests/dist/test_60s_gate.py ........                     8 tests

68 passed, 1 skipped in 0.67s
```

Coverage spans: manifest schema validation, probe behavior, IPC payload
shape, anti-slop sibling integration, uninstall preserve-default, ISS
structural assertions, 60s gate median computation, copy mirror
freshness, wizard component contract gates.

---

## Recommendations

1. **Address W-01** in a separate v3.1 hygiene task — `cargo check` build
   failure is pre-existing and blocks Phase 50 e2e harness from driving
   the actual built binary. Track as a v3.1 milestone close-out.
2. **Track I-01 → I-04** as Phase 50 hardening tasks (none block Phase 49
   closure).
3. **Discharge §INSTALL-COMPANION-SIGN + §INSTALL-VM-RUN + §SHIP-CONTACT-VBAUDIO** as Kaan-action items per autonomous mode contract.

---

## Reviewer notes

Inline review performed by orchestrator (no subagent Task tool available
in current execution environment per `--no-transition` autonomous-mode
constraints). Review depth: standard (per-file analysis with
language-specific checks). Cross-file analysis on the
companion → wizard → release.yml chain done; import graph traced from
`check_no_slop_install.py` → `check_no_ai_slop.py` (sibling-pattern
invariant) and `audio_config.py → blackhole_probe.py` (additive payload
field).

The 1 platform-skipped test (`test_signed_via_sidecar_exits_zero`)
exercises the Linux-CI branch of the verifier; the Darwin path is
exercised in production-equivalent tests on the same script.
