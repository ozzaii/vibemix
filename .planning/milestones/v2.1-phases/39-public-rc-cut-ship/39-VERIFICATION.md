---
status: human_needed
phase: 39
phase_name: Public RC Cut + Ship
milestone: v2.1
verified_at: 2026-05-16T00:00:00Z
plans_complete: 8
plans_total: 8
mode: gsd-autonomous fully
deferred_to_kaan_action: true
legal_capacity_carveout: false
customer_facing_publish_carveout: true
---

# Phase 39 — Verification

## Status: PASSED (engineering) + HUMAN_NEEDED (customer-facing publishes)

Autonomous engineering scope (cut_release.sh pre-flight gates, README hero + feature matrix auto-sync, 5 social templates + publisher + NACK window, Discord launch flow, GitHub meta SoT + script, changelog template + auto-populator, 24h launch rotation doc, Phase 16 override expiry gate + KAAN-ACTION-LEGAL §SHIP + §POST-RC-CLEANUP) is COMPLETE.

The six customer-facing publishes (gh release create, 4-channel social posts, Discord announcement, GitHub topics + repo transfer, 24h rotation execution, v1.0.0 cut decision after RC bake) are by design NEVER discharged autonomously — they live as countersigned protocols in `KAAN-ACTION-LEGAL.md §SHIP`.

## Plan Inventory

| Plan | Commit | Status |
|------|--------|--------|
| 39-01 | 67c3038 | ✅ cut_release.sh pre-flight gates (SHIP-01 / SHIP-06) |
| 39-02 | 456a609 | ✅ README hero <video> + feature matrix + Bravoh footer (SHIP-02 / P68) |
| 39-03 | 51f750f | ✅ publish_social_posts.py + 5 templates + NACK window (SHIP-03 / P78) |
| 39-04 | d29a4ef | ✅ post_discord_launch.py + aligned-community role (SHIP-04 / P59) |
| 39-05 | ce698aa | ✅ sync_github_meta.sh + topics/description SoT (SHIP-05) |
| 39-06 | cc9f39d | ✅ changelog template + auto-populator (SHIP-01 ext) |
| 39-07 | 13c3aeb | ✅ launch-rotation.md 24h coordination (SHIP-07 / P79) |
| 39-08 | d3ffc7a | ✅ KAAN-ACTION-LEGAL §SHIP + §POST-RC-CLEANUP (SHIP-08 / P85) |

## Test Suite Evidence

```
pytest tests/scripts/test_cut_release_preflight.py \
       tests/repo/test_readme_feature_matrix_sync.py \
       tests/scripts/test_publish_social_posts.py \
       tests/scripts/test_post_discord_launch.py \
       tests/scripts/test_sync_github_meta.py \
       tests/scripts/test_populate_changelog.py \
       tests/repo/test_launch_rotation_doc.py \
       tests/security/test_kaan_action_legal_ship.py \
       tests/repo/test_phase_16_override_expiry.py -q
91 passed in 13.13s
```

Regression check on adjacent phases (35 hero hash, 37 POC immutability, 38 KAAN-ACTION-LEGAL DIST-09/11, 33 bundle id): 25 passed.

## `cut_release.sh` dry-run (final pre-flight verification)

```
bash scripts/launch/cut_release.sh v2.1.0-rc1

[Gate 1] Tag prefix         PASS
[Gate 2] Signed binaries    FAIL  (dist/ empty; Phase 38 secrets pending — DIST-09 + DIST-11 legal-capacity carveouts)
[Gate 3] README hero hash   PASS
[Gate 4] Milestone audit    PASS  (verdict WIRED)
[Gate 5] POC files frozen   PASS
[Gate 6] Bundle ID locked   PASS

5/6 gates green. REFUSING TO PRINT cut command.
Gate 2 will flip green automatically once DIST-09 + DIST-11 ship + Phase 38 signing pipeline emits signed artifacts into dist/.
```

This is the **correct** behavior: the cutter refuses to fire until the external clock (Apple Developer Program Agreement + SignPath OSS Foundation approvals) discharges. No autonomous workaround attempted (P46 hard rule respected).

## Hard Gates (all green)

| Gate | Plan | Test |
|------|------|------|
| cut_release.sh refuses to fire on bad pre-flight | 39-01 | `test_cut_release_blocks_on_wrong_tag_prefix` + 10 more |
| cut_release.sh NEVER calls `gh release create` | 39-01 | `test_cut_release_does_not_call_gh_release_create_autonomously` |
| README hero auto-syncs with shipped phases | 39-02 | `test_readme_feature_matrix_in_sync` + 7 more |
| Social publisher refuses real publish without LAUNCH_REAL=1 | 39-03 | `test_real_mode_requires_launch_real_env_flag` |
| Social publisher NEVER touches platform APIs | 39-03 | `test_static_audit_no_platform_api_calls` |
| Discord post never autonomously fires | 39-04 | `test_real_requires_launch_real_env` + `test_real_requires_real_webhook_set` |
| P59 no paid-star language in announcement | 39-04 | `test_p59_no_paid_star_text_in_announcement` |
| GitHub meta sync refuses real call without GH_META_REAL=1 | 39-05 | `test_real_mode_requires_env_flag` |
| Topics list has all 10 required entries | 39-05 | `test_topics_list_includes_required_10` |
| Changelog auto-populator covers every v2.1 phase | 39-06 | `test_changelog_includes_every_v2_1_phase` |
| Changelog includes v2.0 close + Kaan-action list + honest "not in RC" | 39-06 | `test_changelog_includes_v2_0_close_section` + 2 more |
| Launch rotation doc covers 24h with assignments | 39-07 | `test_rotation_doc_covers_24_hours` + `test_rotation_doc_assigns_each_hour_*` |
| KAAN-ACTION-LEGAL §SHIP has all 6 entries | 39-08 | `test_ship_section_has_six_entries` |
| DIST-09 + DIST-11 carveouts preserved (Phase 38 contract) | 39-08 | `test_legal_capacity_carveouts_unchanged` |
| Phase 16 override expiry tracked in STATE.md + cutter reminder | 39-08 | `test_state_md_has_phase_16_override_line` + `test_cut_release_sh_reminds_to_remove_override` |

## Human-Needed Items

Per `KAAN-ACTION-LEGAL.md`:

**§SHIP — 6 customer-facing publishes (Kaan + Francesco):**
1. SHIP-CUT — `gh release create v2.1.0-rc1 --draft` (Kaan, blocked on Phase 38 secrets).
2. SHIP-TWEET — 4-channel social publish (Kaan: Twitter / HN / Reddit; Francesco: IG IT / IG EN).
3. SHIP-DISCORD — `#announcements` real webhook post (Kaan).
4. SHIP-TRANSFER — `sync_github_meta.sh --real` + GitHub org transfer to `bravoh/vibemix` (Kaan).
5. SHIP-ROTATE — 24h hourly monitoring rota execution (Kaan + Francesco + Bravoh-team).
6. SHIP-V1-DECISION — Cut v1.0.0 / cycle RC2 / pause after ~2-wk bake (Kaan, separate phase).

**§POST-RC-CLEANUP — 3 cleanup items (Kaan):**
- Phase 16 ear-test override expiry (P85) — remove STATE.md line after RC bake.
- Bravoh-funnel utm_* attribution verification.
- v2.2 backlog grooming (Mixxx OSC, Rekordbox, ProDJ Link, stores, more i18n).

## Verdict

Engineering scaffold: PASSED.
Customer-facing publish discharge: HUMAN_NEEDED — NEVER autonomously discharged.

Phase 39 is the final v2.1 engineering phase. **v2.1 "The Unified Cut" milestone is engineering-complete.** Ready for the lifecycle audit → complete → cleanup sequence. Once Phase 38 secrets land (DIST-09 Francesco-action + DIST-11 Kaan-action), the cutter Gate 2 flips green and the real v2.1.0-rc1 cut is one Kaan-click away.
