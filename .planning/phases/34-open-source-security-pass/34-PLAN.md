# Phase 34: Open-Source Security Pass — PLAN

**Mode:** `gsd-autonomous fully`
**Plans:** 10 (1 per REQ-ID).
**Discipline:** Atomic commits, hard gates per pitfall (P64/P65/P67).

---

## Plan 34-01 — Gitleaks + .secrets.baseline + secret-scan CI (SEC-01)
**Files:**
- `.pre-commit-config.yaml` (new)
- `.secrets.baseline` (new; gitleaks format)
- `.gitleaks.toml` (new; ruleset config + allowlist references)
- `.github/workflows/secret-scan.yml` (new)
- `tests/security/test_gitleaks_baseline.py` (new)

**Gate:** `test_gitleaks_baseline_surgical` — every baseline entry has non-empty comment and matches an AIza-fixture pattern; broad allowlists rejected.

## Plan 34-02 — Python CVE pip-audit + osv-scanner + severity gate (SEC-02)
**Files:**
- `.github/workflows/python-cve.yml` (new) — nightly + PR + push.
- `scripts/dist/severity_gate.py` (new) — JSON parser + matrix.
- `tests/security/test_severity_gate.py` (new).

**Gate:** `test_cve_severity_gate_high_fails_low_warns` — synthetic JSON of {high direct → fail, low → warn, critical transitive → fail}.

## Plan 34-03 — Rust CVE cargo-audit + cargo-deny (SEC-03)
**Files:**
- `tauri/src-tauri/deny.toml` (new).
- `.github/workflows/rust-cve.yml` (new).

**Gate:** workflow lint + smoke run on local cargo-audit (no extra unit test — gate is the workflow shape verified by yaml-lint + manual cargo audit).

## Plan 34-04 — SBOM syft + release attach (SEC-04)
**Files:**
- `.github/workflows/sbom.yml` (new) — on `release: published`.
- `tests/security/test_sbom_workflow_shape.py` (new).

**Gate:** workflow yaml-lint + structural test that asserts the workflow attaches `sbom.spdx.json` to the release.

## Plan 34-05 — Signed-binary verifier CI surface (SEC-05)
**Files:**
- `.github/workflows/verify-signed.yml` (new) — skip-with-note when no signing yet.
- `scripts/dist/verify_signed.py` (new) — checksum compare + signature placeholders.

**Gate:** unit test on `verify_signed.py` for skip-with-note behavior + the no-Apple/SignPath-POST contract from P46.

## Plan 34-06 — SECURITY.md + PGP placeholder + README link + KAAN-ACTION-LEGAL.md (SEC-06)
**Files:**
- `SECURITY.md` (replace; outbound list is canonical).
- `KAAN-PGP-PLACEHOLDER.asc` (new placeholder armored block).
- `KAAN-ACTION-LEGAL.md` (new — PGP gen steps, Apple/SignPath steps, the no-autonomous boundary).
- `README.md` — first-line security link (edit).

**Gate:** no test — content review only.

## Plan 34-07 — Threat model STRIDE-lite (SEC-07)
**Files:**
- `docs/threat-model.md` (new). 4 surfaces only.

**Gate:** sync test referenced from Plan 34-10 ensures outbound list mirrored.

## Plan 34-08 — Telemetry consent wizard + state.json field (SEC-08)
**Files:**
- `tauri/ui/src/wizard/step-telemetry-consent.ts` (new).
- `tauri/ui/src/wizard/router.ts` (edit — insert step).
- `src/vibemix/runtime/config_store.py` (edit — add `telemetry_consent: bool = False`).
- `tauri/ui/tests/wizard/step-telemetry-consent.spec.ts` (new).
- `tests/security/test_telemetry_consent.py` (new).

**Gate:** `test_telemetry_consent_default_off_no_dark_pattern` — state.json default-OFF + spec ensures both radio options have equal visual prominence (label widths within ±10% chars; identical CSS class).

## Plan 34-09 — Tauri capability snapshot lint (SEC-09)
**Files:**
- `tauri/src-tauri/capabilities/SNAPSHOT.json` (new — generated).
- `scripts/dist/snapshot_capabilities.py` (new).
- `.github/workflows/capabilities-lint.yml` (new).
- `tests/security/test_capability_snapshot.py` (new).

**Gate:** `test_capability_snapshot_drift_detected` — synthetic mutation of capability file produces diff and snapshot-generator catches it.

## Plan 34-10 — runtime/sec_check.py boot banner + outbound sync test (SEC-10)
**Files:**
- `src/vibemix/runtime/sec_check.py` (new).
- `src/vibemix/runtime/__init__.py` (edit — export `print_security_banner`).
- `src/vibemix/__main__.py` (edit — call banner on startup).
- `tests/security/test_sec_check.py` (new).

**Gate:** `test_sec_check_banner_matches_security_md` — banner outbound list parsed and compared against the SECURITY.md§Outbound endpoints section line-for-line.

---

## Cross-cutting

- Atomic commit per plan with `feat(34-NN): ...` or `chore(34-NN): ...` style.
- POC files untouched: `cohost*.py`, `cohost*.bak`, `run*.sh`.
- No autonomous Apple/SignPath POST/PUT — verifier surface only.
- Privacy paths off-limits (no reading of `~/hermes-rig/**` etc).
