# Phase 34: Open-Source Security Pass - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully)

<domain>
## Phase Boundary

vibemix's repo + binary + runtime claims survive public-OSS scrutiny — no leaked secrets, no critical CVEs, signed binary verifiable, telemetry opt-in default-OFF, threat model documented.

**Mapped REQ-IDs (10):** SEC-01 (gitleaks + secret-scan), SEC-02 (Python CVE), SEC-03 (Rust CVE), SEC-04 (SBOM), SEC-05 (signed-binary verifier), SEC-06 (SECURITY.md), SEC-07 (threat-model.md STRIDE-lite), SEC-08 (telemetry consent default-OFF), SEC-09 (Tauri capabilities snapshot lint), SEC-10 (auditable privacy claim via sec_check.py).

**In scope:**
- `gitleaks` pre-commit hook + `.secrets.baseline` with surgical AIza-fixture allowlist (Pitfall P64).
- GitHub Actions secret-scan job blocking PRs.
- `pip-audit` + `osv-scanner` for Python deps; HIGH+ direct / CRITICAL transitives gate (Pitfall P65).
- `cargo-audit` + `cargo-deny` for Rust deps; same severity gate.
- `syft`-generated `sbom.spdx.json` per release, attached to GitHub Release artifacts.
- Post-sign verifier CI job — checksum + signature validate before publish.
- `SECURITY.md`: disclosure policy, PGP key, supported versions table; linked first-line from README.
- `docs/threat-model.md`: STRIDE-lite covering proxy rate-limit bypass + key extraction + telemetry exfil + supply chain.
- First-run wizard telemetry consent screen — default-OFF (Pitfall P67 no dark pattern), field-set disclosure.
- `runtime/sec_check.py` boot banner: "audio + MIDI + screen never leaves machine" claim, with outbound-connection inventory hooks.
- Tauri capabilities snapshot git-tracked; CI diff-fails on unexpected addition.

**Out of scope:**
- Apple notarytool / SignPath signing wiring (Phase 38).
- Real Kaan PGP key generation (Kaan-action via KAAN-ACTION-LEGAL.md — placeholder key in repo).
- Penetration testing engagement (out of scope; OSS-Foundation reviewer signoff is post-launch).
- Encryption of profile / recordings at rest (already local-only + 0o600 perms; encryption v2.2).
- Hardware-security-module / TPM integration.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion (locked per gsd-autonomous fully)

Grounded in:
- ROADMAP Phase 34 verbatim success criteria
- REQUIREMENTS.md SEC-01..10
- Pitfalls P64 (FP flood → surgical baseline), P65 (CVE flood → severity gate), P67 (default-OFF telemetry, no dark pattern)
- v2.0 Phase 21 CI scaffold (shipped)
- Bravoh proxy infrastructure (Bravoh-side)
- Memory: "API key embedded in distributed binary is the API-key-protection problem of the year — solve via Bravoh-side proxy with per-client rate limit"
- Memory `feedback_autonomous_no_grey_area_pause` — autonomous mode

### Secret scanning (SEC-01 / P64)
- `gitleaks` pre-commit hook via `pre-commit` config.
- `.secrets.baseline` (gitleaks format): allowlist AIza-fixture placeholders ONLY. Each entry has comment explaining context.
- `.github/workflows/secret-scan.yml`: runs on `pull_request` + `push:main`. Fails on real key.
- Test: synthetic real-key commit detected; AIza-fixture allowlisted.

### Python CVE (SEC-02 / P65)
- `pip-audit` + `osv-scanner` in CI.
- Severity gate: HIGH+ on direct deps fails the build; CRITICAL on transitives fails.
- LOW/MEDIUM are warnings only (P65 — prevents flood).
- File: `.github/workflows/python-cve.yml`, runs nightly + on PR.

### Rust CVE (SEC-03)
- `cargo-audit` + `cargo-deny` in CI.
- Same severity gate as Python.
- Configs: `deny.toml` + `audit.toml`.
- File: `.github/workflows/rust-cve.yml`.

### SBOM (SEC-04)
- `syft` generates `sbom.spdx.json` (SPDX 2.3 format) per release.
- Attached as GitHub Release artifact.
- File: `.github/workflows/sbom.yml` triggered on `release: published`.

### Signed-binary verifier (SEC-05)
- CI job runs AFTER Phase 38 signing — checksums + signature validates Mac (notarytool ticket) + Windows (Authenticode + SignPath chain).
- Fails publish on mismatch.
- File: `.github/workflows/verify-signed.yml`.
- Note: Phase 38 wires real Apple/SignPath. Phase 34 just provides the verifier surface; on no-sign-yet runs, skip with note.

### SECURITY.md (SEC-06)
- Sections: Reporting policy (email + GPG key fingerprint), supported versions table, vulnerability disclosure timeline (90-day default), Hall of Fame.
- PGP key: placeholder `KAAN-PGP-PLACEHOLDER.asc` — Kaan generates real key, replaces, signs CI. Documented in `KAAN-ACTION-LEGAL.md`.
- Linked first-line from README.

### Threat model (SEC-07)
- `docs/threat-model.md` STRIDE-lite. 4 critical surfaces:
  1. **Proxy rate-limit bypass**: attacker uses our binary's identity to amplify; mitigate via Bravoh per-client token bucket + abuse logging.
  2. **Key extraction**: no raw AIza in binary; proxy auth via short-lived JWT or device-id signature. Reverse engineer extracts JWT minting key → mitigated by server-side rotate + suspect-binary revocation.
  3. **Telemetry exfil**: default-OFF; on-opt-in fields enumerated; no track titles, no audio, no library content.
  4. **Supply chain**: gitleaks + pip-audit + cargo-audit gate. SBOM published. Reproducible build is v2.2.

### Telemetry consent (SEC-08 / P67)
- First-run wizard screen — toggle default-OFF.
- Title: "Help vibemix get better? (you can change later)"
- Field-set disclosure: list every telemetry datum collected (e.g., "anonymized error reports", "feature usage histogram"). NO track titles, NO audio, NO library.
- NO dark patterns — both options equally prominent. No "skip" → off; "Don't share" is the default selected radio.
- Persistent in `~/.config/vibemix/state.json` under `telemetry_consent: bool`.

### Tauri capabilities lint (SEC-09)
- `tauri/src-tauri/capabilities/default.json` is committed.
- New CI gate: `tauri_capabilities_snapshot` — compares current vs `tauri/src-tauri/capabilities/SNAPSHOT.json`. Diff fails CI unless `SNAPSHOT.json` updated in same PR with reason in description.
- File: `.github/workflows/capabilities-lint.yml` + `scripts/check_capability_snapshot.sh`.

### Auditable privacy claim (SEC-10)
- `src/vibemix/runtime/sec_check.py` — boot banner module.
- On import, prints:
  ```
  vibemix vN.N.N — privacy posture
  ✓ Audio capture: BlackHole local — never leaves machine
  ✓ MIDI input: USB local — never leaves machine
  ✓ Screen capture: macOS Quartz local — never leaves machine
  ✓ Network out: Bravoh proxy only (api.bravoh.altidus.world)
  ✓ Telemetry: OFF
  ```
- Outbound-connection inventory in SECURITY.md mirrors this.
- Test: `test_sec_check_banner_matches_security_md` — banner contents and SECURITY.md outbound list stay in sync.

### Frontend convention
- Vanilla TS for consent screen (extends wizard pattern from Phase 32).

### Defer to Phase 38
- Real Apple notarytool + SignPath wiring. Phase 34 provides the verifier surface but does NOT execute signing.

### Test discipline
- pre-commit hook test: `pytest tests/security/test_gitleaks_baseline.py`
- CVE severity gate test: synthetic HIGH CVE entry → CI fails; LOW → CI passes
- SBOM presence test in release job
- Capability snapshot drift test
- sec_check.py boot banner test
- Telemetry consent default-OFF test

</decisions>

<code_context>
## Existing Code Insights

- **v2.0 Phase 21 (shipped)** — CI scaffold at `.github/workflows/`.
- **Bravoh-side proxy** — `https://api.bravoh.altidus.world` (per Bravoh docs in user CLAUDE.md context).
- **Wizard** — v2.0 Phase 11 + Phase 32 consent toggle pattern (vanilla TS).
- **Tauri capabilities** — `tauri/src-tauri/capabilities/default.json` extended in Phase 29 for `--debrief`.
- **AIza-fixture placeholders** — recordings/eval corpus may contain placeholder strings; Phase 27 has `scripts/scan_aiza_keys.py` (related).
- **`runtime/` package** — established by v2.0 (sec_check.py is new addition).

Codebase maps under `.planning/codebase/` feed plan-phase research.

</code_context>

<specifics>
## Specific Ideas

- **No dark patterns** (P67) — both consent options equally prominent. No "skip → off" trick.
- **Severity gate is critical** (P65) — without it, CVE noise floods devs.
- **Surgical secret allowlist** (P64) — every entry has comment explaining the placeholder context.
- **Threat model is STRIDE-lite** — concise, actionable, 4 surfaces only. Not full enterprise STRIDE.
- **Boot banner = single source of truth** for outbound claims.
- **PGP key is Kaan-action** — placeholder in repo, real key generated by Kaan.

</specifics>

<deferred>
## Deferred Ideas

- **Penetration testing engagement** — post-launch.
- **Reproducible builds** — v2.2.
- **HSM / TPM integration** — out of scope.
- **At-rest encryption of profile / recordings** — v2.2.
- **External security auditor signoff** — post-launch (OSS Foundation may include in their review).
- **CodeQL / Semgrep static analysis** — v2.2 stretch.
- **Bug bounty program** — post-launch.
- **Cosign / sigstore for non-Apple-non-Windows signing** — v2.2 (Linux excluded from v1).

</deferred>
