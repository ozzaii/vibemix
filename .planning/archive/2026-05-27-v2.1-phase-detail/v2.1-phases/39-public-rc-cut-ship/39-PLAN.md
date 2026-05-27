# Phase 39 — Public RC Cut + Ship — PLAN

**Status:** Ready to execute (after Phases 33, 37 land + Phase 38 secrets staging)
**Plans:** 8 (39-01 → 39-08)
**Mode:** `gsd-autonomous fully` — scripts + templates + gates in scope; actual cut + posts + transfer = Kaan/Francesco-action

---

## Cross-cutting rules

1. **NEVER autonomously call `gh release create`** — `cut_release.sh` is pre-flight only; real cut is Kaan-action.
2. **NEVER autonomously POST to Twitter / IG / Reddit / HN** — content prepared; publish is Kaan/Francesco-action.
3. **Tag prefix `v2.1.0-rc[0-9]+` is sacred** (P83 — no premature `v1.0.0`).
4. **POC files (`cohost*.py`, `mascot.html`) UNTOUCHED.**
5. **Atomic commits per plan.**

---

## Plan 39-01 — `cut_release.sh` + 6 pre-flight gates (SHIP-01 / SHIP-06 / P83)

**REQ-IDs:** SHIP-01, SHIP-06

**Edits:**
- NEW `scripts/launch/cut_release.sh`:
  - argparse-style positional: tag name.
  - Pre-flight gates (all must pass; print which failed):
    1. Tag prefix regex `^v2\.1\.0-rc[0-9]+$`.
    2. `verify_signed.py --require-signed` for every `dist/*.{dmg,msi,exe}`.
    3. `pytest tests/repo/test_readme_hero_hash_sync.py`.
    4. `.planning/v2.1-MILESTONE-AUDIT.md` exists + grep frontmatter `status: passed`.
    5. `pytest tests/repo/test_g5_poc_files_untouched.py`.
    6. `pytest tests/security/test_bundle_id_locked.py`.
  - On success: prints "ALL GATES PASS — Kaan, run `gh release create ${TAG} --draft ...`" with full command preview but DOES NOT EXECUTE.
  - HARD GUARD: even with `--really`, no `gh release create` invocation autonomously.
- NEW `tests/scripts/test_cut_release_preflight.py`:
  - `test_cut_release_blocks_on_wrong_tag_prefix`.
  - `test_cut_release_blocks_on_missing_milestone_audit`.
  - `test_cut_release_blocks_on_unsigned_binary` (synthetic).
  - `test_cut_release_does_not_call_gh_release_create_autonomously` — script audit.
  - `test_cut_release_prints_dry_run_command_on_pass`.

**Acceptance:** all new tests pass.

---

## Plan 39-02 — README hero + feature matrix + Bravoh footer (SHIP-02 / P68)

**REQ-IDs:** SHIP-02

**Edits:**
- `README.md`:
  - Replace hero section with HTML5 `<video>` block embedding `assets/demo.mp4` (file is placeholder until Kaan-action lands real cut).
  - Add `<!-- AUTO-GEN: feature-matrix START -->` / `<!-- AUTO-GEN: feature-matrix END -->` markers around the feature matrix.
  - Add Bravoh-funnel footer link if not already present.
- NEW `scripts/launch/sync_feature_matrix.py`:
  - Walks `.planning/ROADMAP.md` for `- [x] **Phase N: Name**` completed entries.
  - Emits markdown table mapping phase → shipped surfaces.
  - Writes between AUTO-GEN markers in `README.md`.
- NEW `tests/repo/test_readme_feature_matrix_sync.py`:
  - `test_readme_has_auto_gen_markers`.
  - `test_feature_matrix_includes_all_completed_phases`.
  - `test_bravoh_footer_link_present_and_active`.

**Acceptance:** all new tests pass; `README.md` renders cleanly.

---

## Plan 39-03 — `publish_social_posts.py` + 4-channel templates + NACK window (SHIP-03 / P78)

**REQ-IDs:** SHIP-03

**Edits:**
- NEW `scripts/launch/publish_social_posts.py`:
  - argparse: `--dry-run` (default) / `--real`.
  - Loads 4 templates from `scripts/launch/social_templates/`.
  - Renders via simple `{{ key }}` substitution.
  - `--dry-run`: POSTs each rendered post to Discord webhook preview channel.
  - 5-min NACK window via embed reaction polling.
  - `--real`: refuses to fire unless `cut_release.sh` pre-flight passed AND Kaan flag `LAUNCH_REAL=1` is in env.
- NEW templates:
  - `scripts/launch/social_templates/twitter.txt.jinja`
  - `scripts/launch/social_templates/ig_it.txt.jinja`
  - `scripts/launch/social_templates/ig_en.txt.jinja`
  - `scripts/launch/social_templates/reddit_djs.txt.jinja`
  - `scripts/launch/social_templates/hackernews.txt.jinja`
- NEW `tests/scripts/test_publish_social_posts.py`:
  - `test_dry_run_does_not_post_real_channels`.
  - `test_templates_render_without_missing_keys`.
  - `test_nack_window_blocks_publish_on_negative_reaction`.
  - `test_real_mode_requires_launch_real_env_flag`.

**Acceptance:** all new tests pass; `--dry-run` produces 4 preview posts.

---

## Plan 39-04 — Discord launch flow (SHIP-04 / P59)

**REQ-IDs:** SHIP-04

**Edits:**
- NEW `scripts/launch/post_discord_launch.py`:
  - Reads `scripts/ops/seed_stars.md` aligned-community protocol (Phase 36 — already shipped).
  - POSTs to `#announcements` via Discord webhook.
  - Includes pinned community role mention (configurable via env).
  - DRY-RUN mode that POSTs to a preview channel.
  - `--real` requires `LAUNCH_REAL=1` env.
- NEW `tests/scripts/test_post_discord_launch.py`:
  - `test_dry_run_uses_preview_channel`.
  - `test_announcement_pings_aligned_community_role`.
  - `test_real_requires_launch_real_env`.
  - `test_p59_no_paid_star_text_in_announcement` — grep against banned terms ("buy stars", "pay for review").

**Acceptance:** all new tests pass.

---

## Plan 39-05 — `sync_github_meta.sh` + topics/description gate (SHIP-05)

**REQ-IDs:** SHIP-05

**Edits:**
- NEW `scripts/launch/sync_github_meta.sh`:
  - `gh api repos/{owner}/{repo} -X PATCH -f description="$DESCRIPTION"`.
  - `gh api repos/{owner}/{repo}/topics -X PUT` with `dj`, `ai`, `gemini`, `tauri`, `open-source`, `mascot`, `livekit`, `audio`, `vibemix`, `bravoh`.
  - HARD GUARD: prints what it would do unless `--real` AND `GH_META_REAL=1` in env.
- NEW `docs/launch/github-meta.md` — description + topics canonical source-of-truth.
- NEW `tests/scripts/test_sync_github_meta.py`:
  - `test_sync_github_meta_dry_run_does_not_call_gh_api`.
  - `test_topics_list_includes_required_10`.
  - `test_description_under_350_chars`.

**Acceptance:** all new tests pass.

---

## Plan 39-06 — Changelog template + auto-populator (SHIP-01 ext)

**REQ-IDs:** SHIP-01

**Edits:**
- NEW `scripts/launch/changelog_template.md` — covers v2.0 close, v2.1 buckets, KAAN-ACTION items, honest "not in RC" list, {{ phase_summaries }} block.
- NEW `scripts/launch/populate_changelog.py`:
  - Walks `.planning/phases/*/[PNN]-SUMMARY.md`.
  - Extracts phase number + name + "What shipped" table.
  - Pulls v2.0 close from `.planning/milestones/v2.0-ROADMAP.md`.
  - Renders into `scripts/launch/changelog_template.md` and writes `CHANGELOG-v2.1.0-rc1.md` at repo root.
- NEW `tests/scripts/test_populate_changelog.py`:
  - `test_changelog_includes_every_v2_1_phase`.
  - `test_changelog_includes_v2_0_close_section`.
  - `test_changelog_includes_kaan_action_list`.
  - `test_changelog_honest_not_in_rc_section_present`.

**Acceptance:** all new tests pass; populator emits a valid changelog.

---

## Plan 39-07 — `launch-rotation.md` finalize + 24h coordination (SHIP-07 / P79)

**REQ-IDs:** SHIP-07

**Edits:**
- NEW `docs/launch-rotation.md`:
  - Builds on `docs/day-zero-rota.md` (Phase 36 — shipped).
  - 24h Kaan/Francesco/Bravoh hourly schedule.
  - Per-hour checklist: Discord triage, GitHub Issues, healthz, star velocity.
  - Escalation paths for: showstopper bug, abuse / spam, traffic spike.
- NEW `tests/repo/test_launch_rotation_doc.py`:
  - `test_rotation_doc_covers_24_hours`.
  - `test_rotation_doc_assigns_each_hour_to_kaan_francesco_or_bravoh`.
  - `test_rotation_doc_includes_escalation_paths`.

**Acceptance:** new tests pass.

---

## Plan 39-08 — Phase 16 override expiry gate + KAAN-ACTION-LEGAL final entries (SHIP-08 / P85)

**REQ-IDs:** SHIP-08

**Edits:**
- `KAAN-ACTION-LEGAL.md`:
  - Add §SHIP — entries for SHIP-CUT, SHIP-TWEET, SHIP-DISCORD, SHIP-TRANSFER, SHIP-ROTATE, SHIP-V1-DECISION.
  - Add §POST-RC-CLEANUP — Phase 16 override expiry (P85), Bravoh-funnel verification, v2.2 backlog grooming.
- NEW `tests/security/test_kaan_action_legal_ship.py`:
  - `test_ship_section_has_six_entries`.
  - `test_post_rc_cleanup_section_has_phase_16_override`.
  - `test_legal_capacity_carveouts_unchanged` (DIST-09 + DIST-11 still present and intact).
- NEW `tests/repo/test_phase_16_override_expiry.py`:
  - `test_state_md_has_phase_16_override_line`.
  - `test_state_md_has_expires_post_v2_1_marker`.
  - `test_cut_release_sh_reminds_to_remove_override` — grep `cut_release.sh` output for "Phase 16 override cleanup reminder".

**Acceptance:** all new tests pass; KAAN-ACTION-LEGAL final.

---

## Hard gates (collected from CONTEXT)

| Gate | Plan |
|------|------|
| `cut_release.sh` refuses to fire on bad pre-flight | 39-01 |
| README hero auto-syncs with shipped phases | 39-02 |
| Social publisher refuses real publish without `LAUNCH_REAL=1` | 39-03 |
| Discord post never autonomously fires | 39-04 |
| GitHub meta sync refuses real call without `GH_META_REAL=1` | 39-05 |
| Changelog auto-populator covers every v2.1 phase + v2.0 close | 39-06 |
| Launch rotation doc covers 24h with assignments | 39-07 |
| Phase 16 override expiry tracked in STATE.md + reminded by cutter | 39-08 |

Each plan = one atomic commit. Final verification = `bash scripts/launch/cut_release.sh v2.1.0-rc1` (dry-run) prints all gates and lists the `gh release create` command preview without executing.
