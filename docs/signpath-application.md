# vibemix — SignPath OSS Foundation Application

## Why this file exists

Per historical Pitfall 6
(`.planning/archive/2026-05-27-stale-v6-memory-research/PITFALLS.md`), the
SignPath OSS Foundation approval cycle is ~1 week — they manually verify
open-source identity before granting free code-signing for Windows binaries.
Day-1 of Phase 21, file (or re-verify) the application before any other Phase
21 work proceeds; otherwise the SignPath SLA becomes the critical-path
bottleneck on the v2.0 ship gate. This file is the checklist Kaan works from to
file the application without hunting through old `.planning/research/` notes.

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
| Account / notification email | `kaan@bravoh.ai` (Kaan's decision 2026-05-30 — Bravoh public domain, more credible than a gmail for the org-backed account) |
| Identity proof | Repo control of `github.com/ozzaii/vibemix` (SignPath verifies via the GitHub account, not the account email). Kaan Özkan, backed by Bravoh. |
| Build automation | GitHub Actions (`signpath/github-action-submit-signing-request@v1.2.0`) |
| Artifact configuration slug | `vibemix-binaries` (matches `release.yml` line 297 — `artifact-configuration-slug: vibemix-binaries`) |

## Full form — copy-paste values (live form at https://signpath.org/apply)

Fill these in once the gate below is cleared. `*` = required field.

| Field | Value to paste |
|-------|----------------|
| Project Name * | `vibemix` |
| Repository URL * | `https://github.com/ozzaii/vibemix` |
| Homepage URL * | `https://github.com/ozzaii/vibemix` (repo page; avoids the altidus.world/bravoh.ai naming question) |
| Download URL | `https://github.com/ozzaii/vibemix/releases/latest` (must be live + the page names SignPath Foundation — now satisfied via README + Code Signing Policy) |
| Privacy Policy URL | `https://github.com/ozzaii/vibemix/blob/main/PRIVACY.md` |
| Wikipedia URL | — (none) |
| Tagline * | `An open-source AI co-host that listens to your live DJ set and talks back in real time.` |
| Description * | `vibemix is a free, open-source AI co-host for live DJ sets. It runs locally on macOS and Windows — listening to your master output, watching your DJ software, and reading your controller — then reacts through your headphones as either a hype-man or a coach. It is built to feel like a real DJ friend in your ear: grounded in what's actually happening in the mix, not generic commentary.` |
| Reputation * | `vibemix is the first open-source release from Bravoh (https://bravoh.ai), a music-AI startup running a live closed beta with real artists since March 2026. The project is newly public; reputation is being built through launch.` → **at filing time, append current GitHub stars/forks, release download counts, and any press / Reddit / community links.** |
| Maintainer Type | dropdown — pick `Company` (Bravoh-backed); fall back to `Individual` if no company option fits |
| Build System | dropdown — `GitHub Actions` |
| First Name * | `Kaan` |
| Last Name * | `Özkan` |
| Email * | `kaan@bravoh.ai` |
| Company Name | `Bravoh` |
| Primary Discovery Channel * | dropdown — pick whatever is actually true (e.g. `Web search` or `GitHub`) |
| Exact source (optional) | leave blank or note the real source |

**Consent + bot-check (Kaan does these — I can't):**
- ☑ Code of Conduct + "certificates issued in SignPath Foundation's name" — **required**, you tick.
- ☐ "receive other communications from SignPath" — leave **unchecked** (privacy).
- ☑ "allow SignPath to store and process my personal data" — **required**, you tick.
- reCAPTCHA — **you complete it**, then Submit.

## Status tracking

| Field | Value |
|-------|-------|
| Filed date | [TBD] |
| Ticket ID | [TBD] |
| Approval date | [TBD] |
| Approver | [TBD] |

## Remaining gate before filing (2026-05-30)

The form/CI/docs prep is done, but two SignPath requirements are not yet met — file once both are true:

1. **A published release exists.** Today only `v0.1.0-rc1` exists as a *Draft*; the form requires the project to already be released in the form to be signed, with a download page. Publish the macOS release first (gated by the product no-release hard gate + working co-host — see the live-verify state).
2. **`Reputation*` is a required field and is currently thin** (repo: 4★, 0 forks, 1 watcher). Best honest framing: official open-source release *backed by Bravoh* (funded music-AI startup, live beta with real users since 2026-03-17). Stronger once the release ships and accrues stars/downloads — consider waiting for some traction so this field isn't the rejection reason.

Also note: the SmartScreen warning clears via **download-volume reputation regardless of cert type** — SignPath Foundation (OV-class) builds it the same way a paid cert would.

## Fallback if the Foundation path is rejected or too slow

The OSS Foundation path is the default ($0, matches the open-source model). If rejected:

- ~~EV cert "instant SmartScreen reputation"~~ — **stale rationale.** Since March 2024 EV certs no longer bypass SmartScreen; all cert types must build reputation by download volume, so paying a premium for EV solely to skip the warning is no longer justified.
- Better paid fallback: **Certum Open Source Code Signing** (~€30–120/yr, OV-class, publisher = Kaan/OZAI's name, available to individuals in Turkey). Or **Azure Artifact Signing** (~$10/mo) — but only if an EU/US/CA org entity is available, since Turkish individuals are not eligible.
- **Budget gate, requires explicit Kaan approval, do NOT auto-purchase.**

## Cross-references

- `.planning/archive/2026-05-27-stale-v6-memory-research/PITFALLS.md` P6
  (SignPath OSS ~1-week SLA)
- `.planning/phases/21-sign-notarize-github-release-matrix/21-DEFERRED.md` Blocker B
- `.github/workflows/release.yml` — `build-windows` job stage 2 (`SIGN — Submit signing request to SignPath`) + `secret-name-audit` Wave 0 gate
