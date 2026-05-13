# Security Policy

## Reporting a vulnerability

If you believe you've found a security issue in vibemix, please email **security@bravoh.com** with details. Do **not** open a public issue.

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

A PGP key for `security@bravoh.com` will be published here once Bravoh ops generates one. Until then, email is the primary channel.

## Scope

In scope:

- The vibemix client (this repo).
- The Bravoh proxy endpoints that vibemix talks to (`api.altidus.world/*`).
- The auto-updater manifest endpoint.

Out of scope:

- Third-party services we depend on (report directly to Google, Apple, Microsoft, SignPath, GitHub).
- Vulnerabilities that require physical access to the user's machine.
- Issues in the POC reference files (`cohost*.py`, `mascot.html`) — they are reference, not shipped.

## What we don't do

- We don't run a paid bug bounty for v1. Credit + thanks in the release notes is what we can offer.
- We don't ship CVEs we know about. If a known dep has an unfixable issue, we'll either patch it ourselves or drop the dep.

## Past advisories

None yet.
