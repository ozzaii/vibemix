# Pre-Seeded Star Sourcing Protocol (Day-1)

**Owner:** Kaan + Francesco
**Mission:** Land ≥15 GitHub stars on Day-1 from **aligned-community** sources before the HN/Reddit/Twitter launch goes wide.
**Source phase:** Phase 36 (OPS-12). Pitfall P59 enforced.

---

## Why this protocol exists (Pitfall P59)

> 15 friends star → 15 stars on Day-1 → 14 unstars by Day-7 once they
> realise it was a marketing favour. Net: starless repo on the HN front
> page, visitors bounce.

The launch's first-day-momentum signal is real, but **the quality of
the seeding matters**. This protocol exists to enforce sourcing from
people who will *actually use vibemix* — not marketing-favour acquaintances.

---

## FORBIDDEN — Anti-pattern (P59)

> **NOT 15 random friend-favors.**
>
> Do NOT ask uninvolved friends ("hey, can you star my GitHub repo
> as a favour?"). These stars are reversible, GitHub's anti-fraud may
> flag, and they distort the launch-day momentum signal — leading the
> team to over-invest in a misleading metric.

Specifically the following are off-limits:

- DMing a friend who doesn't DJ, doesn't code, isn't a Bravoh user, just to "help boost".
- A "star-for-star" trade with another indie founder.
- Asking the same person to star multiple Bravoh OSS releases as a recurring favour.
- Buying stars (obvious, but worth stating).

---

## Aligned-community pools (the allowed list)

Source stars exclusively from these pools. Each pool has a different
outreach script — keep it short, value-first, opt-out friendly.

### Pool 1 — Bravoh team + closed-beta users (~8–12 stars)

- Bravoh team members (Kaan, Francesco, Momo, Francis, …).
- Closed-beta artists already invested in the Bravoh ecosystem.
- Outreach: "vibemix is the first Bravoh OSS release — DJ-focused.
  If you want to follow it, here's the repo." No favour-language.

### Pool 2 — Kaan + Francesco's DJ network (~5+ stars)

- Real DJs Kaan and Francesco have played with / shared tracks with.
- They get the *product brief* first (a paragraph + 30s demo). Star
  request comes only if they confirm the product looks useful to them.
- Outreach: "Building an AI DJ co-host. Here's a 30s demo. If you'd
  use this in a set, the repo's [link] — star to follow the v0.2."

### Pool 3 — ARRAY OSS community + Bravoh contributors

- ARRAY developers (Bravoh-adjacent OSS community).
- People who've contributed to other Bravoh OSS repos.
- Outreach: standard new-OSS-launch post in the community channel.

### Pool 4 — Contributor circle (Kaan's GitHub graph)

- People who've previously starred a Bravoh repo, contributed to a
  Kaan project, or have engaged on past launches.
- Outreach: low-key Twitter/X post linking the repo. No DMs.

---

## Day-1 logging

Log every aligned star locally to `scripts/dayzero/seed_stars.log`. The
log is **gitignored** (personal contact info — never committed).

Each line: `YYYY-MM-DDTHH:MM:SSZ | pool=<1|2|3|4> | gh-handle=<…> | notes=<…>`

Target: 15 entries before public-launch push.

---

## Reality-check questions before asking anyone to star

1. Would this person plausibly use vibemix in their actual workflow?
2. If a journalist tomorrow asked them "why did you star vibemix?", do they have a real answer?
3. If they don't star, am I OK with that and our relationship is unaffected?

If any answer is "no", **do not ask**. Better 8 aligned stars than 15
marketing-favour stars.

---

## Cross-references

- Pitfall P59 — `.planning/research/v2-1/PITFALLS.md`.
- KAAN-ACTION-LEGAL §OPS-12-OUTREACH — execution authorisation.
- README.md — public-facing star CTA copy.
