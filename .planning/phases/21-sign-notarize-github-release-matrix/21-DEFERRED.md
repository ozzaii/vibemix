# Phase 21 — Deferred Blockers Tracker

## Why this file exists

This is the single canonical Kaan-action / Francesco-action surface for the two external blockers that Phase 21 (sign + notarize + GitHub release matrix) cannot eliminate from inside the repo: the Apple Developer Program Agreement update (Francesco-action) and the SignPath OSS Foundation application (Kaan-action, ~1-week SLA). Per `feedback_autonomous_no_grey_area_pause` policy, Phase 21 does NOT pause on these; it continues with the mock-signing fallback already wired in `.github/workflows/release.yml` (Wave 0 `detect-signing-mode` job → `SIGNING_AVAILABLE=false` path) while the externalities resolve. Resolution UN-BLOCKS specific downstream plans: Blocker A unblocks **21-03-PLAN.md** (macOS DMG sign + notarize + stapler), Blocker B unblocks **21-04-PLAN.md** (Windows MSI SignPath signing + SmartScreen smoke test). Both blockers are documented per the Phase 16 deferred-tracker pattern (status / owner / downstream-block / workaround / verification / resolution log).

## Blocker A — Apple Developer Program Agreement update [Francesco-action]

- **Status:** OPEN (as of 2026-05-14 per STATE)
- **Deferred to:** francesco-action-required
- **Owner:** Francesco
- **What's needed:** Sign updated Apple Developer Program Agreement at https://developer.apple.com/account/ → Agreements, Tax, and Banking → Paid/Free Apps Agreement
- **Why blocking:** Without agreement update, App Store Connect API key (Issuer ID `3f60cc6b-df70-4ff8-9ceb-865dac6c1b4b`, key URMDRP5M3P) cannot create new code-signing requests; `notarytool submit` returns `Forbidden`
- **Downstream block:** 21-03-PLAN.md mac sign step (`scripts/dist/sign_macos.sh` stage 4 — notarytool submit + stapler)
- **Workaround until resolved:** Plan 03 ships with `SIGNING_AVAILABLE=false` mock-sign path (already wired in `release.yml` Wave 0 `detect-signing-mode` → `build-macos` job conditional `if: env.SIGNING_AVAILABLE == 'true' && env.DRY_RUN != 'true'`); the `release-publish` job is tag-gated AND secrets-gated (`if: startsWith(github.ref, 'refs/tags/v') && needs.detect-signing-mode.outputs.signing_available == 'true'`), so no accidental publish from a `workflow_dispatch` rehearsal
- **Verification when resolved:** `xcrun notarytool history --key AuthKey_URMDRP5M3P.p8 --key-id URMDRP5M3P --issuer 3f60cc6b-df70-4ff8-9ceb-865dac6c1b4b` returns HTTP 200 (not 403); a synthetic `notarytool submit --wait` against a freshly-built debug bundle returns `status: Accepted`
- **Kaan-action-required activation steps (after Francesco resolves):**
  1. Export Developer ID Application cert from Keychain Access → `.p12` with strong passphrase
  2. `base64 -i cert.p12 | tr -d '\n'` → paste into GitHub Actions secret `APPLE_DEVELOPER_ID_P12_BASE64`
  3. Paste passphrase into `APPLE_DEVELOPER_ID_PASSWORD`
  4. Set `APPLE_TEAM_ID` (10-char team ID from Apple Developer portal → Membership)
  5. Set `APPLE_API_KEY_ID = URMDRP5M3P`, `APPLE_API_KEY_ISSUER = 3f60cc6b-df70-4ff8-9ceb-865dac6c1b4b`
  6. Download .p8 from App Store Connect → Users and Access → Keys (one-time download) → `base64 -i AuthKey_URMDRP5M3P.p8 | tr -d '\n'` → paste into `APPLE_API_KEY_P8`
  7. Re-trigger `workflow_dispatch` with `dry_run: false` for end-to-end rehearsal
- **Resolution log:** [empty — append `<date> — resolved by <action>` when closed]

## Blocker B — SignPath OSS Foundation application [Kaan-action Day-1]

- **Status:** UNKNOWN (per STATE blocker line 104 — assumed STILL outstanding from v0.1.0 Phase 1 carry-forward; re-file Day-1 of Phase 21)
- **Deferred to:** kaan-action-required
- **Owner:** Kaan
- **What's needed:** File application at https://signpath.io/foundation per `docs/signpath-application.md` (created in Task 3 of this plan)
- **Why blocking:** Without SignPath OSS approval, Windows MSI ships unsigned → SmartScreen hard-block on first launch on fresh non-dev Win 11 (per Pitfall 6, PITFALLS.md lines 148–172); reputation warning is acceptable for v1, hard-block is not
- **ETA:** ~1 week from filing (SignPath OSS SLA per PITFALLS.md P6)
- **Downstream block:** 21-04-PLAN.md windows sign step (`signpath/github-action-submit-signing-request@v1.2.0` step in `release.yml` `build-windows` job)
- **Workaround until resolved:** Plan 04 ships with `SIGNING_AVAILABLE=false` mock-sign path (already wired); secondary fallback per Pitfall 6 mitigation: Kaan-purchased EV cert (~$200/yr, instant SmartScreen reputation) — **budget gate, do NOT pre-purchase**, requires explicit Kaan approval
- **Verification when resolved:** SignPath dashboard shows project `vibemix-binaries` exists, status = approved; ticket ID recorded in this file under "Resolution log"; a synthetic `workflow_dispatch` run with `dry_run: false` returns `signed` artifact from `signpath/github-action-submit-signing-request@v1.2.0`
- **Day-1 file checklist:** see `docs/signpath-application.md`
- **Kaan-action-required activation steps (after SignPath approval):**
  1. Generate API token in SignPath dashboard → Project → API tokens → paste into GitHub Actions secret `SIGNPATH_API_TOKEN`
  2. Copy Organization ID from SignPath dashboard → Organization settings → paste into `SIGNPATH_ORGANIZATION_ID`
  3. Copy Project slug from Project settings → paste into `SIGNPATH_PROJECT_SLUG`
  4. Copy Signing policy slug from Signing policies → paste into `SIGNPATH_SIGNING_POLICY_SLUG`
  5. Append ticket ID + approval date below; re-trigger `workflow_dispatch` for rehearsal
- **Resolution log:** [empty — append `<date> — ticket #<id> approved` when closed]

## Status board

| Blocker | Owner | Filed | Approved | Unblocks |
|---------|-------|-------|----------|----------|
| A — Apple Developer Program Agreement update | Francesco | — | — | 21-03-PLAN.md (macOS sign + notarize) |
| B — SignPath OSS Foundation application | Kaan | TBD (Day-1 of Phase 21) | TBD (~1 week post-file) | 21-04-PLAN.md (Windows MSI sign) |

## Reference

- `.planning/STATE.md` — blocker section (carry-forward from v0.1.0)
- `.planning/research/PITFALLS.md` P5 (Apple Issuer ID coordination, lines 1051–1056) + P6 (SignPath OSS SLA, lines 148–172)
- `.planning/phases/21-sign-notarize-github-release-matrix/21-CONTEXT.md` — Decisions section
- `docs/signpath-application.md` — Day-1 SignPath OSS application checklist
- `.github/workflows/release.yml` — `detect-signing-mode` Wave 0 job (mock-signing fallback contract)
