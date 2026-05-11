# SignPath Foundation OSS Application — vibemix

> **KAAN-ONLY:** This file is the field-by-field reference for the SignPath OSS application form.
> Submission URL: <https://signpath.io/solutions/open-source-community>
> SLA: ~1 week approval (per amd/gaia#732, April 2026 — single recent data point;
> CONTEXT.md's 3-week buffer is conservative).
> Apply on day 1 of Phase 1 so the cert is ready by Phase 18 (installer signing).
> **Claude cannot submit forms with personal/business info — Kaan files this manually.**

---

## 1. Basic Information

| Field | Value |
|-------|-------|
| Project name | `vibemix` |
| Short name | `vibemix` |
| Homepage | `https://github.com/ozzaii/vibemix` |
| Brief description | Open-source AI DJ co-host. Listens to master audio, watches DJ software, talks back. |
| License | Apache 2.0 |
| License URL | `https://github.com/ozzaii/vibemix/blob/main/LICENSE` |
| Programming languages | Python, JavaScript, HTML/CSS |

**Detailed description (paste verbatim into the form's long-description field):**

> vibemix is a free, open-source AI co-host for live DJ sets. It runs locally on macOS or
> Windows: listens to your master output (via BlackHole on macOS / WASAPI loopback on
> Windows), watches your DJ software's window, ingests your controller actions over MIDI,
> and talks back into your headphones or speakers as either a hype-man (party mode) or a
> coach (feedback mode). Three user levels — Beginner / Intermediate / Pro — with prompt
> templates tuned to each, plus a curated library of popular MIDI controllers mapped out of
> the box. AI is Google Gemini, routed through a server-side proxy so the API key never
> leaves the maintainer's infrastructure. vibemix is the first open-source release from the
> Bravoh team (closed beta March 2026, founder Kaan Özkan).

---

## 2. Repository Information

| Field | Value |
|-------|-------|
| Repository type | Git |
| Repository URL | `https://github.com/ozzaii/vibemix` |
| Contributor count | 1 (Kaan Özkan); Bravoh team (Musa, Yasin) joining post-launch |
| Commit count | (fill at submission time — `git rev-list --count HEAD`) |
| Project age | < 1 week at submission — first commit lands during Phase 1 |
| Development status | Alpha / pre-release |

---

## 3. Distribution & Downloads

| Field | Value |
|-------|-------|
| Download page URL | `https://github.com/ozzaii/vibemix/releases` (will exist post-Phase 18) |
| Package formats | Windows MSI installer, macOS DMG |
| Distribution method | Direct download from GitHub Releases |
| Total downloads (all time) | 0 — pre-release, signed binaries pending SignPath approval |
| Downloads per month | 0 — see above |

**Section 3 candor (paste as a cover note if the form supports it):**

> vibemix is pre-release. This application is filed referencing **expected** future
> artifacts — Windows MSI + macOS DMG via PyInstaller + Inno Setup, attached to GitHub
> Releases starting around June 2026 (Phase 18 of our internal roadmap). If SignPath
> defers approval until binaries exist, we will resubmit at Phase 11–13 once a usable
> pre-release binary is in `dist/`. The 3-week buffer in our planning absorbs this risk.

---

## 4. Privacy Policy

| Field | Value |
|-------|-------|
| Collects/transmits user data? | Yes |
| What is collected? | DJ-window screenshot (user-picked window), master-audio PCM snapshots, MIDI controller events, current track title from the OS now-playing API. |
| Where transmitted? | Google Gemini API via a Bravoh-side server proxy. The raw Gemini API key never leaves the proxy server. End-user clients are rate-limited per-token. |
| Privacy policy URL | Placeholder for Phase 1 application: `https://github.com/ozzaii/vibemix/blob/main/README.md` (privacy section). The dedicated privacy policy page is a Phase 19 deliverable; the placeholder will be replaced once the policy is published. |

---

## 5. Wikipedia Article

| Field | Value |
|-------|-------|
| Wikipedia URL | N/A |
| Justification | Pre-release project < 1 month from launch — Wikipedia notability not yet established. Bravoh (the parent project) launches closed beta March 2026 and is the basis for any future notability claim. |

---

## 6. Verification & Trust Evidence

**Lead with Bravoh's existing footprint (strongest day-1 signal):**

- Maintainer Kaan Özkan is the founder of **Bravoh** (<https://altidus.world>), an AI
  Artist Operating System for music artists. Bravoh closed beta launches March 2026 with
  a dedicated team (Musa — senior dev, Yasin — dev, Francis Tural — test user).
- Bravoh operates production infrastructure today (`api.altidus.world`,
  `dev.altidus.world`, `altidus.world`), running FastAPI + PostgreSQL + Redis + Celery
  + MinIO on dedicated server `77.42.28.93`.
- The Bravoh team is publicly identifiable (LinkedIn, Bravoh website team page).
- vibemix is Bravoh's first open-source release, dropped weeks ahead of Bravoh's public
  launch to warm an audience that converts into Bravoh's waitlist.

**Media / blog evidence:**

- Launch coverage planned via IG ads + DJ network outreach (Francesco — Bravoh
  cofounder, driving marketing). Coverage links to be added at re-submission if SignPath
  requests them.

**GitHub insights:**

- Star / fork / contributor counts: fill at submission time. Pre-release expectation: low
  but non-zero (Kaan + Francesco personal networks drive launch traffic).

**Trademark:**

- The Bravoh trademark is owned by the founding entity. vibemix is an open-source
  sub-brand under the Bravoh project umbrella; Apache 2.0 license allows Bravoh's own
  internal use of the code without additional license grant.

---

## 7. Technical Details

| Field | Value |
|-------|-------|
| What will be signed | Windows MSI (Inno Setup wrapping a PyInstaller `--onedir` payload) + macOS DMG (Notarized .app bundle) |
| File types | `.msi`, `.exe` (PyInstaller bootstrap inside the MSI), `.dmg`, `.app` |
| Signing frequency | Per release — initial v1.0 + roughly monthly patch releases |
| Build process | GitHub Actions on tag push (Phase 20 deliverable). The signed-build job uploads the unsigned artifact to SignPath, downloads the signed binary, attaches it to the GitHub Release. |
| CI/CD | GitHub Actions, using SignPath's official Action (`signpath/github-action-submit-signing-request`). |

---

## 8. Contact Information

| Field | Value |
|-------|-------|
| Primary contact name | Kaan Özkan |
| Primary contact email | `oozzxaaii@gmail.com` |
| Maintainers | Kaan Özkan (primary); Musa, Yasin (Bravoh — joining post-launch) |
| GitHub org/user | `ozzaii` (personal account; transfer to a `bravoh` org deferred — see Submission Notes) |
| Additional contacts | Francesco — Bravoh cofounder, marketing/product (no email shared in this form unless requested) |

---

## 9. Terms & Conditions

Three checkboxes for Kaan to confirm at submission:

- [ ] I confirm vibemix is an open-source project licensed under an OSI-approved license (Apache 2.0).
- [ ] I confirm I am the maintainer and authorized to apply for SignPath OSS signing on the project's behalf.
- [ ] I agree to SignPath's Foundation Terms of Service.

**Note:** Apache 2.0 is OSI-approved and explicitly qualifies for SignPath OSS. No
commercial dual-licensing — vibemix is single-license under Apache 2.0 throughout.

---

## Submission Notes for Kaan

**Three sharp edges to expect:**

1. **Section 3 weak point (downloads = 0):** Be candid in the cover note. The form
   probably expects a non-zero download history; the pre-release framing is your friend.
   If SignPath defers, we resubmit at Phase 11–13 once a pre-release binary exists.
2. **Section 6 needs Bravoh footprint leading:** Lead the trust evidence with
   `altidus.world`, the team, and the production infrastructure. Don't lead with vibemix
   — it's new. Lead with the parent project's existing footprint.
3. **Section 4 privacy policy URL is a placeholder:** README link until Phase 19 ships
   the dedicated privacy page. If the form requires a hosted privacy page, link a stub
   GitHub Pages page under `ozzaii.github.io/vibemix/privacy` (one-time ~5 min setup).

**`bravoh` org transfer (deferred — NOT a Phase 1 blocker):**

> Bravoh Enterprise has 0 orgs and a billing flag. The repo lives at `ozzaii/vibemix`
> for now and can be transferred via `gh api repos/ozzaii/vibemix/transfer -F new_owner=bravoh`
> once a proper `bravoh` GitHub org is stood up. SignPath survives a rename / ownership
> transfer without re-approval (per their stated terms). All URLs above stay consistent
> at submission time.

**Confirmation expectations:**

- SLA: ~1 week per amd/gaia#732 (April 2026). CONTEXT.md's 3-week buffer is conservative.
- Confirmation email arrives at `oozzxaaii@gmail.com` (Section 8 primary contact).
- Once approved, SignPath issues a project token used by the Phase 20 CI workflow.
