# vibemix — OSS Launch & Ecosystem Positioning

**Researched:** 2026-05-25 · **Mode:** Ecosystem + launch playbook · **Confidence:** MEDIUM-HIGH
**Goal:** 500+ stars min / 1000+ realistic, as a Bravoh waitlist funnel.
**Locked (not re-litigated):** Apache 2.0 · Gemini-only · Mac+Win · 150-200€ launch + ~50€/mo API · one-click install HARD req.

## TL;DR — Recommended Launch Plan

1. **The whole launch lives or dies on ONE 30-60s captioned video** of the AI talking over a real set. Magic is *audible* — nobody stars from a screenshot. Cut this before anything else; it's the hero of README, HN, Reddit, X, and the ad spend. Repo is already wired for it (storyboard mock exists) — discharge it.
2. **Anchor the launch on Hacker News "Show HN," Tue-Thu 8-10am ET.** A front-page Show HN = 500-2000 stars in 24h and is the single highest-ROI channel for a dev-adjacent tool. One shot — everything else feeds star-velocity to trip GitHub Trending.
3. **DJ subreddits are SHOW-DON'T-SELL.** r/DJs / r/Beatmatch / r/DJControllers kill naked self-promo. Post the *video* as a story ("does this feel real to you?") with the repo link in the body. A real DJ (Francesco) posting beats Kaan posting.
4. **README must answer "is this spying on me?" and "does it install in 60s?" above the fold** — vibemix's two unique adoption killers (it listens + watches your screen; needs BlackHole/WASAPI routing). Pre-empt in hero copy, not the FAQ.
5. **Coordinated 24-48h burst, not a drip.** Same-day: Show HN (morning ET) → X video thread → DJ Discords/Francesco → Reddit story posts → Product Hunt (secondary). Simultaneous traffic trips Trending; Trending then markets for you.

## 1. OSS DJ / AI-Audio Landscape — whitespace is REAL

| Project | What | ~Stars | Overlap |
|---------|------|--------|---------|
| **mixxxdj/mixxx** | Full OSS DJ mixing app | **6.7k** (1.7k forks) | None — the deck, not a co-host. Integration target. |
| **innermost47/ai-dj** (OBSIDIAN) | AI *music generation* VST | ~213 | None — generates, doesn't react. |
| **teticio/Deej-AI** | DL auto-playlist | mid-hundreds | Adjacent to Viber side, not live co-host. |
| **jasonmayes/Web-AI-Spotify-DJ** | Browser Gemma-2 playlist agent | low-hundreds | Playlist, not live. |
| **Auto-DJ / AI-MiniDJ / artificial_dj** | Academic auto-mixers | tens–low-hundreds | Opposite philosophy — they *replace* the DJ. |

**Finding (HIGH): no OSS real-time AI co-host that listens to a live set and reacts as hype-man/coach exists.** Every AI-audio OSS project is a generator, recommender, or auto-mixer-that-takes-over. Nobody occupies "a friend in your ear *while you* DJ." Clean whitespace.

**Differentiation (verbatim, already locked):** *"The only AI co-host that actually listens to your set."* Reinforce: it doesn't mix for you, doesn't generate music — reacts to what you're actually doing, grounded (never hallucinated). The anti-slop / "trust the audio" thesis IS the differentiation — every other AI-music tool is exactly the slop machine DJs are sick of.

## 2. The 0→1000 Star Playbook (ranked for DJs + AI-curious devs)

| Rank | Channel | ROI | Mechanics |
|------|---------|-----|-----------|
| **1** | **HN "Show HN"** | Highest (500-2000/24h on front page) | Title: `Show HN: vibemix – an open-source AI co-host that listens to your DJ set`. **Tue-Thu 8-10am ET.** One launch. AI-curious-dev half lives here. |
| **2** | **X video thread** | High (amplification + Trending fuel) | Video as first tweet. One influential repost > 100 of your own. |
| **3** | **DJ Discords + Francesco's network** | High, warm | Real DJs sharing = most credible signal. Francesco is the unfair advantage. |
| **4** | **Reddit (story-framed)** | Medium, high-risk wrong | r/DJs, r/Beatmatch, r/DJControllers, r/edmproduction. NOT a link drop (shadowban). Story framing, link in body, post the video. |
| **5** | **Product Hunt** | Medium | Secondary, T0 or T+1. Badge + wave, weaker than HN here. |
| **6** | **YouTube/TikTok** | Slow burn | Long-tail, not launch-day spike. Repurpose. |

**Launch-day mechanics:** T-7→T-1 seed repo (real README + video + green CI badges + a few issues so it's not dead); line up Francesco + friendly DJs for first 2h. T0 morning ET: Show HN first, then fire X + Discords + Reddit within the same window → concurrent traffic trips **GitHub Trending** → algorithm markets for you. First 24h: answer EVERY comment in minutes (responsiveness = #1 trust signal).

**What gets FLAGGED/killed:** HN — vote rings, friend-upvotes, re-posting a flop, marketing-speak titles (lead with honest technical hook). Reddit — naked links, simultaneous cross-posting, "company" voice (use a real DJ's voice). Repo — dead-looking (0 issues, no demo) = bounce; looking *alive* > looking *finished*.

**Timeline expectation:** good Show HN can hit 500-1000 in the window; if HN doesn't catch, expect a gradual curve to 1000 over weeks, then acceleration. Budget for both — don't bet the funnel on one front page.

## 3. README Anatomy (visitor → star)

1. **Hero = demo video/GIF FIRST**, then tagline. GIF inline (≤10MB, ≤20s, ~10fps, ~600×400); video as linked thumbnail or GitHub-hosted `<video>`.
2. **One-sentence what + why** under hero.
3. **Badges (~4):** star-count (+~15% conversion via momentum), Apache 2.0, CI green, platforms. No badge spam.
4. **"Works in 60 seconds" install** high up — the one-click promise (download → open → auto-config audio → ready).
5. **Two trust answers** (see §5): "is it spying?" + audio-routing one-liner.
6. **Hype-man vs Coach + 3 levels** — feature hook, tight.
7. **Controller table** (10 mapped) — DJs scan for their gear.
8. **Waitlist/CTA → Bravoh** AFTER value shown (footer + soft mid-README), opt-in, UTM (default-OFF). Earn the star first.
9. Contributing / license / security at bottom.

**Exemplars:** **mixxx** (same audience, calm not-salesy tone DJs trust); **Lago** (problem-framed README converts > feature lists); any **awesome-readme** CLI with a top-of-file GIF (GIF-first is the most-cited star driver).

## 4. The Demo Asset (gating deliverable)

**ONE 30-60s captioned video (NOT silent GIF) as the canonical artifact.** Captions mandatory — social/HN/Reddit views muted; the AI lines must appear as synced subtitles, which also *shows the grounding* ("it said that because the kick dropped"). Structure: real set → real moment (drop/breakdown/key clash) → AI reacts on-beat, captioned → cut to citation/evidence chip proving no hallucination (the `mocks/vibemix-cinematic-storyboard.html` 8-cut already encodes this — ship that cut).

Two formats from one cut: (a) full captioned **video** → README hero, X, YT, PH; (b) tight **≤10MB looping GIF** of the single best 6-8s reaction → inline README + Reddit/Discord. **If the video is mediocre, the launch is mediocre — no channel saves a weak demo.**

## 5. vibemix-Specific Frictions (pre-empt in README/launch copy)

| Friction | Why it bites | Pre-empt |
|----------|-------------|----------|
| **"Is it spying / why watch my screen + listen?"** | Listening + screenshotting reads creepy; launch audience is privacy-sensitive devs. | Above fold: runs locally; audio/screen processed on-device into compact events; only the grounded reaction request goes to Gemini; nothing stored/uploaded; recordings stay local. Trump card: "it's open source — audit it." |
| **API-key/cost anxiety (BYO vs proxy)** | Embedded-key-in-binary is the leak problem of the year. | Ship **Bravoh proxy + per-client rate limit** as default zero-setup path (no key to try it) + documented **BYO-key**. "Try it free, no API key needed — or bring your own." Never ship a raw key. |
| **Audio routing (BlackHole/WASAPI)** | Biggest first-run drop-off; no sound on first run = bounce, never star. | One-click installer auto-configures; 30s wizard GIF; actionable failure banner. |
| **"Works with MY gear?"** | DJs scan for their controller/app; absence = "not for me." | Up-front controller table (10) + "add yours in N steps" recipe. Frame 10 as "out of the box, more via community." |

## 6. Top 3 Risks + Mitigations

1. **Demo sounds like slop in the one video everyone sees.** Existential — the thesis is "no slop." *Mitigation:* Kaan's ear-pass on the demo cut is non-negotiable (hard gate). Cut from a real session, pick the single most genuinely-alive reaction, caption the grounding. A 25s video of one perfect moment beats 60s of mediocre.
2. **Show HN flops (front page is a coin-flip) → stuck at ~200.** *Mitigation:* don't single-thread HN — DJ-network/Discord wave as independent star source; keep a second *narrative* HN post ("what I learned building an AI that refuses to hallucinate") in reserve for T+2wk; sustain one quality post/week.
3. **First-run friction converts launch traffic to bounces + bad thread comments.** *Mitigation:* verify 60s-install + auto-audio-config on a fresh machine pre-launch; ship a **demo/try mode with zero audio setup** so a curious dev hears the magic instantly before being asked to wire BlackHole.

## Open Questions / Gaps
- Exact current r/DJs / r/Beatmatch sub rules couldn't be fetched (Reddit blocks fetch) — assume strict no-self-promo, route through real-DJ voices + story framing, verify each sidebar before posting (LOW confidence on specifics).
- Is the **Bravoh proxy live + rate-limited at launch?** It's the default zero-key path that removes friction #2; if not production-ready the "try free, no key" promise can't ship.
- **Apple + SignPath signatures** remain the external critical path — unsigned = scary first-launch warning = friction #3 amplified. Launch quality is gated on these landing.

### Sources
- mixxxdj/mixxx (6.7k) · innermost47/ai-dj (~213) · teticio/Deej-AI · jasonmayes/Web-AI-Spotify-DJ · ddman1101/Auto-DJ · JohanesSetiawan/AI-MiniDJ
- Lago "first 1000 stars" case study (HN-driven) · DEV "first 1000 stars" guide · star-history playbook
- README best-practices case studies · DEV demo-GIF guide · matiassingers/awesome-readme
- Reddit self-promo rules · Reddit music-promotion strategy · privacy-framing reference

**Confidence:** Star counts + HN/README mechanics = HIGH (multi-source). Reddit sub-specifics + star-velocity for this niche = LOW-MEDIUM (no direct precedent — whitespace genuinely empty).
