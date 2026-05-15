# Phase 34: Open-Source Security Pass — Research

**Date:** 2026-05-15
**Mode:** Auto (gsd-autonomous fully)

## Existing State (Codebase Touchpoints)

### CI scaffold (`.github/workflows/`)
- `eval.yml` — VCR-cassette hallucination gate (Phase 27).
- `release.yml` — 5-stage matrix (build / sign / package / verify / publish) with mock-signing fallback (Phase 18). Already has `scripts/dist/verify_binary.py` AIza pattern leak gate.
- `issue-triage.yml` — Phase 26 triage.
- README.md inside workflows dir documents secret inventory.

Phase 34 adds 6 fresh workflow files; coexist with existing 3.

### Tauri (`tauri/src-tauri/`)
- Single capability file `capabilities/default.json` (huge inline description string), windows = main+mascot+overlay-*+debrief.
- Permissions enumerated: core:default..updater:default, global-shortcut, shell:allow-execute (sidecar args validator extended in Phase 29), shell:allow-open (3 URLs + recordings paths), fs:allow-read-text-file (logs only).
- `Cargo.toml` Tauri 2.11, plugins shell/store/fs/positioner/updater/process/global-shortcut.

### Runtime (`src/vibemix/runtime/`)
- Existing: cancel, coach, config_store, diag, parent_watchdog, recordings_index, session_loop, settings, ttft, wizard, ws_bus.
- `config_store.py` is the canonical state.json read/write surface (atomic write via os.replace). Phase 34 adds `telemetry_consent: bool` field to its dataclass + load/save defaults — preserves unknown keys per the documented superset contract.
- New module `sec_check.py` is the Phase 34 addition.

### Wizard (Vanilla TS, `tauri/ui/src/wizard/`)
- Existing pattern: router.ts state-machine + per-step `renderStepXxx.ts`. Phase 32 added `step-profile-consent.ts` with default-OFF toggle pattern — Phase 34 follows that exact pattern for telemetry consent.
- Steps currently: intro → permissions → audio → controller → profile-consent → smoke-test → done. Phase 34 inserts `telemetry-consent` between profile-consent and smoke-test.

### Existing security adjacencies
- `scripts/dist/verify_binary.py` (Phase 18) — AIza scan over built bundle. We extend the surface to PR/push secret scanning via gitleaks.
- `scripts/scan_aiza_keys.py` (Phase 27) — runtime recordings/eval corpus AIza scanner. Provides AIza-fixture pattern shape for `.secrets.baseline` allowlist.
- Wave-0 sign-checklist test `tests/test_signpath_checklist.py` already exists — Phase 34 verifier surface complements but does not replace.

### Pre-commit
- No `.pre-commit-config.yaml` exists. Phase 34 introduces it (gitleaks-only initially; Phase 34 keeps it minimal — no ruff/black mandates).

## Tool Versions (locked at research time)

| Tool | Pinned version | Rationale |
|------|----------------|-----------|
| gitleaks | `v8.21.2` | Stable v8.x (8.21.2 verified 2026-05). `--config` plus `--baseline-path` for surgical allowlist. |
| pre-commit | `v3.8.0` | Stable, no breaking changes. |
| pip-audit | `>=2.7.3` | OSS, GitHub Action `pypa/gh-action-pip-audit@v1.1.0`. Supports SARIF and JSON output. |
| osv-scanner | `v1.9.1` | Google OSS-Vulnerability scanner; supports `--call-analysis` and severity gates. |
| cargo-audit | `0.20.1` | Rustsec advisory DB; CI install via `cargo install cargo-audit`. |
| cargo-deny | `0.16.2` | Supports `advisories`, `bans`, `licenses`, `sources`. `deny.toml` config. |
| syft | `v1.14.0` | Anchore SBOM. Outputs `spdx-json` / `cyclonedx-json`. Action `anchore/sbom-action@v0.17.0`. |

## Severity Gate Strategy (Pitfall P65)

- **Fail CI on:**
  - HIGH or CRITICAL CVSS on direct Python deps (`pyproject.toml` `[project].dependencies`).
  - CRITICAL CVSS on Python transitive deps (uv lockfile).
  - HIGH or CRITICAL on direct Rust crates (`Cargo.toml` `[dependencies]`).
  - CRITICAL on Rust transitives (`Cargo.lock`).
- **Warning-only (non-blocking):**
  - LOW + MEDIUM at any depth.
  - HIGH on transitives.
- Implementation: pip-audit `--vulnerability-service=osv --strict` plus a Python `severity_gate.py` script that parses JSON output and applies the matrix above. Same script reusable for cargo-audit JSON.

## Secret Scanning Strategy (Pitfall P64)

- gitleaks `v8.21.2` default ruleset PLUS one allowlist entry for the AIza placeholder pattern used in test fixtures.
- `.secrets.baseline` (custom TOML format gitleaks consumes via `--baseline-path`) contains exactly the known-false-positive findings — each with a `comment` field describing the test path.
- NOT a broad `[allowlist] regexes = [".*"]` — entries are file+rule+secret-hash triples.
- Test gate: `tests/security/test_gitleaks_baseline.py` parses the baseline and asserts every entry has a non-empty `comment` and that the secret matches a known AIza-fixture pattern (`AIza` + 35 base64 chars where the alphabet is fixed).

## Telemetry Consent Strategy (Pitfall P67)

- Wizard step: `tauri/ui/src/wizard/step-telemetry-consent.ts` (new). Router slot between `profile-consent` and `smoke-test`.
- Two equally-prominent radios:
  - `[ ] Don't share` (default-checked — Pitfall P67 default-OFF).
  - `[ ] Share anonymous diagnostics` (off by default).
- Field-set disclosure list:
  - Anonymized error reports (stack hashes; never paths/values).
  - Feature-usage histogram (counts only — which buttons clicked, never timestamps near track changes).
  - Crash banner timing (seconds-since-launch when banner shown).
- Explicit NOT-COLLECTED list rendered visibly:
  - NO track titles, NO audio, NO library contents, NO MIDI device names, NO window titles.
- "Continue" button advances regardless of selection — no `[ ] skip → off` dark pattern.
- Persists to `config_store.py` via `state.json` `telemetry_consent: bool`.

## Outbound Network Inventory (Source of Truth)

The boot banner in `sec_check.py` and SECURITY.md§Outbound endpoints MUST stay in sync. Authoritative list:

1. `https://api.bravoh.altidus.world` — Bravoh proxy (Gemini reactions, TTS).
2. `https://api.altidus.world/vibemix/latest.json` — updater manifest (Phase 18 Plan 18-04).
3. `https://github.com/bravoh-ai/vibemix` — opened via shell on user click (not background).
4. `https://existential.audio/blackhole` — opened on user click during wizard install hint.

Telemetry endpoint (optional, opt-in only):
5. `https://telemetry.altidus.world/vibemix/v1/event` — present in inventory but tagged `opt-in`; sec_check banner says `Telemetry: OFF` when consent is false.

## Tauri Capability Snapshot Strategy

- Snapshot file: `tauri/src-tauri/capabilities/SNAPSHOT.json` (committed).
- Generated by `scripts/dist/snapshot_capabilities.py` — canonical JSON serialization (sorted keys, deterministic indent).
- CI gate (`.github/workflows/capabilities-lint.yml`) runs the snapshot generator and `git diff --exit-code` against committed SNAPSHOT.
- Diff fails CI; resolution requires regenerating snapshot in same PR + a PR-description block tagged `SECURITY_CAPABILITY_DELTA:` justifying the change.

## Decisions Locked

- **gitleaks** over `detect-secrets` (better OSS adoption + simpler baseline format).
- **pip-audit + osv-scanner** both (overlapping coverage; cheap to run; differing DBs catch different things).
- **syft** over `cyclonedx-bom` (broader ecosystem support + Anchore action is well-maintained).
- **STRIDE-lite, 4 surfaces only** — proxy bypass, key extraction, telemetry exfil, supply chain. NOT full enterprise STRIDE.
- **Vanilla TS** for all wizard UI (project convention; Phase 32 set the precedent).
- **Real Apple/SignPath signing deferred** — verifier surface only in Phase 34. No autonomous POST/PUT to Apple/SignPath endpoints (P46).
- **Real PGP key deferred** — placeholder `KAAN-PGP-PLACEHOLDER.asc` shipped; KAAN-ACTION-LEGAL.md documents real-key-generation steps.

## Plan Slice (10 plans, ~1 per REQ-ID)

1. **34-01** — gitleaks + .secrets.baseline + secret-scan CI (SEC-01).
2. **34-02** — pip-audit + osv-scanner Python CVE workflow + severity_gate.py (SEC-02).
3. **34-03** — cargo-audit + cargo-deny Rust CVE workflow (SEC-03).
4. **34-04** — syft SBOM workflow on release (SEC-04).
5. **34-05** — signed-binary verifier CI surface (SEC-05).
6. **34-06** — SECURITY.md update + PGP placeholder + README link + KAAN-ACTION-LEGAL.md (SEC-06).
7. **34-07** — docs/threat-model.md STRIDE-lite (SEC-07).
8. **34-08** — telemetry consent wizard step + state.json field (SEC-08).
9. **34-09** — Tauri capabilities snapshot lint workflow (SEC-09).
10. **34-10** — runtime/sec_check.py boot banner + outbound-list sync test (SEC-10).

Atomic commit per plan. Each ships gate tests.
