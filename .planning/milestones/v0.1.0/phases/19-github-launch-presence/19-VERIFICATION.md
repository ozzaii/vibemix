---
gsd_verification_version: 1.0
phase: 19
phase_name: GitHub Launch Presence
status: human_needed
verified_at: 2026-05-13
---

# Phase 19 Verification

## Status

`human_needed` — all autonomous deliverables shipped (README + 5 OSS hygiene files + 4 templates + architecture SVG + hero placeholder + repo scrub + LFS + metadata + 84 tests). Pending Kaan-side: real artwork (hero PNG, controller logos, screenshots, demo GIF), `bravoh` org + repo transfer, `scripts/dist/configure_repo.sh --apply` execution.

## Success Criteria Coverage

| # | ROADMAP Criterion | Status | Evidence |
|---|---|---|---|
| 1 | README hero + tagline + value prop + demo video/GIF | SHIPPED w/ placeholders | `README.md` hero references `docs/assets/hero.png` (1280×640 amber gradient placeholder), demo references `docs/assets/demo-placeholder.gif` (real shoot TODO). Tagline + value prop landed verbatim from CONTEXT. |
| 2 | Install section + one-click buttons + install GIFs <60s | SHIPPED | Install table links to GitHub Releases. Install GIFs deferred to post-binary-ship. |
| 3 | Controllers grid + FAQ 8-12 covering privacy/data/cost/Linux/Gemini Live/OSS scope | SHIPPED | 10-controller 5×2 grid; 12-question FAQ (verbatim from CONTEXT Area 3). |
| 4 | OSS hygiene: Apache 2.0 LICENSE / NOTICE / TRADEMARKS / SECURITY / COC / CONTRIBUTING w/ DCO / 3 issue templates | SHIPPED | LICENSE present (pre-existing); CONTRIBUTING.md (DCO + 3 paths); CODE_OF_CONDUCT.md (Contributor Covenant 2.1); SECURITY.md; NOTICE; TRADEMARKS.md; 4 issue templates (bug/feature/new_controller/config); PR template. |
| 5 | Repo scrub: no scratch / no .bak / no .env / no large binaries / topics+description | SHIPPED | `_test_*.py` + `sprite-*.png` deleted; `.gitattributes` LFS rule for mascot GLB; `.github/repo-config.yml` (description + 10 topics + merge policy); `tests/repo/test_repo_scrub.py` + `test_repo_metadata.py` CI gates. |
| 6 | Custom OG / social-preview image renders on X/Discord/Slack | DEFERRED | OG image is a GitHub UI-only setting (cannot be code-controlled). Bravoh design lead delivers PNG; Kaan uploads via repo Settings. |

## Automated Gates (all green)

- pytest tests/repo/test_repo_scrub.py + test_repo_metadata.py: 19 passed (Plan 19-01)
- pytest tests/repo/test_oss_hygiene.py: 20 passed (Plan 19-02)
- pytest tests/repo/test_docs_assets.py: 21 passed (Plan 19-04)
- pytest tests/repo/test_readme_shape.py: 44 passed (Plan 19-03)
- **Total Phase 19 tests: 104 passed**
- Architecture SVG uses ONLY CDJ Whisper v5 palette literals (no Mermaid)
- README anti-slop gate: zero banned phrases
- README references all 10 controllers + all 12 FAQ Qs + all 5 asset paths
- Bravoh utm-tagged footer present
- POC files diff-untouched (cohost*.py / mascot.html / mocks/)

## Human Verification Pending

1. **Bravoh org + repo transfer (GH-01):** Create `bravoh` GitHub org (or use existing) and transfer/create `vibemix` repo. Kaan-side, GitHub UI work.
2. **Hero artwork:** Bravoh design lead delivers final `docs/assets/hero.png` (1280×640). Drops in place of the generated placeholder.
3. **Demo video/GIF:** Kaan + Francesco shoot 30-45s during a real set, post-binary-ship. Drops to `docs/assets/demo-placeholder.gif` (or .mp4 + GIF dual).
4. **Controller logos:** 10 PNGs into `docs/assets/controllers/<slug>.png` (slugs match `src/vibemix/midi/profiles/*.json` names).
5. **Screenshot PNGs:** 5 captures into `docs/assets/screenshots/{wizard,mode-picker,voice-picker,session,recordings}.png` post-binary-ship.
6. **Custom OG image:** Bravoh design lead delivers PNG; Kaan uploads via GitHub repo Settings → Social preview.
7. **PGP key:** Bravoh ops generates a PGP keypair for `security@bravoh.com`; fingerprint pastes into SECURITY.md.
8. **Apply repo metadata:** Kaan runs `bash scripts/dist/configure_repo.sh --apply` once to push description + 10 topics + merge policy to GitHub.
9. **LFS migration:** Kaan runs `git lfs install --local && git lfs migrate import --include="tauri/ui/assets/mascot/*.glb"` one-time.
10. **Per-clone pre-commit hook:** Kaan runs `ln -sf ../../scripts/hooks/pre-commit-no-binaries.sh .git/hooks/pre-commit`.

## Files Delivered

- `README.md` (full rewrite, ~7 KB, 12 sections, 12 FAQ, 10 controllers)
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `NOTICE`, `TRADEMARKS.md`
- `.github/repo-config.yml`, `.github/pull_request_template.md`
- `.github/ISSUE_TEMPLATE/{bug_report,feature_request,new_controller,config}.yml`
- `scripts/dist/configure_repo.sh`, `scripts/dist/gen_notice.py`, `scripts/dist/render_architecture.py`, `scripts/dist/render_hero_placeholder.py`
- `scripts/hooks/pre-commit-no-binaries.sh`
- `docs/midi-mapping.md`
- `docs/assets/architecture.svg`, `docs/assets/hero.png`, `docs/assets/demo-placeholder.gif`
- `docs/assets/controllers/.gitkeep`, `docs/assets/screenshots/.gitkeep`
- `tests/repo/test_repo_scrub.py`, `test_repo_metadata.py`, `test_oss_hygiene.py`, `test_docs_assets.py`, `test_readme_shape.py`
- `.gitattributes` (LFS rule for *.glb)
- 4 plan SUMMARYs (19-01 through 19-04)

## Requirements Coverage

| Req | Status | Plan |
|-----|---|---|
| GH-01 | DEFERRED (Kaan: create bravoh org) | — |
| GH-02 | SHIPPED w/ placeholder | 19-03 + 19-04 |
| GH-03 | SHIPPED w/ placeholder | 19-03 |
| GH-04 | SHIPPED | 19-03 |
| GH-05 | SHIPPED | 19-03 |
| GH-06 | SHIPPED | 19-03 |
| GH-07 | SHIPPED w/ placeholders | 19-03 |
| GH-08 | SHIPPED | 19-04 |
| GH-09 | SHIPPED | 19-03 |
| GH-10 | SHIPPED | 19-03 |
| GH-11 | SHIPPED | 19-03 |
| GH-12 | DEFERRED (GitHub UI-only) | — |
| GH-13 | SHIPPED | 19-02 |
| GH-14 | SHIPPED | 19-02 |
| GH-15 | SHIPPED | 19-02 |
| GH-16 | DEFERRED (Phase 18 release.yml produces; Kaan tags) | — |
| GH-17 | SHIPPED | 19-01 |
| GH-18 | SHIPPED | 19-01 |

15 of 18 GH-XX SHIPPED autonomously; 3 (GH-01, GH-12, GH-16) require Kaan-side GitHub UI actions or a real release tag.
