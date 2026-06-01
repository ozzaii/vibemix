# CODEX_READY: Product Posture Docs Cleanup

Date: 2026-06-01
Verifier: Codex
Package: Package 0I - Product Posture Docs Cleanup
Suggested commit: `docs(product): align public posture with managed service`
Decision: LAND as public/product documentation posture cleanup. This is not a
release claim.

## Classification

LAND:

- `README.md`
- `PRODUCT.md`
- `.planning/PROJECT.md`
- `.planning/handoffs/2026-05-30-VIBEMIX-KNOWBOOK.md`
- `docs/code-signing-policy.md`
- `docs/landing/index.html`
- `docs/launch-prep/LAUNCH-SEQUENCE.md`
- `docs/launch-prep/OUTREACH-CALENDAR.md`
- `docs/launch-prep/SHOT-LIST.md`
- `docs/launch/github-meta.md`
- `docs/launch/nda-meturavers.md`
- `docs/launch/partner-brief-meturavers.md`
- `docs/launch/partner-brief.md`
- `docs/launch/partner-capabilities-short.md`
- `docs/launch/partner-capabilities.md`
- `docs/release-process.md`
- `docs/setup-github-repo.md`
- `docs/signing-windows.md`
- `docs/signpath-application.md`

HOLD/DROP:

- Do not bundle this with product source changes.
- Do not make a public product-release claim from this packet.
- Launch collateral remains held by `CODEX_HOLD-launch-collateral.md`; this
  packet only verifies current wording posture for the listed docs.

## Current Evidence

Docs posture tests:

```text
uv run pytest -q tests/repo/test_readme_shape.py tests/repo/test_readme_feature_matrix_sync.py tests/repo/test_oss_presence.py tests/launch/test_launch_docs.py tests/install/test_windows_smartscreen_doc.py
....................................................................     [100%]
68 passed in 0.46s
```

Stale OSS/free/release-claim grep:

```text
rg -n "free, open-source|free open-source|free/open-source|Free, open-source|free · open-source|free · open source|first open-source release|first OSS|Bravoh's first OSS|Bravoh's first open-source|SignPath OSS|OSS-program|OSS launch|Open source under Apache|Open-source AI co-host|open-source AI co-host|open source AI co-host|absorbed by Bravoh|50 €/month|free code signing|OSS eligibility|shipping today|signed and notarized, shipping|ships signed|macOS .*today|Windows ships|current signed/notarized|current signed and notarized|current signed \+ notarized|runs local on macOS today|What's already shipping" README.md PRODUCT.md docs/landing docs/launch docs/launch-prep docs/signpath-application.md docs/code-signing-policy.md docs/release-process.md docs/signing-windows.md docs/setup-github-repo.md .planning/PROJECT.md .planning/handoffs/2026-05-30-VIBEMIX-KNOWBOOK.md
```

Result: one internal historical planning line remains in
`.planning/handoffs/2026-05-30-VIBEMIX-KNOWBOOK.md:706`:

```text
Start the external clock TODAY -- it's the longest pole, pure waiting
```

This is not a public "shipping today" or current release claim. No active
public-facing false-release or old OSS-first positioning hit was found in the
checked docs.

Diff hygiene:

```text
git diff --check -- README.md PRODUCT.md .planning/PROJECT.md .planning/handoffs/2026-05-30-VIBEMIX-KNOWBOOK.md docs/code-signing-policy.md docs/landing/index.html docs/launch-prep/LAUNCH-SEQUENCE.md docs/launch-prep/OUTREACH-CALENDAR.md docs/launch-prep/SHOT-LIST.md docs/launch/github-meta.md docs/launch/nda-meturavers.md docs/launch/partner-brief-meturavers.md docs/launch/partner-brief.md docs/launch/partner-capabilities-short.md docs/launch/partner-capabilities.md docs/release-process.md docs/setup-github-repo.md docs/signing-windows.md docs/signpath-application.md
```

Result: clean.

Package ledger:

```text
uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary
OK: 5566 dirty paths covered by .planning/handoffs/2026-05-31-package-checklist.md; 3 generated launch previews ignored.
OK: every dirty path is assigned to an Include/Hold lane.
```

## Source Checks

- Product posture is now "managed/commercial service with client licensing
  disclosure", not "fully open-source release constrains product decisions".
- Docs still avoid claiming the product is fully released. The latest signed
  DMG proof now lives in `CODEX_PACKAGE_SWEEP_STATUS.md`, while live DJ
  acceptance and launch collateral remain open.
- Current launch collateral remains a separate HOLD because marketing/media
  wording needs a full pass before public use.

## Remaining Risk

Before final release, re-run this packet's grep/test set after launch collateral
is rewritten and after latest-code signing/notarization is complete.
