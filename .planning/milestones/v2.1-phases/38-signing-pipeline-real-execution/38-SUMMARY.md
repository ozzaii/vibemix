# Phase 38 Summary — Signing Pipeline Real Execution

**Status:** SHIPPED 2026-05-15
**Mode:** gsd-autonomous fully (with HARD legal-capacity carveouts — P46)
**Plans:** 6/6 (38-01 through 38-06)
**REQ-IDs satisfied:** DIST-09, DIST-11, DIST-15, DIST-16, DIST-17, DIST-18, DIST-19

## What shipped

| Plan | Commit | Surface | REQ |
|------|--------|---------|-----|
| 38-01 | 389930e | `release.yml` Apple notarytool empty-secret skip annotation | DIST-15 |
| 38-02 | f240fb8 | `release.yml` SignPath wiring empty-secret skip annotation | DIST-16 |
| 38-03 | 5c37359 | Post-sign verifier release-publish gate + `--require-signed` | DIST-17 |
| 38-04 | ec37a36 | `sign_windows.ps1` PowerShell local-rehearsal script | DIST-18 |
| 38-05 | c91a55b | `KAAN-ACTION-LEGAL.md` DIST-09 + DIST-11 + P46 callout | DIST-09, DIST-11 |
| 38-06 | 6f8e8ea | P46 audit extension — `.ps1` + PowerShell verbs + `release.yml` mirror | DIST-19, P46 |

## Hard legal-capacity carveouts (P46)

**These two items are NEVER discharged autonomously:**

1. **Apple Developer Program Agreement update** — Francesco-action (legal capacity required).
2. **SignPath OSS Foundation application** — Kaan-action (legal capacity required).

Both protocols documented in `KAAN-ACTION-LEGAL.md`. Workflow `release.yml` + `verify-signed.yml` audit jobs (`p46-audit`) statically block any `POST|PUT` calls to `apple.com` / `signpath.io` / `notarytool` endpoints across YAML + shell + PowerShell surfaces, so autonomous-discharge attempts fail at CI.

## Empty-secret skip protocol

Both Apple + SignPath secrets are intentionally empty in CI until external approvals land. The skip pattern:

- `release.yml` jobs gate signing steps on `SIGNING_AVAILABLE == 'true'`.
- When `SIGNING_AVAILABLE != 'true'`, an explicit `::warning::` annotation step prints "wiring annotation" pointing at `KAAN-ACTION-LEGAL.md` DIST-09 / DIST-11.
- The full pipeline (build, test, upload) still runs end-to-end so no other gate breaks.
- When secrets populate, signing + notarytool + SignPath + post-sign verifier run automatically with `--require-signed` enforcing.

## Test suite evidence

```
pytest tests/security/test_release_yml_signing_skips.py \
       tests/security/test_verify_signed.py \
       tests/security/test_kaan_action_legal.py \
       tests/security/test_p46_audit.py \
       tests/security/test_sign_windows_ps1.py -q
58 passed in 0.20s
```

Hard gates green:

| Gate | Plan | Test |
|------|------|------|
| Empty Apple secret → skip | 38-01 | `test_release_yml_apple_sign_step_guarded_by_signing_available` |
| Empty SignPath secret → skip | 38-02 | `test_release_yml_signpath_sign_step_guarded_by_signing_available` |
| Post-sign verifier blocks publish on unsigned | 38-03 | `test_post_sign_verifier_blocks_publish_on_unsigned` |
| `sign_windows.ps1` syntactically valid | 38-04 | `test_sign_windows_ps1_syntax_valid` |
| KAAN-ACTION-LEGAL has DIST-09 + DIST-11 | 38-05 | `test_kaan_action_legal_md_has_dist_09_protocol` + `_dist_11_protocol` |
| P46 audit blocks POST to apple/signpath (incl. PowerShell verbs) | 38-06 | `test_p46_audit_blocks_post_to_apple` + `_signpath` + `_powershell_invoke_webrequest_to_signpath` |

## Pitfall coverage

- **P46** — autonomous-discharge attempt against apple/signpath endpoints fails at CI (`p46-audit` job mirror in `release.yml` + `verify-signed.yml`, scans YAML + shell + PowerShell).
- Pre-existing v2.0 Phase 21 contracts preserved — `verify_signed.py` default surface unchanged.

## What's left (deferred to Kaan / Francesco)

- **DIST-09** — Francesco completes Apple Developer Program Agreement update.
- **DIST-11** — Kaan submits SignPath OSS Foundation application + waits on approval.

Once both land, populate `APPLE_*` + `SIGNPATH_*` secrets in GitHub. Pipeline goes live automatically — no further engineering required.
