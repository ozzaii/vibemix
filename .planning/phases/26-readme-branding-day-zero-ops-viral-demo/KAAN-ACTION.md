# Phase 26 — Kaan Action Items

Phase 26 (README + Branding + Day-Zero Ops + Viral Demo) splits cleanly into Claude-automatable work (Waves 1, 2, 5, 6-partial) and Kaan-action work that requires real hardware, social accounts, screencast capture, or strategic launch-trigger judgment.

This file is the consolidated Kaan-action surface for the phase. Auto-executed waves are tracked in their respective SUMMARY.md files.

---

## Wave 3 — Fresh-VM Rehearsals (Pitfall 31)

**Goal:** Verify the v2.0 binary installs and runs cleanly on machines with no dev cruft, no pre-installed BlackHole / WASAPI helpers, and no pre-granted TCC permissions.

### macOS rehearsal

- [ ] Spin up a fresh macOS 14+ VM (or wipe an old MacBook to a clean install).
- [ ] Confirm NO BlackHole pre-installed, NO TCC pre-granted to anything, NO Homebrew.
- [ ] Download the signed DMG from GitHub Releases (Phase 21 deliverable).
- [ ] Record screencast: drag-to-Applications → first launch → TCC prompts → audio device pick → controller pair → first mix moment with a real reaction.
- [ ] Commit screencast artifact to `.planning/phases/26-.../REHEARSAL/mac-fresh-vm-<date>.mov`.
- [ ] File an issue for any friction point that adds >5 seconds to first-run.

### Windows rehearsal

- [ ] Spin up a fresh Windows 11 VM (or wipe a side machine).
- [ ] Confirm NO Python, NO ASIO drivers, NO dev tooling installed.
- [ ] Download the signed MSI from GitHub Releases (Phase 21 deliverable).
- [ ] Test SmartScreen reputation: does the binary trigger the orange "unrecognized publisher" warning? (Expected behavior in the first few weeks post-signing; document the workaround if so.)
- [ ] Record screencast: download → install → first launch → controller pair → first mix.
- [ ] Commit screencast artifact to `.planning/phases/26-.../REHEARSAL/win-fresh-vm-<date>.mov`.

**Why this is Kaan-action:** Requires real VMs / physical hardware, requires Kaan to actually perform the install motion under user-PoV recording, requires real TCC dialogs that can't be scripted from inside the Tauri app.

---

## Wave 4 — 30s Viral Demo Film (3 signature beats)

**Goal:** Produce the 30-second viral demo film that anchors all 4 channel posts. Three signature beats baked in.

### Pre-shoot checklist

- [ ] Signed binary installed on shoot machine (DMG, not dev build — auto-update path, splash screen, signed app icon all visible).
- [ ] djay Pro 5 in **windowed** mode (NOT fullscreen — Pitfall 4 mitigation, fullscreen hides overlay).
- [ ] DDJ-FLX4 powered + paired, MIDI map confirmed loaded.
- [ ] HD25 headphones in shot.
- [ ] CDJ Whisper palette confirmed on overlay (warm blacks + amber accent — no neon, no gradients).
- [ ] Mascot overlay visible and breathing.
- [ ] Two prepped tracks loaded — one in each deck — with the EQ + filter moves pre-rehearsed for Beat A.
- [ ] Test session run end-to-end before record to confirm Beat B mascot anticipation timing.

### The three beats

- [ ] **Beat A (T+8s)** — amber overlay ring lights up on mid-EQ knob of deck A, synchronized with a Gemini voice line citing the move ("Filter sweep — nice tension build"). The visual + audio + actual hand movement form a single grounded moment.
- [ ] **Beat B (T+14s)** — mascot leans forward 200ms BEFORE the Gemini voice line starts. This is the anticipation moment — proves the mascot is beat-coupled, not just lip-synced.
- [ ] **Beat C (T+22-25s)** — 3 seconds of deliberate silence. The AI stays quiet despite an obvious move (load a new track, no transition). On-screen subtitle: "no slop = silence is a feature." This is the anti-slop made visual.

### Post

- [ ] Single take preferred. Multi-take cut OK if it lands the beats more cleanly.
- [ ] Color grade: warm blacks, no LUT that pushes magenta/cyan.
- [ ] No music bed — the DJ set IS the soundtrack. Voice lines audible.
- [ ] Burn captions for sound-off viewers (IG default).
- [ ] Three export formats:
  - **Landscape 16:9** (Twitter, HN, Reddit) — 30-90s
  - **Vertical 9:16** (IG Reels) — 30s exact
  - **GIF 720x720** (Reddit inline, Twitter thread embeds) — ~6s loop on Beat A

### Commit + upload

- [ ] YouTube unlisted upload (single source of truth for the channel posts).
- [ ] Master MP4 to `.planning/phases/26-.../DEMO/v2.0-demo-master.mp4` (NOT committed to repo — too large; reference path only).
- [ ] Update all 6 channel post drafts to replace `<TBD demo_*>` markers with the real URLs.

**Why this is Kaan-action:** Requires real Kaan + real DDJ-FLX4 + real djay Pro + real DJ skill on actual rehearsed mix moments. Cannot be automated.

---

## Wave 6 (partial) — Discord Server + Pre-Seeded Stars

The script half of Wave 6 (proxy_load_test.py + healthz_check.sh) is auto-completed in Plan 26-04. These items remain Kaan-action.

### Discord server setup

- [ ] Create the vibemix Discord server (or carve a vibemix section in an existing Bravoh server).
- [ ] Set up channels: `#welcome`, `#help`, `#controller-mappings`, `#showcase`, `#ai-misbehavior-reports`, `#dev`.
- [ ] Create roles: `Maintainer`, `Contributor`, `Beta`, `Community`.
- [ ] Generate the invite URL (no expiration, unlimited uses).
- [ ] Replace all `<TBD discord_invite>` markers in:
  - `README.md` (footer line)
  - `.planning/phases/26-.../CHANNEL-POSTS/twitter-en.md`
  - `.planning/phases/26-.../CHANNEL-POSTS/instagram-en.md`
  - `.planning/phases/26-.../CHANNEL-POSTS/instagram-it.md`
  - (Reddit + HN drafts link to the repo, which links to Discord — no direct invite needed.)
- [ ] Discord bot (announce-release, FAQ-bot) is deferred to v2.1.

### Pre-seeded stars

- [ ] Identify 15+ pre-seed star contributors: Bravoh team, Bravoh-team friends, vibemix beta testers from Phase 16, Francesco's DJ network.
- [ ] Distribute the GitHub repo URL with a soft ask ("star if it looks interesting, no pressure") 48-72 hours BEFORE launch.
- [ ] Target: 15+ stars before public posts go live. Avoids the "0 stars looks dead" Day-0 problem.
- [ ] NOT a vote-ring: ask only people who have actually tried vibemix or would be plausibly interested. Asking strangers to star = HN flag risk.

**Why this is Kaan-action:** Discord setup is account-level UX. Pre-seed star coordination requires Kaan's network + judgment.

---

## Wave 7 — Launch Trigger

**Goal:** Kaan + Francesco + Momo greenlit all gates and fire the launch.

### Pre-launch gates (all must be green)

- [ ] Phase 21 signed binaries live on GitHub Releases (DMG + MSI).
- [ ] Phase 16 hallucination verification gate passed (Kaan's DJ ear).
- [ ] Wave 3 fresh-VM rehearsals complete on both Mac + Win.
- [ ] Wave 4 demo film exported + uploaded to YouTube unlisted.
- [ ] Bravoh proxy load test (Plan 26-04) passes against staging (`proxy_load_test.py --target https://api.altidus.world/vibemix/healthz --rps 100 --duration 300`).
- [ ] All `<TBD>` markers in README, BRANDING.md, and channel post drafts replaced with real values (repo URL, Discord invite, demo URLs).
- [ ] Discord server live, invite URL distributed in README + channel posts.
- [ ] 15+ pre-seeded stars in place.
- [ ] `healthz_check.sh` running in a tail terminal during the launch window.

### Launch sequence (target: Tue/Wed 9-11am EST)

- [ ] **T-30 min:** healthz_check.sh starts running, tailed in a terminal Kaan can see.
- [ ] **T+0:** Push the GitHub repo public (if it's been private). README + BRANDING + signed binaries already in place.
- [ ] **T+5 min:** Post the HN Show HN (HN takes longest to climb, post first).
- [ ] **T+10 min:** Post Twitter thread.
- [ ] **T+30 min:** Post r/Beatmatch.
- [ ] **T+60 min:** Post IG Reel EN.
- [ ] **T+90 min:** Post r/programming.
- [ ] **T+3h:** Post IG Reel IT.
- [ ] **T+12h:** Post r/DJs (DJ subreddit overlap — don't burn karma with same-day dupes).
- [ ] **T+24h:** Post r/opensource cross-post if r/programming landed.

### Post-launch ops (first 48h)

- [ ] Monitor `healthz_check.sh` output. If alerts > 3 in any 5-min window, page Bravoh team.
- [ ] Reply to every HN comment in the first 4 hours.
- [ ] Reply to every Reddit comment in the first 2 hours per subreddit.
- [ ] Triage ai-misbehavior issues at P0.
- [ ] If GitHub stars > 200 in 24h, escalate Bravoh-team awareness (warm boost from Bravoh socials).
- [ ] If GitHub stars > 500 in 48h, hit the 1k target — start outreach to OSS newsletters.

**Why this is Kaan-action:** Final go/no-go judgment, real-time launch coordination, comment-thread engagement, escalation calls.

---

## Pro Logo Design (post-v2.0)

The current `docs/branding/logo.svg` is a placeholder text-based wordmark. Replace with a designer-finalized logo when:

- [ ] v2.0 launch survives the first 30 days.
- [ ] Discord community is active (>50 members).
- [ ] We have a clear visual identity beyond CDJ Whisper (logo direction emerges from the brand maturing in public).

Kaan-action: hire a designer or commission via Bravoh's design network. Tracked here, NOT a v2.0 blocker.

---

## Summary table

| Wave | Description | Status |
|------|-------------|--------|
| 1    | README + BRANDING + placeholder logo | ✅ Plan 26-01 (Claude) |
| 2    | ai_misbehavior issue template + CONTRIBUTING refinement | ✅ Plan 26-02 (Claude) |
| 3    | Fresh-VM rehearsals (Mac + Win) | ⏳ Kaan-action |
| 4    | 30s viral demo film | ⏳ Kaan-action |
| 5    | 4-channel post drafts (6 files) | ✅ Plan 26-03 (Claude) |
| 6a   | Day-Zero ops scripts (proxy load test + healthz) | ✅ Plan 26-04 (Claude) |
| 6b   | Discord server + pre-seeded stars | ⏳ Kaan-action |
| 7    | Launch trigger | ⏳ Kaan-action |
| —    | Pro logo design | ⏳ Kaan-action (post-v2.0) |
