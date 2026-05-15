# Phase 39 — Research

**Date:** 2026-05-15
**Mode:** gsd-autonomous fully

Final ship phase. Engineering surface is templating + pre-flight gates; actual customer-facing publishes are Kaan/Francesco-action.

## Existing infrastructure

| Surface | Path | Source |
|---------|------|--------|
| README hero hash sync gate | `tests/repo/test_readme_hero_hash_sync.py` | Phase 35 (shipped) |
| `assets/demo.mp4` placeholder | `assets/demo.mp4` (Kaan-action real file) | Phase 35 (shipped) |
| Discord webhook provisioner | `scripts/ops/discord_provision.py` | Phase 36 (shipped) |
| Day-zero rota doc | `docs/day-zero-rota.md` | Phase 36 (shipped) |
| Launch trigger sequence | `scripts/ops/launch_trigger.sh` | Phase 36 (shipped) |
| Signed-binary verifier | `scripts/dist/verify_signed.py --require-signed` | Phase 38 (engineering shipped) |
| Bravoh ops endpoint contract | `docs/bravoh-ops-endpoint.md` | Phase 36 (shipped) |
| Star quality seed protocol | `scripts/ops/seed_stars.md` | Phase 36 (shipped) |

## `cut_release.sh` pre-flight gates

The cutter MUST refuse to fire unless ALL of:

1. **Tag prefix:** matches `^v2\.1\.0-rc[0-9]+$` (P83 — no premature `v1.0.0`).
2. **Signed binaries:** `verify_signed.py --require-signed` exits 0 for every artifact in `dist/`.
3. **README hero hash:** `test_readme_hero_hash_sync.py` passes.
4. **Milestone audit:** `.planning/v2.1-MILESTONE-AUDIT.md` exists + status `passed` (Phase 37 dep).
5. **POC files:** `test_g5_poc_files_untouched.py` passes (P85 + AUDIT-06).
6. **Bundle ID:** `test_bundle_id_locked.py` passes (P63 + Phase 33 INSTALL-07 dep).

Failure mode: print which gate tripped + exit 1. The script never calls `gh release create` autonomously — it only validates the pre-flight surface; final invocation is Kaan-action.

## 4-channel social publisher

| Channel | Template | API |
|---------|----------|-----|
| Twitter / X | `scripts/launch/social_templates/twitter.txt.jinja` | `tweepy` or `gh api graphql` (TBD; deferred to Kaan-action publish path) |
| Instagram Reels (IT + EN) | `scripts/launch/social_templates/ig_{it,en}.txt.jinja` | Manual / Buffer-style (Francesco-action) |
| Reddit r/Bravoh + r/DJs | `scripts/launch/social_templates/reddit.txt.jinja` | `praw` (Kaan-action) |
| HN Show HN | `scripts/launch/social_templates/hackernews.txt.jinja` | Manual (Kaan-action) |

NACK window (P78):
- `publish_social_posts.py --dry-run` POSTs to Discord webhook preview.
- 5-minute window; if NACK received via Discord reaction (👎), abort.
- Auto-publish after 5 min if no NACK.

REAL publishing stays Kaan/Francesco-action — autonomous run only prepares + previews.

## Changelog auto-populator

Walks `.planning/phases/*/[PNN]-SUMMARY.md`, extracts:
- Phase number + name
- "What shipped" table
- "Deferred to Kaan-action" section if present

Emits markdown that slots into `scripts/launch/changelog_template.md`'s `{{ phase_summaries }}` block.

Also walks `.planning/milestones/v2.0-ROADMAP.md` for the v2.0 close summary.

## GitHub meta sync

`scripts/launch/sync_github_meta.sh`:
- `gh api repos/{owner}/{repo} -X PATCH -f description="..."` — sets description.
- `gh api repos/{owner}/{repo}/topics -X PUT -F names[]=...` — sets topics.
- Topics: `dj`, `ai`, `gemini`, `tauri`, `open-source`, `mascot`, `livekit`, `audio`, `vibemix`, `bravoh`.

Real org transfer to `bravoh/vibemix` is Kaan-action (GitHub org transfer flow).

## P85 — Phase 16 override expiry

STATE.md contains: "Phase 16 ear-test memory override accepted for v2.1 only (autonomous proxy gate via Phase 27 substitutes)."

SHIP-08 = grep gate that asserts:
- The override line is present (for traceability)
- A "expires post-v2.1" marker is present near it
- An exit hook in `cut_release.sh` reminds Kaan to remove the override post-RC bake

## Plan slice (preview for 39-PLAN.md)

8 plans:
1. `39-01` — `cut_release.sh` + 6 pre-flight gates (SHIP-01 / SHIP-06 / P83)
2. `39-02` — README hero `<video>` + feature matrix auto-sync + Bravoh footer (SHIP-02 / P68)
3. `39-03` — `publish_social_posts.py` + 4-channel templates + NACK window (SHIP-03 / P78)
4. `39-04` — Discord launch flow (`scripts/launch/post_discord_launch.py`) + pre-seed verify (SHIP-04 / P59)
5. `39-05` — `sync_github_meta.sh` + topics/description gate (SHIP-05)
6. `39-06` — Changelog template + auto-populator (SHIP-01 ext)
7. `39-07` — `launch-rotation.md` finalize + Kaan/Francesco/Bravoh coordination (SHIP-07 / P79)
8. `39-08` — Phase 16 override expiry gate + KAAN-ACTION-LEGAL final entries (SHIP-08 / P85)
