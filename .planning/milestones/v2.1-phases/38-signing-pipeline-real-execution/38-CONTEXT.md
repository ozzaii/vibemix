# Phase 38: Signing Pipeline Real Execution - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully — WITH explicit legal-capacity carveouts)

<domain>
## Phase Boundary

Real Apple notarytool + real SignPath GH Action wired into `release.yml`; signed binaries verifiable end-to-end. **The two legal-capacity human-signature submissions remain in `KAAN-ACTION-LEGAL.md` and are NEVER autonomously discharged.**

**Mapped REQ-IDs (7):** DIST-15 (Apple notarytool wiring), DIST-16 (SignPath GH Action wiring), DIST-17 (post-sign verifier — surface shipped in Phase 34, this phase activates with real creds), DIST-18 (`sign_windows.ps1` local-rehearsal), DIST-09 (Apple Dev Program Agreement — LEGAL CARVEOUT, Francesco-action), DIST-11 (SignPath OSS Foundation application — LEGAL CARVEOUT, Kaan-action), DIST-19 (Kaan sign+verify smoke).

**In scope (autonomous):**
- `release.yml` `xcrun notarytool` workflow scaffold — uses GitHub Secrets that DON'T EXIST YET (Kaan creates after Apple approves). Workflow defines `secrets.APPLE_DEVELOPER_ID` + `secrets.APPLE_ID_USERNAME` + `secrets.APPLE_ID_APP_PASSWORD` etc.
- `release.yml` SignPath GH Action workflow scaffold — uses placeholder secrets, defines `secrets.SIGNPATH_API_TOKEN` + project/cert config.
- Post-sign verifier activation — already scaffolded in Phase 34, this phase activates it once real signing artifacts exist.
- `scripts/dist/sign_windows.ps1` — PowerShell local-rehearsal script.
- KAAN-ACTION-LEGAL.md DIST-09 + DIST-11 entries with detailed protocols.
- CI bash audit P46 grep — verify no `POST`/`PUT` to apple/signpath/notarytool endpoints in any script (Phase 34 already started this; Phase 38 extends with stricter coverage).

**Out of scope (autonomous; HARD CARVEOUTS):**
- ACTUAL Apple Developer Program Agreement update — FRANCESCO-ACTION (legal capacity, Pitfall P46).
- ACTUAL SignPath OSS Foundation application — KAAN-ACTION (legal capacity, Pitfall P46).
- ACTUAL Apple Dev ID cert generation + GitHub Secret upload — Kaan-action after Apple approves.
- ACTUAL SignPath cert generation + GitHub Secret upload — Kaan-action after SignPath approves.
- ACTUAL `bash tauri/src-tauri/spike/sign-and-test.sh` run on signed binary (DIST-19) — Kaan-action manual smoke once signing live.

**Pure out of scope:**
- Linux signing (Linux excluded from v1).
- Sigstore / cosign signing.
- Reproducible builds (v2.2).
- Code-signing for third-party plugins (no plugins in v1).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion (locked per gsd-autonomous fully)

Grounded in:
- ROADMAP Phase 38 verbatim
- REQUIREMENTS.md DIST-09, DIST-11, DIST-15..19
- Pitfall P46 (legal-capacity carveouts NEVER autonomous)
- v2.0 Phase 21 CI scaffold + Phase 34 verifier surface (shipped)
- Memory `feedback_autonomous_no_grey_area_pause` — only legal-capacity + privacy pause
- STATE.md: "two legal-capacity carveouts (Apple Dev Agreement + SignPath OSS Foundation application) — autonomous discharge FORBIDDEN"

### Apple notarytool wiring (DIST-15)
- `release.yml` workflow step (macOS build leg) runs:
  ```
  xcrun notarytool submit dist/vibemix.dmg \
    --apple-id "$APPLE_ID_USERNAME" \
    --password "$APPLE_ID_APP_PASSWORD" \
    --team-id "$APPLE_TEAM_ID" \
    --wait
  xcrun stapler staple dist/vibemix.dmg
  xcrun stapler validate dist/vibemix.dmg
  ```
- Secrets required (Kaan creates AFTER Apple approves): `APPLE_DEVELOPER_ID` (cert), `APPLE_ID_USERNAME`, `APPLE_ID_APP_PASSWORD`, `APPLE_TEAM_ID`.
- Pre-flight CI check: if `APPLE_ID_USERNAME` is empty, workflow skips with explicit log line — does NOT fail. This keeps the workflow valid before Apple approves.

### SignPath wiring (DIST-16)
- `release.yml` workflow step (Windows build leg) uses official `signpath/github-action-submit-signing-request` Action.
- Inputs: organization-id, project-slug, signing-policy-slug, artifact-configuration-slug.
- Secrets required: `SIGNPATH_API_TOKEN`.
- Pre-flight check: skip if token empty, log "SignPath approval pending — see KAAN-ACTION-LEGAL.md DIST-11".

### Post-sign verifier (DIST-17)
- Activates Phase 34's `verify-signed.yml` surface.
- Adds release-publish gate: `release` workflow does NOT publish unless verifier passes.
- Verifier asserts: mac DMG has notarization ticket + valid signature; Windows MSI has Authenticode signature + SignPath chain validates.

### `sign_windows.ps1` local rehearsal (DIST-18)
- PowerShell script. Wraps SignPath CLI for local rehearsal.
- Inputs: `$SIGNPATH_API_TOKEN` env, MSI path.
- Output: signed MSI path + verification log.
- Lets Kaan rehearse the Windows signing flow on his machine BEFORE relying on CI (failure cost is high on launch day).

### Sign+verify smoke (DIST-19)
- `tauri/src-tauri/spike/sign-and-test.sh` exists from v2.0 OVERLAY-02 spike.
- Kaan runs it on the FIRST signed binary after CI signing goes live. Documented in KAAN-ACTION-LEGAL.md.
- Closes v2.0 OVERLAY-02 Wave-0 verdict.

### Legal-capacity carveouts (DIST-09, DIST-11 / P46)
- `KAAN-ACTION-LEGAL.md` already has the surface from Phases 34/35. Phase 38 ADDS:
  - **DIST-09 — Apple Developer Program Agreement update (FRANCESCO-ACTION)**: detailed protocol — login to developer.apple.com, accept Program License Agreement, complete entity update if needed. CANNOT be done autonomously (legal capacity).
  - **DIST-11 — SignPath OSS Foundation application (KAAN-ACTION)**: submit at signpath.org/foundation, ~1-week SLA, fill open-source-project form. CANNOT be done autonomously.
- Both have countersign protocol + status checklist.

### CI bash audit P46 (extending Phase 34)
- Phase 34 already shipped `verify_signed.py` with P46 grep.
- Phase 38 extends to ALL workflow files + scripts: grep -E `POST|PUT` against `apple.com|signpath.io|notarytool`. CI fails on match.
- Test: synthetic workflow with forbidden POST → CI fails. Without → passes.

### Test discipline
- `test_release_yml_skip_on_empty_apple_secret` — synthetic workflow run, asserts skip.
- `test_release_yml_skip_on_empty_signpath_secret`
- `test_p46_audit_blocks_post_to_apple` — synthetic script with forbidden POST → audit fails.
- `test_post_sign_verifier_blocks_publish_on_unsigned` — synthetic unsigned artifact → publish fails.
- `test_sign_windows_ps1_syntax_valid` — PowerShell parse only (no execution).
- `test_kaan_action_legal_md_has_dist_09_dist_11_protocols`.

### Frontend convention
- N/A — Phase 38 is CI + scripts only.

</decisions>

<code_context>
## Existing Code Insights

- **v2.0 Phase 21 (shipped)** — `release.yml` CI scaffold with placeholders for Apple + SignPath.
- **Phase 34 (just shipped)** — `verify_signed.py` + `verify-signed.yml` + P46 audit (initial coverage).
- **v2.0 OVERLAY-02 spike** — `tauri/src-tauri/spike/sign-and-test.sh` (smoke script).
- **`KAAN-ACTION-LEGAL.md`** — exists with entries from Phases 27/29/34/35.
- **GitHub Secrets** — none of the signing-related secrets exist yet (Kaan creates after Apple/SignPath approve).
- **Memory** — Pitfall P46: NEVER autonomously POST/PUT to apple/signpath/notarytool endpoints.

Codebase maps under `.planning/codebase/` feed plan-phase research.

</code_context>

<specifics>
## Specific Ideas

- **Workflow must stay valid before Apple/SignPath approve** — empty-secret skip pattern.
- **PowerShell local-rehearsal script** — high failure cost on launch day, Kaan should test locally first.
- **CI bash audit is the safety net** — grep ensures autonomous mode can't accidentally discharge legal-capacity items.
- **~1-week SLA on SignPath** — start application Day 1, not after engineering complete.
- **Apple Dev Agreement is Francesco-action** — Francesco is cofounder with legal entity capacity.

</specifics>

<deferred>
## Deferred Ideas

- **Linux signing** — out of scope.
- **Sigstore / cosign** — v2.2 stretch.
- **Reproducible builds** — v2.2.
- **Plugin signing** — no plugins in v1.

</deferred>

<kaan_action_required>
## Critical: Kaan/Francesco-Action Required (KAAN-ACTION-LEGAL.md)

**LEGAL-CAPACITY CARVEOUTS — AUTONOMOUS DISCHARGE FORBIDDEN (Pitfall P46):**

1. **DIST-09 (Francesco-action):** Apple Developer Program Agreement update via developer.apple.com login. ~10 minutes once Francesco logs in.
2. **DIST-11 (Kaan-action):** SignPath OSS Foundation application at signpath.org/foundation. ~1-week SLA from submission.

**KAAN-ACTION (post-approval, mechanical):**
3. Apple Dev ID cert generation + GitHub Secrets upload (`APPLE_DEVELOPER_ID`, `APPLE_ID_USERNAME`, `APPLE_ID_APP_PASSWORD`, `APPLE_TEAM_ID`).
4. SignPath cert generation + GitHub Secret upload (`SIGNPATH_API_TOKEN`).
5. `bash tauri/src-tauri/spike/sign-and-test.sh` smoke run on first signed binary (DIST-19).
6. `scripts/dist/sign_windows.ps1` local rehearsal (DIST-18).

Autonomous deliverables: workflow scaffolds + scripts + protocols + tests passing against synthetic fixtures. Real signing activates when Kaan/Francesco discharge legal-capacity items + drop secrets.
</kaan_action_required>
