# Security Policy

> If you believe you've found a security issue in vibemix, please email
> **security@bravoh.com** (encrypt with the PGP key below) instead of
> opening a public issue.

## Reporting a vulnerability

Email **security@bravoh.com** with details. Do **not** open a public issue
until we've coordinated disclosure.

### What to include

- A clear description of the issue.
- Steps to reproduce, or a proof-of-concept where applicable.
- The version of vibemix you tested against (`vibemix --version`).
- Your OS + version.
- Whether you'd like credit in the release notes (optional).

### Our response

- Acknowledgement within 72 hours.
- Initial assessment within 7 days.
- Coordinated disclosure within 90 days of confirmation, unless we agree on a different timeline with you.

### PGP

Encrypted reports preferred. Use the public key in
[`KAAN-PGP-PLACEHOLDER.asc`](./KAAN-PGP-PLACEHOLDER.asc) at the repo root.

**This is a placeholder key.** Kaan Özkan generates and signs the real key
on first vulnerability report — see `KAAN-ACTION-LEGAL.md` for the
generation runbook. Until then, plaintext email to `security@bravoh.com`
is accepted, but please mark sensitive details `[ENCRYPT ON REPLY]` and
we'll move to encrypted thread immediately.

| Key | Fingerprint | Status |
|-----|-------------|--------|
| `KAAN-PGP-PLACEHOLDER.asc` | `PLACEHOLDER-FINGERPRINT-NOT-REAL` | placeholder — Kaan-action |

## Supported versions

| Version | Supported |
|---------|-----------|
| `0.x` (pre-release) | latest tag only |
| `1.x` | latest minor + previous minor |
| `< 0.1.0` | unsupported |

## Scope

In scope:

- The vibemix client (this repo).
- The Bravoh proxy endpoints that vibemix talks to (`api.bravoh.altidus.world/*`).
- The auto-updater manifest endpoint (`api.altidus.world/vibemix/latest.json`).

Out of scope:

- Third-party services we depend on (report directly to Google, Apple,
  Microsoft, SignPath, GitHub).
- Vulnerabilities that require physical access to the user's machine.
- Issues in the POC reference files (`cohost*.py`, `mascot.html`) — they are
  reference, not shipped.

## Outbound endpoints

vibemix talks to a closed list of network endpoints. Anything else is a bug.

| Endpoint | When | Direction |
|----------|------|-----------|
| `https://api.bravoh.altidus.world` | Every AI reaction + TTS request | client → Bravoh proxy |
| `https://api.altidus.world/vibemix/latest.json` | Updater check (~once/day) | client → updater |
| `https://github.com/bravoh-ai/vibemix` | User click in settings | shell-out only |
| `https://existential.audio/blackhole` | User click in wizard install hint | shell-out only |
| `https://telemetry.altidus.world/vibemix/v1/event` | **Only when consent toggled ON** | client → telemetry |

This list is mirrored byte-for-byte by `src/vibemix/runtime/sec_check.py`
(boot banner). A CI test (`tests/security/test_sec_check.py`)
verifies the two stay in sync — adding an endpoint here without
updating `sec_check.py` (or vice versa) fails the build.

## What we don't do

- No paid bug bounty for v1. Credit + thanks in the release notes is what
  we can offer.
- No shipping of known CVEs. If a dep has an unfixable issue, we patch it
  ourselves or drop the dep (gate in `.github/workflows/python-cve.yml`).
- No telemetry without explicit opt-in. Default is OFF, and the consent
  toggle has no dark patterns (see Phase 34 / SEC-08).

## Threat model

A STRIDE-lite threat model lives in [`docs/threat-model.md`](./docs/threat-model.md).
Covers proxy rate-limit bypass, key extraction, telemetry exfil, supply
chain.

## Past advisories

None yet.

## Audit trail

Every release pushes an SBOM (`sbom.spdx.json`) to the GitHub Release
artifacts list. See [`.github/workflows/sbom.yml`](.github/workflows/sbom.yml).
