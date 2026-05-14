---
phase: 26
plan: "03"
subsystem: launch-marketing / channel-posts
tags: [twitter, instagram, reddit, hackernews, anti-slop, launch-ammo]
requires: [Wave 4 demo film (deferred — Kaan-action)]
provides: [6 channel post drafts covering all 4 channels in EN + IT]
affects: [v2.0 launch marketing surface (NOT shipped in repo root — internal launch ammo)]
tech_stack_added: []
tech_stack_patterns: []
key_files_created:
  - .planning/phases/26-readme-branding-day-zero-ops-viral-demo/CHANNEL-POSTS/twitter-en.md
  - .planning/phases/26-readme-branding-day-zero-ops-viral-demo/CHANNEL-POSTS/instagram-en.md
  - .planning/phases/26-readme-branding-day-zero-ops-viral-demo/CHANNEL-POSTS/instagram-it.md
  - .planning/phases/26-readme-branding-day-zero-ops-viral-demo/CHANNEL-POSTS/reddit-rprogramming.md
  - .planning/phases/26-readme-branding-day-zero-ops-viral-demo/CHANNEL-POSTS/reddit-rdjs.md
  - .planning/phases/26-readme-branding-day-zero-ops-viral-demo/CHANNEL-POSTS/hackernews.md
key_files_modified: []
decisions:
  - "Channel post drafts live in .planning/phases/26-.../CHANNEL-POSTS/ (internal launch ammo), NOT shipped in repo root."
  - "Each draft is anti-slop-thesis-led — paragraph 1 or paragraph 2 max — across all 4 channels."
  - "No fabricated URLs. Every not-yet-real link (repo URL, demo media, Discord invite) carries an explicit <TBD ...> marker."
  - "Per-channel hero beat mapping: Twitter + HN = Beat A (overlay ring, engineering audience); IG = Beat B (mascot anticipation, visual-first); Reddit DJ = Beat C (silence, DJ-community anti-slop framing)."
  - "Italian IG draft is idiomatic, not literal — 'AI slop' kept in English (recognized term in AI community)."
  - "HN post strategy: NO Bravoh-team voting (vote-ring detection risk). Author first comment must post within 60s of submission."
metrics:
  duration_minutes: ~25
  completed_date: "2026-05-14"
  tasks_completed: 1
  files_created: 6
  files_modified: 0
---

# Phase 26 Plan 03: 4-Channel Post Arsenal Drafted (6 files)

One-liner: **6 channel post drafts covering Twitter (EN), Instagram (EN + IT), Reddit (r/programming + r/Beatmatch/r/DJs), and Hacker News — each anti-slop-thesis-led, each TBD-marker-honest, each with channel-specific hero beat and tone.**

## What Was Done

Created directory `.planning/phases/26-readme-branding-day-zero-ops-viral-demo/CHANNEL-POSTS/` with 6 draft files:

### twitter-en.md

280-char hook + 4-tweet thread. Beat A hero (amber overlay ring on EQ deck synced with reaction). Anti-slop in tweet 1+2. Thread structure: (1) hook with 30s demo MP4 embed, (2) the anti-slop framing — "prompting alone can't fix it, grounding can", (3) the 3-source stack (audio + screen + MIDI), (4) repo + Discord + community PR call.

### instagram-en.md

9:16 Reel caption + alt-text + pinned comment. Beat B hero (mascot anticipation 200ms before voice). Caption leads with "A real DJ friend in your ear — no AI slop." Alt-text describes all 3 beats for accessibility. Hashtag block tuned for IG algorithm (#dj #ai #opensource etc.). Notes for Kaan on cover frame, burnt captions, retention strategy.

### instagram-it.md

Italian translation — idiomatic, not literal. "AI slop" kept in English (recognized term). Italian hashtags (#djitalia #musicaelettronica). Same Beat B hero. Italian alt-text. Note on optimal IT posting time (19-22 CET).

### reddit-rprogramming.md

Full r/programming Show & Tell. Engineering breakdown framing — opens with the negative result ("we couldn't get usable AI reactions out of better prompting") because r/programming hates self-promo and rewards engineering specificity. Body sections: the problem → grounding architecture (3 input streams + EventDetector + cooldowns) → anti-slop stack (negative dictionary + describe-before-infer + past-tense + `<silence/>` token + anti-repetition) → tech stack → honest caveats (Mac+Win, Bravoh proxy, BYO-key path) → 3 explicit feedback asks.

### reddit-rdjs.md

Full r/Beatmatch primary + r/DJs variant. Beat C hero (3 seconds of deliberate silence as anti-slop made visual). Anti-slop framing as "every other AI music tool sounds like a chatbot — we built it to stay quiet when it doesn't have anything to say." Community-controller-PR call. Strategy notes: 12h gap between r/Beatmatch and r/DJs to avoid karma-burn, OP responsiveness mandatory.

### hackernews.md

Show HN title (80-char ceiling, "Show HN: vibemix – open-source AI co-host for DJ sets, grounded in audio/screen/MIDI") + author first comment (post within 60s — HN author-comment-first context discipline). Engineering audience, Beat A hero, 3 feedback asks (anti-slop gate design + controller library scope + API-key-in-distributed-binary problem). Strict no-Bravoh-team-voting rule.

## Front-matter discipline

Every draft has its own YAML front-matter documenting:

- target channel + language
- hero beat (A / B / C)
- media required (GIF / MP4 / screenshot, with aspect ratio)
- explicit TBD marker list
- where the anti-slop thesis lands in the body

## Deviations from Plan

None. Plan executed exactly as written.

## Verification

- All 6 files exist under CHANNEL-POSTS/ ✅
- `grep -l "AI slop\|anti-slop\|hallucin" CHANNEL-POSTS/*.md | wc -l` = 6 ✅
- `grep -l "<TBD" CHANNEL-POSTS/*.md | wc -l` = 6 ✅
- `grep -E "vibemix\.(app|io|com|net|dev)" CHANNEL-POSTS/*.md` = empty (no fabricated domains) ✅
- No regression: `pytest -q` baseline unchanged

## Commits

- `318e412` — docs(26-03): 4-channel post arsenal drafted (6 files)

## Self-Check: PASSED
