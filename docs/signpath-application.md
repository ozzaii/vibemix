# vibemix — SignPath OSS Foundation Application

## Why this file exists

Per Pitfall 6 (`.planning/research/PITFALLS.md` lines 148–172), the SignPath OSS Foundation approval cycle is ~1 week — they manually verify open-source identity before granting free code-signing for Windows binaries. Day-1 of Phase 21, file (or re-verify) the application before any other Phase 21 work proceeds; otherwise the SignPath SLA becomes the critical-path bottleneck on the v2.0 ship gate. This file is the checklist Kaan works from to file the application without re-reading PITFALLS.md or hunting through old `.planning/research/` notes.

## Pre-application checklist

- [ ] GitHub repo URL is `https://github.com/ozzaii/vibemix` and is public
- [ ] LICENSE file at repo root is Apache-2.0 (per STATE locked decision; confirmed via `head -3 LICENSE` showing "Apache License Version 2.0, January 2004")
- [ ] README has the project description (warmup OK if Phase 26 README rewrite hasn't landed yet — a minimal "AI co-host for live DJ sets" sentence is enough to demonstrate identity)
- [ ] `.github/workflows/release.yml` already shows `signpath/github-action-submit-signing-request@v1.2.0` (already shipped Phase 18 — line 291 of the workflow)

## Application form fields

| Field | Value |
|-------|-------|
| Project name | vibemix |
| Project URL | https://github.com/ozzaii/vibemix |
| License | Apache-2.0 |
| Identity proof | Kaan Özkan (use email matching GitHub commit identity — `oozzxaaii@gmail.com`) |
| Build automation | GitHub Actions (`signpath/github-action-submit-signing-request@v1.2.0`) |
| Artifact configuration slug | `vibemix-binaries` (matches `release.yml` line 297 — `artifact-configuration-slug: vibemix-binaries`) |

## Status tracking

| Field | Value |
|-------|-------|
| Filed date | [TBD] |
| Ticket ID | [TBD] |
| Approval date | [TBD] |
| Approver | [TBD] |

## Fallback if not approved by Phase 21 Wave 5

Per Pitfall 6 mitigation, secondary signing path is a Kaan-purchased EV cert (~$200/yr, instant SmartScreen reputation — no waiting on third-party SLA). **Budget gate, requires explicit Kaan approval, do NOT auto-purchase** — the OSS Foundation path is the default because it costs $0 and matches the open-source distribution model.

## Cross-references

- `.planning/research/PITFALLS.md` P6 (SignPath OSS ~1-week SLA, lines 148–172)
- `.planning/phases/21-sign-notarize-github-release-matrix/21-DEFERRED.md` Blocker B
- `.github/workflows/release.yml` — `build-windows` job stage 2 (`SIGN — Submit signing request to SignPath`) + `secret-name-audit` Wave 0 gate
