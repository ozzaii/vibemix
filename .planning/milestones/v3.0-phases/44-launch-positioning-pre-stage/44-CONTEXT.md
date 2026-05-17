# Phase 44: Launch Positioning + Pre-stage - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning
**Mode:** Autonomous (gsd-autonomous fully)

<domain>
## Phase Boundary

Make vibemix launch-ready short of external-clock items: README rewrite to the public hero pitch, EvidenceRegistry citation strip wired into the live UI as on-screen anti-slop receipts, Bravoh funnel CTA placed (opt-in, not gating), `bravoh` GitHub org standup pre-stage, SHIP-TWEET 5-channel copy reviewed and signed, Discord auto-provision dry-run, outreach calendar + launch sequence doc finalized.

Three internal waves:
- **Wave A — README + grids (LAUNCH-01, LAUNCH-03, LAUNCH-04):** README hero rewrite (frontload "the only AI co-host that actually listens to your set"); DJ-software-logo grid (rekordbox, Serato, Traktor, djay Pro, VirtualDJ, Mixxx); 10-controller supported grid + generic-MIDI calibrate callout.
- **Wave B — In-app surfaces (LAUNCH-02, LAUNCH-05):** EvidenceRegistry citation strip in live session UI; debrief "join Bravoh waitlist" toggle (opt-in, UTM-tracked, signed-out telemetry default-off).
- **Wave C — Pre-stage discharges (LAUNCH-06, LAUNCH-07, LAUNCH-08, LAUNCH-09, LAUNCH-10):** `bravoh` GH org standup runbook (engineering ships the checklist + billing-resolve waiting state; actual org creation is Kaan-discharge); SHIP-TWEET 5-channel copy lock (review + sign + grep gate against AI-slop language); Discord auto-provision dry-run (`scripts/dayzero/discord_provision.py --dry-run` already exists from prior phases — verify + lock + document); outreach calendar populated; launch sequence T-7 → T+30 doc.

Engineering ships everything except real external actions: Bravoh org creation requires Kaan's Bravoh-billing login; Discord live execution requires bot-token; signed copy approval requires Francesco's response. All gated via `KAAN-ACTION-LEGAL.md §LAUNCH-*` runbook sections.

Anti-feature carveouts:
- Do NOT add a Bravoh-waitlist gating flow — opt-in toggle only per LAUNCH-05; memory `feedback_no_scope_creep_clean_utility` locks utility-only scope.
- Do NOT spam the outreach calendar with custom AI-generated email drafts beyond the locked 3 editorial pitches + 3 subreddit posts + Discord T-3 — memory `project_github_star_goal` (500-1000+ stars) frames scale.
- Do NOT introduce a launch-day analytics dashboard (out of scope for v3.0).

</domain>

<decisions>
## Implementation Decisions

### README + Grids Wave (LAUNCH-01, LAUNCH-03, LAUNCH-04)

- **LAUNCH-01 README hero rewrite:** Edit existing `README.md` at repo root (hero block already exists from Phase 39). Replace hero `<em>` tagline with "the only AI co-host that actually listens to your set". Add a "no AI slop" hook section immediately below hero — 2-3 paragraph one-liner pitch ("real DJ friend in your ear, not voice-assistant slop"; "your audio doesn't leave the machine without you knowing"; "built by DJs, runs on your machine"). Static screenshot or GIF in `docs/assets/hero.png` already exists; demo.mp4 reference resolvable post-Francesco-shoot (already linked with placeholder).
- **LAUNCH-03 DJ-software grid:** Add new "Works alongside whatever DJ app you already use" section below the hook. 6-cell grid (3×2 or 2×3): rekordbox, Serato, Traktor, djay Pro, VirtualDJ, Mixxx. Logo assets in `docs/assets/dj-software/` (if absent, ship SVG placeholders with each app's typographic logotype + add `KAAN-DISCHARGE-PENDING` marker for real-logo upload per `KAAN-ACTION-LEGAL.md §LAUNCH-03`). Alt-text per logo. Grid renders correctly in GitHub markdown via `<picture>` or simple `<img>` table.
- **LAUNCH-04 Controller grid:** New "Supported controllers" section. 10 mapped controllers from `src/vibemix/midi/controllers/` or similar (read existing source for which 10 are mapped — DDJ-FLX4 + 9 others per ROADMAP). Add "calibrate any other controller" callout with link to docs / wizard step. Logo assets in `docs/assets/controllers/` (placeholders + §LAUNCH-04 KAAN-discharge). Alt-text + accessibility check via `scripts/launch/check_readme_grids_a11y.py` (new) — asserts every `<img>` has `alt=""`, no empty alt, grid cells balanced.

### In-app Surfaces Wave (LAUNCH-02, LAUNCH-05)

- **LAUNCH-02 EvidenceRegistry citation strip:** Live session UI shows 2-3 word evidence tag per AI reaction. Tag format: `[<verb> @ <mm:ss>]` (e.g. `[kick swap @ 2:33]`, `[layer drop @ 4:50]`). Sourced from existing `EvidenceRegistry` (Phase 23+; load-bearing anti-slop primitive per CONTEXT). Tag renders as a small chip in the session timeline / reaction stream — token-driven CSS, amber accent on hover. Click tag → opens debrief window (existing surface from Phase 29) with waveform region highlighted at the tag's timestamp. Phase 42's `ear_test_capture.py` debrief flow stays in place; this is an additive UI surface, not a replacement.
- **LAUNCH-05 Bravoh waitlist toggle:** New "Join Bravoh waitlist (optional)" toggle in debrief window settings drawer. Default OFF. When ON, debrief save flow optionally surfaces a link `https://bravoh.com/waitlist?utm_source=vibemix&utm_medium=app&utm_campaign=oss-launch`. Subtle, not gating: just a link, not a form intercept. Telemetry default-off — no signed-out events fire unless user explicitly toggles on. Settings persistence reuses existing local config store from `src/vibemix/runtime/config.py` (or similar — planner reads existing source).

### Pre-stage Discharges Wave (LAUNCH-06..10)

- **LAUNCH-06 `bravoh` GH org standup:** Engineering ships `KAAN-ACTION-LEGAL.md §LAUNCH-06` runbook — Bravoh billing-flag resolution checklist + GH CLI commands for org creation + member invite scripts + repo-receive readiness check. Plan 44 also adds `scripts/launch/check_bravoh_org_ready.sh` that polls `https://api.github.com/orgs/bravoh` and exits 0 if the org exists. Plan 45's SHIP-TRANSFER consumes this.
- **LAUNCH-07 SHIP-TWEET 5-channel copy lock:** 4 channels (twitter, instagram, linkedin, reddit) already have draft copy in `scripts/dayzero/launch_copy/`. Add `discord.txt` (5th channel). Lock pass requires: (a) Kaan-sign + Francesco-sign (signature lines at bottom of each file with date), (b) AI-slop grep gate via `scripts/launch/check_no_ai_slop.py` blocking phrases like "leverage", "synergize", "revolutionize", "game-changer", "next-generation" etc. — pin the blocklist explicitly. (c) "Real DJ friend" / "built by DJs" / "your audio doesn't leave your machine" anchor phrases must appear at least once across the 5 files combined. Lock-signed copies committed; §LAUNCH-07 runbook for Francesco sign-off discharge.
- **LAUNCH-08 Discord auto-provision dry-run:** `scripts/dayzero/discord_provision.py` already exists (Phase 36-era). Verify it has `--dry-run` mode; if missing, add. Dry-run prints channel + role plan without API calls. Lock the channel/role taxonomy: `#general`, `#help`, `#showcase`, `#announcements`, `#bugs`, roles `@member`, `@moderator`, `@kaan`, `@francesco`. Bot-token slot prepared via `BRAVOH_DISCORD_BOT_TOKEN` env var + GH secret stub. `KAAN-ACTION-LEGAL.md §LAUNCH-08` documents live-execution discharge.
- **LAUNCH-09 Outreach calendar:** New `docs/launch-prep/OUTREACH-CALENDAR.md`. Sections: editorial pitches (DJ TechTools / DDJ Tips / Mixmag — one draft email body per), subreddit cross-post plan (r/DJs / r/Beatmatch / r/edmproduction — Show HN-style framing), DJ TechTools Discord T-3 soft-launch slot reservation note. Each entry has a status checkbox (Drafted / Sent / Acknowledged / Published).
- **LAUNCH-10 Launch sequence T-7 → T+30 doc:** New `docs/launch-prep/LAUNCH-SEQUENCE.md`. Timeline rows:
  - T-7: pre-seed 15-20 stars from dev network (Kaan's network); calendar slot
  - T-3: DJ TechTools Discord soft-launch slot — exact channel + time
  - T-0: Show HN early-morning ET + 5-channel social cross-post + outreach calendar emails fired
  - T+24h: maintainer-answers-every-comment commitment + monitoring schedule
  - T+72h: Substack "how we built it" — draft outline included
  - T+7d: "week-1 numbers" transparency post — template included
  - T+30: SHIP-V1-DECISION review (cut v1.0.0 / cycle RC2 / pause)
  Each row links to ROADMAP + KAAN-ACTION items it depends on.

### Plan Split (Claude's discretion)

Recommended 7 plans:
- 44-01: README hero rewrite + "no AI slop" hook section (LAUNCH-01)
- 44-02: DJ-software grid + controller grid + a11y check (LAUNCH-03 + LAUNCH-04)
- 44-03: EvidenceRegistry citation strip in live UI + tag→debrief deep link (LAUNCH-02)
- 44-04: Bravoh waitlist toggle in debrief settings (LAUNCH-05)
- 44-05: SHIP-TWEET 5-channel copy lock + AI-slop grep gate + §LAUNCH-07 runbook (LAUNCH-07)
- 44-06: Bravoh GH org runbook + Discord dry-run lock + check scripts (LAUNCH-06 + LAUNCH-08)
- 44-07: Outreach calendar + launch sequence doc (LAUNCH-09 + LAUNCH-10)

(Planner: collapse or split as judgment dictates — keep under 9.)

### Claude's Discretion
- Exact tag chip color/style (planner reads `tokens.css` for amber accent rules).
- Whether to bundle 44-06 (org + Discord) or split (planner decides).
- Logo placeholder style (text-based SVG with brand name OR boxed initials).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `README.md` already has hero block (Phase 39 SHIP-02).
- `scripts/dayzero/launch_copy/{twitter,instagram,linkedin,reddit}.txt` — 4 of 5 channels drafted.
- `scripts/dayzero/discord_provision.py` — existing Discord provision script.
- `scripts/dayzero/seed_stars.md` — existing pre-seed star plan.
- `scripts/dayzero/healthz_check.sh` + `healthz_cron.example` — existing healthz cron stub.
- `src/vibemix/agent/` — likely has the EvidenceRegistry that LAUNCH-02 surfaces.
- `tauri/ui/src/debrief/` — debrief window UI surface (Phase 29 + 42).
- `tauri/ui/src/session/` — live session UI surface.
- `docs/launch-prep/` — created by Phase 43-09 with SHOT-LIST.md / AUDIO-CAPTURE.md / DEMO-MODE-CONFIG.md / README.md.

### Established Patterns
- KAAN-ACTION discharges live in `KAAN-ACTION-LEGAL.md §<TAG>` sections.
- Launch-check scripts live in `scripts/launch/`.
- Day-zero scripts live in `scripts/dayzero/`.
- Token-driven CSS only in frontend (auto-enforced via `frontend-enforcement` skill).
- Tests for launch artifacts live in `tests/launch/`.
- Memory `feedback_no_scope_creep_clean_utility` enforces clean OSS utility scope.

### Integration Points
- LAUNCH-02 reads from `EvidenceRegistry` (Phase 23) — write evidence event already happens; this phase surfaces it in UI.
- LAUNCH-05 telemetry uses existing config store; no new analytics infra.
- LAUNCH-06 produces the `bravoh` org that Phase 45 SHIP-TRANSFER consumes.

</code_context>

<specifics>
## Specific Ideas

- The "the only AI co-host that actually listens to your set" hero is the locked one-liner from ROADMAP — do NOT iterate on it during this phase. If Francesco wants a tweak, that's a `feedback_no_gsd_orchestra_for_trivial_tweaks` follow-up, not a Phase 44 question.
- AI-slop blocklist: ["leverage", "synergize", "revolutionize", "game-changer", "next-generation", "cutting-edge", "seamless", "robust", "powerful", "intuitive", "delightful experience", "AI-powered", "harness the power", "unlock", "transformative", "paradigm"] + any phrase using "deeply" as an adverb adjective qualifier.
- Anchor phrases (positive — must appear in lock):
  - "real DJ friend in your ear"
  - "built by DJs"
  - "your audio doesn't leave"
  - "open-source" / "open source"
  - "Mac + Windows"

</specifics>

<deferred>
## Deferred Ideas

- **Analytics dashboard / launch-day metrics UI:** v3.x.
- **Auto-rotation of launch-day social copy:** v3.x.
- **Multi-language launch copy (Turkish / Italian / Spanish):** v3.x — v3.0 ship is English only.
- **Affiliate / partner program for DJ educators:** v3.x.

</deferred>

<canonical_refs>
## Canonical References
- `README.md` — hero section being rewritten
- `scripts/dayzero/launch_copy/` — 4 of 5 channels drafted
- `scripts/dayzero/discord_provision.py` — Discord provision
- `docs/launch-prep/` — Phase 43-09 handoff package
- Memory: `project_github_star_goal` — 500-1000+ star funnel
- Memory: `feedback_no_scope_creep_clean_utility` — utility-only scope
- `.planning/REQUIREMENTS.md` — LAUNCH-01..10
- `.planning/ROADMAP.md` — Phase 44 success criteria
</canonical_refs>
