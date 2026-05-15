# Phase 39: Public RC Cut + Ship - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning (final phase; gated on Phases 33 + 37 + 38 signed binary)
**Mode:** Auto-generated (gsd-autonomous fully)

<domain>
## Phase Boundary

Cut the public RC — tag the signed binary, publish the GitHub Release, push 4-channel social, light up Discord, embed the demo film in the README hero, monitor the first 24h.

**Mapped REQ-IDs (8):** SHIP-01 (`gh release create` with signed binary + real changelog), SHIP-02 (README hero embeds `demo.mp4` + feature matrix sync — P68), SHIP-03 (4-channel social via `publish_social_posts.py` with NACK window), SHIP-04 (Discord `#announcements` + pre-seeded community + rotation), SHIP-05 (GitHub topics + repo description SEO + repo transfer to bravoh org), SHIP-06 (RC labeling honesty — `v2.1.0-rc1` not premature `v1.0.0`), SHIP-07 (post-launch monitoring rotation Kaan/Francesco/Bravoh), SHIP-08 (Phase 16 override expiry post-v2.1 — memory cleanup).

**In scope (autonomous):**
- `scripts/launch/publish_social_posts.py` — 4-channel publisher with `--dry-run` Discord preview + NACK window logic.
- `scripts/launch/cut_release.sh` — wraps `gh release create` with changelog template loader; refuses to run if tag prefix is wrong (P83) or binary unsigned (Phase 38 dep).
- `scripts/launch/changelog_template.md` — handwritten template covering v2.0 close + v2.1 buckets + tech-debt items.
- README hero update for `assets/demo.mp4` (Phase 35 hash sync gate already shipped).
- GitHub topics + repo description CI gate.
- `docs/launch-rotation.md` — Kaan/Francesco/Bravoh 24h monitoring rotation doc (already partly shipped in Phase 36 day-zero scaffold; this finalizes).
- Phase 16 override expiry cleanup — memory `feedback_autonomous_no_grey_area_pause` already covers; SHIP-08 confirms.
- Bravoh-funnel footer link CI gate.

**Out of scope (autonomous; deferred via KAAN-ACTION-LEGAL.md):**
- ACTUAL `gh release create` run (Kaan-action — once Phase 38 secrets land + Phase 37 audit passes).
- ACTUAL social posts (Kaan + Francesco-action — content scheduled, publish is human-clicked).
- ACTUAL Discord post (Kaan-action).
- ACTUAL repo transfer to `bravoh/vibemix` (Kaan-action — GitHub org transfer flow).
- ACTUAL 24h monitoring rotation execution (Kaan + Francesco + Bravoh-action).

**Pure out of scope:**
- v1.0.0 final cut (P83 — RC only; final after RC bake).
- Paid launch ads (Kaan budget call; not Phase 39 surface).
- Distribution to Mac App Store / MS Store (v2.2 stretch).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion (locked per gsd-autonomous fully)

Grounded in:
- ROADMAP Phase 39 verbatim
- REQUIREMENTS.md SHIP-01..08
- Pitfalls P59 (star quality), P68 (README hero sync), P78 (launch timing), P79 (monitoring gaps), P83 (cut labeling), P85 (Phase 16 override expiry), P86 (defer-to-v2.2 creep), P87 (grey-area drift)
- Phase 35 (shipped) — README hero hash sync gate, `assets/demo.mp4` placeholder + drift detector
- Phase 36 (shipped) — Discord auto-provision, launch_trigger.sh sequence, healthz, load test
- Phase 38 (shipped engineering) — release.yml signing pipeline (secrets pending)

### Social publisher (SHIP-03 / P78)
- File: `scripts/launch/publish_social_posts.py`.
- Channels: Twitter / X, Instagram Reels (IT + EN), Reddit r/Bravoh + r/DJs, HN Show HN.
- `--dry-run` posts to Discord webhook preview first.
- 5-minute NACK window before auto-publish (P78 — quiet hours / wrong timezone catch).
- Templates per channel in `scripts/launch/social_templates/`.
- Real publishing is Kaan/Francesco-action.

### Release cutter (SHIP-01 / SHIP-06 / P83)
- File: `scripts/launch/cut_release.sh`.
- Pre-flight: tag prefix must match `v2.1.0-rc[0-9]+` regex (no premature `v1.0.0`).
- Pre-flight: binary must be SignPath + Apple-signed (uses `verify_signed.py --require-signed` from Phase 38).
- Pre-flight: README hero hash gate must pass (Phase 35).
- Pre-flight: `v2.1-MILESTONE-AUDIT.md` must exist + status passed (Phase 37).
- `gh release create` invocation with `--draft` by default; Kaan flips to published.

### Changelog template (SHIP-01)
- `scripts/launch/changelog_template.md` covers:
  - v2.0 Research-Driven Ship close (Phases 15–26).
  - v2.1 Unified Cut buckets (eval harness, library intel, debrief, hard tek, mascot, profile, install, security, demo film, day-zero ops, integration audit, signing, ship).
  - Known tech-debt items + KAAN-ACTION-LEGAL items still live.
  - Honest "what's not in v2.1.0-rc1" section.
- Auto-populates phase summaries via grep of phase SUMMARY.md files.

### README hero (SHIP-02 / P68)
- README.md hero section embeds `assets/demo.mp4` via HTML5 `<video>` tag.
- Feature matrix syncs with shipped v2.1 surfaces — auto-generated from ROADMAP completed phases.
- Bravoh-funnel footer link CI gate — grep test asserts the link is present + active.

### GitHub topics + repo SEO (SHIP-05)
- File: `scripts/launch/sync_github_meta.sh` — uses `gh api` to set repo description + topics.
- Topics: `dj`, `ai`, `gemini`, `tauri`, `open-source`, `mascot`, `livekit`, `audio`, `vibemix`, `bravoh`.
- Real transfer to `bravoh/vibemix` org is Kaan-action.

### Post-launch monitoring rotation (SHIP-07)
- `docs/launch-rotation.md` finalizes the Kaan/Francesco/Bravoh 24h rotation.
- Hourly check-ins for 24h: Discord, GitHub Issues, healthz, star velocity.
- Built on Phase 36 day-zero rota doc; this is the launch-specific superset.

### Phase 16 override expiry (SHIP-08 / P85)
- Memory `feedback_autonomous_no_grey_area_pause` already covers expiry post-v2.1.
- SHIP-08 = grep gate against STATE.md "Phase 16 ear-test memory override accepted for v2.1 only" line — assert flagged for cleanup post-RC.

### Plan slice
8 plans, mapping 1:1 to SHIP-01..08:
1. `39-01` — `cut_release.sh` + pre-flight gates (SHIP-01 / SHIP-06)
2. `39-02` — README hero + feature matrix + Bravoh footer (SHIP-02 / P68)
3. `39-03` — `publish_social_posts.py` + 4-channel templates + NACK window (SHIP-03)
4. `39-04` — Discord launch flow finalize (SHIP-04)
5. `39-05` — `sync_github_meta.sh` + topics/description gate (SHIP-05)
6. `39-06` — Changelog template + auto-populator from phase summaries (SHIP-01 ext)
7. `39-07` — `launch-rotation.md` finalize + 24h coordination scaffold (SHIP-07)
8. `39-08` — Phase 16 override expiry gate + KAAN-ACTION-LEGAL final entries (SHIP-08 / P85)

</decisions>

<code_context>
## Existing Code Insights

- **Phase 35 (shipped)** — `assets/demo.mp4` placeholder + README hero hash drift detector.
- **Phase 36 (shipped)** — Discord auto-provision, healthz, load test, launch_trigger.sh T-30/T+0/T+5/T+24h, seed_stars protocol.
- **Phase 38 (engineering shipped)** — `verify_signed.py --require-signed`, release.yml signing wires.
- **STATE.md** — Phase 16 override expiry tracker line.
- **`KAAN-ACTION-LEGAL.md`** — already has DIST-09 / DIST-11 + Phase 33 + 35 entries; SHIP-08 adds final entries.

</code_context>

<specifics>
## Specific Ideas

- **NEVER autonomously fire `gh release create`** — pre-flight gates only; final cut is Kaan-action.
- **NEVER autonomously POST to Twitter / IG / Reddit / HN** — content prepared; publish is Kaan/Francesco-action.
- **P83 — tag prefix is sacred** — RC, not v1.
- **P85 — Phase 16 override expires post-v2.1** — SHIP-08 confirms STATE.md tracker is marked for cleanup.
- **P87 — grey-area decision log** — Phase 37 owns the log; Phase 39 references it in the changelog.

</specifics>

<deferred>
## Deferred Ideas

- **v1.0.0 final cut** — separate phase post-RC bake (~2 weeks observation).
- **Paid IG/Reddit ads** — Kaan budget decision; not Phase 39 surface.
- **Translation of social copy beyond IT** — v2.2.
- **Mac App Store / MS Store distribution** — v2.2 stretch.

</deferred>

<kaan_action_required>
## Critical: Kaan-Action Required (KAAN-ACTION-LEGAL.md)

Phase 39 autonomous deliverables: cutter pre-flight, social templates + publisher, Discord flow, GitHub meta, changelog autopopulator, rotation doc, override expiry gate.

Kaan-action items (rolled up by SHIP-08 and aggregated by Phase 37's AUDIT-04):
1. **SHIP-CUT:** Execute `cut_release.sh` after Phase 37 audit passes + Phase 38 secrets land.
2. **SHIP-TWEET:** Trigger 4-channel social publisher; manually confirm in NACK window.
3. **SHIP-DISCORD:** Post Discord `#announcements` (Kaan).
4. **SHIP-TRANSFER:** Transfer repo to `bravoh/vibemix` GitHub org (Kaan-action).
5. **SHIP-ROTATE:** Run 24h Kaan/Francesco/Bravoh monitoring rotation (Kaan + Francesco + Bravoh-action).
6. **SHIP-V1-DECISION:** Decide RC1 → v1.0.0 cut after 2-week bake (Kaan-action — separate phase).

All actual customer-facing publishes are Kaan/Francesco-action. Autonomous run prepares the scripts + content + gates only.
</kaan_action_required>
