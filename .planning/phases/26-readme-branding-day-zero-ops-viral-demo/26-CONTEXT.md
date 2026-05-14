# Phase 26: README + Branding + Day-Zero Ops + Viral Demo Film + Channel Posts - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully — auto-accepted recommended decisions)

<domain>
## Phase Boundary

vibemix v2.0 launches with a public-ready repo front door, fresh-VM-rehearsed day-zero ops, and the 30s viral demo + 4-channel post arsenal warming Bravoh's public launch wave (~early June 2026). Composite launch phase: README full rewrite + fresh-VM rehearsals + Discord + GitHub issue templates + Bravoh proxy load test + 30s viral demo film + Twitter/IG/Reddit/HN posts.

**Critical scope boundary:** This phase IS the public launch surface. It is the LAST phase of v2.0 and is FIRST on the cut list if Bravoh-launch timeline slips (per ROADMAP cut order — "minimum viable: README PR-ready, demo film as v2.0.1 fast-follow"). Tied tightly to Bravoh's public launch wave per `project_v2_planning_active` — vibemix drops weeks before Bravoh as marketing wedge. GitHub star goal per memory `project_github_star_goal`: 500+ minimum, 1000+ realistic.

</domain>

<decisions>
## Implementation Decisions

### README Rewrite (LOCKED — per success criteria)
- Value-prop paragraph above-the-fold: "real DJ friend in your ear, no AI slop" thesis (per CLAUDE.md core value).
- 30s demo GIF embedded (NEW asset — built in this phase Wave 4).
- 12-question FAQ pre-seeded:
  - Anti-slop / "why won't it just talk freely?"
  - Anti-API-key / "do I need a Gemini key?"
  - Why-Gemini / "why not OpenAI/Claude?"
  - Rekordbox-v2-roadmap / "when will Apple Music / Spotify be supported?"
  - Plus 8 more (controllers, OSes, mascot, debrief, library, debugging, contributing, Bravoh-relationship).
- 8-controller logo grid (10 SKUs from Phase 23, but logos for top 8 — Numark Party Mix Live + Mixstream Pro+ in text-only list).
- Badges row: license (Apache 2.0), build status, latest release, Discord, stars.
- Install one-liner (TBD at plan-time — likely direct DMG/MSI download, with Homebrew/winget deferred to v2.0.1).
- Hero PNG + architecture SVG already shipped (Phase 19 absorbed; commits 137200b + 4d20511) — README references them.
- `CONTRIBUTING.md` controller-mapping path references `scripts/sniff_controller.py` (Phase 23 deliverable).

### Fresh-VM Rehearsals (LOCKED — per Pitfall 31)
- Clean macOS 14+ install: NO dev cruft, NO pre-installed BlackHole, NO TCC pre-granted.
- Clean Windows 11 install: AV/Defender SmartScreen reputation check.
- Both rehearsals recorded as screencast artifacts; committed to `.planning/phases/26-.../REHEARSAL/`.
- Rehearsal also serves as Phase 21 Day-0 rehearsal mandate.

### Day-Zero Ops Surface (LOCKED — per Pitfalls 32-35, 39, 41)
- **Discord server (Pitfall 34)**: roles + channels + Day-0 URL in README footer. Bot deferred to v2.1.
- **GitHub issue templates + auto-labeler (Pitfall 35)**: bug / feature / mapping-PR / question templates + auto-label by SKU/OS/severity.
- **`api.altidus.world/healthz` curl gate Day-0 (Pitfall 32)**: gate the public launch on healthz returning 200. Bravoh-team carry-forward — Kaan-action surface in plan.
- **Bravoh proxy load test (Pitfall 30/39)**: 100 RPS for 5 min, p99 <500ms. Validates proxy survives viral RPM exhaustion before launch.
- **Adaptive cap + dashboard for proxy budget (Pitfall 39)**: Pro-key overflow on free-tier breach + live dashboard for Kaan/Francesco visibility.
- **15+ pre-seeded friend/dev stars** before public launch (warm the "0 stars looks dead" Day-0 problem).
- **Weekly slip review (Pitfall 41)**: baked into milestone close gate — vibemix vs Bravoh timeline cross-check.

### 30s Viral Demo Film (LOCKED — per success criteria)
- 3 signature beats:
  - **Beat A (T+8s)** — amber overlay ring on mid EQ deck A, synchronized with Gemini voice line citing the move (Phase 24 anchor).
  - **Beat B (T+14s)** — mascot leans forward 200ms BEFORE Gemini audio (Phase 22 anchor).
  - **Beat C (T+22-25s)** — 3 seconds of deliberate silence — anti-slop made visual (Phase 20 linter integrity made viewable).
- Single take or curated multi-take (whichever lands the moments cleanly).
- djay Pro 5 windowed mode (Pitfall 4 mitigation — fullscreen would hide overlay).
- CDJ Whisper color palette (Phase 14 + `project_visual_direction_cdj_whisper`).
- Kaan + DDJ-FLX4 + HD25 headphones (real DJ rig per memory profile).

### 4-Channel Post Arsenal (LOCKED — per success criteria)
- **Twitter thread**: Beat A hero (overlay ring) — engineering-curious dev audience.
- **IG Reels IT+EN**: Beat B hero (mascot anticipation) — visual-first DJ + creator audience. Italian + English (per CLAUDE.md i18n).
- **Reddit r/Beatmatch + r/DJs**: Beat C hero (silence/anti-slop angle) — DJ-community OSS-credibility audience.
- **HN Show HN**: Beat A hero (overlay ring) — engineering breakdown post body.
- Pre-seeded FAQ per channel (handles "is this just AI slop?" + "is my key safe?" + "why Gemini?").
- GitHub stars ticker outro frame on every video asset.

### Channel-Specific Cuts (Claude's Discretion within constraint)
- Twitter: 60-90s landscape, sound-on assumed.
- IG Reels: 30s vertical 9:16, sound-on captions.
- Reddit: link to YouTube unlisted upload + GIF in post body.
- HN: blog-post-style writeup linking to YouTube + repo.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Existing `README.md` — full rewrite (current content stub-level).
- Hero PNG + architecture SVG (Phase 19 absorbed, commits 137200b + 4d20511) — embedded in new README.
- Phase 21 signed binaries — install one-liner + GitHub Release page link.
- `mocks/vibemix-direction-final.html` — visual reference for any new branding asset.
- `cohost_v4.py` + POC family — REMAIN UNTOUCHED (per CLAUDE.md POC rule); README links to their reference role honestly.

### Established Patterns
- 3-process architecture documentation (Tauri + Python sidecar + FastAPI proxy) — explained in README architecture section.
- Apache 2.0 + DCO license (already in repo).
- macOS 12.3+ / Windows 10/11 only (Linux explicitly excluded per STATE).
- GSD workflow used to ship — referenced in CONTRIBUTING.md as repo-internal practice.

### Integration Points
- `api.altidus.world/healthz` — Bravoh-team carry-forward; healthz curl gate runs Day-0.
- `api.altidus.world/vibemix/updates/upload` — Phase 21 deliverable; live by P26.
- GitHub Actions release pipeline (Phase 21) produces the binaries linked from README.
- Discord server external — URL committed to README footer Day-0.
- Twitter/IG/Reddit/HN posts external — drafts committed to `.planning/phases/26-.../POSTS/`.

</code_context>

<specifics>
## Specific Ideas

- Wave 1: README full rewrite (value prop + FAQ + badges + controller grid + install one-liner).
- Wave 2: GitHub issue templates + auto-labeler + CONTRIBUTING.md updates referencing Phase 23 sniff tool.
- Wave 3: fresh-VM rehearsals (mac + win) recorded as screencast artifacts (Pitfall 31).
- Wave 4: 30s viral demo film recording (3 beats: overlay + mascot anticipation + silence).
- Wave 5: 4-channel post arsenal drafts (Twitter + IG IT+EN + Reddit + HN) + pre-seeded FAQ per channel.
- Wave 6: Day-Zero ops gate (Discord URL live + healthz curl gate + proxy load test 100 RPS×5min + adaptive cap dashboard + 15+ pre-seeded stars).
- Wave 7: launch trigger + weekly slip review baked into milestone close.

</specifics>

<deferred>
## Deferred Ideas

- Homebrew cask + Scoop manifest install paths (v2.0.1+ — direct download in v2.0).
- Discord bot (announce releases, FAQ-bot) — v2.1 (server + roles + channels in v2.0).
- YouTube long-form walkthrough — v2.0.1 (30s viral demo only in v2.0).
- Press kit / journalist outreach — v2.0.1+ (community-channel-first launch in v2.0).
- Localized README (IT/TR) — v2.0.1+ (English + IG IT+EN reels in v2.0).
- Sponsor / OpenCollective surface — v2.x (Apache 2.0 OSS-only in v2.0).
- vibemix.bravoh.world landing page — v2.x (GitHub repo IS the front door in v2.0).
</deferred>

---

*Phase: 26-readme-branding-day-zero-ops-viral-demo*
*Context gathered: 2026-05-14 (smart discuss, fully autonomous)*
