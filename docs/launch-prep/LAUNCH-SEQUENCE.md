<!--
SPDX-License-Identifier: Apache-2.0
Phase 44 / LAUNCH-10 — T-7 → T+30 launch sequence (the synchronization
spine for Kaan + Francesco around the v1 ship window).

Every row cross-links to the ROADMAP phase or success criterion it
depends on AND the relevant KAAN-ACTION-LEGAL §LAUNCH-* runbook so the
team can pivot between this orchestration doc, the per-channel
checklist (OUTREACH-CALENDAR.md), and the Kaan-side discharges without
losing context.
-->

# vibemix launch sequence — T-7 → T+30 (LAUNCH-10)

**Phase 44 / LAUNCH-10** — single-source timeline that orchestrates
when each piece of the launch fires. Pairs with the per-channel
checklist in [`OUTREACH-CALENDAR.md`](./OUTREACH-CALENDAR.md). Owners
column tracks the Kaan-vs-Francesco split per row; cross-links column
hard-references the ROADMAP phase or success-criterion the row blocks
on plus the KAAN-ACTION-LEGAL runbook section that holds the
discharge details.

T-0 is the day the public launch post fires on Show HN. Every row's
"Action" + "Verification" block reads as a checklist Kaan or Francesco
ticks through on the day-of.

---

## T-7 — Pre-seed dev-network stars (15-20)

**Owner:** Kaan + Francesco
**Depends on:** [`scripts/dayzero/seed_stars.md`](../../scripts/dayzero/seed_stars.md)
(existing pre-seed star sourcing protocol — do not duplicate; this row
schedules the calendar slot, the doc owns the recipient list)
**Cross-links:** ROADMAP Phase 44 success criterion 6 (outreach calendar
populated); `KAAN-ACTION-LEGAL.md §LAUNCH-09` (post-stage outreach
discharge); Pitfall P59 (the "marketing-favour star" trap that
seed_stars.md is the antidote to)

**Action:**
- Block a 90-minute calendar slot on T-7 morning. Walk the 15-20
  aligned-community recipients in `seed_stars.md` and send the personal
  "I built this — would love your honest read" outreach copy from that
  protocol.
- Do NOT cold-DM strangers; do NOT batch-send. The whole point of P59 is
  that the seeding has to come from people who will actually use
  vibemix.

**Verification:**
- ≥15 confirmations replied with "yes I'll star it on launch day"
- The reply list logged in the Kaan-side launch journal (private; not
  committed to the repo)

---

## T-3 — DJ TechTools Discord soft-launch

**Owner:** Kaan
**Depends on:** [`OUTREACH-CALENDAR.md` §3](./OUTREACH-CALENDAR.md#3-dj-techtools-discord-t-3-soft-launch-slot)
(the channel + time window + copy block); the Bravoh Discord posting
credentials (separate community — see below)
**Cross-links:** `KAAN-ACTION-LEGAL.md §LAUNCH-08` (Discord live-
execution discharge — the Bravoh-side Discord auto-provision runbook,
NOT the DJ TechTools Discord; the §LAUNCH-08 credentials are still the
"Discord-posting muscle memory" Kaan uses on this T-3 soft-launch)

**Action:**
- 19:00-22:00 CET window. Post the copy block from
  `OUTREACH-CALENDAR.md §3` into the agreed DJ TechTools Discord
  channel (default `#gear-talk`, confirmed with Ean Golden ahead of
  T-3).
- Stay in the channel for 60-90 min after posting to answer any
  immediate "wait what does it actually do" questions in real time.

**Verification:**
- The post is up in the agreed channel
- The first 3 questions answered by Kaan within 90 min
- Status checkbox in `OUTREACH-CALENDAR.md §3` ticked from `Slot
  Reserved` → `Posted`

---

## T-0 — Show HN early-morning ET + 5-channel social cross-post + outreach calendar emails fired

**Owner:** Kaan + Francesco
**Depends on:** Phase 45 SHIP-07 (`gh release create` for v0.1.0 / v1.0.0
tag); Phase 45 SHIP-08 (`scripts/dayzero/launch_trigger.sh --publish`
the 5-channel social cross-post fan-out); Phase 45 SHIP-09 (Show HN
post itself, plus the day-of monitoring rotation kickoff)
**Cross-links:** `KAAN-ACTION-LEGAL.md §LAUNCH-07` (SHIP-TWEET copy-
lock — the signed-off copy that the launch_trigger.sh fan-out fires);
`KAAN-ACTION-LEGAL.md §LAUNCH-09` (outreach calendar discharge — the
email-pitch send-window aligns with the social fan-out on T-0)

**Action:**
- Early-morning ET window (06:00-08:00 ET maximises HN front-page dwell
  time before the US wakes up).
- Run `scripts/dayzero/launch_trigger.sh --publish` to fire the
  twitter / instagram / linkedin / reddit / discord cross-post fan-out
  (copy locked in `scripts/dayzero/launch_copy/` per §LAUNCH-07).
- Send the 3 editorial pitches from `OUTREACH-CALENDAR.md §1`
  (DJ TechTools, DDJ Tips, Mixmag) on the same window.
- Post the Show HN submission with the locked title from §LAUNCH-07.
- Tick the `Sent` checkbox in `OUTREACH-CALENDAR.md` for each entry as
  it goes live.

**Verification:**
- `gh release view v0.1.0` (or v1.0.0) returns the release
- Show HN submission live at the locked title
- All 5 social channels show the launch post
- All 3 editorial pitch emails sent (status ticked in
  OUTREACH-CALENDAR.md §1)
- All 3 subreddit cross-posts live (status ticked in
  OUTREACH-CALENDAR.md §2)

---

## T+24h — Maintainer-answers-every-comment commitment

**Owner:** Kaan (primary) + Francesco (US-evening coverage)
**Depends on:** [`docs/launch-rotation.md`](../launch-rotation.md)
(existing Phase 39 doc — the 6-hour-slot rotation schedule); the Bravoh
ops endpoint at `docs/bravoh-ops-endpoint.md` for any "vibemix uses
Bravoh API how does that work" questions
**Cross-links:** `KAAN-ACTION-LEGAL.md §SHIP-ROTATE` (rotation
discharge); ROADMAP Phase 45 SHIP-09 (the day-of monitoring rotation
kickoff lands the schedule from `launch-rotation.md` on real
calendars)

**Action:**
- The first 24 hours after T-0 are the load-bearing engagement window.
  Every HN comment, every reddit reply, every editor follow-up gets a
  maintainer response within 6 hours (per the §SHIP-ROTATE rotation
  schedule).
- Use the rotation in `docs/launch-rotation.md` to split coverage so
  neither operator burns out.

**Verification:**
- HN comment-reply rate ≥ 90% within 6 hours
- All 3 subreddit threads have at least one OP reply per top-level
  comment
- No editor follow-up sits in inbox for >12 hours

---

## T+72h — Substack "how we built it" post

**Owner:** Kaan (writer) + Francesco (review)
**Depends on:** the T-0 launch numbers (stars + installs + Discord
joins) being recent enough to cite; the Bravoh public Substack already
existing
**Cross-links:** `KAAN-ACTION-LEGAL.md §LAUNCH-09` (post-stage outreach
discharge — Substack is the "longer-form follow-up" channel the
calendar references); Phase 39 deferred-item Substack draft slot
(roadmap line)

**Action:**
- T+72h is the sweet spot — the launch is fresh enough to be relevant
  and the numbers are stable enough to cite. Publish a "how we built
  it" post on the Bravoh Substack.
- 5-7 bullet outline (the lock-in framing per CONTEXT §LAUNCH-10):

  1. **Why we built it for DJs, not for VCs.** Bravoh's first OSS ship,
     the warm-up signal for the closed beta — but vibemix has to stand
     on its own as a real DJ utility first.
  2. **Anti-slop is a UX problem, not an LLM problem.** Every "AI for
     DJs" tool we'd tried was generic chatbot output; the bar we held
     was "real DJ friend in your ear, not voice-assistant slop".
  3. **The 3-Part Gemini grounding stack.** Audio + screen + MIDI fed
     to Gemini Live as three separate Parts — the LLM sees the actual
     evidence it is reacting to, never invents what it didn't hear.
  4. **What we cut.** No CLAP, no ProDJ Link, no stem separation, no
     multi-provider AI. Utility-only scope (link the
     `feedback_no_scope_creep_clean_utility` discipline).
  5. **The 30-day star delta.** Cite the actual number — set the bar
     visible per `project_github_star_goal` (500-1000+).
  6. *(Optional)* The macOS BlackHole + Windows-WASAPI install dance
     and why one-click install was the hardest single problem.
  7. *(Optional)* What Francesco's DJ ear caught that the engineering
     review missed.

**Verification:**
- Substack post live with the draft outline above as the bullet
  skeleton
- Cross-posted as a top-level comment under the HN thread (if still
  active)
- Linked from the README "blog" badge (if added)

---

## T+7d — "Week-1 numbers" transparency post

**Owner:** Kaan
**Depends on:** week-1 telemetry numbers (stars, installs, Discord
members, AI-slop incident count, PRs merged, controller-mapping
contributions); ROADMAP Phase 44 success criterion 6 (the outreach
fired in this window is what drives these numbers)
**Cross-links:** `KAAN-ACTION-LEGAL.md §LAUNCH-09` (post-stage outreach
discharge — the week-1 post is the second-touch on the audience the
calendar reached); the existing `scripts/dayzero/seed_stars.md`
post-launch-audit section

**Action:**
- T+7d post the "week-1 numbers" transparency block on twitter +
  reddit + Bravoh Substack. The bar is honesty: real numbers, no
  vanity-metric framing.

**Transparency post template** (fill the `____` slots on the day):

```text
vibemix — week 1 transparency post

stars: ____
installs (Mac + Win combined): ____
Discord members: ____
AI-slop incidents reported by users: ____
GitHub PRs merged from contributors: ____
controller-mapping contributions accepted: ____

what we learned: ____

what's next: ____

thank you to: ____
```

**Verification:**
- Post live on twitter + reddit + Substack
- Every `____` slot filled with a real number from the telemetry /
  GitHub Insights / Discord member count

---

## T+30 — SHIP-V1-DECISION review

**Owner:** Kaan (decision) + Francesco (DJ-ear input)
**Depends on:** 30 days of post-launch signal (star delta vs. seed,
weekly active installs, GitHub issue velocity, AI-slop incident rate
trend, controller-mapping contribution rate)
**Cross-links:** Phase 45 SHIP-13 (the ~2-week bake → cut v1.0.0 / cycle
RC2 / pause decision — T+30 here is the wider 30-day version of the
same review); `KAAN-ACTION-LEGAL.md §LAUNCH-09` (outreach 30-day
follow-up close-out)

**Action:**
- Sit down with Francesco. Walk the decision rubric:

  | Signal | Bar | Status (T+30) |
  |--------|-----|----------------|
  | Star delta vs. seed (15-20) | ≥ `____` target stars | `____` |
  | Weekly active installs (M+W) | ≥ `____` target installs | `____` |
  | GitHub issues velocity (PRs / week) | ≥ `____` PRs/week | `____` |
  | AI-slop incidents reported | ≤ `____` per 100 sessions | `____` |
  | Controller-mapping contributions | ≥ `____` accepted | `____` |

  (Bars left as `____` for Kaan to set on T+30 — they are the
  meta-decision of the SHIP-V1-DECISION review itself, and forcing
  them now would just be guessing.)

- Pick one of: **cut v1.0.0** (numbers + DJ-ear both green) / **cycle
  RC2** (engineering green, DJ-ear has a load-bearing finding) /
  **pause** (numbers indicate vibemix is not the v1 OSS warm-up Bravoh
  needs — pivot or absorb back into Bravoh main).

**Verification:**
- Decision logged with reasoning in the Kaan-side launch journal
- If cut: Phase 45 SHIP-13 fires the v1.0.0 release pipeline
- If cycle: Phase 45 cuts an RC2 cycle with the load-bearing finding
  as the closing gate
- If pause: ROADMAP updated, milestone status moved, Bravoh team
  notified

---

## Cross-references

- [`OUTREACH-CALENDAR.md`](./OUTREACH-CALENDAR.md) — per-channel
  outreach checklist (LAUNCH-09)
- [`scripts/dayzero/seed_stars.md`](../../scripts/dayzero/seed_stars.md) —
  pre-seed star sourcing protocol (T-7)
- [`docs/launch-rotation.md`](../launch-rotation.md) — day-of comment-
  rotation schedule (T+24h)
- `KAAN-ACTION-LEGAL.md §LAUNCH-07` — SHIP-TWEET copy-lock discharge
- `KAAN-ACTION-LEGAL.md §LAUNCH-08` — Discord auto-provision discharge
- `KAAN-ACTION-LEGAL.md §LAUNCH-09` — outreach + post-stage discharge
- `KAAN-ACTION-LEGAL.md §SHIP-ROTATE` — day-of rotation discharge
- Phase 45 SHIP-07 / SHIP-08 / SHIP-09 / SHIP-13 — the ROADMAP rows
  this sequence depends on
