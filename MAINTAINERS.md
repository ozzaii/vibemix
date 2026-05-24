<!-- SPDX-License-Identifier: Apache-2.0 -->
# vibemix — Maintainers

## Active Maintainers

- Kaan Özkan (@bravoh-ai) — `kaan@bravoh.tech`
  Founder of Bravoh; vibemix is Bravoh's first open-source release.

## How to Reach Us

- General questions / bug reports / feature requests: open a GitHub issue.
- Security vulnerabilities: follow `SECURITY.md` — do NOT open a public issue.
- Contribution questions: follow `CONTRIBUTING.md`.

## Decision Process

- License: Apache-2.0 (see `LICENSE` and `NOTICE`); SPDX-License-Identifier on every source file.
- Governance: lazy consensus among active maintainers.
- Merge bar: 1 maintainer approval + CI green (Full Test Matrix workflow + repo-presence gates).
- Bravoh carveout: this repo (vibemix) is Apache-2.0; the Bravoh proxy is closed-source by design — see `CONTRIBUTING.md` 'Scope: vibemix vs Bravoh' for what belongs here vs there.

## Release Cadence

RC tags follow the `v0.1.0-rcN` pattern per `docs/release-process.md`; pre-flight gates are validated by `scripts/launch/cut_release.sh`; the final `gh release create` is a maintainer-action per `KAAN-ACTION-LEGAL.md §SHIP-V4`.

## On-Call / Response Time

Best-effort. vibemix is Kaan's OSS side-project alongside Bravoh's main product — issues are triaged in batches, typically within 7 days. Security reports per `SECURITY.md` get priority response.
