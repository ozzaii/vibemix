# Phase 39 Summary — Public RC Cut + Ship

**Status:** SHIPPED 2026-05-16 (engineering scaffold; customer-facing publishes Kaan/Francesco-action)
**Mode:** gsd-autonomous fully
**Plans:** 8/8 (39-01 through 39-08)
**REQ-IDs satisfied:** SHIP-01, SHIP-02, SHIP-03, SHIP-04, SHIP-05, SHIP-06, SHIP-07, SHIP-08

## What shipped

| Plan | Commit | Surface | REQ |
|------|--------|---------|-----|
| 39-01 | 67c3038 | `scripts/launch/cut_release.sh` + 6 pre-flight gates | SHIP-01, SHIP-06 |
| 39-02 | 456a609 | README hero `<video>` + feature-matrix auto-sync + Bravoh footer | SHIP-02 |
| 39-03 | 51f750f | `publish_social_posts.py` + 5 channel templates + NACK window | SHIP-03 |
| 39-04 | d29a4ef | `post_discord_launch.py` + aligned-community role ping | SHIP-04 |
| 39-05 | ce698aa | `sync_github_meta.sh` + topics/description SoT | SHIP-05 |
| 39-06 | cc9f39d | Changelog template + auto-populator from phase summaries | SHIP-01 (ext) |
| 39-07 | 13c3aeb | `docs/launch-rotation.md` — 24h hourly schedule + escalation paths | SHIP-07 |
| 39-08 | d3ffc7a | KAAN-ACTION-LEGAL §SHIP (6 entries) + §POST-RC-CLEANUP (P85) | SHIP-08 |

## Scope split — autonomous vs Kaan/Francesco-action

**Autonomous (Phase 39 ships):**
- `cut_release.sh` pre-flight gates (NEVER calls `gh release create`).
- README hero + feature matrix (auto-syncs from ROADMAP).
- Social templates + publisher (POSTs to Discord preview only; platform APIs never called).
- Discord launch script (`--real` gated by `LAUNCH_REAL=1` env).
- GitHub meta script (`--real` gated by `GH_META_REAL=1` env).
- Changelog auto-populator from `.planning/phases/*/[NN]-SUMMARY.md`.
- Launch-rotation doc (24h schedule).
- Phase 16 override expiry tracking + KAAN-ACTION-LEGAL §SHIP + §POST-RC-CLEANUP.

**Kaan/Francesco-action (deferred — six items in §SHIP):**
1. **SHIP-CUT** — Kaan runs `gh release create v2.1.0-rc1 --draft ...` once Phase 38 secrets land.
2. **SHIP-TWEET** — Kaan posts Twitter/HN/Reddit; Francesco posts IG IT + IG EN.
3. **SHIP-DISCORD** — Kaan posts `#announcements` (real webhook + `LAUNCH_REAL=1`).
4. **SHIP-TRANSFER** — Kaan runs `sync_github_meta.sh --real` + GitHub org transfer flow.
5. **SHIP-ROTATE** — Kaan + Francesco + Bravoh-team run the 24h hourly rota.
6. **SHIP-V1-DECISION** — Kaan decides RC1 → v1.0.0 cut after ~2-wk bake (separate phase).

## Hard guards (Phase 39 contract)

| Guard | Mechanism |
|---|---|
| `cut_release.sh` NEVER calls `gh release create` autonomously | Static-audit test scans for live invocations outside heredoc preview |
| `publish_social_posts.py` NEVER touches Twitter / IG / Reddit / HN | Static-audit test scans for `tweepy`/`praw`/`instagrapi` etc. |
| `--real` requires `LAUNCH_REAL=1` env (social + Discord publishers) | Exit 2 + error message |
| `sync_github_meta.sh --real` requires `GH_META_REAL=1` env | Exit 2 + error message |
| Tag prefix `v2.1.0-rc[0-9]+` is sacred (P83) | Gate 1 in `cut_release.sh` |
| POC files (`cohost*.py`, `mascot.html`) untouched | Gate 5 in `cut_release.sh` (delegates to AUDIT-06) |
| Bundle ID locked at `world.bravoh.vibemix` (P63) | Gate 6 in `cut_release.sh` |
| Phase 16 override expiry reminder | Printed by `cut_release.sh` on every success path (P85) |

## Test suite evidence

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

Regression checks for adjacent phases (35, 37, 38) green: 25 passed.

## `cut_release.sh` dry-run output (2026-05-16)

```
[Gate 1] Tag prefix matches ^v2\.1\.0-rc[0-9]+$ (P83)
  PASS  v2.1.0-rc1 matches ^v2\.1\.0-rc[0-9]+$
[Gate 2] verify_signed.py --require-signed for every dist artifact
  FAIL  no .dmg/.pkg/.msi/.exe artifacts in dist/
[Gate 3] README hero hash sync (Phase 35)
  PASS
[Gate 4] .planning/v2.1-MILESTONE-AUDIT.md exists + verdict WIRED (Phase 37)
  PASS
[Gate 5] POC files untouched since v2.0 (AUDIT-06 / P85)
  PASS
[Gate 6] Bundle ID locked at world.bravoh.vibemix (P63)
  PASS

PRE-FLIGHT FAILED — 1 gate(s) tripped (Gate 2 = unsigned binaries).
REFUSING TO PRINT cut command.
```

Behavior matches design contract: 5/6 gates green; Gate 2 trips because Phase 38 secrets (`APPLE_*` + `SIGNPATH_*`) haven't been populated yet (DIST-09 + DIST-11 legal-capacity carveouts pending). Once secrets land + signed `.dmg`/`.msi` drop into `dist/`, Gate 2 flips green and the cutter prints the `gh release create` command for Kaan to copy + run.

## Pitfall coverage

- **P59** — star-quality / paid-star language banned from announcement (test_post_discord_launch.py).
- **P68** — README hero hash sync + feature-matrix drift detector.
- **P78** — NACK window (5 min) + 09:00 CET launch slot.
- **P79** — 24h rotation doc with escalation paths.
- **P83** — Tag prefix sacred — `cut_release.sh` Gate 1 refuses `v1.0.0`.
- **P85** — Phase 16 override expiry tracked in STATE.md + reminder printed by cutter.
- **P86** — `gsd-autonomous fully` defers Kaan/Francesco-action items rather than overreaching.
- **P87** — grey-area decisions (e.g. `--real` env gates) explicitly documented.

## What's left (deferred to Kaan / Francesco)

Six items under KAAN-ACTION-LEGAL.md §SHIP (Kaan: 5, Francesco: 2 shared):
- SHIP-CUT, SHIP-TWEET (5-channel publish), SHIP-DISCORD, SHIP-TRANSFER, SHIP-ROTATE, SHIP-V1-DECISION.

Three items under §POST-RC-CLEANUP:
- Phase 16 override expiry (P85) — remove the STATE.md override line after RC bake.
- Bravoh-funnel utm_* attribution verification.
- v2.2 backlog grooming (Mixxx OSC, Rekordbox, ProDJ Link, stores, IT/EN beyond).

v2.1 engineering is COMPLETE. The whole v2.1 milestone is now ready for the lifecycle audit → complete → cleanup sequence. External clock (Apple Developer Program Agreement + SignPath OSS approvals) remains the critical path to actual public launch.
